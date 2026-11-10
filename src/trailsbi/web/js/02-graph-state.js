/* ---------- graph state ---------- */
var DENSITY_KEY = "trailsbi.cardDensity";
var state = {types: new Set(),          // filled by applyTypePick() below
             hideUnused: false, hideAuto: true, hideHidden: false,
             dense: (function () {
               try { return localStorage.getItem(DENSITY_KEY) === "detailed" ? "detailed" : "compact"; }
               catch (e) { return "compact"; }
             })(),
             focus: null, zoom: 1, query: "", hitIdx: -1, scopeFind: ""};

/* ----- workspace scope: the semantic models and reports every view shows -----
   A folder of several reports and models opens on all of them, or on the
   busiest model when the whole folder is too big to draw at once. */
var WORKSPACE = !!D.meta.workspace;
var REPORT_BY_KEY = new Map((D.meta.reports || []).map(function (r) { return [r.key, r]; }));
(function () {
  var sc = D.meta.scope || {};
  state.scopeModels = new Set(sc.models || (D.meta.models || []).map(function (m) { return m.key; }));
  state.scopeReports = new Set(sc.reports || (D.meta.reports || []).map(function (r) { return r.key; }));
})();
function scopeIsAll() {
  return state.scopeModels.size >= (D.meta.models || []).length && state.scopeReports.size >= (D.meta.reports || []).length;
}
function someIn(keys, set) { return keys.some(function (k) { return set.has(k); }); }
/* Fields read from a published model belong to the reports that use it. */
function extInScope(label) {
  return (D.meta.reports || []).some(function (r) { return !r.model && r.external === label && state.scopeReports.has(r.key); });
}
function inScope(n) {
  if (!WORKSPACE || !n) return true;
  if (n.rkey) return state.scopeReports.has(n.rkey);
  if (n.mkey) return state.scopeModels.has(n.mkey);
  if (n.mkeys && n.mkeys.length) return someIn(n.mkeys, state.scopeModels);
  if (n.rkeys && n.rkeys.length) return someIn(n.rkeys, state.scopeReports);
  if (n.extmodel) return extInScope(n.extmodel);
  return true;
}
/* A Health or AI Readiness finding: kept when what it points at is in scope. */
function scopeKeepsItem(it) {
  if (!WORKSPACE) return true;
  if (it.id && byId.has(it.id)) return inScope(byId.get(it.id));
  if (it.rkey) return state.scopeReports.has(it.rkey);
  if (it.mkey) return state.scopeModels.has(it.mkey);
  return true;
}
/* Bring an item's semantic model and report into scope, so a link to it can open. */
function addToScope(n) {
  if (n.rkey) {
    state.scopeReports.add(n.rkey);
    var r = REPORT_BY_KEY.get(n.rkey);
    if (r && r.model) state.scopeModels.add(r.model);
  }
  if (n.mkey) state.scopeModels.add(n.mkey);
  (n.mkeys || []).forEach(function (k) { state.scopeModels.add(k); });
  (n.rkeys || []).forEach(function (k) { state.scopeReports.add(k); });
  if (n.extmodel) (D.meta.reports || []).forEach(function (r) {
    if (!r.model && r.external === n.extmodel) state.scopeReports.add(r.key);
  });
  if (typeof scopeChanged === "function") scopeChanged(true);
}

function ownerName(n) { return n.model || n.extmodel || ""; }
var FILTERS = [
  {k: "parameter", label: "Parameters", icon: "parameter"},
  {k: "query", label: "Queries", icon: "query"},
  {k: "source", label: "Data sources", icon: "db"},
  {k: "table", label: "Tables", icon: "table"},
  {k: "column", label: "Columns", icon: "column"},
  {k: "measure", label: "Measures", icon: "measure"},
  {k: "calcgroup", label: "Calculation groups", icon: "calcgroup"},
  {k: "visual", label: "Visuals", icon: "v_column"},
  {k: "page", label: "Pages", icon: "page"}
].filter(function (f) {                 // calculation groups only when the project has some
  return f.k !== "calcgroup" || D.nodes.some(function (n) { return n.type === "calcgroup"; });
});
function filterKey(n) {
  if (n.type === "query" && n.sub === "parameter") return "parameter";
  return n.type === "calcitem" ? "calcgroup" : n.type;
}
function isVisible(n) {
  if (!state.types.has(filterKey(n))) return false;
  if (!inScope(n)) return false;
  if (state.hideAuto && n.auto) return false;
  if (state.hideHidden && n.hidden) return false;
  if (state.hideUnused && n.type === "column" && n.sub === "data" &&
      OUT.get(n.id).length === 0) return false;
  return true;
}

var NODE_W = 280, NODE_TOP = 52, NODE_FOOT = 26, NODE_H = NODE_TOP + NODE_FOOT, GAP = 12, COL_GAP = 90, TOP = 50, PAD = 20;
var CARD_TEXT_X = 46;
var CARD_R = 4;
function cardOutline(h) {
  return "M0,0H" + (NODE_W - CARD_R) + "A" + CARD_R + "," + CARD_R + " 0 0 1 " + NODE_W + "," + CARD_R +
         "V" + (h - CARD_R) + "A" + CARD_R + "," + CARD_R + " 0 0 1 " + (NODE_W - CARD_R) + "," + h + "H0Z";
}
var CARD_PATH = cardOutline(NODE_H);
/* Card density: compact is one line with the icon; detailed adds the second
   line and the third row of counts. */
function applyDensity() {
  var compact = state.dense === "compact";
  NODE_TOP = compact ? 34 : 52;
  NODE_FOOT = compact ? 0 : 26;
  NODE_H = NODE_TOP + NODE_FOOT;
  GAP = compact ? 8 : 12;
  CARD_PATH = cardOutline(NODE_H);
}

