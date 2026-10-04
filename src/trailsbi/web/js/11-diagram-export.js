/* ---------- Export a model diagram as a picture ----------
   The diagram on screen is HTML cards over an SVG of the relationship lines,
   which cannot be saved as one file. The same layout is redrawn here as a
   single self-contained SVG - no CSS variables, no nested <svg>, no external
   fonts - so it opens anywhere and rasterises to PNG without tainting a canvas. */
var DX_FONT = '"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,sans-serif';
var TRAILS_LOGO = '__LOGO__', TRAILS_LOGO_W = 509.0, TRAILS_LOGO_H = 125.0;
function dExportMenu() {
  return '<div class="menu dexport">' +
         '<button class="tbtn dexp-btn" aria-haspopup="true" aria-expanded="false" title="Save this diagram as a picture">' +
         icon("ui_download", 14) + '<span>Export</span>' + icon("ui_chev", 12, "chev") + '</button>' +
         '<div class="pop dexp-pop" role="dialog" aria-label="Export diagram" hidden>' +
         '<h5>Export diagram</h5>' +
         '<label><input type="checkbox" class="dexp-mask"> Hide table and column names</label>' +
         '<div class="pop-head"><button class="tbtn" data-exp="png">PNG</button>' +
         '<button class="tbtn" data-exp="svg">SVG</button></div></div></div>';
}
/* Asterisks of the same length, so the drawing keeps its proportions. */
function dxMask(name, on) {
  if (!on) return name;
  var n = Math.max(3, Math.min(String(name || "").length, 18));
  return new Array(n + 1).join("✱");
}
function dxEsc(t) {
  return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
/* Icons go in as plain paths: a nested <svg> is not drawn by every viewer. */
function dxIcon(name, x, y, size, color) {
  var body = ICONS[name] || ICONS.v_generic;
  return '<g transform="translate(' + x + ',' + y + ') scale(' + (size / 24) + ')" ' +
         'fill="none" stroke="' + color + '" stroke-width="2" stroke-linecap="round" ' +
         'stroke-linejoin="round">' + body + '</g>';
}
function dxCard(t, p, keys, mask) {
  var accent = t.k === "calc" ? "#a86a12" : "#1f5fa8";
  var ic = t.k === "calc" ? "calctable" : t.k === "fieldparam" ? "fieldparam"
         : t.k === "calcgroup" ? "calcitem" : "table";
  var rows = t.cols.filter(function (f) { return keys[t.n + "␞" + f.n]; });
  var w = p.w, h = p.h, r = 6;
  var g = '<g transform="translate(' + p.x + ',' + p.y + ')">';
  // body, rounded on the right only, with the 4px accent bar down the left
  g += '<path d="M0,0H' + (w - r) + 'a' + r + ',' + r + ' 0 0 1 ' + r + ',' + r +
       'V' + (h - r) + 'a' + r + ',' + r + ' 0 0 1 ' + (-r) + ',' + r + 'H0Z" fill="#ffffff" stroke="#dde3e9"/>';
  g += '<path d="M0,0h4v' + h + 'h-4Z" fill="' + accent + '"/>';
  g += '<path d="M4,0H' + (w - r) + 'a' + r + ',' + r + ' 0 0 1 ' + r + ',' + r + 'V' + DHEAD +
       'H4Z" fill="#f8fafb"/>';
  g += '<path d="M4,' + DHEAD + 'H' + w + '" stroke="#e8ecf0"/>';
  g += dxIcon(ic, 12, (DHEAD - 16) / 2, 16, accent);
  g += '<text class="dx-h' + (t.h ? " dx-hid" : "") + '" x="36" y="' + (DHEAD / 2 + 4) +
       '" data-room="' + (w - 46) + '" data-full="' + dxEsc(dxMask(t.n, mask)) + '">' +
       dxEsc(dxMask(t.n, mask)) + '</text>';
  rows.forEach(function (f, i) {
    var y = DHEAD + 4 + i * DROW;
    g += dxIcon(f.calc ? "calccolumn" : "column", 10, y + (DROW - 13) / 2, 13,
                f.calc ? "#a86a12" : "#2f7f96");
    g += '<text class="dx-f' + (f.h ? " dx-hid" : "") + '" x="29" y="' + (y + DROW / 2 + 4) +
         '" data-room="' + (w - 29 - 26) + '" data-full="' + dxEsc(dxMask(f.n, mask)) + '">' +
         dxEsc(dxMask(f.n, mask)) + '</text>';
    g += dxIcon("key", w - 22, y + (DROW - 12) / 2, 12, "#5c6a78");
  });
  return g + '</g>';
}
function diagramSvg(m, mask) {
  var V = mdVisible(m), L = layoutDiagramFit(V), keys = dRelKeys(V);
  var slots = dSlots(V.rels, L.pos);
  var paths = V.rels.map(function (r, i) { return dRelPath(slots[i]); });
  var segs = dSegPoints(paths);
  dBadges(paths, slots);
  dNudgeChips(paths, segs);
  var chips = dChipPoints(paths);
  var pad = 16, head = 34, foot = 18;                  // the credit line sits in the footer
  var W = dCanvasW(L, paths) + pad * 2, H = dCanvasH(L, paths) + pad * 2 + head + foot;
  var s = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="' + W + '" height="' + H +
          '" viewBox="0 0 ' + W + ' ' + H + '">';
  s += '<style>svg{font-family:' + DX_FONT + '}text{fill:#13203B}' +
       '.dx-t{font-size:14px;font-weight:600}.dx-s{font-size:12px;fill:#5c6a78}' +
       '.dx-h{font-size:13px;font-weight:700}.dx-f{font-size:12px}' +
       '.dx-hid{fill:#5c6a78;font-style:italic}' +
       '.line{fill:none;stroke:#8795a3;stroke-width:1.6}.inactive .line{stroke-dasharray:5 4}' +
       '.dmark rect,.darrow rect{fill:#f4f6f8;stroke:#cfd7df}' +
       '.darrow path{fill:#13203B;stroke:none}' +
       '.dmark text{font-weight:700;fill:#13203B;text-anchor:middle;dominant-baseline:middle}' +
       '.dmark text.one{font-size:12px}.dmark text.many{font-size:19px}</style>';
  s += '<rect width="' + W + '" height="' + H + '" fill="#eef1f4"/>';
  var title = (mask ? "Semantic model" : m.name) + "  ·  " +
              plural(V.tables.length, "table", "tables") + "  ·  " +
              plural(V.rels.length, "relationship", "relationships");
  s += '<text class="dx-t" x="' + pad + '" y="21">' + dxEsc(title) + '</text>';
  /* Every shared diagram says where it came from. */
  var lh = 15, lk = lh / TRAILS_LOGO_H, lw = TRAILS_LOGO_W * lk, lx = W - pad - lw;
  s += '<a href="https://trailsbi.com" xlink:href="https://trailsbi.com" target="_blank">' +
       '<title>Trails for Power BI · trailsbi.com</title>' +
       '<text class="dx-s" x="' + (lx - 6) + '" y="' + (H - 9) + '" text-anchor="end">Generated by</text>' +
       '<g transform="translate(' + lx + ',' + (H - 8 - lh + 1) + ') scale(' + lk.toFixed(4) + ')">' + TRAILS_LOGO + '</g></a>';
  s += '<g transform="translate(' + pad + ',' + (pad + head) + ')">';
  var bars = [];                          // drawn last, over the lines they speak for
  V.rels.forEach(function (r, i) {
    var pa = paths[i];
    if (!pa) return;
    var fromMark = r.fc === "many" ? "∗" : "1", toMark = r.tc === "many" ? "∗" : "1";
    var m1 = pa.factFirst ? fromMark : toMark, m2 = pa.factFirst ? toMark : fromMark;
    var arrows = r.both ? dArrow(pa, true, true, chips, segs, i)
                        : dArrow(pa, m1 === "1", false, chips, segs, i);
    var marks = "";
    [[pa.m1, m1], [pa.m2, m2]].forEach(function (e) {
      if (!e[0]) return;
      if (e[0].span) bars.push(dMark(e[0], e[1])); else marks += dMark(e[0], e[1]);
    });
    s += '<g class="' + (r.active ? "" : "inactive") + '"><path class="line" d="' + pa.d + '"/>' +
         arrows + marks + '</g>';
  });
  s += bars.join("");
  V.tables.forEach(function (t) {
    var p = L.pos[t.n];
    if (p) s += dxCard(t, p, keys, mask);
  });
  return {svg: s + '</g></svg>', w: W, h: H};
}
/* Text is trimmed by measuring it, the same way the cards on screen are, so the
   picture has to be laid out for a moment before it is saved. */
function diagramSvgFitted(m, mask) {
  var out = diagramSvg(m, mask);
  var host = document.createElement("div");
  host.setAttribute("style", "position:absolute;left:-99999px;top:0;width:" + out.w + "px");
  host.innerHTML = out.svg;
  document.body.appendChild(host);
  var el = host.firstChild;
  try { fitCardLines(el); } catch (e) {}
  el.querySelectorAll("text[data-room]").forEach(function (t) {
    t.removeAttribute("data-room");
    t.removeAttribute("data-full");
  });
  var text = new XMLSerializer().serializeToString(el);
  host.remove();
  return {svg: '<?xml version="1.0" encoding="UTF-8"?>\n' + text, w: out.w, h: out.h};
}
/* A short message at the foot of the window, for the few things that go wrong
   quietly - an export that had to change format, say. */
var toastT = null;
function toast(msg) {
  var el = $("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.setAttribute("role", "status");
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.hidden = false;
  el.classList.remove("out");
  clearTimeout(toastT);
  toastT = setTimeout(function () {
    el.classList.add("out");
    setTimeout(function () { el.hidden = true; }, 300);
  }, 6000);
}
function dxDownload(name, blob) {
  var url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = name; a.style.display = "none";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
}
function dxName(m, mask, ext) {
  var base = mask ? "semantic model diagram (names hidden)" : m.name + " diagram";
  return base.replace(/[\\/:*?"<>|]+/g, "-") + "." + ext;
}
function exportDiagram(m, mask, kind) {
  var out = diagramSvgFitted(m, mask);
  if (kind === "svg") {
    dxDownload(dxName(m, mask, "svg"), new Blob([out.svg], {type: "image/svg+xml;charset=utf-8"}));
    return;
  }
  /* Rasterise. A big diagram runs into two browser limits: a data: URL long
     enough to carry the markup, and the canvas itself - no side over DXMAX and
     no more than DXAREA pixels in all. The source goes through a blob URL, which
     has no length limit, and the scale drops until the bitmap fits. */
  var DXMAX = 16384, DXAREA = 64e6;
  var scale = 2;
  var fit = function () {
    var s = Math.min(scale, DXMAX / out.w, DXMAX / out.h,
                     Math.sqrt(DXAREA / (out.w * out.h)));
    return s > 0 ? s : 1;
  };
  var url = URL.createObjectURL(new Blob([out.svg], {type: "image/svg+xml;charset=utf-8"}));
  var done = false;
  var giveUp = function (why) {               // fall back to the vector file
    if (done) return;
    done = true;
    URL.revokeObjectURL(url);
    dxDownload(dxName(m, mask, "svg"), new Blob([out.svg], {type: "image/svg+xml;charset=utf-8"}));
    toast("This diagram is too large to rasterise here, so it came out as SVG" +
          (why ? " (" + why + ")" : "") + ".");
  };
  var img = new Image();
  img.onload = function () {
    if (done) return;
    var s = fit();
    try {
      var cv = document.createElement("canvas");
      cv.width = Math.max(1, Math.round(out.w * s));
      cv.height = Math.max(1, Math.round(out.h * s));
      var ctx = cv.getContext("2d");
      if (!ctx) return giveUp("no 2d context");
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.drawImage(img, 0, 0, cv.width, cv.height);
      if (!cv.toBlob) return giveUp("no canvas encoder");
      cv.toBlob(function (b) {
        if (done) return;
        if (!b) return giveUp("the bitmap is over this browser's limit");
        done = true;
        URL.revokeObjectURL(url);
        dxDownload(dxName(m, mask, "png"), b);
        if (s < 1) toast("This diagram is wider than a PNG can be, so it was saved at " +
                         Math.round(s * 100) + "% - the SVG keeps every detail.");
      }, "image/png");
    } catch (e) { giveUp(e && e.message); }
  };
  img.onerror = function () { giveUp("the image would not load"); };
  setTimeout(function () { giveUp("it timed out"); }, 20000);
  img.src = url;
}
$("mdDiagram").addEventListener("click", function (e) {
  var btn = e.target.closest && e.target.closest(".dexp-btn");
  if (btn) {
    e.stopPropagation();
    var pop = btn.parentNode.querySelector(".dexp-pop"), open = pop.hidden;
    closeMenus();
    pop.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    return;
  }
  var pop = e.target.closest && e.target.closest(".dexp-pop");
  if (!pop) return;
  e.stopPropagation();
  var go = e.target.closest("button[data-exp]");
  if (!go) return;
  var sec = pop.closest("section.dsec");
  var m = (D.meta.models || []).filter(function (x) { return x.key === sec.getAttribute("data-mkey"); })[0];
  if (!m) return;
  exportDiagram(m, pop.querySelector(".dexp-mask").checked, go.getAttribute("data-exp"));
  pop.hidden = true;
  pop.parentNode.querySelector(".dexp-btn").setAttribute("aria-expanded", "false");
});
/* Side pane: a table's fields, or a relationship's details. */
function mdPanelEmpty() {
  $("mdPanel").innerHTML = '<h2>Select a table or a relationship.</h2>' +
    '<p class="muted">Tables show their columns and measures here. Relationships show both sides, ' +
    'the cardinality, the filter direction and whether they are active.</p>';
}
function openMdSide() {
  var side = $("mdSide");
  if (side && side.classList.contains("collapsed") && typeof setSide === "function") setSide(false, true, side);
}
function showDiagramSelection() {
  $("mdDiagram").querySelectorAll(".dcard.sel, .drel.sel").forEach(function (x) { x.classList.remove("sel"); });
  $("mdDiagram").querySelectorAll(".dcard.lit, .drel.lit, .dbar.lit").forEach(function (x) { x.classList.remove("lit"); });
  $("mdDiagram").querySelectorAll(".drel.run, .dbar.run").forEach(function (x) { x.classList.remove("run"); });
  $("mdDiagram").querySelectorAll("section.dsec.tfocus").forEach(function (x) { x.classList.remove("tfocus"); });
  $("mdDiagram").querySelectorAll(".dfield.keyhl").forEach(function (x) { x.classList.remove("keyhl"); });
  var s = state.mdSel;
  if (!s) { mdPanelEmpty(); return; }
  if (s.kind === "table") {
    var m = (D.meta.models || []).filter(function (x) { return x.key === s.mkey; })[0];
    var V = m ? mdVisible(m) : null;
    var t = V && V.tables.filter(function (x) { return x.n === s.name; })[0];
    if (!t) { mdPanelEmpty(); return; }
    var el = $("mdDiagram").querySelector('.dcard[data-t="' + cssq(s.name) + '"][data-m="' + cssq(s.mkey) + '"]');
    if (el) el.classList.add("sel");
    var rels = V.rels.filter(function (r) { return r.f[0] === t.n || r.t[0] === t.n; });
    /* Light up every relationship this table is in - the line, the key column at
       each end, and the card at the far end - and push the rest of the diagram
       back so what it touches reads at a glance. */
    var tsec = el && el.closest("section.dsec");
    if (tsec && rels.length) {
      tsec.classList.add("tfocus");
      V.rels.forEach(function (r, i) {
        if (r.f[0] !== t.n && r.t[0] !== t.n) return;
        var g = tsec.querySelector('.drel[data-r="' + cssq(s.mkey + "|" + V.ridx[i]) + '"]');
        if (g) {
          g.classList.add("lit");
          (g.getAttribute("data-runs") || "").split(" ").forEach(function (id) {
            if (!id) return;
            tsec.querySelectorAll('.dbar[data-run="' + id + '"]')
                .forEach(function (bar) { bar.classList.add("lit"); });
          });
        }
        [[r.f[0], r.f[1]], [r.t[0], r.t[1]]].forEach(function (pair) {
          var f = tsec.querySelector('.dfield[data-t="' + cssq(pair[0]) + '"][data-c="' + cssq(pair[1]) + '"]');
          if (f) f.classList.add("keyhl");
          if (pair[0] === t.n) return;
          var oc = tsec.querySelector('.dcard[data-t="' + cssq(pair[0]) + '"]');
          if (oc) oc.classList.add("lit");
        });
      });
    }
    var h = '<span class="badge t-table">Table</span><h2>' + icon(iconName({type: "table"}), 20, "t-table") + esc(t.n) + '</h2>' +
            (t.d ? '<p class="muted">' + esc(t.d) + '</p>' : "");
    h += '<h3><span>Columns</span><span class="muted count">' + t.cols.length + '</span></h3><div class="pcards">' +
         t.cols.map(function (c) {
           var nid = fieldId(s.mkey, t.n, c.n);
           return '<div class="card fcard withacts ' + (c.calc ? "t-column s-calculated" : "t-column") + '" title="' + esc(c.n) + '">' +
                  '<span class="bar"></span>' + icon(c.calc ? "calccolumn" : "column", 16) +
                  '<span class="fname' + (c.h ? " hid" : "") + '">' + esc(c.n) + '</span>' +
                  '<small class="inline">' + esc([dataTypeLabel(c.dt), c.key ? "Key" : ""].filter(Boolean).join(" · ")) + '</small>' +
                  '<span class="facts">' +
                  (nid ? '<button class="fact-btn" data-go-id="' + esc(nid) + '" title="Show in lineage" aria-label="' +
                         esc("Show " + c.n + " in the lineage map") + '">' + icon("nav_lineage", 14) + '</button>' : '') +
                  (c.calc ? '<button class="fact-btn" data-detail-m="' + esc(s.mkey) + '" data-detail-t="' + esc(t.n) +
                            '" data-detail-c="' + esc(c.n) + '" title="Show detail with its DAX" aria-label="' +
                            esc("Show " + c.n + " in the model details") + '">' + icon("nav_model", 14) + '</button>' : '') +
                  '</span></div>';
         }).join("") + '</div>';
    h += '<h3><span>Relationships</span><span class="muted count">' + rels.length + '</span></h3><div class="pcards">' +
         (rels.length ? rels.map(function (r) {
           return '<div class="card fcard" style="--c:var(--model)"><span class="bar"></span>' + icon("relationship", 16) +
                  '<span class="fname">' + esc(r.f[0] + "[" + r.f[1] + "] → " + r.t[0] + "[" + r.t[1] + "]") + '</span>' +
                  '<small>' + esc((r.fc === "many" ? "many" : "one") + " → " + (r.tc === "many" ? "many" : "one")) + '</small></div>';
         }).join("") : '<p class="muted">This table has no relationships.</p>') + '</div>';
    $("mdPanel").innerHTML = h;
    return;
  }
  var mm = (D.meta.models || []).filter(function (x) { return x.key === s.mkey; })[0];
  var r = mm && mm.diagram.rels[s.idx];
  if (!r) { mdPanelEmpty(); return; }
  var g = $("mdDiagram").querySelector('.drel[data-r="' + cssq(s.mkey + "|" + s.idx) + '"]');
  if (g) g.classList.add("sel");
  var sec = g && g.closest("section.dsec");
  if (sec) {
    [[r.f[0], r.f[1]], [r.t[0], r.t[1]]].forEach(function (pair) {
      var f = sec.querySelector('.dfield[data-t="' + cssq(pair[0]) + '"][data-c="' + cssq(pair[1]) + '"]');
      if (f) f.classList.add("keyhl");
    });
  }
  var card = function (value, ic, col, sub, tip) {
    return '<div class="rf"><div class="card fcard" style="--c:' + (col || "var(--page)") + '" title="' +
           esc(tip || (sub ? sub + " · " + value : value)) + '"><span class="bar"></span>' + icon(ic, 16) +
           '<span class="fname">' + esc(value) + '</span>' + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</div></div>';
  };
  var cardinality = (r.fc === "many" ? "Many" : "One") + " to " + (r.tc === "many" ? "many" : "one");
  var cardSymbols = "(" + (r.fc === "many" ? "*" : "1") + ":" + (r.tc === "many" ? "*" : "1") + ")";
  $("mdPanel").innerHTML = '<span class="badge k-model">Relationship</span><h2>' + icon("relationship", 20, "k-model") +
    esc(r.f[0] + " → " + r.t[0]) + (r.active ? "" : '<span class="tag bad">Inactive</span>') + '</h2><div class="relform">' +
    '<div class="rf-row one">' + card(r.f[1], "column", "var(--column)", r.f[0]) + '</div>' +
    '<div class="rf-row one">' + card(cardinality, "relationship", "var(--model)", cardSymbols,
                                      "Cardinality: " + cardinality + " " + cardSymbols) + '</div>' +
    '<div class="rf-row one">' + card(r.t[1], "column", "var(--column)", r.t[0]) + '</div>' +
    '<div class="rf-row one">' + card((r.both ? "Both" : "Single") + " filter direction",
                                      r.both ? "arrow_both" : "arrow_one", "var(--page)", "",
                                      "Filter direction: " + (r.both ? "Both" : "Single")) + '</div></div>';
}
var DTYPE_LABEL = {int64: "Int64", double: "Double", decimal: "Decimal", string: "String",
                   datetime: "DateTime", boolean: "Boolean", binary: "Binary", variant: "Variant"};
function dataTypeLabel(dt) {
  if (!dt) return "";
  return DTYPE_LABEL[String(dt).toLowerCase()] || (dt.charAt(0).toUpperCase() + dt.slice(1));
}
var FIELD_ID = {};
byId.forEach(function (n) {
  if (n.type === "column" || n.type === "measure")
    FIELD_ID[(n.mkey || "") + "\u241e" + (n.table || "") + "\u241e" + n.label] = n.id;
});
function fieldId(mkey, table, name) { return FIELD_ID[mkey + "\u241e" + table + "\u241e" + name] || ""; }
state.dZoom = 1;
function applyDiagramZoom() {
  var z = state.dZoom;
  $("mdZLevel").textContent = Math.round(z * 100) + "%";
  $("mdDiagram").querySelectorAll(".dwrap").forEach(function (w) {
    var cv = w.querySelector(".dcanvas");
    cv.style.transform = "scale(" + z + ")";
    w.style.width = Math.round(+w.getAttribute("data-w") * z) + "px";
    w.style.height = Math.round(+w.getAttribute("data-h") * z) + "px";
  });
}
function setDiagramZoom(z) {
  state.dZoom = Math.max(0.3, Math.min(2, z));
  applyDiagramZoom();
}
$("mdZIn").addEventListener("click", function () { setDiagramZoom(state.dZoom * 1.25); });
$("mdZOut").addEventListener("click", function () { setDiagramZoom(state.dZoom / 1.25); });
$("mdZLevel").addEventListener("click", function () { setDiagramZoom(1); });
/* Fit: every diagram as wide as the pane allows; a single diagram also fits the pane's height. */
function fitDiagram() {
  var sc = $("modelScroll"), r0 = sc.getBoundingClientRect(), z = 2;
  var ws = Array.prototype.filter.call($("mdDiagram").querySelectorAll(".dwrap"), function (w) { return w.offsetParent; });
  if (!ws.length) return;
  ws.forEach(function (w) {
    var left = w.getBoundingClientRect().left - r0.left + sc.scrollLeft;
    z = Math.min(z, (sc.clientWidth - 2 * left - 4) / +w.getAttribute("data-w"));
  });
  if (ws.length === 1) {
    var w = ws[0], r = w.getBoundingClientRect(), left = r.left - r0.left + sc.scrollLeft;
    var top = r.top - r0.top + sc.scrollTop;
    z = Math.min(z, (sc.clientHeight - top - left - 4) / +w.getAttribute("data-h"));
  }
  setDiagramZoom(Math.min(z, 1));
  sc.scrollTo(0, 0);
}
$("mdZFit").addEventListener("click", fitDiagram);
function cssq(v) { return (window.CSS && CSS.escape) ? CSS.escape(v) : String(v).replace(/"/g, '\\"'); }
function setModelMode(mode) {
  state.mdMode = mode;
  $("mdList").classList.toggle("on", mode === "list");
  $("mdDiag").classList.toggle("on", mode === "diagram");
  $("mdList").setAttribute("aria-pressed", String(mode === "list"));
  $("mdDiag").setAttribute("aria-pressed", String(mode === "diagram"));
  $("modelDoc").hidden = mode === "diagram";
  $("mdDiagram").hidden = mode !== "diagram";
  $("mdZoom").hidden = mode !== "diagram";
  $("mdSide").hidden = mode !== "diagram";
  $("mdTypes").hidden = mode === "diagram" || openTab() !== "model";
  $("mdViewBox").hidden = openTab() !== "model";
  syncMdView();
  if (mode === "diagram") buildDiagram();
}
$("mdList").addEventListener("click", function () { setModelMode("list"); });
$("mdDiag").addEventListener("click", function () { setModelMode("diagram"); });
$("mdPanel").addEventListener("click", function (e) {
  var go = e.target.closest && e.target.closest("[data-go-id]");
  if (go) { e.stopPropagation(); go2(go.getAttribute("data-go-id")); return; }
  var det = e.target.closest && e.target.closest("[data-detail-c]");
  if (det) {
    e.stopPropagation();
    showColumnDetail(det.getAttribute("data-detail-m"), det.getAttribute("data-detail-t"), det.getAttribute("data-detail-c"));
  }
});
/* Jump to the Details list, open the column's row and show its DAX. */
function showColumnDetail(mkey, table, col) {
  setModelMode("list");
  var nid = fieldId(mkey, table, col);
  if (nid && revealModelRow(nid)) {
    var row = $("modelDoc").querySelector('.mrow[data-id="' + cssq(nid) + '"]');
    var pre = row && row.nextElementSibling;
    if (pre && pre.classList.contains("mcode")) {
      pre.hidden = false;
      var btn = row.querySelector(".mcodebtn");
      if (btn) btn.classList.add("on");
    }
  }
}
function go2(id) { go(id); }
/* A badge bar speaks for a run of relationships, so it lights all of them -
   hovering shows which lines it covers, clicking opens the table they meet at. */
function dRunLight(sec, id, on) {
  if (!sec || !id) return;
  sec.querySelectorAll('.drel[data-runs~="' + id + '"]').forEach(function (g) {
    g.classList.toggle("run", on);
  });
  sec.querySelectorAll('.dbar[data-run="' + id + '"]').forEach(function (g) {
    g.classList.toggle("run", on);
  });
}
$("mdDiagram").addEventListener("mouseover", function (e) {
  var bar = e.target.closest && e.target.closest(".dbar");
  if (!bar) return;
  dRunLight(bar.closest("section.dsec"), bar.getAttribute("data-run"), true);
});
$("mdDiagram").addEventListener("mouseout", function (e) {
  var bar = e.target.closest && e.target.closest(".dbar");
  if (!bar) return;
  dRunLight(bar.closest("section.dsec"), bar.getAttribute("data-run"), false);
});
$("mdDiagram").addEventListener("click", function (e) {
  var bar = e.target.closest && e.target.closest(".dbar");
  if (bar) {
    var sec = bar.closest("section.dsec");
    dRunLight(sec, bar.getAttribute("data-run"), false);
    state.mdSel = {kind: "table", mkey: sec.getAttribute("data-mkey"),
                   name: bar.getAttribute("data-t")};
    openMdSide();
    showDiagramSelection();
    return;
  }
  var rel = e.target.closest && e.target.closest(".drel");
  if (rel) {
    var parts = rel.getAttribute("data-r").split("|");
    state.mdSel = {kind: "rel", mkey: parts.slice(0, -1).join("|"), idx: +parts[parts.length - 1]};
    openMdSide();
    showDiagramSelection();
    return;
  }
  var card = e.target.closest && e.target.closest(".dcard");
  if (card) {
    state.mdSel = {kind: "table", mkey: card.getAttribute("data-m"), name: card.getAttribute("data-t")};
    openMdSide();
    showDiagramSelection();
    return;
  }
  state.mdSel = null;
  showDiagramSelection();
});
setModelMode("list");

/* Open a row's parents, scroll to it and flash it (used by "Show in Model"). */
function revealModelRow(id) {
  var row = null;
  $("modelDoc").querySelectorAll(".mrow[data-id]").forEach(function (r) { if (!row && r.getAttribute("data-id") === id) row = r; });
  if (!row) return false;
  var sec = row.closest("section.mdl"), rows = Array.prototype.slice.call(sec.querySelectorAll(".mrow"));
  sec.classList.remove("collapsed");
  for (var p = +row.getAttribute("data-p"); p >= 0; p = +rows[p].getAttribute("data-p")) rows[p].setAttribute("data-open", "1");
  if (row.hasAttribute("data-open")) row.setAttribute("data-open", "1");
  applyModelView();
  $("modelDoc").querySelectorAll(".mrow.sel").forEach(function (x) { x.classList.remove("sel"); });
  row.classList.add("sel");                       // stays marked until something else is opened
  row.scrollIntoView({block: "center"});
  flashRow(row);
  return true;
}

