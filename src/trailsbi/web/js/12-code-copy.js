/* ---------- code copy: a copy button over whichever code block the pointer is on ----------
   One floating button serves every <pre> on the page (DAX and Power Query in the
   lineage panel, the model list and the diagram panel), so none of those views
   needs to know about it. Inside Power BI the clipboard can be blocked; then the
   code is selected so Ctrl+C copies it. */
var copyBtn = null, copyFor = null, copyHideT = null;

function copyButton() {
  if (copyBtn && copyBtn.isConnected) return copyBtn;
  copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "codecopy";
  copyBtn.hidden = true;
  copyBtn.addEventListener("mouseenter", function () { clearTimeout(copyHideT); });
  copyBtn.addEventListener("mouseleave", hideCopySoon);
  copyBtn.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (copyFor) copyCode(copyFor);
  });
  document.body.appendChild(copyBtn);
  return copyBtn;
}
function setCopyState(done) {
  copyBtn.innerHTML = icon(done ? "ui_check" : "ui_copy", 14);
  copyBtn.classList.toggle("done", done);
  copyBtn.title = done ? "Copied" : "Copy";
  copyBtn.setAttribute("aria-label", done ? "Copied" : "Copy code");
}
function placeCopy(pre) {
  var b = copyButton(), r = pre.getBoundingClientRect();
  clearTimeout(copyHideT);
  if (!r.width || !r.height) { b.hidden = true; copyFor = null; return; }
  if (copyFor !== pre) setCopyState(false);
  copyFor = pre;
  var bar = pre.offsetWidth - pre.clientWidth;          // keep clear of a vertical scrollbar
  b.style.top = Math.round(r.top + 6) + "px";
  b.style.left = Math.round(r.right - bar - 6 - 28) + "px";
  b.hidden = false;
}
function hideCopy() {
  clearTimeout(copyHideT);
  if (copyBtn) copyBtn.hidden = true;
  copyFor = null;
}
function hideCopySoon() {
  clearTimeout(copyHideT);
  copyHideT = setTimeout(hideCopy, 160);
}
function selectCode(pre) {
  var sel = window.getSelection && window.getSelection();
  if (!sel) return;
  var range = document.createRange();
  range.selectNodeContents(pre);
  sel.removeAllRanges();
  sel.addRange(range);
}
function copyWithTextarea(text) {
  var ta = document.createElement("textarea"), ok = false;
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.cssText = "position:fixed;top:-1000px;left:0;opacity:0";
  document.body.appendChild(ta);
  ta.select();
  try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
  ta.remove();
  return ok;
}
function copyCode(pre) {
  var text = pre.textContent;
  var copied = function () { if (copyFor === pre) setCopyState(true); };
  var fallback = function () {
    if (copyWithTextarea(text)) { copied(); return; }
    selectCode(pre);
    toast("Copying is blocked here, so the code is selected: press Ctrl+C (⌘C on a Mac) to copy it.");
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(copied, fallback);
  } else {
    fallback();
  }
}

document.addEventListener("mouseover", function (e) {
  var t = e.target;
  if (copyBtn && (t === copyBtn || copyBtn.contains(t))) return;
  var pre = t && t.closest ? t.closest("pre") : null;
  if (pre) placeCopy(pre);
  else if (copyFor) hideCopySoon();
});
// The button is placed in window coordinates, so anything that moves the code hides it.
document.addEventListener("scroll", hideCopy, true);
window.addEventListener("resize", hideCopy);
