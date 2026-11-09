/* ---------- Health: Best Practice Analyzer rules plus lineage checks ---------- */
var HCATS = ["Error Prevention", "Performance", "DAX Expressions", "Maintenance", "Naming Conventions", "Formatting"];
var ISSUES = {};                                        // node id -> {h: n, a: n}
(function () {
  var add = function (list, key) {
    (list || []).forEach(function (r) {
      r.items.forEach(function (it) {
        if (!it.id) return;
        var e = ISSUES[it.id] || (ISSUES[it.id] = {h: 0, a: 0});
        e[key]++;
      });
    });
  };
  add(D.health, "h");
  add(D.ai, "a");
})();
function issuesFor(id) { return ISSUES[id] || null; }
var KIND_WORD = {table: "table", column: "column", measure: "measure", partition: "partition", hierarchy: "hierarchy",
                 level: "level", calculationItem: "calculation item", relationship: "relationship", role: "role",
                 expression: "query", tablePermission: "table permission", model: "semantic model"};
function entityWhere(e) {
  var word = KIND_WORD[e.kind] || e.kind || "";
  if (e.kind === "column" && /calculated/.test(e.kind)) word = "calculated column";
  return word + (e.table ? " in table " + e.table : "");
}
state.issueEntity = null;                               // {id, label} when filtered from the Model view
var HSEV = {3: {k: "error", label: "Error", c: "var(--bad)"}, 2: {k: "warning", label: "Warning", c: "#b7791f"},
            1: {k: "info", label: "Info", c: "var(--table)"}};
var HKIND_ICON = {relationship: "relationship", model: "ws_model", role: "key", partition: "query",
                  tablePermission: "filter", perspective: "ui_eye", dataSource: "db", calculationItem: "calcitem",
                  hierarchy: "v_tree", table: "table", column: "column", measure: "measure"};
state.hSev = new Set();
function healthCard(it) {
  var note = it.note || "";
  var own = !it.kind || it.kind === "table" || it.kind === "column" || it.kind === "measure" || it.kind === "calculationItem";
  if (it.id && byId.has(it.id) && own) return panelCard(it.id, note);
  var sub = [it.kind === "tablePermission" ? "table permission on " + it.table : it.table, note].filter(Boolean).join(" · ");
  var linked = it.id && byId.has(it.id);
  return h(linked ? "a" : "div", {"class": "card fcard", style: "--c:var(--page)", "data-go": linked ? it.id : null,
                                  title: it.label + (sub ? " · " + sub : "")}, [
    h("span", {"class": "bar"}), icon(HKIND_ICON[it.kind] || "v_generic", 16),
    h("span", {"class": "fname"}, it.label), sub ? h("small", null, sub) : null
  ]);
}
function healthRule(r) {
  var sev = HSEV[r.severity], n = r.items.length, LIMIT = 100;
  return h("details", {"class": "hrule sev-" + sev.k, "data-sev": r.severity}, [
    h("summary", {"class": "card", style: "--c:" + sev.c}, [
      h("span", {"class": "bar"}), h("span", {"class": "hbadge"}, sev.label), h("span", {"class": "hname"}, r.name),
      r.source === "lineage" ? h("span", {"class": "hsrc", title: "Check from this tool, not the BPA rule set"}, "lineage check") : null,
      h("span", {"class": "hcnt"}, n)
    ]),
    h("div", {"class": "hbody"}, [
      h("p", {"class": "muted"}, r.desc),
      h("div", {"class": "pcards"}, [
        r.items.slice(0, LIMIT).map(healthCard),
        n > LIMIT ? h("p", {"class": "muted"}, "… and " + (n - LIMIT) + " more.") : null
      ])
    ])
  ]);
}
function syncFilterBar() {
  var bar = $("filterBar"), e = state.issueEntity, tab = openTab();
  var show = !!e && (tab === "health" || tab === "ai");
  bar.hidden = !show;
  fill(bar, show ? [
    h("span", null, ["Showing findings for ", h("b", null, e.label),
                     e.kind ? [" ", h("span", {"class": "muted"}, entityWhere(e))] : null]),
    h("button", {"class": "hclear"}, "Clear")
  ] : null);
}
function syncRailFilter() {
  var on = !!state.issueEntity;
  document.querySelectorAll('.rail button[data-tab="health"] .rail-filter, .rail button[data-tab="ai"] .rail-filter')
    .forEach(function (el) {
      el.hidden = !on;
      el.title = on ? "Filtered to " + state.issueEntity.label : "";
    });
}
function ruleItemsInView(r) {
  return r.items.filter(function (it) {
    if (state.issueEntity && it.id !== state.issueEntity.id) return false;
    return true;
  });
}
function buildRuleView(docId, rules, cats, sevSet, withScore) {
  rules = rules.filter(function (r) { return r.checked; }).map(function (r) {
    var kept = ruleItemsInView(r);
    return kept.length === r.items.length ? r : Object.assign({}, r, {items: kept});
  });
  var tally = {1: 0, 2: 0, 3: 0}, passed = 0, checked = 0;
  rules.forEach(function (r) {
    tally[r.severity] += r.items.length;
    checked++;
    if (!r.items.length) passed++;
  });
  var cols = (withScore ? 1 : 0) + 3 + (state.issueEntity ? 0 : 1);
  var stats = [];
  if (withScore) {
    var score = checked ? Math.round(100 * passed / checked) : 0;
    var sc = score >= 75 ? "var(--column)" : score >= 50 ? "#b7791f" : "var(--bad)";
    stats.push(h("div", {"class": "hstat card plain", style: "--c:" + sc, title: "Share of checked rules with no findings"},
      [h("span", {"class": "bar"}), h("b", null, score + "%"), h("small", null, "readiness score")]));
  }
  [[3, "error"], [2, "warning"], [1, "info"]].forEach(function (x) {
    var sv = HSEV[x[0]], n = tally[x[0]];
    stats.push(h("button", {"class": "hstat card" + (sevSet.has(x[0]) ? " on" : ""), "data-sev": x[0], style: "--c:" + sv.c},
      [h("span", {"class": "bar"}), h("b", null, n), h("small", null, x[1] + (x[0] === 1 || n === 1 ? "" : "s"))]));
  });
  if (!state.issueEntity)
    stats.push(h("div", {"class": "hstat card plain", style: "--c:var(--column)"},
      [h("span", {"class": "bar"}), h("b", null, passed), h("small", null, "rule" + (passed === 1 ? "" : "s") + " passed")]));
  var out = [h("div", {"class": "hstats", style: "grid-template-columns:repeat(" + cols + ",minmax(0,1fr))"}, stats)];
  cats.forEach(function (cat) {
    var inCat = rules.filter(function (r) { return r.category === cat; });
    if (!inCat.length) return;
    var failing = inCat.filter(function (r) { return r.items.length && (!sevSet.size || sevSet.has(r.severity)); })
                       .sort(function (a, b) { return b.severity - a.severity || b.items.length - a.items.length; });
    var ok = inCat.filter(function (r) { return !r.items.length; });
    var filtering = !!state.issueEntity || sevSet.size > 0;
    if (filtering && !failing.length) return;                 // only show what matches
    var counts = {1: 0, 2: 0, 3: 0};
    failing.forEach(function (r) { counts[r.severity] += r.items.length; });
    out.push(h("section", {"class": "rep hcat"}, [
      h("button", {"class": "rep-h", "aria-expanded": "true"}, [
        cat,
        h("span", {"class": "muted"}, [3, 2, 1].filter(function (k) { return counts[k]; }).map(function (k) {
          return counts[k] + " " + HSEV[k].label.toLowerCase() + (counts[k] === 1 || k === 1 ? "" : "s");
        }).concat(failing.length ? [] : ["no findings"]).join(" · ")),
        h("span", {"class": "rep-chev"})
      ]),
      h("div", {"class": "hbodywrap"}, [
        failing.map(healthRule),
        ok.length && !filtering ? h("details", {"class": "hpass"}, [
          h("summary", null, ok.length + " rule" + (ok.length === 1 ? "" : "s") + " passed"),
          h("ul", null, ok.map(function (r) { return h("li", null, [h("span", {"class": "hok"}, "✓"), r.name]); }))
        ]) : null
      ])
    ]));
  });
  fill($(docId), out);
  syncRailFilter();
  syncFilterBar();
}
function buildHealth() {
  buildRuleView("healthDoc", D.health || [], HCATS, state.hSev, false);
}
var AICATS = ["Foundation", "Naming", "Descriptions", "Prep data for AI", "What AI can see"];
state.aiSev = new Set();
function buildAI() {
  var ai = D.ai || [];
  // With no semantic model in the project, only the report measures are checked: no score.
  var modelChecked = ai.some(function (r) { return r.checked && r.id !== "AI_REPORT_MEASURES"; });
  buildRuleView("aiDoc", ai, AICATS, state.aiSev, modelChecked);
  if (!modelChecked && ai.some(function (r) { return r.checked; }))
    $("aiDoc").insertBefore(h("p", {"class": "muted pnote"}, "The semantic model is not in this project, so only the " +
      "measures the reports add were checked. Scan the model's project too for a readiness score."), $("aiDoc").firstChild);
}
function ruleViewClick(sevSet, rebuild) { return function (e) {
  if (e.target.closest && e.target.closest(".hclear")) {
    state.issueEntity = null;
    buildHealth();
    buildAI();
    return;
  }
  var st = e.target.closest && e.target.closest("button.hstat");
  if (st) {
    var k = +st.getAttribute("data-sev");
    if (sevSet.has(k)) sevSet.delete(k); else sevSet.add(k);
    rebuild();
    return;
  }
  var head = e.target.closest && e.target.closest(".hcat > .rep-h");
  if (head) {
    var sec = head.closest("section"), closed = sec.classList.toggle("collapsed");
    head.setAttribute("aria-expanded", String(!closed));
  }
}; }
$("filterBar").addEventListener("click", function (e) {
  if (e.target.closest && e.target.closest(".hclear")) {
    state.issueEntity = null;
    buildHealth();
    buildAI();
  }
});
$("healthDoc").addEventListener("click", ruleViewClick(state.hSev, function () { buildHealth(); }));
$("aiDoc").addEventListener("click", ruleViewClick(state.aiSev, function () { buildAI(); }));

