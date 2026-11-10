var PREVIEW_SCALE = 0.5;   // screen pixels per report pixel, same for every page

/* ---------- Reports view ----------
   Each report: pages on the left, the selected page's canvas in the middle,
   its filters on the right (visual, page, report level), and the visuals of
   that page underneath. Selecting a visual works from either side. */
var PV_SEQ = 0;
function pagePreview(p) {
  var W = p.width || 1280, H = p.height || 720, k = 1 / PREVIEW_SCALE, fid = "pvsh" + (++PV_SEQ), clipSeq = 0;
  var boxes = (p.layout || []).filter(function (b) { return b.w > 0 && b.h > 0; })
    // Shapes, buttons and images go underneath, data visuals on top, each group in z order,
    // so a page with dozens of overlay buttons still shows its charts clearly.
    .sort(function (a, b) { return ((a.id ? 1 : 0) - (b.id ? 1 : 0)) || ((a.z || 0) - (b.z || 0)); });
  var kids = [
    sg("defs", null, sg("filter", {id: fid, x: "-10%", y: "-10%", width: "120%", height: "120%"},
      sg("feDropShadow", {dx: 0, dy: 2 * k, stdDeviation: 4 * k, "flood-color": "#17212b", "flood-opacity": ".18"}))),
    sg("rect", {"class": "pv-page", width: W, height: H, filter: "url(#" + fid + ")"})
  ];
  boxes.forEach(function (b) {
    var cls = "pv-box " + (b.id ? "t-visual" : "pv-other") + (b.hidden ? " pv-hidden" : "");
    var wpx = b.w / k, hpx = b.h / k;
    var g = sg("g", {"class": cls, "data-vid": b.id || null},
      sg("rect", {x: b.x, y: b.y, width: b.w, height: b.h, rx: 2 * k, "vector-effect": "non-scaling-stroke"}));
    if (wpx >= 30 && hpx >= 20) {
      // Labels are drawn in page units but rescaled to a fixed size, and clipped to the box.
      var cid2 = fid + "c" + (++clipSeq);
      addKids(g, [
        sg("clipPath", {id: cid2}, sg("rect", {x: b.x, y: b.y, width: b.w, height: b.h})),
        sg("g", {"clip-path": "url(#" + cid2 + ")"},
          sg("g", {transform: "translate(" + (b.x + 5 * k) + "," + (b.y + 4 * k) + ")"},
            sg("g", {"class": "fit"}, [
              iconG(b.icon, {"class": "pv-ico", transform: "scale(" + (13 / 24) + ")"}),
              sg("text", {x: 17, y: 10.5, "font-size": 11}, b.label + (b.hidden ? " (hidden)" : "")),
              hpx >= 36 && b.label.indexOf(b.type) !== 0
                ? sg("text", {"class": "sub", x: 17, y: 24, "font-size": 10}, b.type) : null
            ])))
      ]);
    }
    if (b.id && wpx >= 46 && hpx >= 24) {
      /* Anchored to the box corner; sized in real pixels by sizePreviewActions(). */
      g.appendChild(sg("g", {"class": "pv-act", "data-go-vid": b.id, role: "button", tabindex: 0,
                             "aria-label": "Show " + b.label + " in the lineage map",
                             transform: "translate(" + (b.x + b.w) + "," + b.y + ")"}, [
        sg("g", {"class": "fit"}, [
          sg("rect", {"class": "bg", x: -23, y: 3, width: 20, height: 20, rx: 4}),
          iconG("nav_lineage", {transform: "translate(-20,6) scale(" + (14 / 24) + ")"})
        ]),
        sg("title", null, "Show in lineage")
      ]));
    }
    g.appendChild(sg("title", null, b.label + " · " + b.type + "\nPosition x " + Math.round(b.x) + ", y " + Math.round(b.y) +
                  " · size " + Math.round(b.w) + " × " + Math.round(b.h) + (b.hidden ? "\nHidden" : "")));
    kids.push(g);
  });
  return h("div", {"class": "pv", style: "max-width:" + Math.round(W + 16 * k) + "px;max-height:" + Math.round(H + 16 * k) + "px"},
    sg("svg", {viewBox: (-8 * k) + " " + (-8 * k) + " " + (W + 16 * k) + " " + (H + 16 * k),
               preserveAspectRatio: "xMidYMid meet", role: "img", "aria-label": "Layout of page " + p.name}, kids));
}

/* The top row is as tall as a 16:9 canvas of the available width (within limits),
   so the canvas always fills its cell and a wider canvas gives a bigger page. */
function sizeReportRows(root) {
  var cap = Math.min(window.innerHeight * 0.76, 760);
  (root && root.matches && root.matches("section.rep") ? [root]
    : Array.prototype.slice.call((root || $("reportDoc")).querySelectorAll("section.rep"))).forEach(function (sec) {
    if (sec.classList.contains("collapsed") || sec.hidden) return;
    var row = sec.querySelector(".row1"), c = sec.querySelector(".rcanvas");
    if (!row || !c || !c.clientWidth) return;
    var h = Math.max(380, Math.min(cap, Math.round(c.clientWidth * 9 / 16)));
    row.style.height = h + "px";
  });
}
/* The action chips are drawn in page units, so rescale them to a fixed size. */
function sizePreviewActions(root) {
  sizeReportRows(root);
  (root || $("reportDoc")).querySelectorAll(".pv-slot:not([hidden]) .pv").forEach(function (pv) {
    var page = pv.querySelector(".pv-page");
    if (!page || typeof page.getBoundingClientRect !== "function") return;
    var box = page.getBoundingClientRect();
    var W = +(page.getAttribute("width") || 0);
    if (!box.width || !W) return;
    var u = W / box.width;                       // page units per screen pixel
    pv.querySelectorAll("g.fit").forEach(function (g) {
      g.setAttribute("transform", "scale(" + u + ")");
    });
  });
}
function filterCard(id) {
  var n = byId.get(id);
  if (!n) return null;
  return h("a", {"class": "card fcard " + typeCls(n), "data-go": id, title: n.broken ? "Missing from its semantic model" : null}, [
    h("span", {"class": "bar"}), icon(iconName(n), 16, typeCls(n)),
    h("span", {"class": "fname"}, n.label), n.table ? h("small", null, n.table) : null
  ]);
}
/* A field on a visual: the chip itself just belongs to the row; its two small
   buttons open the field in the lineage map or in the Model view. */
function fieldChip(id) {
  var n = byId.get(id);
  if (!n) return null;
  var inModel = !n.broken && !n.external && (n.type === "column" || n.type === "measure" || n.type === "table");
  return h("span", {"class": "card fcard fchip " + typeCls(n), title: n.broken ? "Missing from its semantic model" : null}, [
    h("span", {"class": "bar"}), icon(iconName(n), 16, typeCls(n)),
    h("span", {"class": "fname"}, n.label), n.table ? h("small", null, n.table) : null,
    h("span", {"class": "fact"}, [
      h("button", {"data-fact": "graph", "data-fid": id, title: "Show in lineage",
                   "aria-label": "Show " + n.label + " in the lineage map"}, icon("nav_lineage", 13)),
      inModel ? h("button", {"data-fact": "model", "data-fid": id, title: "Show in Model",
                             "aria-label": "Show " + n.label + " in the Model view"}, icon("nav_model", 13)) : null
    ])
  ]);
}
function pageCard(p, on) {
  var kind = p.kind ? p.kind + " page" : "";
  return h("button", {"class": "pcard card" + (on ? " on" : ""), "data-p": p.id}, [
    h("span", {"class": "bar"}), icon("page", 18, "t-page"),
    h("span", {"class": "ct"}, [
      h("b", {"class": p.hidden ? "hid" : null}, p.name),
      h("small", null, Math.round(p.width || 1280) + " × " + Math.round(p.height || 720) + " · " +
                       plural(p.visuals.length, "data visual", "data visuals") + (kind ? " · " + kind : ""))
    ]),
    p.hidden ? icon("hidden", 14, "is-muted") : null
  ]);
}
function visualRow(vid) {
  var v = byId.get(vid), d = v.detail, byRole = {};
  d.fields.forEach(function (f) { (byRole[f.role] = byRole[f.role] || []).push(f.id); });
  var vtype = (d.props.filter(function (x) { return x[0] === "Visual type"; })[0] || ["", ""])[1];
  return h("div", {"class": "vrow card", "data-vid": vid, tabindex: 0, role: "button"}, [
    h("span", {"class": "bar"}),
    h("div", {"class": "vname"}, [
      icon(iconName(v), 18, "t-visual"), h("b", null, v.label),
      v.hidden ? h("span", {"class": "vhid", title: "Hidden visual"}, icon("hidden", 15)) : null,
      h("button", {"class": "rowact", "data-go-vid": vid, title: "Show in lineage",
                   "aria-label": "Show " + v.label + " in the lineage map"}, icon("nav_lineage", 14))
    ]),
    h("div", {"class": "vtype"}, vtype),
    h("div", {"class": "vfields"}, Object.keys(byRole).map(function (r) {
      return h("div", {"class": "roleline"}, [h("span", {"class": "role"}, r), h("div", {"class": "fchips"}, byRole[r].map(fieldChip))]);
    }))
  ]);
}
function fempty(text) { return h("p", {"class": "fempty"}, text); }
function reportBlock(r, pages) {
  var uses = r.key ? (r.model ? (MODEL_BY_KEY.get(r.model) || {}).name : r.external + " (published)") : null;
  var sec = h("section", {"class": "rep", id: "rep-" + (r.key || ""), "data-rkey": r.key || ""},
    h("button", {"class": "rep-h", "aria-expanded": "true", title: "Click to collapse this report"}, [
      icon("nav_report", 20, "k-report"), r.name,
      uses ? h("span", {"class": "muted"}, "uses " + uses) : null,
      h("span", {"class": "rep-chev"})
    ]));
  if (!pages.length) return addKids(sec, h("p", {"class": "muted rep-empty"}, "This report has no pages."));
  var rfid = "pg:" + (r.key || "") + "\u241f__report__";
  var reportFilters = byId.has(rfid) ? (IN.get(rfid) || []) : [];
  var row1 = h("div", {"class": "row1"}, [
    h("div", {"class": "rside"}, [
      h("div", {"class": "pgroup"}, [
        h("h5", {"class": "phead"}, ["Pages ", h("span", {"class": "cnt"}, pages.length)]),
        pages.map(function (p, i) { return pageCard(p, i === 0); })
      ]),
      h("div", {"class": "fgroup narrow-only"})
    ]),
    h("div", {"class": "rcanvas"}, pages.map(function (p, i) {
      return h("div", {"class": "pv-slot", "data-p": p.id, hidden: i > 0}, pagePreview(p));
    })),
    h("div", {"class": "rfilters"}, [
      h("div", {"class": "fhead"}, [h("span", null, "Filters"), h("button", {"class": "fbtn", "aria-label": "Hide filters", title: "Hide filters"})]),
      h("button", {"class": "frail", "aria-label": "Show filters", title: "Show filters"},
        [h("span", {"class": "frail-ic"}), h("span", {"class": "rail-label"}, "Filters")]),
      h("div", {"class": "fsec"}, [
        h("h5", null, ["Visual level filters ", h("span", {"class": "vfcount"}, "—")]),
        fempty("Select a visual on the canvas to see its filters."),
        pages.map(function (p) {
          return p.visuals.map(function (vid) {
            var f = (byId.get(vid).detail.fields || []).filter(function (x) { return x.role === "Filter"; });
            return h("div", {"class": "vfilters", "data-vid": vid, hidden: true},
              f.length ? f.map(function (x) { return filterCard(x.id); }) : fempty("This visual has no filters of its own."));
          });
        })
      ]),
      h("div", {"class": "fsec"}, [
        h("h5", null, ["Page level filters ", h("span", {"class": "pfcount"}, 0)]),
        pages.map(function (p, i) {
          return h("div", {"class": "pfilters", "data-p": p.id, hidden: i > 0},
            p.filters.length ? p.filters.map(filterCard) : fempty("No page level filters."));
        })
      ]),
      h("div", {"class": "fsec"}, [
        h("h5", null, ["Report level filters ", h("span", null, reportFilters.length)]),
        reportFilters.length ? reportFilters.map(filterCard) : fempty("No report level filters.")
      ])
    ])
  ]);
  var row2 = h("div", {"class": "row2"}, pages.map(function (p, i) {
    return h("div", {"class": "vrows", "data-p": p.id, hidden: i > 0}, [
      h("div", {"class": "tbar"}, [
        h("h5", {"class": "phead"}, ["Visuals on this page ", h("span", {"class": "cnt"}, p.visuals.length)]),
        h("span", {"class": "tsearch"}, [icon("ui_search", 14),
          h("input", {type: "search", "class": "rowq", placeholder: "Search visuals and fields", "aria-label": "Search visuals and fields"})])
      ]),
      p.visuals.length ? p.visuals.map(visualRow) : h("p", {"class": "muted"}, "No visual on this page uses data.")
    ]);
  }));
  return addKids(sec, [row1, row2]);
}
function buildReport() {
  var reps = REPORTS.length ? REPORTS.slice().sort(function (a, b) { return a.name.localeCompare(b.name); })
                            : [{key: "", name: D.meta.name, model: null}];
  var out = [];
  if (!D.pages.length) out.push(h("p", {"class": "muted"}, "No report was found in this project."));
  else reps.forEach(function (r) {
    var pages = r.key ? D.pages.filter(function (p) { return p.rkey === r.key; }) : D.pages;
    out.push(reportBlock(r, pages));
  });
  fill($("reportDoc"), out);
  $("reportDoc").querySelectorAll("section.rep").forEach(function (sec) { syncPageFilterCount(sec); });
  reportSearch(state.query || "");
  if (typeof applyFilterPane === "function") {
    var saved = "expanded";
    try { saved = localStorage.getItem(FILTERS_KEY) || "expanded"; } catch (e) {}
    applyFilterPane(saved === "collapsed");
  }
  sizePreviewActions();
}

function syncPageFilterCount(sec) {
  var open = sec.querySelector(".pfilters:not([hidden])");
  var n = open ? open.querySelectorAll(".fcard").length : 0;
  sec.querySelector(".pfcount").textContent = n;
}
/* Show one page of a report. */
function showPage(rkey, pid, scroll) {
  var sec = null;
  $("reportDoc").querySelectorAll("section.rep").forEach(function (x) {
    if (x.getAttribute("data-rkey") === (rkey || "")) sec = x;
  });
  if (!sec) return null;
  var cards = Array.prototype.slice.call(sec.querySelectorAll(".pcard"));
  var known = cards.some(function (c) { return c.getAttribute("data-p") === pid; });
  var target = known ? pid : (cards.length ? cards[0].getAttribute("data-p") : null);
  if (target) {
    sec.querySelectorAll(".pv-slot, .vrows, .pfilters").forEach(function (x) {
      x.hidden = x.getAttribute("data-p") !== target;
    });
    cards.forEach(function (c) { c.classList.toggle("on", c.getAttribute("data-p") === target); });
    selectVisual(sec, null);
    syncPageFilterCount(sec);
    fitCardLines(sec);
    sizePreviewActions(sec);
  }
  if (scroll) sec.scrollIntoView({block: "start"});
  return sec;
}
/* Select a visual: canvas box, its row and its filters move together. */
function selectVisual(sec, vid) {
  sec.querySelectorAll("g.pv-box.sel, .vrow.on").forEach(function (x) { x.classList.remove("sel", "on"); });
  sec.querySelectorAll(".vfilters").forEach(function (x) { x.hidden = true; });
  var empty = sec.querySelector(".fsec .fempty"), count = sec.querySelector(".vfcount");
  if (!vid) {
    if (empty) empty.hidden = false;
    count.textContent = "—";
    return;
  }
  sec.querySelectorAll('g.pv-box[data-vid]').forEach(function (g) {
    if (g.getAttribute("data-vid") === vid) g.classList.add("sel");
  });
  sec.querySelectorAll(".vrow").forEach(function (rw) {
    if (rw.getAttribute("data-vid") === vid) rw.classList.add("on");
  });
  var block = null;
  sec.querySelectorAll(".vfilters").forEach(function (x) { if (x.getAttribute("data-vid") === vid) block = x; });
  if (empty) empty.hidden = true;
  if (block) {
    block.hidden = false;
    count.textContent = block.querySelectorAll(".fcard").length;
  } else count.textContent = "0";
}
/* Header search on the Reports view: matches report and page names, visual
   names and types, and the fields each visual uses. */
var RHITS = [];
function reportSearch(q) {
  RHITS = [];
  $("reportDoc").querySelectorAll("section.rep").forEach(function (sec) {
    if (sec.classList.contains("out-scope")) return;      // a workspace report left out of scope
    var rk = sec.getAttribute("data-rkey");
    var repName = (sec.querySelector(".rep-h") || {}).textContent || "";
    var repHit = !!q && repName.toLowerCase().indexOf(q) >= 0;
    var any = false;
    sec.querySelectorAll(".pcard").forEach(function (card) {
      var pid = card.getAttribute("data-p"), rows = null;
      sec.querySelectorAll(".vrows").forEach(function (x) { if (x.getAttribute("data-p") === pid) rows = x; });
      var pageHit = repHit || (!!q && card.textContent.toLowerCase().indexOf(q) >= 0);
      var rowHits = 0;
      if (rows) rows.querySelectorAll(".vrow").forEach(function (r) {
        clearMarks(r);
        var hit = !q || pageHit || r.textContent.toLowerCase().indexOf(q) >= 0;
        r.hidden = !hit;
        if (q && !pageHit && hit) rowHits++;
        if (q && hit) markText(r, q);
      });
      clearMarks(card);
      if (q) markText(card, q);
      var match = !q || pageHit || rowHits > 0;
      card.hidden = !!q && !match;
      card.classList.toggle("match", !!q && match);
      if (q && match) { any = true; RHITS.push({sec: sec, pid: pid}); }
    });
    sec.hidden = !!q && !any;
    if (q && any) sec.classList.remove("collapsed");
  });
  return RHITS.length;
}
function openPage(pid) {
  var n = byId.get(pid);
  if (!n) return;
  switchTab("report");
  showPage(n.rkey || "", pid, true);
}
var FILTERS_KEY = "trailsbi.filtersPane";
function applyFilterPane(collapsed) {
  $("reportDoc").querySelectorAll("section.rep").forEach(function (sec) {
    sec.classList.toggle("fcollapsed", collapsed);
    var btn = sec.querySelector(".fbtn"), ric = sec.querySelector(".frail-ic");
    if (btn) {
      fill(btn, [h("span", {"class": "ic-wide"}, icon(collapsed ? "ui_show" : "ui_hide", 16)),
                 h("span", {"class": "ic-narrow"}, icon("ui_chev", 16))]);
      btn.title = collapsed ? "Show filters" : "Hide filters";
      btn.setAttribute("aria-label", btn.title);
      btn.setAttribute("aria-expanded", String(!collapsed));
    }
    if (ric) fill(ric, icon("ui_show", 16));
  });
  try { localStorage.setItem(FILTERS_KEY, collapsed ? "collapsed" : "expanded"); } catch (e) {}
  sizePreviewActions();
}
(function () {
  var saved = "expanded";
  try { saved = localStorage.getItem(FILTERS_KEY) || "expanded"; } catch (e) {}
  applyFilterPane(saved === "collapsed");
})();
$("reportDoc").addEventListener("click", function (e) {
  var t = e.target;
  if (t.closest && t.closest(".fbtn")) { applyFilterPane(!t.closest("section.rep").classList.contains("fcollapsed")); return; }
  if (t.closest && t.closest(".frail")) { applyFilterPane(false); return; }
  var head = t.closest && t.closest(".rep-h");
  if (head) {
    var sec = head.closest("section.rep");
    var open = sec.classList.toggle("collapsed");
    head.setAttribute("aria-expanded", String(!open));
    head.title = open ? "Click to expand this report" : "Click to collapse this report";
    if (!open) sizePreviewActions(sec);
    return;
  }
  var fa = t.closest && t.closest("[data-fact]");
  if (fa) {
    e.preventDefault(); e.stopPropagation();
    var fn = byId.get(fa.getAttribute("data-fid"));
    if (fa.getAttribute("data-fact") === "model") showInModel(fn); else go(fn.id);
    return;
  }
  var act = t.closest && t.closest("[data-go-vid]");
  if (act) { e.preventDefault(); e.stopPropagation(); go(act.getAttribute("data-go-vid")); return; }
  var pc = t.closest && t.closest(".pcard");
  if (pc) { showPage(pc.closest("section.rep").getAttribute("data-rkey"), pc.getAttribute("data-p"), false); return; }
  var vis = t.closest && (t.closest("g.pv-box[data-vid]") || t.closest(".vrow"));
  if (vis && !(t.closest && t.closest("a[data-go]"))) {
    var sec = vis.closest ? vis.closest("section.rep") : null;
    if (!sec) {                                   // SVG nodes need the owner element
      var host = vis.ownerSVGElement;
      sec = host && host.closest("section.rep");
    }
    if (sec) {
      var vid = vis.getAttribute("data-vid");
      selectVisual(sec, sec.querySelector('.vrow.on[data-vid="' + (window.CSS && CSS.escape ? CSS.escape(vid) : vid) + '"]') ? null : vid);
    }
  }
});
$("reportDoc").addEventListener("keydown", function (e) {
  var rw = e.target.closest && e.target.closest(".vrow");
  if (rw && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    selectVisual(rw.closest("section.rep"), rw.getAttribute("data-vid"));
  }
});
/* Mark matching text inside an element (text nodes only, never inside SVG). */
function clearMarks(root) {
  root.querySelectorAll("mark.hit").forEach(function (m) {
    var parent = m.parentNode;
    parent.replaceChild(document.createTextNode(m.textContent), m);
    parent.normalize();
  });
}
function markText(root, q) {
  if (!q) return;
  var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: function (n) {
      var p = n.parentNode;
      if (!p || p.closest("svg, mark, button, input")) return NodeFilter.FILTER_REJECT;
      return n.nodeValue.toLowerCase().indexOf(q) >= 0 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    }
  });
  var nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(function (n) {
    var text = n.nodeValue, low = text.toLowerCase(), frag = document.createDocumentFragment(), i = 0, j;
    while ((j = low.indexOf(q, i)) >= 0) {
      if (j > i) frag.appendChild(document.createTextNode(text.slice(i, j)));
      var m = document.createElement("mark");
      m.className = "hit";
      m.textContent = text.slice(j, j + q.length);
      frag.appendChild(m);
      i = j + q.length;
    }
    if (i < text.length) frag.appendChild(document.createTextNode(text.slice(i)));
    n.parentNode.replaceChild(frag, n);
  });
}
/* Search inside one page's visual list. */
$("reportDoc").addEventListener("input", function (e) {
  if (!e.target.classList || !e.target.classList.contains("rowq")) return;
  var q = e.target.value.trim().toLowerCase(), list = e.target.closest(".vrows");
  list.querySelectorAll(".vrow").forEach(function (rw) {
    clearMarks(rw);
    rw.hidden = !!q && rw.textContent.toLowerCase().indexOf(q) < 0;
    if (q && !rw.hidden) markText(rw, q);
  });
});

function wireReportPreview(root) {
  function mark(el, on) {
    var vid = el.getAttribute("data-vid"), sec = el.closest ? el.closest("section.rep") : null;
    if (!sec && el.ownerSVGElement) sec = el.ownerSVGElement.closest("section.rep");
    (sec || root).querySelectorAll("[data-vid]").forEach(function (x) {
      if (x.getAttribute("data-vid") === vid) x.classList.toggle("hl", on);
    });
  }
  root.addEventListener("mouseover", function (e) {
    var el = e.target.closest && e.target.closest("[data-vid]");
    if (el) mark(el, true);
  });
  root.addEventListener("mouseout", function (e) {
    var el = e.target.closest && e.target.closest("[data-vid]");
    if (el && !(e.relatedTarget && el.contains && el.contains(e.relatedTarget))) mark(el, false);
  });
}
wireReportPreview($("reportDoc"));
window.addEventListener("resize", function () { sizePreviewActions(); });

