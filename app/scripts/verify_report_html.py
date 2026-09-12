# -*- coding: utf-8 -*-
"""报告 HTML 交付前自检：存在性 / 体积 / 内联完整性 / 标签闭合 / 占位符残留。"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "output", "摩托车产销数据分析报告.html")

if not os.path.exists(P):
    print("[FAIL] 文件不存在:", P)
    sys.exit(1)

s = io.open(P, encoding="utf-8").read()
size = os.path.getsize(P)
ok = True

print("=" * 62)
print("1. 文件与体积")
print("   路径:", P)
print("   体积: %.2f MB (%d bytes)" % (size / 1048576.0, size))
if size < 1_000_000:
    print("   [WARN] 体积偏小，可能未完整内联")
    ok = False
if size > 3_000_000:
    print("   [WARN] 体积偏大")
    ok = False

print("=" * 62)
print("2. 内联完整性")
checks = [
    ("ECharts 库", "echarts" in s and ("ECharts" in s or "zrender" in s)),
    ("echarts 全局变量", re.search(r"\becharts\b\s*=", s) is not None or "echarts" in s[:200000]),
    ("REPORT_CHARTS 声明", "window.REPORT_CHARTS" in s),
    ("REPORT_CHARTS 数组项", len(re.findall(r'"id":\s*"[a-z0-9_]+"', s)) >= 21),
    ("caption 字段", s.count('"caption"') >= 21),
]
for name, r in checks:
    print("   [%s] %s" % ("OK " if r else "FAIL", name))
    if not r:
        ok = False

n_opts = len(re.findall(r'"option":\s*\{', s))
print("   [INFO] option 块数量: %d (期望 21)" % n_opts)
if n_opts != 21:
    ok = False

print("=" * 62)
print("3. 外链 / fetch 检查（应为 0）")
bad = []
for pat in ["src=\"http", "src='http", "href=\"http", "fetch(", "XMLHttpRequest", "@import url(http"]:
    c = s.count(pat)
    print("   %-22s %d" % (pat, c))
    if c:
        bad.append(pat)

print("=" * 62)
print("4. 占位符残留")
left = [x for x in ["__GEN_DATE__", "/*__ECHARTS__*/", "/*__CHARTS__*/"] if x in s]
print("   残留:", left if left else "无")
if left:
    ok = False

print("=" * 62)
print("5. 标签闭合")
for tag in ["html", "head", "body", "section", "div", "table", "figure",
            "nav", "footer", "header", "script", "style", "dl", "ol", "ul"]:
    o = len(re.findall(r"<%s[\s>]" % tag, s))
    c = len(re.findall(r"</%s>" % tag, s))
    flag = "OK" if o == c else "MISMATCH"
    if o != c:
        ok = False
    print("   <%-8s> open=%-4d close=%-4d %s" % (tag, o, c, flag))

print("=" * 62)
print("6. 结构计数")
print("   <section> 章节数 :", len(re.findall(r'<section id="', s)))
print("   chart-slot 占位  :", s.count('class="chart-slot"'))
print("   data-chart 引用  :", s.count("data-chart="))
print("   图号 data-fig    :", len(re.findall(r'data-fig="图 \d+"', s)))
print("   <table> 表格数   :", s.count("<table>"))
print("   建议条目 .adv    :", s.count('class="adv"'))
print("   KPI 卡片         :", s.count('class="kpi'))
print("   附录/章节锚点    :", re.findall(r'<section id="([a-z0-9]+)"', s))

# 交叉核对：每个 data-chart id 必须在 REPORT_CHARTS 中存在
slot_ids = re.findall(r'data-chart="([a-z0-9_]+)"', s)
chart_ids = re.findall(r'"id":\s*"([a-z0-9_]+)"\s*,\s*"section"', s)
print("=" * 62)
print("7. 图表 ID 交叉核对")
print("   占位引用 %d 个，图表定义 %d 个" % (len(slot_ids), len(chart_ids)))
missing = [i for i in slot_ids if i not in chart_ids]
unused = [i for i in chart_ids if i not in slot_ids]
dup = [i for i in set(slot_ids) if slot_ids.count(i) > 1]
print("   占位但无定义:", missing if missing else "无")
print("   有定义未放置:", unused if unused else "无")
print("   重复放置    :", dup if dup else "无")
if missing or unused or dup:
    ok = False

print("=" * 62)
print("结论:", "PASS — 报告可正常打开" if ok else "FAIL — 存在问题，需修复")
sys.exit(0 if ok else 1)
