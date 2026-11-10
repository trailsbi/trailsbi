/* ---------- panel ---------- */
/* Details pane entries use the same one-line cards as the Reports filters.
   note is optional text or a node shown before the card's second line. */
function panelCard(id, note) {
  var n = byId.get(id);
  if (!n) return null;
  var sub = n.table ? n.table
          : n.type === "visual" ? (n.page || "") : n.type === "page" ? (n.report || "") : "";
  return h("a", {"class": "card fcard " + typeCls(n), "data-go": id,
                 title: n.label + (sub ? " · " + sub : "") + (n.broken ? "\nMissing from its semantic model" : "")}, [
    h("span", {"class": "bar"}), icon(iconName(n), 16, typeCls(n)),
    h("span", {"class": "fname" + (n.hidden ? " hid" : "")}, n.label),
    note ? h("small", {"class": "fnote"}, note) : null,
    sub ? h("small", null, sub) : null
  ]);
}
function relCard(text) {
  var m = /^(.*?) \((\w+)\) → (.*?) \((\w+)\)$/.exec(text);
  var name = m ? m[1] + " → " + m[3] : text, sub = m ? m[2] + " → " + m[4] : "";
  return h("div", {"class": "card fcard", style: "--c:var(--model)", title: text}, [
    h("span", {"class": "bar"}), icon("relationship", 16),
    h("span", {"class": "fname"}, name), sub ? h("small", null, sub) : null
  ]);
}
/* A pane heading: optional icon, title, and a count on the right. */
function paneHead(title, count, headIcon) {
  return h("h3", null, [
    h("span", null, [headIcon ? [icon(headIcon, 15, "is-muted"), " "] : null, title]),
    count === undefined ? null : h("span", {"class": "muted count"}, count)
  ]);
}
/* A code block: DAX or Power Query, with function help where the page has it. */
function codeBlock(text, lang, attrs) {
  return h("pre", Object.assign({"data-lang": lang || null}, attrs || {}), codeKids(text, lang));
}
function lineageList(title, set, hint, headIcon) {
  var groups = {}, out = [paneHead(title, set.size, headIcon)];
  set.forEach(function (id) { var m = byId.get(id); (groups[m.type] = groups[m.type] || []).push(m); });
  if (!set.size) return out.concat(h("div", {"class": "muted"}, hint));
  TYPES.forEach(function (t) {
    var arr = groups[t.k]; if (!arr) return;
    arr.sort(function (a, b) { return a.label.localeCompare(b.label); });
    out.push(h("details", {open: arr.length <= 15}, [
      h("summary", null, t.label + " (" + arr.length + ")"),
      h("div", {"class": "pcards"}, arr.map(function (m) {
        return panelCard(m.id, isVisible(m) ? "" : h("span", {title: "Hidden by the current view options"}, "not on the map"));
      }))
    ]));
  });
  return out;
}

function showPanel(id) {
  var n = byId.get(id), d = n.detail || {}, lin = lineage(id), out = [];
  out.push(h("span", {"class": "badge t-" + n.type + (n.sub ? " s-" + n.sub : "")}, kindName(n)));
  out.push(h("h2", null, [icon(iconName(n), 22, typeCls(n)), h("span", null, n.name || n.label)]));
  if (n.hidden || n.relkey || n.filtered)
    out.push(h("div", {"class": "muted pmarks"},
      markers(n).filter(function (x) { return x[0] !== "missing"; }).map(function (x) {
        return h("span", null, [icon(x[0], 14, "is-muted"), " " + x[1]]);
      })));
  if (n.broken) out.push(h("div", {"class": "warn"}, "The report uses this field, but the semantic model has no " + n.type +
                                                     " with this name. Rename it back or update the visuals."));
  if (n.type !== "visual" && n.type !== "page" && !n.broken && n.used === false)
    out.push(h("div", {"class": "warn"}, "Nothing in the report depends on this " + kindName(n).toLowerCase() + "."));
  if (d.note) out.push(h("div", {"class": "note"}, d.note));
  if (d.props && d.props.length)
    out.push(h("table", {"class": "kv"}, d.props.map(function (p) {
      return h("tr", null, [h("th", null, p[0]), h("td", null, p[1])]);
    })));
  if (d.fields && d.fields.length) {
    var byRole = {}, cards = [];
    d.fields.forEach(function (f) { (byRole[f.role] = byRole[f.role] || []).push(f.id); });
    Object.keys(byRole).forEach(function (r) {
      cards.push(h("div", {"class": "prole"}, r), byRole[r].map(function (fid) { return panelCard(fid); }));
    });
    out.push(paneHead("Fields used", d.fields.length), h("div", {"class": "pcards pfields"}, cards));
  }
  if (d.steps && d.steps.length) {
    out.push(paneHead("Applied steps", d.steps.length), h("ol", {"class": "steps"}, d.steps.map(function (s) {
      return h("li", null, h("details", null, [
        h("summary", null, [h("b", null, s.label), " ", h("span", {"class": "muted"}, s.name)]),
        codeBlock(s.code, "m")
      ]));
    })));
  }
  (d.code || []).forEach(function (c, i) {
    if (!c.text) return;
    out.push(h("details", {open: i === 0 && !(d.steps && d.steps.length)}, [
      h("summary", null, c.title), codeBlock(c.text, codeLang(c.title))
    ]));
  });
  (d.links || []).forEach(function (l) {
    out.push(paneHead(l.title, l.ids.length), h("div", {"class": "pcards"},
      l.ids.length ? l.ids.map(function (x) { return panelCard(x); }) : h("div", {"class": "muted"}, "None found in the report.")));
  });
  (d.lists || []).forEach(function (l) {
    out.push(paneHead(l.title, l.items.length), h("div", {"class": "pcards"}, l.items.map(function (x) {
      return l.title === "Relationships" ? relCard(x) : h("div", {"class": "muted"}, x);
    })));
  });
  out.push(lineageList("Upstream: what feeds it", lin.up, "Nothing. This is a starting point.", "ui_up"));
  out.push(lineageList("Downstream: what depends on it", lin.down, "Nothing depends on this.", "ui_down"));
  fill($("panel"), out);
  $("panel").scrollTop = 0;
  setRailItem(n.name || n.label);
}

var LEGEND = [
  ["parameter", "t-query", "Parameter"], ["query", "t-query", "Power Query query"],
  ["db", "t-source", "Data source (icon shows the connector)"], ["table", "t-table", "Table"],
  ["calctable", "t-table s-calculated", "Calculated table"], ["fieldparam", "t-table", "Field parameter"],
  ["column", "t-column", "Data column"],
  ["calccolumn", "t-column s-calculated", "Calculated column"], ["measure", "t-measure", "Measure"],
  ["rmeasure", "t-measure s-report", "Report measure (defined in the report, not the model)"],
  ["calcgroup", "t-calcgroup", "Calculation group"], ["calcitem", "t-calcgroup", "Calculation item"],
  ["v_column", "t-visual", "Visual (icon shows the visual type)"],
  ["page", "t-page", "Page"], ["allpages", "t-page", "Report-level filters"],
  ["h", "", "Lines when an item is selected"],
  ["line", "trace-up:1.8:1", "Feeds the selected item directly"],
  ["line", "trace-up:1.1:.6", "Feeds it through other items"],
  ["line", "trace-down:1.8:1", "Uses the selected item directly"],
  ["line", "trace-down:1.1:.6", "Uses it through other items"],
  ["h", "", "Markers"],
  ["missing", "is-bad", "Missing from the model"], ["hidden", "is-muted", "Hidden"],
  ["key", "is-muted", "Relationship key"], ["filter", "is-muted", "Used as a filter"]
];
function emptyPanel() {
  var legend = [];
  LEGEND.forEach(function (x) {
    if (x[0] === "h") { legend.push(h("h4", null, x[2])); return; }
    if (x[0] === "line") {
      var ln = x[1].split(":");
      legend.push(sg("svg", {width: 18, height: 10, "aria-hidden": "true"},
        sg("path", {d: "M1 5H17", stroke: "var(--" + ln[0] + ")", "stroke-width": ln[1], opacity: ln[2], "stroke-linecap": "round"})));
    } else legend.push(icon(x[0], 18, x[1]));
    legend.push(h("span", null, x[2]));
  });
  var out = [
    WORKSPACE && !scopeIsAll() ? h("div", {"class": "note"}, ["Showing " + scopeLabel() + ". Use ", h("b", null, "Scope"),
      " above the map to add or remove semantic models and reports."]) : null,
    h("div", {"class": "empty"}, [h("b", null, "Select any item to trace it."),
      "Its upstream chain lights up in navy and everything that depends on it in teal. The side panel lists the full chain, the M steps and the DAX."]),
    h("div", {"class": "legend"}, legend),
    h("p", {"class": "muted pnote"}, "Each item sits to the right of everything it uses, so arrows always point left to right. " +
      "The first column holds data sources and the queries or parameters that depend on nothing; visuals and pages are always the last two columns.")
  ];
  if (D.meta.warnings && D.meta.warnings.length)
    out.push(paneHead("Notes from the scan"), h("ul", {"class": "links"}, D.meta.warnings.map(function (w) { return h("li", null, w); })));
  fill($("panel"), out);
  setRailItem("");
}
