/**
 * 表 G.1 档案卡片 · 按采样日动态生成（告警记录 / Agent 共用）
 */
var G1Report = (function () {
  var D = typeof DGASeries !== 'undefined' ? DGASeries : null;

  function pad3(n) {
    return n < 10 ? '00' + n : n < 100 ? '0' + n : '' + n;
  }

  function reportId(day) {
    return 'RPT-2025-' + pad3(day);
  }

  function sampleAt(day, offset) {
    if (!D) return null;
    var idx = day - 1 + (offset || 0);
    if (idx < 0 || idx >= D.SERIES.length) return null;
    return D.SERIES[idx];
  }

  function valClass(value, gas) {
    if (!D) return '';
    var tier = D.gasItemTier(value, gas);
    if (tier === 'alarm') return ' over';
    if (tier === 'w2' || tier === 'w1') return ' warn';
    return '';
  }

  function fmtVal(d, field, gas) {
    if (!d) return '<td class="g1-val empty" colspan="2">—</td>';
    return '<td class="g1-val' + valClass(d[field], gas) + '" colspan="2">' + d[field] + '</td>';
  }

  function fmtDate(d) {
    return d ? d.date : '—';
  }

  function thDelta(cur, prev) {
    if (!cur || !prev) return '—';
    var delta = D.round1(cur.th - prev.th);
    return (delta >= 0 ? '+' : '') + delta;
  }

  function daysBetween(a, b) {
    if (!a || !b) return '—';
    return Math.abs(a.day - b.day);
  }

  function buildOpinion(d, lv, rateRow) {
    var levelLabel = D.LEVEL_LABELS[lv];
    var facts = [];
    if (d.c2h2 >= 8) facts.push('C₂H₂ ' + d.c2h2 + ' μL/L（≥8 告警值）');
    else if (d.c2h2 >= 5) facts.push('C₂H₂ ' + d.c2h2 + ' μL/L（≥5 注意值2）');
    else if (d.c2h2 >= 1) facts.push('C₂H₂ ' + d.c2h2 + ' μL/L（≥1 注意值1）');
    if (d.th >= 150) facts.push('总烃 ' + d.th + ' μL/L（≥150 注意值2）');
    else if (d.th >= 120) facts.push('总烃 ' + d.th + ' μL/L（≥120 注意值1）');
    if (d.h2 >= 150) facts.push('H₂ ' + d.h2 + ' μL/L（≥150 注意值2）');
    else if (d.h2 >= 120) facts.push('H₂ ' + d.h2 + ' μL/L（≥120 注意值1）');

    var trend = '';
    if (rateRow) {
      trend = '相对产气速率 ' + rateRow.rate + '%/月';
      if (rateRow.pre) trend += '，触发「预」预警';
      trend += '。';
    } else {
      trend = '产气速率数据不足。';
    }

    var fault = '— 未触发故障类型判断（含量未达注意值2或无增长趋势）';
    var measures = '维持常规 DGA 检测周期。';
    var agent = '当前档位为「' + levelLabel + '」，按表 A.3 监视即可。';

    if (lv === 'w2' || lv === 'alarm') {
      fault = '三比值 102 → T3 高温过热；Duval T3；特征气体法一致，<em>可信度高</em>。';
      measures = '检测周期缩短至每周一次；安排附录 D 推荐试验（绕组直流电阻、铁芯及夹件绝缘电阻）进一步核实。';
      agent = '可信度高，暂不建议二次采样。若 C₂H₂ 继续升高或三方法分歧，按 §5.4.5 建议二次采样。';
    } else if (lv === 'w1') {
      fault = '特征气体法提示关注，三比值法暂不适用（§10.2.4）。';
      measures = '加强监视，关注产气涨势；必要时缩短检测周期。';
      agent = '产气涨势平稳时可维持原周期；见产气趋势页「预」事件。';
    } else if (rateRow && rateRow.pre) {
      fault = '— 未达含量注意值，但产气速率超阈（§9.3.3 a）';
      measures = '缩短检测周期，关注是否升级为注意值。';
      agent = '「预」事件已记录，见产气趋势辅线。';
    }

    var factText = lv === 'normal' && !(rateRow && rateRow.pre)
      ? '各气体在表 A.3 正常范围内。'
      : (facts.length ? facts.join('；') + '。' : D.LEVEL_HINTS[lv]);

    return (
      '<strong>【告警级别】</strong>' + levelLabel + '。' + factText + '<br><br>' +
      '<strong>【趋势】</strong>' + trend + '<br><br>' +
      '<strong>【故障类型】</strong>' + fault + '<br><br>' +
      '<strong>【处置建议】</strong>' + measures +
      '<div class="g1-decision"><strong>监测决策（Agent C）：</strong>' + agent + '</div>'
    );
  }

  function renderSheet(day, rateRow) {
    if (!D) return '';
    var cur = sampleAt(day, 0);
    var prev1 = sampleAt(day, -7);
    var prev2 = sampleAt(day, -14);
    if (!cur) return '';

    var lv = D.LEVELS[day - 1];
    var id = reportId(day);
    var opinion = buildOpinion(cur, lv, rateRow);

    function gasCells(d, field, gas) {
      return fmtVal(d, field, gas) +
        fmtVal(prev1, field, gas) +
        (prev2
          ? '<td class="g1-val' + valClass(prev2[field], gas) + '">' + prev2[field] + '</td>'
          : '<td class="g1-val empty">—</td>') +
        '<td class="g1-val empty">—</td>';
    }

    var gasRows = [
      ['H₂', 'h2', 'h2'],
      ['CH₄', 'ch4', 'th'],
      ['C₂H₄', 'c2h4', 'th'],
      ['C₂H₆', 'c2h6', 'th'],
      ['C₂H₂', 'c2h2', 'c2h2']
    ];

    var gasHtml = gasRows.map(function (g, i) {
      var row = '<tr>';
      if (i === 0) {
        row += '<td class="g1-section" rowspan="5">组分含量<br>μL/L</td>';
      }
      row += '<td class="g1-sub">' + g[0] + '</td>' + gasCells(cur, g[1], g[2]) + '</tr>';
      return row;
    }).join('');

    return (
      '<div class="g1-sheet">' +
        '<div class="g1-title">表 G.1 油中溶解气体分析档案卡片</div>' +
        '<div class="g1-meta">' +
          '<div class="g1-meta-left"><span class="g1-meta-line"></span>局（厂、所）：</div>' +
          '<div class="g1-meta-right">编号：<span class="g1-meta-no">' + id + '</span></div>' +
        '</div>' +
        '<table class="g1-table">' +
          '<tr>' +
            '<td class="g1-lbl">型号</td><td class="g1-val empty">—</td>' +
            '<td class="g1-lbl">电压等级/容量</td><td class="g1-val">220kV 及以下</td>' +
            '<td class="g1-lbl">油重, t</td><td class="g1-val empty">—</td>' +
            '<td class="g1-lbl">油种</td><td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-lbl">制造厂</td><td class="g1-val empty">—</td>' +
            '<td class="g1-lbl">出厂序号</td><td class="g1-val">SYN-001</td>' +
            '<td class="g1-lbl">出厂年月</td><td class="g1-val empty">—</td>' +
            '<td class="g1-lbl">投运日期</td><td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-section" rowspan="2">取样条件</td>' +
            '<td class="g1-sub">年、月、日、时</td>' +
            '<td class="g1-val" colspan="2">' + fmtDate(cur) + ' 08:00</td>' +
            '<td class="g1-val" colspan="2">' + fmtDate(prev1) + '</td>' +
            '<td class="g1-val">' + fmtDate(prev2) + '</td>' +
            '<td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr><td class="g1-sub">取样原因</td><td class="g1-val empty" colspan="6">在线监测例行采样 · D' + day + '</td></tr>' +
          gasHtml +
          '<tr>' +
            '<td class="g1-sub" colspan="2">C₁+C₂（总烃）</td>' +
            fmtVal(cur, 'th', 'th') +
            fmtVal(prev1, 'th', 'th') +
            (prev2 ? '<td class="g1-val' + valClass(prev2.th, 'th') + '">' + prev2.th + '</td>' : '<td class="g1-val empty">—</td>') +
            '<td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-sub" colspan="2">总烃增长, μL/L</td>' +
            '<td class="g1-val" colspan="2">' + thDelta(cur, prev1) + '</td>' +
            '<td class="g1-val" colspan="2">' + thDelta(prev1, prev2) + '</td>' +
            '<td class="g1-val empty">—</td><td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-sub" colspan="2">实际运行时间, 天</td>' +
            '<td class="g1-val" colspan="2">' + daysBetween(cur, prev1) + '</td>' +
            '<td class="g1-val" colspan="2">' + daysBetween(prev1, prev2) + '</td>' +
            '<td class="g1-val empty">—</td><td class="g1-val empty">—</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-sub" colspan="2">试验报告编号</td>' +
            '<td class="g1-val" colspan="6">' + id + '</td>' +
          '</tr>' +
          '<tr>' +
            '<td class="g1-sub" colspan="2">分析意见</td>' +
            '<td class="g1-opinion" colspan="6">' + opinion + '</td>' +
          '</tr>' +
        '</table>' +
      '</div>'
    );
  }

  return {
    reportId: reportId,
    buildOpinion: buildOpinion,
    renderSheet: renderSheet
  };
})();
