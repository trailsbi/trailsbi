/* ---------- Model view: a light, ordered outline of the TMDL ----------
   Every object in the definition, in TMDL order, nested as in the file:
   name, type, key / hidden markers, and buttons for lineage and DAX / M. */
var MKINDS = [
  {k: "table", label: "Tables", icon: "table", c: "var(--table)", of: ["table"]},
  {k: "column", label: "Columns", icon: "column", c: "var(--column)", of: ["column"]},
  {k: "measure", label: "Measures", icon: "measure", c: "var(--measure)", of: ["measure", "calculationItem"]},
  {k: "hierarchy", label: "Hierarchies", icon: "v_tree", c: "var(--table)", of: ["hierarchy", "level"]},
  {k: "partition", label: "Partitions", icon: "query", c: "var(--query)", of: ["partition"]},
  {k: "relationship", label: "Relationships", icon: "relationship", c: "var(--model)", of: ["relationship"]},
  {k: "expression", label: "Parameters and expressions", icon: "parameter", c: "var(--query)",
   of: ["expression", "dataSource", "function", "queryGroup"]},
  {k: "role", label: "Roles and permissions", icon: "key", c: "var(--page)",
   of: ["role", "tablePermission", "columnPermission", "roleMembership"]},
  {k: "annotation", label: "Annotations", icon: "o_text", c: "var(--page)",
   of: ["annotation", "extendedProperty", "changedProperty"]},
  {k: "other", label: "Model, cultures and perspectives", icon: "nav_model", c: "var(--page)", of: []}
];
var MKIND_OF = {};
MKINDS.forEach(function (g) { g.of.forEach(function (k) { MKIND_OF[k] = g.k; }); });
function mGroup(k) { return MKIND_OF[k] || "other"; }
/* Kinds the Model view leaves out: parameters and expressions, annotations,
   and model / culture / perspective entries. */
var MSKIP = {expression: 1, annotation: 1, other: 1};
function mShown(it) { return !MSKIP[mGroup(it.k)] && (state.mdShowAuto || !it.auto); }
function mIcon(it) {
  switch (it.k) {
    case "table": return /field parameter/.test(it.t) ? "fieldparam" : /calculation group/.test(it.t) ? "calcitem"
                       : /calculated/.test(it.t) ? "calctable" : "table";
    case "column": return /calculated/.test(it.t) ? "calccolumn" : "column";
    case "measure": return "measure";
    case "calculationItem": return "calcitem";
    case "hierarchy": return "v_tree";
    case "level": return "column";
    case "partition": return it.l === "DAX" ? "calctable" : "query";
    case "relationship": return "relationship";
    case "expression": return it.t === "parameter" ? "parameter" : "query";
    case "role": return "key";
    case "tablePermission": case "columnPermission": return "filter";
    case "cultureInfo": return "web";
    case "annotation": case "extendedProperty": case "changedProperty": return "o_text";
    case "database": case "dataSource": return "db";
    case "model": return "nav_model";
    default: return /^perspective/.test(it.k) ? "ui_eye" : "v_generic";
  }
}
function mColor(it) {
  if (it.k === "column" && /calculated/.test(it.t)) return "var(--calc)";
  if (it.k === "table" && /calculated/.test(it.t)) return "var(--calc)";
  var g = mGroup(it.k);
  for (var i = 0; i < MKINDS.length; i++) if (MKINDS[i].k === g) return MKINDS[i].c;
  return "var(--page)";
}
state.mdPick = new Set();
state.mdShowAuto = false;                               // Power BI's hidden date tables
state.mdShowRel = false;
state.mdShowRoles = false;
state.mdHoverActions = true;
function mHiddenKind(g) { return (g === "relationship" && !state.mdShowRel) || (g === "role" && !state.mdShowRoles); }

/* Inside a table: partitions, columns, calculated columns, hierarchies, then measures.
   A table with one partition carries its expression itself instead of a partition card. */
function mChildRank(it) {
  if (it.k === "partition") return 0;
  if (it.k === "column") return /calculated/.test(it.t) ? 2 : 1;
  if (it.k === "hierarchy") return 3;
  if (it.k === "measure") return 4;
  if (it.k === "calculationItem") return 5;
  return 6;
}
function mTableLabel(tbl, kids) {
  var parts = kids.filter(function (g) { return g[0].k === "partition"; }).length;
  var cols = kids.filter(function (g) { return g[0].k === "column"; }).length;
  var meas = kids.filter(function (g) { return g[0].k === "measure"; }).length;
  var bits = String(tbl.t).split(" · ");                 // e.g. "table", "import"
  var type = bits[0], mode = bits[1] ? bits[1].charAt(0).toUpperCase() + bits[1].slice(1) : "";
  return [type, mode, parts > 1 ? plural(parts, "partition", "partitions") : "",
          plural(cols, "column", "columns"), plural(meas, "measure", "measures")].filter(Boolean).join(" · ");
}
function mArrange(list) {
  var out = [], i = 0;
  while (i < list.length) {
    var it = list[i];
    if (it.k !== "table") { out.push(it); i++; continue; }
    var j = i + 1, kids = [];
    while (j < list.length && list[j].d > it.d) {
      var start = j, head = list[j];
      j++;
      while (j < list.length && list[j].d > head.d) j++;
      kids.push(list.slice(start, j));
    }
    var tbl = Object.assign({}, it), parts = kids.filter(function (g) { return g[0].k === "partition"; });
    tbl.t = mTableLabel(it, kids);
    tbl.table = true;
    if (parts.length === 1) {                             // one partition: its expression lives on the table card
      if (parts[0][0].x) { tbl.x = parts[0][0].x; tbl.l = parts[0][0].l; }
      kids = kids.filter(function (g) { return g[0].k !== "partition"; });
    }
    out.push(tbl);
    kids.map(function (g, idx) { return {g: g, idx: idx, r: mChildRank(g[0])}; })
        .sort(function (a, b) { return a.r - b.r || a.idx - b.idx; })
        .forEach(function (x) { Array.prototype.push.apply(out, x.g); });
    i = j;
  }
  return out;
}

/* A live-connected semantic model: the folder holds a connection, not a model.
   Shown with the same cards as the outline so the page reads consistently. */
function liveBlock(m) {
  var L = m.live;
  var h = '<p class="note">This semantic model is a live connection. Its tables, columns and ' +
          'measures are defined in the model it points at, so the project has nothing to list ' +
          'here beyond the connection itself.</p>';
  h += '<div class="mrow card" data-info="1" data-p="-1" style="--c:var(--source)"><span class="bar"></span>' +
       '<span class="mtw-sp"></span>' + icon(L.icon || "db", 16) +
       '<span class="mn">' + esc(L.database || L.server) + '</span>' +
       '<span class="mt">' + esc(L.connector) + '</span><span class="macts">' +
       (m.liveId ? '<button class="mlin" data-go-id="' + esc(m.liveId) +
                   '" title="Show in lineage" aria-label="Show this connection in the lineage map">' +
                   icon("nav_lineage", 14) + '</button>' : '') +
       '</span></div>';
  [[L.server.indexOf("://") > 0 ? "cloud" : "db", L.server, "Server"],
   ["db", L.database, "Database"], ["table", L.cube, "Perspective"],
   ["relationship", L.typeLabel, "Connection type"]]
    .forEach(function (r) {
      if (!r[1]) return;
      h += '<div class="mrow card" data-info="1" data-p="-1" style="--c:var(--rule);margin-left:24px"><span class="bar"></span>' +
           '<span class="mtw-sp"></span>' + icon(r[0], 16) +
           '<span class="mn">' + esc(r[1]) + '</span><span class="mt">' + esc(r[2]) + '</span></div>';
    });
  return h;
}

function modelBlock(m) {
  var out = mArrange((m.outline || []).filter(mShown)), cnt = {table: 0, column: 0, measure: 0};
  out.forEach(function (it) { if (cnt[it.k] !== undefined) cnt[it.k]++; });
  var h = '<section class="rep mdl" id="mod-' + esc(m.key) + '" data-mkey="' + esc(m.key) + '">' +
          '<button class="rep-h" aria-expanded="true" title="Click to collapse this semantic model">' +
          icon("ws_model", 20, "k-model") + esc(m.name) + '<span class="muted">' +
          (m.live ? esc(m.live.typeLabel)
                  : [plural(cnt.table, "table", "tables"), plural(cnt.column, "column", "columns"),
                     plural(cnt.measure, "measure", "measures")].join(" · ")) +
          '</span><span class="rep-chev"></span></button><div class="mbody">';
  if (!out.length && m.live) return h + liveBlock(m) + '</div></section>';
  if (!out.length) return h + '<p class="muted">No objects could be read from this semantic model.</p></div></section>';
  var stack = [];
  out.forEach(function (it, i) {
    while (stack.length && out[stack[stack.length - 1]].d >= it.d) stack.pop();
    it._p = stack.length ? stack[stack.length - 1] : -1;
    it._kids = 0;
    if (it._p >= 0) out[it._p]._kids++;
    stack.push(i);
  });
  out.forEach(function (it, i) {
    var node = it.id ? byId.get(it.id) : null;
    var isKey = it.key || (node && node.relkey);
    var hidden = it.h || (node && node.hidden);
    var open = !(it._kids && it.d === 0 && it.k !== "model");      // top-level objects start closed
    h += '<div class="mrow card" data-i="' + i + '" data-p="' + it._p + '" data-g="' + mGroup(it.k) + '"' +
         (it.id ? ' data-id="' + esc(it.id) + '"' : '') + (it._kids ? ' data-open="' + (open ? 1 : 0) + '"' : '') +
         ' style="--c:' + mColor(it) + ';margin-left:' + (it.d * 24) + 'px">' +
         '<span class="bar"></span>' +
         (it._kids ? '<button class="mtw" aria-label="Show or hide contents"></button>' : '<span class="mtw-sp"></span>') +
         icon(mIcon(it), 16) +
         '<span class="mn' + (hidden ? ' hid' : '') + '">' + esc(it.n) + '</span>' +
         '<span class="mt">' + esc(it.t) + '</span>' +
         (isKey ? '<span class="mk" title="Key">' + icon("key", 14) + '</span>' : '') +
         (hidden ? '<span class="mk" title="Hidden">' + icon("hidden", 14) + '</span>' : '') +
         (it._kids && !it.table ? '<span class="mcount">' + it._kids + '</span>' : '') +
         '<span class="macts">' +
         (function () {
           var e = it.id ? issuesFor(it.id) : null;
           if (!e) return "";
           var meta = ' data-id="' + esc(it.id) + '" data-label="' + esc(it.n) + '" data-kind="' + esc(it.k) +
                      '" data-table="' + esc(it.tb || "") + '"';
           return (e.h ? '<button class="mhealth" data-issue="health"' + meta + ' title="' +
                         esc(plural(e.h, "health finding", "health findings")) + '">' + e.h + icon("nav_health", 14) + '</button>' : '') +
                  (e.a ? '<button class="mhealth" data-issue="ai"' + meta + ' title="' +
                         esc(plural(e.a, "AI readiness finding", "AI readiness findings")) + '">' + e.a + icon("nav_ai", 14) + '</button>' : '');
         })() +
         (it.x ? '<button class="mcodebtn" title="Show the ' + it.l + ' expression">' + it.l + '</button>' : '') +
         (it.id ? '<button class="mlin" data-go-id="' + esc(it.id) + '" title="Show in lineage" aria-label="Show ' +
                  esc(it.n) + ' in the lineage map">' + icon("nav_lineage", 14) + '</button>' : '') +
         '</span></div>' +
         (it.x ? '<pre class="mcode" data-i="' + i + '" hidden style="margin-left:' + (it.d * 24) + 'px">' + esc(it.x) + '</pre>' : '');
  });
  return h + '</div></section>';
}
function buildModel() {
  var h = "";
  if (!MODELS.length) {
    var ext = REPORTS.length && REPORTS[0].external;
    h = '<p class="muted">' + (ext ? "The report connects live to the published semantic model <b>" + esc(ext) +
        "</b>, so its tables are not in this project. The lineage shows the fields the report uses."
        : "No semantic model was found in this project.") + '</p>';
  }
  (D.meta.models || []).forEach(function (m) { h += modelBlock(m); });
  $("modelDoc").innerHTML = h;
  applyModelView();
}
/* Which rows show: kind filter and search show matches with their parents;
   otherwise the tree's open / closed state decides. */
var MHITS = [];
/* Index of a row's parent, or -1 at the top. Parsed strictly: a missing
   data-p must not read as row 0, which would loop for ever. */
function mParent(r) {
  var v = r && r.getAttribute("data-p");
  var n = v === null || v === "" ? NaN : parseInt(v, 10);
  return n >= 0 ? n : -1;
}
/* One model's rows, measured once and kept on the section. A large model holds
   thousands of rows, so re-reading each row's name and hunting for its DAX
   block on every keystroke would make searching feel like a hang. */
function mdRows(sec) {
  var c = sec.__mrows;
  if (c) return c;
  var rows = Array.prototype.slice.call(sec.querySelectorAll(".mrow:not([data-info])"));
  var codes = {};
  sec.querySelectorAll("pre.mcode[data-i]").forEach(function (e) { codes[e.getAttribute("data-i")] = e; });
  c = sec.__mrows = {
    rows: rows,
    name: rows.map(function (r) { return r.querySelector(".mn"); }),
    kind: rows.map(function (r) { return r.getAttribute("data-g"); }),
    parent: rows.map(mParent),
    code: rows.map(function (_, i) { return codes[i] || null; }),
    text: rows.map(function (r) {
      var n = r.querySelector(".mn"), t = r.querySelector(".mt");
      return ((n ? n.textContent : "") + " " + (t ? t.textContent : "")).toLowerCase();
    })
  };
  return c;
}
function applyModelView() {
  var q = (state.query || "").toLowerCase(), picks = state.mdPick, filtering = !!q || picks.size > 0;
  MHITS = [];
  $("modelDoc").querySelectorAll("section.mdl").forEach(function (sec) {
    var c = mdRows(sec), rows = c.rows;
    var show = new Array(rows.length).fill(false), ctx = new Array(rows.length).fill(false), any = false;
    var blocked = c.kind.map(mHiddenKind);
    rows.forEach(function (r, i) {
      clearMarks(r);
      if (!filtering || blocked[i]) return;
      var okKind = !picks.size || picks.has(c.kind[i]);
      var okText = !q || c.text[i].indexOf(q) >= 0;
      if (okKind && okText) {
        show[i] = true; any = true; MHITS.push(r);
        for (var p = c.parent[i]; p >= 0; p = c.parent[p]) { if (!show[p]) ctx[p] = true; }
      }
    });
    rows.forEach(function (r, i) {
      var vis;
      if (blocked[i]) vis = false;
      else if (filtering) vis = show[i] || ctx[i];
      else {
        vis = true;
        for (var p = c.parent[i]; p >= 0; p = c.parent[p])
          if (rows[p].getAttribute("data-open") === "0") { vis = false; break; }
      }
      r.hidden = !vis;
      r.classList.toggle("ctx", filtering && ctx[i] && !show[i]);
      if (q && show[i]) markText(c.name[i], q);
      if (c.code[i] && !vis) c.code[i].hidden = true;
    });
    sec.hidden = filtering && !any;
    if (filtering && any) sec.classList.remove("collapsed");
  });
  if (typeof updateSearchUi === "function") updateSearchUi();
}
/* Kind filter in the toolbar, working like the one on the lineage map. */
var mdBox = $("mdTypes");
var mdAll = document.createElement("button");
mdAll.className = "t-all"; mdAll.textContent = "All"; mdAll.title = "All object kinds";
mdAll.addEventListener("click", function () { if (!state.mdPick.size) return; state.mdPick.clear(); syncMdTypes(); applyModelView(); });
mdBox.appendChild(mdAll);
var PRESENT = new Set();
(D.meta.models || []).forEach(function (m) {
  (m.outline || []).forEach(function (it) { if (!MSKIP[mGroup(it.k)]) PRESENT.add(mGroup(it.k)); });
});
MKINDS.forEach(function (g) {
  if (!PRESENT.has(g.k)) return;
  var b = document.createElement("button");
  b.dataset.k = g.k; b.title = g.label; b.setAttribute("aria-label", g.label);
  b.style.setProperty("--c", g.c);
  b.innerHTML = '<span style="display:flex;color:' + g.c + '">' + icon(g.icon, 16) + '</span>';
  b.addEventListener("click", function () {
    if (state.mdPick.has(g.k)) state.mdPick.delete(g.k); else state.mdPick.add(g.k);
    syncMdTypes(); applyModelView();
  });
  mdBox.appendChild(b);
});
function syncMdTypes() {
  mdBox.querySelectorAll("button[data-k]").forEach(function (b) {
    b.hidden = mHiddenKind(b.dataset.k);
    if (b.hidden) state.mdPick.delete(b.dataset.k);
  });
  var picking = state.mdPick.size > 0;
  mdAll.classList.toggle("picked", !picking);
  mdBox.querySelectorAll("button[data-k]").forEach(function (b) {
    var on = state.mdPick.has(b.dataset.k);
    b.classList.toggle("picked", on);
    b.classList.toggle("dim", picking && !on);
    b.setAttribute("aria-pressed", String(on));
  });
}
function syncMdView() {
  $("mdShowAuto").checked = state.mdShowAuto;
  var listOnly = state.mdMode !== "diagram";
  $("mdViewPop").querySelectorAll("label.mdlist").forEach(function (l) { l.hidden = !listOnly; });
  $("mdShowRel").checked = state.mdShowRel;
  $("mdShowRoles").checked = state.mdShowRoles;
  $("mdHoverActions").checked = state.mdHoverActions;
  document.body.classList.toggle("show-actions", !state.mdHoverActions);
  var changed = (state.mdShowAuto ? 1 : 0) + (listOnly ? (state.mdShowRel ? 1 : 0) +
                (state.mdShowRoles ? 1 : 0) + (state.mdHoverActions ? 0 : 1) : 0);
  $("mdViewBtn").innerHTML = icon("ui_eye", 15) + '<span>View options</span><span class="vcount">' + (changed || "") + '</span>' +
                             icon("ui_chev", 14, "chev");
}
$("mdViewBtn").addEventListener("click", function (e) {
  e.stopPropagation();
  var open = $("mdViewPop").hidden;
  closeMenus("mdViewPop");
  $("mdViewPop").hidden = !open;
  $("mdViewBtn").setAttribute("aria-expanded", String(open));
});
$("mdViewPop").addEventListener("click", function (e) { e.stopPropagation(); });
/* Auto date tables change the outline itself, so the page is rebuilt rather
   than just re-filtered: the header counts and the tree have to follow. */
$("mdShowAuto").addEventListener("change", function (e) {
  state.mdShowAuto = e.target.checked; syncMdView(); buildModel(); buildDiagram();
});
$("mdShowRel").addEventListener("change", function (e) { state.mdShowRel = e.target.checked; syncMdView(); syncMdTypes(); applyModelView(); });
$("mdShowRoles").addEventListener("change", function (e) { state.mdShowRoles = e.target.checked; syncMdView(); syncMdTypes(); applyModelView(); });
$("mdHoverActions").addEventListener("change", function (e) { state.mdHoverActions = e.target.checked; syncMdView(); });
syncMdView();
syncMdTypes();
$("modelDoc").addEventListener("click", function (e) {
  var t = e.target;
  var iss = t.closest && t.closest("[data-issue]");
  if (iss) {
    e.stopPropagation();
    state.issueEntity = {id: iss.getAttribute("data-id"), label: iss.getAttribute("data-label"),
                         kind: iss.getAttribute("data-kind"), table: iss.getAttribute("data-table")};
    switchTab(iss.getAttribute("data-issue") === "ai" ? "ai" : "health");
    buildHealth();
    buildAI();
    return;
  }
  var lin = t.closest && t.closest(".mlin");
  if (lin) { e.stopPropagation(); go(lin.getAttribute("data-go-id")); return; }
  var cb = t.closest && t.closest(".mcodebtn");
  if (cb) {
    var row = cb.closest(".mrow"), pre = row.nextElementSibling;
    if (pre && pre.classList.contains("mcode")) { pre.hidden = !pre.hidden; cb.classList.toggle("on", !pre.hidden); }
    return;
  }
  var head = t.closest && t.closest(".rep-h");
  if (head) {
    var sec = head.closest("section.mdl"), closed = sec.classList.toggle("collapsed");
    head.setAttribute("aria-expanded", String(!closed));
    return;
  }
  var r = t.closest && t.closest(".mrow[data-open]");
  if (r) {
    r.setAttribute("data-open", r.getAttribute("data-open") === "1" ? "0" : "1");
    applyModelView();
  }
});
