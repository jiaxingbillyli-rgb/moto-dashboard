"""
Aggregate monthly motorcycle data into dashboard-friendly JSON.

Inputs:
  output/monthly_summary.csv      (year, month, indicator, scope, category, type, value)
  output/monthly_manufacturer.csv (year, month, manufacturer, indicator, value)
  output/monthly_manufacturer_displacement.csv
                                  (year, month, manufacturer, scope, category, indicator, value)
                                  — adds the 排量 filter dimension

Outputs (output/dashboard_data.json):
  meta: { years, months, indicators, vehicle_types, displacement_2w, displacement_3w, manufacturers }
  monthly_total: [{year, month, indicator, value}] — totals (only the 总计 summary row)
  by_displacement_2w: [{year, month, indicator, category, value}] — 2-wheeler by displacement
  by_displacement_3w: same for 3-wheeler
  by_vehicle_type: [{year, month, indicator, scope, category, value}]
  by_manufacturer: [{year, month, indicator, manufacturer, value}] — monthly per-mfg
  yearly_total: [{year, indicator, value}]
  yearly_by_displacement_2w: [{year, indicator, category, value}]
  yearly_by_displacement_3w: same for 3-wheeler
  yearly_by_vehicle_type: [{year, indicator, scope, category, value}]
  yearly_by_manufacturer: [{year, indicator, manufacturer, value}]
  mfg_monthly_totals: [{manufacturer, indicator, total}]
"""

import json
import os
import pandas as pd
from pathlib import Path

# 由脚本自身位置推导，便于云端部署（本地解析结果与原先的硬编码路径一致，行为不变）
# 需要时可用 DATA_DIR 环境变量显式覆盖
OUT = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent / "output"))
SRC_SUMMARY = OUT / "monthly_summary_full.csv"   # 完整数据 2016-02 ~ 2026-06
SRC_MANUFACTURER = OUT / "monthly_manufacturer.csv"   # 厂家明细（仅 2023-09+）
SRC_MFG_DISP = OUT / "monthly_manufacturer_displacement.csv"  # 厂家×排量（仅 2023-09+）
SRC_EXPORT = OUT / "monthly_export.csv"
SRC_EXPORT_AMOUNT = OUT / "monthly_export_amount.csv"
SRC_EXPORT_MFG = OUT / "monthly_export_mfg.csv"
SRC_EXPORT_PDF = OUT / "monthly_export_pdf.csv"   # PDF 出口 2016-2019（分排量）
DEST = OUT / "dashboard_data.json"


def main():
    s = pd.read_csv(SRC_SUMMARY)
    m = pd.read_csv(SRC_MANUFACTURER)
    md = pd.read_csv(SRC_MFG_DISP)
    ex = pd.read_csv(SRC_EXPORT)
    exa = pd.read_csv(SRC_EXPORT_AMOUNT)
    exm = pd.read_csv(SRC_EXPORT_MFG)
    # PDF 出口数据（2016-2019），如文件存在则合并
    expdf = None
    if SRC_EXPORT_PDF.exists():
        expdf = pd.read_csv(SRC_EXPORT_PDF)

    # Normalize types
    s["value"] = s["value"].astype(float)
    s["year"] = s["year"].astype(int)
    s["month"] = s["month"].astype(int)
    m["value"] = m["value"].astype(float)
    m["year"] = m["year"].astype(int)
    m["month"] = m["month"].astype(int)
    md["value"] = md["value"].astype(float)
    md["year"] = md["year"].astype(int)
    md["month"] = md["month"].astype(int)
    ex["value"] = ex["value"].astype(float)
    ex["year"] = ex["year"].astype(int)
    ex["month"] = ex["month"].astype(int)
    exa["amount"] = exa["amount"].astype(float)
    exa["year"] = exa["year"].astype(int)
    exa["month"] = exa["month"].astype(int)
    exm["value"] = exm["value"].astype(float)
    exm["year"] = exm["year"].astype(int)
    exm["month"] = exm["month"].astype(int)
    if expdf is not None:
        expdf["value"] = expdf["value"].astype(float)
        expdf["year"] = expdf["year"].astype(int)
        expdf["month"] = expdf["month"].astype(int)

    # 车型名称规范化：不同时期报表对「骑式车」命名不一致
    # （早期 PDF 抽成「骑式式」/「骑式」，Excel 用「骑式」），统一为「骑式」
    def norm_vehicle(name):
        if name in ("骑式式", "骑式", "骑式车", "跨骑式"):
            return "骑式"
        return name
    s["category"] = s["category"].map(norm_vehicle)

    # Displacement buckets
    # 注：历史上（2016-2017）排量段口径较粗，含合并段（如 150-250ml、400-750ml、>750ml）。
    # 保持原始段，让历史段自然出现在对应年份（不合并、不造数）。
    displacement_2w = [
        "排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
        "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml",
        "110ml<排量≤125ml", "125ml<排量≤150ml", "150ml<排量≤200ml",
        "150ml<排量≤250ml", "200ml<排量≤250ml", "250ml<排量≤400ml",
        "400ml<排量≤500ml", "400ml<排量≤750ml", "500ml<排量≤800ml",
        "排量>750ml", "排量>800ml", "电动摩托车",
    ]
    displacement_3w = [
        "排量≤50ml", "50ml<排量≤100ml", "100ml<排量≤150ml", "125ml<排量≤150ml",
        "150ml<排量≤250ml", "250ml<排量≤400ml", "400ml<排量≤750ml", "排量>750ml",
        "排量>250ml", "电动摩托车",
    ]

    # Full displacement option list for the filter, grouped by scope so the
    # dropdown can show 二轮 / 三轮 / 电动 groups (no cross-scope overlap).
    # Each option carries a scope so identical bucket names (e.g. 排量≤50ml in
    # both 2W and 3W) stay distinct.
    disp_2w_order = [b for b in displacement_2w]
    disp_3w_order = [b for b in displacement_3w]

    disp_all_2w = sorted(md[md["scope"] == "二轮"]["category"].unique().tolist(),
                         key=lambda x: disp_2w_order.index(x) if x in disp_2w_order else 999)
    disp_all_3w = sorted(md[md["scope"] == "三轮"]["category"].unique().tolist(),
                         key=lambda x: disp_3w_order.index(x) if x in disp_3w_order else 999)

    # Grouped options for the filter dropdown: [{scope, label, buckets:[...]}]
    # 电动摩托车 is a separate scope (电动), so it gets its own group to avoid
    # overlapping with 二轮/三轮 displacement buckets.
    disp_groups = [
        {"scope": "二轮", "label": "二轮摩托车（燃油）", "buckets": disp_all_2w},
        {"scope": "三轮", "label": "三轮摩托车（燃油）", "buckets": disp_all_3w},
        {"scope": "电动", "label": "电动摩托车", "buckets": ["电动摩托车"]},
    ]

    data = {
        "meta": {
            "years": sorted(s["year"].unique().tolist()),
            "months": list(range(1, 13)),
            "indicators": ["生产", "销售"],
            "vehicle_types": ["骑式", "弯梁式", "踏板式", "其它式"],
            "three_wheeler_types": ["正三轮", "边三轮"],
            "displacement_2w": displacement_2w,
            "displacement_3w": displacement_3w,
            "displacement_options": disp_all_2w + disp_all_3w,
            "displacement_groups": disp_groups,
            "displacement_options_2w": disp_all_2w,
            "displacement_options_3w": disp_all_3w,
            "manufacturers": sorted(m["manufacturer"].unique().tolist()),
        },
    }

    # Monthly totals (摩托车总计 across all years)
    monthly_total = (
        s[(s["scope"] == "总计") & (s["category"] == "总计")]
        .sort_values(["year", "month", "indicator"])
        [["year", "month", "indicator", "value"]]
        .to_dict(orient="records")
    )
    data["monthly_total"] = monthly_total

    # By displacement — 2-wheeler only
    disp2w = (
        s[(s["scope"] == "二轮") & (s["type"] == "排量")]
        .sort_values(["year", "month", "indicator", "category"])
        [["year", "month", "indicator", "category", "value"]]
        .to_dict(orient="records")
    )
    data["by_displacement_2w"] = disp2w

    # By displacement — 3-wheeler only
    disp3w = (
        s[(s["scope"] == "三轮") & (s["type"] == "排量")]
        .sort_values(["year", "month", "indicator", "category"])
        [["year", "month", "indicator", "category", "value"]]
        .to_dict(orient="records")
    )
    data["by_displacement_3w"] = disp3w

    # By vehicle type
    vtype = (
        s[s["type"] == "车型"]
        .sort_values(["year", "month", "indicator", "scope", "category"])
        [["year", "month", "indicator", "scope", "category", "value"]]
        .to_dict(orient="records")
    )
    data["by_vehicle_type"] = vtype

    # By manufacturer (monthly)
    mfg_m = (
        m.sort_values(["year", "month", "indicator", "manufacturer"])
        [["year", "month", "indicator", "manufacturer", "value"]]
        .to_dict(orient="records")
    )
    data["by_manufacturer"] = mfg_m

    # Manufacturer x displacement (monthly) — powers the 排量 filter
    mfg_disp = (
        md.sort_values(["year", "month", "indicator", "scope", "category", "manufacturer"])
        [["year", "month", "manufacturer", "scope", "category", "indicator", "value"]]
        .to_dict(orient="records")
    )
    data["mfg_displacement"] = mfg_disp

    # Yearly manufacturer x displacement (for annual tab)
    yearly_mfg_disp = (
        md.groupby(["year", "indicator", "scope", "category", "manufacturer"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator", "scope", "category", "value"],
                     ascending=[True, True, True, True, False])
        .to_dict(orient="records")
    )
    data["yearly_mfg_displacement"] = yearly_mfg_disp

    # Yearly totals (sum of monthly values)
    yearly_total = (
        monthly_total_to_df(monthly_total)
        .groupby(["year", "indicator"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator"])
        .to_dict(orient="records")
    )
    data["yearly_total"] = yearly_total

    # Yearly by displacement 2W
    yearly_disp2w = (
        disp_df(disp2w)
        .groupby(["year", "indicator", "category"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator", "category"])
        .to_dict(orient="records")
    )
    data["yearly_by_displacement_2w"] = yearly_disp2w

    # Yearly by displacement 3W
    yearly_disp3w = (
        disp_df(disp3w)
        .groupby(["year", "indicator", "category"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator", "category"])
        .to_dict(orient="records")
    )
    data["yearly_by_displacement_3w"] = yearly_disp3w

    # Yearly by vehicle type
    yearly_vtype = (
        pd.DataFrame(vtype)
        .groupby(["year", "indicator", "scope", "category"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator", "scope", "category"])
        .to_dict(orient="records")
    )
    data["yearly_by_vehicle_type"] = yearly_vtype

    # Yearly by manufacturer
    yearly_mfg = (
        m.groupby(["year", "indicator", "manufacturer"], as_index=False)["value"].sum()
        .sort_values(["year", "indicator", "value"], ascending=[True, True, False])
        .to_dict(orient="records")
    )
    data["yearly_by_manufacturer"] = yearly_mfg

    # All-time mfg totals
    mfg_all = (
        m.groupby(["indicator", "manufacturer"], as_index=False)["value"].sum()
        .sort_values(["indicator", "value"], ascending=[True, False])
        .to_dict(orient="records")
    )
    data["mfg_all_time_totals"] = mfg_all

    # ---- Export (出口) data ----
    # monthly_export: 合并 Excel 出口（2023.9+）与 PDF 出口（2016-2019）
    if expdf is not None and len(expdf):
        ex_merged = pd.concat([ex, expdf], ignore_index=True).drop_duplicates(
            subset=["year", "month", "scope", "category", "type"], keep="first")
    else:
        ex_merged = ex
    data["export_monthly"] = ex_merged.sort_values(["year", "month", "scope", "category"]).to_dict(orient="records")
    # monthly_export_amount: [{year, month, amount}]
    data["export_amount"] = exa.sort_values(["year", "month"]).to_dict(orient="records")
    # monthly_export_mfg: [{year, month, manufacturer, value}]
    data["export_mfg"] = exm.sort_values(["year", "month", "manufacturer"]).to_dict(orient="records")
    # export total (monthly, 摩托车总计) — 合并 PDF + Excel 的出口总量
    data["export_total"] = ex_merged[(ex_merged["scope"] == "总计") & (ex_merged["type"] == "总量")].sort_values(["year", "month"])[["year", "month", "value"]].to_dict(orient="records")

    # Write JSON
    with open(DEST, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"Wrote {DEST}")
    print(f"  monthly_total: {len(data['monthly_total'])} rows")
    print(f"  by_displacement_2w: {len(data['by_displacement_2w'])} rows")
    print(f"  by_manufacturer: {len(data['by_manufacturer'])} rows")
    print(f"  mfg_displacement: {len(data['mfg_displacement'])} rows")
    print(f"  displacement_options: {len(data['meta']['displacement_options'])} buckets")
    print(f"  export_monthly: {len(data['export_monthly'])} rows")
    print(f"  export_mfg: {len(data['export_mfg'])} rows")
    print(f"  yearly_by_displacement_2w: {len(data['yearly_by_displacement_2w'])} rows")
    print(f"  yearly_by_manufacturer: {len(data['yearly_by_manufacturer'])} rows")


def monthly_total_to_df(records):
    return pd.DataFrame(records)


def disp_df(records):
    return pd.DataFrame(records)


if __name__ == "__main__":
    main()
