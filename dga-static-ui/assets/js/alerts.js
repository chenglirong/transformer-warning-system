(function () {
  var D = DGASeries;
  var filter = 'all';
  var page = 1;
  var pageSize = 20;
  var sortBy = 'date-desc';
  var searchText = '';
  var rateByDay = {};

  D.RATES.forEach(function (r) {
    rateByDay[r.day] = r;
  });

  var tierRank = { normal: 0, w1: 1, w2: 2, alarm: 3 };

  function gasFacts(d) {
    var parts = [];
    if (d.c2h2 >= 8) parts.push('C₂H₂ 达告警值');
    else if (d.c2h2 >= 5) parts.push('C₂H₂ 达注意值 2');
    else if (d.c2h2 >= 1) parts.push('C₂H₂ 达注意值 1');
    if (d.th >= 150) parts.push('总烃 达注意值 2');
    else if (d.th >= 120) parts.push('总烃 达注意值 1');
    if (d.h2 >= 150) parts.push('H₂ 达注意值 2');
    else if (d.h2 >= 120) parts.push('H₂ 达注意值 1');
    return parts;
  }

  function summaryText(d, lv, rateRow) {
    if (lv === 'normal') {
      if (rateRow && rateRow.pre) {
        return '各气体在范围内 · 产气速率超阈（预）';
      }
      return '各气体在表 A.3 正常范围内';
    }
    var facts = gasFacts(d);
    var text = facts.length ? facts.join(' · ') : D.LEVEL_HINTS[lv];
    if (rateRow && rateRow.pre) {
      text += ' · 产气速率超阈（预）';
    }
    return text;
  }

  function diagText(lv) {
    if (lv === 'w2' || lv === 'alarm') return 'T3 高温过热';
    return '—';
  }

  function rateCell(rateRow) {
    if (!rateRow) return '<span class="muted">—</span>';
    var cls = rateRow.pre ? ' warn' : '';
    var tag = rateRow.pre ? ' <span class="ops-pre-tag">预</span>' : '';
    return '<span class="num' + cls + '">' + rateRow.rate + '%</span>' + tag;
  }

  function gasCell(value, gas) {
    var tier = D.gasItemTier(value, gas);
    var cls = tier === 'alarm' ? ' over' : tier === 'w2' || tier === 'w1' ? ' warn' : '';
    return '<span class="num' + cls + '">' + value + '</span>';
  }

  function matchesSearch(row) {
    if (!searchText) return true;
    var q = searchText.toLowerCase();
    return (
      row.date.indexOf(q) >= 0 ||
      row.summary.toLowerCase().indexOf(q) >= 0 ||
      row.reportId.toLowerCase().indexOf(q) >= 0 ||
      String(row.day).indexOf(q) >= 0 ||
      D.LEVEL_LABELS[row.level].indexOf(q) >= 0
    );
  }

  function buildRows() {
    var rows = [];
    for (var i = 0; i < D.SERIES.length; i++) {
      var d = D.SERIES[i];
      var lv = D.LEVELS[i];
      var rateRow = rateByDay[d.day];

      if (filter === 'non-normal' && lv === 'normal' && !(rateRow && rateRow.pre)) {
        continue;
      }
      if (filter !== 'all' && filter !== 'non-normal' && lv !== filter) {
        continue;
      }

      var row = {
        day: d.day,
        date: d.date,
        level: lv,
        summary: summaryText(d, lv, rateRow),
        reportId: G1Report.reportId(d.day),
        c2h2: d.c2h2,
        th: d.th,
        h2: d.h2,
        rateHtml: rateCell(rateRow),
        diag: diagText(lv)
      };

      if (matchesSearch(row)) {
        rows.push(row);
      }
    }

    rows.sort(function (a, b) {
      if (sortBy === 'date-asc') return a.day - b.day;
      if (sortBy === 'level-desc') {
        var diff = tierRank[b.level] - tierRank[a.level];
        return diff !== 0 ? diff : b.day - a.day;
      }
      return b.day - a.day;
    });

    return rows;
  }

  function totalPages(total) {
    return Math.max(1, Math.ceil(total / pageSize));
  }

  function clampPage(total) {
    var max = totalPages(total);
    if (page > max) page = max;
    if (page < 1) page = 1;
  }

  function renderKpi() {
    var el = document.getElementById('alert-kpi-row');
    if (!el) return;
    var c = D.countLevels();
    var pre = D.countPreWarnings();
    el.innerHTML =
      '<div class="ops-kpi-card"><div class="ops-kpi-label">流水条数</div><div class="ops-kpi-value">' +
      D.SERIES.length + '</div><div class="ops-kpi-sub">四档全报 · 含正常</div></div>' +
      '<div class="ops-kpi-card"><div class="ops-kpi-label">注意值 1</div><div class="ops-kpi-value w1">' +
      c.w1 + '</div><div class="ops-kpi-sub">天</div></div>' +
      '<div class="ops-kpi-card"><div class="ops-kpi-label">注意值 2</div><div class="ops-kpi-value w2">' +
      c.w2 + '</div><div class="ops-kpi-sub">天</div></div>' +
      '<div class="ops-kpi-card"><div class="ops-kpi-label">告警值</div><div class="ops-kpi-value alarm">' +
      c.alarm + '</div><div class="ops-kpi-sub">「预」' + pre + ' 次 · 见产气趋势</div></div>';
  }

  function pageNumbers(current, max) {
    if (max <= 7) {
      var all = [];
      for (var i = 1; i <= max; i++) all.push(i);
      return all;
    }
    var pages = [1];
    var start = Math.max(2, current - 1);
    var end = Math.min(max - 1, current + 1);
    if (start > 2) pages.push('…');
    for (var p = start; p <= end; p++) pages.push(p);
    if (end < max - 1) pages.push('…');
    pages.push(max);
    return pages;
  }

  function renderPagination(total) {
    var nav = document.getElementById('alert-pagination-nav');
    if (!nav) return;

    var max = totalPages(total);
    var nums = pageNumbers(page, max);
    var html = '<button type="button" class="ops-page-btn" data-action="prev"' +
      (page <= 1 ? ' disabled' : '') + '>上一页</button>';

    nums.forEach(function (n) {
      if (n === '…') {
        html += '<span class="ops-page-ellipsis">…</span>';
        return;
      }
      html += '<button type="button" class="ops-page-btn' + (n === page ? ' active' : '') +
        '" data-page="' + n + '">' + n + '</button>';
    });

    html += '<button type="button" class="ops-page-btn" data-action="next"' +
      (page >= max ? ' disabled' : '') + '>下一页</button>';

    nav.innerHTML = html;
  }

  function renderTableRow(row) {
    return (
      '<tr class="lv-' + row.level + '">' +
        '<td class="num muted">' + row.day + '</td>' +
        '<td class="num">' + row.date + '</td>' +
        '<td><span class="level-badge ' + row.level + '">' + D.LEVEL_LABELS[row.level] + '</span></td>' +
        '<td class="col-summary">' + row.summary + '</td>' +
        '<td>' + gasCell(row.c2h2, 'c2h2') + '</td>' +
        '<td>' + gasCell(row.th, 'th') + '</td>' +
        '<td>' + gasCell(row.h2, 'h2') + '</td>' +
        '<td>' + row.rateHtml + '</td>' +
        '<td class="col-diag">' + row.diag + '</td>' +
        '<td class="col-actions">' +
          '<button type="button" class="ops-act-btn" data-action="report" data-day="' + row.day + '">查看报告</button>' +
        '</td>' +
      '</tr>'
    );
  }

  function renderTable() {
    var tbody = document.getElementById('alert-table-body');
    var countEl = document.getElementById('alert-count');
    var rangeEl = document.getElementById('alert-range');
    if (!tbody) return;

    var rows = buildRows();
    clampPage(rows.length);
    var max = totalPages(rows.length);
    var start = (page - 1) * pageSize;
    var end = Math.min(start + pageSize, rows.length);
    var pageRows = rows.slice(start, end);

    if (countEl) {
      countEl.textContent = '共 ' + rows.length + ' 条' + (searchText ? ' · 已筛选' : '');
    }
    if (rangeEl) {
      rangeEl.textContent = rows.length
        ? '第 ' + (start + 1) + '–' + end + ' 条 · 第 ' + page + ' / ' + max + ' 页'
        : '无匹配记录';
    }

    tbody.innerHTML = pageRows.map(renderTableRow).join('');
    renderPagination(rows.length);

    var wrap = document.querySelector('.ops-alert-table-wrap');
    if (wrap) wrap.scrollTop = 0;
  }

  function openReport(day) {
    var modal = document.getElementById('alert-report-modal');
    var body = document.getElementById('alert-report-body');
    var meta = document.getElementById('alert-report-meta');
    if (!modal || !body) return;

    var rateRow = rateByDay[day];
    var id = G1Report.reportId(day);
    var d = D.SERIES[day - 1];

    body.innerHTML = G1Report.renderSheet(day, rateRow);
    if (meta) {
      meta.textContent = id + ' · ' + (d ? d.date : '') + ' · DL/T 722 附录 G 表 G.1 · Agent 生成';
    }

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeReport() {
    var modal = document.getElementById('alert-report-modal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function init() {
    renderKpi();
    renderTable();

    ['alert-report-close', 'alert-report-cancel', 'alert-report-backdrop'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('click', closeReport);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeReport();
    });

    var tbody = document.getElementById('alert-table-body');
    if (tbody) {
      tbody.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-action="report"]');
        if (!btn) return;
        openReport(parseInt(btn.dataset.day, 10));
      });
    }

    document.querySelectorAll('.ops-chip[data-filter]').forEach(function (chip) {
      chip.addEventListener('click', function () {
        document.querySelectorAll('.ops-chip[data-filter]').forEach(function (c) {
          c.classList.remove('active');
        });
        chip.classList.add('active');
        filter = chip.dataset.filter;
        page = 1;
        renderTable();
      });
    });

    var sizeSelect = document.getElementById('alert-page-size');
    if (sizeSelect) {
      sizeSelect.addEventListener('change', function () {
        pageSize = parseInt(sizeSelect.value, 10) || 20;
        page = 1;
        renderTable();
      });
    }

    var sortSelect = document.getElementById('alert-sort');
    if (sortSelect) {
      sortSelect.addEventListener('change', function () {
        sortBy = sortSelect.value;
        page = 1;
        renderTable();
      });
    }

    var searchInput = document.getElementById('alert-search');
    if (searchInput) {
      var searchTimer;
      searchInput.addEventListener('input', function () {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function () {
          searchText = searchInput.value.trim();
          page = 1;
          renderTable();
        }, 200);
      });
    }

    var nav = document.getElementById('alert-pagination-nav');
    if (nav) {
      nav.addEventListener('click', function (e) {
        var btn = e.target.closest('.ops-page-btn');
        if (!btn || btn.disabled) return;

        var rows = buildRows();
        var max = totalPages(rows.length);

        if (btn.dataset.page) {
          page = parseInt(btn.dataset.page, 10);
        } else if (btn.dataset.action === 'prev' && page > 1) {
          page -= 1;
        } else if (btn.dataset.action === 'next' && page < max) {
          page += 1;
        }

        renderTable();
      });
    }
  }

  init();
})();
