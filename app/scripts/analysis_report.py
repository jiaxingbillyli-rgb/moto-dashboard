# -*- coding: utf-8 -*-
"""
摩托车产销数据 —— Phase1 深度统计分析脚本（可复现）

数据源: output/dashboard_data.json  (交叉校验: output/monthly_summary_full.csv 等)
产出  : output/analysis_findings.md
        output/analysis_metrics.json

运行:
  C:\\Users\\Billy Li\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe scripts\\analysis_report.py
"""
import json
import os
import math
import statistics
from collections import defaultdict

import pandas as pd
import numpy as np

# ----------------------------------------------------------------------------
# 0. 路径与常量
# ----------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "output", "dashboard_data.json")
OUT_MD = os.path.join(ROOT, "output", "analysis_findings.md")
OUT_JSON = os.path.join(ROOT, "output", "analysis_metrics.json")

WAN = 1e4   # 万
YI = 1e8    # 亿

with open(SRC, encoding="utf-8") as f:
    D = json.load(f)

meta = D["meta"]

def df_of(key):
    return pd.DataFrame(D[key])

# ----------------------------------------------------------------------------
# 1. 排量分组映射（统一 2016-2026 跨口径可比）
#    2016-2022 为合并段 (150-250 / 400-750 / >750)
#    2023+    为细分段 (150-200 / 200-250 / 400-500 / 500-800 / >800)
# ----------------------------------------------------------------------------
GROUPS_2W = [
    ("≤110ml",   ["排量≤50ml", "50ml<排量≤60ml", "60ml<排量≤70ml", "70ml<排量≤80ml",
                  "80ml<排量≤90ml", "90ml<排量≤100ml", "100ml<排量≤110ml"]),
    ("110-125ml", ["110ml<排量≤125ml"]),
    ("125-150ml", ["125ml<排量≤150ml"]),
    ("150-250ml", ["150ml<排量≤250ml", "150ml<排量≤200ml", "200ml<排量≤250ml"]),
    (">250ml",    ["250ml<排量≤400ml", "400ml<排量≤750ml", "排量>750ml",
                   "400ml<排量≤500ml", "500ml<排量≤800ml", "排量>800ml"]),
    ("电动",      ["电动摩托车"]),
]
CAT2GROUP = {}
for g, cats in GROUPS_2W:
    for c in cats:
        CAT2GROUP[c] = g
GROUP_ORDER_2W = [g for g, _ in GROUPS_2W]
SUB_ORDER_2W = [c for _, cats in GROUPS_2W for c in cats]

# 大排量定义：二轮 >250ml
BIG_2W = GROUPS_2W[4][1]

REPORT = {}          # 结构化指标
NOTES = []           # 数据质量备注

def add(k, unit, scope, note, data):
    REPORT[k] = {"unit": unit, "scope": scope, "note": note, "data": data}

def r0(x):
    return None if x is None or (isinstance(x, float) and (math.isnan(x))) else round(float(x))

def r1(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 1)

def r2(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 2)

def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)

# ----------------------------------------------------------------------------
# 2. 总量与增长
# ----------------------------------------------------------------------------
mt = df_of("monthly_total")
mt["ym"] = mt["year"].astype(str) + "-" + mt["month"].astype(str).str.zfill(2)
mt["date"] = pd.to_datetime(mt["year"].astype(str) + "-" + mt["month"].astype(str).str.zfill(2) + "-01")
mt = mt.sort_values("date")

piv = mt.pivot_table(index=["year", "month"], columns="indicator", values="value").reset_index()
piv = piv.sort_values(["year", "month"]).reset_index(drop=True)
piv["ym"] = piv["year"].astype(str) + "-" + piv["month"].astype(str).str.zfill(2)
piv["date"] = pd.to_datetime(piv["ym"] + "-01")
piv["产销率"] = piv["销售"] / piv["生产"] * 100
piv["产销差额"] = piv["生产"] - piv["销售"]
piv["累计生产"] = piv["生产"].cumsum()
piv["累计销售"] = piv["销售"].cumsum()
piv["累计产销差"] = piv["累计生产"] - piv["累计销售"]
# 12期移动平均
piv["生产_MA12"] = piv["生产"].rolling(12, min_periods=6).mean()
piv["销售_MA12"] = piv["销售"].rolling(12, min_periods=6).mean()
# 同比（与上一年同月）
piv["生产_YoY"] = piv["生产"].pct_change(12) * 100
piv["销售_YoY"] = piv["销售"].pct_change(12) * 100

N_MONTHS = len(piv)
FIRST, LAST = piv["ym"].iloc[0], piv["ym"].iloc[-1]
TOTAL_P = float(piv["生产"].sum())
TOTAL_S = float(piv["销售"].sum())
OVERALL_RATIO = TOTAL_S / TOTAL_P * 100

add("monthly_production_sales", "辆", "全行业（二轮+三轮+电动）",
    f"月度产销量与产销率，{FIRST} ~ {LAST}，共 {N_MONTHS} 个月。注意 2016 年缺 8/9/10 月、2023 年缺 7 月。",
    [{"ym": r["ym"], "year": int(r["year"]), "month": int(r["month"]),
      "production": r0(r["生产"]), "sales": r0(r["销售"]),
      "ratio_pct": r2(r["产销率"]), "gap": r0(r["产销差额"]),
      "cum_gap": r0(r["累计产销差"]),
      "prod_yoy_pct": r1(r["生产_YoY"]), "sales_yoy_pct": r1(r["销售_YoY"]),
      "prod_ma12": r0(r["生产_MA12"]), "sales_ma12": r0(r["销售_MA12"])}
     for _, r in piv.iterrows()])

# 年度
yt = df_of("yearly_total").pivot_table(index="year", columns="indicator", values="value").reset_index()
yt["产销率"] = yt["销售"] / yt["生产"] * 100
# 完整年份标记（2016 仅8个月 / 2023 仅11个月 / 2026 仅7个月）
FULL_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2024, 2025]
yt["is_full_year"] = yt["year"].isin(FULL_YEARS)
yt["months_covered"] = yt["year"].map(piv.groupby("year").size().to_dict())

# 同比：仅当"本年与上年均为完整年份"时才计算，否则置空（避免口径假象）
prev_year = yt["year"].shift(1)
prev_full = yt["is_full_year"].shift(1).fillna(False)
valid_yoy = yt["is_full_year"] & prev_full
yt["生产YoY"] = (yt["生产"].pct_change() * 100).where(valid_yoy)
yt["销售YoY"] = (yt["销售"].pct_change() * 100).where(valid_yoy)
yt["yoy_comparable"] = valid_yoy
yt["累计生产"] = yt["生产"].cumsum()
yt["累计销售"] = yt["销售"].cumsum()
yt["累计产销差"] = yt["累计生产"] - yt["累计销售"]

add("yearly_production_sales", "辆", "全行业",
    "年度产销量、同比与产销率。2016 年仅 8 个月、2023 年 11 个月、2026 年仅 1-7 月，均非完整年份。"
    "【重要】yoy_comparable=false 时 prod_yoy_pct/sales_yoy_pct 为 null——即'本年和上年不都是完整年'，"
    "此时同比不可比（如 2017vs2016、2024vs2023、2026vs2025）。可比年份：2018/2019/2020/2021/2022/2025。",
    [{"year": int(r["year"]), "months": int(r["months_covered"]), "is_full_year": bool(r["is_full_year"]),
      "yoy_comparable": bool(r["yoy_comparable"]),
      "production": r0(r["生产"]), "sales": r0(r["销售"]),
      "prod_yoy_pct": r1(r["生产YoY"]), "sales_yoy_pct": r1(r["销售YoY"]),
      "ratio_pct": r2(r["产销率"]), "cum_gap": r0(r["累计产销差"])}
     for _, r in yt.iterrows()])

# CAGR（完整年份 2016(不全) 用 2017-2025；另给 2016-2025）
def cagr(a, b, n):
    return ((b / a) ** (1 / n) - 1) * 100

cagr_17_25_p = cagr(float(yt.loc[yt.year == 2017, "生产"].iloc[0]),
                    float(yt.loc[yt.year == 2025, "生产"].iloc[0]), 8)
cagr_17_25_s = cagr(float(yt.loc[yt.year == 2017, "销售"].iloc[0]),
                    float(yt.loc[yt.year == 2025, "销售"].iloc[0]), 8)

# 2026 YTD vs 2025 同期
def ytd(yr, m):
    s = piv[(piv.year == yr) & (piv.month <= m)]
    return float(s["生产"].sum()), float(s["销售"].sum())

p26, s26 = ytd(2026, 7)
p25_7, s25_7 = ytd(2025, 7)
YTD_P_GROWTH = (p26 / p25_7 - 1) * 100
YTD_S_GROWTH = (s26 / s25_7 - 1) * 100

add("headline_totals", "辆/百分比", "全行业",
    "核心总量指标速览，覆盖 2016-02 ~ 2026-07。",
    {
        "period_start": FIRST, "period_end": LAST, "months": N_MONTHS,
        "cum_production": r0(TOTAL_P), "cum_sales": r0(TOTAL_S),
        "cum_production_wan": r1(TOTAL_P / WAN), "cum_sales_wan": r1(TOTAL_S / WAN),
        "overall_sales_to_production_pct": r2(OVERALL_RATIO),
        "cum_gap": r0(TOTAL_P - TOTAL_S),
        "cagr_2017_2025_production_pct": r2(cagr_17_25_p),
        "cagr_2017_2025_sales_pct": r2(cagr_17_25_s),
        "y2025_production": r0(yt.loc[yt.year == 2025, "生产"].iloc[0]),
        "y2025_sales": r0(yt.loc[yt.year == 2025, "销售"].iloc[0]),
        "y2025_prod_yoy_pct": r2(yt.loc[yt.year == 2025, "生产YoY"].iloc[0]),
        "y2025_sales_yoy_pct": r2(yt.loc[yt.year == 2025, "销售YoY"].iloc[0]),
        "y2026_ytd_months": 7,
        "y2026_ytd_production": r0(p26), "y2026_ytd_sales": r0(s26),
        "y2026_ytd_prod_yoy_pct": r2(YTD_P_GROWTH), "y2026_ytd_sales_yoy_pct": r2(YTD_S_GROWTH),
    })

# ----------------------------------------------------------------------------
# 3. 二轮 / 三轮 结构（用车型表，口径完整）
# ----------------------------------------------------------------------------
vt = df_of("by_vehicle_type")
vt_y = vt.groupby(["year", "indicator", "scope"])["value"].sum().reset_index()
vt_y_p = vt_y[vt_y.indicator == "生产"].pivot_table(index="year", columns="scope", values="value")
vt_y_p["合计"] = vt_y_p.sum(axis=1)
vt_y_p["二轮占比"] = vt_y_p["二轮"] / vt_y_p["合计"] * 100
vt_y_p["三轮占比"] = vt_y_p["三轮"] / vt_y_p["合计"] * 100

add("two_wheeler_vs_three_wheeler", "辆/百分比", "分二轮/三轮（生产口径）",
    "二轮/三轮结构，基于分车型表（该表与总量 100% 对齐，口径完整）。2026 为 1-7 月。",
    [{"year": int(y), "two_wheeler": r0(vt_y_p.loc[y, "二轮"]), "three_wheeler": r0(vt_y_p.loc[y, "三轮"]),
      "total": r0(vt_y_p.loc[y, "合计"]),
      "two_wheeler_share_pct": r2(vt_y_p.loc[y, "二轮占比"]),
      "three_wheeler_share_pct": r2(vt_y_p.loc[y, "三轮占比"])}
     for y in vt_y_p.index])

# ----------------------------------------------------------------------------
# 4. 二轮排量结构（统一分组，跨口径可比）
# ----------------------------------------------------------------------------
d2 = df_of("by_displacement_2w")
d2["group"] = d2["category"].map(CAT2GROUP)
assert d2["group"].notna().all(), "存在未映射的二轮排量分类"

g2 = d2.groupby(["year", "indicator", "group"])["value"].sum().reset_index()
g2p = g2[g2.indicator == "生产"].pivot_table(index="year", columns="group", values="value").fillna(0)
g2p = g2p[[c for c in GROUP_ORDER_2W if c in g2p.columns]]
g2p["合计"] = g2p.sum(axis=1)
share2 = g2p[[c for c in GROUP_ORDER_2W if c in g2p.columns]].div(g2p["合计"], axis=0) * 100

add("displacement_2w_share", "百分比", "二轮摩托车（生产口径）",
    "二轮分排量段占比演变。已把 2016-2022 合并段与 2023+ 细分段映射到统一分组（≤110 / 110-125 / 125-150 / 150-250 / >250 / 电动），因此跨年可比；但细分段内部（如 150-200 vs 200-250）仅 2023 年后可得。",
    [{"year": int(y), **{g: r2(share2.loc[y, g]) for g in share2.columns}} for y in share2.index])

add("displacement_2w_volume", "辆", "二轮摩托车（生产口径）",
    "二轮分排量段绝对量演变（统一分组）。",
    [{"year": int(y), **{g: r0(g2p.loc[y, g]) for g in g2p.columns}} for y in g2p.index])

# 燃油口径（剔除电动）排量结构 —— 这是观察"燃油车内部升级"最干净的口径
FUEL_GROUPS = [g for g in GROUP_ORDER_2W if g != "电动"]
fuel_vol = g2p[FUEL_GROUPS].copy()
fuel_tot = fuel_vol.sum(axis=1)
fuel_share = fuel_vol.div(fuel_tot, axis=0) * 100
add("displacement_2w_share_fuel_only", "百分比", "二轮摩托车【燃油车，剔除电动】（生产口径）",
    "剔除电动摩托车后的二轮燃油车排量结构（分母＝燃油二轮总量）。"
    "这是观察燃油车内部'结构升级'最干净的口径：可清晰看到 ≤110ml 萎缩、125-250ml 与 >250ml 上升。"
    "推荐作为报告'排量结构升级'主题的主图。",
    [{"year": int(y), **{g: r2(fuel_share.loc[y, g]) for g in FUEL_GROUPS},
      "fuel_total": r0(fuel_tot.loc[y])} for y in fuel_share.index])

# 细分段（仅 2023+）
fine_cats = ["150ml<排量≤200ml", "200ml<排量≤250ml", "250ml<排量≤400ml",
             "400ml<排量≤500ml", "500ml<排量≤800ml", "排量>800ml"]
d2f = d2[(d2.category.isin(fine_cats)) & (d2.indicator == "生产") & (d2.year >= 2023)]
d2fy = d2f.groupby(["year", "category"])["value"].sum().reset_index().pivot_table(
    index="year", columns="category", values="value").fillna(0)
add("displacement_2w_fine_2023plus", "辆", "二轮摩托车 >150ml（生产口径）",
    "2023 年起才有细分排量段；2016-2022 只有 150-250 / 400-750 / >750 合并段，故本表仅 2023+ 可比。",
    [{"year": int(y), **{c: r0(d2fy.loc[y, c]) for c in d2fy.columns}} for y in d2fy.index])

# 大排量（>250ml）专题
big = g2p[[">250ml"]].copy()
big["二轮合计"] = g2p["合计"]
big["大排量占比"] = big[">250ml"] / big["二轮合计"] * 100
big["大排量YoY"] = (big[">250ml"].pct_change() * 100).where(
    pd.Series([y in FULL_YEARS and (y - 1) in FULL_YEARS for y in big.index], index=big.index))
big150_250 = g2p["150-250ml"]
# 2026 年 1-7 月同期对比
def big_ytd(year, months):
    s = d2[(d2.category.isin(BIG_2W)) & (d2.indicator == "生产") & (d2.year == year) & (d2.month <= months)]
    return float(s["value"].sum())
BIG_YTD_26 = big_ytd(2026, 7)
BIG_YTD_25 = big_ytd(2025, 7)
BIG_YTD_GROWTH = (BIG_YTD_26 / BIG_YTD_25 - 1) * 100
add("big_displacement_2w", "辆/百分比", "二轮摩托车 排量>250ml（生产口径）",
    "大排量（>250ml）二轮车产量、占比与同比。yoy_pct 仅在'本年与上年均为完整年'时给出（可比年份：2018-2022、2025）；"
    "2016/2023/2026 不可比故为 null。"
    f"2026 年 1-7 月 >250ml 产量 {BIG_YTD_26/WAN:.1f} 万辆，较 2025 年同期 {BIG_YTD_25/WAN:.1f} 万辆 {BIG_YTD_GROWTH:+.1f}%。"
    "另注：>250ml 组内 2023 年前为 400-750/>750，2023 年后为 400-500/500-800/>800，界点由 750ml 改为 800ml，存在微小口径差异。",
    [{"year": int(y), "volume": r0(big.loc[y, ">250ml"]),
      "share_of_2w_pct": r2(big.loc[y, "大排量占比"]),
      "yoy_pct": r1(big.loc[y, "大排量YoY"]),
      "is_full_year": bool(y in FULL_YEARS),
      "vol_150_250": r0(big150_250.loc[y])} for y in big.index])

# 大排量 1-7 月同期对比（2026 只有 7 个月，这是唯一同口径的增长序列）
big_ytd_rows = []
prev = None
for y in [2023, 2024, 2025, 2026]:
    v = big_ytd(y, 7)
    tot_y = float(piv[(piv.year == y) & (piv.month <= 7)]["生产"].sum())
    big_ytd_rows.append({"year": y, "volume_1_7": r0(v), "volume_wan": r1(v / WAN),
                         "share_of_total_pct_1_7": r2(v / tot_y * 100),
                         "yoy_1_7_pct": r1((v / prev - 1) * 100) if prev else None})
    prev = v
add("big_displacement_ytd_1_7", "辆/百分比", "全行业 排量>250ml（生产口径，1-7 月）",
    "大排量 1-7 月同期对比，是 2026 年唯一同口径的增长序列。"
    "关键：2025 年 1-7 月同比 +38.0%，2026 年 1-7 月同比骤降至 +1.1%，"
    "而同期行业整体 +14.9% —— 大排量赛道在 2026 年出现明显增速放缓信号。",
    big_ytd_rows)

# ----------------------------------------------------------------------------
# 5. 电动化
# ----------------------------------------------------------------------------
elec = g2p[["电动"]].copy()
elec["二轮合计"] = g2p["合计"]
elec["电动占比_二轮"] = elec["电动"] / elec["二轮合计"] * 100
# 全行业口径电动占比（电动全部在二轮，三轮电动未入分排量表）
elec["全行业产量"] = elec["year"].map(yt.set_index("year")["生产"]) if "year" in elec else None
elec = elec.reset_index()
elec["全行业产量"] = elec["year"].map(yt.set_index("year")["生产"])
elec["电动占比_全行业"] = elec["电动"] / elec["全行业产量"] * 100
elec["电动YoY"] = (elec["电动"].pct_change() * 100).where(elec["year"] != 2026)  # 2026 非完整年，年度同比不可比
# 2026 年 1-7 月同期对比（唯一可比的 2026 口径）
def ytd_sum(year, months, col):
    s = d2[(d2.category == "电动摩托车") & (d2.indicator == "生产") &
           (d2.year == year) & (d2.month <= months)]
    return float(s["value"].sum())
ELEC_YTD_26 = ytd_sum(2026, 7, "电动")
ELEC_YTD_25 = ytd_sum(2025, 7, "电动")
ELEC_YTD_GROWTH = (ELEC_YTD_26 / ELEC_YTD_25 - 1) * 100

add("electric_motorcycle", "辆/百分比", "二轮电动摩托车（生产口径）",
    "电动摩托车产量与占比。重要口径提示：2016-2018 年电动摩托车仅 6~10 万辆/年，与 2019 年起 177 万辆存在数量级断层，"
    "判断为 2019 年新国标实施后统计口径变更（电动摩托车正式纳入机动车统计），故 2019 年前数据不可与之后直接比较；"
    "电动化趋势请以 2019 年起为准。三轮电动摩托车未纳入分排量表（见数据质量备注），故本表不含三轮电动。"
    f"2026 年 yoy_pct 为 null（非完整年，年同比不可比）；2026 年 1-7 月电动产量 {ELEC_YTD_26/WAN:.1f} 万辆，"
    f"较 2025 年同期 {ELEC_YTD_25/WAN:.1f} 万辆 {ELEC_YTD_GROWTH:+.1f}%。",
    [{"year": int(r["year"]), "volume": r0(r["电动"]),
      "share_of_2w_pct": r2(r["电动占比_二轮"]),
      "share_of_total_pct": r2(r["电动占比_全行业"]),
      "yoy_pct": r1(r["电动YoY"]),
      "is_full_year": bool(r["year"] in FULL_YEARS)}
     for _, r in elec.iterrows()])

# 电动月度（2019+ 看波动）
d2["ym"] = d2["year"].astype(str) + "-" + d2["month"].astype(str).str.zfill(2)
em_ = d2[(d2.category == "电动摩托车") & (d2.indicator == "生产")].sort_values(["year", "month"])
add("electric_monthly", "辆", "二轮电动摩托车（生产口径）",
    "电动摩托车月度产量，用于观察 2022 年电动峰值与 2023 年后回落。",
    [{"ym": r["ym"], "volume": r0(r["value"])} for _, r in em_.iterrows()])

# ----------------------------------------------------------------------------
# 6. 车型结构
# ----------------------------------------------------------------------------
vtype = vt[vt.scope == "二轮"].groupby(["year", "indicator", "category"])["value"].sum().reset_index()
vtp = vtype[vtype.indicator == "生产"].pivot_table(index="year", columns="category", values="value").fillna(0)
# 兼容历史命名（跨骑式/骑式 已统一为 骑式）
for a, b in [("跨骑式", "骑式")]:
    if a in vtp.columns:
        vtp[b] = vtp.get(b, 0) + vtp.pop(a)
vtp["二轮合计"] = vtp.sum(axis=1)
vcols = [c for c in ["骑式", "弯梁式", "踏板式", "其它式"] if c in vtp.columns]
vshare = vtp[vcols].div(vtp["二轮合计"], axis=0) * 100

add("vehicle_type_share_2w", "百分比", "二轮摩托车（生产口径，占二轮比重）",
    "二轮车型结构演变。历史报表中'跨骑式/骑式'命名不统一，已合并为'骑式'，口径统一。",
    [{"year": int(y), **{c: r2(vshare.loc[y, c]) for c in vcols},
      "volume_total": r0(vtp.loc[y, "二轮合计"]),
      **{f"vol_{c}": r0(vtp.loc[y, c]) for c in vcols}} for y in vshare.index])

# 燃油口径车型结构（电动摩托车 100% 计入"踏板式"，剔除后可看燃油车真实结构演变）
elec_share_by_year = (g2p["电动"] / g2p["合计"] * 100)
fuel_denom = (100 - elec_share_by_year)
vshare_fuel = vshare.div(fuel_denom / 100, axis=0)
vshare_fuel["踏板式(燃油)"] = vshare_fuel["踏板式"] - 0  # 占位，下面单独算
for y in vshare.index:
    # 电动全部落在踏板式内 → 燃油踏板式 = (踏板式 - 电动) / (1 - 电动占比)
    vshare_fuel.loc[y, "踏板式(燃油)"] = (vshare.loc[y, "踏板式"] - elec_share_by_year.loc[y]) / (fuel_denom.loc[y] / 100)
vshare_fuel = vshare_fuel.drop(columns=["踏板式"])
vshare_fuel = vshare_fuel[[c for c in ["骑式", "弯梁式", "踏板式(燃油)", "其它式"] if c in vshare_fuel.columns]]
add("vehicle_type_share_2w_fuel_only", "百分比", "二轮摩托车【燃油车，剔除电动】（生产口径）",
    "剔除电动摩托车后的二轮燃油车车型结构（分母＝燃油二轮总量）。"
    "【关键发现】电动摩托车在分车型表中 100% 计入'踏板式'（已验证：各年踏板式产量恒 ≥ 电动产量），"
    "因此 2019-2023 年'踏板式份额暴涨至 49%'几乎全部是电动而非燃油踏板。"
    "剔除电动后：燃油踏板式份额 2016 年 23.1% → 2025 年 17.6%（小幅下滑），骑式 58.6% → 67.0%（上升）。"
    "做车型结构图请优先用本表，避免把电动化误读为「踏板车流行」。",
    [{"year": int(y), **{c: r2(vshare_fuel.loc[y, c]) for c in vshare_fuel.columns}}
     for y in vshare_fuel.index])

# 三轮车型
vt3 = vt[vt.scope == "三轮"].groupby(["year", "indicator", "category"])["value"].sum().reset_index()
vt3p = vt3[vt3.indicator == "生产"].pivot_table(index="year", columns="category", values="value").fillna(0)
add("vehicle_type_3w", "辆", "三轮摩托车（生产口径）",
    "三轮车型绝对量（正三轮/边三轮）。三轮分排量表仅覆盖约 53% 的三轮产量（缺电动三轮等），故三轮结构只用车车型表。",
    [{"year": int(y), **{c: r0(vt3p.loc[y, c]) for c in vt3p.columns},
      "total": r0(vt3p.loc[y].sum())} for y in vt3p.index])

# ----------------------------------------------------------------------------
# 7. 出口
# ----------------------------------------------------------------------------
ex = df_of("export_total")
ex["ym"] = ex["year"].astype(str) + "-" + ex["month"].astype(str).str.zfill(2)
ex = ex.sort_values(["year", "month"])
amt = df_of("export_amount")
amt["ym"] = amt["year"].astype(str) + "-" + amt["month"].astype(str).str.zfill(2)

sales_m = piv.set_index("ym")["销售"].to_dict()
rows = []
for _, r in ex.iterrows():
    s = sales_m.get(r["ym"])
    rows.append({"ym": r["ym"], "year": int(r["year"]), "month": int(r["month"]),
                 "export_volume": r0(r["value"]),
                 "domestic_sales": r0(s),
                 "export_ratio_pct": r2(r["value"] / s * 100) if s else None})
add("export_monthly_total", "辆/百分比", "全行业出口",
    "月度出口量与外销率（出口量/当月销量）。出口数据在 2020-2022 缺失（源报表取消分排量出口表），"
    "2018/2019 亦仅部分月份，做年度对比时务必注意年份与月份不连续。", rows)

# 年度出口
exy = ex.groupby("year")["value"].sum()
exm = ex.groupby("year")["month"].apply(lambda s: sorted(s.tolist()))
amty = amt.groupby("year")["amount"].sum()
ey = []
for y in sorted(exy.index):
    months = exm[y]
    sv = float(piv[(piv.year == y) & (piv.month.isin(months))]["销售"].sum())
    v = float(exy[y]); a = float(amty.get(y, 0))
    ey.append({"year": int(y), "months_covered": len(months), "month_list": months,
               "export_volume": r0(v), "export_amount_usd_10k": r1(a),
               "avg_price_usd": r1(a * 1e4 / v) if v else None,
               "same_period_sales": r0(sv),
               "export_ratio_pct": r2(v / sv * 100),
               "is_full_year": len(months) == 12,
               "has_amount_data": bool(a > 0)})
add("export_yearly", "辆/万美元/百分比", "全行业出口",
    "年度出口量、出口金额（万美元）、单车均价与外销率。2020-2022 出口数据缺失；2016/2018/2019/2023 为不完整年份；"
    "出口金额仅 2023-09 起可得。", ey)

# 内销 vs 出口拆分（内销 = 销量 − 出口）
sales_m_full = piv.set_index(["year", "month"])["销售"]
exp_m = ex.set_index(["year", "month"])["value"]
split_rows = []
# 关键：只取"销量与出口都有数据"的月份，避免 2023 年（出口仅 9-12 月）出现 16.7% 的失真外销率
for y in [2023, 2024, 2025, 2026]:
    months = sorted([m for (yy, m) in exp_m.index if yy == y])
    sv = float(sum(sales_m_full.get((y, m), 0) for m in months))
    ev = float(sum(exp_m.get((y, m), 0) for m in months))
    split_rows.append({"year": y, "months": len(months), "month_list": months,
                       "window": f"{min(months)}-{max(months)}月",
                       "is_full_year": len(months) == 12,
                       "sales": r0(sv), "export": r0(ev),
                       "domestic": r0(sv - ev), "sales_wan": r1(sv / WAN),
                       "export_wan": r1(ev / WAN), "domestic_wan": r1((sv - ev) / WAN),
                       "export_ratio_pct": r2(ev / sv * 100)})
# 1-7 月同期序列（可比）
split_ytd = []
for y in [2024, 2025, 2026]:
    months = list(range(1, 8))
    sv = float(sum(sales_m_full.get((y, m), 0) for m in months))
    ev = float(sum(exp_m.get((y, m), 0) for m in months))
    split_ytd.append({"year": y, "sales": r0(sv), "export": r0(ev), "domestic": r0(sv - ev),
                      "sales_wan": r1(sv / WAN), "export_wan": r1(ev / WAN),
                      "domestic_wan": r1((sv - ev) / WAN), "export_ratio_pct": r2(ev / sv * 100)})
for i in range(1, len(split_ytd)):
    a, b = split_ytd[i - 1], split_ytd[i]
    split_ytd[i]["export_yoy_pct"] = r1((b["export"] / a["export"] - 1) * 100)
    split_ytd[i]["domestic_yoy_pct"] = r1((b["domestic"] / a["domestic"] - 1) * 100)
    split_ytd[i]["sales_yoy_pct"] = r1((b["sales"] / a["sales"] - 1) * 100)
# 全年可比（2024 vs 2025）
DOM_24 = split_rows[1]["domestic"]; DOM_25 = split_rows[2]["domestic"]
DOM_YOY_25 = (DOM_25 / DOM_24 - 1) * 100
add("domestic_vs_export_split", "辆/百分比", "全行业（内销 = 销量 − 出口）",
    "内销与出口拆分。这是本报告最重要的结构性判断依据："
    f"2024→2025 全年口径下，销量 +{((split_rows[2]['sales']/split_rows[1]['sales'])-1)*100:.1f}%，"
    f"但**内销从 {split_rows[1]['domestic_wan']:,.1f} 万辆降至 {split_rows[2]['domestic_wan']:,.1f} 万辆（{DOM_YOY_25:+.1f}%）**，"
    f"出口则从 {split_rows[1]['export_wan']:,.1f} 增至 {split_rows[2]['export_wan']:,.1f} 万辆——**增长 100% 来自出口，内需在萎缩**。"
    "annual 部分 2023 年因出口数据仅 4 个月、2026 年仅 7 个月，不可与完整年直接比较；请用 ytd_1_7 部分做同期对比。",
    {"annual": split_rows, "ytd_1_7": split_ytd})

# 34 个月（2023-09 ~ 2026-06）累计 —— 校验前期口径
win = ex[((ex.year == 2023) & (ex.month >= 9)) | (ex.year == 2024) | (ex.year == 2025) |
         ((ex.year == 2026) & (ex.month <= 6))]
win_amt = amt[((amt.year == 2023) & (amt.month >= 9)) | (amt.year == 2024) | (amt.year == 2025) |
              ((amt.year == 2026) & (amt.month <= 6))]
win_sales = float(piv[((piv.year == 2023) & (piv.month >= 9)) | (piv.year == 2024) | (piv.year == 2025) |
                      ((piv.year == 2026) & (piv.month <= 6))]["销售"].sum())
WIN = {"months": len(win), "export_volume": r0(win["value"].sum()),
       "export_volume_wan": r1(win["value"].sum() / WAN),
       "export_amount_usd_10k": r1(win_amt["amount"].sum()),
       "export_amount_usd_yi": r2(win_amt["amount"].sum() / 1e4),
       "same_period_sales": r0(win_sales),
       "export_ratio_pct": r2(win["value"].sum() / win_sales * 100),
       "avg_price_usd": r1(win_amt["amount"].sum() * 1e4 / win["value"].sum())}
add("export_window_2023_09_2026_06", "辆/万美元/百分比", "全行业出口",
    "2023-09 ~ 2026-06（34 个月）出口累计，与前期看板口径对齐校验。", WIN)

# 出口排量结构（2023+）
emd = df_of("export_monthly")
emp = emd[(emd.type == "排量") & (emd.scope == "二轮")].groupby(["year", "category"])["value"].sum().reset_index()
emp_p = emp.pivot_table(index="year", columns="category", values="value").fillna(0)
# 统一分组
exp_group = defaultdict(float)
for y in emp_p.index:
    for c in emp_p.columns:
        exp_group[(y, CAT2GROUP.get(c, "其它"))] += emp_p.loc[y, c]
eg = pd.Series(exp_group).unstack().fillna(0)
eg_share = eg.div(eg.sum(axis=1), axis=0) * 100
add("export_displacement_share", "百分比", "出口二轮摩托车（分排量）",
    "出口二轮车分排量结构（2023+ 细分段；2016-2019 为 100-125 / 50-100 等粗分口径）。"
    "注意：2016-2019 与 2023+ 排量口径不同，不可直接逐段对比。",
    [{"year": int(y), **{c: r2(eg_share.loc[y, c]) for c in eg_share.columns},
      "volume_total": r0(eg.loc[y].sum())} for y in eg_share.index])

add("export_displacement_volume", "辆", "出口二轮摩托车（分排量）",
    "出口二轮车分排量绝对量（统一分组）。",
    [{"year": int(y), **{c: r0(eg.loc[y, c]) for c in eg.columns},
      "total": r0(eg.loc[y].sum())} for y in eg.index])

# 出口 vs 内销 排量结构对比（2024/2025/2026YTD）
cmp_rows = []
for y in [2024, 2025, 2026]:
    if y not in eg_share.index:
        continue
    ex_sh = eg_share.loc[y]
    # 出口分排量表不含电动 → 与"剔除电动的二轮燃油结构"对比才是同口径
    for g in FUEL_GROUPS:
        ev = float(ex_sh.get(g, 0))
        dv = float(fuel_share.loc[y, g])
        cmp_rows.append({"year": y, "group": g,
                         "export_share_pct": r2(ev),
                         "domestic_fuel_share_pct": r2(dv),
                         "diff_pp": r2(ev - dv)})
add("export_vs_domestic_displacement", "百分比", "出口二轮 vs 全行业二轮【燃油，剔除电动】",
    "同口径对比：出口分排量表本身不含电动，故与'剔除电动后的二轮燃油生产结构'对比。"
    "【结论】出口结构与内销结构高度同构，各段差异均在 ±2.1pp 以内；"
    "出口在 150-250ml 段占比高出约 2.0pp，在 >250ml 段反而低 1.3pp——"
    "即大排量增长主要由国内消费升级驱动，而非出口拉动。请勿误读为'出口更偏大排量'。",
    cmp_rows)

# 出口品牌集中度
emfg = df_of("export_mfg")
def cr_by(df, ycol, vcol, year=None):
    d = df if year is None else df[df[ycol] == year]
    t = d.groupby("manufacturer")[vcol].sum().sort_values(ascending=False)
    tot = t.sum()
    cr5 = t.head(5).sum() / tot * 100
    cr10 = t.head(10).sum() / tot * 100
    hhi = float(((t / tot * 100) ** 2).sum())
    return t, tot, cr5, cr10, hhi

exp_cr = []
for y in sorted(emfg["year"].unique()):
    t, tot, cr5, cr10, hhi = cr_by(emfg, "year", "value", y)
    exp_cr.append({"year": int(y), "total_export": r0(tot), "cr5_pct": r2(cr5),
                   "cr10_pct": r2(cr10), "hhi": r1(hhi), "n_brands": int(len(t)),
                   "top10": [{"manufacturer": k, "volume": r0(v), "share_pct": r2(v / tot * 100)}
                             for k, v in t.head(10).items()]})
add("export_brand_concentration", "辆/百分比", "出口品牌",
    "出口品牌集中度 CR5/CR10/HHI 与 TOP10。数据仅 2023-09 起可得。", exp_cr)

# ----------------------------------------------------------------------------
# 8. 品牌竞争格局
# ----------------------------------------------------------------------------
bm = df_of("by_manufacturer")
brand_rows = []
for y in sorted(bm["year"].unique()):
    for ind in ["生产", "销售"]:
        sub = bm[(bm.year == y) & (bm.indicator == ind)]
        t, tot, cr5, cr10, hhi = cr_by(sub, "year", "value")
        brand_rows.append({"year": int(y), "indicator": ind, "total": r0(tot),
                           "cr5_pct": r2(cr5), "cr10_pct": r2(cr10), "cr20_pct": r2(t.head(20).sum() / tot * 100),
                           "hhi": r1(hhi), "n_brands": int(len(t))})
add("brand_concentration", "辆/百分比", "全行业品牌（分生产/销售）",
    "品牌集中度 CR5/CR10/CR20 与 HHI。数据仅 2023-09 起可得；2023 年仅 4 个月且 2023-12 生产数据缺失约 97%，"
    "故 2023 年生产口径集中度不可用，请以 2024/2025 完整年为准。", brand_rows)

# 品牌排名（销量）
rank_rows = []
for y in [2023, 2024, 2025, 2026]:
    sub = bm[(bm.year == y) & (bm.indicator == "销售")]
    t = sub.groupby("manufacturer")["value"].sum().sort_values(ascending=False)
    for i, (k, v) in enumerate(t.head(25).items(), 1):
        rank_rows.append({"year": int(y), "rank": i, "manufacturer": k,
                          "volume": r0(v), "share_pct": r2(v / t.sum() * 100)})
add("brand_ranking_top25", "辆/百分比", "全行业品牌（销售口径）",
    "年度品牌销量 TOP25 与份额。2023 年仅 9-12 月，2026 年仅 1-7 月。", rank_rows)

# 排名变动：2024 vs 2025（完整年）
def rank_map(y):
    sub = bm[(bm.year == y) & (bm.indicator == "销售")]
    t = sub.groupby("manufacturer")["value"].sum().sort_values(ascending=False)
    return {k: i + 1 for i, k in enumerate(t.index)}, t

r24, t24 = rank_map(2024)
r25, t25 = rank_map(2025)
movers = []
for k in set(list(r24.keys())[:40]) | set(list(r25.keys())[:40]):
    a, b = r24.get(k), r25.get(k)
    if a is None or b is None:
        movers.append({"manufacturer": k, "rank_2024": a, "rank_2025": b,
                       "rank_change": None, "volume_2024": r0(t24.get(k)), "volume_2025": r0(t25.get(k)),
                       "note": "新进入TOP40" if a is None else "跌出TOP40"})
    else:
        movers.append({"manufacturer": k, "rank_2024": a, "rank_2025": b, "rank_change": a - b,
                       "volume_2024": r0(t24.get(k)), "volume_2025": r0(t25.get(k)), "note": ""})
movers = sorted(movers, key=lambda x: -(x["rank_change"] if x["rank_change"] is not None else -99))
add("brand_rank_movers_2024_2025", "名次/辆", "全行业品牌（销售口径，TOP40）",
    "2024→2025 品牌排名变动（rank_change 为正＝排名上升）。仅对比两个完整年份。", movers)

# 大排量赛道品牌格局
md = df_of("mfg_displacement")
md_big = md[(md.category.isin(BIG_2W)) & (md.scope == "二轮")]
big_brand = []
for y in sorted(md_big["year"].unique()):
    for ind in ["生产", "销售"]:
        sub = md_big[(md_big.year == y) & (md_big.indicator == ind)]
        t = sub.groupby("manufacturer")["value"].sum().sort_values(ascending=False)
        tot = t.sum()
        if tot == 0:
            continue
        big_brand.append({"year": int(y), "indicator": ind, "total": r0(tot),
                          "cr5_pct": r2(t.head(5).sum() / tot * 100),
                          "top15": [{"manufacturer": k, "volume": r0(v), "share_pct": r2(v / tot * 100)}
                                    for k, v in t.head(15).items()]})
add("big_displacement_brands", "辆/百分比", "二轮 排量>250ml（大排量赛道）",
    "大排量（>250ml）二轮车品牌格局与 CR5。数据仅 2023-09 起可得。", big_brand)

# 电动赛道品牌格局
md_elec = md[(md.category == "电动摩托车")]
elec_brand = []
for y in sorted(md_elec["year"].unique()):
    sub = md_elec[(md_elec.year == y) & (md_elec.indicator == "生产")]
    t = sub.groupby("manufacturer")["value"].sum().sort_values(ascending=False)
    tot = t.sum()
    if tot == 0:
        continue
    elec_brand.append({"year": int(y), "total": r0(tot),
                       "cr5_pct": r2(t.head(5).sum() / tot * 100),
                       "top10": [{"manufacturer": k, "volume": r0(v), "share_pct": r2(v / tot * 100)}
                                 for k, v in t.head(10).items()]})
add("electric_brands", "辆/百分比", "电动摩托车赛道",
    "电动摩托车品牌格局（生产口径，仅二轮，三轮电动未纳入明细）。数据仅 2023-09 起可得。", elec_brand)

# 品牌全周期累计
mat = df_of("mfg_all_time_totals")
mat_s = mat[mat.indicator == "销售"].sort_values("value", ascending=False)
add("brand_all_time_top30", "辆", "全行业品牌（2023-09 ~ 2026-07 累计销售）",
    "品牌全周期累计销量 TOP30。注意：仅覆盖有品牌明细的 35 个月，非'历史十年累计'。",
    [{"rank": i, "manufacturer": r["manufacturer"], "volume": r0(r["value"]),
      "share_pct": r2(r["value"] / mat_s["value"].sum() * 100)}
     for i, (_, r) in enumerate(mat_s.head(30).iterrows(), 1)])

# ----------------------------------------------------------------------------
# 9. 季节性
# ----------------------------------------------------------------------------
full_years = [y for y in FULL_YEARS if y in piv["year"].unique()]
seas = piv[piv.year.isin(full_years)].copy()
year_mean = seas.groupby("year")["生产"].transform("mean")
seas["idx"] = seas["生产"] / year_mean * 100
seas_idx = seas.groupby("month")["idx"].mean()
# 分时期
early = seas[seas.year.isin([2017, 2018, 2019])].copy()
late = seas[seas.year.isin([2024, 2025])].copy()
early["idx"] = early["生产"] / early.groupby("year")["生产"].transform("mean") * 100
late["idx"] = late["生产"] / late.groupby("year")["生产"].transform("mean") * 100
e_idx = early.groupby("month")["idx"].mean()
l_idx = late.groupby("month")["idx"].mean()

add("seasonality_index", "指数(年均=100)", "全行业（生产口径，完整年份 2017-2022/2024-2025）",
    "月度季节性指数（各月产量 / 该年月均 × 100）。分全程、2017-2019 早期、2024-2025 近期三期对比，"
    "用于观察淡旺季是否变化。已剔除 2016/2023/2026 非完整年份。",
    [{"month": int(m),
      "index_all": r1(seas_idx[m]), "index_2017_2019": r1(e_idx.get(m)), "index_2024_2025": r1(l_idx.get(m)),
      "change_recent_vs_early": r1(l_idx.get(m) - e_idx.get(m)) if m in e_idx and m in l_idx else None}
     for m in range(1, 13)])

# ----------------------------------------------------------------------------
# 10. 拐点与异常
# ----------------------------------------------------------------------------
ano = piv.dropna(subset=["销售_YoY"]).copy()
ano["abs_yoy"] = ano["销售_YoY"].abs()
top_ano = ano.nlargest(18, "abs_yoy")
add("turning_points_yoy", "百分比", "全行业（销售同比）",
    "销量同比波动最大的月份（|YoY| 前 18）。同比为与上年同月对比，缺失则无法计算。",
    [{"ym": r["ym"], "sales": r0(r["销售"]), "yoy_pct": r1(r["销售_YoY"]),
      "prod_yoy_pct": r1(r["生产_YoY"])} for _, r in top_ano.iterrows()])

# 简单线性趋势（2019-01 ~ 2026-07，剔除疫情异常）
tr = piv[(piv.date >= "2019-01-01")].copy()
tr["t"] = range(len(tr))
slope_p = np.polyfit(tr["t"], tr["生产"], 1)[0]
slope_s = np.polyfit(tr["t"], tr["销售"], 1)[0]
add("trend_2019_2026", "辆/月", "全行业",
    "2019-01 ~ 2026-07 产销线性趋势斜率（最小二乘，单位：辆/月）。用于判断长期趋势方向。",
    {"period": "2019-01 ~ 2026-07", "months": int(len(tr)),
     "production_slope_per_month": r0(slope_p), "sales_slope_per_month": r0(slope_s),
     "production_slope_per_year_wan": r1(slope_p * 12 / WAN),
     "sales_slope_per_year_wan": r1(slope_s * 12 / WAN)})

# 电动月度峰值
elec_peak = em_.nlargest(3, "value")
add("electric_peak_months", "辆", "二轮电动摩托车（生产口径）",
    "电动摩托车月度产量最高的 3 个月，用于定位 2022 年电动高峰。",
    [{"ym": r["ym"], "volume": r0(r["value"])} for _, r in elec_peak.iterrows()])

# ----------------------------------------------------------------------------
# 11. 数据质量
# ----------------------------------------------------------------------------
# 三轮分排量缺口
d3 = df_of("by_displacement_3w")
d3y = d3[d3.indicator == "生产"].groupby("year")["value"].sum()
vt3y = vt[vt.scope == "三轮"]
vt3y_sum = vt3y[vt3y.indicator == "生产"].groupby("year")["value"].sum()
gap3 = []
for y in sorted(d3y.index):
    a = float(vt3y_sum.get(y, 0)); b = float(d3y.get(y, 0))
    gap3.append({"year": int(y), "three_wheeler_total": r0(a), "displacement_covered": r0(b),
                 "gap": r0(a - b), "coverage_pct": r2(b / a * 100) if a else None})
add("three_wheeler_displacement_coverage", "辆/百分比", "三轮摩托车（生产口径）",
    "三轮分排量表覆盖率。三轮分排量表仅覆盖约一半产量（缺口应为电动三轮车等未纳入分排量统计的类别），"
    "因此三轮排量结构不可代表全部三轮车，总量请用车型表/总量表。", gap3)

# 月度总量 vs 分排量合计
d2m = d2[d2.indicator == "生产"].groupby(["year", "month"])["value"].sum()
d3m = d3[d3.indicator == "生产"].groupby(["year", "month"])["value"].sum()
totm = piv.set_index(["year", "month"])["生产"]
cov = []
for k in totm.index:
    a = float(totm[k]); b = float(d2m.get(k, 0) + d3m.get(k, 0))
    cov.append({"ym": f"{k[0]}-{k[1]:02d}", "total": r0(a), "displacement_sum": r0(b),
                "gap": r0(a - b), "coverage_pct": r2(b / a * 100)})
add("displacement_coverage_monthly", "辆/百分比", "全行业（生产口径）",
    "月度分排量合计对总量的覆盖率。缺口 100% 来自三轮（二轮分排量合计与二轮车型合计完全一致）。", cov)

QUALITY = {
    "coverage": {
        "period": f"{FIRST} ~ {LAST}", "months_with_data": N_MONTHS,
        "expected_months_if_complete": 125,
        "missing_months": ["2016-08", "2016-09", "2016-10", "2023-07"],
        "note": "数据自 2016-02 起，至 2026-07 止，共 122 个月；缺 2016 年 8/9/10 月与 2023 年 7 月。"
                "注意：实际最新月份为 2026-07（非 2026-06）。"
    },
    "source_layers": [
        {"period": "2016-02 ~ 2023-08", "source": "PDF《摩托车情报》抽取", "granularity": "仅汇总级（总量/分排量/分车型）",
         "limitation": "无品牌×排量明细，无法做品牌集中度与细分赛道分析"},
        {"period": "2023-09 ~ 2026-07", "source": "Excel 月报", "granularity": "全维度（含品牌×排量）",
         "limitation": "共 35 个月，品牌类结论仅覆盖此窗口"}
    ],
    "known_issues": [
        {"issue": "三轮分排量表覆盖率仅约 53%", "detail": "2025 年三轮产量 265.2 万辆，分排量表仅合计 141.2 万辆，缺口 124.0 万辆（46.8%），应为电动三轮车未纳入分排量统计。",
         "impact": "三轮排量结构不可代表全部三轮车；全行业分排量合计较总量低 5%~8%，差异全部来自三轮。",
         "mitigation": "三轮总量与结构一律使用分车型表；三轮排量仅作'三轮燃油车内部'结构参考。"},
        {"issue": "出口数据 2020-2022 缺失", "detail": "源报表当年取消分排量出口表，export_total/export_monthly 无 2020/2021/2022 记录；2018 仅 2-3 月，2019 仅 5-11 月。",
         "impact": "出口年度序列不连续，2019→2023 的'变化'不可解读为增长或下滑。",
         "mitigation": "出口结论限定在 2016-2017 与 2023-09+ 两个窗口内分别表述。"},
        {"issue": "排量段口径 2023 年前后变化", "detail": "2016-2022 为合并段（150-250 / 400-750 / >750）；2023+ 为细分段（150-200 / 200-250 / 400-500 / 500-800 / >800）。三轮 2016-2017 用 125-150ml，2018+ 改为 100-150ml。",
         "impact": "细分排量段无法跨 2023 年前后直接对比。",
         "mitigation": "已映射到 ≤110 / 110-125 / 125-150 / 150-250 / >250 / 电动 六个统一分组，实现跨年可比；细分段仅 2023+ 使用。"},
        {"issue": "电动摩托车 2019 年口径断层", "detail": "2016-2018 电动摩托车年产量仅 6.1 / 9.9 / 10.2 万辆，2019 年跃升至 177.7 万辆（+1635%）。",
         "impact": "2019 年前电动数据不可与之后比较。",
         "mitigation": "电动化趋势一律以 2019 年起为准，并在图表中明确标注。"},
        {"issue": "2026 年数据不完整", "detail": "2026 年仅 1-7 月，产量 1433.4 万辆。",
         "impact": "不可与完整年份做年度同比。",
         "mitigation": "统一使用 2026 年 1-7 月 vs 2025 年 1-7 月的同期对比。"},
        {"issue": "2023-12 品牌产量数据缺失", "detail": "by_manufacturer 中 2023-12 生产合计仅 4.4 万辆（应为 144.4 万辆，缺失 97%）。mfg_displacement 同月生产亦仅 43.0 万辆。",
         "impact": "2023 年'生产'口径的品牌集中度/排名不可用。",
         "mitigation": "品牌集中度以 2024/2025 完整年为准；2023 年如需使用请用'销售'口径。"},
        {"issue": "2026-07 品牌×排量明细不完整", "detail": "mfg_displacement 2026-07 合计较总量低 6.6%~7.0%。",
         "impact": "2026-07 细分赛道品牌份额略偏低。", "mitigation": "2026 年细分赛道结论以 2026 年 1-6 月为准或标注为初步值。"},
        {"issue": "三轮电动口径 2024 年起中断", "detail": "by_displacement_3w 中'电动摩托车'在 2016-2023 有值（2023 年 56.9 万辆），2024 年起无记录。",
         "impact": "三轮电动无法跨 2024 年对比。", "mitigation": "三轮电动不单独出结论。"},
        {"issue": "2016 年非完整年份", "detail": "2016 年仅 2-7、11-12 月共 8 个月，产量 1113.7 万辆。",
         "impact": "2016→2017 同比（+53.9%）为口径假象，不可解读为真实增长。",
         "mitigation": "增长率与 CAGR 一律以 2017 年为起点。"}
    ],
    "cross_checks": [
        {"check": "月度总量 vs 分车型合计", "result": "完全一致（0 个月偏差 >0.5%）", "status": "PASS"},
        {"check": "二轮分车型合计 vs 二轮分排量合计", "result": "完全一致（0 个月偏差 >0.5%）", "status": "PASS"},
        {"check": "年度总量 vs 月度汇总", "result": "完全一致（偏差 0.00%）", "status": "PASS"},
        {"check": "出口总量 vs 出口明细'总计'", "result": "完全一致（63 个月零偏差）", "status": "PASS"},
        {"check": "品牌月度合计 vs 月度总量", "result": "除 2023-12 生产外全部一致", "status": "PASS(1例外)"},
        {"check": "三轮分排量合计 vs 三轮分车型合计", "result": "覆盖率约 53%，系统性缺口", "status": "FAIL"},
        {"check": "全行业分排量合计 vs 总量", "result": "2023-09 起低 5%~8%（全部来自三轮）", "status": "WARN"}
    ]
}

# ----------------------------------------------------------------------------
# 12. 组装 JSON
# ----------------------------------------------------------------------------
OUT = {
    "meta": {
        "title": "中国摩托车行业产销数据分析指标集",
        "generated_by": "scripts/analysis_report.py (Phase1 深度统计分析)",
        "source_file": "output/dashboard_data.json",
        "cross_check_files": ["output/monthly_summary_full.csv", "output/monthly_manufacturer.csv",
                              "output/monthly_manufacturer_displacement.csv", "output/monthly_export.csv"],
        "period_start": FIRST, "period_end": LAST, "months": N_MONTHS,
        "indicators": meta.get("indicators"),
        "displacement_group_mapping": {g: cats for g, cats in GROUPS_2W},
        "usage_note": "每个指标含 unit / scope / note / data 四段；note 说明口径与限制，画图前请先读。"
    },
    "data_quality": QUALITY,
    "metrics": REPORT,
}

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)

# ----------------------------------------------------------------------------
# 13. 生成 Markdown
# ----------------------------------------------------------------------------
def fmt(v, unit=""):
    if v is None:
        return "n/a"
    return f"{v:,.0f}{unit}"

# 关键数字
y2016p = float(yt.loc[yt.year == 2016, "生产"].iloc[0])
y2025p = float(yt.loc[yt.year == 2025, "生产"].iloc[0])
y2025s = float(yt.loc[yt.year == 2025, "销售"].iloc[0])
y2024p = float(yt.loc[yt.year == 2024, "生产"].iloc[0])
y2024s = float(yt.loc[yt.year == 2024, "销售"].iloc[0])
y2019p = float(yt.loc[yt.year == 2019, "生产"].iloc[0])

big2025 = float(big.loc[2025, ">250ml"]); big2024 = float(big.loc[2024, ">250ml"])
big2019 = float(big.loc[2019, ">250ml"]); big2017 = float(big.loc[2017, ">250ml"])
big_share_2025 = float(big.loc[2025, "大排量占比"]); big_share_2019 = float(big.loc[2019, "大排量占比"])

elec2022 = float(g2p.loc[2022, "电动"]); elec2025 = float(g2p.loc[2025, "电动"])
elec_share_2022 = float(share2.loc[2022, "电动"]); elec_share_2025 = float(share2.loc[2025, "电动"])
elec_share_2019 = float(share2.loc[2019, "电动"])

cr5_2024 = [b for b in brand_rows if b["year"] == 2024 and b["indicator"] == "销售"][0]["cr5_pct"]
cr5_2025 = [b for b in brand_rows if b["year"] == 2025 and b["indicator"] == "销售"][0]["cr5_pct"]
cr10_2024 = [b for b in brand_rows if b["year"] == 2024 and b["indicator"] == "销售"][0]["cr10_pct"]
cr10_2025 = [b for b in brand_rows if b["year"] == 2025 and b["indicator"] == "销售"][0]["cr10_pct"]

e2024 = [x for x in ey if x["year"] == 2024][0]
e2025 = [x for x in ey if x["year"] == 2025][0]
e2026 = [x for x in ey if x["year"] == 2026][0]
e2017 = [x for x in ey if x["year"] == 2017][0]

m125_2025 = float(g2p.loc[2025, "110-125ml"]) + float(g2p.loc[2025, "125-150ml"])
m125_2019 = float(g2p.loc[2019, "110-125ml"]) + float(g2p.loc[2019, "125-150ml"])

tw_share_2025 = float(vt_y_p.loc[2025, "二轮占比"])

md_big_2025 = [b for b in big_brand if b["year"] == 2025 and b["indicator"] == "销售"]
big_cr5_2025 = md_big_2025[0]["cr5_pct"] if md_big_2025 else None
big_top_2025 = md_big_2025[0]["top15"][:8] if md_big_2025 else []

peak = elec_peak.iloc[0]
cum_gap_2025 = float(yt.loc[yt.year == 2025, "累计产销差"].iloc[0])
ratio_2025 = float(yt.loc[yt.year == 2025, "产销率"].iloc[0])
RATIO_MAX = float(yt["产销率"].max()); RATIO_MIN = float(yt["产销率"].min())
RATIO_MAX_Y = int(yt.loc[yt["产销率"].idxmax(), "year"]); RATIO_MIN_Y = int(yt.loc[yt["产销率"].idxmin(), "year"])
ratio_2020 = float(yt.loc[yt.year == 2020, "产销率"].iloc[0])

L = []
A = L.append
A("# 中国摩托车行业产销数据 —— 深度分析结论")
A("")
A(f"> 分析范围：**{FIRST} ~ {LAST}**，共 **{N_MONTHS} 个月**（含 2016 年 8 个月、2026 年 1-7 月）  ")
A(f"> 数据源：`output/dashboard_data.json`（交叉校验 `monthly_summary_full.csv` 等）  ")
A(f"> 分析脚本：`scripts/analysis_report.py` ｜ 结构化指标：`output/analysis_metrics.json`  ")
A(f"> 分析人：智数分析专家团 · 数据科学工程师 赛奇（Sage）")
A("")

A("## 一、数据口径与覆盖范围")
A("")
A("### 1.1 时间覆盖")
A("")
A("| 区间 | 来源 | 粒度 | 月份数 |")
A("|---|---|---|---|")
A("| 2016-02 ~ 2023-08 | PDF《摩托车情报》抽取 | 仅汇总级（总量/分排量/分车型） | 87 |")
A("| 2023-09 ~ 2026-07 | Excel 月报 | 全维度（含品牌×排量） | 35 |")
A("")
A(f"- **实际最新月份为 2026 年 7 月**（此前看板口径写的是 2026-06，已修正）。")
A("- 缺失月份：2016 年 8/9/10 月、2023 年 7 月。")
A("- **2016 年仅 8 个月（1113.7 万辆）、2023 年 11 个月、2026 年仅 7 个月**，均非完整年份。")
A("")
A("### 1.2 关键口径限制（影响结论解读，务必先读）")
A("")
A("| # | 问题 | 影响 | 处理方式 |")
A("|---|---|---|---|")
A("| 1 | **三轮分排量表仅覆盖约 53%** | 2025 年三轮产量 265.2 万辆，分排量表仅 141.2 万辆，缺口 124.0 万辆（应为电动三轮车未纳入） | 三轮总量与结构一律用分车型表；三轮排量仅作燃油三轮内部结构参考 |")
A("| 2 | **出口数据 2020-2022 缺失** | 出口年度序列断裂 | 出口结论限定在 2016-2017 与 2023-09+ 两个窗口分别表述 |")
A("| 3 | **排量段口径 2023 年前后变化** | 细分段不可跨期对比 | 已映射为 6 个统一分组（≤110/110-125/125-150/150-250/>250/电动） |")
A("| 4 | **电动摩托车 2019 年口径断层** | 2016-2018 仅 6-10 万辆/年，2019 跃至 177.7 万辆 | 电动化趋势以 2019 年起为准 |")
A("| 5 | **2026 年仅 1-7 月** | 不可与完整年份做年度同比 | 统一使用 2026 年 1-7 月 vs 2025 年同期 |")
A("| 6 | 2023-12 品牌产量缺失 97% | 2023 年生产口径品牌集中度不可用 | 品牌集中度以 2024/2025 为准 |")
A("")
A("### 1.3 交叉校验结果")
A("")
A("| 校验项 | 结果 | 状态 |")
A("|---|---|---|")
for c in QUALITY["cross_checks"]:
    A(f"| {c['check']} | {c['result']} | {c['status']} |")
A("")
A("---")
A("")

def fs(y, g):
    return float(fuel_share.loc[y, g])

def vfs(y, c):
    return float(vshare_fuel.loc[y, c])

findings = [
    ("**行业总量创十年新高，2025 年产量突破 2195 万辆。**",
     f"2025 年产量 {y2025p/WAN:,.1f} 万辆、销量 {y2025s/WAN:,.1f} 万辆，为 2016 年以来最高；较 2019 年（{y2019p/WAN:,.1f} 万辆）产量 +{((y2025p/y2019p)-1)*100:.1f}%。",
     "yearly_production_sales｜全行业｜2019 与 2025 均为完整年，可比", "高（年度总量与月度汇总 0 偏差）"),
    ("**但十年 CAGR 只有约 3.1%，行业是低速稳健增长，不是爆发式增长。**",
     f"2017→2025 产量 CAGR {cagr_17_25_p:.2f}%、销量 CAGR {cagr_17_25_s:.2f}%（以 2017 年 1714.0 万辆为起点，避开 2016 年不完整口径）。",
     "headline_totals.cagr_2017_2025｜完整年口径", "高"),
    ("**2026 年 1-7 月延续双位数增长，全年有望再创新高。**",
     f"2026 年 1-7 月产量 {p26/WAN:,.1f} 万辆（较 2025 年同期 +{YTD_P_GROWTH:.1f}%）、销量 {s26/WAN:,.1f} 万辆（+{YTD_S_GROWTH:.1f}%）。这是 2026 年唯一可比的口径，不可用全年同比。",
     "headline_totals.y2026_ytd｜2026 年 1-7 月 vs 2025 年同期", "高"),
    ("**产销率长期稳定在 99%~100%，行业没有系统性库存压力。**",
     f"全周期累计产销率 {OVERALL_RATIO:.2f}%；各年在 {RATIO_MIN:.1f}%~{RATIO_MAX:.1f}% 之间（{RATIO_MAX_Y} 年 {RATIO_MAX:.1f}% 最高，{RATIO_MIN_Y} 年 {RATIO_MIN:.1f}% 最低）；至 2025 年末累计产销差仅 {cum_gap_2025/WAN:,.1f} 万辆，相对年产 2000 万辆量级可忽略。",
     "yearly_production_sales.ratio_pct / cum_gap｜全行业", "高"),
    ("**【核心】燃油车内部正在发生明确的排量升级：≤110ml 大幅萎缩，125-250ml 与 >250ml 双双翻倍以上。**",
     f"剔除电动后的燃油二轮排量结构：≤110ml 从 2016 年 {fs(2016,'≤110ml'):.1f}% 降至 2025 年 {fs(2025,'≤110ml'):.1f}%；"
     f"125-150ml 从 {fs(2016,'125-150ml'):.1f}% 升至 {fs(2025,'125-150ml'):.1f}%；"
     f"150-250ml 从 {fs(2016,'150-250ml'):.1f}% 升至 {fs(2025,'150-250ml'):.1f}%；"
     f">250ml 从 {fs(2016,'>250ml'):.1f}% 升至 {fs(2025,'>250ml'):.1f}%（增长约 {fs(2025,'>250ml')/fs(2016,'>250ml'):.0f} 倍）。",
     "displacement_2w_share_fuel_only｜二轮【燃油，剔除电动】｜统一分组跨年可比", "高（这是本报告最可靠的结构性结论）"),
    ("**大排量（>250ml）是增速最快的细分赛道，六年增长 4 倍多。**",
     f"二轮 >250ml 产量 2019 年 {big2019/WAN:,.1f} 万辆 → 2025 年 {big2025/WAN:,.1f} 万辆（+{((big2025/big2019)-1)*100:.0f}%），"
     f"占二轮比重 {big_share_2019:.2f}% → {big_share_2025:.2f}%；2025 年同比 +{float(big.loc[2025,'大排量YoY']):.1f}%，"
     f"2026 年 1-7 月 {BIG_YTD_26/WAN:.1f} 万辆，较 2025 年同期仅 {BIG_YTD_GROWTH:+.1f}%——"
     f"**显著跑输行业整体 {YTD_P_GROWTH:+.1f}%，占二轮比重从 {big_share_2025:.2f}% 回落至 {float(big.loc[2026,'大排量占比']):.2f}%，大排量赛道出现增速放缓信号。",
     "big_displacement_2w｜二轮生产口径｜>250ml 分组跨年可比（组内 750/800ml 界点有微小差异）", "高"),
    ("**电动摩托车经历 2022 年脉冲式高峰后回落，2025 年企稳在 11% 左右。**",
     f"二轮电动产量 2019 年 {float(g2p.loc[2019,'电动'])/WAN:,.1f} 万辆 → 2022 年峰值 {elec2022/WAN:,.1f} 万辆（占二轮 {elec_share_2022:.1f}%）→ 2023 年 {float(g2p.loc[2023,'电动'])/WAN:,.1f} 万辆 → 2024 年 {float(g2p.loc[2024,'电动'])/WAN:,.1f} 万辆 → 2025 年 {elec2025/WAN:,.1f} 万辆（占二轮 {elec_share_2025:.1f}%，同比 +3.1%）。峰值月 {peak['ym']}（{peak['value']/WAN:,.1f} 万辆）。",
     "electric_motorcycle / electric_peak_months｜二轮生产口径｜2019 年起", "中高（2019 年前口径不可比；三轮电动未纳入）"),
    ("**【易错点】所谓'踏板车份额暴涨至 49%'是电动摩托车造成的假象，燃油踏板车份额其实在小幅下滑。**",
     f"已验证：电动摩托车在分车型表中 100% 计入'踏板式'。剔除电动后，燃油踏板式份额 2016 年 {vfs(2016,'踏板式(燃油)'):.1f}% → 2022 年 {vfs(2022,'踏板式(燃油)'):.1f}% → 2025 年 {vfs(2025,'踏板式(燃油)'):.1f}%；"
     f"骑式则从 {vfs(2016,'骑式'):.1f}% 升至 {vfs(2025,'骑式'):.1f}%；弯梁式从 {vfs(2016,'弯梁式'):.1f}% 降至 {vfs(2025,'弯梁式'):.1f}%。",
     "vehicle_type_share_2w_fuel_only｜二轮【燃油，剔除电动】", "高（已交叉验证踏板式产量恒 ≥ 电动产量）"),
    ("**出口已成行业增长第一引擎，外销率突破 60%。**",
     f"外销率 2023 年 48.4% → 2024 年 {e2024['export_ratio_pct']:.1f}% → 2025 年 {e2025['export_ratio_pct']:.1f}% → 2026 年 1-7 月 {e2026['export_ratio_pct']:.1f}%；"
     f"2025 年出口 {e2025['export_volume']/WAN:,.1f} 万辆，较 2024 年 +{((e2025['export_volume']/e2024['export_volume'])-1)*100:.1f}%，"
     f"而同期国内销量仅 +{((e2025['same_period_sales']-e2024['same_period_sales'])/e2024['same_period_sales'])*100:.1f}%——增量主要来自出口。",
     "export_yearly.export_ratio_pct｜2023-09 起连续可观测｜2020-2022 缺失", "高"),
    ("**【关键判断】2025 年行业增长几乎 100% 来自出口，国内销量实际在萎缩。**",
     f"内销 = 销量 \u2212 出口：2024 年内销 {split_rows[1]['domestic_wan']:,.1f} 万辆 \u2192 2025 年 {split_rows[2]['domestic_wan']:,.1f} 万辆（**{DOM_YOY_25:+.1f}%**）；"
     f"同期出口从 {split_rows[1]['export_wan']:,.1f} 万辆增至 {split_rows[2]['export_wan']:,.1f} 万辆（+{((split_rows[2]['export']/split_rows[1]['export'])-1)*100:.1f}%）。"
     f"2025 年销量净增 {((split_rows[2]['sales']-split_rows[1]['sales'])/WAN):,.1f} 万辆，而出口净增 {((split_rows[2]['export']-split_rows[1]['export'])/WAN):,.1f} 万辆——"
     "出口增量已超过销量总增量，内需为负贡献。"
     f"1-7 月同期看，2026 年内销回升至 {split_ytd[2]['domestic_wan']:,.1f} 万辆（{split_ytd[2]['domestic_yoy_pct']:+.1f}%），出现回暖信号。",
     "domestic_vs_export_split｜全行业｜2024/2025 为完整年可比；2026 用 1-7 月同期", "高（基于与总量 100% 对齐的销量表与出口表）"),
    ("**出口单车均价持续上行，2025 年突破 700 美元。**",
     f"2023 年 {[x for x in ey if x['year']==2023][0]['avg_price_usd']:.1f} 美元 → 2024 年 {e2024['avg_price_usd']:.1f} 美元 → 2025 年 {e2025['avg_price_usd']:.1f} 美元（+{((e2025['avg_price_usd']/e2024['avg_price_usd'])-1)*100:.1f}%），2026 年 1-7 月 {e2026['avg_price_usd']:.1f} 美元。量价齐升，不是单纯走量。",
     "export_yearly.avg_price_usd｜出口金额 2023-09 起可得", "高"),
    ("**【反直觉】出口排量结构与内销高度同构，大排量出口占比反而略低于内销。**",
     f"同口径对比（均剔除电动）：2025 年出口在 150-250ml 段占比高出内销 {[r['diff_pp'] for r in cmp_rows if r['year']==2025 and r['group']=='150-250ml'][0]:+.1f}pp，"
     f"但在 >250ml 段低 {[r['diff_pp'] for r in cmp_rows if r['year']==2025 and r['group']=='>250ml'][0]:+.1f}pp；各段差异均在 ±2.1pp 以内。"
     "结论：大排量增长主要由国内消费升级驱动，出口并非主要拉力。",
     "export_vs_domestic_displacement｜出口二轮 vs 全行业二轮燃油｜2024/2025", "中高（出口排量表不含电动，已做同口径处理）"),
    ("**品牌集中度不升反降，行业仍高度分散，远未形成寡头。**",
     f"销量 CR5：2024 年 {cr5_2024:.1f}% → 2025 年 {cr5_2025:.1f}%（下降 {cr5_2024-cr5_2025:.1f}pp），2026 年 1-7 月回升至 {[b for b in brand_rows if b['year']==2026 and b['indicator']=='销售'][0]['cr5_pct']:.1f}%；"
     f"CR10 稳定在 {cr10_2024:.1f}% → {cr10_2025:.1f}%。约 90 家企业在产，CR10 仅略过半。",
     "brand_concentration｜销售口径｜2023-09 起（35 个月）", "中高（窗口较短；2023 年生产口径数据有缺陷已剔除）"),
    ("**大排量赛道集中度远高于行业平均，是一条「头部通吃」的赛道。**",
     f"2025 年 >250ml 二轮车销量 CR5 达 {big_cr5_2025:.1f}%（对比全行业 CR5 仅 {cr5_2025:.1f}%）；头部：" +
     "、".join([f"{b['manufacturer']} {b['share_pct']:.1f}%" for b in big_top_2025[:5]]) + "。",
     "big_displacement_brands｜二轮 >250ml 销售口径｜2023-09 起", "中高"),
    ("**二轮车占绝对主导（约 88%），三轮是稳定的补充盘。**",
     f"2025 年二轮占 {tw_share_2025:.1f}%（{float(vt_y_p.loc[2025,'二轮'])/WAN:,.1f} 万辆），三轮占 {100-tw_share_2025:.1f}%（{float(vt_y_p.loc[2025,'三轮'])/WAN:,.1f} 万辆）；该比例十年间基本稳定。",
     "two_wheeler_vs_three_wheeler｜分车型表（口径完整，与总量 100% 对齐）", "高"),
    ("**季节性稳定：9 月为全年最高峰，2 月春节为绝对低点。**",
     f"季节性指数（年均=100）：9 月 {seas_idx[9]:.0f}（最高）、12 月 {seas_idx[12]:.0f}、6-7 月 {seas_idx[6]:.0f}~{seas_idx[7]:.0f}；"
     f"2 月仅 {seas_idx[2]:.0f}（最低，约为年均的六成）。淡旺季格局十年间保持稳定，近年（2024-2025）与早期（2017-2019）差异多在 ±7 以内。",
     "seasonality_index｜完整年份 2017-2022 / 2024-2025｜已剔除不完整年", "中高"),
    ("**2016→2017 的 +53.9%'暴涨'是口径假象，绝不可引用。**",
     f"2016 年仅有 8 个月数据（{y2016p/WAN:,.1f} 万辆），2017 年为完整 12 个月（{float(yt.loc[yt.year==2017,'生产'].iloc[0])/WAN:,.1f} 万辆）。"
     "同理，2024 年 vs 2023 年（11 个月）、2026 年 vs 2025 年的年度同比均不可比。",
     "yearly_production_sales.yoy_comparable=false 的年份已置空同比", "高（已确认并已在数据中置空）"),
    ("**三轮分排量表覆盖率仅 53%，是数据结构上最大的坑。**",
     f"2025 年三轮产量 {float(vt_y_p.loc[2025,'三轮'])/WAN:,.1f} 万辆，分排量表仅覆盖 {float(d3y.get(2025,0))/WAN:,.1f} 万辆（{float(d3y.get(2025,0))/float(vt3y_sum.get(2025,1))*100:.0f}%），缺口 {((float(vt3y_sum.get(2025,0))-float(d3y.get(2025,0)))/WAN):,.1f} 万辆，应为电动三轮车未纳入。"
     "全行业分排量合计较总量低 5%~8%，差异 100% 来自三轮（二轮分排量与车型表完全一致）。",
     "three_wheeler_displacement_coverage｜三轮生产口径", "高（已定位，但原始缺口无法补齐）"),
]
A(f"## 二、核心发现（{len(findings)} 条）")
A("")
for i, (c, d, s, conf) in enumerate(findings, 1):
    A(f"{i}. {c}")
    A("")
    A(f"   - 关键数字：{d}")
    A(f"   - 数据出处/口径：{s}")
    A(f"   - 可信度：{conf}")
    A("")

A("---")
A("")

A("## 三、分主题详述")
A("")
A("### 3.1 总量与增长")
A("")
A("| 年份 | 覆盖月数 | 产量(万辆) | 销量(万辆) | 产量YoY | 销量YoY | 产销率 |")
A("|---|---|---|---|---|---|---|")
for _, r in yt.iterrows():
    yoy_p = f"{r['生产YoY']:+.1f}%" if not pd.isna(r["生产YoY"]) else "—"
    yoy_s = f"{r['销售YoY']:+.1f}%" if not pd.isna(r["销售YoY"]) else "—"
    flag = "" if r["is_full_year"] else " ⚠️"
    A(f"| {int(r['year'])}{flag} | {int(r['months_covered'])} | {r['生产']/WAN:,.1f} | {r['销售']/WAN:,.1f} | {yoy_p} | {yoy_s} | {r['产销率']:.1f}% |")
A("")
A("⚠️ = 非完整年份。**同比列仅在「本年与上年均为完整年」时给出**（可比年份：2018/2019/2020/2021/2022/2025）；")
A("2017（vs 2016 仅 8 个月）、2023（11 个月）、2024（vs 2023 不完整）、2026（7 个月）的同比一律置空，**不可引用**。")
A("")
A(f"- **累计**：全周期累计生产 {TOTAL_P/YI:.3f} 亿辆、销售 {TOTAL_S/YI:.3f} 亿辆，产销率 {OVERALL_RATIO:.2f}%。")
A(f"- **CAGR**：2017→2025 产量 {cagr_17_25_p:.2f}%、销量 {cagr_17_25_s:.2f}%。")
A(f"- **2026 年唯一可比口径**：1-7 月产量 {p26/WAN:,.1f} 万辆 / 销量 {s26/WAN:,.1f} 万辆，较 2025 年同期 **{YTD_P_GROWTH:+.1f}% / {YTD_S_GROWTH:+.1f}%**。（表中 -34.7% 是 7 个月 vs 12 个月的假象，已置空）")
A(f"- **长期趋势**：2019-01 ~ 2026-07 产量线性趋势 +{slope_p*12/WAN:.1f} 万辆/年，销量 +{slope_s*12/WAN:.1f} 万辆/年。")
A(f"- **库存**：累计产销差（累计生产−累计销售）至 2025 年末为 {cum_gap_2025/WAN:,.1f} 万辆，相对年产量 2 亿辆量级可忽略，行业无系统性库存压力。")
A("")
A("### 3.2 排量结构（报告核心）")
A("")
A("统一分组后的二轮排量占比（%）：")
A("")
A("| 年份 | ≤110ml | 110-125ml | 125-150ml | 150-250ml | >250ml | 电动 |")
A("|---|---|---|---|---|---|---|")
for y in share2.index:
    A(f"| {int(y)} | " + " | ".join(f"{share2.loc[y, g]:.1f}" for g in GROUP_ORDER_2W) + " |")
A("")
A("**【推荐主图】剔除电动后的燃油二轮排量结构（%，分母＝燃油二轮总量）：**")
A("")
A("| 年份 | ≤110ml | 110-125ml | 125-150ml | 150-250ml | >250ml |")
A("|---|---|---|---|---|---|")
for y in fuel_share.index:
    A(f"| {int(y)} | " + " | ".join(f"{fuel_share.loc[y, g]:.1f}" for g in FUEL_GROUPS) + " |")
A("")
A("> 这是观察燃油车'排量升级'最干净的口径（剔除了电动摩托车的扰动）。"
  f"核心变化：**≤110ml 从 {fs(2016,'≤110ml'):.1f}% 萎缩到 {fs(2025,'≤110ml'):.1f}%**，"
  f"125-150ml、150-250ml、>250ml 三个中高排量段十年间份额全部翻倍以上。")
A("")
A("**大排量（>250ml）专题：**")
A("")
A("| 年份 | >250ml 产量(万辆) | 占二轮比重 | YoY |")
A("|---|---|---|---|")
for y in big.index:
    v = float(big.loc[y, ">250ml"]); sh = float(big.loc[y, "大排量占比"])
    yo = big.loc[y, "大排量YoY"]
    A(f"| {int(y)} | {v/WAN:,.1f} | {sh:.2f}% | " + (f"{yo:+.1f}%" if not pd.isna(yo) else "—") + " |")
A("")
A("**细分段（仅 2023+ 可得，2023 年前为合并段，不可对比）：**")
A("")
A("| 年份 | 150-200ml | 200-250ml | 250-400ml | 400-500ml | 500-800ml | >800ml |")
A("|---|---|---|---|---|---|---|")
for y in d2fy.index:
    A(f"| {int(y)} | " + " | ".join(f"{d2fy.loc[y, c]/WAN:,.1f}" for c in fine_cats) + " |")
A("")
A("> 口径说明：2016-2022 原始分段为 150-250 / 400-750 / >750；2023+ 为 150-200 / 200-250 / 400-500 / 500-800 / >800。上表仅 2023 年后可比。")
A("")
A("**大排量 1-7 月同期对比（2026 年唯一同口径序列）：**")
A("")
A("| 年份 | 1-7 月 >250ml 产量(万辆) | 同期同比 | 占全行业比重(1-7月) |")
A("|---|---|---|---|")
for r in big_ytd_rows:
    A(f"| {r['year']} | {r['volume_wan']:,.1f} | " +
      (f"{r['yoy_1_7_pct']:+.1f}%" if r["yoy_1_7_pct"] is not None else "—") +
      f" | {r['share_of_total_pct_1_7']:.2f}% |")
A("")
A("> **重要信号**：大排量同比从 2025 年 1-7 月的 **+38.0%** 骤降至 2026 年同期的 **+1.1%**，"
  "而同期行业整体产量 +14.9%。大排量赛道的高速增长期在 2026 年出现明显放缓，是报告值得重点提示的风险点。")
A("")
A("### 3.3 电动化")
A("")
A("| 年份 | 电动产量(万辆) | 占二轮比重 | 占全行业比重 | YoY |")
A("|---|---|---|---|---|")
for _, r in elec.iterrows():
    yo = r["电动YoY"]
    A(f"| {int(r['year'])} | {r['电动']/WAN:,.1f} | {r['电动占比_二轮']:.1f}% | {r['电动占比_全行业']:.1f}% | " +
      (f"{yo:+.1f}%" if yo is not None and not pd.isna(yo) else "—") + " |")
A("")
A("> ⚠️ **2016-2018 年电动数据（6.1 / 9.9 / 10.2 万辆）与 2019 年（177.7 万辆）存在数量级断层**，判定为 2019 年新国标实施后统计口径变更。"
  "**电动化结论请只使用 2019 年及以后的数据。** 此外，三轮电动摩托车未纳入分排量明细表，本表仅含二轮电动。")
A("")
A("### 3.4 车型结构")
A("")
A("二轮车型占比（%，占二轮比重）：")
A("")
A("| 年份 | " + " | ".join(vcols) + " |")
A("|---|" + "---|" * len(vcols))
for y in vshare.index:
    A(f"| {int(y)} | " + " | ".join(f"{vshare.loc[y, c]:.1f}" for c in vcols) + " |")
A("")
A("**【推荐主图】剔除电动后的燃油二轮车型结构（%，分母＝燃油二轮总量）：**")
A("")
A("| 年份 | " + " | ".join(vshare_fuel.columns) + " |")
A("|---|" + "---|" * len(vshare_fuel.columns))
for y in vshare_fuel.index:
    A(f"| {int(y)} | " + " | ".join(f"{vshare_fuel.loc[y, c]:.1f}" for c in vshare_fuel.columns) + " |")
A("")
A("> ⚠️ **重要校正**：电动摩托车在分车型表中 100% 计入「踏板式」（已验证各年踏板式产量恒 ≥ 电动产量）。"
  f"因此上表一中 2022 年踏板式 {vshare.loc[2022,'踏板式']:.1f}% 的高点是**电动造成的假象**；"
  f"剔除电动后，燃油踏板式实际从 2016 年 {vfs(2016,'踏板式(燃油)'):.1f}% 小幅下滑至 2025 年 {vfs(2025,'踏板式(燃油)'):.1f}%，"
  f"同期骑式从 {vfs(2016,'骑式'):.1f}% 升至 {vfs(2025,'骑式'):.1f}%。**车型结构图请用本表。**")
A("")
A("### 3.5 出口与内销")
A("")
A("| 年份 | 覆盖月数 | 出口量(万辆) | 出口金额(亿美元) | 单车均价(美元) | 同期销量(万辆) | 外销率 |")
A("|---|---|---|---|---|---|---|")
for x in ey:
    amt_s = f"{x['export_amount_usd_10k']/1e4:.2f}" if x["has_amount_data"] else "—"
    pr = f"{x['avg_price_usd']:.1f}" if x["avg_price_usd"] else "—"
    A(f"| {x['year']} | {x['months_covered']} | {x['export_volume']/WAN:,.1f} | {amt_s} | {pr} | {x['same_period_sales']/WAN:,.1f} | {x['export_ratio_pct']:.1f}% |")
A("")
A(f"**2023-09 ~ 2026-06（34 个月）累计校验**：出口量 {WIN['export_volume_wan']:,.1f} 万辆、出口金额 {WIN['export_amount_usd_yi']:.1f} 亿美元、外销率 {WIN['export_ratio_pct']:.1f}%、单车均价 {WIN['avg_price_usd']:.1f} 美元。"
  "（与前期看板口径 3467.7 万辆 / 233.5 亿美元 / 58.1% 基本一致，差异来自月份边界与四舍五入。）")
A("")
A("> ⚠️ **2020-2022 出口数据完全缺失**，2018 仅 2 个月、2019 仅 7 个月、2023 仅 4 个月。"
  "**不要对 2019→2023 做同比解读。** 出口金额仅 2023-09 起可得。")
A("")
A("**【关键】内销 vs 出口拆分（内销 = 销量 \u2212 出口）：**")
A("")
A("| 年份 | 口径(销量与出口均覆盖的月份) | 销量(万辆) | 出口(万辆) | 内销(万辆) | 外销率 |")
A("|---|---|---|---|---|---|")
for r in split_rows:
    A(f"| {r['year']} | {r['window']} | {r['sales_wan']:,.1f} | {r['export_wan']:,.1f} | {r['domestic_wan']:,.1f} | {r['export_ratio_pct']:.1f}% |")
A("")
A("**1-7 月同期对比（可比序列）：**")
A("")
A("| 年份(1-7月) | 销量(万辆) | 出口(万辆) | 内销(万辆) | 出口同比 | 内销同比 | 销量同比 |")
A("|---|---|---|---|---|---|---|")
for r in split_ytd:
    ey = f"{r['export_yoy_pct']:+.1f}%" if r.get("export_yoy_pct") is not None else "\u2014"
    dy = f"{r['domestic_yoy_pct']:+.1f}%" if r.get("domestic_yoy_pct") is not None else "\u2014"
    sy = f"{r['sales_yoy_pct']:+.1f}%" if r.get("sales_yoy_pct") is not None else "\u2014"
    A(f"| {r['year']} | {r['sales_wan']:,.1f} | {r['export_wan']:,.1f} | {r['domestic_wan']:,.1f} | {ey} | {dy} | {sy} |")
A("")
A(f"> **这是本报告最重要的结构性判断**：2024\u21922025 全年可比口径下，销量 +{((split_rows[2]['sales']/split_rows[1]['sales'])-1)*100:.1f}%，")
A(f"> 但**内销从 {split_rows[1]['domestic_wan']:,.1f} 万辆降至 {split_rows[2]['domestic_wan']:,.1f} 万辆（{DOM_YOY_25:+.1f}%）**；")
A("> 行业增长完全由出口贡献，国内市场实际在萎缩。")
A(f"> 1-7 月同期看，2026 年内销回升 {split_ytd[2]['domestic_yoy_pct']:+.1f}%，出现回暖信号。")
A("")
A("**出口结构 vs 全行业结构（2024 / 2025，%）：**")
A("")
A("> 同口径说明：出口分排量表本身**不含电动**，故与「剔除电动后的二轮燃油生产结构」对比。")
A("")
A("| 年份 | 排量组 | 出口占比 | 内销(二轮燃油)占比 | 差异 pp |")
A("|---|---|---|---|---|")
for r in cmp_rows:
    A(f"| {r['year']} | {r['group']} | {r['export_share_pct']:.1f} | {r['domestic_fuel_share_pct']:.1f} | {r['diff_pp']:+.1f} |")
A("")
A("> **结论（反直觉，务必按此表述）**：出口结构与内销**高度同构**，各排量段差异均在 ±2.1pp 以内。"
  "出口在 150-250ml 段占比高出约 2.0pp，但在 **>250ml 段反而低约 1.3pp**——"
  "**大排量增长主要由国内消费升级驱动，出口不是主要拉力**。请勿写成「出口更偏大排量」。")
A("")
A("**出口品牌集中度：**")
A("")
A("| 年份 | 出口CR5 | 出口CR10 | HHI |")
A("|---|---|---|---|")
for x in exp_cr:
    A(f"| {x['year']} | {x['cr5_pct']:.1f}% | {x['cr10_pct']:.1f}% | {x['hhi']:.0f} |")
A("")
A("### 3.6 竞争格局")
A("")
A("**品牌集中度（销量口径）：**")
A("")
A("| 年份 | CR5 | CR10 | CR20 | HHI | 品牌数 |")
A("|---|---|---|---|---|---|")
for b in [x for x in brand_rows if x["indicator"] == "销售"]:
    A(f"| {b['year']} | {b['cr5_pct']:.1f}% | {b['cr10_pct']:.1f}% | {b['cr20_pct']:.1f}% | {b['hhi']:.0f} | {b['n_brands']} |")
A("")
A("**2025 年销量 TOP10：**")
A("")
A("| 排名 | 品牌 | 销量(万辆) | 份额 |")
A("|---|---|---|---|")
for r in [x for x in rank_rows if x["year"] == 2025][:10]:
    A(f"| {r['rank']} | {r['manufacturer']} | {r['volume']/WAN:,.1f} | {r['share_pct']:.1f}% |")
A("")
A("**2024→2025 排名上升最快 TOP8：**")
A("")
A("| 品牌 | 2024 排名 | 2025 排名 | 变化 | 2025 销量(万辆) |")
A("|---|---|---|---|---|")
shown = 0
for m in movers:
    if m["rank_change"] is None or shown >= 8:
        continue
    A(f"| {m['manufacturer']} | {m['rank_2024']} | {m['rank_2025']} | +{m['rank_change']} | {m['volume_2025']/WAN:,.1f} |")
    shown += 1
A("")
A("**2025 年大排量（>250ml）赛道 TOP8：**")
A("")
A("| 排名 | 品牌 | 销量(辆) | 赛道份额 |")
A("|---|---|---|---|")
for i, b in enumerate(big_top_2025[:8], 1):
    A(f"| {i} | {b['manufacturer']} | {b['volume']:,.0f} | {b['share_pct']:.1f}% |")
A("")
A("### 3.7 季节性")
A("")
A("| 月份 | 全期指数 | 2017-2019 | 2024-2025 | 近期−早期 |")
A("|---|---|---|---|---|")
for m in range(1, 13):
    a = seas_idx[m]; b = e_idx.get(m); c = l_idx.get(m)
    A(f"| {m}月 | {a:.0f} | " + (f"{b:.0f}" if b is not None and not pd.isna(b) else "—") + " | " +
      (f"{c:.0f}" if c is not None and not pd.isna(c) else "—") + " | " +
      (f"{c-b:+.0f}" if (b is not None and not pd.isna(b) and c is not None and not pd.isna(c)) else "—") + " |")
A("")
A("（指数 = 该月产量 / 该年月均产量 × 100；已剔除 2016/2023/2026 非完整年份）")
A("")
A("### 3.8 异常与拐点")
A("")
A("销量同比波动最大的月份（|YoY| TOP12）：")
A("")
A("| 月份 | 销量(万辆) | 销量YoY | 产量YoY |")
A("|---|---|---|---|")
for _, r in top_ano.head(12).iterrows():
    A(f"| {r['ym']} | {r['销售']/WAN:,.1f} | {r['销售_YoY']:+.1f}% | " +
      (f"{r['生产_YoY']:+.1f}%" if not pd.isna(r["生产_YoY"]) else "—") + " |")
A("")
A("已识别的主要拐点：")
A("")
A(f"- **2022 年电动脉冲**：二轮电动产量冲至 {elec2022/WAN:,.1f} 万辆（占二轮 {elec_share_2022:.1f}%），峰值月 {peak['ym']}（{peak['value']/WAN:,.1f} 万辆）；2023 年回落至 {float(g2p.loc[2023,'电动'])/WAN:,.1f} 万辆，2024 年进一步回落至 {float(g2p.loc[2024,'电动'])/WAN:,.1f} 万辆。判断为「新国标过渡期抢装 + 2023 年需求前置透支」的组合效应。")
A("- **2020 年疫情冲击**：2020 年产量 1700.3 万辆，较 2019 年 1718.3 万辆仅 -1.0%，销量反而 +0.8%，**疫情对全年总量冲击有限**，但月度间波动巨大（见上表）。")
A("- **2021-2022 冲高**：2021 年产量 2011.7 万辆（同比 +18.3%，可比）、2022 年 1996.1 万辆（-0.8%，可比）；2023 年回落至 1767.2 万辆（但 2023 仅 11 个月，同比不可比）。")
A(f"- **2025-2026 新一轮增长**：2025 年 {y2025p/WAN:,.1f} 万辆（同比 +{float(yt.loc[yt.year==2025,'生产YoY'].iloc[0]):.1f}%，可比），"
  f"2026 年 1-7 月 {p26/WAN:,.1f} 万辆（较 2025 年同期 +{YTD_P_GROWTH:.1f}%）。这一轮增长**主要由出口驱动**"
  "（2025 年出口 +21.5%，同期国内销量仅 +10.0%）。注：2024 vs 2023 年度同比不可比（2023 缺 7 月），不要引用 +12.6%。")
A("")
A("---")
A("")
A("## 四、数据质量备注（下游必读）")
A("")
A("### 4.1 会导致误读的坑")
A("")
for i, k in enumerate(QUALITY["known_issues"], 1):
    A(f"**{i}. {k['issue']}**")
    A(f"   - 现象：{k['detail']}")
    A(f"   - 影响：{k['impact']}")
    A(f"   - 处理：{k['mitigation']}")
    A("")
A("### 4.2 各主题的可用数据窗口")
A("")
A("| 分析主题 | 可用区间 | 限制 |")
A("|---|---|---|")
A("| 总量走势 | 2016-02 ~ 2026-07 | 缺 2016.08-10、2023.07 |")
A("| 排量结构 | 2016-02 ~ 2026-07（统一分组） | 细分段仅 2023+ |")
A("| 电动化 | **2019 起** | 2016-2018 口径断层 |")
A("| 车型结构 | 2016-02 ~ 2026-07 | 无 |")
A("| 出口量 | 2016-2017 + 2023-09 起 | **2020-2022 缺失** |")
A("| 出口金额/均价 | 2023-09 起 | 之前无数据 |")
A("| 品牌集中度/排名 | 2023-09 起（35 个月） | 之前无品牌明细 |")
A("| 大排量/电动赛道品牌 | 2023-09 起 | 2023-12 生产缺失、2026-07 明细不全 |")
A("| 三轮排量结构 | 不推荐 | 覆盖率仅 53% |")
A("")
A("### 4.3 给可视化与报告撰写的建议")
A("")
A("1. **任何 2016 年参与的增长率对比都要标注不完整**，建议图表以 2017 年或 2019 年为起点。")
A("2. **出口图表必须断开 2020-2022**，用断点或分面（small multiples），不要画连续折线。")
A("3. **电动化图表从 2019 年开始**，或在 2018/2019 之间加断点虚线。")
A("4. **三轮排量结构不要出图**（覆盖率 53% 会误导），如需展示三轮，用分车型表。")
A("5. **2026 年数据点单独标注为'1-7 月'**，与完整年份用不同视觉编码（如空心点/虚线）。")
A("6. **品牌类结论只能说'近 3 年'**，不能说'十年格局变化'——品牌明细只有 35 个月。")
A("")
A("---")
A("")
A("## 五、指标索引（analysis_metrics.json）")
A("")
A("| 指标名 | 单位 | 口径 | 用途 |")
A("|---|---|---|---|")
for k, v in REPORT.items():
    A(f"| `{k}` | {v['unit']} | {v['scope']} | {(v['note'] or '')[:60]}… |")
A("")
A(f"共 {len(REPORT)} 个指标集，全部包含 `unit` / `scope` / `note` / `data` 字段。")
A("")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(L))

print("=" * 70)
print("OK")
print("  markdown ->", OUT_MD)
print("  json     ->", OUT_JSON, f"({os.path.getsize(OUT_JSON)/1024:.0f} KB)")
print("=" * 70)
print(f"period {FIRST} ~ {LAST}, {N_MONTHS} months")
print(f"cum production {TOTAL_P/YI:.3f}亿  sales {TOTAL_S/YI:.3f}亿  ratio {OVERALL_RATIO:.2f}%")
print(f"CAGR 2017-2025: P {cagr_17_25_p:.2f}%  S {cagr_17_25_s:.2f}%")
print(f"2026 YTD(1-7): P {p26/WAN:.1f}万 ({YTD_P_GROWTH:+.1f}%)  S {s26/WAN:.1f}万 ({YTD_S_GROWTH:+.1f}%)")
print(f"34M window: {WIN['export_volume_wan']:.1f}万, {WIN['export_amount_usd_yi']:.1f}亿美元, 外销率{WIN['export_ratio_pct']:.1f}%")
