"""
Extract monthly motorcycle production/sales data from 全国摩托车生产企业产销情况月报 Excel files.

Two schema eras:
  Era A (2023-09 ~ 2024-12): "摩托车生产企业生产情况汇总表", "摩托车生产企业销售情况汇总表"
  Era B (2025-06 ~ 2026-06): "生产汇总表", "销售汇总表"

For per-manufacturer detail (filter on manufacturer):
  Era A: separate "摩托车生产企业生产情况表" / "摩托车生产企业销售情况表" (8 cols)
  Era B: stacked in "企业产销情况表（合并）" — production starts at row 1, sales at row ~100

Outputs:
  data/monthly_summary.csv  — one row per (year, month, indicator[生产/销售], category)
                              where category is either 车型 (跨骑/弯梁/踏板/其他/二轮/三轮)
                              or 排量 bucket.
  data/monthly_manufacturer.csv — one row per (year, month, indicator, manufacturer_name, total)
"""

import os
import re
import csv
from pathlib import Path
import openpyxl
import xlrd
import warnings

warnings.filterwarnings("ignore")

ROOT = Path("C:/Users/Billy Li/Desktop/市场分析报告")
OUT = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent / "output"))
OUT.mkdir(parents=True, exist_ok=True)

# Displacement buckets for 二轮 (2-wheeled)
DISPLACEMENT_2W = [
    "排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
    "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml",
    "110ml<排量≤125ml", "125ml<排量≤150ml", "150ml<排量≤200ml",
    "200ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤500ml",
    "500ml<排量≤800ml", "排量>800ml", "电动摩托车",
]
# Displacement buckets for 三轮 (3-wheeled)
DISPLACEMENT_3W = [
    "排量≤50ml", "50ml<排量≤100ml", "100ml<排量≤150ml",
    "150ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤750ml",
    "排量>750ml", "电动摩托车",
]
# Vehicle types
VEHICLE_TYPES = ["跨骑式摩托车", "弯梁式摩托车", "踏板式摩托车", "其它式摩托车"]


def normalize_name(name):
    """Strip leading whitespace + full-width space from manufacturer name."""
    if name is None:
        return None
    name = str(name).replace("\u3000", "").strip()
    # 去掉「其中：」「一、」「二、」等分类前缀（如「其中：跨骑式摩托车」→「跨骑式摩托车」）
    name = re.sub(r"^(其中[：:])", "", name)
    name = re.sub(r"^[一二三四五六七八九十]+[、.．]", "", name)
    return name


def is_duplicate_row(name):
    """Manufacturer names starting with '*' are duplicate-count markers used by
    the industry report (e.g. '*洛阳北方易初摩托车有限公司' is already included in
    '洛阳北方企业集团有限公司'). Verified against the report's own subtotals."""
    if name is None:
        return False
    return str(name).replace("\u3000", "").strip().startswith("*")


def parse_year_month_from_filename(fname):
    """Return (year, month) tuple from filenames like '2024年1月...'."""
    m = re.search(r"(\d{4})年(\d{1,2})月", fname)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def find_excel_files():
    """Return list of (path, year, month) for all valid Excel files."""
    files = []
    for p in ROOT.rglob("*.xlsx"):
        if p.name.startswith("~$"):  # office lock file
            continue
        if "Thumbs.db" in p.name or "New Microsoft" in p.name:
            continue
        # we only want 月报 files
        if "产销情况月报" not in p.name and "市场分析" not in str(p):
            continue
        if "月报" not in p.name:
            continue
        y, m = parse_year_month_from_filename(p.name)
        if y is None:
            continue
        files.append((p, y, m, "xlsx"))

    for p in ROOT.rglob("*.xls"):
        if p.name.startswith("~$"):
            continue
        if "月报" not in p.name:
            continue
        y, m = parse_year_month_from_filename(p.name)
        if y is None:
            continue
        files.append((p, y, m, "xls"))

    # Dedup by (year, month) - prefer 2025 folder version for 2024-12 (just in case)
    seen = {}
    for path, y, m, fmt in files:
        key = (y, m)
        if key not in seen:
            seen[key] = (path, y, m, fmt)
    return sorted(seen.values(), key=lambda x: (x[1], x[2]))


def find_sheet(wb, candidates):
    """Find first sheet whose name matches, skipping CCS客户 / temp sheets.
    'CCS客户摩托车生产企业生产情况表' CONTAINS '摩托车生产企业生产情况表', so a naive
    substring match picks the wrong table. Exclude those prefixes."""
    names = [n for n in wb.sheetnames
             if not n.startswith("CCS") and not n.startswith("~$")]
    for c in candidates:                    # exact
        if c in names:
            return c
    for name in names:                      # suffix
        for c in candidates:
            if name.endswith(c):
                return name
    for name in names:                      # substring
        for c in candidates:
            if c in name:
                return name
    return None


def detect_era(wb):
    """Return ('A' or 'B') based on sheet names. Era A: '摩托车生产企业生产情况汇总表';
    Era B: '生产汇总表' (sometimes with prefix like 'Z02 ')."""
    names = wb.sheetnames
    if any("摩托车生产企业生产情况汇总表" in n for n in names):
        return "A"
    if any("生产汇总表" in n for n in names):
        return "B"
    return None


def extract_summary_sheet(ws, year, month, indicator):
    """Extract displacement + vehicle type rows from a summary sheet.

    Returns list of dicts:
      {year, month, indicator, scope, category, type, value}
    """
    rows = []
    # Find row where indicator name starts with a key
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if not row:
            continue
        name = normalize_name(row[0])
        if not name:
            continue

        # 当前月完成数量  = col B (index 1)
        # 本月累计         = col C
        # 去年同期累计     = col D
        # We use 本月完成 (single month value) for monthly granularity.
        cur_month = row[1] if len(row) > 1 else None
        if not isinstance(cur_month, (int, float)):
            continue

        # 二轮 vehicle types
        if name in VEHICLE_TYPES:
            rows.append({
                "year": year, "month": month, "indicator": indicator,
                "scope": "二轮", "category": name.replace("摩托车", ""),
                "type": "车型",
                "value": float(cur_month),
            })
            continue
        # 三轮 vehicle types (正/边)
        if name in ("正三轮摩托车", "边三轮摩托车"):
            rows.append({
                "year": year, "month": month, "indicator": indicator,
                "scope": "三轮", "category": name.replace("摩托车", ""),
                "type": "车型",
                "value": float(cur_month),
            })
            continue
        # 二轮合计 / 三轮合计 / 总计
        if name in ("摩托车总计", "一、二轮摩托车合计", "二、三轮摩托车合计"):
            label = name.replace("摩托车合计", "").replace("摩托车总计", "总计")
            scope = "总计" if name == "摩托车总计" else ("二轮" if "二轮" in name else "三轮")
            rows.append({
                "year": year, "month": month, "indicator": indicator,
                "scope": scope, "category": label,
                "type": "汇总",
                "value": float(cur_month),
            })
            continue
        # Displacement buckets for 二轮
        if name in DISPLACEMENT_2W:
            rows.append({
                "year": year, "month": month, "indicator": indicator,
                "scope": "二轮", "category": name,
                "type": "排量",
                "value": float(cur_month),
            })
            continue
        # Displacement buckets for 三轮
        if name in DISPLACEMENT_3W:
            rows.append({
                "year": year, "month": month, "indicator": indicator,
                "scope": "三轮", "category": name,
                "type": "排量",
                "value": float(cur_month),
            })
            continue
    return rows


def extract_manufacturer_old(wb, year, month):
    """For Era A: separate production / sales sheets.

    Sheet names: 摩托车生产企业生产情况表 / 摩托车生产企业销售情况表
    (sometimes prefixed, e.g. 'X01 摩托车生产企业生产情况表').

    Layout varies slightly by month — typical pattern:
      Row 1: title (merged cells)
      Row 2: column group headers (序号, 企业名称, 合计, 排量≤50ml, ...)
      Row 3: sub-headers (二冲程, 四冲程)
      Row 4: column-level headers (本月完成, 本月累计, ...)
      Row 5: 合计 row (sometimes at top, sometimes absent for 4-stroke-only)
      Row 6+ : manufacturer rows

    Col 0=序号, Col 1=企业名称, Col 2=合计's 本月完成

    We dynamically locate the 合计 row (if any) and skip everything up to and
    including it; manufacturer data starts after.
    """
    out = []
    prod_sheet = find_sheet(wb, ["摩托车生产企业生产情况表"])
    sales_sheet = find_sheet(wb, ["摩托车生产企业销售情况表"])
    for sheet_name, indicator in [
        (prod_sheet, "生产"),
        (sales_sheet, "销售"),
    ]:
        if not sheet_name:
            continue
        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))

        # Find data start: skip until row whose col 1 == '合计' (if present),
        # otherwise skip 4 header rows.
        # data_start = 0-based index of the FIRST data row.
        data_start = 4  # default: 4 header rows
        for r_idx, row in enumerate(all_rows[:8]):
            if not row or len(row) < 2:
                continue
            c1 = normalize_name(row[1])
            if c1 == "合计":
                data_start = r_idx + 1  # skip the 合计 row itself
                break

        for row in all_rows[data_start:]:
            if not row or len(row) < 3:
                continue
            name = normalize_name(row[1])
            if not name or name in ("合计", "全国", "总计"):
                continue
            if is_duplicate_row(name):
                continue
            v = row[2]
            if not isinstance(v, (int, float)):
                continue
            out.append({
                "year": year, "month": month,
                "manufacturer": name, "indicator": indicator,
                "value": float(v),
            })
    return out


def is_top_level_title(title):
    """Era B combined sheet has dozens of stacked tables. We only want the
    TOP-LEVEL production and sales tables, not the sub-categorized ones
    (燃油, 排量, 二轮, 三轮, 跨骑式, 弯梁式, 踏板式, 普通客, 普通货, 电动).
    """
    if "情况表" not in title:
        return False
    sub_keywords = ["燃油", "排量", "二轮", "三轮", "跨骑式", "弯梁式",
                    "踏板式", "普通客", "普通货", "电动"]
    return not any(k in title for k in sub_keywords)


def extract_combined_manufacturer(rows_iter, year, month):
    """Unified extractor for Era B combined manufacturer sheets.

    `rows_iter` yields (col0, col1, col2, ...) tuples (1-based row numbering
    is irrelevant — we work row-by-row).
    """
    out = []
    current_indicator = None
    for row in rows_iter:
        if not row:
            continue
        cell0 = row[0]
        if not cell0:
            continue
        # Keep RAW value: str.strip() also strips the full-width space '\u3000'
        # that marks sub-total rows like '　二冲程合计'. Test the prefix BEFORE
        # stripping, otherwise subtotals leak in as if they were manufacturers.
        raw0 = str(cell0)
        cell0 = raw0.strip()

        if "情况表" in cell0:
            if is_top_level_title(cell0):
                if "生产情况表" in cell0 and "销售" not in cell0:
                    current_indicator = "生产"
                elif "销售情况表" in cell0:
                    current_indicator = "销售"
                else:
                    current_indicator = None
            else:
                current_indicator = None
            continue

        if not current_indicator:
            continue

        if cell0 == "企业名称":
            continue
        if cell0 in ("合计", "电动摩托车总计"):
            continue
        # Sub-total rows: full-width-space prefix + '合计'
        if raw0.startswith("\u3000") and "合计" in cell0:
            continue
        if cell0 in ("二冲程合计", "四冲程合计"):
            continue
        if is_duplicate_row(cell0):
            continue

        name = normalize_name(row[0])
        v = row[1] if len(row) > 1 else None
        if not isinstance(v, (int, float)):
            continue

        out.append({
            "year": year, "month": month,
            "manufacturer": name, "indicator": current_indicator,
            "value": float(v),
        })
    return out


def extract_manufacturer_new(ws, year, month):
    """For Era B: stacked tables in 企业产销情况表（合并） / 企业产销（合并）."""
    return extract_combined_manufacturer(ws.iter_rows(values_only=True), year, month)


def main():
    files = find_excel_files()
    print(f"Found {len(files)} Excel files.")

    summary_rows = []
    manufacturer_rows = []

    for path, y, m, fmt in files:
        try:
            if fmt == "xls":
                wb = xlrd.open_workbook(str(path))
                print(f"  [xls] {y}-{m:02d}: {path.name}")
                for sheet in wb.sheets():
                    name = sheet.name
                    if name in ("生产汇总表", "销售汇总表"):
                        indicator = "生产" if "生产" in name else "销售"
                        for r in range(sheet.nrows):
                            row0 = sheet.cell_value(r, 0)
                            if not row0:
                                continue
                            row_name = normalize_name(row0)
                            if not row_name:
                                continue
                            v = sheet.cell_value(r, 1)
                            if not isinstance(v, (int, float)):
                                continue
                            if row_name in VEHICLE_TYPES:
                                summary_rows.append({
                                    "year": y, "month": m, "indicator": indicator,
                                    "scope": "二轮", "category": row_name.replace("摩托车", ""),
                                    "type": "车型", "value": float(v),
                                })
                            elif row_name in ("正三轮摩托车", "边三轮摩托车"):
                                summary_rows.append({
                                    "year": y, "month": m, "indicator": indicator,
                                    "scope": "三轮", "category": row_name.replace("摩托车", ""),
                                    "type": "车型", "value": float(v),
                                })
                            elif row_name in ("摩托车总计", "一、二轮摩托车合计", "二、三轮摩托车合计"):
                                scope = "总计" if row_name == "摩托车总计" else ("二轮" if "二轮" in row_name else "三轮")
                                summary_rows.append({
                                    "year": y, "month": m, "indicator": indicator,
                                    "scope": scope, "category": scope,
                                    "type": "汇总", "value": float(v),
                                })
                            elif row_name in DISPLACEMENT_2W:
                                summary_rows.append({
                                    "year": y, "month": m, "indicator": indicator,
                                    "scope": "二轮", "category": row_name,
                                    "type": "排量", "value": float(v),
                                })
                            elif row_name in DISPLACEMENT_3W:
                                summary_rows.append({
                                    "year": y, "month": m, "indicator": indicator,
                                    "scope": "三轮", "category": row_name,
                                    "type": "排量", "value": float(v),
                                })
                    elif "企业产销" in name or "企业生产" in name or "企业销售" in name:
                        # Manufacturer stacked table — use unified extractor.
                        def rows_iter():
                            for r in range(sheet.nrows):
                                yield [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                        manufacturer_rows.extend(extract_combined_manufacturer(rows_iter(), y, m))
                continue

            wb = openpyxl.load_workbook(str(path), data_only=True)
        except Exception as e:
            print(f"  SKIP {path.name}: {e}")
            continue

        era = detect_era(wb)
        if era is None:
            print(f"  SKIP (unknown era) {path.name}")
            continue

        if era == "A":
            prod_ws = wb[find_sheet(wb, ["摩托车生产企业生产情况汇总表"])]
            sales_ws = wb[find_sheet(wb, ["摩托车生产企业销售情况汇总表"])]
            summary_rows.extend(extract_summary_sheet(prod_ws, y, m, "生产"))
            summary_rows.extend(extract_summary_sheet(sales_ws, y, m, "销售"))
            manufacturer_rows.extend(extract_manufacturer_old(wb, y, m))
        else:
            prod_ws = wb[find_sheet(wb, ["生产汇总表"])]
            sales_ws = wb[find_sheet(wb, ["销售汇总表"])]
            summary_rows.extend(extract_summary_sheet(prod_ws, y, m, "生产"))
            summary_rows.extend(extract_summary_sheet(sales_ws, y, m, "销售"))
            # Manufacturer detail (stacked)
            mfr_sheet = find_sheet(wb, ["企业产销情况表（合并）", "企业产销（合并）", "企业产销情况表"])
            if mfr_sheet:
                manufacturer_rows.extend(extract_manufacturer_new(wb[mfr_sheet], y, m))
        print(f"  [{era}] {y}-{m:02d}: {path.name} -- {len(wb.sheetnames)} sheets")

    # Write summary CSV
    summary_path = OUT / "monthly_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "indicator", "scope", "category", "type", "value"])
        w.writeheader()
        w.writerows(summary_rows)
    print(f"\nWrote {summary_path} ({len(summary_rows)} rows)")

    # Write manufacturer CSV
    mfr_path = OUT / "monthly_manufacturer.csv"
    with open(mfr_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "manufacturer", "indicator", "value"])
        w.writeheader()
        w.writerows(manufacturer_rows)
    print(f"Wrote {mfr_path} ({len(manufacturer_rows)} rows)")


if __name__ == "__main__":
    main()
