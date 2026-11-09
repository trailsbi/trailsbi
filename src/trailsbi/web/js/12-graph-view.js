/* ---------- graph view: the lineage as one network ----------
   The same items and links as the lineage map (same filters, view options,
   search and selection), drawn on a canvas in rings from the middle out: the
   map's left-to-right flow bent into circles. Global by default; "Local" keeps
   only what is within 1-3 steps of the selected item. Items rest on springs, so
   one dragged away comes back. As in Obsidian's graph view, names fade in as you
   zoom (the text fade threshold), and Display has node size, link thickness and
   arrows. */
var LN_MODE_KEY = "trailsbi.lineageMode";
state.lnMode = (function () {
  try { return localStorage.getItem(LN_MODE_KEY) === "graph" ? "graph" : "map"; } catch (e) { return "map"; }
})();
state.gLocal = false;
state.gDepth = 2;

var GV = {canvas: $("gcanvas"), wrap: $("gwrap"), ctx: null, nodes: [], idx: new Map(), links: [],
          pos: new Map(), k: 1, tx: 0, ty: 0, w: 0, h: 0, dpr: 1, running: false, dirty: false,
          hover: null, press: null, autoFit: true, key: ""};
GV.ctx = GV.canvas.getContext("2d");

function graphOn() { return state.lnMode === "graph" && openTab() === "graph"; }

/* ----- which items and links are in the graph ----- */
function graphIds() {
  var ids = L ? Array.from(L.pos.keys()) : [];
  if (!(state.gLocal && state.focus && L && L.pos.has(state.focus))) return ids;
  var vis = new Set(ids), seen = new Set([state.focus]), frontier = [state.focus];
  for (var d = 0; d < state.gDepth; d++) {
    var next = [];
    frontier.forEach(function (id) {
      OUT.get(id).concat(IN.get(id)).forEach(function (y) {
        if (vis.has(y) && !seen.has(y)) { seen.add(y); next.push(y); }
      });
    });
    frontier = next;
  }
  return Array.from(seen);
}
/* Where a new item starts: next to an item it links to, or on a spiral round the middle. */
function graphSeed(id, i) {
  var nb = OUT.get(id).concat(IN.get(id));
  for (var j = 0; j < nb.length; j++) {
    var p = GV.pos.get(nb[j]);
    if (p) return {x: p.x + (hashUnit(id) - 0.5) * 30, y: p.y + (hashUnit(id + "y") - 0.5) * 30};
  }
  var r = 12 * Math.sqrt(i + 0.5), a = i * Math.PI * (3 - Math.sqrt(5));
  return {x: r * Math.cos(a), y: r * Math.sin(a)};
}
/* A stable number in [0, 1) from text, so the same project draws the same picture. */
function hashUnit(s) {
  var h = 2166136261;
  for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) / 4294967296;
}
function graphRebuild() {
  var ids = graphIds();
  var key = ids.length + ":" + (state.gLocal ? state.focus + ":" + state.gDepth : "all") + ":" + D.edges.length;
  var fresh = key !== GV.key;
  GV.key = key;
  var order = ids.slice().sort(function (a, b) {
    return blockRank(byId.get(a)) - blockRank(byId.get(b)) || (a < b ? -1 : 1);
  });
  GV.nodes = []; GV.idx = new Map();
  order.forEach(function (id, i) {
    var p = GV.pos.get(id) || graphSeed(id, i);
    var nd = {id: id, n: byId.get(id), x: p.x, y: p.y, vx: 0, vy: 0, deg: 0, r: 4};
    GV.pos.set(id, nd);
    GV.idx.set(id, nd);
    GV.nodes.push(nd);
  });
  GV.links = [];
  D.edges.forEach(function (e) {
    var a = GV.idx.get(e[0]), b = GV.idx.get(e[1]);
    if (a && b && a !== b) { GV.links.push({s: a, t: b}); a.deg++; b.deg++; }
  });
  graphSizes();
  var empty = $("gempty");
  if (state.gLocal && !(state.focus && GV.idx.has(state.focus))) {
    empty.textContent = "Select an item to see what is around it.";
    empty.hidden = false;
  } else if (!GV.nodes.length) {
    empty.textContent = "Nothing to show with the current filters.";
    empty.hidden = false;
  } else empty.hidden = true;
  ringLayout(!fresh);
  if (fresh) { GV.autoFit = false; graphResize(); graphFit(); }
  graphRun();
}

/* ----- settings: Display, as in Obsidian ----- */
var GS_KEY = "trailsbi.graphSettings", GS_V = 2;
var GS_SPEC = [
  ["Display", [
    ["textFade", "Text fade threshold", -3, 3, 0.1, 0],
    ["nodeSize", "Node size", 0.2, 3, 0.1, 1],
    ["linkWidth", "Link thickness", 0.2, 3, 0.1, 1],
    ["arrows", "Arrows", 0, 1, 1, 0]]]
];
// The rings' spacing: the gap between the queries and the tables' circles, and between
// the tables' circles and the ring of pages and visuals.
var RING_TABLES = 24, RING_PAGES = 30;
var GS = {};
function gsDefaults() { GS_SPEC.forEach(function (g) { g[1].forEach(function (x) { GS[x[0]] = x[5]; }); }); }
gsDefaults();
(function () {
  try {
    var saved = JSON.parse(localStorage.getItem(GS_KEY) || "{}");
    Object.keys(GS).forEach(function (k) {
      if (typeof saved[k] !== "number") return;
      GS[k] = saved[k];
    });
  } catch (e) { /* no storage: the defaults */ }
})();
function gsSave() { try { localStorage.setItem(GS_KEY, JSON.stringify(Object.assign({v: GS_V}, GS))); } catch (e) { /* not kept */ } }
function graphSizes() {
  GV.nodes.forEach(function (nd) { nd.r = Math.min(14, 3.5 + Math.sqrt(nd.deg) * 1.5) * GS.nodeSize; });
}
function gsFmt(x, v) { return (Math.round(v * 100) / 100).toString(); }
function buildGraphSettings() {
  var box = $("gSet");
  fill(box, GS_SPEC.map(function (g) {
    return h("details", {open: true}, [h("summary", null, g[0]), g[1].map(function (x) {
      if (x[0] === "arrows")
        return h("label", {"class": "gchk"}, [h("input", {type: "checkbox", "data-gs": x[0], checked: !!GS.arrows}), x[1]]);
      return [
        h("label", {"for": "gs-" + x[0]}, [x[1], h("span", {"class": "gval"}, gsFmt(x, GS[x[0]]))]),
        h("input", {type: "range", id: "gs-" + x[0], "data-gs": x[0], min: x[2], max: x[3], step: x[4], value: GS[x[0]]})
      ];
    })]);
  }).concat(h("button", {"class": "greset", type: "button"}, "Restore defaults")));
}
function onGraphSetting(e) {
  var inp = e.target.closest && e.target.closest("input[data-gs]");
  if (!inp) return;
  var k = inp.getAttribute("data-gs");
  GS[k] = inp.type === "checkbox" ? (inp.checked ? 1 : 0) : Number(inp.value);
  var spec = null;
  GS_SPEC.forEach(function (g) { g[1].forEach(function (x) { if (x[0] === k) spec = x; }); });
  var out = inp.previousElementSibling && inp.previousElementSibling.querySelector(".gval");
  if (out && spec) out.textContent = gsFmt(spec, GS[k]);
  if (k === "nodeSize") graphSizes();
  if (k === "nodeSize") ringLayout(true);
  gsSave();
  graphRun();
}
$("gSet").addEventListener("input", onGraphSetting);
$("gSet").addEventListener("change", onGraphSetting);
$("gSet").addEventListener("click", function (e) {
  if (!(e.target.closest && e.target.closest(".greset"))) return;
  gsDefaults(); gsSave(); buildGraphSettings(); graphSizes();
  ringLayout(true);
  graphRun();
});
fill($("gSetBtn"), icon("ui_gear", 16));
$("gSetBtn").addEventListener("click", function () {
  var open = $("gSet").hidden;
  if (open) buildGraphSettings();
  $("gSet").hidden = !open;
  $("gSetBtn").setAttribute("aria-expanded", String(open));
});

/* ----- rings: the lineage from the middle out ----------
   The map's left-to-right flow bent into circles. Parameters and data sources sit in
   the middle with the queries round them; tables on the next ring, each with its
   columns, then measures, in small rings around it; visuals on a ring outside all
   tables; pages outside the visuals. Each item faces the items it links to: a query
   at the mean angle of the tables it loads, a visual at the mean angle of the tables
   whose fields it shows, a page at the mean angle of its visuals. */
var TAU = Math.PI * 2;
function angMean(list) {
  var sx = 0, sy = 0;
  list.forEach(function (a) { sx += Math.cos(a); sy += Math.sin(a); });
  return sx || sy ? Math.atan2(sy, sx) : null;
}
/* Places items on a circle near the angles they want, at least `gap` apart.
   Returns the radius used (the ring grows when the items do not fit). */
function ringSpread(items, r, gap) {
  if (!items.length) return r;
  r = Math.max(r, items.length * gap / TAU);
  var g = gap / r;
  items.forEach(function (it, i) { if (it.want === null || it.want === undefined) it.want = i / items.length * TAU; });
  items.sort(function (a, b) { return norm(a.want) - norm(b.want); });
  var at = items.map(function (it) { return norm(it.want); });
  for (var pass = 0; pass < 2; pass++) {                   // twice, so the wrap past 360° is pushed too
    for (var i = 1; i < at.length; i++) if (at[i] < at[i - 1] + g) at[i] = at[i - 1] + g;
    if (at.length > 1 && at[0] + TAU < at[at.length - 1] + g) at[0] = at[at.length - 1] + g - TAU;
  }
  var shift = 0;                                           // keep the group centred on what it wanted
  items.forEach(function (it, i) { shift += norm(it.want) - at[i]; });
  shift /= items.length;
  items.forEach(function (it, i) { it.ang = at[i] + shift; });
  return r;
}
function norm(a) { a %= TAU; return a < 0 ? a + TAU : a; }
/* Slots for an item's children on small rings round it: [radius, share of the turn]. */
/* Slots for an item's children round it: [radius, angle from the outward direction].
   A full ring goes all the way round; a ring the group does not fill stays together on
   the outer side, so two fields and their table make a triangle rather than a line.
   par.c0 is how far the centre of the smallest circle round the group sits from the item
   along the outward direction, and par.cr that circle's radius, so a small group gets a
   small circle. */
function clusterSlots(par, kids, pad) {
  var kr = kids.reduce(function (m, c) { return Math.max(m, c.r); }, 3), step = 2 * kr + pad;
  par.slots = []; var ring = 0, left = kids.length, rr = 0;
  while (left > 0) {
    rr = par.r + kr + Math.max(8, pad) + ring * step;
    var cap = Math.max(3, Math.floor(TAU * rr / step));
    var take = Math.min(cap, left), j;
    if (take < cap) for (j = 0; j < take; j++) par.slots.push([rr, (j - (take - 1) / 2) * step / rr]);
    else for (j = 0; j < take; j++) par.slots.push([rr, j / take * TAU + Math.PI]);
    left -= take; ring++;
  }
  // the smallest circle round the item and its fields (points on the outward axis frame)
  var pts = [{x: 0, y: 0, r: par.r}].concat(par.slots.map(function (sl) {
    return {x: sl[0] * Math.cos(sl[1]), y: sl[0] * Math.sin(sl[1]), r: kr};
  }));
  var cx = 0, cy = 0;
  for (var it = 1; it <= 400 && pts.length > 1; it++) {
    var far = pts[0], fd = -1;
    pts.forEach(function (q) { var d = Math.hypot(q.x - cx, q.y - cy) + q.r; if (d > fd) { fd = d; far = q; } });
    cx += (far.x - cx) / (it + 1); cy += (far.y - cy) / (it + 1);
  }
  par.c0 = cx;                                             // symmetric about the axis, so cy is ~0
  par.cr = pts.reduce(function (m, q) { return Math.max(m, Math.hypot(q.x - cx, q.y) + q.r); }, 0) + 8;
}
/* Where an item's group circle is centred now (it follows the item when dragged). */
function groupCentre(tb) { return {x: tb.x + (tb.c0 || 0) * Math.cos(tb.ang), y: tb.y + (tb.c0 || 0) * Math.sin(tb.ang)}; }
function ringLayout(animate) {
  var prev = new Map();
  GV.nodes.forEach(function (nd) { prev.set(nd, [nd.x, nd.y]); nd.par = null; });
  var SEP = "\u241e", center = [], queries = [], tables = [], visuals = [], pages = [], fields = [];
  var anchor = new Map();
  GV.nodes.forEach(function (nd) {
    var t = nd.n.type;
    nd.kids = null;
    if (t === "source" || (t === "query" && nd.n.sub === "parameter")) center.push(nd);
    else if (t === "query") queries.push(nd);
    else if (t === "table" || t === "calcgroup") { tables.push(nd); anchor.set((nd.n.mkey || "") + SEP + nd.n.label, nd); }
    else if (t === "visual") visuals.push(nd);
    else if (t === "page") pages.push(nd);
    else fields.push(nd);
  });
  // fields round their table; fields of a table that is not here (another model) get a stand-in
  fields.forEach(function (nd) {
    var key = (nd.n.mkey || "") + SEP + (nd.n.table || ""), a = anchor.get(key);
    if (!a) {
      a = {id: "anchor:" + key, n: {label: nd.n.table || "", type: "table"}, ghost: true, x: 0, y: 0, r: 0};
      anchor.set(key, a); tables.push(a);
    }
    (a.kids = a.kids || []).push(nd);
  });
  var KIND = {column: 0, calcitem: 1, measure: 2};
  var maxC = 0;
  tables.forEach(function (tb) {                           // the small rings round each table
    (tb.kids || []).sort(function (a, b) {
      return (KIND[a.n.type] || 0) - (KIND[b.n.type] || 0) || a.n.label.localeCompare(b.n.label);
    });
    clusterSlots(tb, tb.kids || [], 5);
    maxC = Math.max(maxC, tb.cr);
  });
  // tables: grouped by model, then by the source they come from, then by name
  var srcOf = function (tb) {
    if (tb.ghost) return "~";
    var best = "";
    (IN.get(tb.id) || []).forEach(function (u) { if (!best) best = u; });
    return best;
  };
  tables.sort(function (a, b) {
    var ma = a.n.mkey || "~", mb = b.n.mkey || "~";
    return ma < mb ? -1 : ma > mb ? 1 : srcOf(a) < srcOf(b) ? -1 : srcOf(a) > srcOf(b) ? 1 : a.n.label.localeCompare(b.n.label);
  });
  // the middle: parameters and sources, with queries round them
  var R0c = center.length > 1 ? Math.max(24, center.length * 22 / TAU) : 0;
  var R0q = queries.length ? Math.max(R0c + 40, queries.length * 24 / TAU) : R0c;
  // Each table comes in as close to the middle as its own circle allows: its inner edge sits
  // the Tables ring gap outside the queries, so small tables are close in and big ones further
  // out. The turn is shared by the room each circle needs at its own distance; if that is more
  // than a full turn everything moves out together, and any two circles still too close are
  // pushed apart, the outer one outwards.
  var SAFE = 18, a0 = -Math.PI / 2, base = R0q + RING_TABLES;
  tables.forEach(function (tb) { tb.tr = Math.max(base + tb.cr, 60); });
  var wOf = function (tb) { var half = (tb.cr + SAFE / 2) / tb.tr; return half >= 1 ? Math.PI : 2 * Math.asin(half); };
  for (var iter = 0; iter < 80 && tables.length > 1; iter++) {
    var tot = tables.reduce(function (t, tb) { return t + wOf(tb); }, 0);
    if (tot <= TAU) break;
    tables.forEach(function (tb) { tb.tr += 6; });
  }
  var wsA = tables.map(wOf);
  var spareA = Math.max(0, TAU - wsA.reduce(function (t, x) { return t + x; }, 0)) / Math.max(tables.length, 1);
  var accA = 0;
  tables.forEach(function (tb, i) {                        // share out any room left evenly
    tb.ang = a0 + accA + spareA / 2 + wsA[i] / 2; accA += wsA[i] + spareA;
  });
  for (iter = 0; iter < 200; iter++) {
    var worst = 0;
    for (var i = 0; i < tables.length; i++) {
      for (var j = i + 1; j < tables.length; j++) {
        var A = tables[i], B = tables[j];
        var dx = A.tr * Math.cos(A.ang) - B.tr * Math.cos(B.ang), dy = A.tr * Math.sin(A.ang) - B.tr * Math.sin(B.ang);
        var over = A.cr + B.cr + SAFE - Math.sqrt(dx * dx + dy * dy);
        if (over > 0.5) { (A.tr >= B.tr ? A : B).tr += Math.max(1, over * 0.5); worst = Math.max(worst, over); }
      }
    }
    if (!worst) break;
  }
  var Rout = tables.reduce(function (m, tb) { return Math.max(m, tb.tr); }, base);
  var tr = function (tb) { return tb.tr; };
  var put = function (nd, r, a) { nd.x = r * Math.cos(a); nd.y = r * Math.sin(a); nd.ang = a; };
  tables.forEach(function (tb) {
    put(tb, tr(tb) - (tb.c0 || 0), tb.ang);               // the group's centre sits on its spot
    (tb.kids || []).forEach(function (c, i) {
      var sl = tb.slots[i], phase = tb.ang + sl[1];          // a part ring faces outwards, to the visuals
      c.x = tb.x + sl[0] * Math.cos(phase); c.y = tb.y + sl[0] * Math.sin(phase);
    });
  });
  var tableAng = new Map();
  tables.forEach(function (tb) {
    tableAng.set(tb.id, tb.ang);
    (tb.kids || []).forEach(function (c) { tableAng.set(c.id, tb.ang); });
  });
  // angles of the tables an item reaches, a few steps downstream (for the middle) or upstream (outside)
  var reach = function (id, dir, depth) {
    var out = [], seen = new Set([id]), front = [id];
    for (var d = 0; d < depth && front.length; d++) {
      var nx = [];
      front.forEach(function (x) {
        (dir === "down" ? OUT.get(x) : IN.get(x)).forEach(function (y) {
          if (seen.has(y) || !GV.idx.has(y)) return;
          seen.add(y);
          if (tableAng.has(y)) out.push(tableAng.get(y)); else nx.push(y);
        });
      });
      front = nx;
    }
    return out;
  };
  queries.forEach(function (q) { q.want = angMean(reach(q.id, "down", 4)); });
  R0q = queries.length ? ringSpread(queries, R0q, 24) : R0q;
  queries.forEach(function (q) { put(q, R0q, q.ang); });
  var qAng = new Map(queries.map(function (q) { return [q.id, q.ang]; }));
  center.forEach(function (c) {
    var as = [];
    OUT.get(c.id).forEach(function (y) { if (qAng.has(y)) as.push(qAng.get(y)); });
    c.want = as.length ? angMean(as) : angMean(reach(c.id, "down", 4));
  });
  if (center.length === 1) put(center[0], 0, 0);
  else if (center.length) { R0c = ringSpread(center, R0c, 22); center.forEach(function (c) { put(c, R0c, c.ang); }); }
  // pages on the outer ring, in the order of the tables they show; each page's visuals
  // in small rings round it, each visual on the side facing the tables it uses
  var byPage = new Map(), loose = [];
  pages.forEach(function (pg) { byPage.set(pg.id, []); pg.kids = null; });
  visuals.forEach(function (v) {
    var pg = OUT.get(v.id).filter(function (y) { return byPage.has(y); })[0];
    if (pg) byPage.get(pg).push(v); else loose.push(v);
  });
  var holders = pages.slice();
  if (loose.length) {                                      // visuals whose page is not shown
    var lp = {id: "anchor:visuals", n: {label: "", type: "page"}, ghost: true, x: 0, y: 0, r: 0};
    byPage.set(lp.id, loose); holders.push(lp);
  }
  // the outer ring is centred on the area the inner rings actually take up, and clears all of it
  var bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
  GV.nodes.forEach(function (nd) {
    var t = nd.n.type;
    if (t === "visual" || t === "page") return;
    bx0 = Math.min(bx0, nd.x - nd.r); by0 = Math.min(by0, nd.y - nd.r);
    bx1 = Math.max(bx1, nd.x + nd.r); by1 = Math.max(by1, nd.y + nd.r);
  });
  var cx = isFinite(bx0) ? (bx0 + bx1) / 2 : 0, cy = isFinite(by0) ? (by0 + by1) / 2 : 0, reachR = 0;
  // the smallest circle round everything inside (Badoiu-Clarkson): step towards the farthest item
  // what the outer ring must hold: each table's whole background circle, and any item not in one
  var inner = [];
  tables.forEach(function (tb) {
    if (!tb.ghost && tb.kids && tb.kids.length) { var gc = groupCentre(tb); inner.push({x: gc.x, y: gc.y, r: tb.cr}); }
  });
  GV.nodes.forEach(function (nd) {
    var t = nd.n.type;
    if (t === "visual" || t === "page" || (nd.kids && nd.kids.length) || (nd.par && !nd.par.ghost)) return;
    inner.push({x: nd.x, y: nd.y, r: nd.r});
  });
  for (var it = 1; it <= 1500 && inner.length > 1; it++) {
    var far = null, fd = -1;
    inner.forEach(function (q) {
      var d = Math.sqrt((q.x - cx) * (q.x - cx) + (q.y - cy) * (q.y - cy)) + q.r;
      if (d > fd) { fd = d; far = q; }
    });
    cx += (far.x - cx) / (it + 1); cy += (far.y - cy) / (it + 1);
  }
  var outerR = GV.nodes.reduce(function (m, nd) {
    return nd.n.type === "visual" || nd.n.type === "page" ? Math.max(m, nd.r) : m;
  }, 0);
  inner.forEach(function (q) {
    reachR = Math.max(reachR, Math.sqrt((q.x - cx) * (q.x - cx) + (q.y - cy) * (q.y - cy)) + q.r);
  });
  reachR += outerR;                                        // the page ring's own dots stay clear too
  var putC = function (nd, r, a) { nd.x = cx + r * Math.cos(a); nd.y = cy + r * Math.sin(a); nd.ang = a; };
  var tPos = new Map();                                    // where each field sits, to aim visuals at
  tables.forEach(function (tb) { (tb.kids || []).forEach(function (c) { tPos.set(c.id, c); }); tPos.set(tb.id, tb); });
  var aim = function (id) {
    var sx = 0, sy = 0, n = 0;
    IN.get(id).forEach(function (u) { var q = tPos.get(u); if (q) { sx += q.x; sy += q.y; n++; } });
    return n ? {x: sx / n, y: sy / n} : null;
  };
  // each page sits on the ring with its visuals beside it on the same ring, left and right,
  // in the order of the tables they use; a little gap between one page's run and the next
  var VGAP = 24, PGAP = 2;                                 // spacing along the ring; slots of gap between pages
  holders.forEach(function (pg) {
    var vs = byPage.get(pg.id);
    pg.kids = vs;
    vs.forEach(function (v) { v.aimAt = aim(v.id); v.aimA = v.aimAt ? Math.atan2(v.aimAt.y - cy, v.aimAt.x - cx) : null; });
    var as = vs.map(function (v) { return v.aimA; }).filter(function (x) { return x !== null; });
    pg.want = as.length ? angMean(as) : angMean(reach(pg.id, "up", 3));
    pg.slotsN = vs.length + (pg.ghost ? 0 : 1) + PGAP;
  });
  var nSlots = holders.reduce(function (t, pg) { return t + pg.slotsN; }, 0);
  var R2 = Math.max(reachR + RING_PAGES, nSlots * VGAP / TAU);
  var slotA = TAU / Math.max(nSlots, 1);
  holders.sort(function (a, b) { return norm(a.want === null ? 0 : a.want) - norm(b.want === null ? 0 : b.want); });
  var cur = holders.length ? norm(holders[0].want === null ? 0 : holders[0].want) - holders[0].slotsN * slotA / 2 : 0;
  holders.forEach(function (pg) {
    var mid = cur + pg.slotsN * slotA / 2;
    var rel = function (v) { return v.aimA === null ? 0 : Math.atan2(Math.sin(v.aimA - mid), Math.cos(v.aimA - mid)); };
    var run = pg.kids.slice().sort(function (a, b) { return rel(a) - rel(b); });
    if (!pg.ghost) run.splice(Math.floor(run.length / 2), 0, pg);   // the page in the middle of its visuals
    var first = mid - (run.length - 1) * slotA / 2;
    run.forEach(function (nd, i) { putC(nd, R2, first + i * slotA); });
    cur += pg.slotsN * slotA;
  });
  GV.rings = [{r: R0c, x: 0, y: 0}, {r: queries.length ? R0q : 0, x: 0, y: 0}, {r: Rout, x: 0, y: 0},
              {r: holders.length ? R2 : 0, x: cx, y: cy}];
  // Homes: where each item rests. A table's fields rest at their place relative to the table
  // as it is now, so they follow it on a spring when it moves; pages and visuals move alone.
  holders.forEach(function (pg) { pg.kids = null; });
  GV.groups = tables.filter(function (tb) { return !tb.ghost && tb.kids && tb.kids.length; });
  GV.mids = center.concat(queries);
  tables.forEach(function (par) {
    if (par.ghost) return;
    (par.kids || []).forEach(function (c) { c.par = par; c.ox = c.x - par.x; c.oy = c.y - par.y; });
  });
  GV.nodes.forEach(function (nd) {
    nd.hx = nd.x; nd.hy = nd.y; nd.vx = nd.vy = 0;
    if (animate) { var p0 = prev.get(nd); nd.x = p0[0]; nd.y = p0[1]; }
  });
  GV.ringMoving = !!animate;
}

/* Rings with a spring: every item is pulled back to its home, and a field or visual to
   its place beside its table or page, wherever that is now. Returns whether anything
   still moves. */
var RING_HOME = 0.07, RING_KID = 0.11, RING_DAMP = 0.72;
function ringTick() {
  var most = 0;
  GV.nodes.forEach(function (nd) {                         // parents first, so fields aim at where they are
    if (nd.par) return;
    most = Math.max(most, ringStep(nd, nd.hx, nd.hy, RING_HOME));
  });
  GV.nodes.forEach(function (nd) {
    if (!nd.par) return;
    most = Math.max(most, ringStep(nd, nd.par.x + nd.ox, nd.par.y + nd.oy, RING_KID));
  });
  return most > 0.05 || !!(GV.press && GV.press.nd && GV.press.moved);
}
function ringStep(nd, tx, ty, kk) {
  if (nd.fx !== undefined) { nd.x = nd.fx; nd.y = nd.fy; nd.vx = nd.vy = 0; return 1; }
  nd.vx = (nd.vx + (tx - nd.x) * kk) * RING_DAMP;
  nd.vy = (nd.vy + (ty - nd.y) * kk) * RING_DAMP;
  nd.x += nd.vx; nd.y += nd.vy;
  return Math.abs(nd.vx) + Math.abs(nd.vy) + (Math.abs(tx - nd.x) + Math.abs(ty - nd.y)) * 0.05;
}

function graphRun() {
  GV.dirty = true;
  if (GV.running) return;
  GV.running = true;
  var step = function () {
    if (!GV.canvas.isConnected || state.lnMode !== "graph") { GV.running = false; return; }
    var moving = GV.rings ? (GV.ringMoving = ringTick()) : false;
    if (moving || GV.dirty) { GV.dirty = false; graphDraw(); }
    if (moving || GV.dirty) requestAnimationFrame(step);
    else GV.running = false;
  };
  requestAnimationFrame(step);
}

/* ----- drawing ----- */
function cssVar(name, fallback) {
  var v = getComputedStyle(document.documentElement).getPropertyValue(name);
  return (v && v.trim()) || fallback;
}
var G_TYPE_VAR = {source: "--source", query: "--query", table: "--table", column: "--column", measure: "--measure",
                  calcgroup: "--calcgroup", calcitem: "--calcgroup", visual: "--visual", page: "--page"};
function graphResize() {
  var r = GV.wrap.getBoundingClientRect();
  if (!r.width || !r.height) return false;
  GV.dpr = window.devicePixelRatio || 1;
  GV.w = r.width; GV.h = r.height;
  GV.canvas.width = Math.round(r.width * GV.dpr);
  GV.canvas.height = Math.round(r.height * GV.dpr);
  return true;
}
function graphFit() {
  if (!GV.nodes.length || !GV.w) return;
  var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  GV.nodes.forEach(function (nd) {
    x0 = Math.min(x0, nd.x - nd.r); y0 = Math.min(y0, nd.y - nd.r);
    x1 = Math.max(x1, nd.x + nd.r); y1 = Math.max(y1, nd.y + nd.r);
  });
  var k = Math.min((GV.w - 60) / Math.max(x1 - x0, 1), (GV.h - 60) / Math.max(y1 - y0, 1), 2.5);
  GV.k = Math.max(0.05, k);
  GV.tx = GV.w / 2 - (x0 + x1) / 2 * GV.k;
  GV.ty = GV.h / 2 - (y0 + y1) / 2 * GV.k;
  graphZoomLabel();
  GV.dirty = true;
}
function graphZoomLabel() { if (graphOn()) $("zLevel").textContent = Math.round(GV.k * 100) + "%"; }
/* What stands out right now: the item under the pointer and its neighbours, or
   the selected item's whole chain (navy upstream, teal downstream). */
function graphHighlight() {
  if (GV.hover && GV.idx.has(GV.hover)) {
    var near = new Set([GV.hover]);
    OUT.get(GV.hover).concat(IN.get(GV.hover)).forEach(function (y) { near.add(y); });
    return {kind: "hover", near: near};
  }
  if (state.focus && GV.idx.has(state.focus)) {
    var lin = lineage(state.focus);
    var up = new Set(lin.up), down = new Set(lin.down);
    up.add(state.focus); down.add(state.focus);
    return {kind: "focus", up: up, down: down};
  }
  return null;
}
function graphDraw() {
  var c = GV.ctx, k = GV.k;
  if (!GV.w && !graphResize()) return;
  var col = {}, ground = cssVar("--ground", "#e9edf1"), ink = cssVar("--ink", "#13203B"), faint = cssVar("--faint", "#8795a3");
  var up = cssVar("--trace-up", "#13203B"), down = cssVar("--trace-down", "#1FA79A"), brand = cssVar("--brand", "#1FA79A");
  var sel = cssVar("--sel-line", "#6f9fd8"), bad = cssVar("--bad", "#c62828"), font = cssVar("--font", "sans-serif");
  Object.keys(G_TYPE_VAR).forEach(function (t) { col[t] = cssVar(G_TYPE_VAR[t], faint); });
  var hl = graphHighlight();
  var q = state.query, hitSet = q ? new Set(hits) : null;
  c.setTransform(GV.dpr, 0, 0, GV.dpr, 0, 0);
  c.fillStyle = ground;
  c.fillRect(0, 0, GV.w, GV.h);
  c.setTransform(GV.dpr * k, 0, 0, GV.dpr * k, GV.dpr * GV.tx, GV.dpr * GV.ty);
  if (GV.rings && GV.groups) {                             // rings: soft discs behind the bands and groups
    var disc = function (x, y, r, fillCol, a) {
      if (r <= 0) return;
      c.globalAlpha = a; c.fillStyle = fillCol;
      c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill();
    };
    var dimAll = !!hl;
    // one disc round all the tables' circles, on the same centre as the outer ring
    var oc = GV.rings[3] || {x: 0, y: 0}, allR = 0;
    GV.groups.forEach(function (tb) {
      if (!GV.idx.has(tb.id)) return;
      var g2 = groupCentre(tb);
      allR = Math.max(allR, Math.sqrt((g2.x - oc.x) * (g2.x - oc.x) + (g2.y - oc.y) * (g2.y - oc.y)) + tb.cr);
    });
    disc(oc.x, oc.y, allR + 10, col.table || faint, dimAll ? 0.03 : 0.045);
    // one disc round the parameters, sources and queries in the middle
    var midR = 0;
    (GV.mids || []).forEach(function (nd) {
      if (GV.idx.has(nd.id)) midR = Math.max(midR, Math.sqrt(nd.x * nd.x + nd.y * nd.y) + nd.r);
    });
    if (GV.mids && GV.mids.length) disc(0, 0, midR + 14, col.query || faint, dimAll ? 0.06 : 0.1);
    GV.groups.forEach(function (tb) {
      if (!GV.idx.has(tb.id)) return;
      var on = !hl || (hl.kind === "hover" ? hl.near.has(tb.id) : hl.up.has(tb.id) || hl.down.has(tb.id));
      c.globalAlpha = on ? 0.11 : 0.05;
      c.fillStyle = col[tb.n.type] || faint;
      var gq = groupCentre(tb);
      c.beginPath(); c.arc(gq.x, gq.y, tb.cr - 2, 0, Math.PI * 2); c.fill();
    });
    c.globalAlpha = 1;
  }
  // links: quiet by default, the highlighted ones drawn last and on top
  var lit = [];
  var lw = GS.linkWidth;
  c.lineWidth = lw / k;
  c.strokeStyle = faint;
  c.globalAlpha = hl || hitSet ? 0.1 : 0.35;
  c.beginPath();
  GV.links.forEach(function (l) {
    var tone = null;
    if (hl && hl.kind === "hover" && (l.s.id === GV.hover || l.t.id === GV.hover)) tone = brand;
    else if (hl && hl.kind === "focus") {
      if (hl.up.has(l.s.id) && hl.up.has(l.t.id)) tone = up;
      else if (hl.down.has(l.s.id) && hl.down.has(l.t.id)) tone = down;
    }
    if (tone) { lit.push([l, tone]); return; }
    graphLink(c, l);
  });
  c.stroke();
  if (GS.arrows) {                                         // which way each link goes: a head at the user's end
    c.fillStyle = faint;
    c.beginPath();
    GV.links.forEach(function (l) { graphArrow(c, l, k, lw); });
    c.fill();
  }
  c.globalAlpha = 0.9;
  // links that touch the selected item are drawn thicker than the rest of its chain, as on the map
  var sel0 = hl && hl.kind === "focus" ? state.focus : null;
  var isDirect = function (l) { return sel0 && (l.s.id === sel0 || l.t.id === sel0); };
  lit.sort(function (a, b) { return (isDirect(a[0]) ? 1 : 0) - (isDirect(b[0]) ? 1 : 0); });
  lit.forEach(function (x) {
    var w = (isDirect(x[0]) ? 3 : sel0 ? 1.2 : 1.6) * lw;
    c.globalAlpha = isDirect(x[0]) || !sel0 ? 0.95 : 0.7;
    c.lineWidth = w / k;
    c.strokeStyle = x[1];
    c.beginPath(); graphLink(c, x[0]); c.stroke();
    if (GS.arrows) { c.fillStyle = x[1]; c.beginPath(); graphArrow(c, x[0], k, w); c.fill(); }
  });
  // items
  GV.nodes.forEach(function (nd) {
    var on = !hl || (hl.kind === "hover" ? hl.near.has(nd.id) : hl.up.has(nd.id) || hl.down.has(nd.id));
    if (hitSet && !hitSet.has(nd.id)) on = false;
    c.globalAlpha = on ? (nd.n.hidden ? 0.55 : 1) : 0.14;
    c.fillStyle = nd.n.broken ? bad : (col[nd.n.type] || faint);
    var rr = Math.max(nd.r, 2 / k);                        // never smaller than a dot on screen
    c.beginPath(); c.arc(nd.x, nd.y, rr, 0, Math.PI * 2); c.fill();
    if (nd.n.sub === "report") {                           // in the report, not the model: a hollow dot
      c.fillStyle = ground;
      c.beginPath(); c.arc(nd.x, nd.y, rr * 0.55, 0, Math.PI * 2); c.fill();
    }
    if (nd.n.broken || (hitSet && hitSet.has(nd.id)) || nd.id === state.focus) {
      c.globalAlpha = 1;
      c.lineWidth = (nd.id === state.focus ? 2.5 : 2) / k;
      c.strokeStyle = nd.id === state.focus ? ink : nd.n.broken ? bad : sel;
      c.beginPath(); c.arc(nd.x, nd.y, rr + 3 / k, 0, Math.PI * 2); c.stroke();
    }
  });
  // names, at a steady size on screen. As in Obsidian they fade in as you zoom (the text
  // fade threshold moves the zoom where that happens); the item under the pointer, its
  // neighbours, the selected item's chain and search hits always show theirs.
  c.setTransform(GV.dpr, 0, 0, GV.dpr, 0, 0);
  c.font = "12px " + font;
  c.textAlign = "center";
  c.textBaseline = "top";
  c.lineJoin = "round";
  var thr = 1.4 * Math.pow(2, GS.textFade / 2);
  var zoomA = Math.max(0, Math.min(1, (k / thr - 0.6) / 0.4));
  GV.nodes.forEach(function (nd) {
    var inHl = hl && (hl.kind === "hover" ? hl.near.has(nd.id) : hl.up.has(nd.id) || hl.down.has(nd.id));
    if ((hl && !inHl) || (hitSet && !hitSet.has(nd.id))) return;
    var sure = nd.id === state.focus || nd.id === GV.hover || (hl && hl.kind === "hover") ||
               (hl && hl.up.size + hl.down.size < 60) || (hitSet && hitSet.size < 40);
    var a = sure ? 1 : zoomA;
    if (a <= 0.02) return;
    var sx = GV.tx + nd.x * k, sy = GV.ty + (nd.y + nd.r) * k + 3;
    if (sx < -100 || sx > GV.w + 100 || sy < -20 || sy > GV.h + 20) return;
    var text = trunc(nd.n.name || nd.n.label, 30);
    c.globalAlpha = a;
    c.lineWidth = 3;
    c.strokeStyle = ground;
    c.strokeText(text, sx, sy);
    c.fillStyle = ink;
    c.fillText(text, sx, sy);
  });
  c.globalAlpha = 1;
}
/* A link: straight, or in Rings bent towards the middle, so links that cross the
   circle run together through it instead of in a mesh. */
function graphLink(c, l) {
  c.moveTo(l.s.x, l.s.y);
  if (!GV.rings) { c.lineTo(l.t.x, l.t.y); return; }
  // the further apart round the circle, the more it bends in: neighbours stay straight
  var d = Math.abs(Math.atan2(l.s.x * l.t.y - l.s.y * l.t.x, l.s.x * l.t.x + l.s.y * l.t.y));
  var f = 1 - 0.7 * d / Math.PI, mx = (l.s.x + l.t.x) / 2 * f, my = (l.s.y + l.t.y) / 2 * f;
  c.quadraticCurveTo(mx, my, l.t.x, l.t.y);
}
/* An arrow head where a link meets the item it feeds. */
function graphArrow(c, l, k, lw) {
  var dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, d = Math.sqrt(dx * dx + dy * dy);
  var rr = Math.max(l.t.r, 2 / k);
  if (d < rr * 2) return;
  var ux = dx / d, uy = dy / d, len = (5 + 2 * lw) / k, wid = (2.5 + lw) / k;
  var tx = l.t.x - ux * rr, ty = l.t.y - uy * rr, bx = tx - ux * len, by = ty - uy * len;
  c.moveTo(tx, ty);
  c.lineTo(bx - uy * wid, by + ux * wid);
  c.lineTo(bx + uy * wid, by - ux * wid);
  c.closePath();
}

/* ----- pointer, wheel and keys ----- */
function graphAt(px, py) {
  var x = (px - GV.tx) / GV.k, y = (py - GV.ty) / GV.k, best = null, bestD = Infinity;
  GV.nodes.forEach(function (nd) {
    var d = Math.hypot(nd.x - x, nd.y - y), reach = nd.r + 4 / GV.k;
    if (d <= reach && d < bestD) { best = nd; bestD = d; }
  });
  return best;
}
function graphPoint(e) {
  var r = GV.canvas.getBoundingClientRect();
  return {x: e.clientX - r.left, y: e.clientY - r.top};
}
GV.canvas.addEventListener("pointerdown", function (e) {
  if (e.button !== 0) return;
  var p = graphPoint(e), nd = graphAt(p.x, p.y);
  GV.press = {x: p.x, y: p.y, nd: nd, moved: false, tx: GV.tx, ty: GV.ty};
  GV.autoFit = false;
  try { GV.canvas.setPointerCapture(e.pointerId); } catch (err) {}
  GV.canvas.classList.add("dragging");
});
GV.canvas.addEventListener("pointermove", function (e) {
  var p = graphPoint(e), pr = GV.press;
  if (pr) {
    if (!pr.moved && Math.hypot(p.x - pr.x, p.y - pr.y) < 4) return;
    pr.moved = true;
    if (pr.nd) {                                          // hold the item; a table's fields follow on springs
      pr.nd.fx = (p.x - GV.tx) / GV.k; pr.nd.fy = (p.y - GV.ty) / GV.k;
    } else {                                              // drag the background to move around
      GV.tx = pr.tx + p.x - pr.x; GV.ty = pr.ty + p.y - pr.y;
    }
    graphRun();
    return;
  }
  var nd = graphAt(p.x, p.y), id = nd ? nd.id : null;
  if (id !== GV.hover) {
    GV.hover = id;
    GV.canvas.classList.toggle("over", !!id);
    GV.canvas.title = nd ? kindName(nd.n) + ": " + nd.n.label + (nd.n.table ? " · " + nd.n.table : "") : "";
    graphRun();
  }
});
function graphRelease(e) {
  var pr = GV.press;
  GV.press = null;
  GV.canvas.classList.remove("dragging");
  if (!pr) return;
  if (pr.nd) { delete pr.nd.fx; delete pr.nd.fy; }
  if (pr.moved) return;
  clearSearch();
  if (pr.nd) focusNode(pr.nd.id, false);
  else { state.focus = null; applyFocus(); emptyPanel(); }
  if (e && e.type === "pointerup") GV.canvas.focus({preventScroll: true});
}
GV.canvas.addEventListener("pointerup", graphRelease);
GV.canvas.addEventListener("pointercancel", function () { GV.press = null; GV.canvas.classList.remove("dragging"); });
GV.canvas.addEventListener("pointerleave", function () {
  if (GV.hover && !GV.press) { GV.hover = null; GV.canvas.classList.remove("over"); graphRun(); }
});
GV.canvas.addEventListener("dblclick", function (e) {       // double-click: the item's neighbourhood
  var p = graphPoint(e), nd = graphAt(p.x, p.y);
  if (!nd) return;
  state.focus = nd.id;
  setGraphLocal(true);
  showPanel(nd.id);
});
function graphZoomAt(factor, px, py) {
  var k = Math.max(0.05, Math.min(6, GV.k * factor));
  GV.tx = px - (px - GV.tx) * k / GV.k;
  GV.ty = py - (py - GV.ty) * k / GV.k;
  GV.k = k;
  GV.autoFit = false;
  graphZoomLabel();
  graphRun();
}
GV.canvas.addEventListener("wheel", function (e) {
  e.preventDefault();
  var p = graphPoint(e);
  graphZoomAt(Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015)), p.x, p.y);
}, {passive: false});
GV.canvas.addEventListener("keydown", function (e) {
  var step = 60;
  if (e.key === "+" || e.key === "=") graphZoomAt(1.25, GV.w / 2, GV.h / 2);
  else if (e.key === "-") graphZoomAt(1 / 1.25, GV.w / 2, GV.h / 2);
  else if (e.key === "ArrowLeft") GV.tx += step;
  else if (e.key === "ArrowRight") GV.tx -= step;
  else if (e.key === "ArrowUp") GV.ty += step;
  else if (e.key === "ArrowDown") GV.ty -= step;
  else return;
  e.preventDefault();
  graphRun();
});
function graphCenterOn(id) {
  var nd = GV.idx.get(id);
  if (!nd) return;
  GV.autoFit = false;
  if (GV.k < 1.2) GV.k = 1.2;                           // close enough to read the names around it
  GV.tx = GV.w / 2 - nd.x * GV.k;
  GV.ty = GV.h / 2 - nd.y * GV.k;
  graphZoomLabel();
  graphRun();
}

/* ----- the Map | Graph switch and the Local controls ----- */
function syncLineageUi() {
  var onLin = openTab() === "graph", graph = state.lnMode === "graph";
  $("lnModeSeg").hidden = !onLin;
  $("canvas").hidden = graph;
  GV.wrap.hidden = !graph;
  $("gLocalBox").hidden = !(onLin && graph);
  $("gLocalBox").classList.toggle("off", !state.gLocal);
  $("gLocal").checked = state.gLocal;
  if (onLin) $("densitySeg").hidden = graph;
  [["lnMap", !graph], ["lnGraph", graph]].forEach(function (b) {
    $(b[0]).classList.toggle("on", b[1]);
    $(b[0]).setAttribute("aria-pressed", String(b[1]));
  });
  $("gDepthSeg").querySelectorAll("button").forEach(function (b) {
    var on = Number(b.getAttribute("data-depth")) === state.gDepth;
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", String(on));
  });
  $("zLevel").textContent = Math.round((graph ? GV.k : state.zoom) * 100) + "%";
  $("zFit").title = graph ? "Fit the graph to the window" : "Fit to screen";
}
function setLnMode(mode) {
  state.lnMode = mode;
  try { localStorage.setItem(LN_MODE_KEY, mode); } catch (e) {}
  syncLineageUi();
  if (mode === "graph") { graphResize(); graphRebuild(); }
  else if (state.focus) scrollToNode(state.focus);
}
function setGraphLocal(on) {
  state.gLocal = on;
  syncLineageUi();
  graphRebuild();
}
$("lnMap").addEventListener("click", function () { setLnMode("map"); });
$("lnGraph").addEventListener("click", function () { setLnMode("graph"); });
$("gLocal").addEventListener("change", function (e) { setGraphLocal(e.target.checked); });
$("gDepthSeg").addEventListener("click", function (e) {
  var b = e.target.closest("button[data-depth]");
  if (!b) return;
  state.gDepth = Number(b.getAttribute("data-depth"));
  syncLineageUi();
  graphRebuild();
});

/* Hooks the lineage map calls, so both views stay in step. */
/* They can run before this file's own setup (function declarations are hoisted), so each checks GV first. */
function graphOnRender() {
  if (!GV) return;
  syncLineageUi();
  if (state.lnMode === "graph") graphRebuild();
}
function graphOnFocus() {
  if (!GV || state.lnMode !== "graph") return;
  if (state.gLocal) graphRebuild(); else graphRun();
}
function graphOnSearch() { if (GV && state.lnMode === "graph") graphRun(); }
function graphOnShow() {
  if (!GV) return;
  syncLineageUi();
  if (state.lnMode !== "graph") return;
  if (graphResize()) { if (!GV.nodes.length) graphRebuild(); else { if (GV.autoFit) graphFit(); graphRun(); } }
}
window.addEventListener("resize", function () {
  if (state.lnMode === "graph" && !GV.wrap.hidden && graphResize()) graphRun();
});
if (window.ResizeObserver) {
  new ResizeObserver(function () {
    if (state.lnMode === "graph" && !GV.wrap.hidden && graphResize()) graphRun();
  }).observe(GV.wrap);
}
$("themeBtn").addEventListener("click", function () { if (state.lnMode === "graph") graphRun(); });
if (window.matchMedia) {
  var gmq = window.matchMedia("(prefers-color-scheme: dark)");
  if (gmq.addEventListener) gmq.addEventListener("change", function () { if (state.lnMode === "graph") graphRun(); });
}
