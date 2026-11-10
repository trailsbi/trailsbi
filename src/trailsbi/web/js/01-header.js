/* ---------- header ---------- */
var MODELS = D.meta.models || [], REPORTS = D.meta.reports || [];
var MODEL_BY_KEY = new Map(MODELS.map(function (m) { return [m.key, m]; }));
function plural(nm, one, many) { return nm + " " + (nm === 1 ? one : many); }
$("meta").textContent = "Output generated on " + D.meta.generated;
$("aboutGen").textContent = D.meta.generated;          // the header drops the line when it is narrow

/* Theme: the system's light or dark setting, until the switch picks one (remembered). */
var THEME_KEY = "trailsbi.theme";
function systemDark() { return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches); }
function themeNow() { return document.documentElement.getAttribute("data-theme") || (systemDark() ? "dark" : "light"); }
function syncThemeBtn() {
  var dark = themeNow() === "dark", b = $("themeBtn");
  fill(b, icon(dark ? "ui_sun" : "ui_moon", 15));
  b.title = dark ? "Switch to the light theme" : "Switch to the dark theme";
  b.setAttribute("aria-label", b.title);
}
function setTheme(t, remember) {
  if (t) document.documentElement.setAttribute("data-theme", t);
  else document.documentElement.removeAttribute("data-theme");
  if (remember) { try { localStorage.setItem(THEME_KEY, t); } catch (e) {} }
  syncThemeBtn();
}
(function () {
  var saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}
  setTheme(saved === "dark" || saved === "light" ? saved : null, false);
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    if (mq.addEventListener) mq.addEventListener("change", syncThemeBtn);
  }
})();
$("themeBtn").addEventListener("click", function () { setTheme(themeNow() === "dark" ? "light" : "dark", true); });

document.querySelectorAll(".rail .rail-ic").forEach(function (el) {
  el.insertBefore(icon(el.getAttribute("data-icon"), 22), el.firstChild);
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
  var ws = !!D.meta.workspace;
  var onWs = name === "ws";
  $("toolbar").hidden = !(onGraph || onModel || onWs || (onRules && !!state.issueEntity) || (ws && (onRules || onRep)));
  $("scopeBox").hidden = !(ws && (onGraph || onWs || onModel || onRules || onRep));
  $("wsTypes").hidden = !onWs;
  $("types").hidden = !onGraph;
  $("viewBox").hidden = !onGraph;
  $("mdViewBox").hidden = !onModel;
  $("mdModeSeg").hidden = !onModel;
  if (onRules) { buildHealth(); buildAI(); }
  if (name === "ws" && typeof wsFitText === "function") wsFitText();
  if (typeof syncFilterBar === "function") syncFilterBar();
  $("mdTypes").hidden = !onModel || state.mdMode === "diagram";
  $("densitySeg").hidden = onModel || onRep || onRules;
  if (typeof graphOnShow === "function") graphOnShow();
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

