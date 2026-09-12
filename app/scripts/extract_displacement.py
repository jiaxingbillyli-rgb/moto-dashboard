"""
Extract monthly MANUFACTURER x DISPLACEMENT motorcycle production/sales data.

This adds a third filter dimension (排量) to the dashboard. Two schema eras:

Era A (2023-09 ~ 2024-12): wide table in '摩托车生产企业生产情况表' / '...销售情况表'
    Row 1: title (merged cells)
    Row 2: group headers  序号 | 企业名称 | 合计 | 排量≤50ml | 50ml＜排量≤60ml | ...
    Row 3: sub-headers     二冲程 / 四冲程  (per displacement block, 8 cols per block)
    Row 4: column headers  本月完成 | 本月累计 | 去年同期累计 | 同比增长
    Row 5: 合计 (may be absent in some months)
    Row 6+: manufacturer rows

    Column layout per displacement block (starting at col X):
        X    二冲程 本月完成
        X+4  四冲程 本月完成
    Block stride = 8. 2-wheel blocks start at col 6; 3-wheel blocks carry a '（三）' suffix
    in their header. Electric block has 4 sub-columns (二轮轻便/二轮/三轮轻便/三轮).

    Header names use full-width '＜'; normalized to half-width '<'.

Era B (2025-01 ~ 2026-06): stacked sub-tables inside '企业产销情况表（合并）'
    Titles like:
        '2025年6月摩托车生产企业排量≤50ml二轮摩托车生产情况表'
        '2025年6月摩托车生产企业110ml<排量≤125ml三轮摩托车销售情况表'
        '2025年6月摩托车生产企业电动摩托车生产情况表'
    Each sub-table: title row, header row (企业名称/本月完成/...), 合计 row,
    then 二冲程合计 block + 四冲程合计 block (both are sub-totals to skip).

Output: output/monthly_manufacturer_displacement.csv
    year, month, manufacturer, scope(二轮/三轮/电动), category(排量段), indicator, value
"""

import csv
import os
import re
import warnings
from pathlib import Path

import openpyxl
import xlrd

warnings.filterwarnings("ignore")

ROOT = Path("C:/Users/Billy Li/Desktop/市场分析报告")
OUT = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent / "output"))
OUT.mkdir(parents=True, exist_ok=True)

# Canonical 2-wheel displacement buckets (half-width '<')
DISP_2W_CANON = [
    "排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
    "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml",
    "110ml<排量≤125ml", "125ml<排量≤150ml", "150ml<排量≤200ml",
    "200ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤500ml",
    "500ml<排量≤800ml", "排量>800ml",
]
# Canonical 3-wheel displacement buckets
# 注意：源报表（Era A 宽表 + Era B 合并表）的三轮排量段统一为：
#   ≤50 / 50-100 / 100-150 / 150-250 / >250  （>250 是合并段）
# 月度汇总表(summary)里另有 400-750、>750 的细分口径，但与厂家明细表不一致，
# 排量筛选以厂家明细表为准，故此处用合并段。
DISP_3W_CANON = [
    "排量≤50ml", "50ml<排量≤100ml", "100ml<排量≤150ml",
    "150ml<排量≤250ml", "排量>250ml",
]


def norm_disp(name):
    """Normalize displacement header text to canonical half-width form."""
    if name is None:
        return None
    s = str(name).strip()
    # full-width to half-width
    s = s.replace("＜", "<").replace("＞", ">").replace("（", "(").replace("）", ")")
    s = s.replace("\u3000", "").replace(" ", "")
    # unify '排量≤50ml' vs '≤50ml' prefix variants
    if s.startswith("≤"):
        s = "排量" + s
    if s.startswith(">"):
        s = "排量" + s
    return s


def match_canon(name, canon_list):
    """Return canonical name if normalized `name` matches a bucket (tolerating
    'cc' vs 'ml' and spacing)."""
    if not name:
        return None
    s = norm_disp(name)
    for c in canon_list:
        if s == c:
            return c
    # tolerate cc / ml spelling
    s_cc = s.replace("ml", "cc")
    for c in canon_list:
        if s_cc == c.replace("ml", "cc"):
            return c
    return None


def normalize_name(v):
    if v is None:
        return None
    return str(v).replace("\u3000", "").strip()


def is_duplicate_row(name):
    """Rows whose manufacturer name starts with '*' are duplicate-count markers
    used by the industry report (e.g. '*洛阳北方易初摩托车有限公司' is already
    included in '洛阳北方企业集团有限公司'). Verified against the report's own
    subtotals — excluding them makes the per-displacement sums match exactly."""
    return bool(name) and name.startswith("*")


def parse_year_month(fname):
    m = re.search(r"(\d{4})年(\d{1,2})月", fname)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def find_sheet(wb, candidates):
    """Find the main work-sheet, skipping CCS客户 / temp sheets.
    'CCS客户摩托车生产企业生产情况表' CONTAINS '摩托车生产企业生产情况表', so a naive
    substring match picks the wrong (43-col) table. Exclude those prefixes."""
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
    names = wb.sheetnames
    if any("摩托车生产企业生产情况汇总表" in n for n in names):
        return "A"
    if any("生产汇总表" in n for n in names):
        return "B"
    return None


# ---------------- Era A ----------------

def extract_era_a(ws, year, month, indicator):
    """Parse the wide manufacturer table and return
    [{manufacturer, scope, category, value}] for each displacement bucket."""
    out = []
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 5:
        return out

    row_group = rows[1]     # displacement group headers
    row_sub = rows[2]       # 二冲程 / 四冲程
    row_col = rows[3]       # 本月完成 / 本月累计 / ...

    # Locate data start (skip headers + optional 合计 row)
    data_start = 4
    for r_idx, row in enumerate(rows[:8]):
        if not row or len(row) < 2:
            continue
        if normalize_name(row[1]) == "合计":
            data_start = r_idx + 1
            break

    # Build displacement column mapping from the group header row.
    # Collect every group-header column, then, for each block, gather every
    # '本月完成' column within the block and sum them.
    #   Fuel block: 2 strokes (二冲程 at X, 四冲程 at X+4), stride 8 → 2 columns.
    #   Electric block: 4 sub-types × 4 cols (stride 4) → 4 '本月完成' columns.
    group_cols = []  # (start_col, canon_name, scope)
    for col, val in enumerate(row_group):
        if not val:
            continue
        raw = str(val).strip()
        is_3w = "（三）" in raw or "(三)" in raw
        base = raw.replace("（三）", "").replace("(三)", "").strip()
        if "电动" in raw:
            canon, scope = "电动摩托车", "电动"
        else:
            canon = match_canon(base, DISP_3W_CANON if is_3w else DISP_2W_CANON)
            scope = "三轮" if is_3w else "二轮"
        if not canon:
            continue
        group_cols.append((col, canon, scope))
    group_cols.sort()

    blocks = []  # (canon_name, scope, [monthly_done_cols])
    for idx, (start, canon, scope) in enumerate(group_cols):
        end = group_cols[idx + 1][0] if idx + 1 < len(group_cols) else len(row_col)
        month_cols = []
        for c in range(start, end):
            hdr = row_col[c] if c < len(row_col) else None
            if isinstance(hdr, str) and hdr.strip().startswith("本月完成"):
                month_cols.append(c)
        if not month_cols and start < len(row_col):
            month_cols = [start]  # fallback
        blocks.append((canon, scope, month_cols))

    if not blocks:
        return out

    for row in rows[data_start:]:
        if not row or len(row) < 3:
            continue
        name = normalize_name(row[1])
        if not name or name in ("合计", "全国", "总计"):
            continue
        if is_duplicate_row(name):
            continue
        for canon, scope, month_cols in blocks:
            v = 0.0
            got = False
            for c in month_cols:
                if c is None or c >= len(row):
                    continue
                cell = row[c]
                if isinstance(cell, (int, float)):
                    v += float(cell)
                    got = True
            if got and v > 0:
                out.append({
                    "year": year, "month": month,
                    "manufacturer": name, "scope": scope,
                    "category": canon, "indicator": indicator, "value": v,
                })
    return out


# ---------------- Era B ----------------

B_TITLE_RE = re.compile(
    r"摩托车生产企业(?P<disp>.*?)"
    r"(?P<scope>二轮摩托车|三轮摩托车|电动摩托车)"
    r"(?P<ind>生产|销售)情况表"
)
B_SKIP_KEYWORDS = ["跨骑式", "弯梁式", "踏板式", "普通客", "普通货", "燃油"]


def extract_era_b(ws, year, month, sheet_iter):
    """Walk stacked sub-tables; keep only 二轮/三轮/电动 displacement tables."""
    out = []
    cur = None  # (scope, category, indicator)

    for row in sheet_iter:
        if not row:
            continue
        cell0 = row[0]
        if not cell0:
            continue
        # Keep the RAW value: str.strip() also removes the full-width space
        # '\u3000' that marks sub-total rows like '　二冲程合计'. We must test
        # the prefix BEFORE stripping, otherwise those subtotals leak in as if
        # they were manufacturers (which doubles every bucket).
        raw0 = str(cell0)
        cell0 = raw0.strip()

        if "情况表" in cell0:
            # Section boundary — reset unless it's a table we want.
            cur = None
            if any(k in cell0 for k in B_SKIP_KEYWORDS):
                continue
            if "燃油" in cell0 or "发动机" in cell0:
                continue
            m = B_TITLE_RE.search(cell0)
            if not m:
                continue
            disp_raw = m.group("disp")
            scope_raw = m.group("scope")
            indicator = m.group("ind")
            if scope_raw == "电动摩托车":
                scope, category = "电动", "电动摩托车"
            elif scope_raw == "三轮摩托车":
                scope = "三轮"
                category = match_canon(disp_raw, DISP_3W_CANON)
            else:
                scope = "二轮"
                category = match_canon(disp_raw, DISP_2W_CANON)
            if not category:
                continue
            cur = (scope, category, indicator)
            continue

        if not cur:
            continue
        if cell0 == "企业名称":
            continue
        if "km/h" in cell0:
            # 电动子分类标题（带速度标记），整行是该子类别的合计值，非厂家
            continue
        if cell0 in ("合计", "电动摩托车总计"):
            continue
        # Sub-total rows: full-width-space prefix + '合计'
        if raw0.startswith("\u3000") and "合计" in cell0:
            continue
        if cell0 in ("二冲程合计", "四冲程合计"):
            continue
        if "情况表" in cell0:
            continue

        name = normalize_name(row[0])
        if is_duplicate_row(name):
            continue
        v = row[1] if len(row) > 1 else None
        if not isinstance(v, (int, float)):
            continue
        scope, category, indicator = cur
        out.append({
            "year": year, "month": month,
            "manufacturer": name, "scope": scope,
            "category": category, "indicator": indicator, "value": float(v),
        })
    return out


# ---------------- Main ----------------

def find_files():
    files = []
    for p in ROOT.rglob("*.xlsx"):
        if p.name.startswith("~$"):
            continue
        if "月报" not in p.name:
            continue
        y, m = parse_year_month(p.name)
        if y is None:
            continue
        files.append((p, y, m, "xlsx"))
    for p in ROOT.rglob("*.xls"):
        if p.name.startswith("~$") or "月报" not in p.name:
            continue
        y, m = parse_year_month(p.name)
        if y is None:
            continue
        files.append((p, y, m, "xls"))
    seen = {}
    for item in files:
        key = (item[1], item[2])
        seen.setdefault(key, item)
    return sorted(seen.values(), key=lambda x: (x[1], x[2]))


def main():
    files = find_files()
    print(f"Found {len(files)} monthly report files.")
    all_rows = []
    stats = []

    for path, y, m, fmt in files:
        try:
            if fmt == "xls":
                wb = xlrd.open_workbook(str(path))
                print(f"  [xls] {y}-{m:02d}: {path.name}")
                for sheet in wb.sheets():
                    if "企业产销" in sheet.name or "企业生产" in sheet.name or "企业销售" in sheet.name:
                        def it():
                            for r in range(sheet.nrows):
                                yield [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                        got = extract_era_b(None, y, m, it())
                        all_rows.extend(got)
                        stats.append((y, m, len(got)))
                        break
                continue

            wb = openpyxl.load_workbook(str(path), data_only=True)
        except Exception as e:
            print(f"  SKIP {path.name}: {e}")
            continue

        era = detect_era(wb)
        if era == "A":
            got = []
            for sheet_name, indicator in [
                (find_sheet(wb, ["摩托车生产企业生产情况表"]), "生产"),
                (find_sheet(wb, ["摩托车生产企业销售情况表"]), "销售"),
            ]:
                if not sheet_name:
                    continue
                got.extend(extract_era_a(wb[sheet_name], y, m, indicator))
            all_rows.extend(got)
            stats.append((y, m, len(got)))
            print(f"  [A] {y}-{m:02d}: {len(got)} rows")
        elif era == "B":
            sheet_name = find_sheet(wb, ["企业产销情况表（合并）", "企业产销（合并）", "企业产销情况表"])
            if not sheet_name:
                print(f"  [B] {y}-{m:02d}: NO manufacturer sheet")
                continue
            ws = wb[sheet_name]
            got = extract_era_b(ws, y, m, ws.iter_rows(values_only=True))
            all_rows.extend(got)
            stats.append((y, m, len(got)))
            print(f"  [B] {y}-{m:02d}: {len(got)} rows")
        else:
            print(f"  SKIP (unknown era) {path.name}")

    # Aggregate: a manufacturer can appear once per sub-page (二冲程 page and
    # 四冲程 page list the same company separately). Sum them into one record.
    agg = {}
    for r in all_rows:
        key = (r["year"], r["month"], r["manufacturer"], r["scope"],
               r["category"], r["indicator"])
        agg[key] = agg.get(key, 0.0) + r["value"]
    merged = [
        {
            "year": k[0], "month": k[1], "manufacturer": k[2],
            "scope": k[3], "category": k[4], "indicator": k[5],
            "value": round(v, 1),
        }
        for k, v in sorted(agg.items())
    ]

    dest = OUT / "monthly_manufacturer_displacement.csv"
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "year", "month", "manufacturer", "scope", "category", "indicator", "value"])
        w.writeheader()
        w.writerows(merged)
    print(f"\nWrote {dest} ({len(merged)} rows, from {len(all_rows)} raw)")

    # Quick QA: compare per-month sum vs official totals
    try:
        import pandas as pd
        df = pd.DataFrame(merged)
        summ = pd.read_csv(OUT / "monthly_summary.csv")
        print("\n=== QA: displacement-sum vs official 总计 ===")
        bad = 0
        for (yr, mo), g in df.groupby(["year", "month"]):
            for ind in ["生产", "销售"]:
                sub = g[g.indicator == ind]
                # only 2-wheel canonical buckets + electric (exclude 三轮 to compare vs 二轮 total)
                w2 = sub[sub.scope == "二轮"].value.sum()
                off2 = summ[(summ.year == yr) & (summ.month == mo) &
                            (summ.indicator == ind) & (summ.scope == "二轮") &
                            (summ.category == "二轮")].value
                if len(off2) and off2.iloc[0]:
                    pct = abs(w2 - off2.iloc[0]) / off2.iloc[0] * 100
                    if pct > 8:
                        bad += 1
                        if bad <= 12:
                            print(f"  {yr}-{mo:02d} {ind}: disp={w2:,.0f} official={off2.iloc[0]:,.0f} diff={pct:.1f}%")
        print(f"  months outside 8% tolerance: {bad}")
    except Exception as e:
        print(f"  QA skipped: {e}")


if __name__ == "__main__":
    main()
