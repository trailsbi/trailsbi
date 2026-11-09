/* ---------- layout ----------
   Columns are dependency depth, not object type:
   - Column 1 holds the starting points: data sources, plus queries and
     parameters that depend on nothing.
   - Every other item sits one column to the right of the deepest item it
     uses, so every arrow points left to right.
   - Items with no inputs that are not starting points (a constant measure,
     a DAX table like CALENDARAUTO()) move right, next to what uses them.
   - Visuals and pages are always the last two columns.
   Inside a column, items stack in type blocks (sources, queries, tables,
   columns, measures) and are ordered to reduce crossing lines. */
var TERMINAL = {visual: true, page: true};
var BLOCK_GAP = 0, SWEEPS = 4;

// Stacking order of blocks inside a column (top to bottom).
var BLOCK_ORDER = ["parameter", "source", "query", "table", "calcgroup", "column", "measure", "calcitem", "visual", "page"];
function blockRank(n) {
  return BLOCK_ORDER.indexOf(n.type === "query" && n.sub === "parameter" ? "parameter" : n.type);
}

function groupLabel(n) {
  return baseGroupLabel(n);
}
function baseGroupLabel(n) {
  switch (n.type) {
    case "source":  return n.sub || "Data sources";
    case "query":   return n.sub === "parameter" ? "Parameters" : "Queries";
    case "table":   return "Tables";
    case "column":  return "Columns · " + (n.table || "");
    case "measure": return n.sub === "report" ? "Report measures · " + (n.reportname || "")
                                              : "Measures · " + (n.table || "");
    case "calcgroup": return "Calculation groups";
    case "calcitem": return "Calculation items · " + (n.table || "");
    case "visual":  return n.page || "Visuals";
    default:        return "";
  }
}

function assignColumns(vis, visSet) {
  var succ = new Map(), pred = new Map();
  vis.forEach(function (n) { succ.set(n.id, []); pred.set(n.id, []); });
  D.edges.forEach(function (e) {
    if (visSet.has(e[0]) && visSet.has(e[1])) { succ.get(e[0]).push(e[1]); pred.get(e[1]).push(e[0]); }
  });
  var middle = vis.filter(function (n) { return !TERMINAL[n.type]; });
  function isRoot(n) {
    return n.type === "source" || (n.type === "query" && pred.get(n.id).length === 0);
  }
  function middlePreds(id) {
    return pred.get(id).filter(function (p) { return !TERMINAL[byId.get(p).type]; });
  }
  function middleSuccs(id) {
    return succ.get(id).filter(function (y) { return !TERMINAL[byId.get(y).type]; });
  }
  var anyRoot = middle.some(isRoot);

  // 1) Earliest column (longest path from the left). Starting points use
  //    column 0; other items with no inputs start at column 1, or 0 when no
  //    starting point is visible. This alone already keeps every arrow forward.
  var early = new Map(), onStack = new Set();
  function earliest(id) {
    if (early.has(id)) return early.get(id);
    if (onStack.has(id)) return 0;                       // cycle guard
    onStack.add(id);
    var n = byId.get(id), ps = middlePreds(id);
    var d = isRoot(n) ? 0 : (ps.length ? 0 : (anyRoot ? 1 : 0));
    ps.forEach(function (p) { d = Math.max(d, earliest(p) + 1); });
    onStack.delete(id);
    early.set(id, d);
    return d;
  }
  middle.forEach(function (n) { earliest(n.id); });
  var lastEarly = 0;
  early.forEach(function (d) { lastEarly = Math.max(lastEarly, d); });

  // 2) Items not fed by a starting point may move right, next to what uses
  //    them, but never left of their earliest column. Consumers are settled
  //    first (reverse topological order), so a moved item never passes an
  //    item it feeds.
  var rooted = new Set(), stack = [];
  middle.forEach(function (n) { if (isRoot(n)) { rooted.add(n.id); stack.push(n.id); } });
  while (stack.length) {
    middleSuccs(stack.pop()).forEach(function (y) {
      if (!rooted.has(y)) { rooted.add(y); stack.push(y); }
    });
  }
  var col = new Map();
  rooted.forEach(function (id) { col.set(id, early.get(id)); });

  var seen = new Set(), order = [];
  function visit(id) {
    if (seen.has(id)) return;
    seen.add(id);
    middleSuccs(id).forEach(function (y) { if (!rooted.has(y)) visit(y); });
    order.push(id);
  }
  middle.forEach(function (n) { if (!rooted.has(n.id)) visit(n.id); });
  order.forEach(function (id) {
    var n = byId.get(id), lower = early.get(id);
    var ms = middleSuccs(id), best = Infinity;
    ms.forEach(function (y) { if (col.has(y)) best = Math.min(best, col.get(y) - 1); });
    var target;
    if (best !== Infinity) target = best;
    else if (succ.get(id).length) target = lastEarly;          // feeds only visuals/pages
    else {
      var home = n.table ? col.get("t:" + n.table) : undefined;
      target = home !== undefined ? home + 1 : lower;          // feeds nothing
    }
    col.set(id, Math.max(lower, target));
  });

  // 3) Visuals and pages always take the last two columns.
  var last = 0;
  col.forEach(function (d) { last = Math.max(last, d); });
  vis.forEach(function (n) {
    if (n.type === "visual") col.set(n.id, last + 1);
    else if (n.type === "page") col.set(n.id, last + 2);
  });
  return {col: col, succ: succ, pred: pred};
}

function layout() {
  var vis = D.nodes.filter(isVisible);
  var visSet = new Set(vis.map(function (n) { return n.id; }));
  var A = assignColumns(vis, visSet);

  // Compact: drop empty column numbers.
  var used = Array.from(new Set(A.col.values())).sort(function (a, b) { return a - b; });
  var idx = new Map(used.map(function (c, i) { return [c, i]; }));
  var cols = used.map(function () { return []; });
  vis.forEach(function (n) { cols[idx.get(A.col.get(n.id))].push(n); });

  function initialKey(n) {
    return [blockRank(n), TERMINAL[n.type] ? n.order || 0 : 0,
            groupLabel(n).toLowerCase(), n.type === "visual" ? n.pos || 0 : 0, n.label.toLowerCase()];
  }
  function cmp(a, b) {
    for (var i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
  }
  cols.forEach(function (list) {
    list.sort(function (a, b) { return cmp(initialKey(a), initialKey(b)); });
  });

  // Place one column. A card lines up with the
  // topmost item it depends on and only moves down when that row is taken.
  // Type blocks keep a larger gap between them.
  var pos = new Map(), groups = [];
  function anchorY(id) {
    var best = Infinity;
    IN.get(id).forEach(function (p) {
      var q = pos.get(p);
      if (q && visSet.has(p)) best = Math.min(best, q.y);
    });
    return best;
  }
  function place(list, ci) {
    var x = PAD + ci * (NODE_W + COL_GAP), y = TOP, lastBlock = null, lastGroup = null;
    list.forEach(function (n) {
      var g = groupLabel(n);          // used for ordering only; no label is drawn
      var blk = blockRank(n);
      if (lastBlock !== null && (blk !== lastBlock || g !== lastGroup)) y += BLOCK_GAP;
      lastBlock = blk; lastGroup = g;
      var a = ci ? anchorY(n.id) : Infinity;
      if (a !== Infinity) y = Math.max(y, a);
      pos.set(n.id, {x: x, y: y});
      y += NODE_H + GAP;
    });
    return y;
  }
  function placeAll() {
    groups = [];
    var maxY = 0;
    cols.forEach(function (list, ci) { maxY = Math.max(maxY, place(list, ci)); });
    return maxY;
  }

  // Reduce crossings: reorder groups and cards by the average height of their
  // neighbours, alternating left-to-right and right-to-left sweeps.
  // Type blocks keep their order; visuals and pages keep report order.
  function reorder(list, neighbours) {
    if (TERMINAL[list[0] && list[0].type]) return;
    var bary = new Map();
    list.forEach(function (n, i) {
      var ys = neighbours.get(n.id).map(function (id) { return pos.get(id); })
        .filter(Boolean).map(function (p) { return p.y; });
      bary.set(n.id, ys.length ? ys.reduce(function (a, b) { return a + b; }, 0) / ys.length : pos.get(n.id).y);
    });
    var gAvg = new Map();
    list.forEach(function (n) {
      var k = n.type + "\u0000" + groupLabel(n);
      var g = gAvg.get(k) || {sum: 0, count: 0};
      g.sum += bary.get(n.id); g.count++;
      gAvg.set(k, g);
    });
    list.sort(function (a, b) {
      if (blockRank(a) !== blockRank(b)) return blockRank(a) - blockRank(b);
      var ka = a.type + "\u0000" + groupLabel(a), kb = b.type + "\u0000" + groupLabel(b);
      if (ka !== kb) {
        var ga = gAvg.get(ka), gb = gAvg.get(kb);
        var d = ga.sum / ga.count - gb.sum / gb.count;
        return d || (ka < kb ? -1 : 1);
      }
      return (bary.get(a.id) - bary.get(b.id)) || (a.label.toLowerCase() < b.label.toLowerCase() ? -1 : 1);
    });
  }
  placeAll();
  for (var sweep = 0; sweep < SWEEPS; sweep++) {
    if (sweep % 2 === 0) {
      for (var i = 1; i < cols.length; i++) { reorder(cols[i], A.pred); place(cols[i], i); }
    } else {
      for (var j = cols.length - 2; j >= 0; j--) { reorder(cols[j], A.succ); place(cols[j], j); }
    }
  }
  // A column sorted by another column is not a dependency: the two are shown
  // one under the other instead, joined by a short connector.
  function pairSortColumns(list) {
    for (var i = 0; i < list.length; i++) {
      var id = list[i].sortbyId;
      if (!id) continue;
      var j = -1;
      for (var k = 0; k < list.length; k++) if (list[k].id === id) j = k;
      if (j < 0 || j === i + 1) continue;
      var partner = list.splice(j, 1)[0];
      list.splice(j < i ? i : i + 1, 0, partner);
      if (j < i) i--;
    }
  }

  // Final pass, left to right: order each column by the row of what feeds it,
  // then place. Without this a card can be sorted below a neighbour and can no
  // longer line up with its own source, since placing only moves cards down.
  // Real dead ends only: something hidden by the current filters still counts.
  function feedsNothing(n) {
    return !(n.ndown || 0);
  }
  var maxY = TOP;
  cols.forEach(function (list, ci) {
    var idx = new Map(list.map(function (n, i) { return [n.id, i]; }));
    list.sort(function (a, b) {
      var da = feedsNothing(a) ? 1 : 0, db = feedsNothing(b) ? 1 : 0;
      if (da !== db) return da - db;                  // cards nothing depends on sink to the bottom
      var ya = anchorY(a.id), yb = anchorY(b.id);
      if (ya !== yb) return ya === Infinity ? 1 : yb === Infinity ? -1 : ya - yb;
      if (blockRank(a) !== blockRank(b)) return blockRank(a) - blockRank(b);
      return idx.get(a.id) - idx.get(b.id);
    });
    pairSortColumns(list);
    maxY = Math.max(maxY, place(list, ci));
  });

  // Headers only where a column holds a single kind of item.
  var heads = [];
  cols.forEach(function (list, ci) {
    if (!list.length) return;
    var x = PAD + ci * (NODE_W + COL_GAP), label = null;
    var kinds = new Set(list.map(function (n) { return n.type; }));
    if (ci === 0 && (kinds.has("source") || kinds.has("query")))
      label = kinds.has("query") ? (kinds.has("source") ? "Sources & queries" : "Queries & parameters") : "Data sources";
    else if (kinds.size === 1 && kinds.has("visual")) label = "Visuals";
    else if (kinds.size === 1 && kinds.has("page")) label = "Pages";
    if (label) heads.push({x: x, label: label, count: list.length});
  });
  var width = PAD + cols.length * (NODE_W + COL_GAP) - COL_GAP + PAD;
  return {pos: pos, groups: groups, heads: heads, width: Math.max(width, 400), height: maxY + PAD};
}

/* Second line of a card: what the small group label used to say, plus a detail. */
function caps(v) {
  return v ? v.charAt(0).toUpperCase() + v.slice(1).replace(/([a-z])([A-Z])/g, "$1 $2") : "";
}
function cardLine(n) {
  var bits = [];
  if (n.broken) bits.push("Not in " + (ownerName(n) || "the semantic model"));
  else if (n.external) bits.push("In " + (n.extmodel || "another semantic model"));
  else if (n.sub === "report") bits.push("In the report " + (n.reportname || "") + " · " + (n.table || ""));
  else if (n.type === "source") bits.push(n.sub || "Data source");
  else if (n.type === "query" && n.sub === "parameter") bits.push(n.value || "No value stored");
  else if (n.type === "query") {
    var what = n.objects || n.fn || (n.nsteps ? plural(n.nsteps, "step", "steps") : "No source");
    bits.push(what);
  } else if (n.type === "table") {
    bits.push(n.sub === "fieldparam" ? "Field parameter" : (caps(n.mode) || "Table"));
  } else if (n.type === "calcgroup") {
    bits.push(plural(n.nitems || 0, "item", "items"), "precedence " + (n.prec || 0));
  } else if (n.type === "calcitem") {
    bits.push(n.table || "", "Calculation item");
  } else if (n.type === "column" || n.type === "measure") {
    if (n.table) bits.push(n.table);
    if (n.type === "column" && n.dtype) bits.push(caps(n.dtype));
    if (n.sortby) bits.push("sorted by " + n.sortby);
  } else if (n.type === "visual") {
    if (n.page) bits.push(n.page);
  } else if (n.type === "page") {
    if (n.report) bits.push(n.report);
    bits.push(n.sub === "report" ? "Report-level filters" : plural(n.nvis || 0, "visual", "visuals"));
  }
  return bits.join(" · ");
}
var PAIR_ICON = [["column", "column"], ["measure", "measure"], ["v_column", "visual"],
                 ["query", "query"], ["table", "table"]];
function pairSvg(ic, num, cls, x, tip) {
  return sg("g", {"class": "cnt " + cls}, [
    iconG(ic, {"class": "cnt-ic", transform: "translate(" + x + "," + (NODE_TOP + 6) + ") scale(" + (12 / 24) + ")"}),
    sg("text", {"class": "cnt-n", x: x + 15, y: NODE_TOP + 15}, num),
    sg("title", null, tip)
  ]);
}
function countPairs(n) {
  var d = n.down || [0, 0, 0, 0, 0], want = [];
  if (n.type === "query" && n.sub === "parameter") want = [3, 4];
  else if (n.type === "query") want = [3, 4].filter(function (i) { return d[i]; });
  else if (n.type === "table") want = [0, 1, 2];
  else if (n.type === "calcgroup" || n.type === "calcitem") want = [0, 2];
  else if (n.type === "column" || n.type === "measure") want = n.broken || n.external ? [2] : [1, 2];
  else if (n.broken || n.external) want = [2];
  // Totals first, then a divider, then the counts by type.
  var up = n.nup || 0, down = n.ndown || 0, x = 14, out = [];
  out.push(pairSvg("ui_up", up, "tot" + (up ? "" : " zero"), x, plural(up, "item", "items") + " feed this, directly or further back"));
  x += 25 + String(up).length * 6.6;
  out.push(pairSvg("ui_down", down, "tot" + (down ? "" : " zero"), x, plural(down, "item", "items") + " depend on this, directly or further on"));
  x += 25 + String(down).length * 6.6;
  if (want.length) {
    out.push(sg("path", {"class": "vdiv", d: "M" + (x - 3) + "," + NODE_TOP + "V" + NODE_H}));
    x += 8;
    want.forEach(function (i) {
      var num = String(d[i]), name = PAIR_ICON[i][1];
      out.push(pairSvg(PAIR_ICON[i][0], num, "t-" + PAIR_ICON[i][1] + (d[i] ? "" : " zero"), x,
                       plural(d[i], name, name + "s") + " depend on this"));
      x += 25 + num.length * 6.6;
    });
  }
  return {svg: out, width: x - 14};
}
function nodeActions(n) {
  if (n.broken || n.external) return [];
  if (n.type === "table" || n.type === "column" || n.type === "measure" || n.type === "calcgroup" || n.type === "calcitem")
    return [["model", "nav_model", "Show in Model"]];
  if (n.type === "visual") return [["visual", "nav_report", "Show in Reports"]];
  if (n.type === "page" && n.sub !== "report") return [["page", "nav_report", "Show in Reports"]];
  return [];
}
function flashRow(el) {
  if (!el) return;
  el.classList.add("hl");
  setTimeout(function () { el.classList.remove("hl"); }, 2200);
}
function showInModel(n) {
  switchTab("model");
  if (state.mdMode !== "list") setModelMode("list");     // the row lives in Details, not the diagram
  if (revealModelRow(n.id)) return;
  var whole = n.type === "table" || n.type === "calcgroup";
  var tname = whole ? n.label : n.table;
  var block = $("tbl-" + (n.mkey || "") + "|" + tname);
  if (!block) return;
  block.open = true;
  block.scrollIntoView({block: "start"});
  if (!whole) {
    var row = null;
    block.querySelectorAll("tr[data-nid]").forEach(function (r) { if (r.getAttribute("data-nid") === n.id) row = r; });
    flashRow(row);
  }
}
function showVisualInReports(n) {
  var pid = (OUT.get(n.id) || []).filter(function (x) { return byId.get(x).type === "page"; })[0];
  if (!pid) return;
  var sec = (openPage(pid), showPage(byId.get(pid).rkey || "", pid, true));
  if (!sec) return;
  var row = null;
  sec.querySelectorAll("tr[data-vid]").forEach(function (r) { if (r.getAttribute("data-vid") === n.id) row = r; });
  flashRow(row);
}
function runNodeAction(act, n) {
  if (!n) return;
  if (act === "model") showInModel(n);
  if (act === "visual") showVisualInReports(n);
  if (act === "page") openPage(n.id);
}

var svg = $("svg"), L = null, nodeEls = new Map(), edgeEls = [];

/* A card's action buttons (Show in Model, Show in Reports), right-aligned from x. */
function cardActions(n, x, y) {
  var out = [];
  nodeActions(n).slice().reverse().forEach(function (a) {
    x -= 22;
    out.push(sg("g", {"class": "nact", "data-act": a[0], "data-id": n.id, tabindex: 0, role: "button",
                         "aria-label": a[2] + ": " + (n.name || n.label), transform: "translate(" + x + "," + y + ")"}, [
      sg("rect", {width: 22, height: 22, rx: 4}),
      iconG(a[1], {"class": "aic", transform: "translate(4,4) scale(" + (14 / 24) + ")"}),
      sg("title", null, a[2])
    ]));
    x -= 2;
  });
  return {els: out, left: x};
}
function cardText(cls, x, y, room, text) {
  return sg("text", {"class": cls, x: x, y: y, "data-room": room, "data-full": text}, text);
}
function nodeCard(n, p) {
  var cls = ["n", "t-" + n.type, n.sub ? "s-" + n.sub : "", n.hidden ? "hid" : "", n.broken ? "broken" : ""].join(" ");
  var mk = markers(n), name = n.name || n.label;
  var tip = kindName(n) + ": " + n.label +
            (ownerName(n) ? "\nSemantic model: " + ownerName(n) : "") +
            (n.table ? "\nTable: " + n.table : "") +
            (n.sub === "report" ? "\nDefined in the report " + (n.reportname || "") + ", not the semantic model" : "") +
            (n.page ? "\nPage: " + n.page : "") +
            (mk.length ? "\n" + mk.map(function (x) { return x[1]; }).join(" · ") : "");
  var kids = [sg("path", {"class": "box", d: CARD_PATH}), sg("rect", {"class": "bar", width: 4, height: NODE_H})];
  var vtype = function (y) {
    return n.type === "visual" && n.vtype
      ? sg("text", {"class": "t1x", y: y, "data-after": "t1", "data-full": n.vtype}, n.vtype) : null;
  };
  if (state.dense === "compact") {
    var ca = cardActions(n, NODE_W - 6, (NODE_H - 22) / 2);
    var cmx = ca.els.length ? ca.left - 4 : NODE_W - 10;   // markers are a detailed-view thing
    kids.push(iconG(iconName(n), {"class": "ico", transform: "translate(12," + ((NODE_H - 18) / 2) + ") scale(" + (18 / 24) + ")"}),
              cardText("t1", 38, NODE_H / 2 + 4, Math.max(40, cmx - 38), name),
              vtype(NODE_H / 2 + 4), ca.els);
  } else {
    var acts = cardActions(n, NODE_W - 6, NODE_TOP + 2), pairs = countPairs(n);
    var ST = 14, st = [], mx = NODE_W - 10 - ST;            // right edge of the first marker
    mk.slice().reverse().forEach(function (x) {
      st.push(iconG(x[0], {"class": "st" + (x[0] === "missing" ? " bad" : ""),
                           transform: "translate(" + mx + ",9) scale(" + (ST / 24) + ")"}));
      mx -= ST + 4;
    });
    var line2 = cardLine(n);
    kids.push(iconG(iconName(n), {"class": "ico", transform: "translate(14," + ((NODE_TOP - 20) / 2) + ") scale(" + (20 / 24) + ")"}),
              cardText("t1", CARD_TEXT_X, 22, Math.max(40, mx + 6 - CARD_TEXT_X), name),
              vtype(22),
              line2 ? cardText("t2", CARD_TEXT_X, 39, Math.max(40, NODE_W - 10 - CARD_TEXT_X), line2) : null,
              st,
              sg("path", {"class": "divider", d: "M4," + NODE_TOP + "H" + NODE_W}),
              pairs.svg, acts.els);
  }
  kids.push(sg("title", null, tip));
  var g = sg("g", {"class": cls, transform: "translate(" + p.x + "," + p.y + ")", tabindex: 0, role: "button"}, kids);
  g.__id = n.id;
  return g;
}
function render() {
  L = layout();
  var out = [];
  L.heads.forEach(function (hd) {
    out.push(sg("text", {"class": "colhead", x: hd.x, y: 26}, [hd.label + " ", sg("tspan", {"class": "cnt"}, hd.count)]));
  });
  L.groups.forEach(function (g) {
    out.push(sg("text", {"class": "grp", x: g.x + 2, y: g.y + 15}, trunc(g.label, 40)));
  });
  edgeEls = [];
  var lines = sg("g");
  D.edges.forEach(function (e) {
    var pa = L.pos.get(e[0]), pb = L.pos.get(e[1]);
    if (!pa || !pb) return;
    var x1 = pa.x + NODE_W, y1 = pa.y + NODE_H / 2, x2 = pb.x, y2 = pb.y + NODE_H / 2, d;
    if (x2 > x1) {
      var mx = (x1 + x2) / 2;
      d = "M" + x1 + "," + y1 + " C" + mx + "," + y1 + " " + mx + "," + y2 + " " + x2 + "," + y2;
    } else {
      d = "M" + x1 + "," + y1 + " C" + (x1 + 60) + "," + y1 + " " + (x2 - 60) + "," + y2 + " " + x2 + "," + y2;
    }
    var path = sg("path", {"class": "e", d: d});
    lines.appendChild(path);
    edgeEls.push({a: e[0], b: e[1], el: path});
  });
  out.push(lines);
  var cards = sg("g");
  D.nodes.forEach(function (n) {           // sorted column ↔ its sort column
    if (!n.sortbyId) return;
    var a = L.pos.get(n.id), b = L.pos.get(n.sortbyId);
    if (!a || !b || a.x !== b.x) return;
    var top = Math.min(a.y, b.y) + NODE_H, bottom = Math.max(a.y, b.y), x = a.x + 22;
    if (bottom - top > NODE_H) return;     // only when the two sit together
    cards.appendChild(sg("path", {"class": "sortlink", d: "M" + x + "," + top + "V" + bottom}));
  });
  nodeEls = new Map();
  L.pos.forEach(function (p, id) {
    var g = nodeCard(byId.get(id), p);
    cards.appendChild(g);
    nodeEls.set(id, g);
  });
  out.push(cards);
  svg.setAttribute("viewBox", "0 0 " + L.width + " " + L.height);
  fill(svg, out);
  fitCardLines(svg);
  sizeSvg();
  applyFocus();
  applySearch();
  if (typeof graphOnRender === "function") graphOnRender();
}
function sizeSvg() {
  svg.setAttribute("width", Math.round(L.width * state.zoom));
  svg.setAttribute("height", Math.round(L.height * state.zoom));
}

function lineage(id) {
  function walk(adj) {
    var seen = new Set(), stack = [id];
    while (stack.length) {
      adj.get(stack.pop()).forEach(function (y) {
        if (!seen.has(y)) { seen.add(y); stack.push(y); }
      });
    }
    seen.delete(id);
    return seen;
  }
  return {up: walk(IN), down: walk(OUT)};
}

function applyFocus() {
  svg.classList.toggle("focusing", !!state.focus);
  nodeEls.forEach(function (el) { el.classList.remove("up", "down", "focus"); });
  edgeEls.forEach(function (e) { e.el.classList.remove("lit", "upe", "downe", "direct"); });
  if (!state.focus) { if (typeof graphOnFocus === "function") graphOnFocus(); return; }
  var lin = lineage(state.focus);
  lin.up.forEach(function (id) { var el = nodeEls.get(id); if (el) el.classList.add("up"); });
  lin.down.forEach(function (id) { var el = nodeEls.get(id); if (el) el.classList.add("down"); });
  var f = nodeEls.get(state.focus); if (f) f.classList.add("focus");
  var upSet = new Set(lin.up); upSet.add(state.focus);
  var downSet = new Set(lin.down); downSet.add(state.focus);
  // Direct links touch the selected item; indirect ones sit further along the chain.
  // Highlighted lines are moved to the front, direct ones last so they sit on top.
  var indirect = [], direct = [];
  edgeEls.forEach(function (e) {
    var dir = null;
    if (upSet.has(e.a) && upSet.has(e.b)) dir = "upe";
    else if (downSet.has(e.a) && downSet.has(e.b)) dir = "downe";
    if (!dir) return;
    e.el.classList.add("lit", dir);
    if (e.a === state.focus || e.b === state.focus) { e.el.classList.add("direct"); direct.push(e.el); }
    else indirect.push(e.el);
  });
  indirect.concat(direct).forEach(function (el) { el.parentNode.appendChild(el); });
  if (typeof graphOnFocus === "function") graphOnFocus();
}

function scrollToNode(id) {
  if (state.lnMode === "graph" && typeof graphCenterOn === "function") { graphCenterOn(id); return; }
  var p = L && L.pos.get(id); if (!p) return;
  var cv = $("canvas");
  cv.scrollTo({left: Math.max(0, p.x * state.zoom - cv.clientWidth / 3),
               top: Math.max(0, p.y * state.zoom - cv.clientHeight / 2)});
}

function focusNode(id, scroll) {
  state.focus = id;
  applyFocus();
  showPanel(id);
  if (scroll) scrollToNode(id);
}

function go(id) {
  var n = byId.get(id); if (!n) return;
  var changed = false;
  if (!isVisible(n)) {
    changed = true;
    if (state.typePick.size) { state.typePick.add(filterKey(n)); applyTypePick(); }
    if (n.auto) state.hideAuto = false;
    if (n.hidden) state.hideHidden = false;
    state.hideUnused = false;
    syncControls();
  }
  if (changed) render();
  switchTab("graph");
  focusNode(id, true);
}

