# -*- coding: utf-8 -*-
"""交付前独立验收：摩托车产销数据分析报告.html"""
import io
import os
import re
import sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
p = os.path.normpath(os.path.join(OUT, "摩托车产销数据分析报告.html"))

s = io.open(p, encoding="utf-8").read()
size = os.path.getsize(p)

print("file      :", os.path.abspath(p))
print("size      : %.2f MB (%d bytes)" % (size / 1048576.0, size))
print("外链 http :", len(re.findall(r"(?:src|href)=.http", s)))
print("fetch/XHR :", s.count("fetch(") + s.count("XMLHttpRequest"))
print("REPORT_CHARTS 定义 :", s.count("window.REPORT_CHARTS"))
m = re.search(r'version:\s*"?(5\.\d+\.\d+)', s)
print("echarts 版本 :", m.group(1) if m else "NOT FOUND")

slots = re.findall(r'data-chart="([a-z0-9_]+)"', s)
figs = re.findall(r'data-fig="([^"]+)"', s)
print("图表占位  : %d (唯一 %d)" % (len(slots), len(set(slots))))
print("图号      : %d  %s ... %s" % (len(figs), figs[:3], figs[-2:]))

ids = re.findall(r'id:\s*"([a-z0-9_]+)"', s)
print("option 定义: %d (唯一 %d)" % (len(ids), len(set(ids))))
missing = [x for x in slots if x not in set(ids)]
unused = [x for x in set(ids) if x not in set(slots)]
print("占位缺失定义 :", missing or "无")
print("定义未被放置 :", unused or "无")

print("章节      :", re.findall(r'<section id="([a-z0-9]+)"', s))
print("表格      :", s.count("<table"))
print("中文字数  :", len(re.findall(r"[\u4e00-\u9fff]", s)))

# 关键口径红线扫描
bad = []
if re.search(r"2024[^。]{0,20}同比[^。]{0,10}\+?12\.6", s):
    bad.append("出现 2024 vs 2023 +12.6%")
if re.search(r"比2023年增长12\.6", s):
    bad.append("出现 2023 增长 12.6%")
print("红线扫描  :", "发现问题 -> " + "; ".join(bad) if bad else "未发现禁用表述")

# 标签闭合
for tag in ["html", "head", "body", "section", "div", "table", "script", "style", "nav"]:
    o = len(re.findall(r"<%s[\s>]" % tag, s))
    c = len(re.findall(r"</%s>" % tag, s))
    flag = "OK" if o == c else "MISMATCH"
    print("  <%s> open=%d close=%d  %s" % (tag, o, c, flag))
