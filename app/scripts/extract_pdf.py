"""
Extract monthly production/sales summary data from 2016-2023 《摩托车情报》 PDFs.

Each PDF is one issue of the magazine. It contains two key tables:
  '摩托车生产情况汇总表' (production summary)
  '摩托车销售情况汇总表' (sales summary)

Each table has rows (指标) with columns:
  当月完成，辆 | N月累计，辆 | 上年同期累计，辆 | 增长率，% | 占总量比，%

We extract the '当月完成' column (monthly volume) for:
  - 总计 (total)
  - 两轮合计 / 三轮合计
  - 车型: 骑式车 / 弯梁车 / 踏板车 / 正三轮车 / 边三轮车
  - 排量段 (two-wheeler & three-wheeler buckets)
  - 电动摩托车

CRITICAL: issue number ≠ month (publication lags ~2 months). We parse the REAL
year/month from the summary table title like '2016年7月摩托车生产情况汇总表'.

Output: output/monthly_summary_pdf.csv
  year, month, indicator(生产/销售), scope(总计/二轮/三轮), category, type(汇总/车型/排量), value
Also: output/monthly_export_pdf.csv
  year, month, scope, category(排量段/合计), type(排量/总量), value(当月出口量辆)
  — extracted from '摩托车产品分排量出口量及金额汇总' (2016-2019 PDFs only)
"""

import csv
import re
import warnings
from pathlib import Path

import pdfplumber

warnings.filterwarnings("ignore")

ROOT = Path("C:/Users/Billy Li/Desktop/市场分析报告")
OUT = Path("C:/Users/Billy Li/WorkBuddy/2026-09-06-00-19-46/output")
OUT.mkdir(parents=True, exist_ok=True)

# Displacement buckets (normalized half-width)
DISP_2W = [
    "排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
    "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml",
    "110ml<排量≤125ml", "125ml<排量≤150ml", "150ml<排量≤200ml",
    "150ml<排量≤250ml", "200ml<排量≤250ml", "250ml<排量≤400ml",
    "400ml<排量≤500ml", "400ml<排量≤750ml", "500ml<排量≤800ml",
    "排量>750ml", "排量>800ml",
]
DISP_3W = [
    "排量≤50ml", "50ml<排量≤100ml", "100ml<排量≤150ml", "125ml<排量≤150ml",
    "150ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤750ml", "排量>750ml",
]


def norm_disp(name):
    """Normalize displacement text to canonical half-width form."""
    if not name:
        return None
    s = str(name).strip()
    s = s.replace("＜", "<").replace("＞", ">")
    s = s.replace("\u3000", "").replace(" ", "")
    # unify unit: mL/ml/cc -> ml
    s = s.replace("mL", "ml").replace("cc", "ml").replace("CC", "ml")
    # remove leading markers
    s = re.sub(r"^[·•－—-]*", "", s)
    if s.startswith("≤"):
        s = "排量" + s
    if s.startswith(">"):
        s = "排量" + s
    # if the name ends with a digit (unit was stripped), append 'ml'
    if s and s[-1].isdigit():
        s = s + "ml"
    return s


def match_disp(name, canon_list):
    s = norm_disp(name)
    if not s:
        return None
    for c in canon_list:
        if s == c:
            return c
    return None


def parse_num(s):
    """Parse a number like '1,318,482' or '1 318 482' or '-'. Returns float or None."""
    if s is None:
        return None
    t = str(s).strip()
    if t in ("—", "-", "－", ""):
        return None
    # remove commas, spaces, full-width chars
    t = t.replace(",", "").replace("，", "").replace(" ", "").replace("\u3000", "")
    try:
        return float(t)
    except ValueError:
        return None


def clean_indicator_name(raw):
    """Clean a row's indicator name: strip leading vertical-text residue and
    stray characters like '轮 ', '两 ', '三 '."""
    name = str(raw).strip()
    # Remove leading single-char vertical-text residue (轮/两/三/车/辆 etc.)
    name = re.sub(r"^[轮两三轮车车辆辆]+", "", name)
    name = name.strip()
    # Remove trailing 'mL'/'ml' noise already handled by norm_disp
    return name


def find_files():
    files = []
    for d in ROOT.iterdir():
        if not d.is_dir() or "摩托车情报" not in d.name:
            continue
        for p in d.glob("*.pdf"):
            if p.name.startswith("~$"):
                continue
            files.append(p)
    return sorted(files, key=lambda x: str(x))


def locate_summary_pages(pdf):
    """Find the page indices (0-based) of 生产情况汇总表 and 销售情况汇总表.
    Skip the table-of-contents page (which merely MENTIONS the title but lacks
    the real table header '当月完成')."""
    prod_page = sales_page = None
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        # a real summary table page contains the header '当月完成' (not just
        # '指标'/'当月' which also appear in the TOC as 经济指标/当月出口量)
        if "当月完成" not in text:
            continue
        if prod_page is None and "生产情况汇总表" in text and "销售情况汇总表" not in text:
            prod_page = i
        elif sales_page is None and "销售情况汇总表" in text:
            sales_page = i
        if prod_page is not None and sales_page is not None:
            break
    return prod_page, sales_page


def parse_table_page(text, year, month, indicator):
    """Parse one summary table page into rows."""
    rows = []
    lines = text.split("\n")

    data_started = False
    cur_scope = None  # 总计 / 二轮 / 三轮

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # title line (e.g. '2016年7月摩托车生产情况汇总表')
        if "汇总表" in line:
            data_started = True
            continue
        if "指标" in line and "当月" in line:
            data_started = True
            continue
        if not data_started:
            continue

        # Skip standalone vertical-text residue lines (e.g. '排量', '类型', '两', '轮')
        if line in ("排量", "类型", "两", "轮", "三", "车", "辆"):
            continue

        # Displacement rows: name contains '排量' AND 'mL'. Match the name
        # pattern explicitly, then take the numbers after it.
        if "排量" in line and "mL" in line:
            m = re.match(
                r"^(?:[轮两三轮车辆]*\s*)?(排量[≤＜>＞]\s*\d+|[\d.]+\s*mL\s*[＜≤]\s*排量\s*[≤＜]\s*\d+)\s*mL\s+(.*)$",
                line,
            )
            if m:
                name_raw = m.group(1)
                nums = re.findall(r"[\d,，]+(?:\.\d+)?", m.group(2))
                if not nums:
                    continue
                month_val = parse_num(nums[0])
                canon = match_disp(name_raw, DISP_2W + DISP_3W)
                if canon is None:
                    continue
                scope = "三轮" if cur_scope == "三轮" else "二轮"
                rows.append({
                    "year": year, "month": month, "indicator": indicator,
                    "scope": scope, "category": canon, "type": "排量",
                    "value": month_val,
                })
            continue

        # Non-displacement rows: split at the first digit
        digit_match = re.search(r"[\d]", line)
        if not digit_match:
            continue
        split_idx = digit_match.start()
        name_raw = clean_indicator_name(line[:split_idx])
        nums_part = line[split_idx:]

        num_tokens = re.findall(r"[\d,，]+(?:\.\d+)?", nums_part)
        if not num_tokens:
            continue
        month_val = parse_num(num_tokens[0])

        # Classify the row using normalized name
        name_norm = norm_disp(name_raw)
        # Also handle plain category names (骑式车 etc.) which norm_disp keeps intact
        plain = name_raw.replace(" ", "")

        if name_norm is None and not plain:
            continue

        # Determine classification
        if plain == "总计":
            scope, category, rtype = "总计", "总计", "汇总"
        elif plain == "合计":
            if cur_scope is None or cur_scope == "总计":
                scope, category, rtype = "二轮", "二轮", "汇总"
                cur_scope = "二轮"
            else:
                scope, category, rtype = "三轮", "三轮", "汇总"
                cur_scope = "三轮"
        elif plain in ("骑式车", "弯梁车", "踏板车"):
            # 统一车型命名：骑式车→骑式，弯梁车→弯梁式，踏板车→踏板式
            category = {"骑式车": "骑式", "弯梁车": "弯梁式", "踏板车": "踏板式"}[plain]
            scope, rtype = "二轮", "车型"
        elif plain == "其他":
            scope, category, rtype = "二轮", "其它式", "车型"
        elif plain in ("正三轮车", "边三轮车"):
            scope, category, rtype = "三轮", plain[:-1], "车型"
        elif plain == "电动摩托车":
            scope = "三轮" if cur_scope == "三轮" else "二轮"
            category, rtype = "电动摩托车", "排量"
        else:
            # displacement bucket
            canon = match_disp(name_raw, DISP_2W + DISP_3W)
            if canon is None:
                continue
            scope = "三轮" if cur_scope == "三轮" else "二轮"
            category, rtype = canon, "排量"

        if month_val is None:
            continue

        rows.append({
            "year": year, "month": month, "indicator": indicator,
            "scope": scope, "category": category, "type": rtype,
            "value": month_val,
        })
    return rows


# 分排量出口的排量段（PDF 里的口径，含 ～ 全角波浪号）
EXPORT_DISP_MAP = [
    ("≤50", "排量≤50ml"),
    ("50～100", "50ml<排量≤100ml"),
    ("100～125", "100ml<排量≤125ml"),
    ("125～150", "125ml<排量≤150ml"),
    ("150～200", "150ml<排量≤200ml"),
    ("200～250", "200ml<排量≤250ml"),
    ("250～400", "250ml<排量≤400ml"),
    ("400～500", "400ml<排量≤500ml"),
    ("500～800", "500ml<排量≤800ml"),
    ("＞800", "排量>800ml"),
]


def extract_export_from_pdf(pdf, year, month):
    """Extract '摩托车产品分排量出口量及金额汇总' table (2016-2019 only).
    Returns list of export rows [{scope, category, type, value}] with 当月出口量."""
    rows = []
    # Fast path: check TOC page first — only 2016-2019 PDFs have this table
    toc = pdf.pages[1].extract_text() or "" if len(pdf.pages) > 1 else ""
    if "分排量出口" not in toc:
        return rows
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "分排量出口量及金额" not in text:
            continue
        if "当月统计" not in text:
            continue
        # Found the export summary table page
        lines = text.split("\n")
        rows_has_total = False
        for line in lines:
            line = line.strip()
            # stop at 摩托车发动机 section (整车排量段在其之前)
            if "摩托车发动机" in line:
                break
            # 摩托车整车合计 = 当月出口总量（第一个「合计」行）
            if line.startswith("合计") and not rows_has_total:
                nums = re.findall(r"[\d,，]+", line)
                if nums:
                    v = parse_num(nums[0])
                    if v is not None:
                        rows.append({
                            "year": year, "month": month, "scope": "总计",
                            "category": "总计", "type": "总量", "value": v,
                        })
                        rows_has_total = True
                continue
            if "mL" not in line:
                continue
            # 整车合计行之后出现的排量段是发动机的，跳过
            if rows_has_total:
                continue
            # displacement rows: name ends with 'mL', then export volume
            for key, canon in EXPORT_DISP_MAP:
                if key in line:
                    m = re.search(r"mL\s+([\d,，]+)", line)
                    if not m:
                        continue
                    v = parse_num(m.group(1))
                    if v is None:
                        continue
                    rows.append({
                        "year": year, "month": month, "scope": "二轮",
                        "category": canon, "type": "排量", "value": v,
                    })
                    break
        break  # only first export page
    return rows


def parse_year_month_from_text(text):
    """Parse year/month from a summary page. Handle two layouts:
    1. '2016年7月摩托车生产情况汇总表' (single line)
    2. '年 月摩托车生产情况汇总表' + '2016 7' (vertical split, 2023+)
    Also fall back to '2016年7月' anywhere in text.
    """
    # Layout 1: direct
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Layout 2: '年 月...汇总表' + standalone 'YYYY M'
    # find a line that is exactly 'YYYY M'
    for line in text.split("\n"):
        line = line.strip()
        m2 = re.match(r"^(\d{4})\s+(\d{1,2})$", line)
        if m2 and ("汇总表" in text or "产销综述" in text):
            return int(m2.group(1)), int(m2.group(2))
    return None, None


def extract_pdf(path):
    """Extract summary data from one PDF. Returns (rows, export_rows, (year, month))."""
    rows = []
    export_rows = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            prod_page, sales_page = locate_summary_pages(pdf)
            if prod_page is None or sales_page is None:
                return rows, export_rows, None

            # Parse year/month from production table title
            prod_text = pdf.pages[prod_page].extract_text() or ""
            year, month = parse_year_month_from_text(prod_text)
            if year is None:
                # try the review page (previous page)
                if prod_page > 0:
                    prev_text = pdf.pages[prod_page - 1].extract_text() or ""
                    year, month = parse_year_month_from_text(prev_text)
            if year is None:
                return rows, export_rows, None

            # Production
            rows.extend(parse_table_page(prod_text, year, month, "生产"))
            # Sales
            sales_text = pdf.pages[sales_page].extract_text() or ""
            rows.extend(parse_table_page(sales_text, year, month, "销售"))
            # Export (分排量出口汇总, 2016-2019 only)
            export_rows.extend(extract_export_from_pdf(pdf, year, month))
            return rows, export_rows, (year, month)
    except Exception as e:
        return rows, export_rows, None


def main():
    files = find_files()
    print(f"Found {len(files)} PDF files.")

    all_rows = []
    all_export = []
    stats = []
    for path in files:
        rows, export_rows, ym = extract_pdf(path)
        if ym is None:
            print(f"  SKIP {path.name} (no summary table found)")
            continue
        all_rows.extend(rows)
        all_export.extend(export_rows)
        stats.append((ym[0], ym[1], path.name, len(rows)))
        exp_mark = f", export={len(export_rows)}" if export_rows else ""
        print(f"  {ym[0]}-{ym[1]:02d}: {path.name} -> {len(rows)} rows{exp_mark}")

    # De-dup: a (year, month, indicator, scope, category, type) may appear once
    # per PDF; keep first occurrence.
    seen = {}
    for r in all_rows:
        key = (r["year"], r["month"], r["indicator"], r["scope"], r["category"], r["type"])
        if key not in seen:
            seen[key] = r

    merged = sorted(seen.values(), key=lambda x: (x["year"], x["month"], x["indicator"], x["scope"], x["type"], x["category"]))

    dest = OUT / "monthly_summary_pdf.csv"
    with open(dest, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["year", "month", "indicator", "scope", "category", "type", "value"])
        w.writeheader()
        w.writerows(merged)
    print(f"\nWrote {dest} ({len(merged)} rows)")

    # Export data (2016-2019 分排量出口)
    import pandas as pd
    if all_export:
        exp_dest = OUT / "monthly_export_pdf.csv"
        with open(exp_dest, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["year", "month", "scope", "category", "type", "value"])
            w.writeheader()
            w.writerows(all_export)
        print(f"Wrote {exp_dest} ({len(all_export)} rows)")
        exp_df = pd.DataFrame(all_export)
        tot = exp_df[(exp_df.scope == "总计")]
        if len(tot):
            print(f"  出口覆盖: {tot.year.min()}-{tot.month.min():02d} 到 {tot.year.max()}-{tot.month.max():02d} ({len(tot)} 个月)")

    # Coverage check
    df = pd.DataFrame(merged)
    if len(df):
        total = df[(df.scope == "总计") & (df.indicator == "生产")]
        print(f"\n覆盖月份（生产总计）:")
        print(f"  {total.year.min()}-{total.month.min():02d} 到 {total.year.max()}-{total.month.max():02d}")
        print(f"  共 {len(total)} 个月")
        # 检查月份连续性
        months = sorted(zip(total.year, total.month))
        print(f"  月份序列: {months[:5]} ... {months[-5:]}")


if __name__ == "__main__":
    main()
