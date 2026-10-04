/* ---------- collapsible details panes (the lineage and model views share one setting) ---------- */
var SIDE_KEY = "trailsbi.detailsPane";
var SIDES = Array.prototype.slice.call(document.querySelectorAll("aside.side"));
SIDES.forEach(function (side) {
  side.querySelector(".side-hide").innerHTML = icon("ui_hide", 18);
  side.querySelector(".side-show-ic").innerHTML = icon("ui_show", 18);
  side.querySelector(".side-hide").addEventListener("click", function () { setSide(true, true, side); });
  side.querySelector(".side-show").addEventListener("click", function () { setSide(false, true, side); });
});
function setSide(collapsed, remember, origin) {
  SIDES.forEach(function (side) {
    side.classList.toggle("collapsed", collapsed);
    side.querySelector(".side-hide").setAttribute("aria-expanded", String(!collapsed));
    side.querySelector(".side-show").setAttribute("aria-expanded", String(!collapsed));
  });
  if (remember) { try { localStorage.setItem(SIDE_KEY, collapsed ? "collapsed" : "expanded"); } catch (e) {} }
  if (origin) origin.querySelector(collapsed ? ".side-show" : ".side-hide").focus({preventScroll: true});
}
function setRailItem(text) { $("railItem").textContent = text ? "· " + trunc(text, 40) : ""; }
(function () {
  var saved = null;
  try { saved = localStorage.getItem(SIDE_KEY); } catch (e) {}
  if (saved === "collapsed") setSide(true, false);
  else if (saved === null) {            // first visit: the lineage map gets the full width
    var ls = $("side");
    ls.classList.add("collapsed");
    ls.querySelector(".side-hide").setAttribute("aria-expanded", "false");
    ls.querySelector(".side-show").setAttribute("aria-expanded", "false");
  }
})();

/* Type filter: nothing picked = show every type. The first click shows only
   that type; further clicks add or remove types; removing the last one, or
   pressing All, shows everything again. */
var typesBox = $("types");
state.typePick = new Set();
function applyTypePick() {
  state.types = new Set(state.typePick.size ? state.typePick : FILTERS.map(function (t) { return t.k; }));
}
var allBtn = document.createElement("button");
allBtn.className = "t-all";
allBtn.textContent = "All";
allBtn.title = "All types";
allBtn.addEventListener("click", function () {
  if (!state.typePick.size) return;
  state.typePick.clear(); applyTypePick(); syncControls(); render();
});
typesBox.appendChild(allBtn);
FILTERS.forEach(function (t) {
  var b = document.createElement("button");
  b.dataset.k = t.k;
  b.className = "t-" + (t.k === "parameter" ? "query" : t.k);
  b.innerHTML = icon(t.icon, 16, "t-" + (t.k === "parameter" ? "query" : t.k));
  b.setAttribute("aria-label", t.label);
  b.dataset.label = t.label;
  b.addEventListener("click", function () {
    if (state.typePick.has(t.k)) state.typePick.delete(t.k); else state.typePick.add(t.k);
    applyTypePick(); syncControls(); render();
  });
  typesBox.appendChild(b);
});
function syncControls() {
  var picking = state.typePick.size > 0;
  allBtn.classList.toggle("picked", !picking);
  allBtn.setAttribute("aria-pressed", String(!picking));
  typesBox.querySelectorAll("button[data-k]").forEach(function (b) {
    var on = state.typePick.has(b.dataset.k);
    b.classList.toggle("picked", on);
    b.classList.toggle("dim", picking && !on);
    b.setAttribute("aria-pressed", String(on));
    b.title = b.dataset.label;
  });
  ["dCompact", "dDetailed"].forEach(function (id) {
    var on = (id === "dCompact") === (state.dense === "compact");
    $(id).classList.toggle("on", on);
    $(id).setAttribute("aria-pressed", String(on));
  });
  $("optUnused").checked = state.hideUnused;
  $("optAuto").checked = state.hideAuto;
  $("optHidden").checked = state.hideHidden;
  $("optHome").checked = !!state.showHome;
  var changed = (state.hideUnused ? 1 : 0) + (state.hideAuto ? 0 : 1) + (state.hideHidden ? 1 : 0) + (state.showHome ? 1 : 0);
  $("viewBtn").innerHTML = icon("ui_eye", 15) + '<span>View options</span><span class="vcount">' + (changed || "") + '</span>' +
                           icon("ui_chev", 14, "chev");
  $("viewBtn").title = changed ? changed + " view option" + (changed === 1 ? "" : "s") + " changed from the default" : "View options";
}
function setDensity(mode) {
  if (state.dense === mode) return;
  state.dense = mode;
  try { localStorage.setItem(DENSITY_KEY, mode); } catch (e) {}
  applyDensity();
  syncControls();
  render();
}
$("dCompact").addEventListener("click", function () { setDensity("compact"); });
$("dDetailed").addEventListener("click", function () { setDensity("detailed"); });
$("optUnused").addEventListener("change", function (e) { state.hideUnused = e.target.checked; syncControls(); render(); });
$("optAuto").addEventListener("change", function (e) { state.hideAuto = e.target.checked; syncControls(); render(); });
$("optHidden").addEventListener("change", function (e) { state.hideHidden = e.target.checked; syncControls(); render(); });
$("aboutBtn").addEventListener("click", function () { var d = $("about"); if (d.showModal) d.showModal(); else d.setAttribute("open", ""); });
$("aboutClose").addEventListener("click", function () { $("about").close(); });
$("about").addEventListener("click", function (e) { if (e.target === this) this.close(); });   // click outside the card
$("optHome").addEventListener("change", function (e) {
  state.showHome = e.target.checked; wireEdges(state.showHome); syncControls(); render();
});
function setZoom(z) {
  state.zoom = Math.max(0.2, Math.min(2, z));
  $("zLevel").textContent = Math.round(state.zoom * 100) + "%";
  sizeSvg();
}
$("zIn").addEventListener("click", function () { setZoom(state.zoom * 1.25); });
$("zOut").addEventListener("click", function () { setZoom(state.zoom / 1.25); });
$("zLevel").addEventListener("click", function () { setZoom(1); });
/* Fit: the largest zoom at which the whole lineage is visible without scrolling. */
function fitLineage() {
  var cv = $("canvas");
  if (!L || !L.width || !L.height || !cv.clientWidth) return;
  setZoom(Math.min((cv.clientWidth - 16) / L.width, (cv.clientHeight - 16) / L.height, 1));
  cv.scrollTo(0, 0);
}
$("zFit").addEventListener("click", fitLineage);

/* toolbar menus (View options): one open at a time, close on outside click or Esc */
function closeMenus(except) {
  [["viewPop", "viewBtn"], ["mdViewPop", "mdViewBtn"]].forEach(function (m) {
    if (m[0] === except || $(m[0]).hidden) return;
    $(m[0]).hidden = true;
    $(m[1]).setAttribute("aria-expanded", "false");
  });
  document.querySelectorAll(".dexp-pop").forEach(function (p) {     // one per diagram
    if (p.hidden) return;
    p.hidden = true;
    p.parentNode.querySelector(".dexp-btn").setAttribute("aria-expanded", "false");
  });
}
$("viewBtn").addEventListener("click", function (e) {
  e.stopPropagation();
  var open = $("viewPop").hidden;
  closeMenus("viewPop");
  $("viewPop").hidden = !open;
  $("viewBtn").setAttribute("aria-expanded", String(open));
});
$("viewPop").addEventListener("click", function (e) { e.stopPropagation(); });
document.addEventListener("click", function () { closeMenus(); });
document.addEventListener("keydown", function (e) {
  if (e.key !== "Escape") return;
  var open = !$("viewPop").hidden ? "viewBtn" : !$("mdViewPop").hidden ? "mdViewBtn" : null;
  if (open) { closeMenus(); $(open).focus(); return; }
  var t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
  if (openTab() === "graph" && state.focus) { state.focus = null; applyFocus(); emptyPanel(); }
});

svg.addEventListener("click", function (e) {
  var na = e.target.closest("g.nact");
  if (na) { e.stopPropagation(); clearSearch(); runNodeAction(na.getAttribute("data-act"), byId.get(na.getAttribute("data-id"))); return; }
  var g = e.target.closest("g.n");
  if (g) { clearSearch(); focusNode(g.__id, false); }
  else { state.focus = null; applyFocus(); emptyPanel(); }
});
svg.addEventListener("keydown", function (e) {
  var na = e.target.closest && e.target.closest("g.nact");
  if (na && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault(); clearSearch();
    runNodeAction(na.getAttribute("data-act"), byId.get(na.getAttribute("data-id")));
    return;
  }
  var g = e.target.closest && e.target.closest("g.n");
  if (g && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); clearSearch(); focusNode(g.__id, false); }
});
document.addEventListener("click", function (e) {
  var a = e.target.closest("a[data-go]");
  if (a) { e.preventDefault(); go(a.dataset.go); }
});

var hits = [];
function applySearch() {
  var q = state.query;
  hits = [];
  nodeEls.forEach(function (el, id) {
    var n = byId.get(id);
    var m = !!q && (n.label.toLowerCase().indexOf(q) >= 0 || (n.table || "").toLowerCase() + "[" + n.label.toLowerCase() + "]" === q);
    el.classList.toggle("match", m);
    if (m) hits.push(id);
  });
  svg.classList.toggle("searching", !!q);
  updateSearchUi();
}
