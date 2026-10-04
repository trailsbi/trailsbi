/* ---------- card text: trim names to the room a card has ---------- */
/* Longest prefix of the full text that fits, with an ellipsis; blank when even
   one character will not fit. */
function fitText(t, room) {
  var full = t.getAttribute("data-full");
  if (full === null) full = t.textContent;
  t.textContent = full;
  if (t.getComputedTextLength() <= room) return;
  var lo = 0, hi = full.length;
  while (lo < hi) {
    var mid = (lo + hi + 1) >> 1;
    t.textContent = full.slice(0, mid).trimEnd() + "…";
    if (t.getComputedTextLength() <= room) lo = mid; else hi = mid - 1;
  }
  t.textContent = lo ? full.slice(0, lo).trimEnd() + "…" : "";
}
/* Trim card text to the room it has. Text can only be measured while its view
   is on screen: a card drawn behind a hidden tab measures as zero-width, so
   this runs again whenever a view is opened. */
function fitCardLines(el) {
  if (!el || !el.getBoundingClientRect().width) return;      // nothing to measure yet
  el.querySelectorAll("text[data-room][data-full]").forEach(function (t) {
    if (typeof t.getComputedTextLength !== "function") return;
    if (t.classList.contains("t1x")) return;                 // positioned below, after the name
    fitText(t, +t.getAttribute("data-room"));
  });
  // Line-one suffix (a visual's type) sits just after the name, once trimmed.
  el.querySelectorAll("text.t1x[data-after]").forEach(function (t) {
    var g = t.parentNode, name = g.querySelector("text.t1");
    if (!name || typeof name.getComputedTextLength !== "function") return;
    var x = (+name.getAttribute("x")) + name.getComputedTextLength() + 8;
    var room = (+name.getAttribute("data-room")) + (+name.getAttribute("x")) - x;
    t.setAttribute("x", x);
    t.setAttribute("data-room", Math.max(0, room));
    if (room < 24) { t.textContent = ""; return; }
    fitText(t, room);
  });
}
