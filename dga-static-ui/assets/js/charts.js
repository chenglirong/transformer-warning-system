/**
 * 轻量 SVG 图表（无第三方依赖）
 */
var DGACharts = {
  lineChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var data = options.data || [];
    var lines = options.lines || [{ key: 'value', color: '#3dbfb0', label: '数值' }];
    var thresholds = options.thresholds || [];
    var w = el.clientWidth || 600;
    var h = el.clientHeight || 220;
    var pad = { t: 16, r: 16, b: 32, l: 48 };
    var plotW = w - pad.l - pad.r;
    var plotH = h - pad.t - pad.b;

    var allVals = [];
    data.forEach(function (d) {
      lines.forEach(function (ln) {
        if (d[ln.key] != null) allVals.push(d[ln.key]);
      });
    });
    thresholds.forEach(function (t) { allVals.push(t.value); });
    var minV = Math.min.apply(null, allVals) * 0.9;
    var maxV = Math.max.apply(null, allVals) * 1.1;
    if (minV === maxV) { minV -= 1; maxV += 1; }

    function x(i) { return pad.l + (i / (data.length - 1 || 1)) * plotW; }
    function y(v) { return pad.t + plotH - ((v - minV) / (maxV - minV)) * plotH; }

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';

    // Grid
    for (var g = 0; g <= 4; g++) {
      var gy = pad.t + (plotH / 4) * g;
      var gv = maxV - ((maxV - minV) / 4) * g;
      svg += '<line x1="' + pad.l + '" y1="' + gy + '" x2="' + (w - pad.r) + '" y2="' + gy + '" stroke="rgba(148,163,184,0.1)" stroke-width="1"/>';
      svg += '<text x="' + (pad.l - 8) + '" y="' + (gy + 4) + '" fill="#64748b" font-size="10" text-anchor="end" font-family="DM Mono,monospace">' + gv.toFixed(0) + '</text>';
    }

    // Thresholds
    thresholds.forEach(function (t) {
      var ty = y(t.value);
      svg += '<line x1="' + pad.l + '" y1="' + ty + '" x2="' + (w - pad.r) + '" y2="' + ty + '" stroke="' + (t.color || '#fb923c') + '" stroke-width="1" stroke-dasharray="4,4" opacity="0.7"/>';
      svg += '<text x="' + (w - pad.r + 4) + '" y="' + (ty + 3) + '" fill="' + (t.color || '#fb923c') + '" font-size="9" font-family="Noto Sans SC,sans-serif">' + t.label + '</text>';
    });

    // Lines
    lines.forEach(function (ln) {
      var pts = [];
      data.forEach(function (d, i) {
        if (d[ln.key] != null) pts.push(x(i) + ',' + y(d[ln.key]));
      });
      if (pts.length > 1) {
        svg += '<polyline fill="none" stroke="' + ln.color + '" stroke-width="2" points="' + pts.join(' ') + '"/>';
      }
      // Pre-warning markers
      if (ln.markers) {
        ln.markers.forEach(function (m) {
          var idx = data.findIndex(function (d) { return d.date === m.date; });
          if (idx >= 0 && data[idx][ln.key] != null) {
            svg += '<circle cx="' + x(idx) + '" cy="' + y(data[idx][ln.key]) + '" r="5" fill="' + (m.color || '#fbbf24') + '" stroke="#111820" stroke-width="2"/>';
          }
        });
      }
    });

    // X labels (sparse)
    var step = Math.ceil(data.length / 6);
    data.forEach(function (d, i) {
      if (i % step === 0 || i === data.length - 1) {
        svg += '<text x="' + x(i) + '" y="' + (h - 8) + '" fill="#64748b" font-size="9" text-anchor="middle" font-family="DM Mono,monospace">' + (d.date || i) + '</text>';
      }
    });

    svg += '</svg>';
    el.innerHTML = svg;
  },

  duvalTriangle: function (container, point) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var zones = [
      { id: 'PD', color: '#5b9fd4', path: 'M200,30 L360,280 L40,280 Z', label: 'PD 局放' },
      { id: 'D1', color: '#a78bfa', path: 'M200,30 L280,170 L120,170 Z', label: 'D1 低能放电' },
      { id: 'D2', color: '#f472b6', path: 'M200,30 L240,120 L160,120 Z', label: 'D2 高能放电' },
      { id: 'T1', color: '#34d399', path: 'M40,280 L200,280 L120,170 Z', label: 'T1 低温过热' },
      { id: 'T2', color: '#fbbf24', path: 'M360,280 L200,280 L280,170 Z', label: 'T2 中温过热' },
      { id: 'T3', color: '#fb923c', path: 'M120,170 L280,170 L200,30 Z', label: 'T3 高温过热' }
    ];
    var active = point.zone || 'T3';
    var px = point.x || 18;
    var py = point.y || 52;

    var svg = '<svg viewBox="0 0 400 320" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">';
    zones.forEach(function (z) {
      var op = z.id === active ? 0.65 : 0.22;
      svg += '<path d="' + z.path + '" fill="' + z.color + '" opacity="' + op + '" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"/>';
    });
    svg += '<text x="200" y="18" fill="#94a3b8" font-size="11" text-anchor="middle">%C₂H₂</text>';
    svg += '<text x="12" y="300" fill="#94a3b8" font-size="11">%CH₄</text>';
    svg += '<text x="370" y="300" fill="#94a3b8" font-size="11" text-anchor="end">%C₂H₄</text>';
    var cx = 200 + (px - 33) * 1.2;
    var cy = 200 - (py - 33) * 0.8;
    svg += '<circle cx="' + cx + '" cy="' + cy + '" r="9" fill="#d4a054" stroke="#fff" stroke-width="2.5"/>';
    svg += '<circle cx="' + cx + '" cy="' + cy + '" r="14" fill="#d4a054" opacity="0.25"/>';
    svg += '<text x="' + (cx + 16) + '" y="' + (cy + 5) + '" fill="#e8c078" font-size="12" font-weight="700">' + active + '</text>';
    svg += '</svg>';
    el.innerHTML = svg;
  },

  miniSparkline: function (container, values, color) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el || !values.length) return;
    var w = el.clientWidth || 120;
    var h = 36;
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var pts = values.map(function (v, i) {
      var x = (i / (values.length - 1)) * w;
      var y = h - ((v - min) / (max - min || 1)) * (h - 4) - 2;
      return x + ',' + y;
    }).join(' ');
    el.innerHTML = '<svg width="' + w + '" height="' + h + '"><polyline fill="none" stroke="' + (color || '#3dbfb0') + '" stroke-width="1.5" points="' + pts + '"/></svg>';
  },

  areaLineChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var data = options.data || [];
    var lines = options.lines || [{ key: 'value', color: '#3dbfb0', label: '数值' }];
    var thresholds = options.thresholds || [];
    var w = el.clientWidth || 600;
    var h = el.clientHeight || 280;
    var pad = { t: 20, r: 20, b: 36, l: 52 };
    var plotW = w - pad.l - pad.r;
    var plotH = h - pad.t - pad.b;

    var allVals = [];
    data.forEach(function (d) {
      lines.forEach(function (ln) {
        if (d[ln.key] != null) allVals.push(d[ln.key]);
      });
    });
    thresholds.forEach(function (t) { allVals.push(t.value); });
    var minV = Math.min.apply(null, allVals) * 0.9;
    var maxV = Math.max.apply(null, allVals) * 1.08;
    if (minV === maxV) { minV -= 1; maxV += 1; }

    function x(i) { return pad.l + (i / (data.length - 1 || 1)) * plotW; }
    function y(v) { return pad.t + plotH - ((v - minV) / (maxV - minV)) * plotH; }

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';

    svg += '<defs><linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="rgba(61,191,176,0.25)"/><stop offset="100%" stop-color="rgba(61,191,176,0)"/></linearGradient></defs>';

    for (var g = 0; g <= 4; g++) {
      var gy = pad.t + (plotH / 4) * g;
      var gv = maxV - ((maxV - minV) / 4) * g;
      svg += '<line x1="' + pad.l + '" y1="' + gy + '" x2="' + (w - pad.r) + '" y2="' + gy + '" stroke="rgba(148,163,184,0.08)" stroke-width="1"/>';
      svg += '<text x="' + (pad.l - 8) + '" y="' + (gy + 4) + '" fill="#64748b" font-size="10" text-anchor="end" font-family="DM Mono,monospace">' + gv.toFixed(0) + '</text>';
    }

    thresholds.forEach(function (t) {
      var ty = y(t.value);
      svg += '<line x1="' + pad.l + '" y1="' + ty + '" x2="' + (w - pad.r) + '" y2="' + ty + '" stroke="' + (t.color || '#fb923c') + '" stroke-width="1" stroke-dasharray="6,4" opacity="0.65"/>';
      svg += '<text x="' + (w - pad.r + 4) + '" y="' + (ty + 3) + '" fill="' + (t.color || '#fb923c') + '" font-size="9" font-family="Noto Sans SC,sans-serif">' + t.label + '</text>';
    });

    lines.forEach(function (ln, li) {
      var pts = [];
      data.forEach(function (d, i) {
        if (d[ln.key] != null) pts.push({ x: x(i), y: y(d[ln.key]) });
      });
      if (pts.length > 1 && ln.fill && li === 0) {
        var areaPath = 'M' + pts[0].x + ',' + (pad.t + plotH);
        pts.forEach(function (p) { areaPath += ' L' + p.x + ',' + p.y; });
        areaPath += ' L' + pts[pts.length - 1].x + ',' + (pad.t + plotH) + ' Z';
        svg += '<path d="' + areaPath + '" fill="url(#areaGrad)"/>';
      }
      if (pts.length > 1) {
        var linePts = pts.map(function (p) { return p.x + ',' + p.y; }).join(' ');
        svg += '<polyline fill="none" stroke="' + ln.color + '" stroke-width="2" points="' + linePts + '"/>';
        var last = pts[pts.length - 1];
        svg += '<circle cx="' + last.x + '" cy="' + last.y + '" r="4" fill="' + ln.color + '" stroke="#111820" stroke-width="2"/>';
      }
    });

    var step = Math.ceil(data.length / 8);
    data.forEach(function (d, i) {
      if (i % step === 0 || i === data.length - 1) {
        svg += '<text x="' + x(i) + '" y="' + (h - 10) + '" fill="#64748b" font-size="9" text-anchor="middle" font-family="DM Mono,monospace">' + (d.date || i) + '</text>';
      }
    });

    svg += '</svg>';
    el.innerHTML = svg;
  },

  gaugeRing: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var value = options.value || 0;
    var max = options.max || 100;
    var color = options.color || '#3dbfb0';
    var pct = Math.min(value / max, 1);
    var r = 42;
    var circ = 2 * Math.PI * r;
    var arcLen = circ * 0.75;
    var offset = arcLen * (1 - pct);
    el.innerHTML = '<svg viewBox="0 0 100 100" class="gauge-svg">' +
      '<circle cx="50" cy="50" r="' + r + '" fill="none" stroke="rgba(148,163,184,0.12)" stroke-width="8" stroke-linecap="round" transform="rotate(135 50 50)" stroke-dasharray="' + arcLen + ' ' + circ + '"/>' +
      '<circle cx="50" cy="50" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="8" stroke-linecap="round" transform="rotate(135 50 50)" stroke-dasharray="' + arcLen + ' ' + circ + '" stroke-dashoffset="' + offset + '" style="filter:drop-shadow(0 0 6px ' + color + ')"/>' +
      '</svg>';
  },

  horizontalBarChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var items = options.items || [];
    var w = el.clientWidth || 400;
    var rowH = 28;
    var h = items.length * rowH + 16;
    var labelW = 48;
    var padR = 56;
    var barW = w - labelW - padR - 24;

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    items.forEach(function (item, i) {
      var y = 8 + i * rowH;
      var pct = Math.min(item.value / item.max, 1);
      var barLen = pct * barW;
      var threshX = item.threshold ? padR + labelW + (item.threshold / item.max) * barW : 0;

      svg += '<text x="8" y="' + (y + 16) + '" fill="#94a3b8" font-size="11" font-weight="600">' + item.label + '</text>';
      svg += '<rect x="' + (labelW + 8) + '" y="' + (y + 6) + '" width="' + barW + '" height="8" rx="4" fill="rgba(148,163,184,0.1)"/>';
      svg += '<rect x="' + (labelW + 8) + '" y="' + (y + 6) + '" width="' + barLen + '" height="8" rx="4" fill="' + item.color + '" opacity="0.85"/>';
      if (item.threshold) {
        svg += '<line x1="' + threshX + '" y1="' + (y + 4) + '" x2="' + threshX + '" y2="' + (y + 16) + '" stroke="#fb923c" stroke-width="1.5" stroke-dasharray="2,2"/>';
      }
      var valColor = item.status === 'over' ? '#f87171' : (item.status === 'warn' ? '#fb923c' : '#e8edf5');
      svg += '<text x="' + (w - 8) + '" y="' + (y + 16) + '" fill="' + valColor + '" font-size="11" text-anchor="end" font-family="DM Mono,monospace" font-weight="600">' + item.value + '</text>';
    });
    svg += '</svg>';
    el.innerHTML = svg;
  },

  donutChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var segments = options.segments || [];
    var total = segments.reduce(function (s, seg) { return s + seg.value; }, 0) || 1;
    var cx = 80, cy = 80, r = 56, ir = 36;
    var angle = -90;
    var svg = '<svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">';

    segments.forEach(function (seg) {
      var sweep = (seg.value / total) * 360;
      var start = angle;
      var end = angle + sweep;
      angle = end;
      var x1 = cx + r * Math.cos(start * Math.PI / 180);
      var y1 = cy + r * Math.sin(start * Math.PI / 180);
      var x2 = cx + r * Math.cos(end * Math.PI / 180);
      var y2 = cy + r * Math.sin(end * Math.PI / 180);
      var ix1 = cx + ir * Math.cos(end * Math.PI / 180);
      var iy1 = cy + ir * Math.sin(end * Math.PI / 180);
      var ix2 = cx + ir * Math.cos(start * Math.PI / 180);
      var iy2 = cy + ir * Math.sin(start * Math.PI / 180);
      var large = sweep > 180 ? 1 : 0;
      svg += '<path d="M' + x1 + ',' + y1 + ' A' + r + ',' + r + ' 0 ' + large + ' 1 ' + x2 + ',' + y2 +
        ' L' + ix1 + ',' + iy1 + ' A' + ir + ',' + ir + ' 0 ' + large + ' 0 ' + ix2 + ',' + iy2 + ' Z" fill="' + seg.color + '" opacity="0.85"/>';
    });

    svg += '<text x="' + cx + '" y="' + (cy - 4) + '" fill="#e8edf5" font-size="18" font-weight="700" text-anchor="middle" font-family="DM Mono,monospace">' + total + '</text>';
    svg += '<text x="' + cx + '" y="' + (cy + 14) + '" fill="#64748b" font-size="9" text-anchor="middle">采样日</text>';
    svg += '</svg>';
    el.innerHTML = svg;
  },

  /** 发光面积趋势图（大屏主图） */
  glowAreaChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var uid = 'g' + Math.random().toString(36).slice(2, 8);
    var data = options.data || [];
    var lines = options.lines || [];
    var thresholds = options.thresholds || [];
    var markers = options.markers || [];
    var w = el.clientWidth || 600;
    var h = el.clientHeight || 300;
    var pad = { t: 24, r: 24, b: 40, l: 56 };
    var plotW = w - pad.l - pad.r;
    var plotH = h - pad.t - pad.b;

    var allVals = [];
    data.forEach(function (d) {
      lines.forEach(function (ln) {
        if (d[ln.key] != null) allVals.push(d[ln.key]);
      });
    });
    thresholds.forEach(function (t) { allVals.push(t.value); });
    var minV = Math.min.apply(null, allVals) * 0.88;
    var maxV = Math.max.apply(null, allVals) * 1.1;
    if (minV === maxV) { minV -= 1; maxV += 1; }

    function x(i) { return pad.l + (i / (data.length - 1 || 1)) * plotW; }
    function y(v) { return pad.t + plotH - ((v - minV) / (maxV - minV)) * plotH; }

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    svg += '<defs>';
    lines.forEach(function (ln, i) {
      var gid = uid + 'grad' + i;
      svg += '<linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0%" stop-color="' + ln.color + '" stop-opacity="0.35"/>' +
        '<stop offset="100%" stop-color="' + ln.color + '" stop-opacity="0"/>' +
        '</linearGradient>';
      svg += '<filter id="' + uid + 'glow' + i + '"><feGaussianBlur stdDeviation="2.5" result="b"/>' +
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>';
    });
    svg += '</defs>';

    for (var g = 0; g <= 5; g++) {
      var gy = pad.t + (plotH / 5) * g;
      svg += '<line x1="' + pad.l + '" y1="' + gy + '" x2="' + (w - pad.r) + '" y2="' + gy + '" stroke="rgba(148,163,184,0.06)" stroke-width="1"/>';
      if (g % 2 === 0) {
        var gv = maxV - ((maxV - minV) / 5) * g;
        svg += '<text x="' + (pad.l - 10) + '" y="' + (gy + 4) + '" fill="#64748b" font-size="10" text-anchor="end" font-family="DM Mono,monospace">' + gv.toFixed(0) + '</text>';
      }
    }

    thresholds.forEach(function (t) {
      var ty = y(t.value);
      svg += '<line x1="' + pad.l + '" y1="' + ty + '" x2="' + (w - pad.r) + '" y2="' + ty + '" stroke="' + (t.color || '#fb923c') + '" stroke-width="1.5" stroke-dasharray="8,5" opacity="0.7"/>';
      svg += '<rect x="' + (w - pad.r - 72) + '" y="' + (ty - 16) + '" width="72" height="14" rx="3" fill="rgba(251,146,60,0.15)"/>';
      svg += '<text x="' + (w - pad.r - 36) + '" y="' + (ty - 6) + '" fill="' + (t.color || '#fb923c') + '" font-size="9" text-anchor="middle" font-family="Noto Sans SC,sans-serif">' + t.label + '</text>';
    });

    lines.forEach(function (ln, li) {
      var pts = [];
      data.forEach(function (d, i) {
        if (d[ln.key] != null) pts.push({ x: x(i), y: y(d[ln.key]) });
      });
      if (pts.length > 1 && ln.fill !== false) {
        var ap = 'M' + pts[0].x + ',' + (pad.t + plotH);
        pts.forEach(function (p) { ap += ' L' + p.x + ',' + p.y; });
        ap += ' L' + pts[pts.length - 1].x + ',' + (pad.t + plotH) + ' Z';
        svg += '<path d="' + ap + '" fill="url(#' + uid + 'grad' + li + ')"/>';
      }
      if (pts.length > 1) {
        var lp = pts.map(function (p) { return p.x + ',' + p.y; }).join(' ');
        svg += '<polyline fill="none" stroke="' + ln.color + '" stroke-width="2.5" points="' + lp + '" filter="url(#' + uid + 'glow' + li + ')" opacity="0.95"/>';
        var last = pts[pts.length - 1];
        svg += '<circle cx="' + last.x + '" cy="' + last.y + '" r="5" fill="' + ln.color + '" stroke="#0c1117" stroke-width="2"/>';
        svg += '<circle cx="' + last.x + '" cy="' + last.y + '" r="10" fill="' + ln.color + '" opacity="0.2"><animate attributeName="r" values="8;14;8" dur="2s" repeatCount="indefinite"/></circle>';
      }
    });

    markers.forEach(function (m) {
      var idx = data.findIndex(function (d) { return d.date === m.date || d.idx === m.idx; });
      if (idx < 0) idx = m.idx;
      if (idx >= 0 && idx < data.length) {
        var mx = x(idx);
        var my = y(data[idx][m.key] || data[idx].th || 0);
        svg += '<circle cx="' + mx + '" cy="' + my + '" r="7" fill="' + (m.color || '#fbbf24') + '" stroke="#0c1117" stroke-width="2"/>';
        svg += '<text x="' + mx + '" y="' + (my - 12) + '" fill="' + (m.color || '#fbbf24') + '" font-size="9" text-anchor="middle" font-weight="700">' + (m.label || '预') + '</text>';
      }
    });

    var step = Math.ceil(data.length / 7);
    data.forEach(function (d, i) {
      if (i % step === 0 || i === data.length - 1) {
        svg += '<text x="' + x(i) + '" y="' + (h - 12) + '" fill="#64748b" font-size="9" text-anchor="middle" font-family="DM Mono,monospace">' + (d.date || i) + '</text>';
      }
    });
    svg += '</svg>';
    el.innerHTML = svg;
  },

  radarChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var axes = options.axes || [];
    var cx = 120, cy = 120, maxR = 88;
    var n = axes.length;
    var svg = '<svg viewBox="0 0 240 240" xmlns="http://www.w3.org/2000/svg">';

    for (var ring = 1; ring <= 4; ring++) {
      var rr = (maxR / 4) * ring;
      var rp = [];
      for (var a = 0; a < n; a++) {
        var ang = (Math.PI * 2 * a / n) - Math.PI / 2;
        rp.push((cx + rr * Math.cos(ang)) + ',' + (cy + rr * Math.sin(ang)));
      }
      svg += '<polygon points="' + rp.join(' ') + '" fill="none" stroke="rgba(148,163,184,0.12)" stroke-width="1"/>';
    }

    axes.forEach(function (ax, i) {
      var ang = (Math.PI * 2 * i / n) - Math.PI / 2;
      var ex = cx + maxR * Math.cos(ang);
      var ey = cy + maxR * Math.sin(ang);
      svg += '<line x1="' + cx + '" y1="' + cy + '" x2="' + ex + '" y2="' + ey + '" stroke="rgba(148,163,184,0.15)" stroke-width="1"/>';
      var lx = cx + (maxR + 18) * Math.cos(ang);
      var ly = cy + (maxR + 18) * Math.sin(ang);
      svg += '<text x="' + lx + '" y="' + (ly + 4) + '" fill="#94a3b8" font-size="10" text-anchor="middle" font-weight="600">' + ax.label + '</text>';
    });

    var valPts = axes.map(function (ax, i) {
      var ang = (Math.PI * 2 * i / n) - Math.PI / 2;
      var r = maxR * Math.min(ax.value / ax.max, 1);
      return (cx + r * Math.cos(ang)) + ',' + (cy + r * Math.sin(ang));
    }).join(' ');
    svg += '<polygon points="' + valPts + '" fill="rgba(212,160,84,0.2)" stroke="#d4a054" stroke-width="2"/>';

    axes.forEach(function (ax, i) {
      var ang = (Math.PI * 2 * i / n) - Math.PI / 2;
      var r = maxR * Math.min(ax.value / ax.max, 1);
      var px = cx + r * Math.cos(ang);
      var py = cy + r * Math.sin(ang);
      svg += '<circle cx="' + px + '" cy="' + py + '" r="4" fill="' + (ax.color || '#d4a054') + '" stroke="#0c1117" stroke-width="1.5"/>';
    });

    svg += '</svg>';
    el.innerHTML = svg;
  },

  rateChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var data = options.data || [];
    var threshold = options.threshold;
    var w = el.clientWidth || 400;
    var h = el.clientHeight || 180;
    var pad = { t: 16, r: 16, b: 28, l: 44 };
    var plotW = w - pad.l - pad.r;
    var plotH = h - pad.t - pad.b;
    var maxV = Math.max.apply(null, data.map(function (d) { return d.rate; }).concat(threshold != null ? [threshold * 1.5] : []));
    if (!maxV || maxV <= 0) maxV = 1;
    function x(i) { return pad.l + (i / (data.length - 1 || 1)) * plotW; }
    function y(v) { return pad.t + plotH - (v / maxV) * plotH; }

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    svg += '<defs><linearGradient id="rateGrad" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="rgba(61,191,176,0.35)"/><stop offset="100%" stop-color="rgba(61,191,176,0)"/></linearGradient></defs>';

    if (threshold != null) {
      var ty = y(threshold);
      svg += '<line x1="' + pad.l + '" y1="' + ty + '" x2="' + (w - pad.r) + '" y2="' + ty + '" stroke="#fb923c" stroke-dasharray="4,4" opacity="0.6"/>';
      svg += '<text x="' + (pad.l - 4) + '" y="' + (ty + 3) + '" fill="#fb923c" font-size="9" text-anchor="end" font-family="DM Mono,monospace">' + threshold + '%</text>';
    }

    var pts = data.map(function (d, i) { return x(i) + ',' + y(d.rate); });
    var area = 'M' + pad.l + ',' + (pad.t + plotH) + ' L' + pts.join(' L') + ' L' + x(data.length - 1) + ',' + (pad.t + plotH) + ' Z';
    svg += '<path d="' + area + '" fill="url(#rateGrad)"/>';
    var strokeColor = threshold != null ? '#fb923c' : '#3dbfb0';
    var glowColor = threshold != null ? 'rgba(251,146,60,0.6)' : 'rgba(61,191,176,0.5)';
    svg += '<polyline fill="none" stroke="' + strokeColor + '" stroke-width="2.5" points="' + pts.join(' ') + '" style="filter:drop-shadow(0 0 4px ' + glowColor + ')"/>';

    data.forEach(function (d, i) {
      if (d.pre) {
        svg += '<circle cx="' + x(i) + '" cy="' + y(d.rate) + '" r="6" fill="#fbbf24" stroke="#0c1117" stroke-width="2"/>';
        svg += '<text x="' + x(i) + '" y="' + (y(d.rate) - 10) + '" fill="#fbbf24" font-size="9" text-anchor="middle" font-weight="700">预</text>';
      }
    });

    svg += '<text x="' + (w / 2) + '" y="' + (h - 6) + '" fill="#64748b" font-size="9" text-anchor="middle">相对产气速率 %/月 · DL/T 722 §9.3.2</text>';
    svg += '</svg>';
    el.innerHTML = svg;
  },

  completenessRings: function (container, items) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var w = el.clientWidth || 280;
    var cols = 4;
    var cellW = w / cols;
    var rows = Math.ceil(items.length / cols);
    var h = rows * 56 + 8;
    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    items.forEach(function (item, i) {
      var col = i % cols;
      var row = Math.floor(i / cols);
      var cx = col * cellW + cellW / 2;
      var cy = row * 56 + 28;
      var r = 18;
      var pct = item.pct / 100;
      var circ = 2 * Math.PI * r;
      var color = item.core ? '#3dbfb0' : '#5b9fd4';
      if (item.pct < 80) color = '#64748b';
      svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="rgba(148,163,184,0.12)" stroke-width="4"/>';
      svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="4" stroke-dasharray="' + (circ * pct) + ' ' + circ + '" transform="rotate(-90 ' + cx + ' ' + cy + ')" style="filter:drop-shadow(0 0 3px ' + color + ')"/>';
      svg += '<text x="' + cx + '" y="' + (cy + 3) + '" fill="#e8edf5" font-size="8" text-anchor="middle" font-weight="600">' + item.label + '</text>';
      svg += '<text x="' + cx + '" y="' + (cy + 22) + '" fill="' + color + '" font-size="8" text-anchor="middle" font-family="DM Mono,monospace">' + item.pct + '%</text>';
    });
    svg += '</svg>';
    el.innerHTML = svg;
  },

  glowDonut: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var segments = options.segments || [];
    var total = segments.reduce(function (s, seg) { return s + seg.value; }, 0) || 1;
    var cx = 90, cy = 90, r = 68, ir = 42;
    var angle = -90;
    var svg = '<svg viewBox="0 0 180 180" xmlns="http://www.w3.org/2000/svg"><defs>';
    segments.forEach(function (seg, i) {
      svg += '<filter id="dglow' + i + '"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>';
    });
    svg += '</defs>';
    segments.forEach(function (seg, i) {
      var sweep = (seg.value / total) * 360;
      var start = angle;
      var end = angle + sweep;
      angle = end;
      var x1 = cx + r * Math.cos(start * Math.PI / 180);
      var y1 = cy + r * Math.sin(start * Math.PI / 180);
      var x2 = cx + r * Math.cos(end * Math.PI / 180);
      var y2 = cy + r * Math.sin(end * Math.PI / 180);
      var ix1 = cx + ir * Math.cos(end * Math.PI / 180);
      var iy1 = cy + ir * Math.sin(end * Math.PI / 180);
      var ix2 = cx + ir * Math.cos(start * Math.PI / 180);
      var iy2 = cy + ir * Math.sin(start * Math.PI / 180);
      var large = sweep > 180 ? 1 : 0;
      svg += '<path d="M' + x1 + ',' + y1 + ' A' + r + ',' + r + ' 0 ' + large + ' 1 ' + x2 + ',' + y2 +
        ' L' + ix1 + ',' + iy1 + ' A' + ir + ',' + ir + ' 0 ' + large + ' 0 ' + ix2 + ',' + iy2 + ' Z" fill="' + seg.color + '" filter="url(#dglow' + i + ')" opacity="0.9"/>';
    });
    svg += '<text x="' + cx + '" y="' + (cy - 2) + '" fill="#e8edf5" font-size="20" font-weight="700" text-anchor="middle" font-family="DM Mono,monospace">' + total + '</text>';
    svg += '<text x="' + cx + '" y="' + (cy + 14) + '" fill="#64748b" font-size="9" text-anchor="middle">' + (options.centerLabel || '天') + '</text>';
    svg += '</svg>';
    el.innerHTML = svg;
  },

  levelStrip: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var levels = options.levels || [];
    var colors = options.colors || {
      normal: '#34d399', w1: '#fbbf24', w2: '#fb923c', alarm: '#f87171'
    };
    var w = el.clientWidth || 600;
    var h = options.height || 56;
    var pad = { l: 4, r: 4, t: 20, b: 22 };
    var barH = h - pad.t - pad.b;
    var segW = (w - pad.l - pad.r) / (levels.length || 1);
    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    levels.forEach(function (lv, i) {
      var x = pad.l + i * segW;
      svg += '<rect x="' + x + '" y="' + pad.t + '" width="' + Math.max(segW - 0.5, 1) + '" height="' + barH + '" fill="' + (colors[lv] || colors.normal) + '" opacity="0.85"/>';
    });
    var marks = [0, 90, 180, 270, levels.length];
    marks.forEach(function (day) {
      var x = pad.l + (day / levels.length) * (w - pad.l - pad.r);
      if (day > 0 && day < levels.length) {
        svg += '<line x1="' + x + '" y1="' + pad.t + '" x2="' + x + '" y2="' + (pad.t + barH) + '" stroke="rgba(12,17,23,0.35)" stroke-width="1"/>';
      }
      svg += '<text x="' + x + '" y="' + (h - 4) + '" fill="#64748b" font-size="8" text-anchor="' + (day >= levels.length ? 'end' : 'middle') + '" font-family="DM Mono,monospace">D' + (day || 1) + '</text>';
    });
    svg += '<text x="' + (w / 2) + '" y="12" fill="#94a3b8" font-size="9" text-anchor="middle">360 天 · 表 A.3 档位色带（深=越严重）</text>';
    svg += '</svg>';
    el.innerHTML = svg;
  },

  barChart: function (container, options) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var items = options.items || [];
    var w = el.clientWidth || 320;
    var h = el.clientHeight || 180;
    var pad = { t: 16, r: 12, b: 36, l: 36 };
    var plotW = w - pad.l - pad.r;
    var plotH = h - pad.t - pad.b;
    var maxV = Math.max.apply(null, items.map(function (it) { return it.value; }).concat([1]));
    var gap = 12;
    var barW = (plotW - gap * (items.length - 1)) / items.length;
    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    items.forEach(function (it, i) {
      var bh = (it.value / maxV) * plotH;
      var x = pad.l + i * (barW + gap);
      var y = pad.t + plotH - bh;
      svg += '<rect x="' + x + '" y="' + y + '" width="' + barW + '" height="' + bh + '" rx="4" fill="' + (it.color || '#d4a054') + '" opacity="0.9" style="filter:drop-shadow(0 0 4px ' + (it.color || '#d4a054') + ')"/>';
      svg += '<text x="' + (x + barW / 2) + '" y="' + (y - 4) + '" fill="#e8edf5" font-size="10" text-anchor="middle" font-family="DM Mono,monospace">' + it.value + '</text>';
      svg += '<text x="' + (x + barW / 2) + '" y="' + (h - 10) + '" fill="#64748b" font-size="9" text-anchor="middle">' + it.label + '</text>';
    });
    svg += '</svg>';
    el.innerHTML = svg;
  },

  correlationHeatmap: function (container, matrix, labels) {
    var el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    var n = labels.length;
    var cell = 28;
    var pad = 32;
    var w = pad + n * cell + 8;
    var h = pad + n * cell + 8;
    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" xmlns="http://www.w3.org/2000/svg">';
    labels.forEach(function (lb, i) {
      svg += '<text x="' + (pad + i * cell + cell / 2) + '" y="20" fill="#64748b" font-size="8" text-anchor="middle">' + lb + '</text>';
      svg += '<text x="14" y="' + (pad + i * cell + cell / 2 + 3) + '" fill="#64748b" font-size="8" text-anchor="middle">' + lb + '</text>';
    });
    matrix.forEach(function (row, i) {
      row.forEach(function (val, j) {
        var op = i === j ? 0.15 : Math.abs(val) * 0.85;
        var col = val >= 0 ? '61,191,176' : '248,113,113';
        svg += '<rect x="' + (pad + j * cell) + '" y="' + (pad + i * cell) + '" width="' + (cell - 2) + '" height="' + (cell - 2) + '" rx="3" fill="rgba(' + col + ',' + op + ')" stroke="rgba(148,163,184,0.08)"/>';
        if (i !== j && Math.abs(val) >= 0.5) {
          svg += '<text x="' + (pad + j * cell + cell / 2) + '" y="' + (pad + i * cell + cell / 2 + 3) + '" fill="#e8edf5" font-size="7" text-anchor="middle" font-family="DM Mono,monospace">' + val.toFixed(2) + '</text>';
        }
      });
    });
    svg += '</svg>';
    el.innerHTML = svg;
  }
};
