(function () {
  var D = DGASeries;
  var page = 1;
  var pageSize = 15;
  var selectedDay = null;
  var WINDOW = 90;

  var preEvents = D.RATES.filter(function (r) { return r.pre; }).reverse();
  var recentRates = D.RATES.slice(-WINDOW);

  function renderKpi() {
    var curRate = D.currentRate();
    var rateEl = document.getElementById('trend-rate-val');
    rateEl.innerHTML = curRate + '<span class="ops-kpi-unit">%/月</span>';
    rateEl.className = 'ops-kpi-value' + (curRate > D.RATE_THRESH ? ' warn' : '');

    document.getElementById('trend-rate-sub').textContent =
      '参考线 ' + D.RATE_THRESH + '%/月 · DL/T 722 §9.3.2 相对产气速率';

    document.getElementById('trend-pre-count').textContent = String(preEvents.length);

    var over90 = recentRates.filter(function (r) { return r.rate > D.RATE_THRESH; }).length;
    document.getElementById('trend-over-count').textContent = String(over90);
    document.getElementById('trend-over-sub').textContent = '近 ' + WINDOW + ' 天采样 · 速率超阈次数';
  }

  function renderRateChart() {
    DGACharts.rateChart('#trend-rate-chart', {
      data: recentRates,
      threshold: D.RATE_THRESH
    });
  }

  function totalPages() {
    return Math.max(1, Math.ceil(preEvents.length / pageSize));
  }

  function renderPreTable() {
    var tbody = document.getElementById('trend-pre-body');
    var label = document.getElementById('trend-pre-count-label');
    var foot = document.getElementById('trend-pre-pagination');
    if (!tbody) return;

    if (label) {
      label.textContent = '共 ' + preEvents.length + ' 条「预」事件';
    }

    if (!preEvents.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="ops-empty-cell">360 天内暂无「预」事件</td></tr>';
      if (foot) foot.innerHTML = '';
      document.getElementById('trend-detail-panel').hidden = true;
      return;
    }

    var max = totalPages();
    if (page > max) page = max;
    var start = (page - 1) * pageSize;
    var slice = preEvents.slice(start, start + pageSize);

    tbody.innerHTML = slice.map(function (r) {
      var d = D.SERIES[r.day - 1];
      var lv = D.LEVELS[r.day - 1];
      var sel = selectedDay === r.day ? ' selected' : '';
      return (
        '<tr class="ops-pre-row' + sel + '" data-day="' + r.day + '">' +
          '<td class="num muted">' + r.day + '</td>' +
          '<td class="num">' + r.date + '</td>' +
          '<td class="num">' + d.th + '</td>' +
          '<td class="num">' + d.c2h2 + '</td>' +
          '<td class="num warn">' + r.rate + '%/月</td>' +
          '<td><span class="level-badge ' + lv + '">' + D.LEVEL_LABELS[lv] + '</span></td>' +
          '<td>含量未达注意值 2 · 产气速率超 ' + D.RATE_THRESH + '% 阈</td>' +
        '</tr>'
      );
    }).join('');

    if (foot) {
      foot.innerHTML =
        '<div class="ops-pagination-meta">' +
          '<span class="ops-panel-ref">第 ' + (start + 1) + '–' + Math.min(start + pageSize, preEvents.length) +
          ' 条 · 第 ' + page + ' / ' + max + ' 页</span>' +
        '</div>' +
        '<div class="ops-pagination-nav">' +
          '<button type="button" class="ops-page-btn" data-trend-page="prev"' + (page <= 1 ? ' disabled' : '') + '>上一页</button>' +
          '<button type="button" class="ops-page-btn" data-trend-page="next"' + (page >= max ? ' disabled' : '') + '>下一页</button>' +
        '</div>';
    }
  }

  function renderRateCalc(day) {
    var panel = document.getElementById('trend-detail-panel');
    var el = document.getElementById('trend-rate-calc');
    if (!panel || !el) return;

    var idx = day - 1;
    if (idx < 1) {
      panel.hidden = true;
      return;
    }

    var prev = D.SERIES[idx - 1];
    var cur = D.SERIES[idx];
    var rateRow = D.RATES[idx - 1];
    if (!rateRow) {
      panel.hidden = true;
      return;
    }

    panel.hidden = false;
    el.innerHTML =
      '<div class="ops-rate-calc-grid">' +
        '<div><span class="lbl">前次总烃 C₁</span><span class="val num">' + prev.th + ' μL/L</span><span class="sub">' + prev.date + '</span></div>' +
        '<div><span class="lbl">后次总烃 C₂</span><span class="val num">' + cur.th + ' μL/L</span><span class="sub">' + cur.date + '</span></div>' +
        '<div><span class="lbl">相对产气速率 γᵣ</span><span class="val num warn">' + rateRow.rate + '%/月</span><span class="sub">(C₂−C₁)/C₁ × 1/Δt · Δt≈7天折月</span></div>' +
        '<div><span class="lbl">当时档位</span><span class="val"><span class="level-badge ' + D.LEVELS[idx] + '">' + D.LEVEL_LABELS[D.LEVELS[idx]] + '</span></span><span class="sub">' + (rateRow.pre ? '触发「预」' : '未触发「预」') + '</span></div>' +
      '</div>';
  }

  function init() {
    renderKpi();
    renderRateChart();
    renderPreTable();

    var tbody = document.getElementById('trend-pre-body');
    if (tbody) {
      tbody.addEventListener('click', function (e) {
        var row = e.target.closest('.ops-pre-row');
        if (!row) return;
        selectedDay = parseInt(row.dataset.day, 10);
        renderPreTable();
        renderRateCalc(selectedDay);
      });
    }

    var foot = document.getElementById('trend-pre-pagination');
    if (foot) {
      foot.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-trend-page]');
        if (!btn || btn.disabled) return;
        if (btn.dataset.trendPage === 'prev' && page > 1) page -= 1;
        if (btn.dataset.trendPage === 'next' && page < totalPages()) page += 1;
        renderPreTable();
      });
    }

    if (preEvents.length) {
      selectedDay = preEvents[0].day;
      renderPreTable();
      renderRateCalc(selectedDay);
    }
  }

  init();
  window.addEventListener('resize', renderRateChart);
})();
