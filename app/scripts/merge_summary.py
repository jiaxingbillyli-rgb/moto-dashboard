"""
Merge PDF-extracted data (2016-2023) with Excel data (2023.9-2026.6).

Strategy:
- Excel data (monthly_summary.csv) is authoritative for 2023-09 onward.
- PDF data (monthly_summary_pdf.csv) fills 2016-02 ~ 2023-08.
- Overlapping months (2023-09, 2023-10) use Excel data.

Output: output/monthly_summary_full.csv (year, month, indicator, scope, category, type, value)
"""

import pandas as pd
from pathlib import Path

OUT = Path("C:/Users/Billy Li/WorkBuddy/2026-09-06-00-19-46/output")
PDF = OUT / "monthly_summary_pdf.csv"
EXCEL = OUT / "monthly_summary.csv"
DEST = OUT / "monthly_summary_full.csv"


def main():
    pdf = pd.read_csv(PDF)
    excel = pd.read_csv(EXCEL)

    # Normalize types
    for df in (pdf, excel):
        df["value"] = df["value"].astype(float)
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)

    # Excel covers 2023-09 onward. Keep Excel fully.
    # PDF: keep only months BEFORE Excel's earliest month (2023-09).
    excel_min = (excel["year"] * 100 + excel["month"]).min()
    pdf_ym = pdf["year"] * 100 + pdf["month"]
    pdf_early = pdf[pdf_ym < excel_min]

    # Also drop PDF's own 2023-09/10 (Excel has them, more complete for 电动)
    merged = pd.concat([pdf_early, excel], ignore_index=True)

    # Dedup by (year, month, indicator, scope, category, type)
    merged = merged.drop_duplicates(
        subset=["year", "month", "indicator", "scope", "category", "type"],
        keep="first",
    )

    merged = merged.sort_values(["year", "month", "indicator", "scope", "type", "category"])

    merged.to_csv(DEST, index=False, encoding="utf-8-sig")
    print(f"Wrote {DEST} ({len(merged)} rows)")

    # Coverage report
    total = merged[(merged.scope == "总计") & (merged.indicator == "生产")]
    months = sorted(zip(total.year, total.month))
    print(f"\n覆盖月份（生产总计）: {len(months)} 个月")
    print(f"  范围: {months[0][0]}-{months[0][1]:02d} 到 {months[-1][0]}-{months[-1][1]:02d}")

    # Gaps
    all_m = []
    for y in range(2016, 2027):
        for m in range(1, 13):
            all_m.append((y, m))
    present = set(months)
    # limit to range
    lo, hi = months[0], months[-1]
    gaps = [(y, m) for y, m in all_m if lo <= (y, m) <= hi and (y, m) not in present]
    print(f"  缺失月份: {[(f'{y}-{m:02d}') for y, m in gaps] if gaps else '(无)'}")


if __name__ == "__main__":
    main()
