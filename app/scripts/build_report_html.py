# -*- coding: utf-8 -*-
"""
build_report_html.py
====================
组装自包含的单文件 HTML 分析报告（Phase3 交付物）。

输入：
  output/echarts.min.js      —— ECharts 5 库（内联）
  output/report_charts.js    —— window.REPORT_CHARTS 图表配置集（内联）
输出：
  output/摩托车产销数据分析报告.html   —— 完全自包含，可双击打开 / 打印为 PDF

作者：智数分析专家团 · 洞察报告撰写师 若溪（Rex）
"""
import os
import sys
import datetime
import io

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")
SRC_ECHARTS = os.path.join(OUT, "echarts.min.js")
SRC_CHARTS = os.path.join(OUT, "report_charts.js")
DST = os.path.join(OUT, "摩托车产销数据分析报告.html")

GEN_DATE = datetime.date.today().strftime("%Y-%m-%d")

# ----------------------------------------------------------------------------
# HTML 模板（图表以 <div class="chart-slot" data-chart="id" data-fig="图 X"> 占位，
# 由页面底部的 JS 从 window.REPORT_CHARTS 取出并渲染）
# ----------------------------------------------------------------------------
HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国摩托车行业产销数据分析报告（2016.02–2026.07）</title>
<style>
:root{
  --ink:#1B2733; --ink2:#44515F; --ink3:#7A8794;
  --line:#E4E8ED; --line2:#EFF2F5;
  --bg:#F4F6F8; --card:#FFFFFF;
  --navy:#16375C; --navy2:#245C92; --navy-soft:#EEF3F9;
  --teal:#0E7C7B; --gold:#A8760B; --red:#B23A2E; --green:#2E7D4F;
  --serif: Georgia,"Times New Roman","Songti SC","Noto Serif SC","Source Han Serif SC",serif;
  --sans: -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:var(--sans); font-size:15px; line-height:1.8;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px;margin:0 auto;padding:0 28px}

/* ---------- 顶部导航 ---------- */
.topnav{
  position:sticky; top:0; z-index:100;
  background:rgba(255,255,255,.94); backdrop-filter:saturate(180%) blur(8px);
  border-bottom:1px solid var(--line);
}
.topnav-inner{max-width:1080px;margin:0 auto;padding:0 28px;display:flex;align-items:center;gap:4px;height:50px;overflow-x:auto}
.topnav .brand{font-family:var(--serif);font-weight:700;color:var(--navy);font-size:14.5px;margin-right:14px;white-space:nowrap;letter-spacing:.02em}
.topnav a{
  color:var(--ink2); text-decoration:none; font-size:13px; padding:5px 9px; border-radius:5px;
  white-space:nowrap; transition:background .15s,color .15s;
}
.topnav a:hover{background:var(--navy-soft); color:var(--navy)}
.topnav .spacer{flex:1}
.btn-print{
  border:1px solid var(--line); background:#fff; color:var(--ink2); font-size:12.5px;
  padding:5px 12px; border-radius:5px; cursor:pointer; font-family:var(--sans); white-space:nowrap;
}
.btn-print:hover{border-color:var(--navy2); color:var(--navy)}

/* ---------- 封面 ---------- */
.cover{
  background:linear-gradient(155deg,#16375C 0%,#1E4E7C 52%,#245C92 100%);
  color:#fff; padding:64px 0 54px; position:relative; overflow:hidden;
}
.cover:after{
  content:""; position:absolute; right:-90px; top:-70px; width:340px; height:340px;
  border-radius:50%; background:rgba(255,255,255,.05);
}
.cover .wrap{position:relative;z-index:1}
.cover .kicker{
  font-size:12px; letter-spacing:.24em; text-transform:uppercase;
  color:#A9C6E4; margin-bottom:20px; font-weight:600;
}
.cover h1{
  font-family:var(--serif); font-size:40px; line-height:1.28; margin:0 0 14px;
  font-weight:700; letter-spacing:.01em;
}
.cover .h1-en{
  font-family:var(--serif); font-size:16px; color:#BFD6EE; font-style:italic;
  margin:0 0 26px; font-weight:400; letter-spacing:.01em;
}
.cover .lede{
  font-size:15.5px; color:#DCE8F5; max-width:760px; line-height:1.85; margin:0 0 30px;
}
.cover-meta{display:flex;flex-wrap:wrap;gap:10px}
.cover-meta span{
  background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.2);
  padding:6px 13px; border-radius:999px; font-size:12.5px; color:#EAF2FA;
}

/* ---------- 章节 ---------- */
section{padding:52px 0 8px}
.sec-head{border-bottom:2px solid var(--navy); padding-bottom:12px; margin-bottom:8px}
.sec-num{
  display:inline-block; font-family:var(--serif); font-size:12.5px; letter-spacing:.16em;
  color:var(--gold); font-weight:700; margin-bottom:6px;
}
.sec-head h2{
  font-family:var(--serif); font-size:27px; margin:0; color:var(--navy);
  font-weight:700; line-height:1.35;
}
.sec-head .h2-en{
  font-family:var(--serif); font-style:italic; color:var(--ink3);
  font-size:13.5px; margin-top:4px; font-weight:400;
}
h3{
  font-family:var(--serif); font-size:19px; color:var(--navy); margin:34px 0 10px;
  font-weight:700; line-height:1.5;
}
h3 .h3-en{font-family:var(--serif); font-style:italic; font-weight:400; font-size:13px; color:var(--ink3); margin-left:8px}
h4{font-size:15.5px; color:var(--ink); margin:22px 0 8px; font-weight:700}
p{margin:0 0 14px; color:var(--ink2)}
strong{color:var(--ink); font-weight:700}
em{font-style:normal; color:var(--navy2); font-weight:600}
a{color:var(--navy2)}
ul,ol{margin:0 0 16px; padding-left:22px; color:var(--ink2)}
li{margin-bottom:7px}
.lead{font-size:16px; color:var(--ink2); line-height:1.9}

/* ---------- 卡片 ---------- */
.card{
  background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:22px 24px; margin:18px 0;
}
.card.tight{padding:16px 20px}

/* KPI */
.kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0 8px}
.kpi{
  background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:16px 18px; border-top:3px solid var(--navy2);
}
.kpi.warn{border-top-color:var(--red)}
.kpi.good{border-top-color:var(--green)}
.kpi.gold{border-top-color:var(--gold)}
.kpi .k-label{font-size:12px;color:var(--ink3);margin-bottom:6px;letter-spacing:.02em}
.kpi .k-value{font-family:var(--serif);font-size:27px;line-height:1.15;color:var(--navy);font-weight:700}
.kpi .k-value small{font-size:14px;font-weight:600;color:var(--ink2);margin-left:3px}
.kpi .k-note{font-size:12px;color:var(--ink3);margin-top:7px;line-height:1.6}

/* 要点列表 */
.finding{
  background:var(--card); border:1px solid var(--line); border-left:3px solid var(--navy2);
  border-radius:8px; padding:18px 22px; margin:14px 0;
}
.finding.warn{border-left-color:var(--red)}
.finding.good{border-left-color:var(--green)}
.finding .f-no{
  font-family:var(--serif); font-size:12px; font-weight:700; color:var(--gold);
  letter-spacing:.1em; display:block; margin-bottom:5px;
}
.finding .f-title{font-size:16px;font-weight:700;color:var(--ink);display:block;margin-bottom:7px;line-height:1.55}
.finding p{margin:0;font-size:14.5px}

/* 提示框 */
.callout{
  border-radius:8px; padding:15px 19px; margin:18px 0; font-size:14px; line-height:1.8;
  border:1px solid; background:#FFFDF6; border-color:#EBDFB8; color:#6B5518;
}
.callout .c-t{font-weight:700;display:block;margin-bottom:5px;color:#8A6A0B}
.callout.info{background:var(--navy-soft);border-color:#D3E0EE;color:#2B4A6B}
.callout.info .c-t{color:var(--navy)}
.callout.danger{background:#FDF4F3;border-color:#F0D5D1;color:#7C3128}
.callout.danger .c-t{color:var(--red)}
.callout p{margin:6px 0 0;color:inherit}

/* ---------- 表格 ---------- */
.table-scroll{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:#fff}
table th{
  background:#F7F9FB; color:var(--navy); font-weight:700; text-align:right;
  padding:10px 12px; border-bottom:1.5px solid var(--line); white-space:nowrap; font-size:12.5px;
}
table th:first-child,table td:first-child{text-align:left}
table td{padding:9px 12px;border-bottom:1px solid var(--line2);text-align:right;color:var(--ink2);white-space:nowrap}
table tbody tr:hover{background:#FAFCFE}
table tr.hl td{background:#FFFBF0}
table tr.tot td{font-weight:700;color:var(--ink);background:#F7F9FB;border-top:1.5px solid var(--line)}
table .warn-y{color:var(--gold);font-weight:600}
table .neg{color:var(--red);font-weight:600}
table .pos{color:var(--green);font-weight:600}
table caption{
  caption-side:bottom; text-align:left; font-size:12px; color:var(--ink3);
  padding-top:9px; line-height:1.7;
}

/* ---------- 图表 ---------- */
.chart-figure{
  background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:20px 22px 16px; margin:22px 0;
}
.chart-head{margin-bottom:12px;border-bottom:1px solid var(--line2);padding-bottom:11px}
.chart-no{
  display:inline-block;font-family:var(--serif);font-size:11.5px;font-weight:700;color:#fff;
  background:var(--navy2);padding:2px 9px;border-radius:4px;letter-spacing:.06em;margin-bottom:7px;
}
.chart-title{font-family:var(--serif);font-size:17px;margin:0 0 4px;color:var(--navy);font-weight:700;line-height:1.5}
.chart-sub{font-size:12.5px;color:var(--ink3);margin:0;line-height:1.65}
.chart-canvas{width:100%}
.chart-caption{
  margin:12px 0 0; padding:11px 14px; background:#F7F9FB; border-left:3px solid var(--gold);
  border-radius:0 6px 6px 0; font-size:12.5px; color:var(--ink2); line-height:1.8;
}
.chart-missing{padding:20px;border:1px dashed var(--red);color:var(--red);border-radius:8px;font-size:13px}

/* ---------- 建议 ---------- */
.adv{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px 22px;margin:16px 0}
.adv .a-head{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px;flex-wrap:wrap}
.adv .a-tag{
  font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:4px;color:#fff;
  background:var(--navy2);white-space:nowrap;letter-spacing:.04em;
}
.adv .a-tag.product{background:var(--navy2)}
.adv .a-tag.market{background:var(--teal)}
.adv .a-tag.strategy{background:#6B4E9B}
.adv .a-tag.risk{background:var(--red)}
.adv .a-title{font-family:var(--serif);font-size:17px;font-weight:700;color:var(--ink);flex:1;min-width:240px;line-height:1.5}
.adv dl{display:grid;grid-template-columns:76px 1fr;gap:6px 12px;margin:0;font-size:14px}
.adv dt{color:var(--ink3);font-size:12.5px;padding-top:2px;font-weight:600}
.adv dd{margin:0;color:var(--ink2);line-height:1.8}
.adv .prio{font-size:12px;font-weight:700;padding:2px 9px;border-radius:4px;white-space:nowrap}
.prio.high{background:#FDECEA;color:var(--red);border:1px solid #F3C9C3}
.prio.mid{background:#FFF7E3;color:var(--gold);border:1px solid #EDDCB0}

/* ---------- 页脚 ---------- */
footer{
  margin-top:56px; padding:30px 0 46px; border-top:1px solid var(--line);
  font-size:12.5px; color:var(--ink3); line-height:1.85;
}
footer strong{color:var(--ink2)}

/* ---------- 响应式 ---------- */
@media (max-width:820px){
  .kpi-grid{grid-template-columns:repeat(2,1fr)}
  .cover h1{font-size:29px}
  .wrap{padding:0 18px}
  .topnav-inner{padding:0 18px}
  .adv dl{grid-template-columns:1fr}
}

/* ---------- 打印 ---------- */
@media print{
  @page{ size:A4; margin:13mm 12mm; }
  html,body{background:#fff;font-size:10.4pt;line-height:1.65}
  .topnav{display:none!important}
  .wrap{max-width:100%;padding:0}
  .cover{background:#16375C!important;-webkit-print-color-adjust:exact;print-color-adjust:exact;padding:26mm 0 16mm}
  .cover h1{font-size:25pt}
  .cover .lede{font-size:10.5pt;color:#DCE8F5}
  section{padding:14px 0 4px;break-inside:auto}
  .sec-head{break-after:avoid;page-break-after:avoid}
  h3,h4{break-after:avoid;page-break-after:avoid}
  .card,.kpi,.finding,.adv,.callout,.chart-figure,.table-scroll,table,figure{
    break-inside:avoid;page-break-inside:avoid;
  }
  .chart-figure{padding:10px 0 8px;border:0;border-top:1px solid #DDD;border-radius:0}
  .chart-canvas{height:auto!important;break-inside:avoid;page-break-inside:avoid}
  .chart-canvas>div{break-inside:avoid;page-break-inside:avoid}
  .chart-canvas canvas{width:100%!important;max-width:100%!important;height:auto!important}
  .chart-caption{background:#F6F7F9!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .kpi{border-top-width:2px}
  .kpi,.finding,.adv,.card{border-color:#D8DDE3}
  a{color:inherit;text-decoration:none}
  footer{margin-top:20px;font-size:9pt}
  table{font-size:9.2pt}
  table th{background:#F2F4F7!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
</style>
</head>
<body>

<nav class="topnav">
  <div class="topnav-inner">
    <span class="brand">摩托车产销分析报告</span>
    <a href="#summary">执行摘要</a>
    <a href="#method">数据与方法</a>
    <a href="#s1">§1 总量与增长</a>
    <a href="#s2">§2 出口 vs 内销</a>
    <a href="#s3">§3 排量与车型</a>
    <a href="#s4">§4 竞争格局</a>
    <a href="#s5">§5 2026 新信号</a>
    <a href="#advice">结论与建议</a>
    <a href="#appendix">附录</a>
    <span class="spacer"></span>
    <button class="btn-print" onclick="window.print()">打印 / 存为 PDF</button>
  </div>
</nav>

<!-- ============================ 封面 ============================ -->
<header class="cover" id="cover">
  <div class="wrap">
    <div class="kicker">China Motorcycle Industry &nbsp;·&nbsp; Production &amp; Sales Analytics</div>
    <h1>中国摩托车行业产销数据分析报告</h1>
    <p class="h1-en">Production &amp; Sales Analysis Report, 2016.02 – 2026.07</p>
    <p class="lede">
      基于 122 个月行业级产销数据，回答一个问题：当总量创下十年新高、而增长几乎全部来自海外时，
      这个行业正在发生什么，身处其中的企业应该怎么办。
      本报告覆盖总量增长、出口与内销的结构性位移、排量与车型的消费升级、竞争格局的分化，
      以及 2026 年最新出现的两个方向相反的信号。
    </p>
    <div class="cover-meta">
      <span>数据覆盖：2016.02 – 2026.07（122 个月）</span>
      <span>累计产销：1.919 亿辆 / 1.911 亿辆</span>
      <span>21 张图表 · 35 个指标集</span>
      <span>生成日期：__GEN_DATE__</span>
    </div>
  </div>
</header>

<!-- ============================ 执行摘要 ============================ -->
<section id="summary">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">EXECUTIVE SUMMARY</span>
      <h2>执行摘要<span class="h2-en" style="font-style:italic"></span></h2>
      <div class="h2-en">Executive Summary — 高管只需读这一节</div>
    </div>

    <p class="lead">
      2026 年的中国摩托车行业交出了一份"总量创十年新高"的成绩单：2025 年产量 <strong>2,195.0 万辆</strong>、
      销量 <strong>2,180.4 万辆</strong>，均为 2016 年以来最高。但只要把销量拆成内销与出口两部分，
      这幅图景的性质立刻改变——<strong>行业的增长已不再由国内需求驱动，而是由海外订单驱动</strong>。
      这不是周期性波动，而是一次结构性位移。
    </p>

    <div class="kpi-grid">
      <div class="kpi">
        <div class="k-label">2025 年产量（十年新高）</div>
        <div class="k-value">2,195.0<small>万辆</small></div>
        <div class="k-note">同比 +10.3%（可比年份口径）</div>
      </div>
      <div class="kpi warn">
        <div class="k-label">2025 年内销</div>
        <div class="k-value">852.2<small>万辆</small></div>
        <div class="k-note">同比 −4.4%，连续萎缩</div>
      </div>
      <div class="kpi good">
        <div class="k-label">2025 年出口</div>
        <div class="k-value">1,328.2<small>万辆</small></div>
        <div class="k-note">同比 +21.5%，外销率 60.9%</div>
      </div>
      <div class="kpi warn">
        <div class="k-label">2026 年 1–7 月外销率</div>
        <div class="k-value">63.0<small>%</small></div>
        <div class="k-note">2024 年 55.1% → 2025 年 60.9% → 63.0%</div>
      </div>
      <div class="kpi gold">
        <div class="k-label">&gt;250ml 占二轮比重</div>
        <div class="k-value">5.6<small>%（2025）</small></div>
        <div class="k-note">2016 年仅 0.33%，约 17 倍</div>
      </div>
      <div class="kpi">
        <div class="k-label">行业销量 CR5（2025）</div>
        <div class="k-value">36.9<small>%</small></div>
        <div class="k-note">2024 年 38.1%，不升反降；89 家在产</div>
      </div>
    </div>

    <div class="finding warn">
      <span class="f-no">01 &nbsp;·&nbsp; 最重要的判断</span>
      <span class="f-title">增长的 100% 来自出口，内需实际在萎缩</span>
      <p>
        2025 年销量较 2024 年净增 <strong>195.3 万辆</strong>，而同期出口净增 <strong>234.6 万辆</strong>——
        出口增量已经超过销量总增量。这意味着内销不仅没有贡献，反而是负贡献：内销从 891.5 万辆降至
        <strong>852.2 万辆（−4.4%）</strong>。外销率从 2024 年的 55.1% 升至 2025 年的 60.9%，
        2026 年 1–7 月进一步升至 <strong>63.0%</strong>。行业已从内需驱动转为出口驱动。
      </p>
    </div>

    <div class="finding">
      <span class="f-no">02</span>
      <span class="f-title">这是低速稳健增长，不是爆发式增长</span>
      <p>
        以完整年份计算的 2017→2025 年复合增速，产量 <strong>CAGR 仅 3.14%</strong>、销量 3.07%；
        2019–2026 年的线性趋势为每年 +7.7 万辆，相对 2,000 万辆级的基数不足 0.4%。
        2025 年 +10.3% 的高增速带有 2022–2023 年低基数的修复性质，不宜简单外推。
      </p>
    </div>

    <div class="finding">
      <span class="f-no">03 &nbsp;·&nbsp; 最具价值的结构性机会</span>
      <span class="f-title">燃油车正在发生十年尺度上最确定的一次排量升级</span>
      <p>
        剔除电动摩托车后，二轮燃油车中 <strong>≤110ml 份额从 30.1% 腰斩至 17.4%</strong>；
        125-150ml 从 22.6% 升至 29.0%；150-250ml 从 5.7% 升至 12.0%；
        <strong>&gt;250ml 从 0.33% 升至 5.6%（约 17 倍）</strong>。三个中高排量段的份额十年间全部翻倍以上。
      </p>
    </div>

    <div class="finding">
      <span class="f-no">04 &nbsp;·&nbsp; 反直觉结论</span>
      <span class="f-title">大排量是内需故事，不是出口故事</span>
      <p>
        同口径对比下，出口与内销的排量结构<strong>高度同构</strong>，各段差异均在 ±2.1pp 以内；
        出口在 150-250ml 段高出约 2.0pp，但在 <strong>&gt;250ml 段反而比内销低 1.3pp</strong>。
        因此大排量的增长主要由国内消费升级驱动；出口的升级主要体现在单车均价
        （2025 年 <strong>709.1 美元，+11.5%</strong>）而非排量段跃迁。
      </p>
    </div>

    <div class="finding">
      <span class="f-no">05</span>
      <span class="f-title">电动摩托车的"暴跌"不是失败，是抢装后的正常回归</span>
      <p>
        2019 年 177.7 万辆起步，2022 年在新国标过渡期抢装下冲至 <strong>542.2 万辆（占二轮 30.6%）</strong>，
        随后两年回落六成至 2024 年 219.6 万辆，2025 年企稳在 <strong>226.5 万辆</strong>
        （占二轮 11.7%，同比 +3.1%）。11%–12% 才是这一品类更可持续的稳态水平，
        不应把 2022 年的峰值当作基准来评判 2025 年的表现。
      </p>
    </div>

    <div class="finding">
      <span class="f-no">06</span>
      <span class="f-title">分散的行业，集中的赛道</span>
      <p>
        全行业销量 CR5 从 2024 年的 38.1% <strong>降至</strong> 2025 年的 36.9%（不升反降），CR10 约 53.5%，
        89 家企业在产，行业远未形成寡头；但 <strong>&gt;250ml 大排量赛道 CR5 高达 69.9%</strong>，
        电动摩托车赛道 CR5 达 76.3%。这八个字是当前格局最准确的概括。
      </p>
    </div>

    <div class="finding good">
      <span class="f-no">07 &nbsp;·&nbsp; 2026 年的正面信号</span>
      <span class="f-title">内销回暖 +8.0%，为 2021 年以来首次同期转正</span>
      <p>
        2026 年 1–7 月内销 <strong>528.6 万辆，同比 +8.0%</strong>（2025 年同期为 −5.5%），
        同期出口 +18.6%、总销量 +14.4%。这是积极信号，但只有<strong>一个 1–7 月窗口</strong>，
        且外销率仍在上升（60.8% → 63.0%），回暖只是"增速转正"，并未改变出口主导的格局。
      </p>
    </div>

    <div class="finding warn">
      <span class="f-no">08 &nbsp;·&nbsp; 2026 年的风险信号</span>
      <span class="f-title">大排量赛道增速从 +38.0% 骤降至 +1.1%</span>
      <p>
        1–7 月 &gt;250ml 产量 60.8 万辆，同比仅 <strong>+1.1%</strong>——远低于 2025 年同期的 +38.0%，
        也显著跑输行业整体的 +14.9%；占全行业比重从 4.82% 回落至 4.24%。
        "大排量将保持 30%+ 增长"的假设在 2026 年已经不成立，这是本报告提示的首要风险。
      </p>
    </div>

    <div class="callout info">
      <span class="c-t">补充：行业没有库存压力，总量数据可信度高</span>
      <p>
        全周期累计产销率 <strong>99.56%</strong>，至 2025 年末累计产销差仅 78.2 万辆
        （不足 2025 年产量的 3.6%）。行业长期"以销定产"，产量与销量互为镜像，
        因此本报告基于销量口径的结构拆解与基于生产口径的排量/车型结构具备一致性。
      </p>
    </div>

    <h3 style="margin-top:30px">结论图：增长几乎全部来自海外 <span class="h3-en">The Conclusion Chart</span></h3>
    <div class="chart-slot" data-chart="b1_domestic_export_split" data-fig="图 1"></div>
  </div>
</section>

<!-- ============================ 数据说明与方法 ============================ -->
<section id="method">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">DATA &amp; METHODOLOGY</span>
      <h2>数据说明与方法</h2>
      <div class="h2-en">Data Sources, Coverage and Known Limitations</div>
    </div>

    <p>
      本报告的数据来自两个在 2023 年 9 月前后衔接的官方口径来源。二者粒度不同，
      这直接决定了"哪些结论可以说、能说到什么程度"。以下口径说明请先读，再读正文——
      其中若干条会直接改变结论的解读方式。
    </p>

    <div class="table-scroll">
      <table>
        <thead>
          <tr><th>数据区间</th><th>来源</th><th>粒度</th><th>月份数</th></tr>
        </thead>
        <tbody>
          <tr><td>2016-02 ~ 2023-08</td><td style="text-align:left">《摩托车情报》月刊 PDF（数字化抽取）</td><td style="text-align:left">汇总级：总量 / 分排量 / 分车型</td><td>87</td></tr>
          <tr><td>2023-09 ~ 2026-07</td><td style="text-align:left">《全国摩托车生产企业产销情况月报》Excel</td><td style="text-align:left">全维度：含品牌 × 排量交叉</td><td>35</td></tr>
        </tbody>
      </table>
    </div>

    <h3>八条口径红线 <span class="h3-en">Eight Caliber Red Lines</span></h3>
    <p>
      以下八条是本次分析中被反复验证的"易错点"。违反任何一条都会得出错误结论，
      因此正文与图注中均已显式标注。
    </p>

    <div class="card tight">
      <ol style="margin-bottom:0">
        <li><strong>2026 年只有 1–7 月。</strong>凡涉及 2026 年的表述均写明"1–7 月"，不与完整年份并列比较绝对量。2026 年唯一的合法同比口径是"1–7 月 vs 上年同期"。</li>
        <li><strong>出口数据 2020–2022 年完全缺失。</strong>源报表当年取消了分排量出口表，因此出口年度序列在此断开。出口结论只能分别在"2016–2019"与"2023.09 起"两个窗口内表述，<strong>2019→2023 的变化不可解读为增长或下滑</strong>。图中已用断点处理。</li>
        <li><strong>电动化结论只使用 2019 年起的数据。</strong>2016–2018 年电动摩托车仅 6.1 / 9.9 / 10.2 万辆，2019 年突然跃至 177.7 万辆，判定为 2019 年新国标实施后的统计口径变更，属数量级断层而非真实增长。</li>
        <li><strong>年度同比只有 2018 / 2019 / 2020 / 2021 / 2022 / 2025 六个年份可比。</strong>2016（8 个月）、2023（11 个月）、2024（对比 2023 不完整）、2026（7 个月）的年度同比一律不可引用。特别提示：<em>"2024 年同比 +12.6%"是错误的，本报告从不使用</em>。同理，2016→2017 的 +53.9% 也是口径假象。</li>
        <li><strong>车型结构必须使用"剔除电动"的口径。</strong>电动摩托车在分车型表中 100% 计入"踏板式"（已交叉验证各年踏板式产量恒 ≥ 电动产量）。含电动的口径会得出"踏板车份额暴涨至 49%"的假象，真实情况是燃油踏板 23.3% → 20.0%（略降）。</li>
        <li><strong>三轮车排量数据覆盖率仅约 53%。</strong>2025 年三轮产量 265.2 万辆，分排量表仅覆盖 141.2 万辆，缺口 124.0 万辆（应为电动三轮车未纳入）。因此本报告<strong>不出三轮排量结构结论</strong>，三轮一律使用分车型表口径。</li>
        <li><strong>品牌类结论只能说"近 3 年"。</strong>品牌明细仅覆盖 2023.09–2026.07 共 35 个月，PDF 历史数据无品牌明细。任何"十年格局变化"的表述都是不成立的。此外 2023 年 12 月品牌产量缺失 97%，2023 年生产口径的品牌指标已剔除。</li>
        <li><strong>2016 年与 2023 年不是完整年份。</strong>2016 年仅 8 个月（1,113.7 万辆）、2023 年仅 11 个月。所有增长率与 CAGR 均以 2017 年为起点计算。</li>
      </ol>
    </div>

    <h3>交叉校验结果 <span class="h3-en">Cross-validation</span></h3>
    <div class="table-scroll">
      <table>
        <thead><tr><th>校验项</th><th style="text-align:left">结果</th><th>状态</th></tr></thead>
        <tbody>
          <tr><td>月度总量 vs 分车型合计</td><td style="text-align:left">完全一致（0 个月偏差 &gt; 0.5%）</td><td class="pos">PASS</td></tr>
          <tr><td>二轮分车型合计 vs 二轮分排量合计</td><td style="text-align:left">完全一致</td><td class="pos">PASS</td></tr>
          <tr><td>年度总量 vs 月度汇总</td><td style="text-align:left">偏差 0.00%</td><td class="pos">PASS</td></tr>
          <tr><td>出口总量 vs 出口明细"总计"</td><td style="text-align:left">63 个月零偏差</td><td class="pos">PASS</td></tr>
          <tr><td>品牌月度合计 vs 月度总量</td><td style="text-align:left">除 2023-12 生产外全部一致</td><td class="pos">PASS（1 例外）</td></tr>
          <tr><td>三轮分排量合计 vs 三轮分车型合计</td><td style="text-align:left">覆盖率约 53%，系统性缺口</td><td class="neg">FAIL</td></tr>
          <tr><td>全行业分排量合计 vs 总量</td><td style="text-align:left">2023-09 起低 5%~8%，差异 100% 来自三轮</td><td class="warn-y">WARN</td></tr>
        </tbody>
      </table>
    </div>

    <h3>分析口径定义 <span class="h3-en">Definitions</span></h3>
    <ul>
      <li><strong>内销</strong>：本报告定义为「销量 − 出口」。出口表与销量表已通过 63 个月零偏差的交叉校验，拆分结果可信。</li>
      <li><strong>外销率</strong>：出口量 ÷ 当期销量。注意分母是销量而非产量。</li>
      <li><strong>排量结构</strong>：统一映射为 ≤110 / 110-125 / 125-150 / 150-250 / &gt;250ml / 电动 六个分组，把 2016–2022 的合并段与 2023 年起的细分段对齐，从而实现跨年可比。细分段（如 500-800ml）仅 2023 年后可用。</li>
      <li><strong>燃油口径</strong>：指剔除电动摩托车后的二轮车，分母为燃油二轮总量。这是观察"排量升级"最干净的口径。</li>
      <li><strong>CR5 / CR10</strong>：前 5 家 / 前 10 家企业销量（或出口量）占全行业比重。HHI 为赫芬达尔指数（按份额的万分比计）。</li>
    </ul>
  </div>
</section>

<!-- ============================ §1 总量与增长 ============================ -->
<section id="s1">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">SECTION 01</span>
      <h2>总量与增长：十年全景</h2>
      <div class="h2-en">Aggregate Volume &amp; Growth: A Ten-Year Panorama</div>
    </div>

    <p>
      2016 年 2 月至 2026 年 7 月，行业累计生产 <strong>1.919 亿辆</strong>、累计销售 <strong>1.911 亿辆</strong>。
      十年间总量从 1,100 万辆量级走到 2,200 万辆量级，但这条路不是一条直线——它由三个台阶、
      两次回落和一轮尚未结束的上行周期组成。
    </p>

    <div class="chart-slot" data-chart="a1_monthly_trend" data-fig="图 2"></div>

    <h3>1.1 三个台阶与两次回落 <span class="h3-en">Three Steps, Two Setbacks</span></h3>
    <p>
      第一个台阶是 2017 年：全年产量 1,714.0 万辆，这是数据序列中第一个完整年份，
      也是后续所有增长率与 CAGR 的基准。2018 年小幅回落至 1,553.4 万辆（−9.4%，可比）。
      第二个台阶是 2021 年：产量 2,011.7 万辆，同比 <strong>+18.3%</strong>，为十年最高增速——
      这背后既有疫情后海外需求的集中释放，也有国内通勤需求的脉冲。
      第三个台阶是 2025 年：产量 2,195.0 万辆，同比 <strong>+10.3%</strong>，
      在 2022 年（−0.8%）、2023 年（11 个月口径）连续两年走弱之后重新加速。
    </p>

    <div class="chart-slot" data-chart="a2_yearly_prod_sales" data-fig="图 3"></div>

    <div class="table-scroll">
      <table>
        <caption>注：⚠️ 为非完整年份。同比列仅在本年与上年均为完整年时给出（可比年份：2018/2019/2020/2021/2022/2025）；其余年份已在数据中置空，切勿插值或口算。</caption>
        <thead>
          <tr><th>年份</th><th>覆盖月数</th><th>产量(万辆)</th><th>销量(万辆)</th><th>产量 YoY</th><th>销量 YoY</th><th>产销率</th></tr>
        </thead>
        <tbody>
          <tr><td>2016 ⚠️</td><td>8</td><td>1,113.7</td><td>1,105.1</td><td>—</td><td>—</td><td>99.2%</td></tr>
          <tr><td>2017</td><td>12</td><td>1,714.0</td><td>1,712.5</td><td>—</td><td>—</td><td>99.9%</td></tr>
          <tr><td>2018</td><td>12</td><td>1,553.4</td><td>1,553.1</td><td class="neg">−9.4%</td><td class="neg">−9.3%</td><td>100.0%</td></tr>
          <tr><td>2019</td><td>12</td><td>1,718.3</td><td>1,693.8</td><td class="pos">+10.6%</td><td class="pos">+9.1%</td><td>98.6%</td></tr>
          <tr><td>2020</td><td>12</td><td>1,700.3</td><td>1,706.9</td><td class="neg">−1.0%</td><td class="pos">+0.8%</td><td>100.4%</td></tr>
          <tr><td>2021</td><td>12</td><td>2,011.7</td><td>2,009.7</td><td class="pos">+18.3%</td><td class="pos">+17.7%</td><td>99.9%</td></tr>
          <tr><td>2022</td><td>12</td><td>1,996.1</td><td>2,006.1</td><td class="neg">−0.8%</td><td class="neg">−0.2%</td><td>100.5%</td></tr>
          <tr><td>2023 ⚠️</td><td>11</td><td>1,767.2</td><td>1,729.6</td><td>—</td><td>—</td><td>97.9%</td></tr>
          <tr><td>2024</td><td>12</td><td>1,990.7</td><td>1,985.1</td><td>—</td><td>—</td><td>99.7%</td></tr>
          <tr class="hl"><td>2025</td><td>12</td><td>2,195.0</td><td>2,180.4</td><td class="pos">+10.3%</td><td class="pos">+9.8%</td><td>99.3%</td></tr>
          <tr><td>2026 ⚠️</td><td>7</td><td>1,433.4</td><td>1,427.1</td><td>—</td><td>—</td><td>99.6%</td></tr>
        </tbody>
      </table>
    </div>

    <h3>1.2 为什么说是"低速稳健"而不是"爆发" <span class="h3-en">Steady, Not Explosive</span></h3>
    <p>
      三个证据支持这一判断。其一，<strong>2017→2025 年产量 CAGR 仅 3.14%、销量 3.07%</strong>，
      低于同期名义经济增速，也显著低于一个"成长型行业"应有的水平。
      其二，2019-01 至 2026-07 的最小二乘趋势斜率为 <strong>每年 +7.7 万辆</strong>（销量 +7.6 万辆），
      相对 2,000 万辆级的基数不足 0.4%——趋势线几乎是平的。
      其三，2021 与 2025 两个高点之间隔了四年，中间还夹着一次 −0.8% 的负增长与一个低基数的不完整年。
    </p>
    <p>
      但这不等于"行业没有机会"。需要区分两个时间尺度：<strong>十年均值是低速的，当前位置则处在一轮上行周期中</strong>。
      2024→2025 是完整年可比口径下真实的 +10.3%，为 2018 年以来最高；2026 年 1–7 月产量同比 +14.9%、
      销量 +14.4%，增速进一步抬升。真正的机会不在总量，而在结构——这正是后续四章要展开的内容。
    </p>

    <h3>1.3 产销率 99.56%：没有库存压力意味着什么 <span class="h3-en">What "No Inventory Pressure" Implies</span></h3>
    <p>
      全周期累计产销率 <strong>99.56%</strong>，各年在 97.9%~100.5% 之间窄幅波动
      （2022 年 100.5% 最高，2023 年 97.9% 最低）。至 2025 年末，累计产销差仅 78.2 万辆，
      相对年产 2,000 万辆以上的体量可以忽略。这个事实有三层含义：
    </p>
    <ul>
      <li><strong>产量可以作为销量的代理变量。</strong>本报告中的排量结构与车型结构使用生产口径（数据更完整），
      出口与内销拆解使用销量口径（出口表与销量表对齐），二者的一致性由产销率保证。</li>
      <li><strong>行业没有通过压库存来粉饰销量。</strong>总量数据的"含金量"高，不需要做渠道库存调整。</li>
      <li><strong>但行业也失去了缓冲垫。</strong>产销同步意味着海外订单一旦波动，需求冲击会立刻传导到生产端，
      不会先被库存吸收。在外销率已达 63% 的今天，这一点尤为重要（见 §5 风险提示）。</li>
    </ul>

    <h3>1.4 二轮 88% / 三轮 12%：结构十年未变 <span class="h3-en">Two-Wheelers Dominate, Stably</span></h3>
    <p>
      2025 年二轮车 1,929.8 万辆（占 87.9%）、三轮车 265.2 万辆（占 12.1%）。
      这个比例十年间几乎纹丝不动：2016 年为 87.4% / 12.6%，2017 年为 88.1% / 11.9%。
      三轮车在 2025 年创下 265.2 万辆的十年新高，但增速与二轮同步，占比反而稳定在 12% 左右。
      结论很直接：<strong>三轮是一个规模可观但缺乏弹性的补充盘，不构成战略主线</strong>，
      本报告后续结构分析均以二轮车为核心。
    </p>

    <div class="chart-slot" data-chart="a3_two_three_wheeler" data-fig="图 4"></div>

    <h3>1.5 2026 年前景：一个基于季节性的推算 <span class="h3-en">A Seasonality-Based Projection</span></h3>
    <p>
      2026 年 1–7 月产量 1,433.4 万辆、销量 1,427.1 万辆，同比 +14.9% / +14.4%。
      按 2025 年 1–7 月产量占全年 56.8% 的季节性比例推算，2026 全年产量有望达到
      <strong>约 2,520 万辆</strong>（较 2025 年 +15% 左右）。
    </p>
    <div class="callout">
      <span class="c-t">口径提醒</span>
      <p>
        这是<strong>基于季节性节奏的推算，不是观测值</strong>。其成立的前提是 8–12 月出口订单维持
        1–7 月的强度。考虑到外销率已达 63%，实际结果对海外需求的敏感度远高于历史任何时期，
        建议在 2026 年 Q4 用实际月度数据重新校准。
      </p>
    </div>
  </div>
</section>

<!-- ============================ §2 出口 vs 内销 ============================ -->
<section id="s2">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">SECTION 02 &nbsp;·&nbsp; 核心章节</span>
      <h2>出口 vs 内销：外需撑起的繁荣</h2>
      <div class="h2-en">Exports vs Domestic Sales: A Prosperity Propped Up by Overseas Demand</div>
    </div>

    <p>
      这是全报告最重要的一章。它解释了那个看似矛盾的现象：<strong>为什么总量创下十年新高，
      而大多数国内从业者却感受不到"景气"</strong>。答案藏在销量内部的拆解里。
    </p>

    <h3>2.1 拆解：内销 = 销量 − 出口 <span class="h3-en">Decomposing Sales</span></h3>
    <p>
      出口表与销量表已经通过 63 个月零偏差的交叉校验，因此"内销 = 销量 − 出口"这个恒等式
      是可靠的结构拆解工具。在 2024 与 2025 两个完整年之间：
    </p>

    <div class="table-scroll">
      <table>
        <caption>注：内销 = 销量 − 出口。2023 年为 9–12 月、2026 年为 1–7 月，均非完整年，不可与 2024/2025 并列比较绝对量。</caption>
        <thead>
          <tr><th>年份</th><th>口径</th><th>销量(万辆)</th><th>出口(万辆)</th><th>内销(万辆)</th><th>外销率</th></tr>
        </thead>
        <tbody>
          <tr><td>2023</td><td style="text-align:left">9–12 月</td><td>598.0</td><td>289.3</td><td>308.7</td><td>48.4%</td></tr>
          <tr><td>2024</td><td style="text-align:left">1–12 月</td><td>1,985.1</td><td>1,093.6</td><td>891.5</td><td>55.1%</td></tr>
          <tr class="hl"><td>2025</td><td style="text-align:left">1–12 月</td><td>2,180.4</td><td>1,328.2</td><td>852.2</td><td>60.9%</td></tr>
          <tr><td>2026</td><td style="text-align:left">1–7 月</td><td>1,427.1</td><td>898.5</td><td>528.6</td><td>63.0%</td></tr>
        </tbody>
      </table>
    </div>

    <p>
      把 2024→2025 的变化拆成增量，结论会变得非常锋利：
      <strong>销量净增 195.3 万辆（+9.8%），出口净增 234.6 万辆（+21.5%），内销净减 39.3 万辆（−4.4%）</strong>。
      出口增量（+234.6 万辆）已经超过了销量总增量（+195.3 万辆）——这在数学上只有一个解释：
      <em>国内市场需求对行业增长是负贡献</em>。
    </p>

    <div class="callout danger">
      <span class="c-t">这意味着什么</span>
      <p>
        行业已经完成了一次驱动力的切换：从"内需驱动"转为"出口驱动"。这不只是周期性波动——
        2023 年 9 月以来外销率的抬升是单调的、持续的，三年内从 48.4% 升到 63.0%，抬升 14.6pp。
        其底层原因是国内摩托车的通勤功能被电动两轮车与汽车持续替代，
        而中国摩托车在亚非拉市场凭借性价比与完整供应链拿下了份额。
        <strong>对企业而言，战略坐标系的原点已经从"国内渠道"移到了"海外订单"</strong>——
        产品定义、产能布局、汇率与合规能力的重要性都在上升。
      </p>
    </div>

    <h3>2.2 外销率：三年抬升 14.6 个百分点 <span class="h3-en">Export Ratio: +14.6pp in Three Years</span></h3>
    <p>
      2023 年 48.4%（9–12 月）→ 2024 年 55.1% → 2025 年 60.9% → 2026 年 1–7 月 63.0%。
      这条曲线是理解当前行业状态的钥匙。
    </p>

    <div class="chart-slot" data-chart="b2_export_ratio_trend" data-fig="图 5"></div>

    <h3>2.3 出口量与价：不是靠降价换量 <span class="h3-en">Volume and Price Both Rising</span></h3>
    <p>
      2024 年出口 1,093.6 万辆 → 2025 年 1,328.2 万辆，同比增长 <strong>21.5%</strong>，
      这是唯一两个可比的完整年份。更值得注意的是价格：出口单车均价从 2023 年的 619.2 美元、
      2024 年的 635.7 美元，升至 2025 年的 <strong>709.1 美元（+11.5%）</strong>。
      34 个月（2023.09–2026.06）累计出口 3,467.7 万辆、233.5 亿美元，均价 673.4 美元，外销率 58.1%。
    </p>

    <div class="chart-slot" data-chart="b3_export_volume_yearly" data-fig="图 6"></div>
    <div class="chart-slot" data-chart="b4_export_value_price" data-fig="图 7"></div>

    <p>
      <strong>均价 +11.5% 是本报告中最容易被忽略、但商业含义最重的一个数字。</strong>
      它证明出口增长不是靠低价走量换来的。而结合下一节的结构证据——出口的排量结构与内销高度同构——
      可以进一步推断：<em>均价的提升并非来自"排量段跃迁"，而更可能来自段内产品升级、
      配置提升、品牌直营替代纯贴牌，以及汇率与全球通胀的共同作用</em>。
      这是一个值得企业单独建立仪表盘跟踪的指标，因为它直接决定出口业务的利润质量。
    </p>

    <div class="callout">
      <span class="c-t">一个需要警惕的边际变化</span>
      <p>
        2026 年 1–7 月出口单车均价为 <strong>691.6 美元</strong>，较 2025 年全年的 709.1 美元回落约 2.5%。
        需提示：1–7 月与完整年份的口径不完全可比（年内各月产品结构不同），
        这个回落<strong>尚不能确认为趋势</strong>，但应纳入季度跟踪。若 2026 全年均价确认下滑，
        则"量增价跌"会显著改变出口业务的利润预期。
      </p>
    </div>

    <h3>2.4 反直觉：出口并不更偏大排量 <span class="h3-en">Counter-Intuitive: Exports Are Not More Big-Bore</span></h3>
    <p>
      一个流传很广的假设是"出口在拉动中国摩托车向大排量升级"。数据不支持这个说法。
      在同口径对比下（出口分排量表本身不含电动，因此与"剔除电动后的二轮燃油生产结构"对比）：
    </p>

    <div class="table-scroll">
      <table>
        <caption>同口径说明：出口分排量表本身不含电动，故与"剔除电动后的二轮燃油生产结构"对比。</caption>
        <thead><tr><th>排量组</th><th>出口占比(2025)</th><th>内销(二轮燃油)占比</th><th>差异 pp</th></tr></thead>
        <tbody>
          <tr><td>≤110ml</td><td>16.2%</td><td>17.4%</td><td class="neg">−1.1</td></tr>
          <tr><td>110-125ml</td><td>35.6%</td><td>36.0%</td><td class="neg">−0.4</td></tr>
          <tr><td>125-150ml</td><td>29.9%</td><td>29.0%</td><td class="pos">+0.8</td></tr>
          <tr><td>150-250ml</td><td>14.0%</td><td>12.0%</td><td class="pos">+2.0</td></tr>
          <tr class="hl"><td>&gt;250ml</td><td>4.3%</td><td>5.6%</td><td class="neg">−1.3</td></tr>
        </tbody>
      </table>
    </div>

    <p>
      各排量段的差异全部落在 <strong>±2.1pp 以内</strong>，两个结构几乎是同一条曲线的两次采样。
      出口在 150-250ml 段高出约 2.0pp，但在 <strong>&gt;250ml 段反而比内销低 1.3pp</strong>。
      2024 与 2026 年的结论完全一致。
    </p>

    <div class="chart-slot" data-chart="b6_export_vs_domestic_disp" data-fig="图 8"></div>

    <div class="callout info">
      <span class="c-t">这个反直觉结论对决策的意义</span>
      <p>
        第一，<strong>不要把大排量产品规划建立在"出口大排量"的假设上</strong>——大排量的增长引擎在国内，
        出口不是拉力。第二，<strong>出口的结构性机会在 110–150ml</strong>：该区间合计占 2025 年出口的
        <strong>65.5%</strong>，是规模最大、中国供应链最具成本优势的区间；在这里做配置升级与品牌直营，
        比追逐大排量出海更现实。第三，出口的升级路径是<strong>"段内价值提升"而非"跨段跃迁"</strong>，
        这与 §2.3 中均价 +11.5% 而结构同构的观察是互相印证的。
      </p>
    </div>

    <h3>2.5 出口的渠道结构：比国内更头部，但也不是寡头 <span class="h3-en">Export Channel Structure</span></h3>
    <p>
      2025 年出口 CR5 为 <strong>42.2%</strong>、CR10 为 60.8%（68 家企业在出口），
      均高于全行业的 36.9% / 53.5%。这说明出口是一条比国内<strong>更依赖头部</strong>的渠道——
      海外认证、渠道与售后网络的门槛高于国内，中小厂难以独立完成——但 42% 的 CR5 仍远未形成寡头，
      长尾机会依然存在。2025 年出口前三为大长江 175.8 万辆（13.2%）、隆鑫 141.9 万辆（10.7%）、
      大冶 98.8 万辆（7.4%）；大长江在 2026 年 1–7 月进一步升至 14.2%。
    </p>

    <h3>2.6 小结 <span class="h3-en">Summary</span></h3>
    <p>
      出口已经不是行业的一个"补充渠道"，而是<strong>增长的唯一引擎和风险的唯一主要来源</strong>。
      外销率 63% 意味着：汇率、海运成本、目的国关税与准入政策、以及海外经销商的库存周期，
      这四件事中的任何一件出问题，都会直接决定中国摩托车行业当年的总量走向。
      对一家企业而言，把出口业务从"销售职能"升级为"战略职能"，已经是必选项而非可选项。
    </p>
  </div>
</section>

<!-- ============================ §3 排量与车型结构 ============================ -->
<section id="s3">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">SECTION 03</span>
      <h2>排量与车型结构：消费升级与电动过山车</h2>
      <div class="h2-en">Displacement &amp; Body-Type Structure: Upgrading, and the Electric Rollercoaster</div>
    </div>

    <p>
      如果 §2 讲的是"量从哪里来"，这一章讲的是"量是什么"。
      在总量低速增长的背后，产品结构正发生十年尺度上最剧烈的一次变化。
    </p>

    <h3>3.1 主图：小排量腰斩，大排量 17 倍 <span class="h3-en">The Key Structural Chart</span></h3>
    <p>
      下图是观察燃油车"排量升级"最干净的口径——分母为二轮燃油车总量（已剔除电动摩托车），
      消除了 2022 年电动脉冲对整体结构的扰动。
    </p>

    <div class="chart-slot" data-chart="c1_disp_2w_fuel_share" data-fig="图 9"></div>

    <p>
      核心变化一目了然：<strong>≤110ml 从 30.1% 萎缩至 17.4%（腰斩）</strong>；
      125-150ml 从 22.6% 升至 29.0%；150-250ml 从 5.7% 升至 12.0%；
      <strong>&gt;250ml 从 0.33% 升至 5.6%（约 17 倍）</strong>。
      三个中高排量段的份额在十年间全部翻倍以上，而最低排量段份额腰斩。
      这是全报告最可靠、最可外推的一条结构性结论。
    </p>

    <h3>3.2 绝对量视角：增量到底来自哪里 <span class="h3-en">Where the Incremental Volume Came From</span></h3>
    <p>
      份额会骗人——当分母在增长时，一个份额腰斩的排量段，绝对量可能并没有下降。
      因此必须看绝对量。以 2017 年（第一个完整年份）为基准，到 2025 年二轮车总量增加 420.5 万辆，
      增量构成如下：
    </p>

    <div class="table-scroll">
      <table>
        <caption>口径：二轮摩托车生产口径。2017 与 2025 均为完整年。电动摩托车 2019 年起口径才可比，此处以 2017 年为统一基准计算增量。</caption>
        <thead>
          <tr><th>排量组</th><th>2017(万辆)</th><th>2025(万辆)</th><th>绝对变化</th><th>增幅</th><th>占二轮总增量</th></tr>
        </thead>
        <tbody>
          <tr><td>≤110ml</td><td>425.9</td><td>296.4</td><td class="neg">−129.5 万</td><td class="neg">−30.4%</td><td class="neg">−30.8%</td></tr>
          <tr><td>110-125ml</td><td>607.6</td><td>612.9</td><td>+5.3 万</td><td>+0.9%</td><td>+1.3%</td></tr>
          <tr><td>125-150ml</td><td>362.0</td><td>494.3</td><td class="pos">+132.3 万</td><td class="pos">+36.5%</td><td class="pos">+31.5%</td></tr>
          <tr><td>150-250ml</td><td>94.1</td><td>204.2</td><td class="pos">+110.1 万</td><td class="pos">+117.0%</td><td class="pos">+26.2%</td></tr>
          <tr class="hl"><td>&gt;250ml</td><td>9.6</td><td>95.4</td><td class="pos">+85.8 万</td><td class="pos">+894%</td><td class="pos">+20.4%</td></tr>
          <tr><td>电动</td><td>9.9</td><td>226.5</td><td class="pos">+216.5 万</td><td class="pos">+2,185%</td><td class="pos">+51.5%</td></tr>
          <tr class="tot"><td>二轮合计</td><td>1,509.3</td><td>1,929.8</td><td>+420.5 万</td><td>+27.9%</td><td>100%</td></tr>
        </tbody>
      </table>
    </div>

    <p>这张表给出了三个在份额图上看不到的判断：</p>
    <ul>
      <li><strong>125ml 以上才是真正的增长引擎。</strong>125-150ml、150-250ml、&gt;250ml 三段合计贡献
      <strong>+328.2 万辆</strong>，占二轮总增量的 78.0%（若把电动计入则为 129%）。</li>
      <li><strong>110-125ml 是一个"停止增长的现金牛"。</strong>绝对量十年 +0.9%（607.6 → 612.9 万辆），
      几乎原地踏步，但它仍是 2025 年最大的单一排量段（612.9 万辆，占二轮 31.8%）。
      规模巨大、增长为零——这是典型的高现金流、低投入价值区间。</li>
      <li><strong>≤110ml 是唯一的负贡献段。</strong>绝对量十年 −30.4%，是唯一在萎缩的排量区间。
      它的份额腰斩不是被"摊薄"，而是真实的需求退出。</li>
    </ul>

    <h3>3.3 大排量：六年 9.9 倍，但 2026 年踩了刹车 <span class="h3-en">Big Bore: 9.9x in Six Years, Then a Brake</span></h3>
    <p>
      二轮 &gt;250ml 产量从 2019 年的 18.1 万辆增至 2025 年的 <strong>95.4 万辆（+426%）</strong>，
      占二轮比重从 1.19% 升至 4.94%，2025 年同比 +23.3%。这条曲线是全行业增速最快的赛道。
    </p>

    <div class="chart-slot" data-chart="c2_big_displacement" data-fig="图 10"></div>

    <p>
      把 2023 年起可得的细分段展开，还能看到赛道<strong>内部</strong>的升级：
      2024→2025 年，250-400ml 从 42.0 万辆增至 52.7 万辆（+25%），
      400-500ml 从 24.2 万辆<strong>降至</strong> 21.6 万辆（−11%），
      而 500-800ml 从 9.6 万辆增至 <strong>18.7 万辆（+95%）</strong>，
      &gt;800ml 从 1.6 万辆增至 2.4 万辆（+50%）。
      增长最快的是 500ml 以上，中端 400-500ml 反而出现回落——
      这说明大排量赛道本身也在向更高端迁移，而不是均匀扩张。
    </p>

    <div class="callout">
      <span class="c-t">口径提示</span>
      <p>
        &gt;250ml 组在 2023 年前为 400-750 / &gt;750ml 分段，2023 年起改为 400-500 / 500-800 / &gt;800ml，
        界点由 750ml 改为 800ml，存在微小口径差异。组级别的跨年比较是可靠的，
        但"400-500ml vs 400-750ml"这类细分段比较<strong>仅限 2023 年之后</strong>。
      </p>
    </div>

    <h3>3.4 车型结构：纠正一个广泛流传的误读 <span class="h3-en">Correcting a Common Misreading</span></h3>
    <p>
      如果直接看含电动的车型结构表，会得出"踏板车份额从 23.7% 暴涨至 49.0%"的结论。
      <strong>这是错的。</strong>原因是电动摩托车在分车型表中 100% 计入"踏板式"
      （已交叉验证：各年踏板式产量恒 ≥ 电动产量）。2022 年踏板式 49.0% 的高点，
      完全是当年电动摩托车冲到 542.2 万辆造成的假象。
    </p>

    <div class="chart-slot" data-chart="c3_vehicle_type_fuel" data-fig="图 11"></div>

    <p>
      剔除电动后的真实情况是：<strong>骑式从 58.7% 升至 67.1%</strong>（上升 8.4pp），
      弯梁式从 18.1% 降至 13.0%，<strong>燃油踏板式从 23.3% 微降至 20.0%</strong>。
      燃油车不但没有"踏板化"，反而向骑式集中。
    </p>
    <p>
      这个纠正的商业含义很直接：电动摩托车抢占的正是<strong>踏板形态的短途通勤场景</strong>，
      燃油车则退守骑式所代表的载重、长途、耐用与性价比场景。
      任何在做产品形态规划的企业，如果沿用了含电动的口径，都会误判踏板车市场在扩张，
      从而把资源投向一个实际在收缩的细分形态。
    </p>

    <h3>3.5 电动摩托车：过山车之后是稳态 <span class="h3-en">Electric Motorcycles: After the Rollercoaster</span></h3>
    <p>
      电动摩托车（二轮）的轨迹是过去十年最戏剧化的一条曲线：
      2019 年 177.7 万辆 → 2021 年 311.8 万辆 → <strong>2022 年 542.2 万辆（占二轮 30.6%）</strong>
      → 2023 年 390.0 万辆 → 2024 年 219.6 万辆 → 2025 年 226.5 万辆（占二轮 11.7%，同比 +3.1%）。
      峰值月为 2022 年 9 月的 77.5 万辆。
    </p>

    <div class="chart-slot" data-chart="c4_electric_trend" data-fig="图 12"></div>
    <div class="chart-slot" data-chart="c5_electric_monthly" data-fig="图 13"></div>

    <p>
      如何解读这条曲线？<strong>2022 年的峰值是"新国标过渡期抢装 + 渠道压货"的一次性脉冲，
      不是电动化的真实需求水平；2023–2024 年是需求被前置透支后的去库存；
      2025 年 +3.1% 则说明品类已回到由真实替换需求支撑的稳态。</strong>
      换句话说，从 542 万跌到 220 万不是"电动化失败"，而是挤出了水分。
      11%–12% 的二轮占比，才是评估电动摩托车业务时应该使用的基准。
    </p>

    <div class="callout info">
      <span class="c-t">两点必要的澄清</span>
      <p>
        其一，<strong>电动摩托车是纳入机动车管理、需要驾照与牌照的品类，与电动自行车不是同一市场</strong>，
        不能用电动自行车的渗透逻辑外推电动摩托车的空间。其二，本表仅含二轮电动，
        三轮电动摩托车未纳入分排量明细表（这也是三轮排量表覆盖率仅 53% 的主要原因）。
        <br><br>
        赛道格局方面，2025 年电动摩托车 CR5 达 <strong>76.3%</strong>（生产口径），
        雅迪 28.6%、绿源 17.2%、宗申 13.4%，前三家合计 59.2%——
        这是一条比大排量更集中、格局更稳定的赛道。
      </p>
    </div>
  </div>
</section>

<!-- ============================ §4 竞争格局 ============================ -->
<section id="s4">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">SECTION 04</span>
      <h2>竞争格局：分散的行业，集中的赛道</h2>
      <div class="h2-en">Competitive Landscape: A Fragmented Industry, Concentrated Segments</div>
    </div>

    <p>
      本章的所有结论都基于 2023 年 9 月至 2026 年 7 月共 35 个月的品牌明细数据。
      <strong>品牌类结论只能说"近 3 年"，不能说"十年格局变化"</strong>——这是数据的硬约束。
    </p>

    <h3>4.1 集中度不升反降：行业尚未进入整合期 <span class="h3-en">Concentration Is Falling, Not Rising</span></h3>
    <p>
      一个反常识的事实：在总量创十年新高、出口高速增长的背景下，
      行业销量 CR5 却从 2024 年的 38.1% <strong>降至</strong> 2025 年的 36.9%（−1.2pp），
      2026 年 1–7 月小幅回升至 37.4%；CR10 从 54.2% 降至 53.5%。
      同期在产企业数从 90 家微降至 89 家——<strong>几乎没有人退出</strong>。
    </p>

    <div class="chart-slot" data-chart="d1_brand_concentration" data-fig="图 14"></div>

    <p>为什么行业越增长反而越分散？三个机制在同时起作用：</p>
    <ul>
      <li><strong>出口订单碎片化。</strong>海外市场的准入门槛主要是认证与价格，而非品牌与渠道。
      中小厂可以通过 OEM/ODM 直接拿到海外订单，绕开了国内最难攻克的渠道壁垒。
      出口 CR5（42.2%）虽然高于国内，但 66–68 家企业在做出口，长尾同样很长。</li>
      <li><strong>新赛道留出了空间。</strong>2022–2025 年电动与大排量两条赛道快速扩容，
      给新进入者提供了"换道超车"的窗口，稀释了头部份额。</li>
      <li><strong>头部企业无暇打价格战。</strong>头部忙于出海与产能，
      国内市场尚未出现以份额为目标的正面决战——这也意味着价格战的引信还在。</li>
    </ul>

    <div class="callout danger">
      <span class="c-t">这意味着什么</span>
      <p>
        规模本身在这个行业里<strong>不构成壁垒</strong>。CR5 36.9%、89 家在产、CR10 仅略过半，
        说明行业远未进入整合期，规模效应与议价能力都还很弱。
        对企业来说，追求"总销量排名前五"的战略目标，在这个格局下既难达成、也难转化为利润；
        <strong>真正的护城河在细分赛道的地位，而不是在总盘的规模</strong>。
      </p>
    </div>

    <h3>4.2 头部格局：长尾极长，头部与腰部没有断层 <span class="h3-en">A Very Long Tail</span></h3>
    <div class="chart-slot" data-chart="d2_brand_ranking_2025" data-fig="图 15"></div>

    <div class="table-scroll">
      <table>
        <caption>注：销售口径，2025 完整年。品牌明细仅覆盖 2023-09 起的 35 个月，本表不代表"十年格局"。</caption>
        <thead><tr><th>排名</th><th style="text-align:left">品牌</th><th>销量(万辆)</th><th>份额</th></tr></thead>
        <tbody>
          <tr class="hl"><td>1</td><td style="text-align:left">江门市大长江集团有限公司</td><td>268.7</td><td>12.3%</td></tr>
          <tr class="hl"><td>2</td><td style="text-align:left">重庆隆鑫机车有限公司</td><td>164.5</td><td>7.5%</td></tr>
          <tr class="hl"><td>3</td><td style="text-align:left">宗申产业集团有限公司</td><td>160.4</td><td>7.4%</td></tr>
          <tr class="hl"><td>4</td><td style="text-align:left">广东大冶摩托车技术有限公司</td><td>110.9</td><td>5.1%</td></tr>
          <tr class="hl"><td>5</td><td style="text-align:left">新大洲本田摩托(苏州)有限公司</td><td>100.3</td><td>4.6%</td></tr>
          <tr><td>6</td><td style="text-align:left">雅迪科技集团有限公司</td><td>92.1</td><td>4.2%</td></tr>
          <tr><td>7</td><td style="text-align:left">重庆银翔摩托车集团有限公司</td><td>73.7</td><td>3.4%</td></tr>
          <tr><td>8</td><td style="text-align:left">广州豪进摩托车股份有限公司</td><td>72.9</td><td>3.3%</td></tr>
          <tr><td>9</td><td style="text-align:left">五羊-本田摩托（广州）有限公司</td><td>61.7</td><td>2.8%</td></tr>
          <tr><td>10</td><td style="text-align:left">洛阳北方企业集团有限公司</td><td>61.3</td><td>2.8%</td></tr>
        </tbody>
      </table>
    </div>

    <p>
      前五名合计仅 36.9%，第 15 名仍有 41.4 万辆（1.9%）。更值得注意的是：
      第 1 名与第 5 名之间相差 7.7pp，而<strong>第 5 名与第 15 名之间只相差约 2.7pp</strong>——
      头部与腰部之间几乎不存在断层。这是一个"人人都有机会、但也人人都不安全"的格局。
    </p>

    <h3>4.3 谁在上升：踩对赛道的企业 <span class="h3-en">Who Is Gaining</span></h3>
    <div class="chart-slot" data-chart="d3_brand_share_shift" data-fig="图 16"></div>

    <p>
      份额口径（%）比绝对销量更适合跨期比较。2024 → 2025 → 2026 年 1–7 月，
      三条曲线最值得注意：<strong>春风动力 1.6% → 2.6% → 4.1%</strong>，是头部中上升最快的；
      <strong>大长江 11.7% → 12.3% → 13.1%</strong>，稳健扩张且优势在扩大；
      隆鑫则从 7.5% 回落至 2026 年 1–7 月的 6.3%。
      排名跃升最快的企业包括长铃集团（+8 位）、重庆安第斯（+8 位）、康超集团（+6 位）、
      航天巴山（+5 位）与<strong>春风动力（+5 位）</strong>。
    </p>
    <p>
      规律很清楚：<strong>上升最快的企业几乎都踩在大排量或电动这两条高增长赛道上；
      仅靠 110-125ml 走量的企业份额普遍在下滑</strong>。这与 §3 的结构结论完全一致——
      在一个总量低速增长的行业里，份额的变化几乎完全由"你在哪条赛道上"决定。
    </p>

    <h3>4.4 赛道集中度：三个数字的强烈对比 <span class="h3-en">Three Numbers, One Message</span></h3>
    <div class="chart-slot" data-chart="d4_big_disp_brands" data-fig="图 17"></div>

    <div class="table-scroll">
      <table>
        <caption>三条赛道均为 2025 年数据。全行业与出口为销量口径，大排量为二轮 &gt;250ml 销量口径，电动为二轮生产口径。</caption>
        <thead><tr><th style="text-align:left">赛道</th><th>CR5</th><th>CR10</th><th style="text-align:left">头部构成</th></tr></thead>
        <tbody>
          <tr><td style="text-align:left">全行业（销量）</td><td>36.9%</td><td>53.5%</td><td style="text-align:left">大长江 12.3% / 隆鑫 7.5% / 宗申 7.4%</td></tr>
          <tr><td style="text-align:left">出口</td><td>42.2%</td><td>60.8%</td><td style="text-align:left">大长江 13.2% / 隆鑫 10.7% / 大冶 7.4%</td></tr>
          <tr class="hl"><td style="text-align:left">&gt;250ml 大排量</td><td>69.9%</td><td>—</td><td style="text-align:left">春风 19.8% / 大冶 18.1% / 隆鑫 14.8% / 钱江 11.9% / 宗申 5.2%</td></tr>
          <tr class="hl"><td style="text-align:left">电动摩托车</td><td>76.3%</td><td>—</td><td style="text-align:left">雅迪 28.6% / 绿源 17.2% / 宗申 13.4%</td></tr>
        </tbody>
      </table>
    </div>

    <p>
      36.9% → 42.2% → 69.9% → 76.3%，这组数字是"分散的行业，集中的赛道"最直接的证据。
      它的战略含义非常明确：<strong>在总盘上，行业不会给你规模红利；但在赛道上，先发者已经筑起了墙</strong>。
      对企业而言，战略的第一性问题不是"怎么做大总份额"，而是"选哪条赛道、如何在这条赛道进前三"。
    </p>
    <p>
      一个有意思的观察：<strong>春风动力是全行业排名第 12（2025 年销量 56.0 万辆、份额 2.6%），
      却是大排量赛道的第一（19.8%）</strong>。这说明在当前的行业结构下，
      "赛道第一"带来的品牌溢价与定价权，可能比"总排名前十"更有价值。
    </p>
  </div>
</section>

<!-- ============================ §5 2026 新信号 ============================ -->
<section id="s5">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">SECTION 05</span>
      <h2>2026 年的两个新信号与季节性</h2>
      <div class="h2-en">Two New Signals from 2026, and Seasonality</div>
    </div>

    <p>
      2026 年只有 1–7 月的数据，因此本章全部使用"1–7 月 vs 上年同期"这一唯一可比的口径。
      在这个口径下，2026 年给出了两个方向相反的信号。
    </p>

    <h3>5.1 正面信号：内销回暖 +8.0% <span class="h3-en">Signal 1: Domestic Demand Recovering</span></h3>

    <div class="chart-slot" data-chart="b5_ytd_1_7_split" data-fig="图 18"></div>

    <div class="table-scroll">
      <table>
        <caption>注：2026 年仅 1–7 月，故统一采用 1–7 月同期口径。这是 2026 年唯一合法的同比序列。</caption>
        <thead>
          <tr><th>年份(1–7月)</th><th>销量(万辆)</th><th>出口(万辆)</th><th>内销(万辆)</th><th>出口同比</th><th>内销同比</th><th>外销率</th></tr>
        </thead>
        <tbody>
          <tr><td>2024</td><td>1,127.5</td><td>609.5</td><td>518.0</td><td>—</td><td>—</td><td>54.1%</td></tr>
          <tr><td>2025</td><td>1,247.2</td><td>757.9</td><td>489.3</td><td class="pos">+24.3%</td><td class="neg">−5.5%</td><td>60.8%</td></tr>
          <tr class="hl"><td>2026</td><td>1,427.1</td><td>898.5</td><td>528.6</td><td class="pos">+18.6%</td><td class="pos">+8.0%</td><td>63.0%</td></tr>
        </tbody>
      </table>
    </div>

    <p>
      出口同比从 +24.3% 放缓至 +18.6%（高位减速但仍然强劲），
      <strong>内销同比则从 −5.5% 转为 +8.0%</strong>——这是 2021 年以来内销首次在同期口径下转正，
      是明确的积极信号。
    </p>
    <p>
      但需要两个保留。其一，<strong>这只是一个 1–7 月的窗口，尚不构成趋势</strong>；
      2025 年同期是 −5.5%，一年之内的波动区间达 13.5pp，单期数据的信息量有限。
      其二，<strong>外销率仍在上升</strong>（54.1% → 60.8% → 63.0%），
      说明内销回暖只是"增速转正"，并没有改变出口主导的格局。
      正确的读法是"内需的萎缩暂停了"，而不是"内需回来了"。
    </p>

    <h3>5.2 风险信号：大排量增速骤降至 +1.1% <span class="h3-en">Signal 2: Big Bore Stalls</span></h3>

    <div class="chart-slot" data-chart="e3_big_disp_slowdown" data-fig="图 19"></div>

    <p>
      这是本报告提示的首要风险。1–7 月 &gt;250ml 产量的同期同比：
      2024 年 +77.8% → 2025 年 +38.0% → <strong>2026 年 +1.1%</strong>。
      同期行业整体产量 +14.9%。大排量占全行业比重也从 4.82% 回落至 <strong>4.24%</strong>。
      换句话说，<em>2026 年大排量赛道不但没有跑赢行业，反而大幅跑输</em>。
    </p>
    <p>有三种可能的解释，本报告无法用现有数据完全区分，但每一种都有明确的验证方法：</p>
    <ul>
      <li><strong>高基数与需求前置。</strong>2024–2025 连续两年 +77.8% / +38.0%，
      把未来两三年的换车需求提前释放。<em>验证：看 2026 年 8–12 月是否回补。</em></li>
      <li><strong>消费力约束。</strong>大排量摩托车具有明显的可选消费与"玩具"属性，
      对居民可支配收入与消费信心高度敏感。<em>验证：看 500ml 以上段是否与 250-400ml 段同步走弱——
      若同步走弱则是需求侧问题，若仅低段走弱则是结构问题。</em></li>
      <li><strong>赛道内部竞争加剧。</strong>头部为保份额下探价格与主销区间，
      但未能换来量的增长。<em>验证：看 CR5 合计份额是否松动、终端折扣是否扩大。</em></li>
    </ul>

    <div class="callout danger">
      <span class="c-t">无论哪种解释成立，结论是一样的</span>
      <p>
        <strong>"大排量将保持 30%+ 增长"的假设在 2026 年已经不成立。</strong>
        而 2024–2025 年按 +78% / +38% 的增速规划建设的大排量产能，恰好在 2026 年集中释放。
        供给的惯性遇上了需求的刹车，这是产能利用率与库存最需要警惕的地方。
      </p>
    </div>

    <h3>5.3 两个信号合起来怎么看 <span class="h3-en">Reading the Two Signals Together</span></h3>
    <p>
      内销回暖 +8.0% 与大排量失速 +1.1%，看似矛盾，其实指向同一件事：
      <strong>2026 年的内需回暖发生在中低排量的实用型市场，而不是在消费升级的高端市场。</strong>
      这与 §3 的排量结构证据是一致的——125-150ml 依然是增量最大的单个排量段
      （2017→2025 年 +132.3 万辆），而 &gt;250ml 的绝对量（95.4 万辆）只有它的五分之一。
      如果这一判断成立，2026 年的产品重心应回到 <strong>125–250ml 的"高性价比升级"区间</strong>，
      而不是继续加码 &gt;250ml。这也是本报告 §6 第一条建议的依据。
    </p>

    <h3>5.4 季节性：十年稳定，2 月是绝对低点 <span class="h3-en">Seasonality: Stable for a Decade</span></h3>

    <div class="chart-slot" data-chart="e1_seasonality" data-fig="图 20"></div>

    <p>
      季节性指数（年均 = 100）：<strong>9 月 112 为全年最高</strong>，12 月 108，6–7 月 107；
      <strong>2 月仅 59</strong>，约为年均的六成（春节停工）。
      淡旺季格局十年间保持稳定——近期（2024–2025）与早期（2017–2019）各月差异多在 ±7 以内，
      仅 2 月（−6.9）与 7 月（+6.1）变化稍大，主要来自春节错位与出口发运节奏提前。
    </p>
    <p>
      运营含义很实用：2 月的产能利用率只有年均的六成，是安排检修、产线切换与人员调配的最佳窗口；
      <strong>3–4 月与 8–9 月是两个发货高峰</strong>，出口订舱与国内渠道备货应前置 1–2 个月；
      年底 12 月的冲量高峰（108）通常来自渠道年度目标结算，需提前判断是真实需求还是渠道压货。
    </p>

    <h3>5.5 单月同比不能用来判断景气 <span class="h3-en">Do Not Judge the Cycle from Monthly YoY</span></h3>

    <div class="chart-slot" data-chart="e2_turning_points" data-fig="图 21"></div>

    <p>
      销量同比波动最大的月份里，2021-02 的 <strong>+221.6%</strong> 是 2020 年疫情低基数叠加春节错位
      （2020 年春节在 1 月、2021 年在 2 月）的技术性波动；2020-02 的 −60.6% 是疫情停工；
      2023-01 / 2023-02、2025-02 的大幅波动同样主要来自春节错位。
      这些都是统计假象，不是景气变化。<strong>判断趋势请一律使用年度或累计口径（图 3）</strong>，
      不要用单月同比下结论。
    </p>
  </div>
</section>

<!-- ============================ 结论与决策建议 ============================ -->
<section id="advice">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">CONCLUSIONS &amp; RECOMMENDATIONS</span>
      <h2>结论与决策建议</h2>
      <div class="h2-en">Conclusions and Actionable Recommendations</div>
    </div>

    <p class="lead">
      综合五章的证据，本报告的核心判断是：<strong>中国摩托车行业已经完成从"内需驱动"到"出口驱动"的切换，
      总量低速增长，但内部结构剧烈分化；机会不在总盘，而在赛道与排量段的选择。</strong>
      以下八条建议按【产品】【市场】【战略】【风险】分类，每条均给出量化依据、具体动作与预期效果。
    </p>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag product">产品</span>
        <span class="a-title">P1 · 把 125–250ml 作为未来三年的主战场</span>
        <span class="prio high">优先级：高</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>2025 年该区间合计 <strong>698.5 万辆</strong>，占燃油二轮 41.0%；2017→2025 年增量 +242.4 万辆，占二轮总增量的 <strong>57.6%</strong>（125-150ml +36.5%、150-250ml +117%）。2026 年内销回暖 +8.0% 大概率发生在此区间。</dd>
        <dt>具体动作</dt><dd>主力新品与新增产能投向 125–250ml；在该区间内做配置、外观与品质升级（段内升级），而非跨段跳跃。</dd>
        <dt>预期效果</dt><dd>跟随该区间即可获得高于行业均速的增量；避开 &gt;250ml 已放缓的赛道。</dd>
        <dt>实施难度</dt><dd>中（现有平台可延伸，无需全新动力总成）</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag product">产品</span>
        <span class="a-title">P2 · 大排量从"抢规模"转向"抢结构与利润"</span>
        <span class="prio high">优先级：高</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>1–7 月同期增速 +38.0% → <strong>+1.1%</strong>，跑输行业 +14.9%；赛道 CR5 已达 <strong>69.9%</strong>（春风 19.8% / 大冶 18.1% / 隆鑫 14.8% / 钱江 11.9% / 宗申 5.2%）。但 500-800ml 2024→2025 从 9.6 万增至 18.7 万辆（+95%），&gt;800ml 从 1.6 万增至 2.4 万辆（+50%），高端段仍在翻倍。</dd>
        <dt>具体动作</dt><dd>新进入者避开 250–400ml 的正面竞争（该段已被 CR5 占据）；已在局内者向 500ml 以上做差异化与品牌溢价，而非追求 250-400ml 的销量。</dd>
        <dt>预期效果</dt><dd>避免与头部在已饱和段打价格战；500ml 以上的单车毛利显著高于 250-400ml，赛道内部升级仍有空间。</dd>
        <dt>实施难度</dt><dd>高（需要动力平台与品牌溢价能力）</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag product">产品</span>
        <span class="a-title">P3 · ≤110ml 与 110-125ml 转为维护与出口走量，不再新增投入</span>
        <span class="prio mid">优先级：中</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>≤110ml 份额 30.1% → 17.4%，2017→2025 绝对量 <strong>−30.4%</strong>，是唯一负贡献段。110-125ml 绝对量十年 <strong>+0.9%</strong>（607.6 → 612.9 万辆），是最大单一排量段（2025 年占二轮 31.8%）却已停止增长。出口在这两段合计占 51.8%（2025）。</dd>
        <dt>具体动作</dt><dd>冻结该区间的新产品开发，保留产能用于出口订单与零部件通用化；把研发资源腾给 125–250ml 与 500ml 以上。</dd>
        <dt>预期效果</dt><dd>释放研发资源；该区间竞争将以成本为主，规模不经济者应主动收缩。</dd>
        <dt>实施难度</dt><dd>低</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag market">市场</span>
        <span class="a-title">P4 · 出口优先，但考核指标从"量"改为"价"</span>
        <span class="prio high">优先级：高</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>外销率 <strong>63.0%</strong>；2025 年出口 1,328.2 万辆、均价 <strong>709.1 美元（+11.5%）</strong>；但 2026 年 1–7 月均价回落至 691.6 美元（−2.5%，口径不完全可比，需跟踪）。出口在 110–150ml 段合计占 <strong>65.5%</strong>。</dd>
        <dt>具体动作</dt><dd>出口团队 KPI 增加"单车均价"与"高附加值车型占比"两项；在 110–150ml 主力段做配置升级与品牌直营，逐步替代纯贴牌。</dd>
        <dt>预期效果</dt><dd>按 2025 年出口量静态测算，<strong>单车均价每提升 5% 可增加约 4.7 亿美元出口收入</strong>（1,328.2 万辆 × 709.1 美元 × 5%）。</dd>
        <dt>实施难度</dt><dd>中</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag market">市场</span>
        <span class="a-title">P5 · 内销回暖需验证，不要提前加码专用产能</span>
        <span class="prio mid">优先级：中</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>+8.0% 只有一个 1–7 月窗口，且 2025 年同期为 −5.5%，一年之内波动 13.5pp；同期外销率仍从 60.8% 升至 63.0%。</dd>
        <dt>具体动作</dt><dd>以季度滚动跟踪内销同比，设定"连续两个季度为正"再加码；优先用现有产能的柔性切换满足回暖需求。</dd>
        <dt>预期效果</dt><dd>避免在单季信号上做出不可逆的产能决策；保留应对出口波动的产能弹性。</dd>
        <dt>实施难度</dt><dd>低</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag market">市场</span>
        <span class="a-title">P6 · 电动摩托车定位为"合规替换"，优先绑定头部而非自研整车</span>
        <span class="prio mid">优先级：中</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>2025 年 226.5 万辆（占二轮 11.7%，<strong>+3.1%</strong>，已回稳态）；赛道 CR5 <strong>76.3%</strong>，雅迪 28.6% + 绿源 17.2% + 宗申 13.4% 合计 59.2%。</dd>
        <dt>具体动作</dt><dd>不新建整车品牌（格局已定），转向为头部做配套/代工，或聚焦电动摩托车专用零部件；把 11%–12% 的稳态占比作为规划基准，<strong>不要用 2022 年 30.6% 的峰值做基准</strong>。</dd>
        <dt>预期效果</dt><dd>整车自研胜率低（CR5 76.3% 且仍在向头部集中）；供应链路线的确定性更高、资本开支更低。</dd>
        <dt>实施难度</dt><dd>中</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag strategy">战略</span>
        <span class="a-title">P7 · 用"赛道第一"替代"总份额前五"作为战略目标</span>
        <span class="prio high">优先级：高</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>全行业 CR5 <strong>36.9%</strong> 且不升反降（2024 年 38.1%），89 家在产，行业未进入整合期；而大排量 CR5 <strong>69.9%</strong>、电动 CR5 <strong>76.3%</strong>。春风动力全行业仅排第 12（2.6%），却是大排量赛道第一（19.8%）。</dd>
        <dt>具体动作</dt><dd>把三年战略目标设定为"在某一条细分赛道进入前三"（如 500ml 以上、或某个出口区域市场），而非追求总销量排名；配套调整考核与资源配置逻辑。</dd>
        <dt>预期效果</dt><dd>在总盘上规模不构成壁垒；赛道地位才能转化为定价权与品牌溢价。</dd>
        <dt>实施难度</dt><dd>高（需要战略定力与资源取舍）</dd>
      </dl>
    </div>

    <div class="adv">
      <div class="a-head">
        <span class="a-tag risk">风险</span>
        <span class="a-title">P8 · 建立出口依赖度与景气预警机制</span>
        <span class="prio high">优先级：高</span>
      </div>
      <dl>
        <dt>量化依据</dt><dd>外销率 55.1%（2024）→ 60.9%（2025）→ <strong>63.0%</strong>（2026 1–7 月）；行业对海外单一变量的敞口已达历史最高。大排量增速从 +38.0% 降至 +1.1%，而按高增速规划建设的产能在 2026 年集中释放。</dd>
        <dt>具体动作</dt><dd>设定三条预警线并明确触发后的动作：<strong>(a)</strong> 月度外销率 &gt; 65%；<strong>(b)</strong> 出口量同比连续 3 个月为负；<strong>(c)</strong> 出口单车均价同比 −5%。任一触发即启动产能、库存与订单的专项复盘。</dd>
        <dt>预期效果</dt><dd>把行业级风险转化为可操作的内部触发条件，把反应周期从"季度"缩短到"月度"。</dd>
        <dt>实施难度</dt><dd>中</dd>
      </dl>
    </div>
  </div>
</section>

<!-- ============================ 附录 ============================ -->
<section id="appendix">
  <div class="wrap">
    <div class="sec-head">
      <span class="sec-num">APPENDIX</span>
      <h2>附录</h2>
      <div class="h2-en">Appendix: Data Quality &amp; Indicator Dictionary</div>
    </div>

    <h3>A. 数据质量说明 <span class="h3-en">Data Quality Notes</span></h3>
    <div class="table-scroll">
      <table>
        <thead><tr><th style="text-align:left">分析主题</th><th style="text-align:left">可用区间</th><th style="text-align:left">已知限制</th></tr></thead>
        <tbody>
          <tr><td style="text-align:left">总量走势</td><td style="text-align:left">2016-02 ~ 2026-07</td><td style="text-align:left">缺 2016 年 8/9/10 月、2023 年 7 月</td></tr>
          <tr><td style="text-align:left">排量结构</td><td style="text-align:left">2016-02 ~ 2026-07（统一分组）</td><td style="text-align:left">细分段（如 500-800ml）仅 2023 年起可用</td></tr>
          <tr><td style="text-align:left">电动化</td><td style="text-align:left"><strong>2019 年起</strong></td><td style="text-align:left">2016-2018 口径断层（6~10 万辆/年）；三轮电动未纳入</td></tr>
          <tr><td style="text-align:left">车型结构</td><td style="text-align:left">2016-02 ~ 2026-07</td><td style="text-align:left">必须使用剔除电动的口径</td></tr>
          <tr><td style="text-align:left">出口量</td><td style="text-align:left">2016-2017 + 2023-09 起</td><td style="text-align:left"><strong>2020-2022 完全缺失</strong>；2018 仅 2 个月、2019 仅 7 个月</td></tr>
          <tr><td style="text-align:left">出口金额 / 均价</td><td style="text-align:left">2023-09 起</td><td style="text-align:left">此前源报表无金额字段</td></tr>
          <tr><td style="text-align:left">品牌集中度 / 排名</td><td style="text-align:left">2023-09 起（35 个月）</td><td style="text-align:left">2023-12 生产口径缺失 97%，已用销售口径</td></tr>
          <tr><td style="text-align:left">大排量 / 电动赛道品牌</td><td style="text-align:left">2023-09 起</td><td style="text-align:left">2026-07 品牌×排量明细不完整（低 6.6%~7.0%），赛道结论用 2025 完整年</td></tr>
          <tr><td style="text-align:left">三轮排量结构</td><td style="text-align:left">不推荐</td><td style="text-align:left">覆盖率仅约 53%，本报告未出相关结论</td></tr>
        </tbody>
      </table>
    </div>

    <h4>三轮车排量表覆盖率（缺口应为电动三轮车未纳入）</h4>
    <div class="table-scroll">
      <table>
        <thead><tr><th>年份</th><th>三轮产量(辆)</th><th>排量表覆盖(辆)</th><th>缺口(辆)</th><th>覆盖率</th></tr></thead>
        <tbody>
          <tr><td>2022</td><td>2,253,102</td><td>2,253,102</td><td>0</td><td>100.0%</td></tr>
          <tr><td>2023</td><td>2,195,911</td><td>1,791,264</td><td>404,647</td><td>81.6%</td></tr>
          <tr><td>2024</td><td>2,550,426</td><td>1,305,551</td><td>1,244,875</td><td class="neg">51.2%</td></tr>
          <tr class="hl"><td>2025</td><td>2,652,425</td><td>1,411,949</td><td>1,240,476</td><td class="neg">53.2%</td></tr>
          <tr><td>2026（1-7月）</td><td>1,585,225</td><td>891,200</td><td>694,025</td><td class="neg">56.2%</td></tr>
        </tbody>
      </table>
    </div>

    <h3>B. 主要指标口径表 <span class="h3-en">Indicator Dictionary</span></h3>
    <div class="table-scroll">
      <table>
        <thead><tr><th style="text-align:left">指标集</th><th style="text-align:left">口径</th><th style="text-align:left">用途与提示</th></tr></thead>
        <tbody>
          <tr><td style="text-align:left">monthly / yearly_production_sales</td><td style="text-align:left">全行业（二轮+三轮+电动）</td><td style="text-align:left">月度/年度产销与产销率；年度同比仅 6 个年份可比</td></tr>
          <tr><td style="text-align:left">headline_totals</td><td style="text-align:left">全行业</td><td style="text-align:left">累计产销、CAGR（2017 起）、2026 年 1-7 月速览</td></tr>
          <tr><td style="text-align:left">domestic_vs_export_split</td><td style="text-align:left">内销 = 销量 − 出口</td><td style="text-align:left">本报告最重要的结构性判断依据</td></tr>
          <tr><td style="text-align:left">export_yearly / export_monthly_total</td><td style="text-align:left">全行业出口</td><td style="text-align:left">出口量、金额、均价、外销率；2020-2022 缺失</td></tr>
          <tr><td style="text-align:left">export_vs_domestic_displacement</td><td style="text-align:left">出口二轮 vs 二轮燃油</td><td style="text-align:left">同口径对比，结论为"高度同构"</td></tr>
          <tr><td style="text-align:left">displacement_2w_share_fuel_only</td><td style="text-align:left">二轮燃油（剔除电动）</td><td style="text-align:left">观察排量升级最干净的口径，本报告主图</td></tr>
          <tr><td style="text-align:left">displacement_2w_volume</td><td style="text-align:left">二轮（生产口径）</td><td style="text-align:left">各排量段绝对量，用于增量拆解</td></tr>
          <tr><td style="text-align:left">big_displacement_2w / _ytd_1_7</td><td style="text-align:left">二轮 &gt;250ml</td><td style="text-align:left">大排量赛道；1-7 月同期序列是 2026 年唯一可比增速</td></tr>
          <tr><td style="text-align:left">electric_motorcycle / electric_monthly</td><td style="text-align:left">二轮电动（生产口径）</td><td style="text-align:left">2019 年起；三轮电动未纳入</td></tr>
          <tr><td style="text-align:left">vehicle_type_share_2w_fuel_only</td><td style="text-align:left">二轮燃油（剔除电动）</td><td style="text-align:left">车型结构必须使用本口径</td></tr>
          <tr><td style="text-align:left">brand_concentration / brand_ranking_top25</td><td style="text-align:left">全行业品牌（销售口径）</td><td style="text-align:left">CR5/CR10/CR20/HHI 与排名；仅 2023-09 起</td></tr>
          <tr><td style="text-align:left">big_displacement_brands / electric_brands</td><td style="text-align:left">细分赛道品牌</td><td style="text-align:left">赛道 CR5 与头部构成</td></tr>
          <tr><td style="text-align:left">seasonality_index</td><td style="text-align:left">全行业（完整年份）</td><td style="text-align:left">月度季节性指数（年均=100），已剔除不完整年</td></tr>
          <tr><td style="text-align:left">turning_points_yoy</td><td style="text-align:left">全行业（销售同比）</td><td style="text-align:left">波动最大的月份；含大量春节错位假象</td></tr>
          <tr><td style="text-align:left">three_wheeler_displacement_coverage</td><td style="text-align:left">三轮（生产口径）</td><td style="text-align:left">覆盖率监测，用于判断三轮排量结论不可用</td></tr>
        </tbody>
      </table>
    </div>

    <h3>C. 分析局限与免责声明 <span class="h3-en">Limitations &amp; Disclaimer</span></h3>
    <ul>
      <li>本报告的结论完全基于《全国摩托车生产企业产销情况月报》（2023.09 起）与《摩托车情报》月刊 PDF（2016.02–2023.08）两个来源的公开行业汇总数据，<strong>不包含企业财务、价格、渠道库存、终端零售等非公开数据</strong>。</li>
      <li>"内销"为「销量 − 出口」的推算值，非官方直接统计；虽然出口表与销量表已通过 63 个月零偏差校验，但两者的统计主体与申报时点可能存在细微差异。</li>
      <li>品牌明细仅覆盖 35 个月，所有品牌类结论的时间范围应理解为"近 3 年"，不可外推为长期格局。</li>
      <li>本报告对 2026 年全年总量的推算（约 2,520 万辆）基于季节性比例，属预测而非观测，实际结果取决于 8–12 月出口订单强度。</li>
      <li>报告中的所有增长率均标注了可比性；凡标注"不可比"或"—"的位置，均已核验为口径不具备可比性，请勿自行插值或估算。</li>
      <li>本报告由智数分析专家团基于数据分析引擎自动生成与人工审校，用于行业研究与内部决策参考，不构成投资或经营决策的直接依据。</li>
    </ul>
  </div>
</section>

<footer>
  <div class="wrap">
    <strong>中国摩托车行业产销数据分析报告（2016.02 – 2026.07）</strong><br>
    数据覆盖 122 个月 ｜ 累计生产 1.919 亿辆 / 累计销售 1.911 亿辆 ｜ 21 张图表 ｜ 35 个指标集<br>
    数据来源：《全国摩托车生产企业产销情况月报》（2023.09–2026.07）、《摩托车情报》月刊 PDF（2016.02–2023.08）<br>
    分析：智数分析专家团 · 数据科学工程师 赛奇（Sage）· 可视化设计师 灵犀（Lumen）· 洞察报告撰写师 若溪（Rex）<br>
    生成日期：__GEN_DATE__ ｜ 本文件为自包含单文件 HTML，可直接打开或在浏览器中打印为 PDF
  </div>
</footer>

<script>/*__ECHARTS__*/</script>
<script>/*__CHARTS__*/</script>
<script>
(function () {
  var charts = window.REPORT_CHARTS || [];
  var byId = {};
  charts.forEach(function (c) { byId[c.id] = c; });

  var instances = [];
  var used = {};

  function render(slot, chart, figNo) {
    var fig = document.createElement('figure');
    fig.className = 'chart-figure';

    var head = document.createElement('div');
    head.className = 'chart-head';
    if (figNo) {
      var no = document.createElement('span');
      no.className = 'chart-no';
      no.textContent = figNo;
      head.appendChild(no);
    }
    var t = document.createElement('h4');
    t.className = 'chart-title';
    t.textContent = chart.title || '';
    head.appendChild(t);
    if (chart.subtitle) {
      var st = document.createElement('p');
      st.className = 'chart-sub';
      st.textContent = chart.subtitle;
      head.appendChild(st);
    }

    var box = document.createElement('div');
    box.className = 'chart-canvas';
    box.style.height = (chart.height || 400) + 'px';

    fig.appendChild(head);
    fig.appendChild(box);

    if (chart.caption) {
      var cap = document.createElement('figcaption');
      cap.className = 'chart-caption';
      cap.textContent = chart.caption;   // 用 textContent，自动转义 ≤ > & 等字符
      fig.appendChild(cap);
    }

    slot.parentNode.replaceChild(fig, slot);
    var inst = echarts.init(box, null, { renderer: 'canvas' });
    inst.setOption(chart.option || {});
    instances.push(inst);
  }

  document.querySelectorAll('.chart-slot').forEach(function (slot) {
    var id = slot.getAttribute('data-chart');
    var chart = byId[id];
    if (!chart) {
      slot.innerHTML = '<div class="chart-missing">图表未找到：' + id + '</div>';
      return;
    }
    used[id] = true;
    render(slot, chart, slot.getAttribute('data-fig') || '');
  });

  // 兜底：如有未被安放的图表，追加到文末，避免遗漏
  var rest = charts.filter(function (c) { return !used[c.id]; });
  if (rest.length) {
    var host = document.createElement('section');
    host.innerHTML = '<div class="wrap"><div class="sec-head"><h2>补充图表</h2></div></div>';
    var inner = host.querySelector('.wrap');
    rest.forEach(function (c) {
      var d = document.createElement('div');
      d.className = 'chart-slot';
      d.setAttribute('data-chart', c.id);
      inner.appendChild(d);
      render(d, c, '附图');
    });
    document.body.insertBefore(host, document.querySelector('footer'));
  }

  var raf;
  window.addEventListener('resize', function () {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(function () {
      instances.forEach(function (i) { try { i.resize(); } catch (e) {} });
    });
  });

  // 打印前重新布局，确保图表宽度匹配纸张
  function relayout() {
    instances.forEach(function (i) { try { i.resize(); } catch (e) {} });
  }
  if (window.matchMedia) {
    var mq = window.matchMedia('print');
    if (mq.addEventListener) { mq.addEventListener('change', relayout); }
    else if (mq.addListener) { mq.addListener(relayout); }
  }
  window.addEventListener('beforeprint', relayout);
  window.addEventListener('afterprint', relayout);

  window.__REPORT_CHART_COUNT__ = instances.length;
})();
</script>
</body>
</html>
'''


def main():
    if not os.path.exists(SRC_ECHARTS):
        print("[ERROR] 找不到 echarts.min.js:", SRC_ECHARTS, file=sys.stderr)
        return 1
    if not os.path.exists(SRC_CHARTS):
        print("[ERROR] 找不到 report_charts.js:", SRC_CHARTS, file=sys.stderr)
        return 1

    with io.open(SRC_ECHARTS, encoding="utf-8") as f:
        echarts_js = f.read()
    with io.open(SRC_CHARTS, encoding="utf-8") as f:
        charts_js = f.read()

    # 安全检查：内联脚本中若出现 </script 会提前闭合标签
    for name, js in (("echarts.min.js", echarts_js), ("report_charts.js", charts_js)):
        if "</script" in js.lower():
            print("[WARN] %s 中含 </script，已做转义" % name, file=sys.stderr)
            js = js.replace("</script", "<\\/script")

    html = HTML.replace("__GEN_DATE__", GEN_DATE)
    html = html.replace("/*__ECHARTS__*/", echarts_js)
    html = html.replace("/*__CHARTS__*/", charts_js)

    with io.open(DST, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    size = os.path.getsize(DST)
    print("[OK] 已生成:", DST)
    print("     体积: %.2f MB (%d bytes)" % (size / 1048576.0, size))
    print("     图表数: %d" % charts_js.count('"id":'))
    return 0


if __name__ == "__main__":
    sys.exit(main())
