/* Motorcycle dashboard — interactive ECharts visualization */
(async function() {
  const PALETTE = {
    prod: '#1e40af',
    sales: '#c0392b',
    prodLight: '#93c5fd',
    salesLight: '#fca5a5',
    accent: '#16a34a',
    amber: '#f59e0b',
    purple: '#7c3aed',
    gray: '#9ca3af',
  };
  const DISP_COLORS = [
    '#1e3a8a', '#3b82f6', '#06b6d4', '#10b981', '#84cc16',
    '#f59e0b', '#f97316', '#ef4444', '#dc2626', '#b91c1c',
    '#7c3aed', '#a855f7', '#ec4899', '#f43f5e', '#0ea5e9',
    '#22c55e',
  ];

  // 排量段固定颜色映射：同一排量段在所有图表、图例、下拉框中颜色一致
  // 按排量从小到大，用确定性哈希映射到色板，保证稳定不随位置变化
  const DISP_ORDER = [
    '排量≤50ml', '50ml<排量≤60ml', '60ml<排量≤70ml', '70ml<排量≤80ml',
    '80ml<排量≤90ml', '90ml<排量≤100ml', '100ml<排量≤110ml', '110ml<排量≤125ml',
    '125ml<排量≤150ml', '150ml<排量≤200ml', '200ml<排量≤250ml', '250ml<排量≤400ml',
    '400ml<排量≤500ml', '500ml<排量≤800ml', '排量>800ml',
    // 历史合并段（口径变化产生的段）
    '150ml<排量≤250ml', '400ml<排量≤750ml', '排量>750ml',
    // 三轮特有段
    '50ml<排量≤100ml', '100ml<排量≤150ml', '125ml<排量≤150ml', '排量>250ml',
    '250ml<排量≤400ml',
    // 电动
    '电动摩托车',
  ];
  // 固定色板（24 色高对比离散色板，排量段在堆叠柱状图中清晰区分）
  // 按排量从小到大：冷色(小排量) → 暖色(大排量) → 深色(超大/电动)
  const DISP_PALETTE = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
    '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#2f4554',
    '#61a0a8', '#d48265', '#749f83', '#ca8622', '#bda29a',
    '#6e7074', '#546570', '#c4ccd3', '#f05b72', '#905a3d',
    '#7ec2f3', '#0aa3b4', '#e6a23c', '#67c23a',
  ];
  const DISP_COLOR_MAP = {};
  DISP_ORDER.forEach((name, i) => { DISP_COLOR_MAP[name] = DISP_PALETTE[i % DISP_PALETTE.length]; });
  function dispColor(name) {
    // 归一化：去掉 scope 前缀（如 '二轮|110ml<排量≤125ml' -> '110ml<排量≤125ml'）
    const key = String(name).includes('|') ? String(name).split('|').pop() : String(name);
    if (DISP_COLOR_MAP[key]) return DISP_COLOR_MAP[key];
    // 兜底：确定性哈希
    let h = 0; for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) % DISP_PALETTE.length;
    return DISP_PALETTE[h];
  }
  // >250ml 大排量段（严格大于 250，不含 200-250、150-250）
  const LARGE_DISP = ['250ml<排量≤400ml', '400ml<排量≤500ml', '400ml<排量≤750ml', '500ml<排量≤800ml', '排量>750ml', '排量>800ml'];

  // 双语标签 Bilingual labels
  const L = {
    生产: '生产 Production',
    销售: '销售 Sales',
    内销: '内销 Domestic',
    出口: '出口 Export',
    内销占比: '内销占比 Domestic %',
    出口占比: '出口占比 Export %',
    累计库存: '累计库存 Cumulative Inventory',
    同比增速: '同比增速 YoY %',
    生产同比: '生产同比 Prod YoY',
    销售同比: '销售同比 Sales YoY',
    生产MoM: '生产 MoM',
    销售MoM: '销售 MoM',
    总产量: '总产量 Total Prod',
    总销量: '总销量 Total Sales',
    电动产量: '电动产量 EV Prod',
    电动占比: '电动占比 EV %',
    差值: '差值(销-产) Diff',
  };

  // ---- Load data ----
  let RAW;
  try {
    const r = await fetch('dashboard_data.json');
    RAW = await r.json();
  } catch (e) {
    document.body.insertAdjacentHTML('afterbegin',
      `<div style="padding:20px;background:#fee;color:#c00;">无法加载 dashboard_data.json: ${e.message}</div>`);
    return;
  }

  // Quick indexes
  const monthlyTotal = RAW.monthly_total;          // [{year, month, indicator, value}]
  const byDisp2w = RAW.by_displacement_2w;        // [{year, month, indicator, category, value}]
  const byDisp3w = RAW.by_displacement_3w;
  const byVtype = RAW.by_vehicle_type;
  const byMfg = RAW.by_manufacturer;
  const mfgDisp = RAW.mfg_displacement || [];   // 厂家 × 排量（新增维度）
  const yearlyTotal = RAW.yearly_total;
  const yearlyDisp2w = RAW.yearly_by_displacement_2w;
  const yearlyDisp3w = RAW.yearly_by_displacement_3w;
  const yearlyVtype = RAW.yearly_by_vehicle_type;
  const yearlyMfg = RAW.yearly_by_manufacturer;
  const mfgAll = RAW.mfg_all_time_totals;
  const exportMonthly = RAW.export_monthly || [];   // [{year,month,scope,category,type,value}]
  const exportAmount = RAW.export_amount || [];     // [{year,month,amount}]
  const exportMfg = RAW.export_mfg || [];           // [{year,month,manufacturer,value}]
  const exportTotal = RAW.export_total || [];       // [{year,month,value}]
  const META = RAW.meta;

  document.getElementById('dataRange').textContent =
    `${META.years[0]} 年 ${firstAvailMonth()} 月 — ${META.years[META.years.length-1]} 年 ${lastAvailMonth()} 月`;

  function firstAvailMonth() {
    const k = `${META.years[0]}`;
    const min = monthlyTotal.filter(r => r.year === META.years[0]).reduce((a, r) => Math.min(a, r.month), 13);
    return min;
  }
  function lastAvailMonth() {
    const lastYear = META.years[META.years.length-1];
    const max = monthlyTotal.filter(r => r.year === lastYear).reduce((a, r) => Math.max(a, r.month), 0);
    return max;
  }

  // ---- Populate filter controls ----
  const fYear = document.getElementById('fYear');
  const fMonth = document.getElementById('fMonth');
  const fIndicator = document.getElementById('fIndicator');
  const fScope = document.getElementById('fScope');
  const fDisp = document.getElementById('fDisp');
  const fMfg = document.getElementById('fMfg');
  const fReportType = document.getElementById('fReportType');
  const fDispPreset = document.getElementById('fDispPreset');
  const fPowertrain = document.getElementById('fPowertrain');

  META.years.forEach(y => {
    const o = document.createElement('option'); o.value = y; o.textContent = `${y} 年`; o.selected = true;
    fYear.appendChild(o);
  });
  META.months.forEach(m => {
    const o = document.createElement('option'); o.value = m; o.textContent = `${m} 月`; o.selected = true;
    fMonth.appendChild(o);
  });
  META.manufacturers.forEach(name => {
    const o = document.createElement('option'); o.value = name; o.textContent = name;
    fMfg.appendChild(o);
  });
  // 排量段下拉：按 scope 分组（二轮 / 三轮 / 电动），值带 scope 前缀消除同名段重叠
  // 每个选项前加颜色圆点，颜色与该排量段在图表中的颜色一致
  const DISP_GROUPS = META.displacement_groups || [];
  DISP_GROUPS.forEach(g => {
    const og = document.createElement('optgroup');
    og.label = g.label;
    (g.buckets || []).forEach(b => {
      const o = document.createElement('option');
      o.value = `${g.scope}|${b}`;         // 值带 scope，避免二轮/三轮同名段冲突
      o.dataset.scope = g.scope;
      o.dataset.bucket = b;
      // 颜色圆点 + 段名
      o.textContent = `● ${b}`;
      o.style.color = dispColor(b);        // 文字也染成该段颜色
      og.appendChild(o);
    });
    fDisp.appendChild(og);
  });

  // ---- Tab switching ----
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      document.querySelector(`[data-pane="${t.dataset.tab}"]`).classList.add('active');
      // Trigger resize for any newly-visible chart
      Object.values(charts).forEach(c => c && c.resize());
    });
  });

  // ---- Initialize charts ----
  const charts = {};
  ['chartTrend', 'chartRatio', 'chartMom',
   'chartDisp2wYear', 'chartDisp3wYear', 'chartDispHeatmap', 'chartDispLines',
   'chartVtypePie', 'chartVtypeStacked', 'chartVtype3w',
   'chartMfgRank', 'chartMfgPie', 'chartMfgTrend', 'chartMfgRankChange',
   'chartMfgCompareBar', 'chartMfgCompareTrend',
   'chartMfgLargeDisp', 'chartMfgLargePie',
   'chartExportStack', 'chartExportRatio', 'chartExportAmt', 'chartExportMfg', 'chartExportDisp', 'chartExportYear',
   'chartExportCompare', 'chartExportShare',
   'chartExportType', 'chartExportLarge',
   'chartAnnualTotal', 'chartAnnualYoy', 'chartEvShare', 'chartLargeDisp',
  ].forEach(id => {
    charts[id] = echarts.init(document.getElementById(id), null, { renderer: 'canvas' });
  });

  // ---- Filter helpers ----
  function getFilters() {
    // 排量选项值形如 "scope|bucket"（如 "二轮|110ml<排量≤125ml"），拆成 {scope, bucket}
    const displacements = Array.from(fDisp.selectedOptions).map(o => {
      const [scope, bucket] = o.value.split('|');
      return { scope, bucket };
    });
    return {
      years: Array.from(fYear.selectedOptions).map(o => +o.value),
      months: Array.from(fMonth.selectedOptions).map(o => +o.value),
      indicator: fIndicator.value,
      scope: fScope.value,
      displacements,
      mfgs: Array.from(fMfg.selectedOptions).map(o => o.value),
      reportType: fReportType.value,
      dispPreset: fDispPreset.value,
      powertrain: fPowertrain.value,
    };
  }

  // 动力类型筛选：category === '电动摩托车' 视为电动，其他（含二轮/三轮各排量段）视为燃油
  function powertrainMatch(category, pt) {
    if (pt === 'all' || !pt) return true;
    if (pt === 'ev') return category === '电动摩托车';
    if (pt === 'ice') return category !== '电动摩托车';
    return true;
  }

  // 判断某条 mfg_displacement 记录是否命中已选排量（带 scope 匹配）
  function dispMatch(row, displacements) {
    if (!displacements.length) return true;
    return displacements.some(d => d.scope === row.scope && d.bucket === row.category);
  }

  // 宽松排量匹配：把用户选的细分段映射到历史合并段（用于内销外销页）。
  // 历史口径（2016-2019）排量段更粗：100-125（含110-125）、50-100（含50-60等）、150-250（含150-200/200-250）
  function dispMatchLoose(bucket, displacements) {
    if (!displacements.length) return true;
    const buckets = displacements.map(d => d.bucket);
    if (buckets.includes(bucket)) return true;
    // 110-125 或 100-110 → 历史合并段 100-125
    if ((buckets.includes('110ml<排量≤125ml') || buckets.includes('100ml<排量≤110ml')) &&
        bucket === '100ml<排量≤125ml') return true;
    // 50-60/60-70/70-80/80-90/90-100 → 历史合并段 50-100
    const sub50 = ['50ml<排量≤60ml','60ml<排量≤70ml','70ml<排量≤80ml','80ml<排量≤90ml','90ml<排量≤100ml'];
    if (sub50.some(b => buckets.includes(b)) && bucket === '50ml<排量≤100ml') return true;
    // 150-200 / 200-250 → 历史合并段 150-250
    if ((buckets.includes('150ml<排量≤200ml') || buckets.includes('200ml<排量≤250ml')) &&
        bucket === '150ml<排量≤250ml') return true;
    // 400-500 / 500-800 / >800 → 历史合并段 400-750 / >750
    if ((buckets.includes('400ml<排量≤500ml') || buckets.includes('500ml<排量≤800ml') || buckets.includes('排量>800ml')) &&
        (bucket === '400ml<排量≤750ml' || bucket === '排量>750ml')) return true;
    return false;
  }

  function applyFilters(records, f) {
    return records.filter(r =>
      f.years.includes(r.year) &&
      f.months.includes(r.month) &&
      (f.indicator === 'both' || r.indicator === f.indicator) &&
      (f.mfgs.length === 0 || (r.manufacturer && f.mfgs.includes(r.manufacturer)))
    );
  }

  // 车型范围 → mfg_displacement 的 scope 字段
  // 电动摩托车主是二轮轻便/二轮摩托，所以 '二轮' 时一并纳入
  function scopeMatch(rowScope, fScope) {
    if (fScope === 'all') return true;
    if (fScope === '二轮') return rowScope === '二轮' || rowScope === '电动';
    return rowScope === fScope;
  }

  /**
   * 排量感知的数据源切换。
   * 未选排量 → 直接用官方月度总计 / 厂家总计（精度最高）
   * 选了排量 → 从「厂家 × 排量」明细聚合出等价的月度总计 / 厂家数据
   * 这样下游所有图表无需关心数据来自哪里。
   */
  function buildData(f, extraYears) {
    const years = extraYears ? [...new Set([...f.years, ...extraYears])] : f.years;

    if (!f.displacements.length) {
      const ff = Object.assign({}, f, { years });
      return { totals: applyFilters(monthlyTotal, ff), mfg: applyFilters(byMfg, ff), source: 'total' };
    }

    const rows = mfgDisp.filter(r =>
      years.includes(r.year) &&
      f.months.includes(r.month) &&
      dispMatch(r, f.displacements) &&
      (f.indicator === 'both' || r.indicator === f.indicator) &&
      (f.mfgs.length === 0 || f.mfgs.includes(r.manufacturer)) &&
      scopeMatch(r.scope, f.scope)
    );

    // 聚合为月度总计（同一厂家在二冲程页/四冲程页各出现一次，需相加）
    const tMap = new Map();
    const mMap = new Map();
    rows.forEach(r => {
      const tk = `${r.year}|${r.month}|${r.indicator}`;
      tMap.set(tk, (tMap.get(tk) || 0) + r.value);
      const mk = `${r.year}|${r.month}|${r.indicator}|${r.manufacturer}`;
      mMap.set(mk, (mMap.get(mk) || 0) + r.value);
    });

    const totals = [...tMap.entries()].map(([k, v]) => {
      const [y, mo, ind] = k.split('|');
      return { year: +y, month: +mo, indicator: ind, value: v };
    });
    const mfg = [...mMap.entries()].map(([k, v]) => {
      const i = k.indexOf('|', k.indexOf('|', k.indexOf('|') + 1) + 1);
      const [y, mo, ind] = k.slice(0, i).split('|');
      return { year: +y, month: +mo, indicator: ind, manufacturer: k.slice(i + 1), value: v };
    });
    return { totals, mfg, source: 'displacement' };
  }

  // 西方计数：K=千, M=百万, B=十亿；千分位逗号
  function fmt(n) {
    if (n === null || n === undefined) return '—';
    const a = Math.abs(n);
    if (a >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return Math.round(n).toLocaleString('en-US');
    return Math.round(n).toLocaleString('en-US');
  }
  function fmtPct(n) {
    if (n === null || n === undefined) return '—';
    return (n >= 0 ? '+' : '') + n.toFixed(1) + '%';
  }
  // 金额格式化：输入单位为「万美元」，转为美元后按西方计数（K/M/B）
  function fmtAmt(n) {
    if (n === null || n === undefined) return '—';
    const usd = n * 10000; // 万美元 → 美元
    const a = Math.abs(usd);
    if (a >= 1e9) return '$' + (usd / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return '$' + (usd / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return '$' + Math.round(usd).toLocaleString('en-US');
    return '$' + Math.round(usd).toLocaleString('en-US');
  }

  // ---- KPI calculation ----
  // mfg: 厂家数据（可选），用于统计活跃厂家数（monthly_total 无厂家字段）
  function updateKPIs(filtered, mfg) {
    const total = { 生产: 0, 销售: 0 };
    const monthsSet = new Set();
    filtered.forEach(r => {
      total[r.indicator] += r.value;
      monthsSet.add(`${r.year}-${r.month}`);
    });
    document.getElementById('kpiProd').textContent = fmt(total.生产);
    document.getElementById('kpiSales').textContent = fmt(total.销售);
    document.getElementById('kpiRatio').textContent =
      total.生产 ? ((total.销售 / total.生产) * 100).toFixed(1) + '%' : '—';
    // 活跃厂家数：优先从厂家明细去重，否则从 monthly_total 兼容
    const mfgsSet = new Set();
    (mfg || []).forEach(r => { if (r.manufacturer) mfgsSet.add(r.manufacturer); });
    if (!mfgsSet.size) filtered.forEach(r => { if (r.manufacturer) mfgsSet.add(r.manufacturer); });
    document.getElementById('kpiMfg').textContent = mfgsSet.size;

    // YoY delta (vs same months last year)
    const f = getFilters();
    const monthsCount = monthsSet.size;
    if (monthsCount > 0) {
      const lastYM = [...monthsSet].sort().pop();
      const lastY = +lastYM.split('-')[0];
      const prevY = lastY - 1;
      const inFilterMonths = (year) => filtered.filter(r =>
        r.year === year && f.months.includes(r.month)
      ).reduce((acc, r) => { acc[r.indicator] = (acc[r.indicator] || 0) + r.value; return acc; }, {});
      const samePeriodLastYear = (year) => {
        const same = monthlyTotal.filter(r =>
          r.year === year && f.months.includes(r.month) &&
          (f.indicator === 'both' || r.indicator === f.indicator)
        ).reduce((acc, r) => { acc[r.indicator] = (acc[r.indicator] || 0) + r.value; return acc; }, {});
        return same;
      };
      const lastYearData = samePeriodLastYear(lastY);
      const prevYearData = samePeriodLastYear(prevY);
      const indicators = f.indicator === 'both' ? ['生产', '销售'] : [f.indicator];
      let prodDeltaText = '', salesDeltaText = '';
      indicators.forEach(ind => {
        const cur = ind === '生产' ? total.生产 : total.销售;
        const base = lastYearData[ind] || 0;
        if (base > 0) {
          const pct = ((cur - base) / base) * 100;
          const cls = pct >= 0 ? 'up' : 'down';
          const arrow = pct >= 0 ? '↑' : '↓';
          const txt = `<span class="${cls}">同比 ${lastY} 年同期 ${arrow} ${fmtPct(pct)}</span>`;
          if (ind === '生产') prodDeltaText = txt;
          else salesDeltaText = txt;
        }
      });
      document.getElementById('kpiProdDelta').innerHTML = prodDeltaText;
      document.getElementById('kpiSalesDelta').innerHTML = salesDeltaText;
    }

    const ratio = total.生产 ? (total.销售 / total.生产) : 0;
    document.getElementById('kpiRatioHint').innerHTML =
      `<span class="${ratio >= 1 ? 'up' : 'down'}">${ratio >= 1 ? '供不应求' : '供过于求'}</span>`;
    document.getElementById('kpiMfgHint').innerHTML =
      `共 ${mfgsSet.size} 个品牌在筛选范围内有生产/销售记录 ${mfgsSet.size} brands with records`;
  }

  // ---- Chart: Monthly Trend ----
  // baseline: 同一筛选口径下、额外包含上一年的数据，用于算同比
  function renderTrend(filtered, baseline) {
    const base = baseline || filtered;
    const months = sortedMonths(filtered);
    const prodData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const r = filtered.find(x => x.year === y && x.month === m && x.indicator === '生产');
      return r ? r.value : null;
    });
    const salesData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const r = filtered.find(x => x.year === y && x.month === m && x.indicator === '销售');
      return r ? r.value : null;
    });

    // YoY % (vs same month last year) — 基准必须与当前口径一致（同排量/同厂家）
    const yoyProd = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const prevR = base.find(x => x.year === y - 1 && x.month === m && x.indicator === '生产');
      const curR = filtered.find(x => x.year === y && x.month === m && x.indicator === '生产');
      if (!prevR || !curR || !prevR.value) return null;
      return +(((curR.value - prevR.value) / prevR.value) * 100).toFixed(1);
    });
    const yoySales = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const prevR = base.find(x => x.year === y - 1 && x.month === m && x.indicator === '销售');
      const curR = filtered.find(x => x.year === y && x.month === m && x.indicator === '销售');
      if (!prevR || !curR || !prevR.value) return null;
      return +(((curR.value - prevR.value) / prevR.value) * 100).toFixed(1);
    });

    charts.chartTrend.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: [L.生产, L.销售, L.生产同比, L.销售同比], top: 0 },
      grid: { left: 70, right: 70, top: 40, bottom: 60 },
      xAxis: {
        type: 'category',
        data: months,
        axisLabel: {
          rotate: 30,
          // 1 月高亮显示年份（如「2018年」），其余月份只显示数字（节省空间）
          formatter: v => {
            const [y, m] = v.split('-').map(Number);
            return m === 1 ? `${y}年` : `${m}月`;
          },
          fontSize: 10,
        },
      },
      yAxis: [
        { type: 'value', name: '辆 Units', position: 'left', axisLabel: { formatter: fmt } },
        { type: 'value', name: '同比 YoY %', position: 'right', axisLabel: { formatter: '{value}%' } },
      ],
      series: [
        { name: L.生产, type: 'line', smooth: true, data: prodData, itemStyle: { color: PALETTE.prod },
          areaStyle: { opacity: 0.15, color: PALETTE.prod },
          markLine: { silent: true, symbol: 'none',
            data: yearBoundaries(months).map(y => ({ xAxis: `${y}-01` })),
            lineStyle: { color: '#d1d5db', type: 'dashed', width: 1 } } },
        { name: L.销售, type: 'line', smooth: true, data: salesData, itemStyle: { color: PALETTE.sales },
          areaStyle: { opacity: 0.15, color: PALETTE.sales } },
        { name: L.生产同比, type: 'bar', yAxisIndex: 1, data: yoyProd, itemStyle: { color: PALETTE.prodLight, opacity: 0.7 } },
        { name: L.销售同比, type: 'bar', yAxisIndex: 1, data: yoySales, itemStyle: { color: PALETTE.salesLight, opacity: 0.7 } },
      ],
      dataZoom: [
        { type: 'inside' },
        // 默认显示最近 ~50% 数据（约 5 年），用户可拖动滑块查看 2016 至今全部
        { type: 'slider', height: 20, bottom: 15, start: 50, end: 100 },
      ],
    });
  }

  // ---- Chart: Sales/Production Ratio ----
  function renderRatio(filtered) {
    const months = sortedMonths(filtered);
    const ratios = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const prodR = filtered.find(x => x.year === y && x.month === m && x.indicator === '生产');
      const salesR = filtered.find(x => x.year === y && x.month === m && x.indicator === '销售');
      if (!prodR || !salesR || !prodR.value) return null;
      return +((salesR.value / prodR.value) * 100).toFixed(2);
    });

    charts.chartRatio.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => v ? v.toFixed(2) + '%' : '—' },
      grid: { left: 60, right: 30, top: 20, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', name: '产销率 %', axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line', smooth: true, data: ratios,
        markLine: { data: [{ yAxis: 100, label: { formatter: '100%' }, lineStyle: { color: PALETTE.gray, type: 'dashed' } }] },
        itemStyle: { color: PALETTE.purple },
        areaStyle: { opacity: 0.1, color: PALETTE.purple },
      }],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 10 }],
    });
  }

  // ---- Chart: Month-over-Month Bar ----
  function renderMonthBar(filtered) {
    const months = sortedMonths(filtered);
    const prodData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const r = filtered.find(x => x.year === y && x.month === m && x.indicator === '生产');
      return r ? r.value : 0;
    });
    const salesData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const r = filtered.find(x => x.year === y && x.month === m && x.indicator === '销售');
      return r ? r.value : 0;
    });
    const diff = salesData.map((v, i) => v - prodData[i]);

    charts.chartMonthBar.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: [L.生产, L.销售, L.差值], top: 0 },
      grid: { left: 70, right: 70, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: [
        { type: 'value', axisLabel: { formatter: fmt } },
        { type: 'value', axisLabel: { formatter: fmt } },
      ],
      series: [
        { name: L.生产, type: 'bar', data: prodData, itemStyle: { color: PALETTE.prod } },
        { name: L.销售, type: 'bar', data: salesData, itemStyle: { color: PALETTE.sales } },
        { name: L.差值, type: 'line', yAxisIndex: 1, data: diff,
          itemStyle: { color: PALETTE.accent }, smooth: true, lineStyle: { width: 2 } },
      ],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 14, bottom: 5 }],
    });
  }

  // ---- Chart: MoM growth ----
  // full: 同一筛选口径下的完整月度序列（供跨出 last12 窗口时取上月）
  function renderMoM(filtered, full) {
    const all = full || filtered;
    const allMonths = sortedMonths(all);
    const months = sortedMonths(filtered);
    const last12 = months.slice(-12);
    const mom = (ym, indicator) => {
      const idx = allMonths.indexOf(ym);
      if (idx <= 0) return null;
      const [y, m] = ym.split('-').map(Number);
      const [py, pm] = allMonths[idx - 1].split('-').map(Number);
      const cur = filtered.find(x => x.year === y && x.month === m && x.indicator === indicator);
      const prev = all.find(x => x.year === py && x.month === pm && x.indicator === indicator);
      if (!cur || !prev || !prev.value) return null;
      return +(((cur.value - prev.value) / prev.value) * 100).toFixed(1);
    };
    const prodMom = last12.map(ym => mom(ym, '生产'));
    const salesMom = last12.map(ym => mom(ym, '销售'));

    charts.chartMom.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => v === null ? '—' : v + '%' },
      legend: { data: ['生产 MoM Production MoM', '销售 MoM Sales MoM'], top: 0 },
      grid: { left: 60, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: last12, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [
        { name: '生产 MoM Production MoM', type: 'line', data: prodMom, itemStyle: { color: PALETTE.prod }, smooth: true, lineStyle: { width: 2.5 }, symbol: 'circle', symbolSize: 6,
          markLine: { silent: true, symbol: 'none', label: { formatter: '0%', position: 'end' }, lineStyle: { color: '#94a3b8', type: 'dashed' }, data: [{ yAxis: 0 }] } },
        { name: '销售 MoM Sales MoM', type: 'line', data: salesMom, itemStyle: { color: PALETTE.sales }, smooth: true, lineStyle: { width: 2.5 }, symbol: 'circle', symbolSize: 6,
          markLine: { silent: true, symbol: 'none', label: { formatter: '0%', position: 'end' }, lineStyle: { color: '#94a3b8', type: 'dashed' }, data: [{ yAxis: 0 }] } },
      ],
    });
  }

  // ---- Chart: 2W Displacement by Year ----
  function renderDisp2wYear(filtered) {
    const years = sortedYears(filtered);
    const buckets = META.displacement_2w;
    const series = buckets.map((b, i) => ({
      name: b, type: 'bar', stack: 'total',
      data: years.map(y => {
        const sum = filtered.filter(r => r.year === y && r.category === b)
          .reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: dispColor(b) },
    }));
    charts.chartDisp2wYear.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      // 图例放底部（支持多行），确保所有 19 个排量段都能显示
      legend: { bottom: 0, left: 'center', textStyle: { fontSize: 10 },
        itemWidth: 14, itemHeight: 10, itemGap: 8 },
      grid: { left: 70, right: 30, top: 30, bottom: 90 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
    });
  }

  // ---- Chart: 3W Displacement by Year ----
  function renderDisp3wYear(filtered) {
    const years = sortedYears(filtered);
    const buckets = META.displacement_3w;
    const series = buckets.map((b, i) => ({
      name: b, type: 'bar', stack: 'total',
      data: years.map(y => {
        const sum = filtered.filter(r => r.year === y && r.category === b)
          .reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: dispColor(b) },
    }));
    charts.chartDisp3wYear.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      // 图例放底部，确保所有排量段都能显示
      legend: { bottom: 0, left: 'center', textStyle: { fontSize: 10 },
        itemWidth: 14, itemHeight: 10, itemGap: 8 },
      grid: { left: 70, right: 30, top: 30, bottom: 90 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
    });
  }

  // ---- Chart: Displacement Heatmap (months × buckets) ----
  function renderDispHeatmap(f) {
    f = f || getFilters();
    // 排量筛选后只显示选中的行（二轮口径）
    const buckets = f.displacements.length
      ? f.displacements.filter(d => d.scope === '二轮').map(d => d.bucket)
      : META.displacement_2w;
    const src = applyDispFilter(byDisp2w, f);
    const allMonths = sortedMonths(src.length ? src : byDisp2w);
    const data = [];
    let maxV = 0;
    buckets.forEach((b, y) => {
      allMonths.forEach((ym, x) => {
        const [yr, mo] = ym.split('-').map(Number);
        const r = src.find(k => k.year === yr && k.month === mo && k.category === b);
        const v = r ? r.value : 0;
        data.push([x, y, Math.round(v)]);
        if (v > maxV) maxV = v;
      });
    });
    charts.chartDispHeatmap.setOption({
      tooltip: { formatter: p => `${buckets[p.value[1]]}<br/>${allMonths[p.value[0]]}<br/>${fmt(p.value[2])}` },
      grid: { left: 130, right: 20, top: 20, bottom: 60 },
      xAxis: { type: 'category', data: allMonths, axisLabel: { rotate: 45, fontSize: 10 }, splitArea: { show: true } },
      yAxis: { type: 'category', data: buckets, splitArea: { show: true } },
      visualMap: { min: 0, max: maxV, calculable: true, orient: 'vertical', right: 0, top: 'center',
        inRange: { color: ['#f0f9ff', '#0c4a6e'] }, text: ['高', '低'], textStyle: { fontSize: 10 } },
      series: [{ name: '生产/销售', type: 'heatmap', data: data, label: { show: false } }],
    });
  }

  // ---- Chart: Major Displacement Trends ----
  function renderDispLines(f) {
    f = f || getFilters();
    const preset = ['100ml<排量≤110ml', '110ml<排量≤125ml', '125ml<排量≤150ml',
                    '150ml<排量≤200ml', '250ml<排量≤400ml', '电动摩托车'];
    // 用户选了排量就画选中的，否则画预设的几段
    const main = f.displacements.length
      ? f.displacements.filter(d => d.scope === '二轮').map(d => d.bucket)
      : preset;
    const src = applyDispFilter(byDisp2w, f);
    const allMonths = sortedMonths(src.length ? src : byDisp2w);
    const series = main.map((b, i) => ({
      name: b, type: 'line', smooth: true,
      data: allMonths.map(ym => {
        const [y, m] = ym.split('-').map(Number);
        const r = src.find(k => k.year === y && k.month === m && k.category === b);
        return r ? r.value : null;
      }),
      itemStyle: { color: dispColor(b) },
    }));
    charts.chartDispLines.setOption({
      tooltip: { trigger: 'axis', valueFormatter: fmt },
      legend: { top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: allMonths, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });
  }

  // ---- Chart: Vehicle Type Pie (latest year) ----
  function renderVtypePie(filtered) {
    const latest = META.years[META.years.length - 1];
    const types = META.vehicle_types;
    const data = types.map(t => {
      const sum = filtered.filter(r => r.scope === '二轮' && r.category === t)
        .reduce((a, r) => a + r.value, 0);
      return { name: t, value: Math.round(sum) };
    });
    charts.chartVtypePie.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmt(p.value)}<br/>${p.percent.toFixed(1)}%` },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: true,
        label: { formatter: '{b}\n{d}%' },
        data: data,
      }],
    });
  }

  // ---- Chart: Vehicle Type Stacked ----
  function renderVtypeStacked(filtered) {
    const years = sortedYears(filtered);
    const types = META.vehicle_types;
    const series = types.map((t, i) => ({
      name: t, type: 'bar', stack: 'total',
      data: years.map(y => {
        const sum = filtered.filter(r => r.scope === '二轮' && r.category === t && r.year === y)
          .reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: DISP_COLORS[i % DISP_COLORS.length] },
    }));
    charts.chartVtypeStacked.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      legend: { top: 0 },
      grid: { left: 70, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
    });
  }

  // ---- Chart: 3W Vehicle Types ----
  function renderVtype3w(filtered) {
    const years = sortedYears(filtered);
    const types = META.three_wheeler_types;
    const series = types.map((t, i) => ({
      name: t, type: 'bar', stack: 'total',
      data: years.map(y => {
        const sum = filtered.filter(r => r.scope === '三轮' && r.category === t && r.year === y)
          .reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: DISP_COLORS[i * 4 % DISP_COLORS.length] },
    }));
    charts.chartVtype3w.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      legend: { top: 0 },
      grid: { left: 70, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
    });
  }

  // ---- Chart: Manufacturer Ranking ----
  function renderMfgRank(filtered) {
    // Aggregate by manufacturer in filtered data
    const map = new Map();
    filtered.forEach(r => {
      if (!r.manufacturer) return;
      const k = `${r.manufacturer}|${r.indicator}`;
      map.set(k, (map.get(k) || 0) + r.value);
    });
    const merged = new Map();
    map.forEach((v, k) => {
      const [name, ind] = k.split('|');
      const cur = merged.get(name) || { 生产: 0, 销售: 0 };
      cur[ind] += v;
      merged.set(name, cur);
    });
    const arr = [...merged.entries()]
      .map(([name, v]) => ({ name, value: v.生产 + v.销售 }))
      .sort((a, b) => b.value - a.value).slice(0, 20);

    charts.chartMfgRank.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      grid: { left: 180, right: 50, top: 10, bottom: 30 },
      xAxis: { type: 'value', axisLabel: { formatter: fmt } },
      yAxis: { type: 'category', data: arr.map(a => a.name).reverse(), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: arr.map(a => a.value).reverse(),
        itemStyle: {
          color: (params) => {
            const colors = DISP_COLORS;
            return colors[params.dataIndex % colors.length];
          },
        },
        label: { show: true, position: 'right', formatter: p => fmt(p.value), fontSize: 10 },
      }],
    });
  }

  // ---- Chart: Mfg Pie (latest year) ----
  function renderMfgPie(filtered) {
    const f = getFilters();
    const latest = META.years[META.years.length - 1];
    const map = new Map();
    filtered.filter(r => r.year === latest && r.indicator === '生产')
      .forEach(r => map.set(r.manufacturer, (map.get(r.manufacturer) || 0) + r.value));
    const arr = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
    const others = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(10);
    const otherSum = others.reduce((a, [, v]) => a + v, 0);
    if (otherSum > 0) arr.push(['其他', otherSum]);

    charts.chartMfgPie.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmt(p.value)}<br/>${p.percent.toFixed(1)}%` },
      legend: { type: 'scroll', orient: 'vertical', left: 0, top: 'middle' },
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['65%', '50%'],
        avoidLabelOverlap: true, label: { formatter: '{b}\n{d}%' },
        data: arr.map(([name, value]) => ({ name, value: Math.round(value) })),
      }],
    });
  }

  // ---- Chart: Mfg Trend Comparison ----
  function renderMfgTrend(filtered) {
    const f = getFilters();
    const topMfgs = [...new Set(filtered.filter(r => r.manufacturer).map(r => r.manufacturer))];
    const selectedMfgs = f.mfgs.length > 0 ? f.mfgs : topMfgs.slice(0, 5);
    const months = sortedMonths(filtered);
    // 指标：both 时画生产+销售两条，否则只画所选指标
    const indicators = f.indicator === 'both' ? ['生产', '销售'] : [f.indicator];
    const series = [];
    selectedMfgs.slice(0, 8).forEach((m, i) => {
      indicators.forEach((ind, j) => {
        series.push({
          name: `${m}·${ind}`, type: 'line', smooth: true,
          data: months.map(ym => {
            const [y, mo] = ym.split('-').map(Number);
            const r = filtered.find(k => k.year === y && k.month === mo &&
                                         k.manufacturer === m && k.indicator === ind);
            return r ? r.value : null;
          }),
          itemStyle: { color: DISP_COLORS[i % DISP_COLORS.length] },
          lineStyle: { type: j === 0 ? 'solid' : 'dashed' },
        });
      });
    });
    charts.chartMfgTrend.setOption({
      tooltip: { trigger: 'axis', valueFormatter: fmt },
      legend: { type: 'scroll', top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: series,
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });
  }

  // ---- Chart: Mfg Compare (销量对比专区) ----
  function renderMfgCompare(filtered) {
    const f = getFilters();
    const topMfgs = [...new Set(filtered.filter(r => r.manufacturer).map(r => r.manufacturer))];
    const selectedMfgs = f.mfgs.length > 0 ? f.mfgs : topMfgs.slice(0, 8);
    const months = sortedMonths(filtered);

    // 指标：默认按「销售」，用户切「仅生产」时用生产，both 时销售优先展示
    const compareInd = f.indicator === '生产' ? '生产' : '销售';

    // 1) 累计对比（横条）
    const barData = selectedMfgs.map(m => ({
      name: m,
      value: Math.round(filtered.filter(r => r.manufacturer === m && r.indicator === compareInd)
        .reduce((a, r) => a + r.value, 0)),
    })).sort((a, b) => a.value - b.value);

    charts.chartMfgCompareBar.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      grid: { left: 180, right: 60, top: 10, bottom: 30 },
      xAxis: { type: 'value', axisLabel: { formatter: fmt } },
      yAxis: { type: 'category', data: barData.map(d => d.name), axisLabel: { fontSize: 11 } },
      series: [{
        name: `${compareInd}累计`, type: 'bar',
        data: barData.map(d => d.value),
        itemStyle: { color: compareInd === '销售' ? PALETTE.sales : PALETTE.prod },
        label: { show: true, position: 'right', formatter: p => fmt(p.value), fontSize: 10 },
      }],
    });

    // 2) 月度趋势对比
    const trendSeries = selectedMfgs.slice(0, 8).map((m, i) => ({
      name: m, type: 'line', smooth: true,
      data: months.map(ym => {
        const [y, mo] = ym.split('-').map(Number);
        const r = filtered.find(k => k.year === y && k.month === mo &&
                                     k.manufacturer === m && k.indicator === compareInd);
        return r ? r.value : null;
      }),
      itemStyle: { color: DISP_COLORS[i % DISP_COLORS.length] },
    }));
    charts.chartMfgCompareTrend.setOption({
      tooltip: { trigger: 'axis', valueFormatter: fmt },
      legend: { type: 'scroll', top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: trendSeries,
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });
  }

  // ---- Chart: Mfg Rank Change (Top 10 rank over years) ----
  function renderMfgRankChange(filtered) {
    const years = sortedYears(filtered);
    // For each year, rank top 10 by production
    const yearRanks = {};
    years.forEach(y => {
      const map = new Map();
      filtered.filter(r => r.year === y && r.indicator === '生产')
        .forEach(r => map.set(r.manufacturer, (map.get(r.manufacturer) || 0) + r.value));
      const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
      yearRanks[y] = sorted.map(([name], idx) => ({ name, rank: idx + 1 }));
    });

    // Build dataset: rows = manufacturers, cols = years, cell = rank (or null if not in top 10)
    const allNames = new Set();
    years.forEach(y => yearRanks[y].forEach(r => allNames.add(r.name)));
    const namesArr = [...allNames];
    const data = [];
    namesArr.forEach((name, ni) => {
      years.forEach((y, yi) => {
        const rankInfo = yearRanks[y].find(r => r.name === name);
        data.push([yi, ni, rankInfo ? rankInfo.rank : 0]);
      });
    });

    charts.chartMfgRankChange.setOption({
      tooltip: { formatter: p => `${namesArr[p.value[1]]}<br/>${years[p.value[0]]} 年<br/>第 ${p.value[2] || '>10'} 名` },
      grid: { left: 130, right: 30, top: 10, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'category', data: namesArr, axisLabel: { fontSize: 10 } },
      visualMap: { min: 0, max: 10, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
        inRange: { color: ['#fee2e2', '#fff', '#1e40af'] }, text: ['10名外', '前 1'], textStyle: { fontSize: 10 } },
      series: [{ type: 'heatmap', data: data, label: { show: true, formatter: p => p.value[2] || '' } }],
    });
  }

  // ---- Chart: Large Displacement Mfg Rank ----
  // 基于「厂家×排量」明细（仅 2023.9+），筛 >250ml 段，按厂家聚合产量
  function renderMfgLargeDisp() {
    const f = getFilters();
    const rows = mfgDisp.filter(r =>
      f.years.includes(r.year) && f.months.includes(r.month) &&
      LARGE_DISP.includes(r.category) &&
      (f.indicator === 'both' || r.indicator === f.indicator)
    );
    const map = new Map();
    rows.forEach(r => map.set(r.manufacturer, (map.get(r.manufacturer) || 0) + r.value));
    const arr = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15);
    charts.chartMfgLargeDisp.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      grid: { left: 180, right: 60, top: 10, bottom: 30 },
      xAxis: { type: 'value', axisLabel: { formatter: fmt } },
      yAxis: { type: 'category', data: arr.map(a => a[0]).reverse(), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: arr.map(a => Math.round(a[1])).reverse(),
        itemStyle: { color: PALETTE.purple },
        label: { show: true, position: 'right', formatter: p => fmt(p.value), fontSize: 10 },
      }],
    });

    // 大排量市场份额饼图
    const pieData = arr.slice(0, 10).map(([name, v]) => ({ name, value: Math.round(v) }));
    charts.chartMfgLargePie.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmt(p.value)}<br/>${p.percent.toFixed(1)}%` },
      legend: { type: 'scroll', orient: 'vertical', left: 0, top: 'middle' },
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['65%', '50%'],
        avoidLabelOverlap: true, label: { formatter: '{b}\n{d}%' },
        data: pieData,
      }],
    });
  }

  // ---- Chart: Annual Total ----
  function renderAnnualTotal(filtered) {
    const years = sortedYears(filtered);
    const f = getFilters();
    const indicators = f.indicator === 'both' ? ['生产', '销售'] : [f.indicator];
    const series = indicators.map((ind, i) => ({
      name: L[ind], type: 'bar',
      data: years.map(y => {
        const sum = filtered.filter(r => r.year === y && r.indicator === ind).reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: ind === '生产' ? PALETTE.prod : PALETTE.sales },
      label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 11 },
    }));
    charts.chartAnnualTotal.setOption({
      tooltip: { trigger: 'axis', valueFormatter: fmt },
      legend: { data: indicators.map(i => L[i]), top: 0 },
      grid: { left: 70, right: 30, top: 50, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', name: '辆/年 Units/Year', axisLabel: { formatter: fmt } },
      series: series,
    });
  }

  // ---- Chart: Annual YoY ----
  // base: 同时含上一年同期月份、相同排量/厂家口径的数据集
  function renderAnnualYoy(filtered, base) {
    base = base || (() => {
      // 回退：若未传 base，从总数据构造（永远保证有序）
      const all = monthlyTotal;
      return filtered.map(() => null) && all;
    })();
    const years = sortedYears(filtered);
    const f = getFilters();
    const indicators = f.indicator === 'both' ? ['生产', '销售'] : [f.indicator];
    const series = indicators.map(ind => ({
      name: ind, type: 'bar',
      data: years.map((y, i) => {
        if (i === 0) return null;
        const cur = filtered.filter(r => r.year === y && r.indicator === ind).reduce((a, r) => a + r.value, 0);
        const sameMonths = new Set(filtered.filter(r => r.year === y).map(r => r.month));
        // 同比基准：上一层（同期 + 上一年的月份）— base 已经按 f.displacements/f.mfgs 过滤
        const prevSum = base.filter(r => r.year === years[i-1] && sameMonths.has(r.month) && r.indicator === ind)
          .reduce((a, r) => a + r.value, 0);
        if (!prevSum) return null;
        return +(((cur - prevSum) / prevSum) * 100).toFixed(1);
      }),
      itemStyle: { color: ind === '生产' ? PALETTE.prod : PALETTE.sales },
    }));
    charts.chartAnnualYoy.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => v === null ? '—' : v + '%' },
      legend: { top: 0 },
      grid: { left: 60, right: 30, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: series,
    });
  }

  // ---- Chart: EV Share ----
  function renderEvShare(filtered) {
    const years = sortedYears(filtered);
    const data = years.map(y => {
      const total = filtered.filter(r => r.year === y && r.indicator === '生产').reduce((a, r) => a + r.value, 0);
      const ev2w = filtered.filter(r => r.year === y && r.indicator === '生产' && r.scope === '二轮' && r.category === '电动摩托车')
        .reduce((a, r) => a + r.value, 0);
      const ev3w = filtered.filter(r => r.year === y && r.indicator === '生产' && r.scope === '三轮' && r.category === '电动摩托车')
        .reduce((a, r) => a + r.value, 0);
      const evTotal = ev2w + ev3w;
      return {
        year: y,
        total: Math.round(total),
        ev: Math.round(evTotal),
        evPct: total > 0 ? +((evTotal / total) * 100).toFixed(2) : 0,
      };
    });
    charts.chartEvShare.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: [L.总产量, L.电动产量, L.电动占比], top: 0 },
      grid: { left: 70, right: 70, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: [
        { type: 'value', name: '辆 Units', axisLabel: { formatter: fmt } },
        { type: 'value', name: '占比 Share %', position: 'right', axisLabel: { formatter: '{value}%' }, max: 100 },
      ],
      series: [
        { name: L.总产量, type: 'bar', stack: 'v', data: data.map(d => d.total - d.ev), itemStyle: { color: PALETTE.gray } },
        { name: L.电动产量, type: 'bar', stack: 'v', data: data.map(d => d.ev), itemStyle: { color: PALETTE.accent } },
        { name: L.电动占比, type: 'line', yAxisIndex: 1, data: data.map(d => d.evPct),
          itemStyle: { color: PALETTE.purple }, smooth: true, symbolSize: 8,
          label: { show: true, formatter: p => p.value + '%', position: 'top', fontSize: 10 } },
      ],
    });
  }

  // ---- Chart: Large Displacement (>250ml) Growth ----
  function renderLargeDisp(filtered) {
    const years = sortedYears(filtered);
    // 各段堆叠柱状 + 总量数值标签
    const series = LARGE_DISP.map((b, i) => ({
      name: b, type: 'bar', stack: 'large',
      data: years.map(y => {
        const sum = filtered.filter(r => r.year === y && r.category === b).reduce((a, r) => a + r.value, 0);
        return Math.round(sum);
      }),
      itemStyle: { color: dispColor(b) },
    }));
    // 每年 >250ml 总量（用于数值标签和增长率）
    const totals = years.map(y =>
      filtered.filter(r => r.year === y && LARGE_DISP.includes(r.category))
        .reduce((a, r) => a + r.value, 0)
    );
    // 线状增长率（同比）
    const growth = years.map((y, i) => {
      if (i === 0 || totals[i - 1] === 0) return null;
      return +(((totals[i] - totals[i - 1]) / totals[i - 1]) * 100).toFixed(1);
    });
    series.push({
      name: '总量 Total', type: 'bar', stack: 'large',
      data: totals.map(Math.round),
      itemStyle: { color: 'transparent' },
      tooltip: { show: false },
      label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 11, fontWeight: 'bold', color: '#1f2937' },
    });
    series.push({
      name: '同比增速 YoY %', type: 'line', yAxisIndex: 1,
      data: growth,
      itemStyle: { color: PALETTE.purple }, smooth: true, symbolSize: 7,
      lineStyle: { width: 2 },
      label: { show: true, formatter: p => (p.value === null ? '' : p.value + '%'), position: 'top', fontSize: 10, color: PALETTE.purple },
    });
    charts.chartLargeDisp.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => (typeof v === 'number' ? fmt(v) : v) },
      legend: { type: 'scroll', top: 0 },
      grid: { left: 70, right: 70, top: 60, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: [
        { type: 'value', axisLabel: { formatter: fmt } },
        { type: 'value', name: '增速 YoY %', axisLabel: { formatter: '{value}%' } },
      ],
      series: series,
    });
  }

  // ---- Render Mfg Detail Table ----
  function renderMfgTable(filteredMfg) {
    const f = getFilters();
    const tbody = document.querySelector('#mfgTable tbody');
    tbody.innerHTML = '';
    const src = filteredMfg || applyFilters(byMfg, f);

    // 按厂家聚合（生产+销售）
    const merged = new Map();
    src.forEach(r => {
      const cur = merged.get(r.manufacturer) || { 生产: 0, 销售: 0 };
      cur[r.indicator] = (cur[r.indicator] || 0) + r.value;
      merged.set(r.manufacturer, cur);
    });
    const sorted = [...merged.entries()]
      .map(([name, v]) => ({ name, total: (v.生产 || 0) + (v.销售 || 0) }))
      .sort((a, b) => b.total - a.total).slice(0, 30);

    if (!sorted.length) {
      tbody.innerHTML = '<tr><td colspan="16" style="text-align:center;color:#9ca3af;">当前筛选条件下无数据</td></tr>';
      return;
    }

    const yearsLabel = f.years.join(',');
    sorted.forEach(m => {
      const indicators = f.indicator === 'both' ? ['生产', '销售'] : [f.indicator];
      indicators.forEach(ind => {
        const tr = document.createElement('tr');
        const monthly = META.months.map(mo => {
          let total = 0;
          f.years.forEach(y => {
            total += src.filter(r => r.manufacturer === m.name && r.year === y &&
                                   r.month === mo && r.indicator === ind)
                        .reduce((a, r) => a + r.value, 0);
          });
          return Math.round(total);
        });
        const yrTotal = monthly.reduce((a, v) => a + v, 0);
        tr.innerHTML = `
          <td>${m.name}</td>
          <td>${ind}</td>
          <td>${yearsLabel}</td>
          ${monthly.map(v => `<td>${v ? fmt(v) : '—'}</td>`).join('')}
          <td><strong>${fmt(yrTotal)}</strong></td>
        `;
        tbody.appendChild(tr);
      });
    });
  }

  // ---- Export / 内销外销 rendering ----
  function renderExport() {
    const f = getFilters();

    // 出口总量按筛选（年月 + 厂家，排量筛选不影响出口总量口径，但可影响二轮排量结构）
    let exportTotalFiltered = exportTotal.filter(r =>
      f.years.includes(r.year) && f.months.includes(r.month)
    );
    const exportAmtFiltered = exportAmount.filter(r =>
      f.years.includes(r.year) && f.months.includes(r.month)
    );

    // 销量总量（用于算内销、外销率）
    let salesFiltered = applyFilters(monthlyTotal, f).filter(r => r.indicator === '销售');

    // ---- 排量感知：选了排量段后，改用「分排量出口 + 分排量产量」口径 ----
    if (f.displacements.length) {
      // 1) 分排量出口（exportMonthly 中 type='排量'，宽松匹配所选段）
      const expByDisp = exportMonthly.filter(r =>
        r.type === '排量' &&
        dispMatchLoose(r.category, f.displacements) &&
        f.years.includes(r.year) && f.months.includes(r.month)
      );
      // 2) 分排量产量（byDisp2w 中该排量段的生产，宽松匹配）
      const prodByDisp = byDisp2w.filter(r =>
        r.indicator === '生产' &&
        dispMatchLoose(r.category, f.displacements) &&
        f.years.includes(r.year) && f.months.includes(r.month)
      );

      // 出口量：按年月聚合
      const expMap = new Map();
      expByDisp.forEach(r => {
        const k = `${r.year}-${r.month}`;
        expMap.set(k, (expMap.get(k) || 0) + r.value);
      });
      exportTotalFiltered = [...expMap.entries()].map(([k, v]) => {
        const [y, m] = k.split('-').map(Number);
        return { year: y, month: m, value: v };
      });

      // 产量（替代销量）：按年月聚合
      const prodMap = new Map();
      prodByDisp.forEach(r => {
        const k = `${r.year}-${r.month}`;
        prodMap.set(k, (prodMap.get(k) || 0) + r.value);
      });
      salesFiltered = [...prodMap.entries()].map(([k, v]) => {
        const [y, m] = k.split('-').map(Number);
        return { year: y, month: m, indicator: '生产', value: v };
      });
    }

    // 销量/产量总量（用于算内销、外销率）— 限定在有出口数据的月份，保证口径一致
    const exportMonthsSet = new Set(exportTotalFiltered.map(r => `${r.year}-${r.month}`));
    salesFiltered = salesFiltered.filter(r => exportMonthsSet.has(`${r.year}-${r.month}`));

    // KPI
    const totExport = exportTotalFiltered.reduce((a, r) => a + r.value, 0);
    const totAmt = exportAmtFiltered.reduce((a, r) => a + r.amount, 0);
    const totSales = salesFiltered.reduce((a, r) => a + r.value, 0);
    const totDomestic = totSales - totExport;

    document.getElementById('kpiExport').textContent = fmt(totExport);
    document.getElementById('kpiExportAmt').textContent = totAmt ? fmtAmt(totAmt) : '—';
    document.getElementById('kpiExportRatio').textContent = totSales ? ((totExport / totSales) * 100).toFixed(1) + '%' : '—';
    document.getElementById('kpiDomestic').textContent = fmt(totDomestic);

    document.getElementById('kpiExportRatioHint').innerHTML =
      `<span class="up">外销率 = 出口 / 销量</span>`;
    document.getElementById('kpiDomesticHint').innerHTML =
      `<span>内销 = 销量 − 出口</span>`;

    // 1) 内销 vs 出口 分组并列柱状
    const months = sortedMonths(exportTotalFiltered);
    const domData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const exp = exportTotalFiltered.find(r => r.year === y && r.month === m);
      const sal = salesFiltered.find(r => r.year === y && r.month === m);
      const ex = exp ? exp.value : 0;
      const sl = sal ? sal.value : 0;
      return Math.round(Math.max(0, sl - ex));
    });
    const expData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const exp = exportTotalFiltered.find(r => r.year === y && r.month === m);
      return exp ? Math.round(exp.value) : 0;
    });
    charts.chartExportStack.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      legend: { data: [L.内销, L.出口], top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: [
        { name: L.内销, type: 'bar', data: domData, itemStyle: { color: PALETTE.prod } },
        { name: L.出口, type: 'bar', data: expData, itemStyle: { color: PALETTE.accent } },
      ],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });

    // 1b) 内销 vs 出口 月度折线对比
    charts.chartExportCompare.setOption({
      tooltip: { trigger: 'axis', valueFormatter: fmt },
      legend: { data: [L.内销, L.出口], top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: [
        { name: L.内销, type: 'line', smooth: true, data: domData,
          itemStyle: { color: PALETTE.prod }, areaStyle: { opacity: 0.12, color: PALETTE.prod } },
        { name: L.出口, type: 'line', smooth: true, data: expData,
          itemStyle: { color: PALETTE.accent }, areaStyle: { opacity: 0.12, color: PALETTE.accent } },
      ],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });

    // 2) 出口占销量比
    const ratioData = months.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const exp = exportTotalFiltered.find(r => r.year === y && r.month === m);
      const sal = salesFiltered.find(r => r.year === y && r.month === m);
      if (!exp || !sal || !sal.value) return null;
      return +((exp.value / sal.value) * 100).toFixed(2);
    });
    charts.chartExportRatio.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => v === null ? '—' : v + '%' },
      grid: { left: 60, right: 30, top: 20, bottom: 50 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
      series: [{
        type: 'line', smooth: true, data: ratioData,
        itemStyle: { color: PALETTE.accent }, areaStyle: { opacity: 0.15, color: PALETTE.accent },
      }],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });

    // 3) 出口金额
    const amtMonths = sortedMonths(exportAmtFiltered);
    const amtData = amtMonths.map(ym => {
      const [y, m] = ym.split('-').map(Number);
      const r = exportAmtFiltered.find(k => k.year === y && k.month === m);
      return r ? Math.round(r.amount) : null;
    });
    charts.chartExportAmt.setOption({
      tooltip: { trigger: 'axis', valueFormatter: v => v === null ? '—' : fmtAmt(v) },
      grid: { left: 70, right: 30, top: 20, bottom: 50 },
      xAxis: { type: 'category', data: amtMonths, axisLabel: { rotate: 30 } },
      yAxis: { type: 'value', axisLabel: { formatter: fmtAmt } },
      series: [{
        type: 'bar', data: amtData,
        itemStyle: { color: PALETTE.amber },
      }],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
    });

    // 4) 厂家出口排名
    const mfgMap = new Map();
    exportMfg.filter(r => f.years.includes(r.year) && f.months.includes(r.month))
      .forEach(r => mfgMap.set(r.manufacturer, (mfgMap.get(r.manufacturer) || 0) + r.value));
    const mfgArr = [...mfgMap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15);
    charts.chartExportMfg.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      grid: { left: 180, right: 50, top: 10, bottom: 30 },
      xAxis: { type: 'value', axisLabel: { formatter: fmt } },
      yAxis: { type: 'category', data: mfgArr.map(a => a[0]).reverse(), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: mfgArr.map(a => Math.round(a[1])).reverse(),
        itemStyle: { color: PALETTE.accent },
        label: { show: true, position: 'right', formatter: p => fmt(p.value), fontSize: 10 },
      }],
    });

    // 5) 二轮出口结构（按排量段）
    const dispRows = exportMonthly.filter(r =>
      r.scope === '二轮' && r.type === '排量' &&
      f.years.includes(r.year) && f.months.includes(r.month)
    );
    const dispMap = new Map();
    dispRows.forEach(r => dispMap.set(r.category, (dispMap.get(r.category) || 0) + r.value));
    const dispArr = [...dispMap.entries()].sort((a, b) => b[1] - a[1]);
    charts.chartExportDisp.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmt(p.value)}<br/>${p.percent.toFixed(1)}%` },
      legend: { type: 'scroll', orient: 'vertical', right: 0, top: 'middle' },
      series: [{
        type: 'pie', radius: ['35%', '65%'], center: ['40%', '50%'],
        data: dispArr.map(([name, v]) => ({ name, value: Math.round(v), itemStyle: { color: dispColor(name) } })),
        label: { formatter: '{b}\n{d}%', fontSize: 10 },
      }],
    });

    // 6) 内销 vs 出口 年度分组对比
    const years = sortedYears(exportTotalFiltered);
    const yearDom = years.map(y => {
      const exp = exportTotalFiltered.filter(r => r.year === y).reduce((a, r) => a + r.value, 0);
      const sal = salesFiltered.filter(r => r.year === y).reduce((a, r) => a + r.value, 0);
      return Math.round(Math.max(0, sal - exp));
    });
    const yearExp = years.map(y => {
      return Math.round(exportTotalFiltered.filter(r => r.year === y).reduce((a, r) => a + r.value, 0));
    });
    charts.chartExportYear.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      legend: { data: [L.内销, L.出口], top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: [
        { name: L.内销, type: 'bar', data: yearDom, itemStyle: { color: PALETTE.prod },
          label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 10 } },
        { name: L.出口, type: 'bar', data: yearExp, itemStyle: { color: PALETTE.accent },
          label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 10 } },
      ],
    });

    // 7) 内销 vs 出口 占比演变（百分比堆叠）
    const shareDom = years.map((y, i) => {
      const total = yearDom[i] + yearExp[i];
      return total > 0 ? +((yearDom[i] / total) * 100).toFixed(1) : 0;
    });
    const shareExp = years.map((y, i) => {
      const total = yearDom[i] + yearExp[i];
      return total > 0 ? +((yearExp[i] / total) * 100).toFixed(1) : 0;
    });
    charts.chartExportShare.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: v => v + '%' },
      legend: { data: [L.内销占比, L.出口占比], top: 0 },
      grid: { left: 60, right: 30, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: years.map(String) },
      yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      series: [
        { name: L.内销占比, type: 'bar', stack: 'p', data: shareDom, itemStyle: { color: PALETTE.prod },
          label: { show: true, formatter: p => p.value + '%', fontSize: 10 } },
        { name: L.出口占比, type: 'bar', stack: 'p', data: shareExp, itemStyle: { color: PALETTE.accent },
          label: { show: true, formatter: p => p.value + '%', fontSize: 10 } },
      ],
    });

    // 8) 内销 / 出口 按车型分布
    const types = ['骑式', '弯梁式', '踏板式'];
    const exportByType = types.map(t => {
      const exp = exportMonthly.filter(r => r.scope === '二轮' && r.category === t && r.type === '车型' &&
        f.years.includes(r.year) && f.months.includes(r.month))
        .reduce((a, r) => a + r.value, 0);
      return Math.round(exp);
    });
    // 内销按车型 = 车型总产量 - 车型出口量（车型总产量来自 byVtype）
    const domesticByType = types.map(t => {
      const prod = byVtype.filter(r => r.scope === '二轮' && r.category === t && r.indicator === '生产' &&
        f.years.includes(r.year) && f.months.includes(r.month))
        .reduce((a, r) => a + r.value, 0);
      const exp = exportMonthly.filter(r => r.scope === '二轮' && r.category === t && r.type === '车型' &&
        f.years.includes(r.year) && f.months.includes(r.month))
        .reduce((a, r) => a + r.value, 0);
      return Math.round(Math.max(0, prod - exp));
    });
    charts.chartExportType.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: fmt },
      legend: { data: [L.内销, L.出口], top: 0 },
      grid: { left: 70, right: 30, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: types },
      yAxis: { type: 'value', axisLabel: { formatter: fmt } },
      series: [
        { name: L.内销, type: 'bar', data: domesticByType, itemStyle: { color: PALETTE.prod },
          label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 10 } },
        { name: L.出口, type: 'bar', data: exportByType, itemStyle: { color: PALETTE.accent },
          label: { show: true, position: 'top', formatter: p => fmt(p.value), fontSize: 10 } },
      ],
    });

    // 9) 大排量（>250ml）出口与内销
    const largeExp = exportMonthly.filter(r => r.scope === '二轮' && r.type === '排量' && LARGE_DISP.includes(r.category) &&
      f.years.includes(r.year) && f.months.includes(r.month))
      .reduce((a, r) => a + r.value, 0);
    const largeProd = byDisp2w.filter(r => r.scope === '二轮' && r.indicator === '生产' && LARGE_DISP.includes(r.category) &&
      f.years.includes(r.year) && f.months.includes(r.month))
      .reduce((a, r) => a + r.value, 0);
    const largeDom = Math.max(0, largeProd - largeExp);
    charts.chartExportLarge.setOption({
      tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmt(p.value)}<br/>${p.percent.toFixed(1)}%` },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        data: [
          { name: L.内销, value: Math.round(largeDom) },
          { name: L.出口, value: Math.round(largeExp) },
        ],
        itemStyle: {
          color: (p) => p.name === L.内销 ? PALETTE.prod : PALETTE.accent,
        },
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
      }],
    });
  }

  // ---- Render Annual Detail Table ----
  function renderAnnualTable() {
    const tbody = document.querySelector('#annualTable tbody');
    const thead = document.querySelector('#annualTableHead');
    tbody.innerHTML = '';
    const years = sortedYears(monthlyTotal);

    // 动态生成表头（2016-2026）
    thead.innerHTML = '<tr><th>指标 / 维度</th>' + years.map(y => {
      const first = monthlyTotal.filter(r => r.year === y).length ? '' : '*';
      return `<th>${y}${first}</th>`;
    }).join('') + '</tr>';

    const rows = [
      { label: '总产量 Total Production', data: monthlyTotal.filter(r => r.indicator === '生产') },
      { label: '总销量 Total Sales', data: monthlyTotal.filter(r => r.indicator === '销售') },
      { label: '二轮总产量 2W Production', data: byDisp2w.filter(r => r.indicator === '生产') },
      { label: '二轮总销量 2W Sales', data: byDisp2w.filter(r => r.indicator === '销售') },
      { label: '三轮总产量 3W Production', data: byDisp3w.filter(r => r.indicator === '生产') },
      { label: '三轮总销量 3W Sales', data: byDisp3w.filter(r => r.indicator === '销售') },
      { label: '110-125ml 生产 Production', data: byDisp2w.filter(r => r.indicator === '生产' && r.category === '110ml<排量≤125ml') },
      { label: '125-150ml 生产 Production', data: byDisp2w.filter(r => r.indicator === '生产' && r.category === '125ml<排量≤150ml') },
      { label: '电动二轮生产 2W EV Production', data: byDisp2w.filter(r => r.indicator === '生产' && r.category === '电动摩托车') },
      { label: '>250ml 大排量生产 >250ml Production', data: byDisp2w.filter(r => r.indicator === '生产' && LARGE_DISP.includes(r.category)) },
      { label: '>250ml 大排量销售 >250ml Sales', data: byDisp2w.filter(r => r.indicator === '销售' && LARGE_DISP.includes(r.category)) },
      { label: '>250ml 占比 Share(%)', data: null, isPct: true,
        calc: y => {
          const total = monthlyTotal.filter(r => r.year === y && r.indicator === '生产').reduce((a, r) => a + r.value, 0);
          const big = byDisp2w.filter(r => r.year === y && r.indicator === '生产' && LARGE_DISP.includes(r.category)).reduce((a, r) => a + r.value, 0);
          return total > 0 ? (big / total * 100) : 0;
        } },
    ];
    rows.forEach(row => {
      const tr = document.createElement('tr');
      if (row.isPct) {
        tr.innerHTML = `<td>${row.label}</td>` + years.map(y => {
          const v = row.calc(y);
          return `<td>${v ? v.toFixed(1) + '%' : '—'}</td>`;
        }).join('');
      } else {
        tr.innerHTML = `<td>${row.label}</td>` + years.map(y => {
          const sum = row.data.filter(r => r.year === y).reduce((a, r) => a + r.value, 0);
          return `<td>${sum ? fmt(sum) : '—'}</td>`;
        }).join('');
      }
      tbody.appendChild(tr);
    });
  }

  // ---- 业务洞察 Insights ----
  // 基于全量数据自动计算关键业务发现与决策建议
  function renderInsights() {
    const root = document.getElementById('insightsRoot');
    if (!root) return;

    // 年度总量（生产，全时段）
    const yearlyProd = {};
    const yearlySales = {};
    const yearMonthCount = {};
    monthlyTotal.forEach(r => {
      if (r.indicator === '生产') yearlyProd[r.year] = (yearlyProd[r.year] || 0) + r.value;
      if (r.indicator === '销售') yearlySales[r.year] = (yearlySales[r.year] || 0) + r.value;
      if (r.indicator === '生产') yearMonthCount[r.year] = (yearMonthCount[r.year] || 0) + 1;
    });
    const years = Object.keys(yearlyProd).map(Number).sort((a, b) => a - b);
    // 最后一个「完整年」（≥11 个月），避免用 2026 上半年失真
    const fullYears = years.filter(y => yearMonthCount[y] >= 11);
    const lastYear = fullYears[fullYears.length - 1];   // 最后一个完整年
    const prevYear = fullYears[fullYears.length - 2];   // 上一个完整年
    const latestYear = years[years.length - 1];          // 数据最新年（可能是当年至今）
    const firstYear = years[0];

    // 1) 行业增长：近三年 CAGR 与最新 YoY
    const pLast = yearlyProd[lastYear] || 0;
    const pPrev = yearlyProd[prevYear] || 0;
    const yoyLatest = pPrev ? ((pLast - pPrev) / pPrev * 100) : 0;
    const p3ago = yearlyProd[lastYear - 3] || yearlyProd[years[0]] || 0;
    const cagr3 = p3ago ? ((Math.pow(pLast / p3ago, 1 / 3) - 1) * 100) : 0;

    // 2) 电动化趋势
    const evTotal = byDisp2w.filter(r => r.indicator === '生产' && r.category === '电动摩托车').reduce((a, r) => a + r.value, 0);
    const evLast = byDisp2w.filter(r => r.year === lastYear && r.indicator === '生产' && r.category === '电动摩托车').reduce((a, r) => a + r.value, 0);
    const totalLast = yearlyProd[lastYear] || 1;
    const evShare = evLast / totalLast * 100;

    // 3) 大排量趋势
    const largeLast = byDisp2w.filter(r => r.year === lastYear && r.indicator === '生产' && LARGE_DISP.includes(r.category)).reduce((a, r) => a + r.value, 0);
    const largeShare = largeLast / totalLast * 100;
    const largePrev = byDisp2w.filter(r => r.year === prevYear && r.indicator === '生产' && LARGE_DISP.includes(r.category)).reduce((a, r) => a + r.value, 0);
    const largeGrowth = largePrev ? ((largeLast - largePrev) / largePrev * 100) : 0;

    // 4) 出口依赖度
    const exportTotalAll = exportTotal.reduce((a, r) => a + r.value, 0);
    const salesTotalAll = monthlyTotal.filter(r => r.indicator === '销售').reduce((a, r) => a + r.value, 0);
    const exportRatio = salesTotalAll ? exportTotalAll / salesTotalAll * 100 : 0;

    // 5) 品牌集中度 CR5 / CR10
    const mfgProd = {};
    byMfg.filter(r => r.indicator === '生产').forEach(r => mfgProd[r.manufacturer] = (mfgProd[r.manufacturer] || 0) + r.value);
    const mfgSorted = Object.entries(mfgProd).sort((a, b) => b[1] - a[1]);
    const mfgTotalProd = mfgSorted.reduce((a, x) => a + x[1], 0);
    const cr5 = mfgSorted.slice(0, 5).reduce((a, x) => a + x[1], 0) / mfgTotalProd * 100;
    const cr10 = mfgSorted.slice(0, 10).reduce((a, x) => a + x[1], 0) / mfgTotalProd * 100;
    const topBrand = mfgSorted[0] ? mfgSorted[0][0] : '—';

    // 6) 季节性规律：各月平均占比（找峰值月）
    const monthAvg = {};
    const monthCount = {};
    monthlyTotal.filter(r => r.indicator === '生产').forEach(r => {
      monthAvg[r.month] = (monthAvg[r.month] || 0) + r.value;
      monthCount[r.month] = (monthCount[r.month] || 0) + 1;
    });
    Object.keys(monthAvg).forEach(m => monthAvg[m] = monthAvg[m] / monthCount[m]);
    const peakMonth = Object.entries(monthAvg).sort((a, b) => b[1] - a[1])[0];
    const troughMonth = Object.entries(monthAvg).sort((a, b) => a[1] - b[1])[0];

    // 7) 车型/产品结构（二轮：骑式 / 弯梁 / 踏板）
    // 车型名称可能含历史「骑式式」，统一归一
    const vtNorm = c => (c === '骑式式' || c === '跨骑式') ? '骑式' : c;
    const vtYear = {}; // { year: { 骑式: n, 弯梁式: n, 踏板式: n } }
    byVtype.filter(r => r.scope === '二轮' && r.indicator === '生产').forEach(r => {
      const c = vtNorm(r.category);
      if (!['骑式', '弯梁式', '踏板式'].includes(c)) return;
      vtYear[r.year] = vtYear[r.year] || {};
      vtYear[r.year][c] = (vtYear[r.year][c] || 0) + r.value;
    });
    const vtLast = vtYear[lastYear] || {};
    const vtPrev = vtYear[prevYear] || {};
    const vtTotalLast = (vtLast['骑式'] || 0) + (vtLast['弯梁式'] || 0) + (vtLast['踏板式'] || 0);
    const scooterShareLast = vtTotalLast ? (vtLast['踏板式'] || 0) / vtTotalLast * 100 : 0;
    const scooterSharePrev = (vtPrev['骑式'] || 0) + (vtPrev['弯梁式'] || 0) + (vtPrev['踏板式'] || 0)
      ? (vtPrev['踏板式'] || 0) / ((vtPrev['骑式'] || 0) + (vtPrev['弯梁式'] || 0) + (vtPrev['踏板式'] || 0)) * 100 : 0;
    const topVt = Object.entries(vtLast).sort((a, b) => b[1] - a[1])[0];

    // 8) 产销率 / 库存健康度（最后一个完整年）
    const salesLastYear = yearlySales[lastYear] || 0;
    const prodLastYear = yearlyProd[lastYear] || 0;
    const sellThrough = prodLastYear ? salesLastYear / prodLastYear * 100 : 0;

    // 9) 出口结构：大排量出口占比（产品出海升级信号）
    const exportLargeAll = exportMonthly.filter(r => r.scope === '二轮' && r.type === '排量' && LARGE_DISP.includes(r.category)).reduce((a, r) => a + r.value, 0);
    const export2wAll = exportMonthly.filter(r => r.scope === '二轮' && r.type === '排量').reduce((a, r) => a + r.value, 0);
    const exportLargeShare = export2wAll ? exportLargeAll / export2wAll * 100 : 0;

    // 生成洞察列表
    const insights = [];
    // 增长趋势（基于最后一个完整年 vs 上一个完整年）
    const yoyNote = (latestYear > lastYear)
      ? `${latestYear} 年（截至 ${yearMonthCount[latestYear]} 月）产量 <span class="num">${fmt(yearlyProd[latestYear])}</span> 辆`
      : '';
    if (yoyLatest > 0) {
      insights.push({ tone: 'up', txt: `行业保持增长态势：${lastYear} 年产量 <span class="num">${fmt(pLast)}</span> 辆，同比 <span class="good">+${yoyLatest.toFixed(1)}%</span>。近三年复合增速 <span class="num">${cagr3.toFixed(1)}%</span>，行业景气度稳健。${yoyNote}` });
    } else {
      insights.push({ tone: 'down', txt: `行业出现调整：${lastYear} 年产量同比 <span class="bad">${yoyLatest.toFixed(1)}%</span>，需关注需求变化与库存压力。${yoyNote}` });
    }
    // 电动化
    if (evShare > 5) {
      insights.push({ tone: 'info', txt: `电动化已成重要赛道：${lastYear} 年电动摩托车产量 <span class="num">${fmt(evLast)}</span> 辆，占比 <span class="num">${evShare.toFixed(1)}%</span>。雅迪、爱玛等电动品牌已深度入局，传统燃油车企需评估电动化转型节奏。` });
    } else {
      insights.push({ tone: 'info', txt: `电动化尚处起步：电动摩托车占比仅 ${evShare.toFixed(1)}%，但政策与消费趋势指向电动化，宜提前布局。` });
    }
    // 大排量
    if (largeGrowth > 0) {
      insights.push({ tone: 'up', txt: `大排量（>250ml）是增长亮点：${lastYear} 年产量 <span class="num">${fmt(largeLast)}</span> 辆，同比 <span class="good">+${largeGrowth.toFixed(1)}%</span>，占比 ${largeShare.toFixed(1)}%。玩乐型/高端化市场快速扩容，是品牌溢价与差异化竞争的主战场。` });
    } else {
      insights.push({ tone: 'warn', txt: `大排量（>250ml）增长放缓（${largeGrowth.toFixed(1)}%），占比 ${largeShare.toFixed(1)}%，高端化进程需政策与产品力共同驱动。` });
    }
    // 出口
    if (exportRatio > 40) {
      insights.push({ tone: 'up', txt: `出口导向显著：出口占销量比 <span class="num">${exportRatio.toFixed(1)}%</span>。海外市场是增长核心引擎，需关注汇率、贸易壁垒与海外渠道建设。` });
    } else if (exportRatio > 20) {
      insights.push({ tone: 'info', txt: `内外销并重：出口占比 ${exportRatio.toFixed(1)}%。建议平衡国内渠道深耕与海外市场拓展。` });
    } else {
      insights.push({ tone: 'info', txt: `以内销为主：出口占比 ${exportRatio.toFixed(1)}%，海外拓展空间较大。` });
    }
    // 品牌集中度
    insights.push({ tone: 'info', txt: `市场集中度：CR5 <span class="num">${cr5.toFixed(1)}%</span>、CR10 <span class="num">${cr10.toFixed(1)}%</span>。头部品牌「${topBrand}」领跑，中小企业竞争压力大，需走差异化或细分市场路线。` });
    // 季节性
    insights.push({ tone: 'info', txt: `季节性规律：生产旺季为 <span class="num">${peakMonth[0]} 月</span>，淡季为 <span class="num">${troughMonth[0]} 月</span>。可据此优化排产计划与备货节奏。` });
    // 车型/产品结构
    if (topVt && vtTotalLast > 0) {
      insights.push({ tone: 'info', txt: `产品结构：${lastYear} 年二轮主力车型为「<strong>${topVt[0]}</strong>」（<span class="num">${fmt(topVt[1])}</span> 辆，占 ${(topVt[1] / vtTotalLast * 100).toFixed(1)}%）。踏板式占比 <span class="num">${scooterShareLast.toFixed(1)}%</span>${scooterSharePrev ? `（较 ${prevYear} 年 ${scooterShareLast > scooterSharePrev ? '上升' : '下降'} ${Math.abs(scooterShareLast - scooterSharePrev).toFixed(1)} 个百分点）` : ''}，反映城市通勤与女性消费群体的扩张趋势。` });
    }
    // 产销率/库存健康度
    if (sellThrough >= 98 && sellThrough <= 102) {
      insights.push({ tone: 'up', txt: `产销平衡健康：${lastYear} 年产销率 <span class="num">${sellThrough.toFixed(1)}%</span>，产销衔接良好，库存压力小，经营稳健。` });
    } else if (sellThrough > 102) {
      insights.push({ tone: 'warn', txt: `产销率偏高（<span class="num">${sellThrough.toFixed(1)}%</span>）：销量略超产量，可能存在去库存或供不应求，需关注补产节奏。` });
    } else {
      insights.push({ tone: 'warn', txt: `产销率偏低（<span class="num">${sellThrough.toFixed(1)}%</span>）：产量大于销量，库存有积压风险，需控制排产并强化去化。` });
    }
    // 出口产品结构升级
    if (exportLargeShare > 0) {
      insights.push({ tone: 'info', txt: `出口产品升级：二轮出口中大排量（>250ml）占比 <span class="num">${exportLargeShare.toFixed(1)}%</span>，反映中国摩托车出口正从低端代步向中大排量、高附加值方向升级，品牌出海含金量提升。` });
    }

    // 决策建议（分产品、客户/市场、运营、战略四类）
    const recs = [];
    // —— 产品与车型 ——
    if (largeGrowth > 10) recs.push(`【产品】加码大排量（>250ml）产品线：该细分市场增速 ${largeGrowth.toFixed(0)}%，是当前最具增长潜力和利润空间的赛道，建议增加研发与产能投入，布局玩乐型、ADV 等高端品类。`);
    if (topVt) recs.push(`【产品】巩固主力车型「${topVt[0]}」（占比 ${(topVt[1] / vtTotalLast * 100).toFixed(0)}%）的同时，关注踏板式增长（占比 ${scooterShareLast.toFixed(0)}%），针对城市通勤、女性及年轻客群开发差异化踏板车型。`);
    // —— 客户与市场 ——
    if (exportRatio > 30) recs.push(`【客户】深化海外市场布局：出口占比 ${exportRatio.toFixed(0)}%，建议按区域细分目标客户（东南亚代步、欧美中大排量玩乐），建立本地化渠道与售后网络，管理汇率与贸易政策风险。`);
    else if (exportRatio > 15) recs.push(`【客户】内外销并重：出口占比 ${exportRatio.toFixed(0)}%，建议国内深耕下沉市场与渠道，海外聚焦高潜力区域，形成双轮驱动。`);
    if (cr10 > 60) recs.push(`【客户】锁定细分客群突破：CR10 达 ${cr10.toFixed(0)}%，头部集中度高，建议在细分排量段、特定场景（外卖/物流/越野）或区域市场寻找差异化客群，避开头部正面竞争。`);
    // —— 电动化战略 ——
    if (evShare > 5) recs.push(`【战略】制定电动化路线图：电动摩托车占比已至 ${evShare.toFixed(1)}%，建议评估自身电动产品矩阵，切入城市短途出行与配送电动市场，避免在新赛道掉队。`);
    // —— 运营与排产 ——
    if (sellThrough < 98) recs.push(`【运营】强化库存去化：${lastYear} 年产销率 ${sellThrough.toFixed(1)}%，建议控制排产节奏、加大促销与渠道去化力度，防范库存积压。`);
    recs.push(`【运营】优化排产与备货节奏：结合 ${peakMonth[0]} 月旺季、${troughMonth[0]} 月淡季规律，动态调整产能与安全库存，降低旺季缺货与淡季积压风险。`);

    // 汇总统计卡
    const stats = [
      { icon: '📈', label: `${lastYear} 年产量 Production`, value: fmt(pLast), sub: `同比 YoY ${yoyLatest >= 0 ? '+' : ''}${yoyLatest.toFixed(1)}% · 近3年CAGR ${cagr3.toFixed(1)}%` },
      { icon: '🔌', label: `电动化占比 EV Share (${lastYear})`, value: evShare.toFixed(1) + '%', sub: `电动产量 ${fmt(evLast)}` },
      { icon: '🏍️', label: `大排量占比 >250ml (${lastYear})`, value: largeShare.toFixed(1) + '%', sub: `同比 YoY ${largeGrowth >= 0 ? '+' : ''}${largeGrowth.toFixed(1)}%` },
      { icon: '🌍', label: '出口占比 Export Share', value: exportRatio.toFixed(1) + '%', sub: `品牌集中度 CR5 ${cr5.toFixed(1)}%` },
    ];

    // 渲染
    const toneColor = { up: '#ef4444', down: '#10b981', warn: '#f59e0b', info: '#3b82f6' };
    root.innerHTML = `
      <div class="insights-summary">
        ${stats.map(s => `
          <div class="insight-stat">
            <div class="stat-icon">${s.icon}</div>
            <div class="stat-label">${s.label}</div>
            <div class="stat-value">${s.value}</div>
            <div class="stat-sub">${s.sub}</div>
          </div>`).join('')}
      </div>
      <div class="insight-grid">
        <div class="insight-card">
          <h3>📊 关键业务发现 Key Findings</h3>
          <ul class="insight-list">
            ${insights.map(i => `
              <li>
                <span class="dot" style="background:${toneColor[i.tone]}"></span>
                <span class="txt">${i.txt}</span>
              </li>`).join('')}
          </ul>
        </div>
        <div class="insight-card">
          <h3>💡 战略决策建议 Strategic Recommendations</h3>
          <ol class="rec-list">
            ${recs.map(r => `<li>${r}</li>`).join('')}
          </ol>
        </div>
      </div>
      <div class="insight-card" style="margin-bottom:0;">
        <h3>📋 数据覆盖 Data Coverage <span class="tag info">${firstYear} — ${lastYear}</span></h3>
        <p style="font-size:13px;color:var(--text-muted);margin:0;line-height:1.7;">
          覆盖 ${years.length} 年（${firstYear} 年 2 月 至 ${lastYear} 年），共 ${monthlyTotal.filter(r => r.indicator === '生产').length} 个月度观测。
          数据来源：全国摩托车生产企业产销情况月报。注：2020–2022 年出口数据因源报表口径调整存在缺失，出口相关指标以可获取月份为基准。
        </p>
      </div>
    `;
  }

  // ---- Helpers ----
  function sortedMonths(records) {
    const set = new Set();
    records.forEach(r => set.add(`${r.year}-${String(r.month).padStart(2, '0')}`));
    return [...set].sort();
  }
  function sortedYears(records) {
    return [...new Set(records.map(r => r.year))].sort();
  }
  // 从月份序列提取所有年份（用于 markLine 年份分隔）
  function yearBoundaries(months) {
    const ys = new Set();
    months.forEach(ym => {
      const [y, m] = ym.split('-').map(Number);
      if (m === 1) ys.add(y);
    });
    return [...ys].sort();
  }

  // 排量筛选（用于本身带 category 维度的数据集，如 byDisp2w/byDisp3w）
  // byDisp2w 的 scope 固定为二轮，byDisp3w 固定为三轮，电动单独
  function applyDispFilter(records, f) {
    if (!f.displacements.length) return records;
    return records.filter(r => dispMatch(r, f.displacements));
  }

  // 顶部提示条：说明当前口径来源
  function updateFilterNote(f, source) {
    const el = document.getElementById('dispFilterNote');
    const parts = [];
    // 报告类型 / 排量快捷 / 动力类型 —— 仅作用于「月度趋势」图
    const trendOnly = [];
    if (f.reportType === 'yearly') {
      trendOnly.push('报告类型：<strong>年度 Annual</strong>');
    }
    if (f.powertrain === 'ev') {
      trendOnly.push('动力：<strong>电动 EV</strong>');
    } else if (f.powertrain === 'ice') {
      trendOnly.push('动力：<strong>燃油 ICE</strong>');
    }
    if (f.dispPreset && f.dispPreset !== 'all') {
      const labels = { ge150: '≥150cc', gt250: '>250cc', ge400: '≥400cc', ge800: '≥800cc' };
      trendOnly.push(`排量：<strong>${labels[f.dispPreset]}</strong>`);
    }
    if (trendOnly.length) {
      parts.push(`📈 <strong>仅「月度趋势」图生效 Trend-only</strong>：${trendOnly.join(' · ')}`);
      el.className = 'filter-note warn';
    } else {
      el.className = 'filter-note';
    }
    if (f.displacements.length) {
      const labels = f.displacements.map(d => d.bucket);
      parts.push(`已选排量 Displacement <strong>${f.displacements.length}</strong> 段：${labels.join('、')}`);
      parts.push('趋势 / 品牌图表已按该排量口径重算（由「品牌×排量」明细聚合）');
      el.className = 'filter-note';
    }
    if (f.displacements.length && f.scope !== 'all') {
      parts.push(`车型范围 Category <strong>${f.scope}</strong>`);
    }
    if (f.displacements.length) {
      parts.push('<em>注：「车型分布」页与「年度明细表」为官方汇总口径，不含排量维度，不受排量筛选影响</em>');
      el.className = 'filter-note warn';
    }
    el.innerHTML = parts.join(' · ');
  }

  // ---- Main update flow ----
  function applyAll() {
    const f = getFilters();

    // 排量感知数据源（全局，供除趋势图外的所有图表）
    const cur = buildData(f);
    const base = buildData(f, f.years.map(y => y - 1));          // 同比基准
    const full = buildData(Object.assign({}, f, { years: META.years }));  // 环比完整序列

    const filteredTotal = cur.totals;
    const baseTotal = base.totals;
    const filteredMfg = cur.mfg;

    // 排量 / 车型数据集
    const filteredDisp2w = applyDispFilter(applyFilters(byDisp2w, f), f);
    const filteredDisp3w = applyDispFilter(applyFilters(byDisp3w, f), f);
    const filteredVtype = applyFilters(byVtype, f);   // 车型维度无排量字段，保持汇总口径

    updateKPIs(filteredTotal, filteredMfg);
    updateFilterNote(f, cur.source);

    // 趋势图：独立应用「报告类型 / 排量快捷 / 动力类型」三个专属筛选
    const trendF = buildTrendData(f);
    const trendBase = buildTrendData(Object.assign({}, f, { years: f.years.map(y => y - 1) }));
    // Overview charts
    renderTrend(trendF, trendBase);
    renderRatio(filteredTotal);
    renderMoM(filteredTotal, full.totals);
    // Displacement
    renderDisp2wYear(filteredDisp2w);
    renderDisp3wYear(filteredDisp3w);
    renderDispHeatmap(f);
    renderDispLines(f);
    // Vehicle types
    renderVtypePie(filteredVtype);
    renderVtypeStacked(filteredVtype);
    renderVtype3w(filteredVtype);
    // Manufacturers
    renderMfgRank(filteredMfg);
    renderMfgPie(filteredMfg);
    renderMfgTrend(filteredMfg);
    renderMfgRankChange(filteredMfg);
    renderMfgCompare(filteredMfg);
    renderMfgLargeDisp();
    renderMfgTable(filteredMfg);
    // Export / 内销外销
    renderExport();
    // Annual
    renderAnnualTotal(filteredTotal);
    renderAnnualYoy(filteredTotal, baseTotal);
    renderEvShare(filteredDisp2w);
    renderLargeDisp(filteredDisp2w);
    renderAnnualTable();
    // Insights / 业务洞察
    renderInsights();
  }

  // 把月度数据按年聚合（年度合计），返回 [{year, month=1, indicator, value}]
  function aggregateYearly(monthlyRecords) {
    const map = new Map();
    monthlyRecords.forEach(r => {
      const key = `${r.year}|${r.indicator}`;
      map.set(key, (map.get(key) || 0) + r.value);
    });
    return [...map.entries()].map(([k, v]) => {
      const [y, ind] = k.split('|');
      return { year: +y, month: 1, indicator: ind, value: v };
    }).sort((a, b) => a.year - b.year);
  }

  // 排量段下限解析：'50ml<排量≤60ml' → 50；'排量>800ml' → 800；'排量≤50ml' → 0；'电动摩托车' → null
  function dispLowerBound(bucket) {
    if (!bucket || bucket === '电动摩托车') return null;
    if (/^排量≤/.test(bucket)) return 0;
    if (/^排量>/.test(bucket)) {
      const m = bucket.match(/(\d+)/);
      return m ? +m[1] : null;
    }
    const m = bucket.match(/^(\d+)\s*ml\s*[<＜]/);
    return m ? +m[1] : null;
  }

  // 排量快捷预设 → 下限判断条件（null 表示不筛选）
  function dispPresetPredicate(preset) {
    if (!preset || preset === 'all') return null;
    // ge150: ≥150（含）; gt250: >250（不含）; ge400: ≥400（含）; ge800: ≥800（含）
    return (bucket) => {
      const lb = dispLowerBound(bucket);
      if (lb === null) return false;  // 电动摩托车不计入燃油排量快捷
      if (preset === 'ge150') return lb >= 150;
      if (preset === 'gt250') return lb > 250;
      if (preset === 'ge400') return lb >= 400;
      if (preset === 'ge800') return lb >= 800;
      return false;
    };
  }

  // 趋势图独立数据源：只应用「报告类型 / 排量快捷 / 动力类型」三个筛选，
  // 不影响其他图表（其他图表用全局 filteredTotal）
  function buildTrendData(f) {
    const needDetail = (f.powertrain && f.powertrain !== 'all') ||
                       (f.dispPreset && f.dispPreset !== 'all');
    // 无额外筛选 + 月度报告 → 直接用官方口径（精度最高）
    if (!needDetail && f.reportType !== 'yearly') {
      return buildData(f).totals;
    }

    // 需要明细筛选 → 从 byDisp2w 聚合
    const pred = dispPresetPredicate(f.dispPreset);
    const rows = byDisp2w.filter(r =>
      f.years.includes(r.year) &&
      f.months.includes(r.month) &&
      (f.indicator === 'both' || r.indicator === f.indicator) &&
      powertrainMatch(r.category, f.powertrain) &&
      (pred === null || pred(r.category))
    );

    const tMap = new Map();
    rows.forEach(r => {
      const tk = `${r.year}|${r.month}|${r.indicator}`;
      tMap.set(tk, (tMap.get(tk) || 0) + r.value);
    });
    let totals = [...tMap.entries()].map(([k, v]) => {
      const [y, mo, ind] = k.split('|');
      return { year: +y, month: +mo, indicator: ind, value: v };
    });

    if (f.reportType === 'yearly') totals = aggregateYearly(totals);
    return totals;
  }

  document.getElementById('btnApply').addEventListener('click', applyAll);
  document.getElementById('btnDispAll').addEventListener('click', () => {
    Array.from(fDisp.options).forEach(o => o.selected = true);
    applyAll();
  });
  document.getElementById('btnDispNone').addEventListener('click', () => {
    Array.from(fDisp.options).forEach(o => o.selected = false);
    applyAll();
  });
  // 厂家销量对比快捷按钮：选 Top 10 / 清空
  document.getElementById('btnMfgCompareTop10').addEventListener('click', () => {
    Array.from(fMfg.options).forEach(o => o.selected = false);
    // 按当前口径取销量 Top 10 厂家
    const f = getFilters();
    const cur = buildData(f);
    const map = new Map();
    cur.mfg.forEach(r => map.set(r.manufacturer, (map.get(r.manufacturer) || 0) + r.value));
    const top10 = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(x => x[0]);
    top10.forEach(name => {
      const opt = Array.from(fMfg.options).find(o => o.value === name);
      if (opt) opt.selected = true;
    });
    applyAll();
  });
  document.getElementById('btnMfgCompareClear').addEventListener('click', () => {
    Array.from(fMfg.options).forEach(o => o.selected = false);
    applyAll();
  });
  document.getElementById('btnReset').addEventListener('click', () => {
    Array.from(fYear.options).forEach(o => o.selected = true);
    Array.from(fMonth.options).forEach(o => o.selected = true);
    fIndicator.value = 'both';
    fScope.value = 'all';
    Array.from(fDisp.options).forEach(o => o.selected = false);
    Array.from(fMfg.options).forEach(o => o.selected = false);
    fReportType.value = 'monthly';
    fDispPreset.value = 'all';
    fPowertrain.value = 'all';
    applyAll();
  });

  // 排量快捷：只作用于「月度趋势」图（不改变全局排量段 fDisp 的勾选）
  fDispPreset.addEventListener('change', () => {
    applyAll();
  });

  // 报告类型：只作用于「月度趋势」图（月度/年度聚合）
  fReportType.addEventListener('change', () => {
    applyAll();
  });

  // 动力类型：只作用于「月度趋势」图（燃油/电动）
  fPowertrain.addEventListener('change', () => {
    applyAll();
  });

  // ---- 上传月度更新文件 ----
  const btnUpload = document.getElementById('btnUpload');
  const fileInput = document.getElementById('fileInput');
  const uploadStatus = document.getElementById('uploadStatus');

  btnUpload.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    const setStatus = (text, cls) => {
      uploadStatus.textContent = text;
      uploadStatus.className = 'upload-status' + (cls ? ' ' + cls : '');
    };

    setStatus(`上传中 Uploading ${file.name} ...`);
    btnUpload.disabled = true;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const resp = await fetch('/upload', { method: 'POST', body: formData });
      const data = await resp.json();

      if (!data.ok) {
        throw new Error(data.error || '上传失败');
      }

      const r = data.result;
      setStatus(
        `✓ 已更新 ${r.year}年${r.month}月 Updated ${r.year}-${String(r.month).padStart(2,'0')}，页面即将刷新 Reloading...`,
        'ok'
      );

      // 重新加载页面以刷新数据（最可靠）
      setTimeout(() => location.reload(), 1500);

    } catch (e) {
      setStatus(`✗ 失败 Failed：${e.message}`, 'error');
    } finally {
      btnUpload.disabled = false;
      fileInput.value = '';
    }
  });

  // Re-render on resize
  window.addEventListener('resize', () => Object.values(charts).forEach(c => c && c.resize()));

  // Initial render
  applyAll();
})();
