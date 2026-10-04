/* ---------- Model diagram ----------
   Dimensions run along the top row, facts down the left column, both in
   ascending order of how many relationships they have. Tables related to
   another table of the same kind are placed next to it, and tables with no
   relationships sit apart on the right. */
state.mdMode = "list";
state.mdSel = null;                                     // {kind:"table"|"rel", ...}
/* DGAP is the gap between columns and DVGAP the gap between rows; they are the
   same so the grid reads evenly whichever way you scan it. DLOOSE is tighter,
   for the tables with no relationships at all - nothing has to pass between
   them. */
var DW = 230, DVGAP = 96, DGAP = DVGAP, DLOOSE = 40,
    DROW = 22, DHEAD = 34, DMAXROWS = 4, DPAD = 24, DSLOT = 24, DTIGHT = 12;

/* The diagram honours "Show auto date tables" as well. Hidden tables and the
   relationships into them are left out, but each kept relationship remembers
   its index in the model's own list, so a selection survives the toggle. */
function mdVisible(m) {
  var d = m.diagram || {tables: [], rels: []};
  if (state.mdShowAuto)
    return {tables: d.tables, rels: d.rels, ridx: d.rels.map(function (_, i) { return i; })};
  var rels = [], ridx = [];
  d.rels.forEach(function (r, i) { if (!r.auto) { rels.push(r); ridx.push(i); } });
  return {tables: d.tables.filter(function (t) { return !t.auto; }), rels: rels, ridx: ridx};
}
function diagramModels() {
  return (D.meta.models || []).filter(function (m) {
    return m.diagram && mdVisible(m).tables.length;
  });
}
function dCardHeight(t, keys) {
  var rows = keys ? t.cols.filter(function (f) { return keys[t.n + "\u241e" + f.n]; }).length
                  : Math.min(t.cols.length, DMAXROWS);
  return DHEAD + (rows ? rows * DROW + 8 : 0);
}
var DGROUP = 90;                                        // clear water between separate graphs
var DCHAIN = 64;                                        // room for both chips and the arrow between them
function layoutDiagram(dg, widen) {
  var keys = dRelKeys(dg);
  var dCardHeightK = function (t) { return dCardHeight(t, keys); };
  /* A card is normally DW wide; one whose edge carries more lines than that
     will hold is widened to fit them (see layoutDiagramFit). */
  var wOf = function (t) { return Math.max(DW, (widen && widen[t.n]) || 0); };
  var byName = {}, count = {}, isFact = {}, many = {}, one = {};
  dg.tables.forEach(function (t) {
    byName[t.n] = t; count[t.n] = 0; many[t.n] = 0; one[t.n] = 0;
  });
  dg.rels.forEach(function (r) {
    if (count[r.f[0]] === undefined || count[r.t[0]] === undefined) return;
    count[r.f[0]]++; count[r.t[0]]++;
    (r.fc === "many" ? many : one)[r.f[0]]++;
    (r.tc === "many" ? many : one)[r.t[0]]++;
  });
  /* A fact is a table that is mostly on the many side. Counting rather than
     latching keeps a dimension that also points at a parent - a snowflake, a
     country or bridge lookup - out of the fact column. A tie reads as a
     dimension, which is what a table in the middle of a snowflake is. */
  dg.tables.forEach(function (t) { isFact[t.n] = many[t.n] > one[t.n]; });
  /* Two bands of their own: a table joined to everything one-to-one, and one
     joined to everything many-to-many. Both are read as extensions of what they
     hang off rather than as facts or dimensions. */
  var only11 = {}, onlyMM = {};
  dg.tables.forEach(function (t) { only11[t.n] = true; onlyMM[t.n] = true; });
  dg.rels.forEach(function (r) {
    var oo = r.fc === "one" && r.tc === "one", mm = r.fc === "many" && r.tc === "many";
    [r.f[0], r.t[0]].forEach(function (n) {
      if (only11[n] === undefined) return;
      if (!oo) only11[n] = false;
      if (!mm) onlyMM[n] = false;
    });
  });
  dg.tables.forEach(function (t) {                       // no relationships is not a band
    if (!count[t.n]) { only11[t.n] = false; onlyMM[t.n] = false; }
  });
  /* A bridge splits one many-to-many into a many-to-one and a one-to-many, so it
     is the one side of both of its relationships, and one of the two tables
     hanging off it has no other relationship. The pair reads as an extension of
     the table on the thick side. */
  var sides = {};
  dg.tables.forEach(function (t) { sides[t.n] = []; });
  dg.rels.forEach(function (r) {
    if (!sides[r.f[0]] || !sides[r.t[0]]) return;
    sides[r.f[0]].push({to: r.t[0], mine: r.fc});
    sides[r.t[0]].push({to: r.f[0], mine: r.tc});
  });
  var isBridge = {}, thickOf = {}, bridgeOf = {};
  dg.tables.forEach(function (t) {
    var ps = sides[t.n];
    if (ps.length !== 2) return;                         // a bridge joins exactly two tables
    if (!ps.every(function (e) { return e.mine !== "many"; })) return;   // the one side of both
    if ((t.ms || []).length) return;                     // something with measures is a fact
    var thin = ps.filter(function (e) { return count[e.to] === 1; });
    var thick = ps.filter(function (e) { return count[e.to] > 1; });
    if (thin.length !== 1 || thick.length !== 1) return;
    isBridge[t.n] = true;
    thickOf[t.n] = thick[0].to;
    bridgeOf[thin[0].to] = t.n;                          // the table on the thin side
  });
  /* Row of each key column inside a card, so a line can leave from the column
     it actually uses rather than from the middle of the card. */
  function rowsOf(t) {
    var m = {};
    t.cols.filter(function (f) { return keys[t.n + "\u241e" + f.n]; })
          .forEach(function (f, i) { m[f.n] = i; });
    return m;
  }
  /* Tables that only relate to each other are a graph of their own. Each is
     laid out on its own and the pieces are packed afterwards. */
  function components(tables) {
    var idx = {}, parent = [];
    tables.forEach(function (t, i) { idx[t.n] = i; parent[i] = i; });
    function find(i) { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; }
    dg.rels.forEach(function (r) {
      var a = idx[r.f[0]], b = idx[r.t[0]];
      if (a === undefined || b === undefined) return;
      var ra = find(a), rb = find(b);
      if (ra !== rb) parent[ra] = rb;
    });
    var groups = {};
    tables.forEach(function (t, i) { (groups[find(i)] = groups[find(i)] || []).push(t); });
    return Object.keys(groups).map(function (k) { return groups[k]; })
      .sort(function (a, b) { return b.length - a.length || a[0].n.localeCompare(b[0].n); });
  }
  /* One graph: dimensions across the top, facts down the left, both in
     ascending order of how many relationships they have. Local coordinates. */
  function placeGroup(tables) {
    var names = {};
    tables.forEach(function (t) { names[t.n] = 1; });
    var rels = dg.rels.filter(function (r) { return names[r.f[0]] && names[r.t[0]]; });
    var inBand = function (t) {
      return only11[t.n] || onlyMM[t.n] || isBridge[t.n] || bridgeOf[t.n];
    };
    var band = tables.filter(inBand);
    var core = tables.filter(function (t) { return !inBand(t); });
    var facts = core.filter(function (t) { return isFact[t.n]; });
    var dims = core.filter(function (t) { return !isFact[t.n]; });
    var asc = function (a, b) { return count[a.n] - count[b.n] || a.n.localeCompare(b.n); };
    facts.sort(asc); dims.sort(asc);
    /* Keep same-kind pairs together: the one with fewer relationships moves
       next to the one with more. */
    function pairUp(list) {
      var order = list.map(function (t) { return t.n; });
      rels.forEach(function (r) {
        var a = order.indexOf(r.f[0]), b = order.indexOf(r.t[0]);
        if (a < 0 || b < 0 || a === b) return;
        var hi = count[r.f[0]] >= count[r.t[0]] ? r.f[0] : r.t[0];
        var lo = hi === r.f[0] ? r.t[0] : r.f[0];
        order.splice(order.indexOf(lo), 1);
        order.splice(order.indexOf(hi) + 1, 0, lo);
      });
      return order.map(function (n) { return byName[n]; });
    }
    facts = pairUp(facts); dims = pairUp(dims);
    /* Who each table is joined to, within this graph. */
    function partners(name) {
      var out = [];
      rels.forEach(function (r) {
        if (r.f[0] === name) out.push(r.t[0]);
        else if (r.t[0] === name) out.push(r.f[0]);
      });
      return out;
    }
    /* Which lane a band table takes depends on what it hangs off, not only on
       its cardinality: whatever it extends, it sits beside that. */
    var dimSet = {}, factSet = {};
    dims.forEach(function (t) { dimSet[t.n] = 1; });
    facts.forEach(function (t) { factSet[t.n] = 1; });
    function joinedOnlyTo(name, set) {
      var ps = partners(name);
      return ps.length > 0 && ps.every(function (p) { return set[p]; });
    }
    var topRow = [], leftCol = [];
    band.forEach(function (t) {
      var bridge = isBridge[t.n] ? t.n : bridgeOf[t.n];
      if (bridge) (factSet[thickOf[bridge]] ? leftCol : topRow).push(t);
      else if (only11[t.n]) (joinedOnlyTo(t.n, factSet) ? leftCol : topRow).push(t);
      else (joinedOnlyTo(t.n, dimSet) ? topRow : leftCol).push(t);
    });
    var local = {}, w = 0, h = 0;
    var widest = function (list) { return Math.max.apply(null, list.map(wOf).concat([0])); };
    var leftColW = leftCol.length ? widest(leftCol) + DGAP : 0;   // the band column before the facts
    var factColW = facts.length ? widest(facts) + DGAP : 0;
    var factX = leftColW;
    var dimX0 = leftColW + factColW;
    var topRowH = Math.max.apply(null, topRow.map(dCardHeightK).concat([0]));
    var dimRowH = Math.max.apply(null, dims.map(dCardHeightK).concat([0]));
    var dimY = topRow.length ? topRowH + DVGAP : 0;      // the band row sits above
    var dimIdx = {};
    dims.forEach(function (t, i) { dimIdx[t.n] = i; });
    /* The band row: over the dimension each table is joined to, else the nearest
       free slot on either side. Slots inside the dimension row are used up
       first; only when they are all taken does the row run past the last one.
       Slots are handed out before any x is worked out, because a band card can
       be wider than the dimension it sits over and the column has to fit both. */
    var taken = {}, slotOf = {}, lastCol = Math.max(0, dims.length - 1);
    function freeSlot(want) {
      for (var d = 0; d <= lastCol + 1; d++) {
        var r = want + d, l = want - d;
        if (r <= lastCol && !taken[r]) return r;
        if (d > 0 && l >= 0 && !taken[l]) return l;
      }
      var i = lastCol + 1;                               // the row has to grow
      while (taken[i]) i++;
      return i;
    }
    function putTop(t, want) {
      var i = freeSlot(want);
      taken[i] = 1;
      slotOf[t.n] = i;
    }
    function topWant(t) {
      var want = Infinity;
      partners(t.n).forEach(function (p) {
        if (dimIdx[p] !== undefined) want = Math.min(want, dimIdx[p]);
      });
      return want === Infinity ? 0 : want;
    }
    var thinIn = {};
    topRow.forEach(function (t) { if (bridgeOf[t.n]) thinIn[bridgeOf[t.n]] = t; });
    // a bridge and its thin table are placed together so they stay side by side
    topRow.filter(function (t) { return isBridge[t.n] && thinIn[t.n]; })
      .map(function (t) { return {t: t, want: topWant(t)}; })
      .sort(function (a, b) { return a.want - b.want || a.t.n.localeCompare(b.t.n); })
      .forEach(function (e) {
        putTop(e.t, e.want);
        putTop(thinIn[e.t.n], slotOf[e.t.n]);
      });
    topRow.filter(function (t) { return !slotOf[t.n]  && slotOf[t.n] !== 0; })
      .map(function (t) { return {t: t, want: topWant(t)}; })
      .sort(function (a, b) { return a.want - b.want || a.t.n.localeCompare(b.t.n); })
      .forEach(function (e) { putTop(e.t, e.want); });
    /* Every column is as wide as the widest card standing in it, band or
       dimension, and the columns are laid out left to right from there. */
    var colW = [];
    var setCol = function (i, wd) { colW[i] = Math.max(colW[i] || DW, wd); };
    dims.forEach(function (t, i) { setCol(i, wOf(t)); });
    topRow.forEach(function (t) { setCol(slotOf[t.n], wOf(t)); });
    var colAt = [], cx = dimX0;
    for (var ci = 0; ci < colW.length; ci++) {
      if (colW[ci] === undefined) colW[ci] = DW;          // a slot nobody stands in
      colAt[ci] = cx;
      cx += colW[ci] + DGAP;
    }
    var colX = function (i) { return colAt[i] === undefined ? dimX0 + i * (DW + DGAP) : colAt[i]; };
    dims.forEach(function (t, i) {
      local[t.n] = {x: colX(i), y: dimY, w: wOf(t), h: dCardHeightK(t), role: "dim", rows: rowsOf(t)};
    });
    topRow.forEach(function (t) {
      local[t.n] = {x: colX(slotOf[t.n]), y: 0, w: wOf(t), h: dCardHeightK(t),
                    role: "one", rows: rowsOf(t)};
    });
    var fy0 = dimY + (dims.length ? dimRowH + DVGAP : 0);
    var fy = fy0, factY = {};
    facts.forEach(function (t) {
      factY[t.n] = fy;
      local[t.n] = {x: factX, y: fy, w: wOf(t), h: dCardHeightK(t), role: "fact", rows: rowsOf(t)};
      fy += dCardHeightK(t) + DVGAP;
    });
    /* The band column, before the facts: each card sits level with the table it
       extends. Its line runs into that card's left edge, clear of the lines
       leaving on the right. */
    var bottom = -Infinity;
    function putLeft(t, want) {
      var hgt = dCardHeightK(t);
      var y = bottom === -Infinity ? want : Math.max(want, bottom + DVGAP);
      local[t.n] = {x: 0, y: y, w: wOf(t), h: hgt, role: "mm", rows: rowsOf(t)};
      bottom = y + hgt;
    }
    function leftWant(t) {
      var want = Infinity;
      partners(t.n).forEach(function (p) { if (local[p]) want = Math.min(want, local[p].y); });
      return Math.max(want === Infinity ? fy0 : want, dimY);
    }
    var thinLeft = {};
    leftCol.forEach(function (t) { if (bridgeOf[t.n]) thinLeft[bridgeOf[t.n]] = t; });
    leftCol.filter(function (t) { return !bridgeOf[t.n]; })
      .map(function (t) { return {t: t, want: leftWant(t)}; })
      .sort(function (a, b) { return a.want - b.want || a.t.n.localeCompare(b.t.n); })
      .forEach(function (e) {
        putLeft(e.t, e.want);
        if (thinLeft[e.t.n]) putLeft(thinLeft[e.t.n], local[e.t.n].y);   // straight underneath
      });
    Object.keys(local).forEach(function (n) {
      w = Math.max(w, local[n].x + local[n].w);
      h = Math.max(h, local[n].y + local[n].h);
    });
    return {pos: local, w: w, h: h, facts: facts, dims: dims};
  }
  /* A graph of three tables or fewer is a chain, so it reads best on one line:
     the hub in the middle, its neighbours either side, and no card sitting on
     top of a relationship. Both shapes are worked out; the packer picks. */
  function placeChain(tables) {
    var names = {};
    tables.forEach(function (t) { names[t.n] = 1; });
    var rels = dg.rels.filter(function (r) { return names[r.f[0]] && names[r.t[0]]; });
    if (tables.length > 3 || rels.length > tables.length - 1) return null;   // not a simple chain
    var deg = {};
    tables.forEach(function (t) { deg[t.n] = 0; });
    rels.forEach(function (r) { deg[r.f[0]]++; deg[r.t[0]]++; });
    var order;
    if (tables.length === 1) order = tables.slice();
    else if (tables.length === 2) order = [byName[rels[0].f[0]], byName[rels[0].t[0]]];
    else {
      var byDeg = tables.slice().sort(function (x, y) { return deg[y.n] - deg[x.n] || x.n.localeCompare(y.n); });
      var rest = byDeg.slice(1).sort(function (x, y) { return x.n.localeCompare(y.n); });
      order = [rest[0], byDeg[0], rest[1]];              // the hub goes in the middle
    }
    function lay(vertical) {
      var local = {}, x = 0, y = 0, w = 0, h = 0;
      order.forEach(function (t) {
        var ch = dCardHeightK(t);
        local[t.n] = {x: x, y: y, w: wOf(t), h: ch, role: "chain", rows: rowsOf(t)};
        if (vertical) y += ch + DVGAP; else x += wOf(t) + DCHAIN;
        w = Math.max(w, local[t.n].x + wOf(t));
        h = Math.max(h, local[t.n].y + ch);
      });
      return {pos: local, w: w, h: h, facts: [], dims: order};
    }
    var row = lay(false), col = lay(true);
    row.alt = col; col.alt = row;
    return row;
  }
  /* Tables with no relationships at all: columns down the side, each filled to
     the height the rest of the drawing already takes up before the next one
     starts, so they cost width only once the free height is gone. */
  function placeLoose(tables, maxH) {
    var local = {}, w = 0, h = 0, x = 0, y = 0, cw = 0;
    tables.forEach(function (t) {
      var ch = dCardHeightK(t);
      if (y && y + ch > maxH) { x += cw + DGAP; y = 0; cw = 0; }   // this column is full
      local[t.n] = {x: x, y: y, w: wOf(t), h: ch, role: "loose", rows: rowsOf(t)};
      cw = Math.max(cw, wOf(t));
      y += ch + DLOOSE;
    });
    Object.keys(local).forEach(function (k) {
      w = Math.max(w, local[k].x + local[k].w);
      h = Math.max(h, local[k].y + local[k].h);
    });
    return {pos: local, w: w, h: h, facts: [], dims: []};
  }

  var linked = dg.tables.filter(function (t) { return count[t.n] > 0; });
  var loose = dg.tables.filter(function (t) { return count[t.n] === 0; });
  var blocks = components(linked).map(function (c) { return placeChain(c) || placeGroup(c); });

  /* Packing. The main graph anchors the top left. Every graph after that goes
     next to what is already on the shelf when that costs no extra width;
     otherwise the shape of the whole drawing so far decides - a tall one grows
     sideways, a wide one starts a new shelf below. The tables with no
     relationships come last, after every graph. */
  var pos = {}, facts = [], dims = [], totW = 0, totH = 0;
  var shelfX = DPAD, shelfY = DPAD, shelfBottom = DPAD;
  function put(bk, x, y) {
    Object.keys(bk.pos).forEach(function (n) {
      var q = bk.pos[n];
      pos[n] = {x: q.x + x, y: q.y + y, w: q.w, h: q.h, role: q.role, rows: q.rows};
    });
    facts = facts.concat(bk.facts); dims = dims.concat(bk.dims);
    totW = Math.max(totW, x + bk.w);
    totH = Math.max(totH, y + bk.h);
    shelfX = x + bk.w + DGROUP;
    shelfBottom = Math.max(shelfBottom, y + bk.h);
  }
  if (blocks.length) put(blocks[0], DPAD, DPAD);
  blocks.slice(1).forEach(function (bk) {
    var tall = totH > totW;
    if (bk.alt && tall) bk = bk.alt;                     // a column suits a tall drawing
    if (shelfX + bk.w <= totW) { put(bk, shelfX, shelfY); return; }
    if (tall) { put(bk, shelfX, shelfY); return; }
    shelfY = shelfBottom + DGROUP;                       // new shelf below everything
    shelfBottom = shelfY;
    put(bk, DPAD, shelfY);
  });
  if (loose.length) {
    var free = Math.max(totH - DPAD, dCardHeight(loose[0], keys) + 1);
    put(placeLoose(loose, free), blocks.length ? totW + DGROUP : DPAD, DPAD);
  }
  var W = DPAD, H = DPAD;                               // fit the canvas to the cards
  Object.keys(pos).forEach(function (n) {
    W = Math.max(W, pos[n].x + pos[n].w + DPAD);
    H = Math.max(H, pos[n].y + pos[n].h + DPAD);
  });
  return {pos: pos, width: W, height: H, facts: facts, dims: dims, loose: loose, count: count,
          groups: blocks.length};
}
/* How wide a card has to be for n lines to leave one edge at their natural
   step, plus the 20px of breathing room asked for. */
var DWMAX = 1200;                                       // even a hub has to stop somewhere
function dNeedW(n) { return Math.min(DWMAX, Math.round((n - 1) * DTIGHT + 2 * DEDGE) + 20); }
/* A fan squeezed below its natural step reads as one thick line, so any card
   whose top or bottom edge carries more lines than it can hold is widened and
   the whole graph laid out again. Widening moves cards, which can change which
   edge a line leaves by, so it settles over a few passes. */
function layoutDiagramFit(dg) {
  var L = layoutDiagram(dg), widen = {};
  for (var pass = 0; pass < 3; pass++) {
    var more = false;
    dSlots(dg.rels, L.pos).forEach(function (p) {
      if (!p) return;
      [[p.e1, p.n1], [p.e2, p.n2]].forEach(function (e) {
        var edge = e[0].charAt(0);                       // T and B fan across the width
        if ((edge !== "T" && edge !== "B") || e[1] <= 1) return;
        var name = e[0].slice(2), need = dNeedW(e[1]);
        if (need > (widen[name] || DW)) { widen[name] = need; more = true; }
      });
    });
    if (!more) break;
    L = layoutDiagram(dg, widen);
  }
  return L;
}
function dFieldRow(f, kind, tname) {
  var ic = kind === "measure" ? "measure" : f.calc ? "calccolumn" : "column";
  var cls = kind === "measure" ? "t-measure" : f.calc ? "t-column s-calculated" : "t-column";
  return '<div class="dfield' + (f.h ? " hid" : "") + '" data-t="' + esc(tname || "") + '" data-c="' + esc(f.n) + '">' +
         icon(ic, 13, cls) + '<span>' + esc(f.n) + '</span>' + icon("key", 12, "is-muted") + '</div>';
}
function dRelKeys(dg) {
  var keys = {};
  dg.rels.forEach(function (r) { keys[r.f[0] + "\u241e" + r.f[1]] = 1; keys[r.t[0] + "\u241e" + r.t[1]] = 1; });
  return keys;
}
function dTableCard(t, p, mkey, keys) {
  var ic = t.k === "calc" ? "calctable" : t.k === "fieldparam" ? "fieldparam" : t.k === "calcgroup" ? "calcitem" : "table";
  var c = t.k === "calc" ? "var(--calc)" : "var(--table)";
  var shown = t.cols.filter(function (f) { return keys[t.n + "\u241e" + f.n]; });   // relationship keys only
  var fields = shown.map(function (f) { return dFieldRow(f, "column", t.n); });
  return '<div class="dcard' + (t.h ? " hid" : "") + '" data-t="' + esc(t.n) + '" data-m="' + esc(mkey) + '" tabindex="0" ' +
         'style="left:' + p.x + 'px;top:' + p.y + 'px;width:' + p.w + 'px;--c:' + c + '">' +
         '<div class="dhead">' + icon(ic, 16) + '<b>' + esc(t.n) + '</b></div>' +
         (fields.length ? '<div class="dfields">' + fields.join("") + '</div>' : "") + '</div>';
}
/* Elbow path from the fact's edge to the dimension's edge, with 1 and * marks. */
/* At most one bend. A fact meets a dimension from its right edge to the
   dimension's bottom edge. Each line gets its own slot on both card edges so
   lines never run on top of each other. */
function dSlots(rels, pos) {
  var plan = [], total = {}, used = {}, rowUse = {}, rowTotal = {}, mark = {};
  var ek = function (name, edge) { return edge + "\u241f" + name; };
  rels.forEach(function (r) {
    var a = pos[r.f[0]], b = pos[r.t[0]];
    if (!a || !b) { plan.push(null); return; }
    var isF = function (q) { return q.role === "fact" || q.role === "mm"; };
    var fact = isF(a) ? a : isF(b) ? b : null;
    var dim = a.role === "dim" ? a : b.role === "dim" ? b : null;
    var p;
    if (fact && dim && fact !== dim) {
      var fFirst = fact === a;
      var fn = fFirst ? r.f[0] : r.t[0], dn = fFirst ? r.t[0] : r.f[0];
      var fcol = fFirst ? r.f[1] : r.t[1];
      p = {kind: "fd", fact: fact, dim: dim, factFirst: fFirst, col: fcol,
           c1: fact, c2: dim,
           e1: ek(fn, "R"), e2: ek(dn, "B"), rk: fn + "\u241f" + fcol,
           k1: (fFirst ? r.fc : r.tc) === "many" ? "*" : "1",
           k2: (fFirst ? r.tc : r.fc) === "many" ? "*" : "1"};
      rowTotal[p.rk] = (rowTotal[p.rk] || 0) + 1;       // two lines on one column share a row
    } else {
      var ac = {x: a.x + a.w / 2, y: a.y + a.h / 2}, bc = {x: b.x + b.w / 2, y: b.y + b.h / 2};
      // a card in the row above always drops down to the row below; two cards in
      // that row are side by side and join across
      var banded = (a.role === "one") !== (b.role === "one");
      if (!banded && Math.abs(ac.x - bc.x) >= Math.abs(ac.y - bc.y)) {
        var left = ac.x < bc.x;
        /* Two cards in the same row with a third standing between them cannot
           join straight across - the line would run behind that card, and behind
           any other line already crossing the gap. It drops under the row
           instead and comes back up. */
        var gapLo = Math.min(a.x + a.w, b.x + b.w), gapHi = Math.max(a.x, b.x);
        var yLo = Math.max(a.y, b.y), yHi = Math.min(a.y + a.h, b.y + b.h);
        var floor = Math.max(a.y + a.h, b.y + b.h), blocked = false;
        if (yHi > yLo) Object.keys(pos).forEach(function (n) {
          var c = pos[n];
          if (c === a || c === b) return;
          if (c.x + c.w <= gapLo || c.x >= gapHi) return;
          if (c.y >= yHi || c.y + c.h <= yLo) return;
          blocked = true;
          floor = Math.max(floor, c.y + c.h);
        });
        if (blocked) {
          p = {kind: "h", under: true, a: a, b: b, left: left, c1: a, c2: b, uy: floor + 20,
               e1: ek(r.f[0], "B"), e2: ek(r.t[0], "B"),
               k1: r.fc === "many" ? "*" : "1", k2: r.tc === "many" ? "*" : "1"};
        } else {
          p = {kind: "h", a: a, b: b, left: left, col1: r.f[1], col2: r.t[1], c1: a, c2: b,
               e1: ek(r.f[0], left ? "R" : "L"), e2: ek(r.t[0], left ? "L" : "R"),
               k1: r.fc === "many" ? "*" : "1", k2: r.tc === "many" ? "*" : "1"};
          p.rk = r.f[0] + "\u241f" + r.f[1];
          rowTotal[p.rk] = (rowTotal[p.rk] || 0) + 1;
        }
      } else {
        var up = ac.y > bc.y;
        p = {kind: "v", a: a, b: b, up: up, c1: a, c2: b,
             e1: ek(r.f[0], up ? "T" : "B"), e2: ek(r.t[0], up ? "B" : "T"),
             k1: r.fc === "many" ? "*" : "1", k2: r.tc === "many" ? "*" : "1"};
      }
    }
    total[p.e1] = (total[p.e1] || 0) + 1;
    total[p.e2] = (total[p.e2] || 0) + 1;
    (mark[p.e1] = mark[p.e1] || {})[p.k1] = 1;
    (mark[p.e2] = mark[p.e2] || {})[p.k2] = 1;
    plan.push(p);
  });
  /* Order the lines on each edge by where they are headed - the card at the far
     end, left to right then top to bottom - so they leave in the same order they
     arrive and do not cross each other on the way. */
  var byEdge = {};
  plan.forEach(function (p) {
    if (!p) return;
    (byEdge[p.e1] = byEdge[p.e1] || []).push({p: p, end: 1, to: p.c2});
    (byEdge[p.e2] = byEdge[p.e2] || []).push({p: p, end: 2, to: p.c1});
  });
  Object.keys(byEdge).forEach(function (k) {
    var list = byEdge[k];
    /* Cardinality first, so an edge carrying both keeps all its ones together
       and all its many together and each group can be badged as one. Within a
       group, by where the line is headed, so they do not cross on the way. */
    var markOf = function (m) { return m.end === 1 ? m.p.k1 : m.p.k2; };
    list.sort(function (m, n) {
      var a = markOf(m), b = markOf(n);
      if (a !== b) return a === "1" ? -1 : 1;
      return (m.to.x + m.to.w / 2) - (n.to.x + n.to.w / 2) ||
             (m.to.y + m.to.h / 2) - (n.to.y + n.to.h / 2);
    });
    list.forEach(function (m, i) {
      if (m.end === 1) { m.p.i1 = i; m.p.n1 = list.length; }
      else { m.p.i2 = i; m.p.n2 = list.length; }
    });
  });
  plan.forEach(function (p) {
    if (!p) return;

    if (p.rk) {
      p.ri = (rowUse[p.rk] = (rowUse[p.rk] || 0) + 1) - 1;
      p.rn = rowTotal[p.rk];
    }
  });
  /* Give each bend its own lane. Without this every connector between the same
     two rows turns at the same height and the runs pile into one long rail. */
  function lanes(list, spanOf, atOf) {
    var groups = {};
    list.forEach(function (p) {
      var at = Math.round(atOf(p) / 24);
      (groups[at] = groups[at] || []).push(p);
    });
    Object.keys(groups).forEach(function (g) {
      var items = groups[g].map(function (p) { return {p: p, s: spanOf(p)}; });
      items.sort(function (a, b) { return a.s[0] - b.s[0] || a.s[1] - b.s[1]; });
      var ends = [];                                    // rightmost point used on each lane
      items.forEach(function (it) {
        var ln = 0;
        while (ends[ln] !== undefined && ends[ln] > it.s[0] - 8) ln++;
        ends[ln] = it.s[1];
        it.p.lane = ln;
      });
      items.forEach(function (it) { it.p.lanes = ends.length; });
    });
  }
  var vs = plan.filter(function (p) { return p && p.kind === "v"; });
  lanes(vs, function (p) {
    var x1 = dFan(p.a.x + p.a.w / 2, p.i1, p.n1, p.a.w);
    var x2 = dFan(p.b.x + p.b.w / 2, p.i2, p.n2, p.b.w);
    return [Math.min(x1, x2), Math.max(x1, x2)];
  }, function (p) {
    return (p.up ? p.a.y + p.b.y + p.b.h : p.a.y + p.a.h + p.b.y) / 2;
  });
  var hs = plan.filter(function (p) { return p && p.kind === "h" && !p.under; });
  lanes(hs, function (p) {
    var y1 = dRowY(p.a, p.col1, 0, 1) || dFan(p.a.y + p.a.h / 2, p.i1, p.n1, p.a.h);
    var y2 = dRowY(p.b, p.col2, 0, 1) || dFan(p.b.y + p.b.h / 2, p.i2, p.n2, p.b.h);
    return [Math.min(y1, y2), Math.max(y1, y2)];
  }, function (p) {
    return (p.left ? p.a.x + p.a.w + p.b.x : p.a.x + p.b.x + p.b.w) / 2;
  });
  /* The rails under a row share one height, so they are spread by how far each
     one reaches across rather than by where its bend is. */
  var us = plan.filter(function (p) { return p && p.under; });
  lanes(us, function (p) {
    var x1 = dFan(p.a.x + p.a.w / 2, p.i1, p.n1, p.a.w);
    var x2 = dFan(p.b.x + p.b.w / 2, p.i2, p.n2, p.b.w);
    return [Math.min(x1, x2), Math.max(x1, x2)];
  }, function (p) { return p.uy; });
  return plan;
}
/* Attach points spread out from the middle of an edge but never run past it:
   the more lines an edge carries, the smaller the step, down to a minimum. */
var DEDGE = 14, DMIN = DTIGHT;
function dFan(centre, i, n, extent) {
  if (n <= 1) return centre;
  var step = Math.max(DMIN, Math.min(DSLOT, (extent - 2 * DEDGE) / (n - 1)));
  return Math.round(centre + (i - (n - 1) / 2) * step);
}
/* A 1 / * chip is 18 square on its own line. When the lines on an edge are too
   close for that, the chips for a run of like cardinality merge into one bar
   spanning exactly the lines it speaks for - see dBadges. */
var DCHIPW = 18;
function dChipBox(p) {
  if (!p) return {hw: 0, hh: 0};
  if (p.span) return p.horiz ? {hw: p.span / 2, hh: 9} : {hw: 9, hh: p.span / 2};
  return {hw: DCHIPW / 2, hh: 9};
}
/* The middle of a card's row for a key column, or 0 when it has no such row.
   Two lines on one column share the row, nudged apart. */
function dRowY(card, col, i, n) {
  var row = card.rows ? card.rows[col] : undefined;
  if (row === undefined) return 0;
  return Math.round(card.y + DHEAD + 4 + row * DROW + DROW / 2 +
                    (n > 1 ? (i - (n - 1) / 2) * 7 : 0));
}
/* How far this connector's bend sits from the middle of the gap. */
var DLANE = 18;
function dLaneShift(slot) {
  if (slot.lane === undefined || slot.lanes < 2) return 0;
  return (slot.lane - (slot.lanes - 1) / 2) * DLANE;
}
function dRelPath(slot) {
  if (!slot) return null;
  if (slot.kind === "fd") {
    var f = slot.fact, d = slot.dim;
    // leave the fact from the row of the key column this relationship uses
    var y1 = dRowY(f, slot.col, slot.ri, slot.rn) || dFan(f.y + f.h / 2, slot.i1, slot.n1, f.h);
    var p1 = {x: f.x + f.w, y: y1};
    var p2 = {x: dFan(d.x + d.w / 2, slot.i2, slot.n2, d.w), y: d.y + d.h};
    return {d: "M" + p1.x + "," + p1.y + "H" + p2.x + "V" + p2.y, factFirst: slot.factFirst,
            m1: {x: p1.x + 9, y: p1.y}, m2: {x: p2.x, y: p2.y + 9},
            o1: {x: 1, y: 0}, o2: {x: 0, y: 1},
            segs: [{x1: p1.x, y1: p1.y, x2: p2.x, y2: p1.y}, {x1: p2.x, y1: p1.y, x2: p2.x, y2: p2.y}],
            all: [{x1: p1.x, y1: p1.y, x2: p2.x, y2: p1.y}, {x1: p2.x, y1: p1.y, x2: p2.x, y2: p2.y}]};
  }
  var a = slot.a, b = slot.b;
  if (slot.under) {
    var ab = a.y + a.h, bb = b.y + b.h;
    var ux1 = dFan(a.x + a.w / 2, slot.i1, slot.n1, a.w);
    var ux2 = dFan(b.x + b.w / 2, slot.i2, slot.n2, b.w);
    var uy = Math.round(slot.uy + dLaneShift(slot));
    return {d: "M" + ux1 + "," + ab + "V" + uy + "H" + ux2 + "V" + bb, factFirst: true,
            m1: {x: ux1, y: ab + 9}, m2: {x: ux2, y: bb + 9},
            o1: {x: 0, y: 1}, o2: {x: 0, y: 1},
            segs: [{x1: ux1, y1: ab, x2: ux1, y2: uy}, {x1: ux2, y1: uy, x2: ux2, y2: bb}],
            all: [{x1: ux1, y1: ab, x2: ux1, y2: uy}, {x1: ux1, y1: uy, x2: ux2, y2: uy},
                  {x1: ux2, y1: uy, x2: ux2, y2: bb}]};
  }
  if (slot.kind === "h") {
    var left = slot.left;
    // side by side: leave from the row of the key column, as a fact does
    var q1 = {x: left ? a.x + a.w : a.x,
              y: dRowY(a, slot.col1, slot.ri, slot.rn) || dFan(a.y + a.h / 2, slot.i1, slot.n1, a.h)};
    var q2 = {x: left ? b.x : b.x + b.w,
              y: dRowY(b, slot.col2, 0, 1) || dFan(b.y + b.h / 2, slot.i2, slot.n2, b.h)};
    var qm = Math.round((q1.x + q2.x) / 2 + dLaneShift(slot));
    var s1 = left ? 1 : -1;
    return {d: "M" + q1.x + "," + q1.y + "H" + qm + "V" + q2.y + "H" + q2.x, factFirst: true,
            m1: {x: q1.x + 9 * s1, y: q1.y}, m2: {x: q2.x - 9 * s1, y: q2.y},
            o1: {x: s1, y: 0}, o2: {x: -s1, y: 0},
            segs: [{x1: q1.x, y1: q1.y, x2: qm, y2: q1.y}, {x1: qm, y1: q2.y, x2: q2.x, y2: q2.y}],
            all: [{x1: q1.x, y1: q1.y, x2: qm, y2: q1.y}, {x1: qm, y1: q1.y, x2: qm, y2: q2.y},
                  {x1: qm, y1: q2.y, x2: q2.x, y2: q2.y}]};
  }
  var up = slot.up;
  var r1 = {x: dFan(a.x + a.w / 2, slot.i1, slot.n1, a.w), y: up ? a.y : a.y + a.h};
  var r2 = {x: dFan(b.x + b.w / 2, slot.i2, slot.n2, b.w), y: up ? b.y + b.h : b.y};
  var rm = Math.round((r1.y + r2.y) / 2 + dLaneShift(slot));
  var v1 = up ? -1 : 1;
  return {d: "M" + r1.x + "," + r1.y + "V" + rm + "H" + r2.x + "V" + r2.y, factFirst: true,
          m1: {x: r1.x, y: r1.y + 9 * v1}, m2: {x: r2.x, y: r2.y - 9 * v1},
          o1: {x: 0, y: v1}, o2: {x: 0, y: -v1},
          segs: [{x1: r1.x, y1: r1.y, x2: r1.x, y2: rm}, {x1: r2.x, y1: rm, x2: r2.x, y2: r2.y}],
          all: [{x1: r1.x, y1: r1.y, x2: r1.x, y2: rm}, {x1: r1.x, y1: rm, x2: r2.x, y2: rm},
                {x1: r2.x, y1: rm, x2: r2.x, y2: r2.y}]};
}
/* An arrow on the line shows which way the filter flows.  It always sits ON one
   of the line's own runs: it slides along the path looking for a clear spot
   rather than stepping off to the side, because a badge floating beside a line
   reads as belonging to nothing. */
function dSegLen(sg) { return Math.abs(sg.x2 - sg.x1) + Math.abs(sg.y2 - sg.y1); }
/* Where along a run to try, middle first and then outward to either end. */
var DARROW_TS = [0.5, 0.625, 0.375, 0.75, 0.25, 0.875, 0.125, 1, 0];
function dArrow(pa, toSecond, both, others, lines, mine) {
  var runs = ((pa && (pa.all || pa.segs)) || []).filter(function (sg) { return dSegLen(sg) > 1; });
  if (!runs.length) return "";
  var last = runs[runs.length - 1];
  var w = both ? 22 : 18;
  /* Stay off the end chips: both boxes are 18 tall, the arrow w wide. */
  var blocks = [pa.m1, pa.m2, {x: runs[0].x1, y: runs[0].y1}, {x: last.x2, y: last.y2}]
                 .concat(others || []).filter(Boolean);
  var free = function (px, py, hw, avoidLines) {
    var clearOfChips = blocks.every(function (e) {
      var bx = e.span ? dChipBox(e) : {hw: DCHIPW / 2, hh: 9};
      return Math.abs(px - e.x) >= hw + bx.hw + 2 || Math.abs(py - e.y) >= bx.hh + 11;
    });
    if (!clearOfChips) return false;
    if (!avoidLines || !lines) return true;
    return lines.every(function (L) {
      return L.owner === mine || !dSegInBox(L.sg, px, py, hw + 3, 12);
    });
  };
  /* Longest run first - it has the most room - then the shorter ones. */
  var order = runs.map(function (sg) { return {sg: sg, len: dSegLen(sg)}; })
                  .sort(function (p, q) { return q.len - p.len; });
  var scan = function (hw, avoidLines) {
    for (var oi = 0; oi < order.length; oi++) {
      var sg = order[oi].sg, len = order[oi].len;
      var margin = Math.min(hw + 6, len / 2);           // keep the badge off the elbows
      var span = len - 2 * margin;
      var ux = (sg.x2 - sg.x1) / len, uy = (sg.y2 - sg.y1) / len;
      for (var s = 0; s < DARROW_TS.length; s++) {
        var t = margin + DARROW_TS[s] * span;
        var px = sg.x1 + ux * t, py = sg.y1 + uy * t;
        if (free(px, py, hw, avoidLines)) return {at: {x: px, y: py}, on: sg};
      }
    }
    return null;
  };
  var hit = scan(w / 2, true);
  var bare = !hit;                                      // nowhere clear: the glyph alone, no chip
  if (!hit) hit = scan(5, true);                        // the bare glyph is small enough to fit between lines
  if (!hit) hit = scan(5, false);                       // and at the last, it only has to miss the chips
  if (!hit) hit = {at: {x: (order[0].sg.x1 + order[0].sg.x2) / 2,
                        y: (order[0].sg.y1 + order[0].sg.y2) / 2}, on: order[0].sg};
  var at = hit.at, on = hit.on;
  var mx = Math.round(at.x), my = Math.round(at.y);
  var dx = on.x2 - on.x1, dy = on.y2 - on.y1;
  if (!toSecond) { dx = -dx; dy = -dy; }
  var deg = Math.round(Math.atan2(dy, dx) * 180 / Math.PI);
  var glyph = both ? '<path d="M-6.5,0 L-1.5,-4 L-1.5,4 Z"/><path d="M6.5,0 L1.5,-4 L1.5,4 Z"/>'
                   : '<path d="M-3.5,-4 L4,0 L-3.5,4 Z"/>';
  return '<g class="darrow' + (bare ? " bare" : "") + '">' +
         (bare ? "" : '<rect x="' + (mx - w / 2) + '" y="' + (my - 9) + '" width="' + w +
                      '" height="18" rx="3"/>') +
         '<g transform="translate(' + mx + ',' + my + ') rotate(' + deg + ')">' + glyph + '</g></g>';
}
/* The canvas fits the cards, but a rail routed under a row can reach past the
   lowest one, so the lines get a say in the size too. */
function dCanvasEdge(L, paths, key) {
  var v = key === "y" ? L.height : L.width;
  paths.forEach(function (pa) {
    if (!pa) return;
    (pa.all || pa.segs).forEach(function (sg) {
      v = Math.max(v, sg[key + "1"] + DPAD, sg[key + "2"] + DPAD);
    });
  });
  return Math.round(v);
}
function dCanvasW(L, paths) { return dCanvasEdge(L, paths, "x"); }
function dCanvasH(L, paths) { return dCanvasEdge(L, paths, "y"); }
/* Chips start out one per line. Where an edge is too crowded for that, every
   run of like cardinality merges into a single bar covering exactly the lines
   it speaks for - so a fan of twenty ones reads as one "1" over the whole fan,
   and an edge carrying both shows a "1" bar over its ones and a "*" bar over
   its many. The fan is already ordered by cardinality, so the runs are
   contiguous. */
function dBadges(paths, slots) {
  var edges = {};
  paths.forEach(function (pa, i) {
    var s = slots[i];
    if (!pa || !s) return;
    [[s.e1, "m1", s.k1], [s.e2, "m2", s.k2]].forEach(function (e) {
      if (!e[0] || !pa[e[1]]) return;
      (edges[e[0]] = edges[e[0]] || []).push({pa: pa, end: e[1], mark: e[2]});
    });
  });
  Object.keys(edges).forEach(function (k) {
    var list = edges[k], horiz = k.charAt(0) === "T" || k.charAt(0) === "B";
    var at = function (q) { return horiz ? q.pa[q.end].x : q.pa[q.end].y; };
    list.sort(function (a, b) { return at(a) - at(b); });
    var tight = false;
    for (var i = 1; i < list.length; i++)
      if (at(list[i]) - at(list[i - 1]) < DCHIPW + 2) tight = true;
    if (!tight) return;                                 // there is room for one each
    var runs = [];
    list.forEach(function (q) {
      var r = runs[runs.length - 1];
      if (r && r.mark === q.mark) { r.hi = at(q); r.rest.push(q); return; }
      runs.push({mark: q.mark, lo: at(q), hi: at(q), head: q, rest: []});
    });
    runs.forEach(function (r, ri) {
      if (!r.rest.length) return;                       // one line is just a chip, not a bar
      /* Two runs on one edge meet at the midpoint of the gap between them, so
         neither bar reaches over a line the other one speaks for. */
      var prev = runs[ri - 1], next = runs[ri + 1];
      var lo = prev ? (prev.hi + r.lo) / 2 : r.lo - 9;
      var hi = next ? (r.hi + next.lo) / 2 : r.hi + 9;
      var c = Math.round((lo + hi) / 2);
      var p = r.head.pa[r.head.end];
      var id = "b" + (DBAR_ID++);
      p.text = r.mark;
      p.span = Math.max(DCHIPW, Math.round(hi - lo));   // never narrower than a plain chip
      p.horiz = horiz;
      p.run = id;
      p.table = k.slice(2);                             // the card whose edge this is
      p.count = r.rest.length + 1;
      if (horiz) p.x = c; else p.y = c;
      /* Every line under the bar remembers it, so hovering the bar can light
         all of them and not just the one that happens to carry it. */
      [r.head].concat(r.rest).forEach(function (q) {
        q.pa.runs = (q.pa.runs || []).concat(id);
      });
      r.rest.forEach(function (q) { q.pa[q.end] = null; });   // spoken for by the bar
    });
  });
}
var DBAR_ID = 1;
function dChipPoints(paths) {
  var out = [];
  paths.forEach(function (pa) { if (!pa) return; if (pa.m1) out.push(pa.m1); if (pa.m2) out.push(pa.m2); });
  return out;
}
/* Every line on the drawing, so an arrow can keep off the ones that are not its
   own - a badge sitting on someone else's line reads as a junction. */
function dSegPoints(paths) {
  var out = [];
  paths.forEach(function (pa, i) {
    if (!pa) return;
    (pa.all || pa.segs).forEach(function (sg) { out.push({sg: sg, owner: i}); });
  });
  return out;
}
/* A chip that another line runs through, or another chip sits on, slides
   further out along its own line until it is clear - it stays on the line it
   belongs to either way. */
function dNudgeChips(paths, segs) {
  var all = [];
  paths.forEach(function (pa, i) {
    if (!pa) return;
    if (pa.m1 && pa.o1) all.push({m: pa.m1, o: pa.o1, owner: i});
    if (pa.m2 && pa.o2) all.push({m: pa.m2, o: pa.o2, owner: i});
  });
  all.forEach(function (e) {
    if (e.m.span) return;                               // a bar belongs over its whole run
    var x0 = e.m.x, y0 = e.m.y;
    var clear = function (d) {
      var x = x0 + e.o.x * d, y = y0 + e.o.y * d;
      var onLine = segs.some(function (L) {
        return L.owner !== e.owner && dSegInBox(L.sg, x, y, 11, 11);
      });
      if (onLine) return false;
      var mine = dChipBox(e.m);
      return !all.some(function (o) {
        var his = dChipBox(o.m);
        return o !== e && Math.abs(o.m.x - x) < mine.hw + his.hw + 1 &&
               Math.abs(o.m.y - y) < mine.hh + his.hh + 1;
      });
    };
    var at = [0, 14, 28, 42, 56].filter(clear)[0];
    if (at === undefined) return;                       // nowhere better; leave it on the edge
    e.m.x = x0 + e.o.x * at;
    e.m.y = y0 + e.o.y * at;
  });
}
function dSegInBox(sg, cx, cy, hw, hh) {
  var lo = {x: Math.min(sg.x1, sg.x2), y: Math.min(sg.y1, sg.y2)};
  var hi = {x: Math.max(sg.x1, sg.x2), y: Math.max(sg.y1, sg.y2)};
  return lo.x <= cx + hw && hi.x >= cx - hw && lo.y <= cy + hh && hi.y >= cy - hh;
}
function dMark(p, text, live) {
  if (!p) return "";                                    // a neighbouring bar speaks for this line
  var many = (p.text || text) !== "1";
  var b = dChipBox(p);
  /* A bar stands for a whole run of lines, so it is not part of any one
     relationship's group: it goes in its own layer, over the lines, and names
     the run it speaks for so hovering it can light all of them. */
  var attrs = "";
  if (p.span) {
    attrs = ' data-run="' + p.run + '"' + (live ? ' data-t="' + esc(p.table || "") + '"' : "");
  }
  return '<g class="dmark' + (p.span ? " all dbar" : "") + '"' + attrs + '>' +
         '<rect x="' + (p.x - b.hw) + '" y="' + (p.y - b.hh) + '" width="' + (b.hw * 2) +
         '" height="' + (b.hh * 2) + '" rx="3"/>' +
         '<text class="' + (many ? "many" : "one") + '" x="' + p.x + '" y="' + (p.y + (many ? 5 : 1)) + '">' +
         (many ? "*" : "1") + '</text>' +
         (p.span ? '<title>' + esc(p.count + " relationship" + (p.count === 1 ? "" : "s") +
                                  " on " + (p.table || "this table") + ", " +
                                  (many ? "many" : "one") + " side") + '</title>' : "") +
         '</g>';
}
function buildDiagram() {
  var models = diagramModels(), h = "";
  /* A live-connected model carries no tables, so there is nothing to draw. It
     still gets a section that says where the model lives. */
  var live = (D.meta.models || []).filter(function (m) {
    return m.live && !(m.diagram && mdVisible(m).tables.length);
  });
  if (!models.length && !live.length) h = '<p class="muted">No semantic model to draw.</p>';
  models.forEach(function (m) {
    var V = mdVisible(m), L = layoutDiagramFit(V);
    var slots = dSlots(V.rels, L.pos);
    var paths = V.rels.map(function (r, i) { return dRelPath(slots[i]); });
    var segs = dSegPoints(paths);
    dBadges(paths, slots);
    dNudgeChips(paths, segs);
    var chips = dChipPoints(paths);        // an arrow dodges every chip, not only its own two
    var CW = dCanvasW(L, paths), CH = dCanvasH(L, paths);
    h += '<section class="dsec" data-mkey="' + esc(m.key) + '">' +
         '<h3 class="dtitle">' + icon("ws_model", 18, "k-model") + esc(m.name) + '<span class="muted">' +
         plural(V.tables.length, "table", "tables") + ' · ' +
         plural(V.rels.length, "relationship", "relationships") + '</span>' + dExportMenu() + '</h3>' +
         '<div class="dwrap" data-w="' + CW + '" data-h="' + CH + '">' +
         '<div class="dcanvas" style="width:' + CW + 'px;height:' + CH + 'px">' +
         '<svg class="dlines" width="' + CW + '" height="' + CH + '">';
    var bars = [];                        // drawn last, over the lines they speak for
    V.rels.forEach(function (r, i) {
      var pa = paths[i];
      if (!pa) return;
      var fromMark = r.fc === "many" ? "∗" : "1", toMark = r.tc === "many" ? "∗" : "1";
      var m1 = pa.factFirst ? fromMark : toMark, m2 = pa.factFirst ? toMark : fromMark;
      /* the filter flows from the one side to the many side */
      var firstIsOne = m1 === "1";
      var arrows = r.both ? dArrow(pa, true, true, chips, segs, i)
                          : dArrow(pa, firstIsOne, false, chips, segs, i);
      var marks = "";
      [[pa.m1, m1], [pa.m2, m2]].forEach(function (e) {
        if (!e[0]) return;
        if (e[0].span) bars.push(dMark(e[0], e[1], true));
        else marks += dMark(e[0], e[1]);
      });
      h += '<g class="drel' + (r.active ? "" : " inactive") + '" data-r="' + esc(m.key + "|" + V.ridx[i]) + '"' +
           (pa.runs ? ' data-runs="' + pa.runs.join(" ") + '"' : "") + '>' +
           '<path class="hit" d="' + pa.d + '"/><path class="line" d="' + pa.d + '"/>' + arrows + marks +
           '<title>' + esc(r.f[0] + "[" + r.f[1] + "] → " + r.t[0] + "[" + r.t[1] + "]") + '</title></g>';
    });
    h += '<g class="dbars">' + bars.join("") + '</g></svg>';
    var keys = dRelKeys(V);
    V.tables.forEach(function (t) {
      var p = L.pos[t.n];
      if (p) h += dTableCard(t, p, m.key, keys);
    });
    h += '</div></div></section>';
  });
  live.forEach(function (m) {
    h += '<section class="dsec" data-mkey="' + esc(m.key) + '">' +
         '<h3 class="dtitle">' + icon("ws_model", 18, "k-model") + esc(m.name) +
         '<span class="muted">' + esc(m.live.typeLabel) + '</span></h3>' +
         '<p class="note">No diagram: this semantic model is a live connection to ' +
         esc(m.live.database || m.live.server) + ', so its tables and relationships are defined ' +
         'there rather than in the project.</p></section>';
  });
  $("mdDiagram").innerHTML = h;
  applyDiagramZoom();
  showDiagramSelection();
}
