(function () {
  var D = DGASeries;
  var day = D.CURRENT_DAY;
  var rateByDay = {};

  D.RATES.forEach(function (r) {
    rateByDay[r.day] = r;
  });

  var A3_ROWS = [
    {
      key: 'c2h2', label: 'C₂H₂', gas: 'c2h2',
      normal: '<1.0', w1: '≥1.0', w2: '≥5.0', alarm: '≥8'
    },
    {
      key: 'h2', label: 'H₂', gas: 'h2',
      normal: '<120', w1: '≥120', w2: '≥150', alarm: '—'
    },
    {
      key: 'th', label: '总烃 C₁+C₂', gas: 'th',
      normal: '<120', w1: '≥120', w2: '≥150', alarm: '—'
    }
  ];

  function gradeFacts(d) {
    var items = [];
    A3_ROWS.forEach(function (row) {
      var val = d[row.key];
      var tier = D.gasItemTier(val, row.gas);
      if (tier !== 'normal') {
        items.push(row.label + ' ' + val + ' μL/L → ' + D.LEVEL_LABELS[tier]);
      }
    });
    return items.length ? items.join(' · ') : 'C₂H₂、H₂、总烃均在表 A.3 正常范围内';
  }

  function getRate(dayNum) {
    return rateByDay[dayNum] || null;
  }

  function clampDay(n) {
    return Math.max(1, Math.min(D.SERIES.length, n));
  }

  function setDay(n) {
    day = clampDay(n);
    render();
  }

  function readUrlDay() {
    var m = location.search.match(/[?&]day=(\d+)/);
    if (m) return parseInt(m[1], 10);
    return null;
  }

  var syncingSelect = false;

  function buildDaySelect() {
    var sel = document.getElementById('det-day-select');
    if (!sel) return;

    var html = '';
    var currentMonth = '';
    D.SERIES.forEach(function (d, i) {
      var n = i + 1;
      var month = d.date.slice(0, 7);
      if (month !== currentMonth) {
        if (currentMonth) html += '</optgroup>';
        html += '<optgroup label="' + month + '">';
        currentMonth = month;
      }
      html += '<option value="' + n + '">' + d.date + ' · D' + n + ' · ' + D.LEVEL_LABELS[D.LEVELS[i]] + '</option>';
    });
    html += '</optgroup>';
    sel.innerHTML = html;

    sel.addEventListener('change', function () {
      if (syncingSelect) return;
      setDay(parseInt(sel.value, 10));
    });
  }

  function syncDaySelect() {
    var sel = document.getElementById('det-day-select');
    if (!sel) return;
    syncingSelect = true;
    sel.value = String(day);
    syncingSelect = false;
  }

  function renderDayPicker() {
    syncDaySelect();
    document.getElementById('det-prev').disabled = day <= 1;
    document.getElementById('det-next').disabled = day >= D.SERIES.length;
  }

  function tierCell(tier) {
    return '<span class="level-badge ' + tier + '">' + D.LEVEL_LABELS[tier] + '</span>';
  }

  function hitClass(tier, col) {
    if (col === tier) return ' hit-' + tier;
    return '';
  }

  function urgencyInfo(d, lv, rateRow) {
    var rate = rateRow ? rateRow.rate : 0;
    var overRate = rate > D.RATE_THRESH;

    if (lv === 'w2' || lv === 'alarm') {
      if (overRate) {
        return {
          label: '偏高 · 需关注',
          cls: 'warn',
          title: '超标且涨势偏快',
          text: '表 A.3 已报 ' + D.LEVEL_LABELS[lv] + '（事实不变）。产气速率 ' + rate + '%/月 超 ' + D.RATE_THRESH + '% 阈 → 处置紧急度偏高，Agent 可建议缩短检测周期。'
        };
      }
      return {
        label: '加强监视',
        cls: 'pre',
        title: '超标 · 涨势尚可控',
        text: '档位仍报 ' + D.LEVEL_LABELS[lv] + '。产气速率 ' + rate + '%/月 未超阈 → §9.3.3：可加强监视，暂不按最高紧急度处置。'
      };
    }

    if (rateRow && rateRow.pre) {
      return {
        label: '「预」· 缩短周期',
        cls: 'pre',
        title: '§9.3.3 a · 未达注意值 2 但涨势快',
        text: '含量档位为 ' + D.LEVEL_LABELS[lv] + '，但相对产气速率 ' + rate + '%/月 超阈 → 建议缩短检测周期。完整「预」列表见产气趋势页。'
      };
    }

    if (lv === 'w1' && d.h2 >= 120 && d.c2h2 < 1 && !overRate) {
      return {
        label: '偏低 · H₂ 单项',
        cls: 'ok',
        title: '§9.3.3 d · H₂ 单项偏高且平稳',
        text: 'H₂ 达注意值 1，但 C₂H₂/总烃正常且涨势平稳 → 档位如实报，紧急度解读降低（加强监视即可）。'
      };
    }

    if (lv === 'normal') {
      return {
        label: '常规监视',
        cls: 'ok',
        title: '各气体在表 A.3 范围内',
        text: '未触发注意值 2 以上处置研判。产气速率 ' + (rateRow ? rate + '%/月' : '—') + '。'
      };
    }

    return {
      label: '关注',
      cls: 'pre',
      title: '注意值 1 · 加强监视',
      text: '单项达注意值 1，综合档位 ' + D.LEVEL_LABELS[lv] + '。产气速率 ' + (rateRow ? rate + '%/月' : '—') + '，继续跟踪涨势。'
    };
  }

  function renderA3Table(d) {
    var tbody = document.getElementById('det-a3-body');
    if (!tbody) return;

    tbody.innerHTML = A3_ROWS.map(function (row) {
      var val = d[row.key];
      var tier = D.gasItemTier(val, row.gas);
      return (
        '<tr>' +
          '<td><strong>' + row.label + '</strong></td>' +
          '<td class="num"><strong>' + val + '</strong></td>' +
          '<td class="num' + hitClass(tier, 'normal') + '">' + row.normal + '</td>' +
          '<td class="num' + hitClass(tier, 'w1') + '">' + row.w1 + '</td>' +
          '<td class="num' + hitClass(tier, 'w2') + '">' + row.w2 + '</td>' +
          '<td class="num' + hitClass(tier, 'alarm') + '">' + row.alarm + '</td>' +
          '<td>' + tierCell(tier) + '</td>' +
        '</tr>'
      );
    }).join('');
  }

  function render() {
    var d = D.SERIES[day - 1];
    var lv = D.LEVELS[day - 1];
    var rateRow = getRate(day);
    var u = urgencyInfo(d, lv, rateRow);

    renderDayPicker();

    var badge = document.getElementById('det-level-badge');
    badge.textContent = D.LEVEL_LABELS[lv];
    badge.className = 'level-badge level-lg ' + lv;

    document.getElementById('det-level-hint').textContent = D.LEVEL_HINTS[lv];
    document.getElementById('det-over-items').textContent = gradeFacts(d);

    var urgEl = document.getElementById('det-urgency');
    urgEl.textContent = u.label;
    urgEl.className = 'urgency-val tone-' + u.cls;
    document.getElementById('det-urgency-sub').textContent =
      rateRow ? '产气速率 ' + rateRow.rate + '%/月 · 不改档位' : '无产气速率数据';

    var verdict = document.getElementById('det-verdict');
    if (verdict) verdict.className = 'ops-det-verdict tone-' + (lv === 'normal' ? 'ok' : lv);

    document.getElementById('det-interpret-title').textContent = u.title;
    document.getElementById('det-interpret-text').textContent = u.text;

    var box = document.getElementById('det-interpret');
    box.className = 'ops-urgency-box tone-' + u.cls;

    renderA3Table(d);
  }

  function init() {
    var urlDay = readUrlDay();
    if (urlDay) day = clampDay(urlDay);

    buildDaySelect();

    document.getElementById('det-prev').addEventListener('click', function () {
      setDay(day - 1);
    });
    document.getElementById('det-next').addEventListener('click', function () {
      setDay(day + 1);
    });
    document.getElementById('det-day-latest').addEventListener('click', function () {
      setDay(D.CURRENT_DAY);
    });

    document.addEventListener('keydown', function (e) {
      if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }
      if (e.key === 'ArrowLeft') setDay(day - 1);
      if (e.key === 'ArrowRight') setDay(day + 1);
    });

    render();
  }

  init();
})();
