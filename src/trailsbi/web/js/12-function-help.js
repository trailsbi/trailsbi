/* ---------- function help in DAX and Power Query code ----------
   Code is built as text. Function names the page has help for (D.fnhelp, only
   the functions this project uses) become small spans; pointing at one shows
   its syntax, what it does and a link to its page on Microsoft Learn. Strings,
   comments, table names and [column] references are skipped, so a name inside
   them is never mistaken for a call. */
var FNHELP = D.fnhelp || {dax: {}, m: {}};
function codeLang(title) {
  if (/SQL/.test(title)) return "sql";
  if (/\(M\)|Power Query/.test(title)) return "m";
  return "dax";
}
/* Where a quoted run that starts at i ends (just past the closing quote). A doubled
   closing character is an escaped one: "" in strings, '' in names, ]] in references. */
function quotedEnd(text, i, close) {
  var j = i + 1;
  while (j < text.length) {
    if (text.charAt(j) === close) {
      if (text.charAt(j + 1) === close) { j += 2; continue; }
      return j + 1;
    }
    j++;
  }
  return text.length;
}
function commentEnd(text, i) {
  if (text.substr(i, 2) === "/*") { var e = text.indexOf("*/", i + 2); return e < 0 ? text.length : e + 2; }
  var nl = text.indexOf("\n", i);
  return nl < 0 ? text.length : nl;
}
var DAX_IDENT = /[A-Za-z_][A-Za-z0-9_.]*/y, M_IDENT = /#?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*/y;
function codeKids(text, lang) {
  text = String(text == null ? "" : text);
  var table = lang === "dax" ? FNHELP.dax : lang === "m" ? FNHELP.m : null;
  if (!table || !Object.keys(table).length) return text;
  var out = [], plain = "", i = 0, n = text.length;
  var flush = function () { if (plain) { out.push(plain); plain = ""; } };
  while (i < n) {
    var c = text.charAt(i), two = text.substr(i, 2), end = -1;
    if (two === "//" || two === "/*" || (lang === "dax" && two === "--")) end = commentEnd(text, i);
    else if (c === '"') end = quotedEnd(text, i, '"');
    else if (lang === "m" && two === '#"') end = quotedEnd(text, i + 1, '"');
    else if (lang === "dax" && c === "'") end = quotedEnd(text, i, "'");
    else if (lang === "dax" && c === "[") end = quotedEnd(text, i, "]");
    if (end > i) { plain += text.slice(i, end); i = end; continue; }
    var re = lang === "dax" ? DAX_IDENT : M_IDENT;
    var before = i ? text.charAt(i - 1) : "";
    re.lastIndex = i;
    var m = /[A-Za-z_#]/.test(c) && !/[A-Za-z0-9_.]/.test(before) ? re.exec(text) : null;
    if (!m) { plain += c; i++; continue; }
    var word = m[0], key = lang === "dax" ? word.toUpperCase() : word;
    var call = lang !== "dax" || /^\s*\(/.test(text.slice(i + word.length, i + word.length + 40));
    if (table[key] && call) {
      flush();
      out.push(h("span", {"class": "fn", "data-fn": key, "data-lang": lang}, word));
    } else plain += word;
    i += word.length;
  }
  flush();
  return out;
}
function fnLearnUrl(lang, name) {
  return lang === "dax"
    ? "https://learn.microsoft.com/dax/" + name.toLowerCase().replace(/\./g, "-") + "-function-dax"
    : "https://learn.microsoft.com/powerquery-m/" + name.toLowerCase().replace(/^#/, "sharp").replace(/\./g, "-");
}
var fnTip = null, fnFor = null, fnHideT = null;
function fnTipEl() {
  if (fnTip && fnTip.isConnected) return fnTip;
  fnTip = h("div", {id: "fnhelp", role: "tooltip", hidden: true});
  fnTip.addEventListener("mouseenter", function () { clearTimeout(fnHideT); });
  fnTip.addEventListener("mouseleave", hideFnSoon);
  document.body.appendChild(fnTip);
  return fnTip;
}
function showFn(span) {
  var lang = span.getAttribute("data-lang"), name = span.getAttribute("data-fn");
  var entry = (FNHELP[lang] || {})[name];
  if (!entry) return;
  clearTimeout(fnHideT);
  var tip = fnTipEl();
  if (fnFor !== span) {
    fill(tip, [
      h("div", {"class": "fh-head"}, [h("b", null, name), h("span", null, lang === "dax" ? "DAX function" : "Power Query function")]),
      h("code", {"class": "fh-sig"}, entry[0]),
      h("p", null, entry[1]),
      h("a", {href: fnLearnUrl(lang, name), target: "_blank", rel: "noopener noreferrer"}, "Read more on Microsoft Learn")
    ]);
    fnFor = span;
  }
  tip.hidden = false;
  var r = span.getBoundingClientRect(), w = tip.offsetWidth, ht = tip.offsetHeight;
  var left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8));
  var top = r.bottom + 6 + ht > window.innerHeight - 8 ? r.top - ht - 6 : r.bottom + 6;
  tip.style.left = Math.round(left) + "px";
  tip.style.top = Math.round(Math.max(8, top)) + "px";
  span.setAttribute("aria-describedby", "fnhelp");
}
function hideFn() {
  clearTimeout(fnHideT);
  if (fnTip) fnTip.hidden = true;
  if (fnFor) fnFor.removeAttribute("aria-describedby");
  fnFor = null;
}
function hideFnSoon() {
  clearTimeout(fnHideT);
  fnHideT = setTimeout(hideFn, 200);
}
document.addEventListener("mouseover", function (e) {
  var t = e.target;
  if (fnTip && fnTip.contains(t)) return;
  var span = t && t.closest ? t.closest("span.fn") : null;
  if (span) showFn(span);
  else if (fnFor) hideFnSoon();
});
document.addEventListener("click", function (e) {    // touch screens have no hover
  var span = e.target && e.target.closest ? e.target.closest("span.fn") : null;
  if (span) showFn(span);
});
document.addEventListener("keydown", function (e) { if (e.key === "Escape" && fnFor) hideFn(); });
document.addEventListener("scroll", hideFn, true);
window.addEventListener("resize", hideFn);
