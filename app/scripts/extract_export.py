"""
Extract motorcycle EXPORT (出口) data for the dashboard.

Two schema eras:

Era A (2023-09 ~ 2024-12):
  - '摩托车出口情况汇总表'  : 指标名称 | 本月完成(辆) | 本月累计 | ...
      rows: 摩托车总计 / 一、二轮摩托车合计 / 排量段... / 二、三轮摩托车合计
  - '摩托车出口金额情况汇总表': 指标名称 | 本月完成(万美元) | ...
  - '全国摩托车生产企业整车出口情况表': 厂家 × 排量 宽表（146 列），合计列 = col 2

Era B (2025-01 ~ 2026-06):
  - '摩托车出口1、2张表': 指标名称 | 出口量(辆) col1 | ... | 出口金额(万美元) col5
      rows: 摩托车合计 / 排量段... / 电动摩托车 / 三轮车 / ...
  - '摩托车出口量第3张表' (或 '出口量第3张表'): 企业名称 | 本月完成(辆) | ...

Outputs (output/monthly_export.csv):
  year, month, scope(总计/二轮/三轮/电动), category(排量段 or 汇总), type(总量/排量), value(辆)
Outputs (output/monthly_export_amount.csv):
  year, month, amount(万美元)  — 摩托车出口总额
Outputs (output/monthly_export_mfg.csv):
  year, month, manufacturer, value(辆)  — 厂家出口量
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

DISP_2W_CANON = [
    "排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
    "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml",
    "110ml<排量≤125ml", "125ml<排量≤150ml", "150ml<排量≤200ml",
    "200ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤500ml",
    "500ml<排量≤800ml", "排量>800ml",
]


def norm_disp(name):
    if name is None:
        return None
    s = str(name).strip()
    s = s.replace("＜", "<").replace("＞", ">").replace("（", "(").replace("）", ")")
    s = s.replace("\u3000", "").replace(" ", "")
    if s.startswith("≤"):
        s = "排量" + s
    if s.startswith(">"):
        s = "排量" + s
    return s


def match_canon(name, canon_list):
    if not name:
        return None
    s = norm_disp(name)
    for c in canon_list:
        if s == c:
            return c
    return None


def normalize_name(v):
    if v is None:
        return None
    return str(v).replace("\u3000", "").strip()


def parse_year_month(fname):
    m = re.search(r"(\d{4})年(\d{1,2})月", fname)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def find_sheet(wb, keywords):
    """Find a sheet whose name contains any keyword, skipping CCS/temp sheets."""
    names = [n for n in wb.sheetnames if not n.startswith("CCS") and not n.startswith("~$")]
    for name in names:
        if any(k in name for k in keywords):
            return name
    return None


def detect_era(wb):
    names = wb.sheetnames
    if any("摩托车生产企业生产情况汇总表" in n for n in names):
        return "A"
    if any("生产汇总表" in n for n in names):
        return "B"
    return None


def extract_era_a(wb, year, month):
    """Return (export_rows, amount, mfg_rows)."""
    export_rows = []
    amount = None
    mfg_rows = []

    # 1) 出口量汇总表
    ws = wb["摩托车出口情况汇总表"] if "摩托车出口情况汇总表" in wb.sheetnames else None
    if ws:
        for row in ws.iter_rows(min_row=3, values_only=True):
            if not row or not row[0]:
                continue
            name = normalize_name(row[0])
            if not name:
                continue
            v = row[1]
            if not isinstance(v, (int, float)):
                continue
            if name == "摩托车总计":
                export_rows.append({
                    "year": year, "month": month, "scope": "总计",
                    "category": "总计", "type": "总量", "value": float(v),
                })
            elif "二轮" in name and "合计" in name:
                export_rows.append({
                    "year": year, "month": month, "scope": "二轮",
                    "category": "二轮", "type": "汇总", "value": float(v),
                })
            elif "三轮" in name and "合计" in name:
                export_rows.append({
                    "year": year, "month": month, "scope": "三轮",
                    "category": "三轮", "type": "汇总", "value": float(v),
                })
            elif "跨骑" in name:
                export_rows.append({
                    "year": year, "month": month, "scope": "二轮",
                    "category": "跨骑式", "type": "车型", "value": float(v),
                })
            elif "弯梁" in name:
                export_rows.append({
                    "year": year, "month": month, "scope": "二轮",
                    "category": "弯梁式", "type": "车型", "value": float(v),
                })
            elif "踏板" in name:
                export_rows.append({
                    "year": year, "month": month, "scope": "二轮",
                    "category": "踏板式", "type": "车型", "value": float(v),
                })
            else:
                canon = match_canon(name, DISP_2W_CANON)
                if canon:
                    export_rows.append({
                        "year": year, "month": month, "scope": "二轮",
                        "category": canon, "type": "排量", "value": float(v),
                    })

    # 2) 出口金额汇总表
    ws_a = wb["摩托车出口金额情况汇总表"] if "摩托车出口金额情况汇总表" in wb.sheetnames else None
    if ws_a:
        for row in ws_a.iter_rows(min_row=3, values_only=True):
            if not row or not row[0]:
                continue
            if normalize_name(row[0]) == "摩托车总计" and isinstance(row[1], (int, float)):
                amount = float(row[1])
                break

    # 3) 厂家出口明细（宽表，合计列 = col 2）
    ws_m = wb["全国摩托车生产企业整车出口情况表"] if "全国摩托车生产企业整车出口情况表" in wb.sheetnames else None
    if ws_m:
        for row in ws_m.iter_rows(min_row=6, values_only=True):
            if not row or len(row) < 3:
                continue
            # 企业名称在 col 1；第一行数据是 合计（序号列 col0 为空字符串或'合计'）
            name = normalize_name(row[1])
            if not name or name in ("合计", "企业名称", ""):
                continue
            if name.startswith("*"):
                continue
            v = row[2]  # 合计列「本月完成」出口量
            if not isinstance(v, (int, float)):
                continue
            mfg_rows.append({
                "year": year, "month": month, "manufacturer": name, "value": float(v),
            })

    return export_rows, amount, mfg_rows


def extract_era_b(wb, year, month):
    """Return (export_rows, amount, mfg_rows)."""
    export_rows = []
    amount = None
    mfg_rows = []

    # 1) 出口量+金额表：兼容三种命名
    #   '摩托车出口1、2张表'（量+金额合并）
    #   'CK02 摩托车出口第1张表'（量+金额合并，2025-08）
    #   '摩托车出口情况汇总表'（Era A 量）
    ws = None
    for kw in ["出口1、2", "出口1,2", "出口第1张表", "出口第1张", "出口情况汇总表"]:
        ws = find_sheet(wb, [kw])
        if ws:
            break
    if ws:
        for row in wb[ws].iter_rows(min_row=4, values_only=True):
            if not row or not row[0]:
                continue
            name = normalize_name(row[0])
            if not name:
                continue
            v = row[1]  # 出口量(辆) 本月完成
            amt = row[5] if len(row) > 5 else None  # 出口金额(万美元) 本月完成
            if name == "摩托车合计":
                if isinstance(v, (int, float)):
                    export_rows.append({
                        "year": year, "month": month, "scope": "总计",
                        "category": "总计", "type": "总量", "value": float(v),
                    })
                if isinstance(amt, (int, float)):
                    amount = float(amt)
            elif name == "电动摩托车":
                if isinstance(v, (int, float)):
                    export_rows.append({
                        "year": year, "month": month, "scope": "电动",
                        "category": "电动摩托车", "type": "总量", "value": float(v),
                    })
            elif name == "三轮车":
                if isinstance(v, (int, float)):
                    export_rows.append({
                        "year": year, "month": month, "scope": "三轮",
                        "category": "三轮", "type": "汇总", "value": float(v),
                    })
            else:
                canon = match_canon(name, DISP_2W_CANON)
                if canon and isinstance(v, (int, float)):
                    export_rows.append({
                        "year": year, "month": month, "scope": "二轮",
                        "category": canon, "type": "排量", "value": float(v),
                    })

    # 2) 厂家出口明细（第3张表）
    ws_m = find_sheet(wb, ["出口量第3", "出口第3", "出口量第三"])
    if not ws_m:
        ws_m = find_sheet(wb, ["摩托车出口量第3"])
    if ws_m:
        for row in wb[ws_m].iter_rows(min_row=3, values_only=True):
            if not row or len(row) < 2:
                continue
            name = normalize_name(row[0])
            if not name or "合计" in name or "企业名称" in name:
                continue
            if name.startswith("*"):
                continue
            v = row[1]
            if not isinstance(v, (int, float)):
                continue
            mfg_rows.append({
                "year": year, "month": month, "manufacturer": name, "value": float(v),
            })

    # 3) 车型出口（企业二轮出口表：跨骑/弯梁/踏板 合计行）
    ws_t = find_sheet(wb, ["企业二轮出口表"])
    if ws_t:
        for row in wb[ws_t].iter_rows(values_only=True):
            if not row or not row[0]:
                continue
            name = normalize_name(row[0])
            if not name:
                continue
            v = row[1]
            if not isinstance(v, (int, float)):
                continue
            if "跨骑" in name and "合计" in name:
                export_rows.append({"year": year, "month": month, "scope": "二轮", "category": "跨骑式", "type": "车型", "value": float(v)})
            elif "弯梁" in name and "合计" in name:
                export_rows.append({"year": year, "month": month, "scope": "二轮", "category": "弯梁式", "type": "车型", "value": float(v)})
            elif "踏板" in name and "合计" in name:
                export_rows.append({"year": year, "month": month, "scope": "二轮", "category": "踏板式", "type": "车型", "value": float(v)})

    return export_rows, amount, mfg_rows


def find_files():
    files = []
    for p in ROOT.rglob("*.xlsx"):
        if p.name.startswith("~$") or "月报" not in p.name:
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

    all_export = []
    all_amount = []
    all_mfg = []

    for path, y, m, fmt in files:
        try:
            if fmt == "xls":
                wb = xlrd.open_workbook(str(path))
                # 判断 era
                names = wb.sheet_names()
                era = "B" if any("生产汇总表" in n for n in names) else "A"
                if era == "B":
                    # xls 也走 Era B 逻辑，但 xlrd 需要适配
                    exp_rows, amount, mfg_rows = extract_era_b_xls(wb, y, m)
                else:
                    exp_rows, amount, mfg_rows = [], None, []
            else:
                wb = openpyxl.load_workbook(str(path), data_only=True)
                era = detect_era(wb)
                if era == "A":
                    exp_rows, amount, mfg_rows = extract_era_a(wb, y, m)
                elif era == "B":
                    exp_rows, amount, mfg_rows = extract_era_b(wb, y, m)
                else:
                    exp_rows, amount, mfg_rows = [], None, []
        except Exception as e:
            print(f"  SKIP {path.name}: {e}")
            continue

        all_export.extend(exp_rows)
        if amount is not None:
            all_amount.append({"year": y, "month": m, "amount": amount})
        all_mfg.extend(mfg_rows)
        print(f"  [{era}] {y}-{m:02d}: export={len(exp_rows)} rows, amount={amount}, mfg={len(mfg_rows)} rows")

    # Write export rows
    dest = OUT / "monthly_export.csv"
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "scope", "category", "type", "value"])
        w.writeheader()
        w.writerows(all_export)
    print(f"\nWrote {dest} ({len(all_export)} rows)")

    # Write amount
    dest_a = OUT / "monthly_export_amount.csv"
    with open(dest_a, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "amount"])
        w.writeheader()
        w.writerows(all_amount)
    print(f"Wrote {dest_a} ({len(all_amount)} rows)")

    # Write mfg
    dest_m = OUT / "monthly_export_mfg.csv"
    with open(dest_m, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "manufacturer", "value"])
        w.writeheader()
        w.writerows(all_mfg)
    print(f"Wrote {dest_m} ({len(all_mfg)} rows)")


def extract_era_b_xls(wb, year, month):
    """Era B via xlrd (only used for .xls files, i.e. 2026-03)."""
    export_rows = []
    amount = None
    mfg_rows = []

    # 出口1、2张表
    for sn in wb.sheet_names():
        if "出口1" in sn or "出口1、2" in sn:
            ws = wb.sheet_by_name(sn)
            for r in range(3, ws.nrows):
                name = normalize_name(ws.cell_value(r, 0))
                if not name:
                    continue
                v = ws.cell_value(r, 1)
                amt = ws.cell_value(r, 5) if ws.ncols > 5 else None
                if name == "摩托车合计":
                    if isinstance(v, (int, float)):
                        export_rows.append({"year": year, "month": month, "scope": "总计", "category": "总计", "type": "总量", "value": float(v)})
                    if isinstance(amt, (int, float)):
                        amount = float(amt)
                elif name == "电动摩托车":
                    if isinstance(v, (int, float)):
                        export_rows.append({"year": year, "month": month, "scope": "电动", "category": "电动摩托车", "type": "总量", "value": float(v)})
                elif name == "三轮车":
                    if isinstance(v, (int, float)):
                        export_rows.append({"year": year, "month": month, "scope": "三轮", "category": "三轮", "type": "汇总", "value": float(v)})
                else:
                    canon = match_canon(name, DISP_2W_CANON)
                    if canon and isinstance(v, (int, float)):
                        export_rows.append({"year": year, "month": month, "scope": "二轮", "category": canon, "type": "排量", "value": float(v)})

    # 厂家出口明细
    for sn in wb.sheet_names():
        if "出口量第3" in sn or "出口第3" in sn:
            ws = wb.sheet_by_name(sn)
            for r in range(2, ws.nrows):
                name = normalize_name(ws.cell_value(r, 0))
                if not name or "合计" in name or "企业名称" in name:
                    continue
                v = ws.cell_value(r, 1)
                if not isinstance(v, (int, float)):
                    continue
                mfg_rows.append({"year": year, "month": month, "manufacturer": name, "value": float(v)})

    return export_rows, amount, mfg_rows


if __name__ == "__main__":
    main()
