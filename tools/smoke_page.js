// Opens generated pages in Chromium, goes through every view and fails on any script error.
// Usage: node tools/smoke_page.js page1.html [page2.html ...]
// Needs Playwright: npm install playwright && npx playwright install chromium
"use strict";
const path = require("path");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) { ({ chromium } = require("playwright-core")); }

async function check(browser, file) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto("file://" + path.resolve(file));
  await page.waitForTimeout(800);
  const step = async (name, fn) => {
    try { await fn(); await page.waitForTimeout(200); } catch (e) { errors.push(`${name}: ${e.message.split("\n")[0]}`); }
  };
  await step("select a card", () => page.click("#svg g.n"));
  await step("density", async () => { await page.click("#dDetailed"); await page.click("#dCompact"); });
  await step("fit", () => page.click("#zFit"));
  await step("search", async () => { await page.fill("#q", "a"); await page.press("#q", "Enter"); await page.press("#q", "Escape"); });
  for (const tab of ["model", "report", "health", "ai", "graph"]) {
    await step(`open ${tab}`, () => page.click(`.rail button[data-tab="${tab}"]`));
  }
  await step("model diagram", async () => {
    await page.click('.rail button[data-tab="model"]');
    await page.click("#mdDiag");
    await page.click("#mdZFit");
    await page.click("#mdList");
  });
  await step("about", async () => { await page.click("#aboutBtn"); await page.keyboard.press("Escape"); });
  await page.close();
  return errors;
}

(async () => {
  const files = process.argv.slice(2);
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  let failed = 0;
  for (const f of files) {
    const errors = await check(browser, f);
    console.log(`${path.basename(f)}: ${errors.length ? errors.join(" | ") : "ok"}`);
    failed += errors.length ? 1 : 0;
  }
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
