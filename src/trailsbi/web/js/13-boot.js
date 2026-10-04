/* Booting. Building every view takes a while on a large model, and doing it in
   one go leaves the shell on screen half drawn. Each step hands control back
   to the browser first, so what people see is a progress bar. */
var BOOT = [
  [2,  "Preparing the view", function () { applyTypePick(); applyDensity(); syncControls(); }],
  [30, "Drawing the lineage map", function () { render(); emptyPanel(); }],
  [20, "Building " + plural(D.pages.length, "report page", "report pages"),
       function () { buildReport(); }],
  [25, "Reading " + plural((D.meta.models || []).length, "semantic model", "semantic models"),
       function () { buildModel(); }],
  [10, "Checking best practices", function () { buildHealth(); }],
  [5,  "Checking AI readiness", function () { buildAI(); }]
];
var BOOT_TOTAL = BOOT.reduce(function (a, b) { return a + b[0]; }, 0);
var bootStart = Date.now(), bootDone = 0;
function bootFinish() {
  var el = $("boot");
  if (!el) return;
  if (Date.now() - bootStart < 400) { el.remove(); return; }   // too quick to be worth a fade
  el.classList.add("done");
  setTimeout(function () { el.remove(); }, 300);
}
function bootStep(i) {
  if (i >= BOOT.length) {
    var f = $("bootFill");
    if (f) f.style.width = "100%";
    bootFinish();
    return;
  }
  var fill = $("bootFill"), step = $("bootStep");
  if (step) step.textContent = BOOT[i][1] + "…";
  if (fill) fill.style.width = Math.round(bootDone / BOOT_TOTAL * 100) + "%";
  var next = function () {
    try {
      BOOT[i][2]();
    } catch (err) {                       // never let one view strand the splash
      if (window.console) console.error("Could not build: " + BOOT[i][1], err);
    }
    bootDone += BOOT[i][0];
    bootStep(i + 1);
  };
  // let the bar paint, then work on the turn after it
  if (window.requestAnimationFrame) requestAnimationFrame(function () { setTimeout(next, 0); });
  else setTimeout(next, 0);
}
bootStep(0);
