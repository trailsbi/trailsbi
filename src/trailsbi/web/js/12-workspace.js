/* ---------- workspace: several reports and semantic models in one page ----------
   The Workspace view maps which data sources feed which semantic models, and
   which reports use each model. Scope, in the toolbar, picks the semantic
   models and reports every other view shows. */
var ITEMS = D.items || [];
var ITEM_BY_ID = new Map(ITEMS.map(function (i) { return [i.id, i]; }));
var IOUT = new Map(), IIN = new Map();
ITEMS.forEach(function (i) { IOUT.set(i.id, []); IIN.set(i.id, []); });
(D.itemEdges || []).forEach(function (e) {
  if (IOUT.has(e[0]) && IIN.has(e[1])) { IOUT.get(e[0]).push(e[1]); IIN.get(e[1]).push(e[0]); }
});
var SPACES = D.meta.spaces || [];
var MODEL_BY_KEY = new Map(MODELS.map(function (m) { return [m.key, m]; }));
/* With several workspaces a repeated name carries its workspace ("Sales/Model"); the
   workspace is shown beside it, so the name drops it. */
function shortName(x) {
  var nm = x.name || x.label || "";
  return x.space && nm.indexOf(x.space + "/") === 0 ? nm.slice(x.space.length + 1) : nm;
}
ITEMS.forEach(function (i) { if (i.space) i.name = shortName({label: i.label, space: i.space}); });
var KIND_NAME = {source: "Data source", model: "Semantic model", external: "Semantic model from another workspace", report: "Report"};
function reportsOfModel(key) { return REPORTS.filter(function (r) { return r.model === key; }); }

var WS_FILTERS = [
  {k: "source", label: "Data sources", icon: "db", cls: "k-source"},
  {k: "model", label: "Semantic models", icon: "ws_model", cls: "k-model"},
  {k: "report", label: "Reports", icon: "nav_report", cls: "k-report"}
];
state.wsPick = new Set();
function wsKind(it) { return it.kind === "external" ? "model" : it.kind; }
function itemInScope(it) {
  if (!WORKSPACE) return true;
  if (it.kind === "model") return state.scopeModels.has(it.key);
  if (it.kind === "report") return state.scopeReports.has(it.key);
  if (it.kind === "external") return (IOUT.get(it.id) || []).some(function (id) {
    var r = ITEM_BY_ID.get(id);
    if (!r) return false;
    return r.kind === "model" ? state.scopeModels.has(r.key) : state.scopeReports.has(r.key);
  });
  if (it.kind === "source") return (it.mkeys || []).some(function (k) { return state.scopeModels.has(k); });
  return true;
}
function itemVisible(it) {
  if (state.wsPick.size && !state.wsPick.has(wsKind(it))) return false;
  return itemInScope(it);
}

/* ----- item filters (Workspace view) ----- */
var wsTypesBox = $("wsTypes");
var wsAllBtn = h("button", {"class": "t-all", title: "All items"}, "All");
wsAllBtn.addEventListener("click", function () {
  if (!state.wsPick.size) return;
  state.wsPick.clear(); syncWsTypes(); wsRender();
});
wsTypesBox.appendChild(wsAllBtn);
WS_FILTERS.forEach(function (f) {
  var b = h("button", {"data-k": f.k, "class": f.cls, title: f.label, "aria-label": f.label}, icon(f.icon, 16, f.cls));
  b.addEventListener("click", function () {
    if (state.wsPick.has(f.k)) state.wsPick.delete(f.k); else state.wsPick.add(f.k);
    syncWsTypes(); wsRender();
  });
  wsTypesBox.appendChild(b);
});
function syncWsTypes() {
  var picking = state.wsPick.size > 0;
  wsAllBtn.classList.toggle("picked", !picking);
  wsAllBtn.setAttribute("aria-pressed", String(!picking));
  wsTypesBox.querySelectorAll("button[data-k]").forEach(function (b) {
    var on = state.wsPick.has(b.getAttribute("data-k"));
    b.classList.toggle("picked", on);
    b.classList.toggle("dim", picking && !on);
    b.setAttribute("aria-pressed", String(on));
  });
}

/* ----- scope picker ----- */
function scopeShort() {
  var nm = state.scopeModels.size, nr = state.scopeReports.size;
  if (scopeIsAll()) return "all";
  return plural(nm, "model", "models") + ", " + plural(nr, "report", "reports");
}
function scopeLabel() {
  var nm = state.scopeModels.size, nr = state.scopeReports.size;
  if (scopeIsAll()) return "all semantic models and reports";
  return nm + " of " + MODELS.length + " semantic models and " + nr + " of " + REPORTS.length + " reports";
}
/* Text with every occurrence of the query marked. */
function hlKids(text, q) {
  text = String(text || "");
  if (!q) return text;
  var low = text.toLowerCase(), out = [], i = 0, j;
  while ((j = low.indexOf(q, i)) >= 0) {
    if (j > i) out.push(text.slice(i, j));
    out.push(h("mark", {"class": "hit"}, text.slice(j, j + q.length)));
    i = j + q.length;
  }
  if (i < text.length) out.push(text.slice(i));
  return out;
}
/* What the list is showing: Select all and Clear act on these, so searching
   first and then selecting works on the matches alone. */
var SCOPE_SHOWN = {models: [], reports: []};
function fillScopeList() {
  var q = (state.scopeFind || "").trim().toLowerCase();
  var byModel = {};
  REPORTS.forEach(function (r) { var k = r.model || ""; (byModel[k] = byModel[k] || []).push(r); });
  function hit(s) { return !q || String(s || "").toLowerCase().indexOf(q) >= 0; }
  function box(attr, key, on) {
    var a = {type: "checkbox", checked: on};
    a[attr] = key;
    return h("input", a);
  }
  SCOPE_SHOWN = {models: [], reports: []};
  var out = [], body = [], boxes = [], spBoxes = [];
  function modelRows(m, rows, force) {
    var rs = byModel[m.key] || [], mOk = force || hit(m.name);
    var list = mOk ? rs : rs.filter(function (r) { return hit(r.name); });
    if (!mOk && !list.length) return;                    // neither the model nor any of its reports match
    SCOPE_SHOWN.models.push(m.key);
    var cb = box("data-m", m.key, state.scopeModels.has(m.key));
    boxes.push([cb, rs]);
    rows.push(h("label", {"class": "sc-m", title: m.rel || m.key}, [cb, icon("ws_model", 14, "k-model"),
      h("span", null, hlKids(shortName(m), q)), rs.length ? null : h("span", {"class": "muted"}, "no reports")]));
    list.forEach(function (r) {
      SCOPE_SHOWN.reports.push(r.key);
      var away = SPACES.length > 1 && r.space && r.space !== m.space;
      rows.push(h("label", {"class": "sc-r", title: r.rel || r.key}, [box("data-r", r.key, state.scopeReports.has(r.key)),
        icon("nav_report", 14, "k-report"), h("span", null, hlKids(shortName(r), q)),
        away ? h("span", {"class": "muted"}, hlKids(r.space, q)) : null]));
    });
  }
  if (SPACES.length > 1) {                               // one group per workspace
    SPACES.forEach(function (sp) {
      var ms = MODELS.filter(function (m) { return m.space === sp; });
      var rs = REPORTS.filter(function (r) { return r.space === sp; });
      var spOk = !!q && hit(sp), rows = [];
      ms.forEach(function (m) { modelRows(m, rows, spOk); });
      var elsewhere = rs.filter(function (r) { var m = MODEL_BY_KEY.get(r.model); return m && m.space !== sp; });
      if (!rows.length && !spOk && !elsewhere.some(function (r) { return hit(r.name); })) return;
      if (spOk) rs.forEach(function (r) { if (SCOPE_SHOWN.reports.indexOf(r.key) < 0) SCOPE_SHOWN.reports.push(r.key); });
      var keys = ms.map(function (m) { return state.scopeModels.has(m.key); })
        .concat(rs.map(function (r) { return state.scopeReports.has(r.key); }));
      var on = keys.filter(Boolean).length;
      var cb = box("data-s", sp, on > 0 && on === keys.length);
      spBoxes.push([cb, on > 0 && on < keys.length]);
      body.push(h("label", {"class": "sc-s", title: "Workspace " + sp}, [cb, icon("nav_workspace", 14, "is-muted"),
        h("span", null, hlKids(sp, q)),
        h("span", {"class": "muted"}, plural(ms.length, "model", "models") + ", " + plural(rs.length, "report", "reports"))]));
      body.push(rows);
      if (elsewhere.length) body.push(h("p", {"class": "sc-note"},
        plural(elsewhere.length, "report", "reports") + " here " + (elsewhere.length === 1 ? "is" : "are") +
        " listed under " + (elsewhere.length === 1 ? "its semantic model" : "their semantic models") + " in another workspace."));
    });
    if (body.length) out.push(body);
  } else {
    MODELS.forEach(function (m) { modelRows(m, body, false); });
    if (body.length) out.push(h("h5", null, "Semantic models and their reports"), body);
  }
  var ext = (byModel[""] || []).filter(function (r) { return hit(r.name) || hit(r.external); });
  if (ext.length) {
    out.push(h("h5", null, "Reports on semantic models from other workspaces"));
    ext.forEach(function (r) {
      SCOPE_SHOWN.reports.push(r.key);
      out.push(h("label", {"class": "sc-r sc-x", title: r.rel || r.key}, [box("data-r", r.key, state.scopeReports.has(r.key)),
        icon("nav_report", 14, "k-report"), h("span", null, hlKids(r.name, q)),
        h("span", {"class": "muted"}, hlKids(r.external || "", q))]));
    });
  }
  $("scopeList").classList.toggle("by-space", SPACES.length > 1);
  fill($("scopeList"), out.length ? out : h("p", {"class": "pop-none"}, "Nothing matches “" + state.scopeFind + "”."));
  spBoxes.forEach(function (x) { x[0].indeterminate = x[1]; });
  boxes.forEach(function (x) {                            // a model with only some of its reports
    var on = x[1].filter(function (r) { return state.scopeReports.has(r.key); }).length;
    x[0].indeterminate = x[0].checked && on > 0 && on < x[1].length;
  });
  var searching = !!q;
  $("scopeAll").textContent = searching ? "Select matches" : "Select all";
  $("scopeNone").textContent = searching ? "Clear matches" : "Clear";
  $("scopeCount").textContent = searching
    ? SCOPE_SHOWN.models.length + " of " + MODELS.length + " models, " +
      SCOPE_SHOWN.reports.length + " of " + REPORTS.length + " reports match"
    : scopeLabel();
}
function buildScopePop() {
  if (!$("scopeList")) {                                 // the search box outlives each refill
    fill($("scopePop"), [
      h("div", {"class": "pop-top"}, [
        h("div", {"class": "pop-find"}, [icon("ui_search", 14, "is-muted"),
          h("input", {id: "scopeFind", type: "text", placeholder: "Find a model or report",
                      "aria-label": "Find a semantic model or report", autocomplete: "off", spellcheck: "false"})]),
        h("div", {"class": "pop-head"}, [
          h("button", {"class": "tbtn", id: "scopeAll", "data-sc": "all"}, "Select all"),
          h("button", {"class": "tbtn", id: "scopeNone", "data-sc": "none"}, "Clear"),
          h("button", {"class": "tbtn", id: "scopeSave",
                       title: "Save this scope as JSON, to build just these with trailsbi --include"}, "Save as JSON"),
          h("span", {"class": "muted", id: "scopeCount"})
        ])
      ]),
      h("div", {id: "scopeList"})
    ]);
  }
  $("scopeFind").value = state.scopeFind || "";
  fillScopeList();
}
/* The scope in the shape --include reads, so a scope worked out here can
   become a smaller build. */
function scopeJson() {
  var keep = function (list, set) {
    return list.filter(function (x) { return set.has(x.key); }).map(function (x) { return x.key; });
  };
  return JSON.stringify({models: keep(MODELS, state.scopeModels), reports: keep(REPORTS, state.scopeReports)}, null, 2) + "\n";
}
function syncScope() {
  if (!WORKSPACE) return;
  fill($("scopeBtn"), [icon("ui_scope", 15), h("span", null, "Scope: " + scopeShort()), icon("ui_chev", 14, "chev")]);
  $("scopeBtn").title = "Showing " + scopeLabel();
  $("scopeBtn").classList.toggle("narrowed", !scopeIsAll());
  if (!$("scopePop").hidden) buildScopePop();
}
/* Hide the model and report sections the scope leaves out. */
function applyScopeToDocs() {
  document.querySelectorAll("#modelDoc section.mdl[data-mkey], #mdDiagram .dsec[data-mkey]").forEach(function (sec) {
    sec.classList.toggle("out-scope", !state.scopeModels.has(sec.getAttribute("data-mkey")));
  });
  document.querySelectorAll("#reportDoc section.rep[data-rkey]").forEach(function (sec) {
    var k = sec.getAttribute("data-rkey");
    sec.classList.toggle("out-scope", !!k && !state.scopeReports.has(k));
  });
}
/* quiet: the caller redraws the lineage itself. */
function scopeChanged(quiet) {
  syncScope();
  applyScopeToDocs();
  if (typeof buildHealth === "function") { buildHealth(); buildAI(); }
  wsRender();
  if (quiet) return;
  if (state.focus && !inScope(byId.get(state.focus))) state.focus = null;
  render();
  if (state.focus) showPanel(state.focus); else emptyPanel();
}
function setScopePop(open) {
  if (open) closeMenus("scopePop");
  $("scopePop").hidden = !open;
  $("scopeBtn").setAttribute("aria-expanded", String(open));
  if (!open) return;
  state.scopeFind = "";                                  // each opening starts unfiltered
  buildScopePop();
  $("scopeFind").focus();
}
$("scopeBtn").addEventListener("click", function (e) {
  e.stopPropagation();
  setScopePop($("scopePop").hidden);
});
$("scopePop").addEventListener("click", function (e) {
  e.stopPropagation();
  if (e.target.closest("#scopeSave")) {
    dxDownload((D.meta.name || "workspace").replace(/[\\/:*?"<>|]+/g, "-") + " scope.json",
               new Blob([scopeJson()], {type: "application/json"}));
    toast("Saved. Build just these with:  trailsbi <folder> --include \"<file>\"");
    return;
  }
  var b = e.target.closest("button[data-sc]");
  if (!b) return;
  var all = b.getAttribute("data-sc") === "all";
  if ((state.scopeFind || "").trim()) {                  // searching: only the matches change
    SCOPE_SHOWN.models.forEach(function (k) { if (all) state.scopeModels.add(k); else state.scopeModels.delete(k); });
    SCOPE_SHOWN.reports.forEach(function (k) { if (all) state.scopeReports.add(k); else state.scopeReports.delete(k); });
  } else {
    state.scopeModels = new Set(all ? MODELS.map(function (m) { return m.key; }) : []);
    state.scopeReports = new Set(all ? REPORTS.map(function (r) { return r.key; }) : []);
  }
  scopeChanged();
});
$("scopePop").addEventListener("input", function (e) {
  if (e.target.id !== "scopeFind") return;
  state.scopeFind = e.target.value;
  fillScopeList();
});
$("scopePop").addEventListener("change", function (e) {
  var cb = e.target, mk = cb.getAttribute("data-m"), rk = cb.getAttribute("data-r"), sk = cb.getAttribute("data-s");
  if (sk !== null) {                                     // a whole workspace
    MODELS.forEach(function (m) {
      if (m.space !== sk) return;
      if (cb.checked) state.scopeModels.add(m.key);
      else { state.scopeModels.delete(m.key); reportsOfModel(m.key).forEach(function (r) { state.scopeReports.delete(r.key); }); }
    });
    REPORTS.forEach(function (r) {
      if (r.space !== sk) return;
      if (cb.checked) { state.scopeReports.add(r.key); if (r.model) state.scopeModels.add(r.model); }
      else state.scopeReports.delete(r.key);
    });
  } else if (mk !== null) {
    var rs = reportsOfModel(mk);
    if (cb.checked) { state.scopeModels.add(mk); rs.forEach(function (r) { state.scopeReports.add(r.key); }); }
    else { state.scopeModels.delete(mk); rs.forEach(function (r) { state.scopeReports.delete(r.key); }); }
  } else if (rk !== null) {
    var r = REPORT_BY_KEY.get(rk);
    if (cb.checked) { state.scopeReports.add(rk); if (r && r.model) state.scopeModels.add(r.model); }
    else state.scopeReports.delete(rk);
  }
  scopeChanged();
});
/* Escape drops a search first, then closes the menu. */
$("scopePop").addEventListener("keydown", function (e) {
  if (e.key !== "Escape") return;
  e.stopPropagation();
  if ((state.scopeFind || "") && e.target.id === "scopeFind") {
    state.scopeFind = ""; e.target.value = ""; fillScopeList(); return;
  }
  setScopePop(false);
  $("scopeBtn").focus();
});

/* ----- overview map ----- */
var WS_W = 280, WS_HEAD = 52, WS_FOOT = 26, WS_H = 78, WS_GAP = 14, WS_COL = 90, WS_TOP = 50, WS_PAD = 20;
function applyWsDensity() {
  var compact = state.dense === "compact";
  WS_HEAD = compact ? 34 : 52;
  WS_FOOT = compact ? 0 : 26;
  WS_H = WS_HEAD + WS_FOOT;
  WS_GAP = compact ? 10 : 14;
}
var WSV = {focus: null, pos: new Map(), els: new Map(), edges: [], hits: [], hitIdx: -1};
function wsCardPath(w, hh, r) {
  return "M0,0H" + (w - r) + "A" + r + "," + r + " 0 0 1 " + w + "," + r + "V" + (hh - r) +
         "A" + r + "," + r + " 0 0 1 " + (w - r) + "," + hh + "H0Z";
}
function byLabel(a, b) { return a.label.localeCompare(b.label); }
function wsColumns() {
  var models = ITEMS.filter(function (i) { return i.kind === "model" && itemVisible(i); }).sort(byLabel)
    .concat(ITEMS.filter(function (i) { return i.kind === "external" && itemVisible(i); }).sort(byLabel));
  var readsModel = function (it) {
    return (IIN.get(it.id) || []).some(function (id) {
      var up = ITEM_BY_ID.get(id);
      return up && (up.kind === "model" || up.kind === "external");
    });
  };
  var composite = models.filter(readsModel);
  var base = models.filter(function (m) { return !readsModel(m); });
  var idx = new Map();
  base.forEach(function (m, i) { idx.set(m.id, i); });
  composite.forEach(function (m, i) { idx.set(m.id, base.length + i); });
  function avg(ids) {
    var xs = ids.map(function (id) { return idx.get(id); }).filter(function (x) { return x !== undefined; });
    return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : 1e9;
  }
  var reports = ITEMS.filter(function (i) { return i.kind === "report" && itemVisible(i); })
    .sort(function (a, b) { return avg(IIN.get(a.id)) - avg(IIN.get(b.id)) || byLabel(a, b); });
  var sources = ITEMS.filter(function (i) { return i.kind === "source" && itemVisible(i); })
    .sort(function (a, b) { return avg(IOUT.get(a.id)) - avg(IOUT.get(b.id)) || byLabel(a, b); });
  var cols = [{title: "Data sources", list: sources}, {title: "Semantic models", list: base}];
  if (composite.length) cols.push({title: "Composite models", list: composite});
  cols.push({title: "Reports", list: reports});
  return cols;
}
function itemLine(it) {
  if (it.kind === "source") return it.line || "Data source";
  if (it.kind === "external") return "Semantic model · not in these folders";
  var head = it.space || (it.kind === "model" ? "Semantic model" : "Report");
  if (it.kind === "model") {
    if (it.live) return head + " · live connection";
    var mode = (it.props || []).filter(function (p) { return p[0] === "Storage mode"; })[0];
    return head + (mode && mode[1] && mode[1] !== "—" ? " · " + caps(mode[1]) : "");
  }
  if (it.kind === "report") return it.space ? "Report · " + it.space : "Report";
  return it.line || "";
}
function itemReach(id, adj) {
  var seen = new Set(), st = [id];
  while (st.length) (adj.get(st.pop()) || []).forEach(function (y) { if (!seen.has(y)) { seen.add(y); st.push(y); } });
  seen.delete(id);
  return seen.size;
}
function wsPair(ic, num, cls, x, tip) {
  return sg("g", {"class": "cnt " + cls}, [
    iconG(ic, {"class": "cnt-ic", transform: "translate(" + x + "," + (WS_HEAD + 6) + ") scale(" + (12 / 24) + ")"}),
    sg("text", {"class": "cnt-n", x: x + 15, y: WS_HEAD + 15}, num),
    sg("title", null, tip)
  ]);
}
function wsCountRow(it, rightEdge) {
  var up = itemReach(it.id, IIN), down = itemReach(it.id, IOUT);
  var x = 14, out = [];
  out.push(wsPair("ui_up", String(up), "tot" + (up ? "" : " zero"), x, plural(up, "item feeds", "items feed") + " this, directly or further back"));
  x += 25 + String(up).length * 6.6;
  out.push(wsPair("ui_down", String(down), "tot" + (down ? "" : " zero"), x, plural(down, "item depends", "items depend") + " on this, directly or further on"));
  x += 25 + String(down).length * 6.6;
  var counts = it.counts || [];
  if (counts.length) {
    var need = 8 + counts.reduce(function (t, c) { return t + 25 + c[2].toLocaleString("en-US").length * 6.6; }, 0);
    if (x + need <= rightEdge) {                         // the per-kind counts only when they all fit
      out.push(sg("path", {"class": "vdiv", d: "M" + (x - 3) + "," + WS_HEAD + "V" + WS_H}));
      x += 8;
      counts.forEach(function (c) {
        var num = c[2].toLocaleString("en-US");
        out.push(wsPair(c[0], num, "t-" + c[1] + (c[2] ? "" : " zero"), x, c[3]));
        x += 25 + num.length * 6.6;
      });
    }
  }
  return out;
}
function itemActions(it) {
  var acts = [];
  // the lineage only when something of this item's is on it
  var onMap = it.kind === "model" || it.kind === "report"
           || (it.kind === "source" && (it.mkeys || []).length > 0)
           || (it.kind === "external" && (it.reports || []).length > 0);
  if (onMap) acts.push(["lineage", "nav_lineage", "Open in Lineage"]);
  if (it.kind === "model") acts.push(["model", "nav_model", "Show in Model"]);
  if (it.kind === "report") acts.push(["pages", "nav_report", "Show the report pages"]);
  return acts;
}
function runItemAction(act, it) {
  if (!it) return;
  if (act === "lineage") openInLineage(it);
  if (act === "model") {
    if (!state.scopeModels.has(it.key)) { state.scopeModels.add(it.key); scopeChanged(); }
    switchTab("model");
    if (state.mdMode !== "list") setModelMode("list");
    var sec = $("mod-" + it.key);
    if (sec) sec.scrollIntoView({block: "start"});
  }
  if (act === "pages") {
    if (!state.scopeReports.has(it.key)) {
      state.scopeReports.add(it.key);
      if (it.model) state.scopeModels.add(it.model);
      scopeChanged();
    }
    switchTab("report");
    showPage(it.key, null, true);
  }
}
function wsActs(it, y) {
  var acts = itemActions(it), x = WS_W - 6, els = [];
  acts.slice().reverse().forEach(function (a) {
    x -= 22;
    els.push(sg("g", {"class": "act", "data-act": a[0], "data-item": it.id, tabindex: 0, role: "button",
                      "aria-label": a[2] + ": " + (it.name || it.label), transform: "translate(" + x + "," + y + ")"}, [
      sg("rect", {width: 22, height: 22, rx: 4}),
      iconG(a[1], {"class": "aic", transform: "translate(4,4) scale(" + (14 / 24) + ")"}),
      sg("title", null, a[2])
    ]));
    x -= 2;
  });
  return {els: els, left: acts.length ? x - 4 : WS_W - 10};
}
function wsTip(it) {
  var unused = it.kind === "model" && !(it.reports || []).length;
  return KIND_NAME[it.kind] + ": " + (it.name || it.label) + (it.space ? "\nWorkspace: " + it.space : "") + (it.rel ? "\n" + it.rel : "") + (it.line ? "\n" + it.line : "") +
         (it.missing ? "\n" + plural(it.missing, "field", "fields") + " missing from its semantic model" : "") +
         (unused ? "\nNo report in this folder uses it" : "");
}
function wsCard(it, p) {
  var name = it.name || it.label, kids = [], flag = [], flagW = 0;
  kids.push(sg("path", {"class": "box", d: wsCardPath(WS_W, WS_H, 5)}), sg("rect", {"class": "bar", width: 4, height: WS_H}));
  if (state.dense === "compact") {
    var ca = wsActs(it, (WS_H - 22) / 2);
    kids.push(iconG(it.icon || "db", {"class": "ico", transform: "translate(12," + ((WS_H - 18) / 2) + ") scale(" + (18 / 24) + ")"}),
              cardText("t1", 38, WS_H / 2 + 4, Math.max(40, ca.left - 38 - (it.missing ? 20 : 0)), name));
    if (it.missing) kids.push(iconG("missing", {"class": "fic", transform: "translate(" + (ca.left - 16) + "," + ((WS_H - 14) / 2) + ") scale(" + (14 / 24) + ")"}));
    kids.push(ca.els);
  } else {
    if (it.missing) {
      var txt = it.missing + " missing";
      flagW = 22 + txt.length * 6.4;
      flag = [iconG("missing", {"class": "fic", transform: "translate(" + (WS_W - flagW) + ",10) scale(.55)"}),
              sg("text", {"class": "flag", x: WS_W - flagW + 16, y: 21}, txt)];
    } else if (it.kind === "model" && !(it.reports || []).length) {
      flagW = 70;
      flag = [sg("text", {"class": "flag soft", x: WS_W - 64, y: 21}, "No reports")];
    }
    var acts = wsActs(it, WS_HEAD + 2);
    kids.push(iconG(it.icon || "db", {"class": "ico", transform: "translate(14," + ((WS_HEAD - 20) / 2) + ") scale(" + (20 / 24) + ")"}),
              cardText("t1", CARD_TEXT_X, 22, WS_W - CARD_TEXT_X - 12 - flagW, name),
              cardText("t2", CARD_TEXT_X, 39, WS_W - CARD_TEXT_X - 10, itemLine(it)),
              flag,
              sg("path", {"class": "divider", d: "M4," + WS_HEAD + "H" + WS_W}),
              wsCountRow(it, acts.left), acts.els);
  }
  kids.push(sg("title", null, wsTip(it)));
  var g = sg("g", {"class": "wi k-" + it.kind, transform: "translate(" + p.x + "," + p.y + ")", tabindex: 0, role: "button",
                   "aria-label": KIND_NAME[it.kind] + ": " + name}, kids);
  g.__id = it.id;
  return g;
}
function wsRender() {
  if (!WORKSPACE) return;
  applyWsDensity();
  var cols = wsColumns(), maxY = 0, ROW = WS_H + WS_GAP;
  WSV.pos = new Map();
  function colX(ci) { return WS_PAD + ci * (WS_W + WS_COL); }
  // The topmost placed neighbour: the row a card lines up with (Infinity if none).
  function anchorY(ids) {
    var best = Infinity;
    (ids || []).forEach(function (id) { var q = WSV.pos.get(id); if (q) best = Math.min(best, q.y); });
    return best;
  }
  var fromIn = function (id) { return IIN.get(id); };
  cols[0].list.forEach(function (it, i) {                 // data sources start the layout
    WSV.pos.set(it.id, {x: colX(0), y: WS_TOP + i * ROW});
    maxY = Math.max(maxY, WS_TOP + i * ROW + WS_H);
  });
  cols.slice(1).forEach(function (col, i) {               // each later column lines up with what feeds it
    col.list.sort(function (a, b) {
      var ya = anchorY(fromIn(a.id)), yb = anchorY(fromIn(b.id));
      if (ya !== yb) return ya === Infinity ? 1 : yb === Infinity ? -1 : ya - yb;
      return ((a.kind === "external" ? 1 : 0) - (b.kind === "external" ? 1 : 0)) || byLabel(a, b);
    });
    var x = colX(i + 1), next = WS_TOP;
    col.list.forEach(function (it) {
      var a = anchorY(fromIn(it.id));
      var y = a === Infinity ? next : Math.max(next, a);
      WSV.pos.set(it.id, {x: x, y: y});
      next = y + ROW;
      maxY = Math.max(maxY, y + WS_H);
    });
  });
  var heads = cols.map(function (col, ci) {
    return sg("text", {"class": "colhead", x: colX(ci), y: 26}, [col.title + " ", sg("tspan", {"class": "cnt"}, String(col.list.length))]);
  });
  var edges = [], edgeEls = [];
  (D.itemEdges || []).forEach(function (e) {
    var a = WSV.pos.get(e[0]), b = WSV.pos.get(e[1]);
    if (!a || !b) return;
    var x1 = a.x + WS_W, y1 = a.y + WS_H / 2, x2 = b.x, y2 = b.y + WS_H / 2, mx = (x1 + x2) / 2;
    var el = sg("path", {"class": "e", d: "M" + x1 + "," + y1 + " C" + mx + "," + y1 + " " + mx + "," + y2 + " " + x2 + "," + y2});
    edgeEls.push(el);
    edges.push({a: e[0], b: e[1], el: el});
  });
  WSV.els = new Map();
  var cards = [];
  cols.forEach(function (col) {
    col.list.forEach(function (it) {
      var g = wsCard(it, WSV.pos.get(it.id));
      WSV.els.set(it.id, g);
      cards.push(g);
    });
  });
  var n = cols.length, empty = !cards.length;
  var width = WS_PAD * 2 + n * WS_W + (n - 1) * WS_COL, height = Math.max(maxY, empty ? WS_TOP + 40 : 0) + WS_PAD;
  var svgEl = $("wsSvg");
  svgEl.setAttribute("viewBox", "0 0 " + width + " " + height);
  svgEl.setAttribute("width", width);
  svgEl.setAttribute("height", height);
  fill(svgEl, [heads, sg("g", null, edgeEls), sg("g", null, cards),
               empty ? sg("text", {"class": "ws-none", x: WS_PAD, y: WS_TOP + 20},
                          state.wsPick.size ? "Nothing of these kinds in the scope." : "Nothing in scope. Use Scope above to pick semantic models and reports.") : null]);
  WSV.edges = edges;
  wsFitText();
  if (WSV.focus && !WSV.els.has(WSV.focus) && !ITEM_BY_ID.has(WSV.focus)) WSV.focus = null;
  wsApplyFocus();
  wsApplySearch();
}
function wsFitText() { if (typeof fitCardLines === "function") fitCardLines($("wsSvg")); }
function wsLineage(id) {
  function walk(adj) {
    var seen = new Set(), st = [id];
    while (st.length) (adj.get(st.pop()) || []).forEach(function (y) { if (!seen.has(y)) { seen.add(y); st.push(y); } });
    seen.delete(id);
    return seen;
  }
  return {up: walk(IIN), down: walk(IOUT)};
}
function wsApplyFocus() {
  var svgEl = $("wsSvg");
  svgEl.classList.toggle("focusing", !!WSV.focus);
  WSV.els.forEach(function (el) { el.classList.remove("up", "down", "focus"); });
  WSV.edges.forEach(function (e) { e.el.classList.remove("lit", "upe", "downe", "direct"); });
  if (!WSV.focus) return;
  var lin = wsLineage(WSV.focus);
  lin.up.forEach(function (id) { var el = WSV.els.get(id); if (el) el.classList.add("up"); });
  lin.down.forEach(function (id) { var el = WSV.els.get(id); if (el) el.classList.add("down"); });
  var focused = WSV.els.get(WSV.focus);                   // may be filtered off the map
  if (focused) focused.classList.add("focus");
  var up = new Set(lin.up), down = new Set(lin.down);
  up.add(WSV.focus); down.add(WSV.focus);
  var later = [];
  WSV.edges.forEach(function (e) {
    var dir = up.has(e.a) && up.has(e.b) ? "upe" : down.has(e.a) && down.has(e.b) ? "downe" : null;
    if (!dir) return;
    e.el.classList.add("lit", dir);
    if (e.a === WSV.focus || e.b === WSV.focus) { e.el.classList.add("direct"); later.push(e.el); }
  });
  later.forEach(function (el) { el.parentNode.appendChild(el); });   // direct links on top
}
function wsFocus(id, scroll) {
  if (id && !ITEM_BY_ID.has(id)) return;
  WSV.focus = id;
  wsApplyFocus();
  wsShowPanel(id);
  if (scroll) {
    var p = WSV.pos.get(id), cv = $("wsCanvas");
    if (p && cv.scrollTo) cv.scrollTo({left: Math.max(0, p.x - cv.clientWidth / 3), top: Math.max(0, p.y - cv.clientHeight / 2)});
  }
}
function wsClear() { WSV.focus = null; wsApplyFocus(); wsEmptyPanel(); }
function openItem(id) {
  if (!ITEM_BY_ID.has(id)) return;
  var it = ITEM_BY_ID.get(id);
  if (!itemInScope(it)) {                                 // bring it into scope so it is on the map
    if (it.kind === "model") state.scopeModels.add(it.key);
    if (it.kind === "report") { state.scopeReports.add(it.key); if (it.model) state.scopeModels.add(it.model); }
    if (it.kind === "source") (it.mkeys || []).forEach(function (k) { state.scopeModels.add(k); });
    if (it.kind === "external") (it.reports || []).forEach(function (k) { state.scopeReports.add(k); });
    scopeChanged();
  }
  if (state.wsPick.size && !state.wsPick.has(wsKind(it))) { state.wsPick.clear(); syncWsTypes(); wsRender(); }
  switchTab("ws");
  wsFocus(id, true);
}

/* ----- details pane ----- */
function itemCard(id) {
  var it = ITEM_BY_ID.get(id);
  if (!it) return null;
  return h("a", {"class": "card fcard k-" + it.kind, "data-item": id, href: "#", title: (it.name || it.label) + " · " + itemLine(it)}, [
    h("span", {"class": "bar"}), icon(it.icon || "db", 16, "k-" + it.kind),
    h("span", {"class": "fname"}, it.name || it.label), h("small", null, itemLine(it))
  ]);
}
function itemList(title, ids, hint) {
  ids = (ids || []).slice().sort(function (a, b) {
    var x = ITEM_BY_ID.get(a), y = ITEM_BY_ID.get(b);
    return (x ? x.label : a).localeCompare(y ? y.label : b);
  });
  return [paneHead(title, ids.length),
          ids.length ? h("div", {"class": "pcards"}, ids.map(itemCard)) : h("div", {"class": "muted"}, hint)];
}
function wsShowPanel(id) {
  var it = ITEM_BY_ID.get(id);
  if (!it) { wsEmptyPanel(); return; }
  var out = [];
  out.push(h("span", {"class": "badge k-" + it.kind}, KIND_NAME[it.kind]));
  out.push(h("h2", null, [icon(it.icon || "db", 22, "k-" + it.kind), h("span", null, it.name || it.label)]));
  if (it.missing) out.push(h("div", {"class": "warn"}, plural(it.missing, "field", "fields") + " used in this report " +
                             (it.missing === 1 ? "is" : "are") + " missing from its semantic model. See Health."));
  if (it.kind === "model" && !(it.reports || []).length)
    out.push(h("div", {"class": "warn"}, "No report in this folder uses this semantic model."));
  if (!itemInScope(it))
    out.push(h("div", {"class": "note"}, "Out of scope: the other views leave it out until you add it under Scope."));
  if (it.props && it.props.length)
    out.push(h("table", {"class": "kv"}, it.props.map(function (p) { return h("tr", null, [h("th", null, p[0]), h("td", null, p[1])]); })));
  if (it.kind === "source") out.push(itemList("Read by semantic models", IOUT.get(id), "None"));
  if (it.kind === "model" || it.kind === "external") {
    var up = IIN.get(id) || [];
    if (it.kind === "model" || up.length) out.push(itemList("Reads from", up, it.live ? "A live connection: the data sources are in the published model." : "No data sources found in its Power Query code."));
    out.push(itemList("Used by", IOUT.get(id), "No reports in this folder."));
  }
  if (it.kind === "report") out.push(itemList("Semantic model", IIN.get(id), "Unknown"));
  fill($("wsPanel"), out);
  $("wsPanel").scrollTop = 0;
  $("wsRailItem").textContent = "· " + trunc(it.name || it.label, 40);
}
function wsEmptyPanel() {
  var counts = {source: 0, model: 0, external: 0, report: 0};
  ITEMS.forEach(function (i) { counts[i.kind] = (counts[i.kind] || 0) + 1; });
  var missing = ITEMS.reduce(function (a, i) { return a + (i.missing || 0); }, 0);
  var unused = ITEMS.filter(function (i) { return i.kind === "model" && !(i.reports || []).length; }).length;
  var out = [];
  if (!scopeIsAll()) out.push(h("div", {"class": "note"}, ["Showing " + scopeLabel() + ". Use ", h("b", null, "Scope"),
    " above to add or remove semantic models and reports."]));
  out.push(h("div", {"class": "empty"}, [h("b", null, "Select a data source, semantic model or report."),
    "Its connections light up and this pane lists its details. The buttons on each card open it in Lineage, Model or the report pages."]));
  out.push(h("table", {"class": "kv"}, [
    h("tr", null, [h("th", null, "Data sources"), h("td", null, String(counts.source))]),
    h("tr", null, [h("th", null, "Semantic models"), h("td", null, counts.model + (counts.external ? " (+" + counts.external + " from other workspaces)" : ""))]),
    h("tr", null, [h("th", null, "Reports"), h("td", null, String(counts.report))]),
    h("tr", null, [h("th", null, "Models without reports"), h("td", null, String(unused))]),
    h("tr", null, [h("th", null, "Missing fields"), h("td", null, String(missing))])
  ]));
  var legend = [];
  [["db", "k-source", "Data source (the icon shows the connector)"], ["ws_model", "k-model", "Semantic model"],
   ["ws_model", "k-model", "Semantic model from another workspace (dashed card)"], ["nav_report", "k-report", "Report"],
   ["missing", "is-bad", "Report uses fields missing from its model"]]
    .forEach(function (x) { legend.push(icon(x[0], 18, x[1]), h("span", null, x[2])); });
  out.push(h("div", {"class": "legend"}, legend));
  fill($("wsPanel"), out);
  $("wsRailItem").textContent = "";
}
function openInLineage(it) {
  var ms = new Set(), rs = new Set(), focus = null;
  if (it.kind === "model") { ms.add(it.key); reportsOfModel(it.key).forEach(function (r) { rs.add(r.key); }); }
  if (it.kind === "report") { rs.add(it.key); if (it.model) ms.add(it.model); }
  if (it.kind === "source") {
    (it.mkeys || []).forEach(function (k) { ms.add(k); reportsOfModel(k).forEach(function (r) { rs.add(r.key); }); });
    focus = it.id;
  }
  if (it.kind === "external") (IOUT.get(it.id) || []).forEach(function (id) {
    var r = ITEM_BY_ID.get(id);
    if (r && r.kind === "report") rs.add(r.key);
    if (r && r.kind === "model") ms.add(r.key);
  });
  state.scopeModels = ms;
  state.scopeReports = rs;
  state.focus = null;
  scopeChanged(true);
  switchTab("graph");
  render();
  if (focus && byId.has(focus)) focusNode(focus, true);
  else { emptyPanel(); var cv = $("canvas"); if (cv.scrollTo) cv.scrollTo({left: 0, top: 0}); }
}

/* ----- events ----- */
function wsAct(el) {
  clearSearch();
  runItemAction(el.getAttribute("data-act"), ITEM_BY_ID.get(el.getAttribute("data-item")));
}
$("wsSvg").addEventListener("click", function (e) {
  e.stopPropagation();
  var a = e.target.closest("g.act");
  if (a) { wsAct(a); return; }
  var g = e.target.closest("g.wi");
  if (g) wsFocus(g.__id, false); else wsClear();
});
$("wsSvg").addEventListener("keydown", function (e) {
  if (e.key !== "Enter" && e.key !== " ") return;
  var a = e.target.closest && e.target.closest("g.act");
  if (a) { e.preventDefault(); wsAct(a); return; }
  var g = e.target.closest && e.target.closest("g.wi");
  if (g) { e.preventDefault(); wsFocus(g.__id, false); }
});
document.addEventListener("click", function (e) {
  var a = e.target.closest && e.target.closest("a[data-item]");
  if (a) { e.preventDefault(); openItem(a.getAttribute("data-item")); }
});
document.addEventListener("keydown", function (e) {
  if (e.key !== "Escape" || openTab() !== "ws" || !WSV.focus) return;
  var t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
  wsClear();
});
function wsApplySearch() {
  var q = state.query || "";
  WSV.hits = [];
  WSV.hitIdx = -1;
  WSV.els.forEach(function (el, id) {
    var it = ITEM_BY_ID.get(id);
    var m = !!q && ((it.name || "") + "\n" + it.label).toLowerCase().indexOf(q) >= 0;
    el.classList.toggle("match", m);
    if (m) WSV.hits.push(id);
  });
  $("wsSvg").classList.toggle("searching", !!q);
  if (typeof updateSearchUi === "function") updateSearchUi();
}

/* ----- start ----- */
if (WORKSPACE) {
  document.querySelector('.rail button[data-tab="ws"]').hidden = false;
  syncWsTypes();
  syncScope();
}
