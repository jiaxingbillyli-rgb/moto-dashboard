# -*- coding: utf-8 -*-
"""
Phase2 - 报告图表生成
读取 output/analysis_metrics.json -> 产出 output/report_charts.js + report_charts_preview.html
严格遵守 analysis_findings.md 第 4.3 节的数据口径红线。
"""
import json, os, io, math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'output')

METRICS = json.load(open(os.path.join(OUT, 'analysis_metrics.json'), encoding='utf-8'))['metrics']
M = METRICS

# ---------------------------------------------------------------- 配色
C_PROD      = '#3A6EA5'   # 产量 深蓝
C_SALES     = '#E8A33D'   # 销量 琥珀
C_EXPORT    = '#C0392B'   # 出口 砖红（重点）
C_EXPORT_L  = '#E18B85'   # 出口 浅（不完整口径）
C_DOMESTIC  = '#8FA9C4'   # 内销 灰蓝
C_DOM_L     = '#C6D2DE'
C_GREY      = '#9AA5B1'
C_GREY_L    = '#C9CDD4'
C_UP        = '#C0392B'   # 涨 红（中国市场惯例）
C_DOWN      = '#2E8B57'   # 跌 绿

D_LE110   = '#A9C0D8'
D_110_125 = '#4A7FB5'
D_125_150 = '#5AD8A6'
D_150_250 = '#F0B429'
D_GT250   = '#D64541'

VT_QI    = '#3A6EA5'
VT_WAN   = '#9DB4D0'
VT_TA    = '#E8A33D'
VT_OTHER = '#CFD6DE'

C_ELEC    = '#8E6BBF'
C_ELEC_L  = '#BFA6D8'

FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif'

def ax_label(opts=None):
    d = {"color": "#5B6673", "fontSize": 11}
    if opts: d.update(opts)
    return d

AXIS_LINE  = {"lineStyle": {"color": "#D5DCE6"}}
SPLIT_LINE = {"lineStyle": {"color": "#EDF1F6"}}

def tooltip(extra=None):
    t = {
        "trigger": "axis",
        "axisPointer": {"type": "shadow", "shadowStyle": {"color": "rgba(150,160,175,0.08)"}},
        "backgroundColor": "rgba(255,255,255,0.97)",
        "borderColor": "#D5DCE6",
        "borderWidth": 1,
        "padding": [8, 12],
        "textStyle": {"color": "#2C3542", "fontSize": 12, "fontFamily": FONT},
        "extraCssText": "box-shadow:0 6px 20px rgba(31,41,55,0.12);border-radius:6px;"
    }
    if extra: t.update(extra)
    return t

def legend(data=None, bottom=0):
    d = {
        "textStyle": {"color": "#5B6673", "fontSize": 11, "fontFamily": FONT},
        "itemWidth": 14, "itemHeight": 9, "itemGap": 14,
        "bottom": bottom, "left": "center"
    }
    if data: d["data"] = data
    return d

def value_axis(name, opts=None):
    d = {
        "type": "value", "name": name,
        "nameTextStyle": {"color": "#7A8798", "fontSize": 11, "padding": [0, 0, 0, -4]},
        "axisLine": {"show": False}, "axisTick": {"show": False},
        "axisLabel": ax_label(),
        "splitLine": SPLIT_LINE
    }
    if opts: d.update(opts)
    return d

def cat_axis(data, opts=None):
    d = {
        "type": "category", "data": data,
        "axisLine": AXIS_LINE,
        "axisTick": {"show": False},
        "axisLabel": ax_label()
    }
    if opts: d.update(opts)
    return d

BASE_OPT = {
    "backgroundColor": "transparent",
    "textStyle": {"fontFamily": FONT, "color": "#2C3542"},
    "animation": False,
}

def nice_range(vals, pad_ratio=0.12, floor_to=None, min0=False):
    vs = [v for v in vals if v is not None]
    lo, hi = min(vs), max(vs)
    if min0: lo = min(lo, 0)
    span = hi - lo or 1
    lo = lo - span * pad_ratio
    hi = hi + span * pad_ratio
    if floor_to:
        lo = math.floor(lo / floor_to) * floor_to
        hi = math.ceil(hi / floor_to) * floor_to
    return round(lo, 2), round(hi, 2)

CHARTS = []
def add(cid, title, subtitle, caption, height, option, section=""):
    o = dict(BASE_OPT)
    o.update(option)
    CHARTS.append({
        "id": cid, "section": section, "title": title, "subtitle": subtitle,
        "caption": caption, "height": height, "option": o
    })

# ================================================================ 品牌简称
SHORT = {
    '江门市大长江集团有限公司': '大长江',
    '重庆隆鑫机车有限公司': '隆鑫',
    '宗申产业集团有限公司': '宗申',
    '广东大冶摩托车技术有限公司': '大冶',
    '新大洲本田摩托(苏州)有限公司': '新大洲本田',
    '雅迪科技集团有限公司': '雅迪',
    '重庆银翔摩托车集团有限公司': '银翔',
    '广州豪进摩托车股份有限公司': '豪进',
    '五羊-本田摩托（广州）有限公司': '五羊-本田',
    '洛阳北方企业集团有限公司': '洛阳北方',
    '浙江绿源电动车有限公司': '绿源',
    '浙江春风动力股份有限公司': '春风动力',
    '江门市珠峰摩托车有限公司': '珠峰',
    '广州大运摩托车有限公司': '大运',
    '重庆航天巴山摩托车制造有限公司': '航天巴山',
    '浙江钱江摩托股份有限公司': '钱江',
    '重庆千里科技股份有限公司': '千里科技',
    '厦门厦杏摩托有限公司': '厦杏',
    '济南轻骑铃木摩托车有限公司': '轻骑铃木',
    '广州天马集团天马摩托车有限公司': '天马',
    '广州三雅摩托车有限公司': '三雅',
    '广东星际机车科技有限公司': '星际机车',
    '重庆润通智能装备有限公司': '润通',
    '重庆鑫源摩托车股份有限公司': '鑫源',
    '江苏新日电动车股份有限公司': '新日',
    '江苏淮海新能源车辆有限公司': '淮海新能源',
    '西藏新珠峰摩托车有限公司': '新珠峰',
    '杭州土星动力科技有限公司': '土星动力',
    '重庆银钢科技(集团)有限公司': '银钢',
    '浙江华洋赛车股份有限公司': '华洋赛车',
    '济南大隆机车工业有限公司': '济南大隆',
    '常州光阳摩托车有限公司': '光阳',
    '重庆光宇摩托车制造有限公司': '光宇',
    '力帆实业（集团）股份有限公司': '力帆',
}
CITY = ['江门市', '重庆市', '重庆', '广州市', '广州', '浙江省', '浙江', '广东省', '广东',
        '江苏省', '江苏', '西藏自治区', '西藏', '杭州市', '杭州', '厦门市', '厦门',
        '济南市', '济南', '洛阳市', '洛阳', '常州市', '常州', '苏州市', '苏州']

def short_name(n):
    if n in SHORT: return SHORT[n]
    s = n
    for suf in ('股份有限公司', '有限责任公司', '有限公司', '公司'):
        if s.endswith(suf):
            s = s[:-len(suf)]; break
    for c in CITY:
        if s.startswith(c) and len(s) - len(c) >= 2:
            s = s[len(c):]; break
    return s or n

def wan(x, nd=1):
    return None if x is None else round(x / 10000.0, nd)

# =====================================================================================
# A1 月度产销趋势
# =====================================================================================
mp = M['monthly_production_sales']['data']
yms = [r['ym'] for r in mp]
prod_w = [wan(r['production']) for r in mp]
sale_w = [wan(r['sales']) for r in mp]
ratio = [r['ratio_pct'] for r in mp]
lo, hi = nice_range(ratio, 0.10, floor_to=5)
add('a1_monthly_trend',
    '月度产销趋势（2016.02 – 2026.07）',
    '全行业产量与销量月度走势，灰色虚线为产销率（销量/产量）',
    '图注：共 122 个月，单位为万辆；2016 年缺 8/9/10 月、2023 年缺 7 月（已断开，非"跌至零"）。'
    '产销率长期围绕 100% 窄幅波动，全周期累计产销率 99.56%，行业无系统性库存压力。'
    '2026 年仅 1–7 月，右端为最新观测点而非全年。',
    430,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 52, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(yms, {"axisLabel": ax_label({"rotate": 45, "interval": 11, "fontSize": 10}),
                                "axisLine": {"lineStyle": {"color": "#D5DCE6"}},
                                "splitLine": {"show": False}}),
        "yAxis": [
            value_axis('万辆', {"min": 0}),
            value_axis('产销率 %', {"min": lo, "max": hi, "splitLine": {"show": False},
                                    "axisLabel": ax_label({"formatter": "{value}%"})})
        ],
        "dataZoom": [{"type": "inside", "throttle": 50},
                     {"type": "slider", "height": 15, "bottom": 22,
                      "borderColor": "#DDE3EB", "fillerColor": "rgba(58,110,165,0.10)",
                      "handleStyle": {"color": "#8FA9C4"}, "textStyle": {"color": "#8A95A3", "fontSize": 10}}],
        "series": [
            {"name": "产量", "type": "line", "data": prod_w, "showSymbol": False, "smooth": False,
             "lineStyle": {"width": 1.6, "color": C_PROD}, "itemStyle": {"color": C_PROD},
             "z": 3},
            {"name": "销量", "type": "line", "data": sale_w, "showSymbol": False, "smooth": False,
             "lineStyle": {"width": 1.6, "color": C_SALES}, "itemStyle": {"color": C_SALES},
             "z": 2},
            {"name": "产销率", "type": "line", "yAxisIndex": 1, "data": ratio, "showSymbol": False,
             "lineStyle": {"width": 1, "color": C_GREY, "type": "dashed"},
             "itemStyle": {"color": C_GREY}, "z": 1,
             "markLine": {"silent": True, "symbol": "none",
                          "data": [{"yAxis": 100,
                                    "lineStyle": {"color": "#C9CDD4", "type": "dashed", "width": 1},
                                    "label": {"formatter": "产销率 100%", "position": "insideEndTop",
                                              "color": "#9AA5B1", "fontSize": 10}}]}}
        ]
    }, section='A. 总量与增长')

# =====================================================================================
# A2 年度产销量与可比同比
# =====================================================================================
yp = M['yearly_production_sales']['data']
years = [r['year'] for r in yp]
x_lbl = [str(r['year']) + ('' if r['is_full_year'] else '\n(不完整)') for r in yp]
prod_y = [wan(r['production']) for r in yp]
sale_y = [wan(r['sales']) for r in yp]
ypoy = [r['prod_yoy_pct'] for r in yp]
ysyoy = [r['sales_yoy_pct'] for r in yp]

def bar_with_flag(vals, flags, color, color_l):
    return [{"value": v, "itemStyle": {"color": color_l if f else color}}
            for v, f in zip(vals, flags)]

notfull = [not r['is_full_year'] for r in yp]
add('a2_yearly_prod_sales',
    '年度产销量与可比同比（2016 – 2026）',
    '柱：年度产量/销量（万辆）；线：同比增速，仅在本年与上年均为完整年时给出',
    '图注：可比年份仅 2018 / 2019 / 2020 / 2021 / 2022 / 2025；2017（对比 2016 仅 8 个月）、'
    '2023（11 个月）、2024（对比 2023 不完整）、2026（1–7 月）的同比已在数据中置空，图中不留数据点，'
    '切勿插值或口算。浅色柱代表非完整年份（2016 / 2023 / 2026）。'
    '2017→2025 产量 CAGR 仅 3.14%，行业是低速稳健增长。',
    420,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(x_lbl, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('同比 %', {"splitLine": {"show": False},
                                        "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": "产量", "type": "bar", "data": bar_with_flag(prod_y, notfull, C_PROD, '#A9C0D8'),
             "barMaxWidth": 26, "z": 2},
            {"name": "销量", "type": "bar", "data": bar_with_flag(sale_y, notfull, C_SALES, '#F0D5A8'),
             "barMaxWidth": 26, "z": 2},
            {"name": "产量同比", "type": "line", "yAxisIndex": 1, "data": ypoy, "connectNulls": False,
             "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 1.8, "color": C_UP}, "itemStyle": {"color": C_UP}, "z": 4,
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_UP, "fontSize": 10}},
            {"name": "销量同比", "type": "line", "yAxisIndex": 1, "data": ysyoy, "connectNulls": False,
             "symbol": "emptyCircle", "symbolSize": 6,
             "lineStyle": {"width": 1.4, "color": C_UP, "type": "dashed"},
             "itemStyle": {"color": C_UP}, "z": 3}
        ]
    }, section='A. 总量与增长')

# =====================================================================================
# A3 二轮 / 三轮结构
# =====================================================================================
tw = M['two_wheeler_vs_three_wheeler']['data']
tw_y = [str(r['year']) + ('' if r['year'] not in (2016, 2023, 2026) else '\n(不完整)') for r in tw]
tw2 = [wan(r['two_wheeler']) for r in tw]
tw3 = [wan(r['three_wheeler']) for r in tw]
tw3s = [r['three_wheeler_share_pct'] for r in tw]
add('a3_two_three_wheeler',
    '二轮车与三轮车产量结构（2016 – 2026）',
    '柱：二轮/三轮产量（万辆，堆叠＝行业总量）；线：三轮占比',
    '图注：基于分车型表（与总量 100% 对齐，口径完整）。二轮车长期占 88% 左右，三轮是稳定的 12% 补充盘，'
    '十年间结构基本未变。三轮分排量表覆盖率仅约 53%（电动三轮未纳入），因此不出三轮排量结构图。',
    360,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(tw_y, {"axisLabel": ax_label({"fontSize": 10})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('三轮占比 %', {"min": 0, "max": 20, "splitLine": {"show": False},
                                            "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": "二轮车", "type": "bar", "stack": "t", "data": tw2, "barMaxWidth": 34,
             "itemStyle": {"color": C_PROD}},
            {"name": "三轮车", "type": "bar", "stack": "t", "data": tw3, "barMaxWidth": 34,
             "itemStyle": {"color": C_SALES}},
            {"name": "三轮占比", "type": "line", "yAxisIndex": 1, "data": tw3s,
             "symbol": "circle", "symbolSize": 5,
             "lineStyle": {"width": 1.6, "color": C_EXPORT}, "itemStyle": {"color": C_EXPORT}}
        ]
    }, section='A. 总量与增长')

# =====================================================================================
# B1 内销 vs 出口拆分（核心图）
# =====================================================================================
dv = M['domestic_vs_export_split']['data']['annual']
b1_x = [("%d\n(%s)" % (r['year'], r['window'].replace('1-12月', '全年'))) for r in dv]
b1_dom = [r['domestic_wan'] for r in dv]
b1_exp = [r['export_wan'] for r in dv]
b1_rat = [r['export_ratio_pct'] for r in dv]
add('b1_domestic_export_split',
    '销量 = 内销 + 出口：增长几乎全部来自海外（2023.09 – 2026.07）',
    '柱：内销与出口（万辆，堆叠＝当期销量）；线：外销率（出口/销量）',
    '图注：内销 = 销量 − 出口。2024→2025 为全年可比口径：销量 +9.8%，其中出口 +21.5%、'
    '内销从 891.5 万辆降至 852.2 万辆（−4.4%）——出口增量（+234.6 万辆）已超过销量总增量（+195.3 万辆），'
    '内需为负贡献。2023 年为 9–12 月、2026 年为 1–7 月，不可与完整年直接比较（浅色柱）。'
    '出口数据 2020–2022 缺失，故本图从 2023 年起。',
    430,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(b1_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('外销率 %', {"min": 0, "max": 80, "splitLine": {"show": False},
                                          "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": "内销", "type": "bar", "stack": "s", "data": b1_dom, "barMaxWidth": 56,
             "itemStyle": {"color": C_DOMESTIC},
             "label": {"show": True, "position": "inside", "formatter": "{c}",
                       "color": "#FFFFFF", "fontSize": 11, "fontWeight": "bold"}},
            {"name": "出口", "type": "bar", "stack": "s", "data": b1_exp, "barMaxWidth": 56,
             "itemStyle": {"color": C_EXPORT},
             "label": {"show": True, "position": "inside", "formatter": "{c}",
                       "color": "#FFFFFF", "fontSize": 11, "fontWeight": "bold"}},
            {"name": "外销率", "type": "line", "yAxisIndex": 1, "data": b1_rat,
             "symbol": "circle", "symbolSize": 7,
             "lineStyle": {"width": 2, "color": C_UP}, "itemStyle": {"color": C_UP},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_UP, "fontSize": 11, "fontWeight": "bold"}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# B2 外销率走势（断开 2020-2022）
# =====================================================================================
emt = M['export_monthly_total']['data']
early_map = {r['ym']: r['export_ratio_pct'] for r in emt if r['year'] <= 2019}
recent_map = {r['ym']: r['export_ratio_pct'] for r in emt if r['ym'] >= '2023-09'}
s_early = [early_map.get(y) for y in yms]
s_recent = [recent_map.get(y) for y in yms]
lo2, hi2 = nice_range([v for v in s_early + s_recent if v is not None], 0.12, floor_to=5)
add('b2_export_ratio_trend',
    '外销率走势（月度，2016 – 2026）：出口占比持续抬升',
    '出口量 / 当月销量。2020–2022 年源报表取消出口统计，图中已断开并留出缺失带',
    '图注：★ 关键口径 —— 2020、2021、2022 三个完整年度出口数据完全缺失（源报表当年取消该表），'
    '2018 年仅 2 个月、2019 年仅 7 个月、2023 年仅 9–12 月。因此 2019→2023 的"变化"不可解读为增长或下滑，'
    '两条线段必须分开看（早期窗口 2016–2019 / 近期窗口 2023.09 起）。'
    '在近期窗口内，外销率由 2023 年的 48.4% 单调升至 2026 年 1–7 月的 63.0%。',
    400,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(yms, {"axisLabel": ax_label({"rotate": 45, "interval": 11, "fontSize": 10}),
                                "splitLine": {"show": False}}),
        "yAxis": value_axis('外销率 %', {"min": lo2, "max": hi2,
                                          "axisLabel": ax_label({"formatter": "{value}%"})}),
        "series": [
            {"name": "外销率（早期窗口 2016–2019）", "type": "line", "data": s_early,
             "connectNulls": False, "showSymbol": False,
             "lineStyle": {"width": 1.6, "color": C_GREY}, "itemStyle": {"color": C_GREY}},
            {"name": "外销率（2023.09 起）", "type": "line", "data": s_recent,
             "connectNulls": False, "showSymbol": False,
             "lineStyle": {"width": 2.2, "color": C_EXPORT}, "itemStyle": {"color": C_EXPORT},
             "markArea": {"silent": True, "itemStyle": {"color": "rgba(120,130,145,0.10)"},
                          "label": {"show": True, "position": "insideTop", "distance": 8,
                                    "formatter": "2020–2022 出口数据缺失",
                                    "color": "#8A95A3", "fontSize": 11},
                          "data": [[{"xAxis": "2020-01"}, {"xAxis": "2022-12"}]]}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# B3 出口量年度对比（断开 2020-2022）
# =====================================================================================
ey = {r['year']: r for r in M['export_yearly']['data']}
order = [2016, 2017, 2018, 2019, 0, 2023, 2024, 2025, 2026]
b3_x, b3_v, b3_style = [], [], []
for y in order:
    if y == 0:
        b3_x.append('2020–2022')
        b3_v.append(None)
        b3_style.append(None)
        continue
    r = ey[y]
    b3_x.append("%d\n(%d个月)" % (y, r['months_covered']))
    b3_v.append(wan(r['export_volume']))
    b3_style.append({"value": wan(r['export_volume']),
                     "itemStyle": {"color": C_EXPORT if r['is_full_year'] else C_EXPORT_L}})
add('b3_export_volume_yearly',
    '出口量年度对比（万辆）：2020–2022 数据缺失，已断开',
    '仅 2024、2025 为完整年（实心柱），其余年份覆盖率不同，柱上方标注覆盖月数',
    '图注：★ 切勿把 2019 年的 549.4 万辆与 2023 年的 289.3 万辆连起来解读 —— 2020–2022 出口数据完全缺失，'
    '且 2018 年仅 2 个月、2019 年仅 7 个月、2023 年仅 9–12 月，口径互不相同。'
    '可用于对比的只有 2024（1,093.6 万辆）与 2025（1,328.2 万辆）两个完整年，同比 +21.5%。'
    '2026 年为 1–7 月（898.5 万辆），与 2025 年同期（757.9 万辆）相比 +18.6%。',
    400,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(b3_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": value_axis('万辆', {"min": 0}),
        "series": [
            {"name": "出口量", "type": "bar", "data": b3_style, "barMaxWidth": 58,
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11},
             "markArea": {"silent": True, "itemStyle": {"color": "rgba(120,130,145,0.10)"},
                          "data": [[{"xAxis": "2020–2022"}, {"xAxis": "2020–2022"}]]}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# B4 出口金额与单车均价
# =====================================================================================
ey4 = [ey[y] for y in (2023, 2024, 2025, 2026)]
b4_x = ["%d\n(%s)" % (r['year'], '9-12月' if r['year'] == 2023 else ('1-7月' if r['year'] == 2026 else '全年'))
        for r in ey4]
b4_amt = [round(r['export_amount_usd_10k'] / 10000.0, 2) for r in ey4]
b4_price = [r['avg_price_usd'] for r in ey4]
add('b4_export_value_price',
    '出口金额与单车均价（2023.09 – 2026.07）：量价齐升',
    '柱：出口金额（亿美元）；线：单车均价（美元/辆）',
    '图注：出口金额数据仅 2023 年 9 月起可得（此前源报表无金额字段），故本图不含 2023 年之前的年份。'
    '2023 年为 9–12 月、2026 年为 1–7 月，不可与完整年（2024/2025）直接比较。'
    '2025 年单车均价 709.1 美元，较 2024 年 +11.5% —— 出口是"量价齐升"，不是单纯走量。',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(b4_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": [value_axis('亿美元', {"min": 0}),
                  value_axis('美元/辆', {"min": 500, "max": 800, "splitLine": {"show": False}})],
        "series": [
            {"name": "出口金额", "type": "bar",
             "data": [{"value": v, "itemStyle": {"color": C_EXPORT if i in (1, 2) else C_EXPORT_L}}
                      for i, v in enumerate(b4_amt)],
             "barMaxWidth": 56,
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11}},
            {"name": "单车均价", "type": "line", "yAxisIndex": 1, "data": b4_price,
             "symbol": "circle", "symbolSize": 8,
             "lineStyle": {"width": 2.2, "color": C_SALES}, "itemStyle": {"color": C_SALES},
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": C_SALES, "fontSize": 11, "fontWeight": "bold"}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# B5 1-7 月同期对比（唯一可比序列）
# =====================================================================================
ytd = M['domestic_vs_export_split']['data']['ytd_1_7']
b5_x = ["%d年1-7月" % r['year'] for r in ytd]
b5_exp = [r['export_wan'] for r in ytd]
b5_dom = [r['domestic_wan'] for r in ytd]
b5_rat = [r['export_ratio_pct'] for r in ytd]
add('b5_ytd_1_7_split',
    '1–7 月同期对比（唯一可比序列）：2026 年内销回暖 +8.0%',
    '柱：出口与内销（万辆）；线：外销率。气泡标注为对上年同期的同比',
    '图注：由于 2026 年仅 1–7 月，年度同比不可比，本图统一采用 1–7 月同期口径。'
    '出口：+24.3%（2025）→ +18.6%（2026），维持高增长；'
    '内销：−5.5%（2025）→ +8.0%（2026），出现回暖信号。这是报告"一正一反"判断的数据来源。'
    '注意：外销率仍在上升（54.1% → 60.8% → 63.0%），内销回暖只是增速转正，并未改变出口主导的格局。',
    400,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(b5_x, {"axisLabel": ax_label({"fontSize": 11})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('外销率 %', {"min": 0, "max": 80, "splitLine": {"show": False},
                                          "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": "出口", "type": "bar", "data": b5_exp, "barMaxWidth": 42,
             "itemStyle": {"color": C_EXPORT},
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11},
             "markPoint": {"symbol": "circle", "symbolSize": 1,
                           "data": [{"coord": [1, 757.9], "value": "同比 +24.3%",
                                     "label": {"show": True, "position": "top", "offset": [0, -12],
                                               "color": C_UP, "fontSize": 11, "fontWeight": "bold"}},
                                    {"coord": [2, 898.5], "value": "同比 +18.6%",
                                     "label": {"show": True, "position": "top", "offset": [0, -12],
                                               "color": C_UP, "fontSize": 11, "fontWeight": "bold"}}]}},
            {"name": "内销", "type": "bar", "data": b5_dom, "barMaxWidth": 42,
             "itemStyle": {"color": C_DOMESTIC},
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11},
             "markPoint": {"symbol": "circle", "symbolSize": 1,
                           "data": [{"coord": [1, 489.3], "value": "同比 −5.5%",
                                     "label": {"show": True, "position": "top", "offset": [0, -12],
                                               "color": C_DOWN, "fontSize": 11, "fontWeight": "bold"}},
                                    {"coord": [2, 528.6], "value": "同比 +8.0%",
                                     "label": {"show": True, "position": "top", "offset": [0, -12],
                                               "color": C_UP, "fontSize": 11, "fontWeight": "bold"}}]}},
            {"name": "外销率", "type": "line", "yAxisIndex": 1, "data": b5_rat,
             "symbol": "circle", "symbolSize": 7,
             "lineStyle": {"width": 2, "color": C_UP}, "itemStyle": {"color": C_UP},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_UP, "fontSize": 11, "fontWeight": "bold"}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# B6 出口 vs 内销排量结构（反直觉）
# =====================================================================================
evd = [r for r in M['export_vs_domestic_displacement']['data'] if r['year'] == 2025]
groups = [r['group'] for r in evd]
add('b6_export_vs_domestic_disp',
    '出口 vs 内销排量结构（2025）：高度同构，出口并非更偏大排量',
    '同口径对比（出口分排量表本身不含电动，故与"剔除电动后的二轮燃油生产结构"对比）',
    '图注：★ 反直觉结论 —— 出口结构与内销结构高度同构，各排量段差异均在 ±2.1pp 以内。'
    '出口在 150–250ml 段高出内销约 +2.0pp，但在 >250ml 大排量段反而低 1.3pp。'
    '即：大排量增长主要由国内消费升级驱动，出口不是主要拉力，请勿写成"出口更偏大排量"。'
    '（2024 与 2026 年结论一致。）',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(groups, {"axisLabel": ax_label({"fontSize": 11})}),
        "yAxis": [value_axis('占比 %', {"min": 0, "max": 40,
                                        "axisLabel": ax_label({"formatter": "{value}%"})}),
                  value_axis('差异 pp', {"min": -3, "max": 3, "splitLine": {"show": False}})],
        "series": [
            {"name": "出口结构", "type": "bar", "data": [r['export_share_pct'] for r in evd],
             "barMaxWidth": 34, "itemStyle": {"color": C_EXPORT},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": "#6B7785", "fontSize": 10}},
            {"name": "内销（二轮燃油）结构", "type": "bar",
             "data": [r['domestic_fuel_share_pct'] for r in evd],
             "barMaxWidth": 34, "itemStyle": {"color": C_DOMESTIC},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": "#6B7785", "fontSize": 10}},
            {"name": "差异（出口−内销）", "type": "line", "yAxisIndex": 1,
             "data": [r['diff_pp'] for r in evd], "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 1.4, "color": C_GREY, "type": "dashed"},
             "itemStyle": {"color": C_GREY}}
        ]
    }, section='B. 出口 vs 内销')

# =====================================================================================
# C1 ★ 二轮燃油排量结构演变
# =====================================================================================
df = M['displacement_2w_share_fuel_only']['data']
c1_x = [str(r['year']) for r in df]
c1_x[-1] = '2026\n(1-7月)'
segs = [('≤110ml', D_LE110), ('110-125ml', D_110_125), ('125-150ml', D_125_150),
        ('150-250ml', D_150_250), ('>250ml', D_GT250)]
c1_series = []
for i, (nm, col) in enumerate(segs):
    show_lbl = nm in ('≤110ml', '>250ml')
    c1_series.append({
        "name": nm, "type": "bar", "stack": "d", "data": [r[nm] for r in df],
        "barMaxWidth": 44, "itemStyle": {"color": col},
        "label": {"show": show_lbl,
                  "position": "top" if nm == '>250ml' else "inside",
                  "formatter": "{c}%", "fontSize": 10,
                  "color": D_GT250 if nm == '>250ml' else "#FFFFFF",
                  "fontWeight": "bold" if nm == '>250ml' else "normal"}
    })
c1_series.append({"name": "≤110ml 趋势", "type": "line", "data": [r['≤110ml'] for r in df],
                  "symbol": "circle", "symbolSize": 5, "z": 6,
                  "lineStyle": {"width": 1.6, "color": "#5B6673", "type": "dashed"},
                  "itemStyle": {"color": "#5B6673"}})
c1_series.append({"name": ">250ml 趋势", "type": "line", "data": [r['>250ml'] for r in df],
                  "symbol": "circle", "symbolSize": 5, "z": 7,
                  "lineStyle": {"width": 2.4, "color": D_GT250},
                  "itemStyle": {"color": D_GT250}})
add('c1_disp_2w_fuel_share',
    '二轮燃油车排量结构演变（2016 – 2026）：小排量腰斩，大排量增长 17 倍',
    '★ 全报告最重要的结构图。分母 = 二轮燃油车总量（已剔除电动摩托车），堆叠为 100%',
    '图注：这是观察燃油车内部"结构升级"最干净的口径（剔除电动扰动）。核心变化：'
    '≤110ml 从 30.1% 萎缩至 17.4%（腰斩）；125-150ml 22.6%→29.0%；150-250ml 5.7%→12.0%；'
    '>250ml 0.3%→5.6%（约 17 倍）。中高排量段份额十年间全部翻倍以上。'
    '2026 年为 1–7 月数据。已把 2016–2022 合并段与 2023+ 细分段映射到统一分组，跨年可比。'
    '注意：本图不含电动摩托车，电动化趋势见 C4。',
    470,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 44, "containLabel": True},
        "legend": legend(data=[s[0] for s in segs], bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(c1_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": value_axis('占燃油二轮比重 %', {"min": 0, "max": 100,
                                                  "axisLabel": ax_label({"formatter": "{value}%"})}),
        "series": c1_series
    }, section='C. 排量与车型结构')

# =====================================================================================
# C2 大排量（>250ml）专题
# =====================================================================================
bd = M['big_displacement_2w']['data']
c2_x = [str(r['year']) + ('' if r['is_full_year'] else '\n(不完整)') for r in bd]
c2_v = [wan(r['volume']) for r in bd]
c2_s = [r['share_of_2w_pct'] for r in bd]
add('c2_big_displacement',
    '大排量（>250ml）二轮车：六年增长 4 倍多，2026 年增速骤降',
    '柱：>250ml 产量（万辆）；线：占二轮车比重（%）',
    '图注：2019 年 18.1 万辆 → 2025 年 95.4 万辆（+426%），占二轮比重 1.19% → 4.94%，2025 年同比 +23.3%。'
    '但 2026 年 1–7 月 60.8 万辆，较 2025 年同期 60.2 万辆仅 +1.1%，显著跑输行业整体 +14.9%，'
    '占二轮比重回落至 4.77% —— 高速增长期出现放缓信号（详见 E3）。'
    '浅色柱为非完整年份（2016 / 2023 / 2026）。口径提示：>250ml 组内 2023 年前为 400-750/>750ml，'
    '2023 年后为 400-500/500-800/>800ml，界点由 750ml 改为 800ml，存在微小口径差异。',
    400,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(c2_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('占二轮比重 %', {"min": 0, "max": 6, "splitLine": {"show": False},
                                              "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": ">250ml 产量", "type": "bar",
             "data": [{"value": v, "itemStyle": {"color": D_GT250 if f else "#EFA9A4"}}
                      for v, f in zip(c2_v, [r['is_full_year'] for r in bd])],
             "barMaxWidth": 40,
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 10}},
            {"name": "占二轮比重", "type": "line", "yAxisIndex": 1, "data": c2_s,
             "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 2.2, "color": C_UP}, "itemStyle": {"color": C_UP},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_UP, "fontSize": 10}}
        ]
    }, section='C. 排量与车型结构')

# =====================================================================================
# C3 车型结构（燃油 only）
# =====================================================================================
vt = M['vehicle_type_share_2w_fuel_only']['data']
c3_x = [str(r['year']) for r in vt]
c3_x[-1] = '2026\n(1-7月)'
vt_segs = [('骑式', VT_QI, True), ('弯梁式', VT_WAN, False),
           ('踏板式(燃油)', VT_TA, True), ('其它式', VT_OTHER, False)]
add('c3_vehicle_type_fuel',
    '二轮燃油车车型结构演变（2016 – 2026）：骑式上升，燃油踏板小幅下滑',
    '分母 = 二轮燃油车总量（已剔除电动摩托车），堆叠为 100%',
    '图注：★ 重要校正 —— 电动摩托车在分车型表中 100% 计入"踏板式"（已验证各年踏板式产量恒 ≥ 电动产量）。'
    '因此含电动的口径会得出"踏板车份额暴涨至 49%"的假象。剔除电动后的真实情况：'
    '骑式 58.7% → 67.1%（上升），弯梁式 18.1% → 13.0%（下降），燃油踏板式 23.3% → 20.0%（小幅下滑）。'
    '车型结构图必须使用本口径。2026 年为 1–7 月。',
    420,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(c3_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": value_axis('占燃油二轮比重 %', {"min": 0, "max": 100,
                                                  "axisLabel": ax_label({"formatter": "{value}%"})}),
        "series": [
            {"name": nm, "type": "bar", "stack": "v", "data": [r[nm] for r in vt],
             "barMaxWidth": 44, "itemStyle": {"color": col},
             "label": {"show": sl, "position": "inside", "formatter": "{c}%",
                       "fontSize": 10, "color": "#FFFFFF"}}
            for nm, col, sl in vt_segs
        ]
    }, section='C. 排量与车型结构')

# =====================================================================================
# C4 电动摩托车年度走势（2019 起）
# =====================================================================================
em = [r for r in M['electric_motorcycle']['data'] if r['year'] >= 2019]
c4_x = [str(r['year']) + ('' if r['is_full_year'] else '\n(不完整)') for r in em]
c4_v = [wan(r['volume']) for r in em]
c4_s = [r['share_of_2w_pct'] for r in em]
add('c4_electric_trend',
    '电动摩托车：2022 年脉冲式高峰后回落，2025 年企稳在 11% 左右',
    '柱：二轮电动摩托车产量（万辆）；线：占二轮车比重（%）。2019 年起',
    '图注：★ 口径提示 —— 2016–2018 年电动摩托车仅 6.1 / 9.9 / 10.2 万辆，与 2019 年的 177.7 万辆存在数量级断层'
    '（判定为 2019 年新国标实施后统计口径变更），故本图从 2019 年起，2019 年同比 +1634% 无解读价值。'
    '走势：2019 年 177.7 万辆 → 2022 年峰值 542.2 万辆（占二轮 30.6%）→ 2023 年 390.0 万辆 → '
    '2024 年 219.6 万辆 → 2025 年 226.5 万辆（11.7%，同比 +3.1%），两年回落六成后企稳。'
    '判断为"新国标过渡期抢装 + 需求前置透支"，而非电动化失败。本表仅含二轮电动，三轮电动未纳入明细表。',
    400,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(c4_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('占二轮比重 %', {"min": 0, "max": 35, "splitLine": {"show": False},
                                              "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": "电动摩托车产量", "type": "bar",
             "data": [{"value": v, "itemStyle": {"color": C_ELEC if r['is_full_year'] else C_ELEC_L}}
                      for v, r in zip(c4_v, em)],
             "barMaxWidth": 48,
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11},
             "markPoint": {"symbol": "circle", "symbolSize": 1,
                           "data": [{"coord": [3, 542.2], "value": "峰值 542.2 万辆 / 占二轮 30.6%",
                                     "label": {"show": True, "position": "top", "offset": [0, -14],
                                               "color": C_ELEC, "fontSize": 11, "fontWeight": "bold"}}]}},
            {"name": "占二轮比重", "type": "line", "yAxisIndex": 1, "data": c4_s,
             "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 2.2, "color": C_ELEC}, "itemStyle": {"color": C_ELEC},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_ELEC, "fontSize": 10}}
        ]
    }, section='C. 排量与车型结构')

# =====================================================================================
# C5 电动摩托车月度（峰值可视化）
# =====================================================================================
emm = [r for r in M['electric_monthly']['data'] if r['ym'] >= '2019-01']
c5_x = [r['ym'] for r in emm]
c5_v = [wan(r['volume']) for r in emm]
add('c5_electric_monthly',
    '电动摩托车月度产量（2019.01 – 2026.07）：2022 年 9 月见顶',
    '万辆/月。峰值月 2022-09 为 77.5 万辆，随后快速回落',
    '图注：本图用于直观展示 2022 年的"抢装脉冲"——单月产量在 2022-09 达到 77.5 万辆的历史峰值，'
    '到 2024 年多数月份已回落至 15–20 万辆区间，2025–2026 年企稳在 20 万辆/月左右。'
    '2019 年之前的电动数据在源报表中口径不同（仅 6–10 万辆/年），已从本图剔除。'
    '2026 年右端为 1–7 月。',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 52, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(c5_x, {"axisLabel": ax_label({"rotate": 45, "interval": 5, "fontSize": 10}),
                                 "splitLine": {"show": False}}),
        "yAxis": value_axis('万辆', {"min": 0}),
        "dataZoom": [{"type": "inside", "throttle": 50},
                     {"type": "slider", "height": 15, "bottom": 22,
                      "borderColor": "#DDE3EB", "fillerColor": "rgba(142,107,191,0.10)",
                      "handleStyle": {"color": "#BFA6D8"}, "textStyle": {"color": "#8A95A3", "fontSize": 10}}],
        "series": [
            {"name": "电动摩托车产量", "type": "line", "data": c5_v, "showSymbol": False,
             "lineStyle": {"width": 1.6, "color": C_ELEC}, "itemStyle": {"color": C_ELEC},
             "areaStyle": {"color": "rgba(142,107,191,0.14)"},
             "markPoint": {"symbol": "pin", "symbolSize": 42,
                           "data": [{"coord": ["2022-09", 77.5], "value": "峰值 77.5",
                                     "itemStyle": {"color": C_ELEC},
                                     "label": {"color": "#FFFFFF", "fontSize": 10}}]}}
        ]
    }, section='C. 排量与车型结构')

# =====================================================================================
# D1 品牌集中度
# =====================================================================================
bc = [r for r in M['brand_concentration']['data'] if r['indicator'] == '销售']
d1_x = ["%d\n(%s)" % (r['year'], {2023: '9-12月', 2024: '全年', 2025: '全年', 2026: '1-7月'}[r['year']])
        for r in bc]
add('d1_brand_concentration',
    '行业品牌集中度：CR5 不升反降，行业仍高度分散',
    '销售口径。约 90 家企业在产，CR10 仅略过半',
    '图注：销量 CR5 由 2024 年的 38.1% 降至 2025 年的 36.9%（−1.2pp），2026 年 1–7 月回升至 37.4%；'
    'CR10 稳定在 54.2% → 53.5%。行业远未形成寡头格局。'
    '品牌明细数据仅覆盖 2023 年 9 月 – 2026 年 7 月（35 个月），PDF 历史数据无品牌明细，'
    '因此所有品牌类结论只能说"近 3 年"，不能说"十年格局变化"。2023 年生产口径因 2023-12 数据缺失 97% 已剔除。',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(d1_x, {"axisLabel": ax_label({"fontSize": 10, "lineHeight": 13})}),
        "yAxis": value_axis('占行业销量 %', {"min": 0, "max": 90,
                                             "axisLabel": ax_label({"formatter": "{value}%"})}),
        "series": [
            {"name": "CR5", "type": "line", "data": [r['cr5_pct'] for r in bc],
             "symbol": "circle", "symbolSize": 8,
             "lineStyle": {"width": 2.6, "color": C_EXPORT}, "itemStyle": {"color": C_EXPORT},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_EXPORT, "fontSize": 11, "fontWeight": "bold"}},
            {"name": "CR10", "type": "line", "data": [r['cr10_pct'] for r in bc],
             "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 1.8, "color": C_SALES}, "itemStyle": {"color": C_SALES},
             "label": {"show": True, "position": "bottom", "formatter": "{c}%",
                       "color": C_SALES, "fontSize": 10}},
            {"name": "CR20", "type": "line", "data": [r['cr20_pct'] for r in bc],
             "symbol": "circle", "symbolSize": 6,
             "lineStyle": {"width": 1.4, "color": C_GREY, "type": "dashed"},
             "itemStyle": {"color": C_GREY},
             "label": {"show": True, "position": "bottom", "formatter": "{c}%",
                       "color": C_GREY, "fontSize": 10}}
        ]
    }, section='D. 竞争格局')

# =====================================================================================
# D2 2025 年销量 TOP15
# =====================================================================================
rk = [r for r in M['brand_ranking_top25']['data'] if r['year'] == 2025][:15]
d2_names = [short_name(r['manufacturer']) for r in rk][::-1]
d2_vals = [wan(r['volume']) for r in rk][::-1]
d2_shr = [r['share_pct'] for r in rk][::-1]
d2_data = []
for i, (v, s) in enumerate(zip(d2_vals, d2_shr)):
    top5 = i >= (len(d2_vals) - 5)
    d2_data.append({"value": v, "share": s,
                    "itemStyle": {"color": C_EXPORT if top5 else C_PROD}})
add('d2_brand_ranking_2025',
    '2025 年销量 TOP15 品牌（万辆）：头部五家仅占 36.9%',
    '销售口径，完整年。红色为 CR5 成员（合计 36.9%）',
    '图注：2025 年行业第一大长江 268.7 万辆（12.3%），第二至第五为隆鑫 164.5 万（7.5%）、'
    '宗申 160.4 万（7.4%）、大冶 110.9 万（5.1%）、新大洲本田 100.3 万（4.6%）。'
    '前五家合计仅 36.9%，第 15 名仍有 41.4 万辆 —— 长尾极长，行业高度分散。'
    '品牌明细仅覆盖 2023-09 起的 35 个月，本图不代表"十年格局"。',
    470,
    {
        "grid": {"left": 6, "right": 40, "top": 20, "bottom": 24, "containLabel": True},
        "tooltip": tooltip({"trigger": "item",
                            "formatter": "{b}<br/>销量 {c} 万辆"}),
        "xAxis": value_axis('万辆', {"min": 0}),
        "yAxis": cat_axis(d2_names, {"axisLabel": ax_label({"fontSize": 11}),
                                     "splitLine": {"show": False},
                                     "axisLine": {"lineStyle": {"color": "#D5DCE6"}}}),
        "series": [
            {"name": "2025 年销量", "type": "bar", "data": d2_data, "barMaxWidth": 18,
             "itemStyle": {"borderRadius": [0, 3, 3, 0]},
             "label": {"show": True, "position": "right",
                       "formatter": "{c} 万辆", "color": "#6B7785", "fontSize": 10}}
        ]
    }, section='D. 竞争格局')

# =====================================================================================
# D3 头部品牌份额变化
# =====================================================================================
top12 = [r['manufacturer'] for r in M['brand_ranking_top25']['data'] if r['year'] == 2025][:12][::-1]
rank_map = {}
for y in (2024, 2025, 2026):
    rank_map[y] = {r['manufacturer']: r['share_pct'] for r in M['brand_ranking_top25']['data'] if r['year'] == y}
d3_names = [short_name(n) for n in top12]
add('d3_brand_share_shift',
    '头部品牌份额变化：2024 → 2025 → 2026 年 1–7 月',
    '销售口径份额（%）。份额在时间上可比性较好，但 2026 年仅为 1–7 月',
    '图注：份额口径（%）比绝对销量更适合跨期比较。可见春风动力份额持续上行（1.6%→2.6%→4.1%）、'
    '大长江稳居第一（11.7%→12.3%→13.1%）、隆鑫 2026 年 1–7 月回落至 6.3%。'
    '注意：2026 年为 1–7 月，与完整年份额存在季节性差异，仅作趋势参考。'
    '品牌明细仅 35 个月，不能解读为长期格局变化。',
    470,
    {
        "grid": {"left": 6, "right": 16, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": value_axis('销量份额 %', {"min": 0, "max": 15,
                                            "axisLabel": ax_label({"formatter": "{value}%"})}),
        "yAxis": cat_axis(d3_names, {"axisLabel": ax_label({"fontSize": 11}),
                                     "splitLine": SPLIT_LINE}),
        "series": [
            {"name": "2024 全年", "type": "bar", "data": [rank_map[2024].get(n) for n in top12],
             "barMaxWidth": 10, "itemStyle": {"color": C_DOM_L, "borderRadius": [0, 2, 2, 0]}},
            {"name": "2025 全年", "type": "bar", "data": [rank_map[2025].get(n) for n in top12],
             "barMaxWidth": 10, "itemStyle": {"color": C_PROD, "borderRadius": [0, 2, 2, 0]}},
            {"name": "2026 年1–7月", "type": "bar", "data": [rank_map[2026].get(n) for n in top12],
             "barMaxWidth": 10, "itemStyle": {"color": C_SALES, "borderRadius": [0, 2, 2, 0]}}
        ]
    }, section='D. 竞争格局')

# =====================================================================================
# D4 大排量赛道品牌格局
# =====================================================================================
bb = [r for r in M['big_displacement_brands']['data']
      if r['year'] == 2025 and r['indicator'] == '销售'][0]
top10 = bb['top15'][:10][::-1]
d4_names = [short_name(r['manufacturer']) for r in top10]
d4_data = []
for i, r in enumerate(top10):
    top5 = i >= (len(top10) - 5)
    d4_data.append({"value": r['share_pct'], "volume": r['volume'],
                    "itemStyle": {"color": C_EXPORT if top5 else C_DOM_L}})
add('d4_big_disp_brands',
    '大排量（>250ml）赛道品牌格局（2025）：CR5 高达 69.9%',
    '销售口径。红色为 CR5 成员（合计 69.9%），灰色为第 6–10 名',
    '图注：★ 与全行业 CR5 仅 36.9% 形成鲜明对比 —— 大排量赛道是一条"头部通吃"的赛道。'
    'CR5：春风动力 19.8%、大冶 18.1%、隆鑫 14.8%、钱江 11.9%、宗申 5.2%。'
    '赛道总量 2025 年销售 95.2 万辆。数据仅 2023-09 起可得；2023-12 生产口径数据缺失 97%（已用销售口径）；'
    '2026-07 品牌×排量明细不完整，故本图用 2025 完整年。',
    430,
    {
        "grid": {"left": 6, "right": 40, "top": 20, "bottom": 24, "containLabel": True},
        "tooltip": tooltip({"trigger": "item", "formatter": "{b}<br/>赛道销量份额 {c}%"}),
        "xAxis": value_axis('赛道份额 %', {"min": 0, "max": 22,
                                            "axisLabel": ax_label({"formatter": "{value}%"})}),
        "yAxis": cat_axis(d4_names, {"axisLabel": ax_label({"fontSize": 11}),
                                     "splitLine": {"show": False}}),
        "graphic": [{"type": "text", "right": 46, "top": 6,
                     "style": {"text": "CR5 = 69.9%（全行业仅 36.9%）",
                               "fill": C_EXPORT, "fontSize": 12, "fontWeight": "bold",
                               "fontFamily": FONT}}],
        "series": [
            {"name": "2025 年赛道份额", "type": "bar", "data": d4_data, "barMaxWidth": 18,
             "itemStyle": {"borderRadius": [0, 3, 3, 0]},
             "label": {"show": True, "position": "right", "formatter": "{c}%",
                       "color": "#6B7785", "fontSize": 10}}
        ]
    }, section='D. 竞争格局')

# =====================================================================================
# E1 季节性指数
# =====================================================================================
se = M['seasonality_index']['data']
e1_x = ["%d月" % r['month'] for r in se]
add('e1_seasonality',
    '月度季节性指数（年均 = 100）：9 月最高峰，2 月春节为绝对低点',
    '指数 = 该月产量 / 该年月均产量 × 100。已剔除 2016 / 2023 / 2026 非完整年份',
    '图注：全期指数 9 月 112（最高）、12 月 108、6–7 月 107；2 月仅 59，约为年均的六成（春节停工）。'
    '淡旺季格局十年间保持稳定：近期（2024–2025）与早期（2017–2019）各月差异多在 ±7 以内，'
    '仅 2 月（−6.9）与 7 月（+6.1）变化稍大。',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(e1_x, {"axisLabel": ax_label({"fontSize": 11})}),
        "yAxis": value_axis('指数（年均=100）', {"min": 40, "max": 125}),
        "series": [
            {"name": "全期指数", "type": "bar", "data": [r['index_all'] for r in se],
             "barMaxWidth": 30, "itemStyle": {"color": "#A9C0D8", "borderRadius": [3, 3, 0, 0]},
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 10},
             "markLine": {"silent": True, "symbol": "none",
                          "data": [{"yAxis": 100,
                                    "lineStyle": {"color": "#C9CDD4", "type": "dashed"},
                                    "label": {"formatter": "年均 100", "position": "insideEndTop",
                                              "color": "#9AA5B1", "fontSize": 10}}]}},
            {"name": "早期 2017–2019", "type": "line", "data": [r['index_2017_2019'] for r in se],
             "symbol": "circle", "symbolSize": 5,
             "lineStyle": {"width": 1.4, "color": C_GREY, "type": "dashed"},
             "itemStyle": {"color": C_GREY}},
            {"name": "近期 2024–2025", "type": "line", "data": [r['index_2024_2025'] for r in se],
             "symbol": "circle", "symbolSize": 5,
             "lineStyle": {"width": 2, "color": C_EXPORT}, "itemStyle": {"color": C_EXPORT}}
        ]
    }, section='E. 季节性与拐点')

# =====================================================================================
# E2 同比拐点
# =====================================================================================
tp = sorted(M['turning_points_yoy']['data'], key=lambda r: r['ym'])
e2_x = [r['ym'] for r in tp]
e2_data = [{"value": r['yoy_pct'],
            "itemStyle": {"color": C_UP if r['yoy_pct'] >= 0 else C_DOWN}} for r in tp]
add('e2_turning_points',
    '销量同比波动最大的月份（|YoY| 前 18）：疫情冲击与春节错位是主因',
    '柱：当月销量同比（%）。红＝同比增长，绿＝同比下降（中国市场惯例）',
    '图注：同比为与上年同月对比。2020-02 的 −60.6% 是疫情停工，2021-02 的 +221.6% 是 2020 年低基数叠加'
    '春节错位（2020 年春节在 1 月、2021 年在 2 月），属技术性波动而非真实景气变化。'
    '同理 2023-01 / 2023-02、2025-02 的大幅波动也主要来自春节错位。'
    '解读年度趋势请以全年口径（A2）为准，不要用单月同比下结论。',
    380,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 48, "containLabel": True},
        "tooltip": tooltip(),
        "xAxis": cat_axis(e2_x, {"axisLabel": ax_label({"rotate": 45, "interval": 0, "fontSize": 10})}),
        "yAxis": value_axis('销量同比 %', {"axisLabel": ax_label({"formatter": "{value}%"})}),
        "series": [
            {"name": "销量同比", "type": "bar", "data": e2_data, "barMaxWidth": 24,
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": "#6B7785", "fontSize": 9},
             "markLine": {"silent": True, "symbol": "none",
                          "data": [{"yAxis": 0, "lineStyle": {"color": "#B9C2CD", "width": 1}}]}}
        ]
    }, section='E. 季节性与拐点')

# =====================================================================================
# E3 大排量 1-7 月增速放缓信号
# =====================================================================================
yd = M['big_displacement_ytd_1_7']['data']
e3_x = ["%d年1-7月" % r['year'] for r in yd]
e3_v = [r['volume_wan'] for r in yd]
e3_y = [r['yoy_1_7_pct'] for r in yd]
add('e3_big_disp_slowdown',
    '风险信号：大排量赛道增速从 +38.0% 骤降至 +1.1%',
    '柱：1–7 月 >250ml 产量（万辆）；线：1–7 月同期同比（%）',
    '图注：这是 2026 年唯一同口径的增长序列。大排量 1–7 月同比 2024 年 +77.8% → 2025 年 +38.0% → '
    '2026 年 +1.1%，而同期行业整体产量 +14.9%（红色虚线）—— 大排量赛道的高速增长期在 2026 年明显放缓，'
    '占全行业比重也从 4.82% 回落至 4.24%。与"2026 年内销回暖 +8.0%"（B5）构成一正一反的两个新信号。',
    390,
    {
        "grid": {"left": 6, "right": 6, "top": 26, "bottom": 40, "containLabel": True},
        "legend": legend(bottom=0),
        "tooltip": tooltip(),
        "xAxis": cat_axis(e3_x, {"axisLabel": ax_label({"fontSize": 11})}),
        "yAxis": [value_axis('万辆', {"min": 0}),
                  value_axis('同期同比 %', {"min": 0, "max": 90, "splitLine": {"show": False},
                                            "axisLabel": ax_label({"formatter": "{value}%"})})],
        "series": [
            {"name": ">250ml 产量(1-7月)", "type": "bar",
             "data": [{"value": v, "itemStyle": {"color": C_EXPORT if i == 3 else "#EFA9A4"}}
                      for i, v in enumerate(e3_v)],
             "barMaxWidth": 52,
             "label": {"show": True, "position": "top", "formatter": "{c}",
                       "color": "#6B7785", "fontSize": 11}},
            {"name": "1–7 月同期同比", "type": "line", "yAxisIndex": 1, "data": e3_y,
             "symbol": "circle", "symbolSize": 8,
             "lineStyle": {"width": 2.4, "color": C_UP}, "itemStyle": {"color": C_UP},
             "label": {"show": True, "position": "top", "formatter": "{c}%",
                       "color": C_UP, "fontSize": 11, "fontWeight": "bold"},
             "markLine": {"silent": True, "symbol": "none",
                          "data": [{"yAxis": 14.9,
                                    "lineStyle": {"color": C_UP, "type": "dashed", "width": 1.4},
                                    "label": {"formatter": "行业整体 +14.9%", "position": "insideEndTop",
                                              "color": C_UP, "fontSize": 10}}]}}
        ]
    }, section='E. 季节性与拐点')

# ===================================================================================== 写出
os.makedirs(OUT, exist_ok=True)
js = io.StringIO()
js.write('/* ============================================================================\n')
js.write(' * 摩托车行业产销分析报告 —— 图表配置集（Phase2 交付物）\n')
js.write(' * 生成脚本：scripts/build_report_charts.py  数据源：output/analysis_metrics.json\n')
js.write(' * 用法：引入本文件后，window.REPORT_CHARTS 为图表数组；\n')
js.write(' *       每项含 {id, section, title, subtitle, caption, height, option}，\n')
js.write(' *       option 为完整 ECharts option，数据全部内联，无任何网络请求。\n')
js.write(' * 口径红线：2026=1-7月 / 出口 2020-2022 缺失 / 电动 2019 起 / 车型用 fuel_only / 品牌仅近 3 年\n')
js.write(' * ========================================================================== */\n')
js.write('window.REPORT_CHARTS = ')
js.write(json.dumps(CHARTS, ensure_ascii=False, indent=2))
js.write(';\n\nif (typeof module !== "undefined" && module.exports) { module.exports = window.REPORT_CHARTS; }\n')
with open(os.path.join(OUT, 'report_charts.js'), 'w', encoding='utf-8') as f:
    f.write(js.getvalue())

print('report_charts.js written, %d charts, %d chars' % (len(CHARTS), len(js.getvalue())))
for c in CHARTS:
    print('  -', c['id'], '|', c['title'])

# ------------------------------------------------------------------ preview html
sec_order = []
for c in CHARTS:
    if c['section'] not in sec_order:
        sec_order.append(c['section'])
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>报告图表预览 · 摩托车产销数据分析</title>
<script src="echarts.min.js"></script>
<style>
  :root{ --ink:#1F2937; --sub:#6B7785; --line:#E4E9F0; --bg:#F7F9FC; }
  *{ box-sizing:border-box; }
  body{ margin:0; padding:32px 24px 80px; background:var(--bg); color:var(--ink);
        font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif; }
  .wrap{ max-width:1080px; margin:0 auto; }
  h1{ font-size:24px; margin:0 0 6px; font-weight:700; letter-spacing:.5px; }
  .lead{ color:var(--sub); font-size:13px; margin-bottom:28px; line-height:1.7; }
  .sec{ margin:36px 0 14px; font-size:15px; font-weight:700; color:#3A6EA5;
        border-left:4px solid #3A6EA5; padding-left:10px; }
  .card{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:22px 24px 18px;
         margin-bottom:22px; box-shadow:0 1px 3px rgba(31,41,55,.04); }
  .cid{ font-size:11px; color:#9AA5B1; letter-spacing:1px; text-transform:uppercase; margin-bottom:6px; }
  .ct{ font-size:17px; font-weight:700; margin:0 0 4px; line-height:1.45; }
  .cs{ font-size:13px; color:var(--sub); margin:0 0 14px; }
  .chart{ width:100%; }
  .cap{ margin-top:12px; padding-top:12px; border-top:1px dashed var(--line);
        font-size:12px; color:#6B7785; line-height:1.75; }
  .err{ color:#C0392B; font-size:13px; padding:20px; background:#FDF2F1; border-radius:6px; }
  .stat{ font-size:12px; color:#9AA5B1; margin-top:4px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>摩托车行业产销分析报告 · 图表预览</h1>
  <div class="lead">
    共 __N__ 张图表，对应 5 条故事线。数据全部内联，无网络请求。<br>
    口径红线：2026 年仅 1–7 月（浅色/显式标注）· 出口数据 2020–2022 缺失（已断开）· 电动摩托车从 2019 年起 · 车型结构用剔除电动口径 · 品牌结论仅限近 3 年。
  </div>
  <div id="root"></div>
</div>
<script src="report_charts.js"></script>
<script>
(function(){
  var charts = window.REPORT_CHARTS || [];
  var root = document.getElementById('root');
  var lastSec = '';
  var ok = 0, bad = 0;
  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  charts.forEach(function(c, i){
    if (c.section && c.section !== lastSec) {
      lastSec = c.section;
      var h = document.createElement('div');
      h.className = 'sec'; h.textContent = c.section;
      root.appendChild(h);
    }
    var card = document.createElement('div'); card.className = 'card';
    card.innerHTML =
      '<div class="cid">' + esc(c.id) + '</div>' +
      '<div class="ct">' + esc(c.title) + '</div>' +
      '<div class="cs">' + esc(c.subtitle || '') + '</div>' +
      '<div class="chart" id="c_' + esc(c.id) + '" style="height:' + (c.height||400) + 'px"></div>' +
      '<div class="cap">' + esc(c.caption || '') + '</div>';
    root.appendChild(card);
    try {
      var el = document.getElementById('c_' + c.id);
      var inst = echarts.init(el, null, {renderer:'canvas'});
      inst.setOption(c.option, true);
      ok++;
      window.addEventListener('resize', function(){ inst.resize(); });
    } catch(e) {
      bad++;
      var el2 = document.getElementById('c_' + c.id);
      if (el2) el2.innerHTML = '<div class="err">渲染失败：' + (e && e.message ? e.message : e) + '</div>';
      console.error('[chart error]', c.id, e);
    }
  });
  var s = document.createElement('div');
  s.className = 'stat';
  s.textContent = '渲染完成：成功 ' + ok + ' / 失败 ' + bad + ' / 共 ' + charts.length;
  root.insertBefore(s, root.firstChild);
})();
</script>
</body>
</html>
""".replace('__N__', str(len(CHARTS)))
with open(os.path.join(OUT, 'report_charts_preview.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print('report_charts_preview.html written')
