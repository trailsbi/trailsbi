/* ---------- graph state ---------- */
var DENSITY_KEY = "trailsbi.cardDensity";
var state = {types: new Set(),          // filled by applyTypePick() below
             hideUnused: false, hideAuto: true, hideHidden: false,
             dense: (function () {
               try { return localStorage.getItem(DENSITY_KEY) === "detailed" ? "detailed" : "compact"; }
               catch (e) { return "compact"; }
             })(),
             focus: null, zoom: 1, query: "", hitIdx: -1};

function ownerName(n) { return n.model || n.extmodel || ""; }
var FILTERS = [
  {k: "parameter", label: "Parameters", icon: "parameter"},
  {k: "query", label: "Queries", icon: "query"},
  {k: "source", label: "Data sources", icon: "db"},
  {k: "table", label: "Tables", icon: "table"},
  {k: "column", label: "Columns", icon: "column"},
  {k: "measure", label: "Measures", icon: "measure"},
  {k: "visual", label: "Visuals", icon: "v_column"},
  {k: "page", label: "Pages", icon: "page"}
];
function filterKey(n) {
  return n.type === "query" && n.sub === "parameter" ? "parameter" : n.type;
}
function isVisible(n) {
  if (!state.types.has(filterKey(n))) return false;
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

