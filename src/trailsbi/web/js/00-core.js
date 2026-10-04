/* ---------- core: page data, graph indexes and small helpers ---------- */
var D = JSON.parse(document.getElementById("data").textContent);
var ICONS = JSON.parse(document.getElementById("icons").textContent);
var TYPES = [
  {k:"source",  label:"Data sources"},
  {k:"query",   label:"Queries & parameters"},
  {k:"table",   label:"Tables"},
  {k:"column",  label:"Columns"},
  {k:"measure", label:"Measures"},
  {k:"visual",  label:"Visuals"},
  {k:"page",    label:"Pages"}
];
var TYPE_IDX = {}; TYPES.forEach(function (t, i) { TYPE_IDX[t.k] = i; });
var SINGULAR = {source:"Data source", query:"Query", table:"Table", column:"Column",
                measure:"Measure", visual:"Visual", page:"Page"};
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

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  });
}
function trunc(s, n) { s = String(s); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
function $(id) { return document.getElementById(id); }
function kindName(n) {
  if (n.type === "column" && n.sub === "calculated") return "Calculated column";
  if (n.type === "table" && n.sub === "calculated") return "Calculated table";
  if (n.type === "table" && n.sub === "fieldparam") return "Field parameter";
  if (n.type === "table" && n.sub === "calcgroup") return "Calculation group";
  if (n.type === "query" && n.sub === "parameter") return "Parameter";
  if (n.sub === "calcitem") return "Calculation item";
  if (n.broken) return "Missing " + n.type;
  return SINGULAR[n.type];
}
var TYPE_ICON = {source:"db", query:"query", table:"table", column:"column",
                 measure:"measure", visual:"v_column", page:"page"};
function iconName(n) { return n.icon || TYPE_ICON[n.type] || "v_generic"; }
function typeCls(n) { return n.broken ? "is-bad" : "t-" + n.type + (n.sub ? " s-" + n.sub : ""); }
function icon(name, size, cls) {
  return '<svg class="ic ' + (cls || "") + '" width="' + size + '" height="' + size +
    '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    (ICONS[name] || ICONS.v_generic) + '</svg>';
}
function markers(n) {
  var m = [];
  if (n.broken) m.push(["missing", "Missing from the model"]);
  if (n.hidden) m.push(["hidden", "Hidden"]);
  if (n.relkey) m.push(["key", "Relationship key"]);
  if (n.filtered) m.push(["filter", "Used as a filter"]);
  return m;
}

