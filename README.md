# 摩托车产销数据看板 / Motorcycle Production & Sales Dashboard

中国摩托车产销月度数据交互式看板。覆盖 **2016年2月 至 2026年6月**（121 个月）的摩托车生产、销售、出口数据，支持按年份、月份、排量段、车型、品牌多维筛选。

An interactive dashboard for China's monthly motorcycle production & sales data, covering Feb 2016 – Jun 2026 (121 months), with filtering by year, month, displacement, vehicle type, and brand.

## 在线访问 / Live Demo

部署后访问 / After deployment: `https://<your-username>.github.io/<repo-name>/`

## 功能特性 / Features

- **月度趋势 / Monthly Trend** — 生产/销售走势、产销率、环比增速
- **排量分布 / Displacement** — 二轮/三轮按排量段分布、热力图、主流排量趋势
- **车型分布 / Vehicle Types** — 跨骑/弯梁/踏板结构演变
- **品牌排名 / Brands** — Top 品牌排行、市场份额、品牌销量对比、大排量（>250ml）排名
- **内销外销 / Domestic & Export** — 内销 vs 出口对比、外销率、出口金额、出口品牌排名
- **年度报告 / Annual Report** — 年度产销量、同比增速、累计库存、大排量增长、电动化占比
- 中英文双语界面，西方计数方式（K/M/B）

## 文件说明 / Files

| 文件 | 说明 |
|------|------|
| `index.html` | 看板入口 / Entry point |
| `dashboard.js` | 交互逻辑 / Interaction logic |
| `dashboard_data.json` | 数据源（约 10MB）/ Data source (~10MB) |
| `echarts.min.js` | 图表库（本地化，离线可用）/ Chart library (local, offline-ready) |

## 技术栈 / Tech Stack

纯静态站点，无构建步骤，无后端依赖。基于 [Apache ECharts](https://echarts.apache.org/) 渲染图表。

Pure static site, no build step, no backend dependency. Charts rendered with Apache ECharts.

## 本地运行 / Run Locally

任选一种方式 / Either way:

```bash
# 方式一：任意静态服务器 / Any static server
cd 项目目录
python -m http.server 8765
# 访问 http://localhost:8765/

# 方式二：带「上传更新」功能 / With upload-update feature
python server.py 8765
# 访问 http://localhost:8765/dashboard.html
```

## 关于「上传更新」功能 / About Upload-Update

本仓库为**静态部署版本**，用于只读浏览。**「上传月度 Excel 更新报告」**功能依赖 Python 后端（`server.py`），需在本地运行，线上静态托管不支持。

This repo is a **static-deployment version** for read-only browsing. The monthly Excel upload-update feature requires the Python backend (`server.py`) and only works locally.

## 数据说明 / Data Notes

- 数据来源：全国摩托车生产企业产销情况月报 / Source: national motorcycle manufacturer monthly production & sales reports
- 2020–2022 年出口数据缺失（源报表当年取消了分排量出口表）
- Export data for 2020–2022 is missing (the source reports dropped the displacement-level export table in those years)

## License

[MIT](LICENSE)
