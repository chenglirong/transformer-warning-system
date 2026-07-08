/**
 * Agent 编排页：纵向流程动画 + 报告弹框
 */
(function () {
  var STEPS = [
    { label: '时序输入', tag: 'detect', log: '加载虚拟设备 #SYN-001 · 第287采样日 DGA 数据' },
    { label: '四档分级', tag: 'detect', log: '表A.3 分级 → 注意值2 · C₂H₂ 6.2≥5.0 · 总烃 168.5≥150' },
    { label: '处置紧急度', tag: 'detect', log: '产气速率研判 → 相对速率 11.2%/月 超阈 · 紧急度：偏高' },
    { label: '故障类型', tag: 'diag', log: '三比值 102 → T3高温过热 · Duval T3 · 特征气体一致 · 可信度高' },
    { label: '产气趋势', tag: 'trend', log: '近30天 C₂H₂ 持续上升 · 10-08 触发「预」预警(35%/周)' },
    { label: 'Agent 决策', tag: 'agent', log: 'Agent C → 检测周期缩短至每周 · 暂不建议二次采样 · 附录D试验建议' },
    { label: '表 G.1 报告', tag: 'report', log: '生成 DL/T 722 表G.1 档案卡片 · 分析意见已写入 · RPT-2025-287' }
  ];

  var stepEls = document.querySelectorAll('.agent-v-step');
  var lineEls = document.querySelectorAll('.agent-v-line');
  var logEl = document.getElementById('agent-log');
  var progressFill = document.getElementById('agent-progress-fill');
  var progressText = document.getElementById('agent-progress-text');
  var g1Preview = document.getElementById('g1-preview');
  var decisionLock = document.getElementById('agent-decision-lock');
  var runBtn = document.getElementById('agent-run-btn');
  var openReportBtns = [
    document.getElementById('open-report-btn'),
    document.getElementById('open-report-btn-inline')
  ];
  var modal = document.getElementById('report-modal');
  var modalClose = document.getElementById('report-modal-close');
  var modalCancel = document.getElementById('report-modal-cancel');
  var modalBackdrop = document.getElementById('report-modal-backdrop');
  var running = false;
  var currentIdx = -1;
  var reportReady = false;

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function appendLog(step) {
    if (!logEl) return;
    var now = new Date();
    var ts = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
    var line = document.createElement('div');
    line.className = 'agent-log-line';
    line.innerHTML =
      '<span class="ts">' + ts + '</span>' +
      '<span class="tag ' + step.tag + '">' + step.label + '</span>' +
      '<span class="msg">' + step.log + '</span>';
    logEl.appendChild(line);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setStepState(idx, state) {
    if (!stepEls[idx]) return;
    stepEls[idx].classList.remove('pending', 'active', 'done');
    stepEls[idx].classList.add(state);
  }

  function setReportButtons(enabled) {
    openReportBtns.forEach(function (btn) {
      if (btn) btn.disabled = !enabled;
    });
  }

  function unlockOutput() {
    reportReady = true;
    if (g1Preview) {
      g1Preview.classList.remove('locked');
      g1Preview.classList.add('unlocked');
    }
    if (decisionLock) decisionLock.classList.add('hidden');
    setReportButtons(true);
  }

  function resetPipeline() {
    currentIdx = -1;
    reportReady = false;
    stepEls.forEach(function (el, i) {
      el.classList.remove('active', 'done');
      el.classList.add('pending');
    });
    lineEls.forEach(function (l) { l.classList.remove('flowing'); });
    if (logEl) logEl.innerHTML = '';
    if (progressFill) progressFill.style.width = '0%';
    if (progressText) progressText.textContent = '就绪';
    if (g1Preview) {
      g1Preview.classList.remove('unlocked');
      g1Preview.classList.add('locked');
    }
    if (decisionLock) decisionLock.classList.remove('hidden');
    setReportButtons(false);
    closeModal();
  }

  function advanceStep() {
    if (currentIdx >= 0) {
      setStepState(currentIdx, 'done');
      if (lineEls[currentIdx]) lineEls[currentIdx].classList.add('flowing');
    }
    currentIdx++;
    if (currentIdx >= STEPS.length) {
      running = false;
      if (runBtn) {
        runBtn.textContent = '重新运行';
        runBtn.disabled = false;
      }
      if (progressText) progressText.textContent = '流程完成 · 报告已生成';
      if (progressFill) progressFill.style.width = '100%';
      unlockOutput();
      return;
    }
    setStepState(currentIdx, 'active');
    appendLog(STEPS[currentIdx]);
    var pct = Math.round(((currentIdx + 1) / STEPS.length) * 100);
    if (progressFill) progressFill.style.width = pct + '%';
    if (progressText) progressText.textContent = '步骤 ' + (currentIdx + 1) + '/' + STEPS.length + ' · ' + STEPS[currentIdx].label;
    setTimeout(advanceStep, currentIdx === STEPS.length - 1 ? 1200 : 900);
  }

  function runPipeline() {
    if (running) return;
    running = true;
    if (runBtn) {
      runBtn.textContent = '运行中…';
      runBtn.disabled = true;
    }
    resetPipeline();
    setTimeout(advanceStep, 400);
  }

  function openModal() {
    if (!reportReady || !modal) return;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  if (runBtn) runBtn.addEventListener('click', runPipeline);

  openReportBtns.forEach(function (btn) {
    if (btn) btn.addEventListener('click', openModal);
  });

  if (modalClose) modalClose.addEventListener('click', closeModal);
  if (modalCancel) modalCancel.addEventListener('click', closeModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', closeModal);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  setTimeout(runPipeline, 800);
})();
