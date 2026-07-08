/**
 * 合成 360 天时序 · 各页共享
 */
var DGASeries = (function () {
  var SERIES = [];
  var LEVELS = [];
  var RATES = [];
  var CURRENT_DAY = 287;

  var LEVEL_LABELS = { normal: '正常', w1: '注意值 1', w2: '注意值 2', alarm: '告警值' };
  var LEVEL_HINTS = {
    normal: '各气体在表 A.3 正常范围内',
    w1: '单项达注意值 1，需关注',
    w2: '可能存在隐患，需加强监视（A.1）',
    alarm: '可能存在缺陷，需采取措施（A.1）'
  };
  var LEVEL_COLORS = { normal: '#34d399', w1: '#fbbf24', w2: '#fb923c', alarm: '#f87171' };
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

  function gasItemTier(value, gas) {
    return gasTier(value, gas);
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
        day: i + 1,
        date: '2025-' + padDate(i),
        label: 'D' + (i + 1),
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

  function padDate(i) {
    var m = Math.floor(i / 30) + 1;
    var d = (i % 30) + 1;
    return (m < 10 ? '0' : '') + m + '-' + (d < 10 ? '0' : '') + d;
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
        day: i + 1,
        label: 'D' + (i + 1),
        date: cur.date,
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

  function current() {
    return SERIES[CURRENT_DAY - 1];
  }

  function currentLevel() {
    return LEVELS[CURRENT_DAY - 1];
  }

  function currentRate() {
    return RATES.length ? RATES[RATES.length - 1].rate : 0;
  }

  function countPreWarnings() {
    return RATES.filter(function (r) { return r.pre; }).length;
  }

  function init() {
    SERIES = buildSeries();
    LEVELS = SERIES.map(classifyDay);
    RATES = buildRates();
  }

  init();

  return {
    SERIES: SERIES,
    LEVELS: LEVELS,
    RATES: RATES,
    CURRENT_DAY: CURRENT_DAY,
    LEVEL_LABELS: LEVEL_LABELS,
    LEVEL_HINTS: LEVEL_HINTS,
    LEVEL_COLORS: LEVEL_COLORS,
    TH_W2: TH_W2,
    C2H2_W2: C2H2_W2,
    RATE_THRESH: RATE_THRESH,
    round1: round1,
    pct: pct,
    tierRank: tierRank,
    gasItemTier: gasItemTier,
    classifyDay: classifyDay,
    countLevels: countLevels,
    current: current,
    currentLevel: currentLevel,
    currentRate: currentRate,
    countPreWarnings: countPreWarnings
  };
})();
