/* ---------- panel ---------- */
function link(id) {
  var n = byId.get(id); if (!n) return esc(id);
  return '<a data-go="' + esc(id) + '"' + (n.broken ? ' class="bad"' : '') + '>' +
         icon(iconName(n), 14, typeCls(n)) + esc(n.label) + '</a>' +
         (n.table && n.type !== "table" ? ' <span class="muted">' + esc(n.table) + '</span>' : '');
}

/* Details pane entries use the same one-line cards as the Reports filters. */
function panelCard(id, note) {
  var n = byId.get(id);
  if (!n) return "";
  var sub = n.table ? n.table
          : n.type === "visual" ? (n.page || "") : n.type === "page" ? (n.report || "") : "";
  return '<a class="card fcard ' + typeCls(n) + '" data-go="' + esc(id) + '" title="' +
         esc(n.label + (sub ? " · " + sub : "") + (n.broken ? "\nMissing from its semantic model" : "")) + '"><span class="bar"></span>' +
         icon(iconName(n), 16, typeCls(n)) + '<span class="fname' + (n.hidden ? ' hid' : '') + '">' + esc(n.label) + '</span>' +
         (note ? '<small class="fnote">' + note + '</small>' : '') + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</a>';
}
function relCard(text) {
  var m = /^(.*?) \((\w+)\) → (.*?) \((\w+)\)$/.exec(text);
  var name = m ? m[1] + " → " + m[3] : text, sub = m ? m[2] + " → " + m[4] : "";
  return '<div class="card fcard" style="--c:var(--model)" title="' + esc(text) + '"><span class="bar"></span>' + icon("relationship", 16) +
         '<span class="fname">' + esc(name) + '</span>' + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</div>';
}
function lineageList(title, set, hint, headIcon) {
  var groups = {};
  set.forEach(function (id) { var m = byId.get(id); (groups[m.type] = groups[m.type] || []).push(m); });
  var h = '<h3><span>' + (headIcon ? icon(headIcon, 15, "is-muted") + " " : "") + title +
          '</span><span class="muted count">' + set.size + '</span></h3>';
  if (!set.size) return h + '<div class="muted">' + hint + '</div>';
  TYPES.forEach(function (t) {
    var arr = groups[t.k]; if (!arr) return;
    arr.sort(function (a, b) { return a.label.localeCompare(b.label); });
    h += '<details' + (arr.length <= 15 ? ' open' : '') + '><summary>' + t.label + ' (' + arr.length + ')</summary><div class="pcards">' +
         arr.map(function (m) {
           return panelCard(m.id, isVisible(m) ? "" : '<span title="Hidden by the current view options">not on the map</span>');
         }).join("") + '</div></details>';
  });
  return h;
}

function showPanel(id) {
  var n = byId.get(id), d = n.detail || {}, lin = lineage(id), h = "";
  h += '<span class="badge t-' + n.type + (n.sub ? ' s-' + n.sub : '') + '">' + esc(kindName(n)) + '</span>';
  h += '<h2>' + icon(iconName(n), 22, typeCls(n)) + '<span>' + esc(n.name || n.label) + '</span></h2>';
  if (n.hidden || n.relkey || n.filtered)
    h += '<div class="muted" style="font-size:13px;display:flex;gap:12px;flex-wrap:wrap;margin-top:4px">' +
         markers(n).filter(function (x) { return x[0] !== "missing"; }).map(function (x) {
           return '<span>' + icon(x[0], 14, "is-muted") + ' ' + x[1] + '</span>';
         }).join("") + '</div>';
  if (n.broken) h += '<div class="warn">The report uses this field, but the semantic model has no ' + esc(n.type) + ' with this name. Rename it back or update the visuals.</div>';
  if (n.type !== "visual" && n.type !== "page" && !n.broken && n.used === false)
    h += '<div class="warn">Nothing in the report depends on this ' + esc(n.type) + '.</div>';
  if (d.note) h += '<div class="note">' + esc(d.note) + '</div>';
  if (d.props && d.props.length)
    h += '<table class="kv">' + d.props.map(function (p) {
      return '<tr><th>' + esc(p[0]) + '</th><td>' + esc(p[1]) + '</td></tr>';
    }).join("") + '</table>';
  if (d.fields && d.fields.length) {
    h += '<h3><span>Fields used</span><span class="muted count">' + d.fields.length + '</span></h3><div class="pcards pfields">';
    var byRole = {};
    d.fields.forEach(function (f) { (byRole[f.role] = byRole[f.role] || []).push(f.id); });
    Object.keys(byRole).forEach(function (r) {
      h += '<div class="prole">' + esc(r) + '</div>' + byRole[r].map(function (fid) { return panelCard(fid); }).join("");
    });
    h += '</div>';
  }
  if (d.steps && d.steps.length) {
    h += '<h3><span>Applied steps</span><span class="muted count">' + d.steps.length + '</span></h3><ol class="steps">';
    d.steps.forEach(function (s) {
      h += '<li><details><summary><b>' + esc(s.label) + '</b> <span class="muted">' + esc(s.name) + '</span></summary><pre>' + esc(s.code) + '</pre></details></li>';
    });
    h += '</ol>';
  }
  (d.code || []).forEach(function (c, i) {
    if (!c.text) return;
    h += '<details' + (i === 0 && !(d.steps && d.steps.length) ? ' open' : '') + '><summary>' + esc(c.title) + '</summary><pre>' + esc(c.text) + '</pre></details>';
  });
  (d.lists || []).forEach(function (l) {
    h += '<h3><span>' + esc(l.title) + '</span><span class="muted count">' + l.items.length + '</span></h3><div class="pcards">' +
         l.items.map(function (x) { return l.title === "Relationships" ? relCard(x) : '<div class="muted">' + esc(x) + '</div>'; }).join("") +
         '</div>';
  });
  h += lineageList("Upstream: what feeds it", lin.up, "Nothing. This is a starting point.", "ui_up");
  h += lineageList("Downstream: what depends on it", lin.down, "Nothing depends on this.", "ui_down");
  $("panel").innerHTML = h;
  $("panel").scrollTop = 0;
  setRailItem(n.name || n.label);
}

function emptyPanel() {
  var h = '<div class="empty"><b>Select any item to trace it.</b>Its upstream chain lights up in navy and everything that depends on it in teal. The side panel lists the full chain, the M steps and the DAX.</div><div class="legend">';
  [["parameter","t-query","Parameter"],["query","t-query","Power Query query"],
   ["db","t-source","Data source (icon shows the connector)"],["table","t-table","Table"],
   ["calctable","t-table s-calculated","Calculated table"],["fieldparam","t-table","Field parameter"],
   ["column","t-column","Data column"],
   ["calccolumn","t-column s-calculated","Calculated column"],["measure","t-measure","Measure"],
   ["calcitem","t-measure","Calculation item"],["v_column","t-visual","Visual (icon shows the visual type)"],
   ["page","t-page","Page"],["allpages","t-page","Report-level filters"],
   ["h","","Lines when an item is selected"],
   ["line","trace-up:1.8:1","Feeds the selected item directly"],
   ["line","trace-up:1.1:.6","Feeds it through other items"],
   ["line","trace-down:1.8:1","Uses the selected item directly"],
   ["line","trace-down:1.1:.6","Uses it through other items"],
   ["h","","Markers"],
   ["missing","is-bad","Missing from the model"],["hidden","is-muted","Hidden"],
   ["key","is-muted","Relationship key"],["filter","is-muted","Used as a filter"]]
    .forEach(function (x) {
      if (x[0] === "h") { h += '<h4>' + x[2] + '</h4>'; return; }
      if (x[0] === "line") {
        var ln = x[1].split(":");
        h += '<svg width="18" height="10" aria-hidden="true"><path d="M1 5H17" stroke="var(--' + ln[0] +
             ')" stroke-width="' + ln[1] + '" opacity="' + ln[2] + '" stroke-linecap="round"/></svg>';
      } else h += icon(x[0], 18, x[1]);
      h += '<span>' + x[2] + '</span>';
    });
  h += '</div>';
  h += '<p class="muted" style="margin-top:18px;font-size:13px">Each item sits to the right of everything it uses, so arrows always point left to right. The first column holds data sources and the queries or parameters that depend on nothing; visuals and pages are always the last two columns.</p>';
  if (D.meta.warnings && D.meta.warnings.length)
    h += '<h3><span>Notes from the scan</span></h3><ul class="links">' + D.meta.warnings.map(function (w) { return '<li>' + esc(w) + '</li>'; }).join("") + '</ul>';
  $("panel").innerHTML = h;
  setRailItem("");
}

