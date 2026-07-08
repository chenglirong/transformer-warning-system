/**
 * 监测总览 · 360 天整体态势（合成时序 SYN-001）
 */
(function () {
  var SERIES = [];
  var LEVELS = [];
  var RATES = [];
  var CURRENT_DAY = 287;
  var trendRange = 360;

  var LEVEL_LABELS = { normal: '正常', w1: '注意值 1', w2: '注意值 2', alarm: '告警值' };
  var LEVEL_HINTS = {
    normal: '各气体在表 A.3 正常范围内',
    w1: '单项达注意值 1，需关注',
    w2: '可能存在隐患，需加强监视（A.1）',
    alarm: '可能存在缺陷，需采取措施（A.1）'
  };
  var LEVEL_COLORS = { normal: '#34d399', w1: '#fbbf24', w2: '#fb923c', alarm: '#f87171' };
  var GAS_MAX = { h2: 150, ch4: 150, c2h4: 150, c2h6: 150, c2h2: 5 };
  var TH_W2 = 150;
  var C2H2_W2 = 5;
  var RATE_THRESH = 10;

  function round1(v) { return Math.round(v * 10) / 10; }
  function pct(part, total) { return total ? round1(part / total * 100) : 0; }

  function gasTier(value, gas) {
    if (gas === 'c2h2') {
      if (value >= 8) return 'alarm';
      if (value >= 5) return 'w2';
      if (value >= 1) return 'w1';
      return 'normal';
    }
    if (value >= 150) return 'w2';
    if (value >= 120) return 'w1';
    return 'normal';
  }

  function tierRank(t) {
    return { normal: 0, w1: 1, w2: 2, alarm: 3 }[t] || 0;
  }

  function classifyDay(d) {
    var tiers = [gasTier(d.c2h2, 'c2h2'), gasTier(d.h2, 'h2'), gasTier(d.th, 'th')];
    return tiers.sort(function (a, b) { return tierRank(b) - tierRank(a); })[0];
  }

  function buildSeries() {
    var data = [];
    for (var i = 0; i < 360; i++) {
      var ch4 = 55 + i * 0.11 + Math.sin(i / 12) * 6;
      var c2h4 = 30 + i * 0.08 + Math.sin(i / 10) * 4;
      var c2h6 = 14 + i * 0.035 + Math.sin(i / 14) * 2;
      var c2h2 = 1.2 + i * 0.018 + (i > 270 ? (i - 270) * 0.025 : 0);
      var h2 = 95 + i * 0.42 + Math.sin(i / 7) * 10;
      if (i > 270) {
        c2h2 += (i - 270) * 0.04;
        h2 += (i - 270) * 0.35;
      }
      data.push({
        date: 'D' + (i + 1),
        h2: round1(h2),
        ch4: round1(ch4),
        c2h4: round1(c2h4),
        c2h6: round1(c2h6),
        c2h2: round1(c2h2),
        th: round1(ch4 + c2h4 + c2h6 + c2h2)
      });
    }
    return data;
  }

  function buildRates() {
    var data = [];
    for (var i = 1; i < SERIES.length; i++) {
      var prev = SERIES[i - 1];
      var cur = SERIES[i];
      if (!prev.th) continue;
      var lv = LEVELS[i];
      var rate = round1(((cur.th - prev.th) / prev.th) * 100 * (30 / 7));
      data.push({
        rate: rate,
        pre: lv !== 'w2' && lv !== 'alarm' && rate > RATE_THRESH
      });
    }
    return data;
  }

  function countLevels() {
    var c = { normal: 0, w1: 0, w2: 0, alarm: 0 };
    LEVELS.forEach(function (lv) { c[lv]++; });
    return c;
  }

  function countPreWarnings() {
    return RATES.filter(function (r) { return r.pre; }).length;
  }

  function countRateOverDays() {
    return RATES.filter(function (r) { return r.rate > RATE_THRESH; }).length;
  }

  function quarterAbnormalDays() {
    var q = [];
    for (var qn = 0; qn < 4; qn++) {
      var start = qn * 90;
      var end = start + 90;
      var n = 0;
      for (var i = start; i < end; i++) {
        if (LEVELS[i] !== 'normal') n++;
      }
      q.push(n);
    }
    return q;
  }

  function currentRate() {
    return RATES.length ? RATES[RATES.length - 1].rate : 0;
  }

  function statusTag(value, threshold, overLabel, okLabel) {
    return value >= threshold ? overLabel : okLabel;
  }

  function updateSummary() {
    var counts = countLevels();
    var normalPct = pct(counts.normal, 360);
    var cur = SERIES[CURRENT_DAY - 1];
    var d90 = SERIES[Math.max(0, CURRENT_DAY - 90)];
    var preCount = countPreWarnings();
    var rateOverDays = countRateOverDays();
    var rate = currentRate();
    var lv = LEVELS[CURRENT_DAY - 1];

    setText('stat-current-level', LEVEL_LABELS[lv]);
    var levelEl = document.getElementById('stat-current-level');
    if (levelEl) {
      levelEl.className = 'ops-kpi-value ' + (lv === 'normal' ? 'ok' : lv === 'w1' ? 'pre' : 'warn');
    }
    setText('stat-level-hint', LEVEL_HINTS[lv]);

    setText('stat-th-value', String(cur.th));
    var thEl = document.getElementById('stat-th-value');
    if (thEl) {
      thEl.innerHTML = cur.th + '<span class="ops-kpi-unit">μL/L</span>';
      thEl.className = 'ops-kpi-value ' + (cur.th >= TH_W2 ? 'warn' : cur.th >= 120 ? 'pre' : '');
    }
    setText('stat-th-sub', statusTag(cur.th, TH_W2, '超注意值 2 线 ' + TH_W2, '未超注意值 2') + ' · 90天 ' + d90.th + '→' + cur.th);

    setText('stat-c2h2-value', String(cur.c2h2));
    var c2El = document.getElementById('stat-c2h2-value');
    if (c2El) {
      c2El.innerHTML = cur.c2h2 + '<span class="ops-kpi-unit">μL/L</span>';
      c2El.className = 'ops-kpi-value ' + (cur.c2h2 >= C2H2_W2 ? 'warn' : cur.c2h2 >= 1 ? 'pre' : '');
    }
    setText('stat-c2h2-sub', statusTag(cur.c2h2, C2H2_W2, '超注意值 2 线 ' + C2H2_W2, '未超注意值 2'));

    var rateEl = document.getElementById('stat-rate-value');
    if (rateEl) {
      rateEl.innerHTML = rate + '<span class="ops-kpi-unit">%/月</span>';
      rateEl.className = 'ops-kpi-value ' + (rate > RATE_THRESH ? 'warn' : '');
    }
    setText('stat-rate-sub', (rate > RATE_THRESH ? '超 ' + RATE_THRESH + '% 阈 · ' : '') +
      '360天超阈 ' + rateOverDays + ' 次 · 「预」' + preCount + ' 次');

    var el = document.getElementById('overview-summary');
    if (el) {
      el.textContent =
        '360 天监测：正常 ' + normalPct + '%（' + counts.normal + ' 天），非正档 ' + (360 - counts.normal) + ' 天；' +
        '近 90 天总烃 ' + d90.th + '→' + cur.th + ' μL/L，产气速率 ' + rate + '%/月；' +
        '当前' + LEVEL_LABELS[lv] + '。详细判据与报告请走 Agent 分析。';
    }

    DGACharts.miniSparkline('#spark-level', LEVELS.map(function (l) { return tierRank(l); }), '#fb923c');
    DGACharts.miniSparkline('#spark-th', SERIES.slice(-90).map(function (d) { return d.th; }), '#d4a054');
    DGACharts.miniSparkline('#spark-c2h2', SERIES.slice(-90).map(function (d) { return d.c2h2; }), '#f87171');
    DGACharts.miniSparkline('#spark-rate', RATES.slice(-60).map(function (d) { return d.rate; }), '#3dbfb0');
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function renderTrend() {
    var start = Math.max(0, CURRENT_DAY - trendRange);
    DGACharts.glowAreaChart('#dashboard-trend', {
      data: SERIES.slice(start, CURRENT_DAY),
      lines: [
        { key: 'th', color: '#d4a054', fill: true },
        { key: 'c2h2', color: '#f87171', fill: false },
        { key: 'h2', color: '#5b9fd4', fill: false }
      ],
      thresholds: [
        { value: TH_W2, label: '总烃 150', color: '#fb923c' }
      ]
    });
  }

  function renderLevelDonut() {
    var counts = countLevels();
    DGACharts.glowDonut('#chart-level-donut', {
      centerLabel: '采样',
      segments: [
        { label: '正常', value: counts.normal, color: LEVEL_COLORS.normal },
        { label: '注意1', value: counts.w1, color: LEVEL_COLORS.w1 },
        { label: '注意2', value: counts.w2, color: LEVEL_COLORS.w2 },
        { label: '告警', value: counts.alarm, color: LEVEL_COLORS.alarm }
      ]
    });
    var legend = document.getElementById('legend-level-donut');
    if (legend) {
      legend.innerHTML = ['normal', 'w1', 'w2', 'alarm'].map(function (k) {
        return '<li><i style="background:' + LEVEL_COLORS[k] + '"></i>' +
          LEVEL_LABELS[k] + ' <span>' + counts[k] + '天 · ' + pct(counts[k], 360) + '%</span></li>';
      }).join('');
    }
  }

  function renderLevelStrip() {
    DGACharts.levelStrip('#level-strip', { levels: LEVELS, height: 64 });
  }

  function renderQuarterBars() {
    var q = quarterAbnormalDays();
    DGACharts.barChart('#chart-quarter', {
      items: [
        { label: 'Q1', value: q[0], color: '#5b9fd4' },
        { label: 'Q2', value: q[1], color: '#5b9fd4' },
        { label: 'Q3', value: q[2], color: '#fb923c' },
        { label: 'Q4', value: q[3], color: '#f87171' }
      ]
    });
  }

  function renderRadar() {
    var cur = SERIES[CURRENT_DAY - 1];
    var gases = ['h2', 'ch4', 'c2h4', 'c2h6', 'c2h2'];
    var labels = ['H₂', 'CH₄', 'C₂H₄', 'C₂H₆', 'C₂H₂'];
    DGACharts.radarChart('#chart-gas-radar', {
      axes: gases.map(function (g, i) {
        return {
          label: labels[i],
          value: cur[g],
          max: GAS_MAX[g] * 1.2,
          color: '#d4a054'
        };
      })
    });
    var medEl = document.getElementById('radar-median-note');
    if (medEl) {
      medEl.textContent = '五烃 vs 表 A.3 注意值 2 参考上限（雷达归一化）';
    }
  }

  function renderRates() {
    DGACharts.rateChart('#rate-chart', { data: RATES, threshold: RATE_THRESH });
  }

  function refreshAll() {
    updateSummary();
    renderTrend();
    renderLevelDonut();
    renderLevelStrip();
    renderQuarterBars();
    renderRadar();
    renderRates();
  }

  function init() {
    SERIES = buildSeries();
    LEVELS = SERIES.map(classifyDay);
    RATES = buildRates();

    document.querySelectorAll('.chart-tab[data-range]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        document.querySelectorAll('.chart-tab[data-range]').forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        trendRange = parseInt(tab.dataset.range, 10);
        renderTrend();
      });
    });
  }

  init();
  refreshAll();
  window.addEventListener('resize', refreshAll);
  setTimeout(refreshAll, 200);
})();
