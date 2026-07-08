/**
 * 公共脚本：导航高亮、Tab 切换、图表渲染
 */
(function () {
  var page = document.body.dataset.page;
  if (page) {
    document.querySelectorAll('.nav-item[data-page]').forEach(function (el) {
      if (el.dataset.page === page) el.classList.add('active');
    });
  }

  // Tab 切换
  document.querySelectorAll('.tabs').forEach(function (tabGroup) {
    var btns = tabGroup.querySelectorAll('.tab-btn');
    var panels = tabGroup.parentElement.querySelectorAll('.tab-panel');
    btns.forEach(function (btn, i) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) { b.classList.remove('active'); });
        panels.forEach(function (p) { p.classList.remove('active'); });
        btn.classList.add('active');
        if (panels[i]) panels[i].classList.add('active');
      });
    });
  });

  // Filter chips
  document.querySelectorAll('.filter-chips').forEach(function (wrap) {
    wrap.querySelectorAll('.chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        wrap.querySelectorAll('.chip').forEach(function (c) { c.classList.remove('active'); });
        chip.classList.add('active');
        var filter = chip.dataset.filter;
        document.querySelectorAll('[data-level]').forEach(function (row) {
          if (filter === 'all' || row.dataset.level === filter) {
            row.style.display = '';
          } else {
            row.style.display = 'none';
          }
        });
      });
    });
  });
})();
