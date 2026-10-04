/* ---------- global search (acts on the open view) ---------- */
$("gIcon").innerHTML = icon("ui_search", 16);
var PLACEHOLDER = {
  graph: "Search tables, columns, measures and visuals",
  report: "Search reports, pages, visuals and fields",
  model: "Search tables, columns, measures and other model objects"
};
function openTab() { var b = document.querySelector(".rail button.on"); return b ? b.dataset.tab : "graph"; }
function updateSearchUi() {
  var tab = openTab();
  $("q").placeholder = PLACEHOLDER[tab] || "";
  document.querySelector(".gsearch").style.visibility = PLACEHOLDER[tab] ? "" : "hidden";   // Health and AI Readiness have no search
  var q = state.query, n = hits.length;
  if (tab === "report") { n = RHITS.length; }
  if (tab === "model") { n = MHITS.length; }
  $("hits").textContent = q ? (n ? n + " found" : "No matches") : "";
}
/* One search box, three views. Only the one being looked at is searched now; the
   others are marked stale and catch up when they are opened, so typing stays
   quick on a large model. */
var SEARCH_STALE = {graph: false, report: false, model: false};
function searchTab(tab) {
  if (tab === "graph") applySearch();
  else if (tab === "report") { if (typeof reportSearch === "function") reportSearch(state.query || ""); }
  else if (tab === "model") { if (typeof applyModelView === "function") applyModelView(); }
  else return;
  SEARCH_STALE[tab] = false;
}
function runSearch() {
  var tab = openTab();
  Object.keys(SEARCH_STALE).forEach(function (k) { if (k !== tab) SEARCH_STALE[k] = true; });
  searchTab(tab);
  updateSearchUi();
}
function catchUpSearch(tab) {
  if (SEARCH_STALE[tab]) searchTab(tab);
}
var qTimer = null;
function flushSearch() {
  if (!qTimer) return false;
  clearTimeout(qTimer); qTimer = null;
  runSearch();
  return true;
}
function clearSearch() {
  if (!$("q").value && !state.query) return;
  clearTimeout(qTimer); qTimer = null;
  $("q").value = "";
  state.query = ""; state.hitIdx = -1;
  state.rHitIdx = -1;
  runSearch();
}
$("q").addEventListener("input", function (e) {
  var v = e.target.value.trim().toLowerCase();
  state.query = v; state.hitIdx = -1;
  state.rHitIdx = -1;
  clearTimeout(qTimer);
  qTimer = setTimeout(function () { qTimer = null; runSearch(); }, 140);
});
$("q").addEventListener("keydown", function (e) {
  if (e.key === "Escape") { clearSearch(); return; }
  if (e.key !== "Enter") return;
  flushSearch();                                        // act on what was typed, not on the last pass
  if (openTab() === "model") {
    if (!MHITS.length) return;
    state.mHitIdx = ((state.mHitIdx === undefined ? -1 : state.mHitIdx) + 1) % MHITS.length;
    MHITS[state.mHitIdx].scrollIntoView({block: "center"});
    flashRow(MHITS[state.mHitIdx]);
    return;
  }
  if (openTab() === "report") {
    if (!RHITS.length) return;
    state.rHitIdx = ((state.rHitIdx || 0) + 1) % RHITS.length;
    var h = RHITS[state.rHitIdx];
    showPage(h.sec.getAttribute("data-rkey"), h.pid, true);
    return;
  }
  if (openTab() !== "graph") switchTab("graph");
  if (hits.length) {
    state.hitIdx = (state.hitIdx + 1) % hits.length;
    focusNode(hits[state.hitIdx], true);
  }
});
document.addEventListener("keydown", function (e) {
  var t = e.target, typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
  if (e.key === "/" && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); $("q").focus(); $("q").select(); }
});


