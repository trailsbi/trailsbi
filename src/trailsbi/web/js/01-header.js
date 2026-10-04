/* ---------- header ---------- */
var MODELS = D.meta.models || [], REPORTS = D.meta.reports || [];
var MODEL_BY_KEY = new Map(MODELS.map(function (m) { return [m.key, m]; }));
function plural(nm, one, many) { return nm + " " + (nm === 1 ? one : many); }
$("meta").textContent = "Output generated on " + D.meta.generated;

document.querySelectorAll(".rail .rail-ic").forEach(function (el) {
  el.insertAdjacentHTML("afterbegin", icon(el.getAttribute("data-icon"), 22));
});
document.querySelectorAll(".rail button").forEach(function (b) {
  b.addEventListener("click", function () { switchTab(b.dataset.tab); });
});
function switchTab(name) {
  document.querySelectorAll(".rail button").forEach(function (b) {
    var on = b.dataset.tab === name;
    b.classList.toggle("on", on);
    if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  document.querySelectorAll(".tab").forEach(function (t) {
    t.classList.toggle("on", t.id === "tab-" + name);
  });
  var onGraph = name === "graph", onModel = name === "model", onRep = name === "report";
  var onRules = name === "health" || name === "ai";
  $("toolbar").hidden = !(onGraph || onModel || (onRules && !!state.issueEntity));
  $("types").hidden = !onGraph;
  $("viewBox").hidden = !onGraph;
  $("mdViewBox").hidden = !onModel;
  $("mdModeSeg").hidden = !onModel;
  if (onRules) { buildHealth(); buildAI(); }
  if (typeof syncFilterBar === "function") syncFilterBar();
  $("mdTypes").hidden = !onModel || state.mdMode === "diagram";
  $("densitySeg").hidden = onModel || onRep || onRules;
  // Cards drawn while their view was hidden could not be measured: trim them now.
  if (typeof fitCardLines === "function") {
    if (onGraph) fitCardLines($("svg"));
    if (onRep) $("reportDoc").querySelectorAll("section").forEach(function (sec) { fitCardLines(sec); });
  }
  if (name === "report" && typeof sizePreviewActions === "function") sizePreviewActions();
  // this view may have missed a search while it was closed
  if (typeof catchUpSearch === "function") catchUpSearch(name);
  if (typeof updateSearchUi === "function") updateSearchUi();
}

