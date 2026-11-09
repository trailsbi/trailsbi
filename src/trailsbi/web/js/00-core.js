/* ---------- core: page data, graph indexes and small helpers ---------- */
var D = JSON.parse(document.getElementById("data").textContent);
var ICONS = JSON.parse(document.getElementById("icons").textContent);
var TYPES = [
  {k:"source",  label:"Data sources"},
  {k:"query",   label:"Queries & parameters"},
  {k:"table",   label:"Tables"},
  {k:"column",  label:"Columns"},
  {k:"measure", label:"Measures"},
  {k:"calcgroup", label:"Calculation groups"},
  {k:"calcitem", label:"Calculation items"},
  {k:"visual",  label:"Visuals"},
  {k:"page",    label:"Pages"}
];
var TYPE_IDX = {}; TYPES.forEach(function (t, i) { TYPE_IDX[t.k] = i; });
var SINGULAR = {source:"Data source", query:"Query", table:"Table", column:"Column",
                measure:"Measure", calcgroup:"Calculation group", calcitem:"Calculation item",
                visual:"Visual", page:"Page"};
var byId = new Map(), OUT = new Map(), IN = new Map(), ROLE = new Map();
D.nodes.forEach(function (n) { byId.set(n.id, n); });
/* "home" edges tie a measure to the table it is stored in. They always count
   for usage, health and AI checks (worked out when the page was built), but the
   lineage only draws them when "Show measures under their home table" is on. */
var ALL_EDGES = D.edges;
function wireEdges(withHome) {
  D.edges = withHome ? ALL_EDGES : ALL_EDGES.filter(function (e) { return e[2] !== "home"; });
  OUT.clear(); IN.clear(); ROLE.clear();
  D.nodes.forEach(function (n) { OUT.set(n.id, []); IN.set(n.id, []); });
  D.edges.forEach(function (e) {
    OUT.get(e[0]).push(e[1]); IN.get(e[1]).push(e[0]); ROLE.set(e[0] + "\u0000" + e[1], e[2]);
  });
}
wireEdges(false);

/* ---------- DOM building ----------
   Every view is built from elements, never from markup strings: names, DAX and
   anything else read from the project only ever become text nodes or attribute
   values, so nothing in a model can turn into markup or script.
     h("div", {class: "x", "data-id": id}, [child, "text", [more]])
   Attributes that are null, undefined or false are left out; true sets an empty
   attribute. Children can be nodes, strings, numbers or nested arrays; null and
   false are skipped. sg() does the same for SVG elements. */
var SVGNS = "http://www.w3.org/2000/svg";
function addKids(parent, kids) {
  if (kids === null || kids === undefined || kids === false) return parent;
  if (Array.isArray(kids)) { for (var i = 0; i < kids.length; i++) addKids(parent, kids[i]); return parent; }
  parent.appendChild(kids.nodeType ? kids : document.createTextNode(String(kids)));
  return parent;
}
function makeEl(ns, tag, attrs, kids) {
  var e = ns ? document.createElementNS(ns, tag) : document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(function (k) {
    var v = attrs[k];
    if (v === null || v === undefined || v === false) return;
    e.setAttribute(k, v === true ? "" : String(v));
  });
  return addKids(e, kids);
}
function h(tag, attrs, kids) { return makeEl(null, tag, attrs, kids); }
function sg(tag, attrs, kids) { return makeEl(SVGNS, tag, attrs, kids); }
function frag(kids) { return addKids(document.createDocumentFragment(), kids); }
/* Replace everything inside an element. */
function fill(el, kids) { el.textContent = ""; return addKids(el, kids); }
/* An element tree from the page's icon data: [tag, {attributes}, [children]]. */
function treeEl(t) { return sg(t[0], t[1], (t[2] || []).map(treeEl)); }
function iconParts(name) { return (ICONS[name] || ICONS.v_generic).map(treeEl); }
/* An icon as a <g> for drawing inside a larger SVG. */
function iconG(name, attrs) { return sg("g", attrs, iconParts(name)); }
function trunc(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function $(id) { return document.getElementById(id); }
function kindName(n) {
  if (n.type === "column" && n.sub === "calculated") return "Calculated column";
  if (n.type === "table" && n.sub === "calculated") return "Calculated table";
  if (n.type === "table" && n.sub === "fieldparam") return "Field parameter";
  if (n.type === "query" && n.sub === "parameter") return "Parameter";
  if (n.type === "measure" && n.sub === "report") return "Report measure";
  if (n.broken) return "Missing " + n.type;
  return SINGULAR[n.type];
}
var TYPE_ICON = {source:"db", query:"query", table:"table", column:"column",
                 measure:"measure", calcgroup:"calcgroup", calcitem:"calcitem", visual:"v_column", page:"page"};
function iconName(n) { return n.icon || TYPE_ICON[n.type] || "v_generic"; }
function typeCls(n) { return n.broken ? "is-bad" : "t-" + n.type + (n.sub ? " s-" + n.sub : ""); }
function icon(name, size, cls) {
  return sg("svg", {"class": "ic " + (cls || ""), width: size, height: size, viewBox: "0 0 24 24", fill: "none",
                    stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round",
                    "stroke-linejoin": "round", "aria-hidden": "true"}, iconParts(name));
}
function markers(n) {
  var m = [];
  if (n.broken) m.push(["missing", "Missing from the model"]);
  if (n.hidden) m.push(["hidden", "Hidden"]);
  if (n.relkey) m.push(["key", "Relationship key"]);
  if (n.filtered) m.push(["filter", "Used as a filter"]);
  return m;
}

