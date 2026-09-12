// 无头渲染校验：用 ECharts SSR 把每张 option 渲染成 SVG，捕获任何运行时错误
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'output');

// --- 最小 DOM 桩，让 zrender 走浏览器分支（SSR 渲染需要） ---
global.window = global;
global.self = global;
global.navigator = { userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' };
global.SVGRect = function SVGRect() {};
global.document = {
  documentElement: { style: {} },
  createElement: () => ({ style: {}, getContext: () => null, setAttribute() {}, appendChild() {} }),
  addEventListener() {}, removeEventListener() {}
};
global.Image = function Image() {};
require(path.join(OUT, 'report_charts.js'));
const echarts = require(path.join(OUT, 'echarts.min.js'));

echarts.setPlatformAPI({
  measureText: (text, font) => ({ width: String(text).length * 12, height: 14 })
});

const charts = global.REPORT_CHARTS;
let ok = 0, fail = 0;
const problems = [];

charts.forEach((c) => {
  // 1) 基本结构检查
  const must = ['id', 'title', 'subtitle', 'caption', 'height', 'option'];
  must.forEach((k) => {
    if (c[k] === undefined || c[k] === null || c[k] === '') {
      problems.push(`[${c.id}] 缺少字段 ${k}`);
    }
  });
  const o = c.option;
  if (!o.series || !o.series.length) problems.push(`[${c.id}] 没有 series`);
  (o.series || []).forEach((s, i) => {
    if (!s.type) problems.push(`[${c.id}] series[${i}] 缺少 type`);
    if (!s.name) problems.push(`[${c.id}] series[${i}] 缺少 name`);
    if (s.data === undefined) problems.push(`[${c.id}] series[${i}] 缺少 data`);
    else if (!Array.isArray(s.data) || s.data.length === 0) problems.push(`[${c.id}] series[${i}] data 为空`);
    else {
      const nonempty = s.data.some((d) => {
        if (d === null || d === undefined) return false;
        if (typeof d === 'object' && 'value' in d) return d.value !== null && d.value !== undefined;
        return true;
      });
      if (!nonempty) problems.push(`[${c.id}] series[${i}](${s.name}) 全部数据点为空`);
    }
    // NaN 检查
    JSON.stringify(s.data, (k, v) => {
      if (typeof v === 'number' && !isFinite(v)) problems.push(`[${c.id}] series[${i}] 存在非法数值 ${v}`);
      return v;
    });
  });
  if (o.xAxis) {
    const xs = Array.isArray(o.xAxis) ? o.xAxis : [o.xAxis];
    xs.forEach((x, i) => { if (x.type === 'category' && (!x.data || !x.data.length)) problems.push(`[${c.id}] xAxis[${i}] 类目为空`); });
  }
  if (o.yAxis) {
    const ys = Array.isArray(o.yAxis) ? o.yAxis : [o.yAxis];
    ys.forEach((y, i) => { if (y.type === 'category' && (!y.data || !y.data.length)) problems.push(`[${c.id}] yAxis[${i}] 类目为空`); });
  }

  // 2) 真实渲染
  try {
    const inst = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: c.height || 400 });
    inst.setOption(o, true);
    const svg = inst.renderToSVGString();
    if (!svg || svg.length < 500) problems.push(`[${c.id}] 渲染输出过小 (${svg ? svg.length : 0} bytes)`);
    const textCount = (svg.match(/<text/g) || []).length;
    if (textCount < 3) problems.push(`[${c.id}] 渲染几乎没有文字 (${textCount})`);
    inst.dispose();
    ok++;
    console.log(`  OK  ${c.id.padEnd(28)} svg=${String(svg.length).padStart(7)}B  texts=${String(textCount).padStart(3)}  series=${o.series.length}`);
  } catch (e) {
    fail++;
    problems.push(`[${c.id}] 渲染抛错: ${e && e.message ? e.message : e}`);
    console.log(`  ERR ${c.id} -> ${e && e.message ? e.message : e}`);
  }
});

console.log('\n=========================================');
console.log(`渲染：成功 ${ok} / 失败 ${fail} / 共 ${charts.length}`);
if (problems.length) {
  console.log(`\n发现 ${problems.length} 个问题：`);
  problems.forEach((p) => console.log('  - ' + p));
  process.exit(1);
} else {
  console.log('全部通过：无结构问题、无渲染错误。');
}
