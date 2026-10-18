// End-to-end smoke test of the running app in a real browser.
//
//   BASE_URL=http://127.0.0.1:8000 npm run e2e            # app must be running
//   SCREENSHOTS=../docs/screenshots npm run e2e           # also write README screenshots
//
// Uses an installed Chrome (CHROME_CHANNEL=chrome by default; set CHROME_PATH to override).
import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:8000";
const SHOTS = process.env.SCREENSHOTS;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const launch = process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : { channel: process.env.CHROME_CHANNEL ?? "chrome" };
const browser = await chromium.launch({ ...launch, headless: true });
const results = [];
const step = async (name, fn) => {
  const t = Date.now();
  try { await fn(); results.push(`  ✓ ${name} (${Date.now() - t} ms)`); }
  catch (e) { results.push(`  ✗ ${name}: ${e.message.split("\n")[0]}`); process.exitCode = 1; }
};
const shot = async (page, name, opts = {}) => SHOTS && page.screenshot({ path: `${SHOTS}/${name}.png`, ...opts });

async function freshPage(viewport = { width: 1440, height: 960 }) {
  const context = await browser.newContext({ viewport, colorScheme: "light" });
  const page = await context.newPage();
  page.errors = [];
  page.on("console", (m) => m.type() === "error" && page.errors.push(m.text()));
  page.on("pageerror", (e) => page.errors.push(String(e)));
  await page.goto(BASE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForSelector('#program option[value="mathematics-major-ba"]', { state: "attached" });
  return page;
}
const courseCodes = (page) => page.$$eval(".term .course .code", (els) => els.map((e) => e.textContent));
const build = async (page) => {
  await page.click("button.primary");
  await page.waitForSelector(".result-title, .infeasible", { timeout: 60_000 });
  await page.waitForFunction(() => !document.querySelector(".stale"));
};

// 1 ─ the main journey: courses + AP credit -> plan -> inspect -> edit
const page = await freshPage();
await step("landing page shows the hero and the Math B.A. preselected", async () => {
  await page.waitForSelector(".hero h1");
  assert.equal(await page.$eval("#program", (s) => s.options[s.selectedIndex].text), "Mathematics Major, B.A.");
  await shot(page, "01-landing");
});
await step("add a UNC course with a grade via catalog search", async () => {
  await page.fill('input[type="search"]', "stor 155");
  await page.waitForSelector(".combo-list li");
  await page.keyboard.press("Enter");
  await page.selectOption('select[aria-label="Grade for STOR 155"]', "A-");
});
await step("add AP Calculus BC and see the catalog award before adding", async () => {
  await page.selectOption('select[aria-label="Exam"]', "Calculus BC");
  await page.selectOption('select[aria-label="Score"]', "5");
  assert.match(await page.textContent(".award-preview"), /MATH 231, MATH 232 · 8 hrs/);
  await page.click(".exam-row button.secondary");
  await page.waitForSelector(".chip-row");
});
await step("build a feasible, provisional plan", async () => {
  await build(page);
  assert.match(await page.textContent(".banner.provisional"), /not graduation-certified/);
  const codes = await courseCodes(page);
  assert.ok(!codes.includes("MATH 231") && !codes.includes("MATH 232"), "AP credit should remove calculus I/II");
  for (const req of ["MATH 381", "MATH 383", "MATH 521"]) assert.ok(codes.includes(req), `${req} missing`);
  assert.match(await page.textContent(".starting"), /AP Calculus BC \(5\)/);
  await shot(page, "02-plan", { fullPage: true });
});
await step("prerequisite map draws the chains", async () => {
  await page.click('button[role="tab"]:has-text("Prerequisite map")');
  await page.waitForSelector(".map-node");
  assert.ok((await page.$$(".map-edge")).length >= 5);
  await page.hover('.map-node:has-text("MATH 521")');
  assert.ok((await page.$$(".map-edge.lit")).length >= 2);
  await shot(page, "03-prereq-map", { fullPage: true });
});
await step("requirements show verification and verbatim catalog source", async () => {
  await page.click('button[role="tab"]:has-text("Requirements")');
  await page.locator(".req-line", { hasText: "Three more MATH courses" }).locator("button", { hasText: "source" }).click();
  assert.match(await page.textContent(".provenance"), /counts as one 500-level course/);
  assert.ok(await page.isVisible(".badge.verified"));
  await shot(page, "04-requirements", { fullPage: true });
});
await step("checks list honest limitations", async () => {
  await page.click('button[role="tab"]:has-text("Checks")');
  assert.match(await page.textContent(".issues"), /Course offering terms are not modeled/);
});
await step("course drawer explains prerequisites in plan context", async () => {
  await page.click('button[role="tab"]:has-text("Semesters")');
  await page.locator(".course .code", { hasText: /^MATH 521$/ }).click();
  await page.waitForSelector(".drawer h2");
  assert.match(await page.textContent(".drawer"), /Interpreted as/);
  assert.match(await page.textContent(".drawer .in-plan"), /Prerequisites met by/);
  await shot(page, "05-course-drawer");
  await page.keyboard.press("Escape");
  await page.waitForSelector(".drawer", { state: "detached" });
});
await step("avoiding MATH 347 re-plans with MATH 577", async () => {
  await page.locator(".course").filter({ has: page.locator(".code", { hasText: /^MATH 347$/ }) })
    .getByRole("button", { name: "Avoid" }).click();
  await page.waitForSelector(".pin.avoid");
  await page.waitForFunction(() => !document.querySelector(".stale"));
  assert.ok((await courseCodes(page)).includes("MATH 577"));
});
await step("pinning keeps a course in its term", async () => {
  const card = page.locator(".term").filter({ has: page.locator(".code", { hasText: /^MATH 381$/ }) });
  const term = await card.locator("h3").textContent();
  await card.locator(".course").filter({ has: page.locator(".code", { hasText: /^MATH 381$/ }) })
    .getByRole("button", { name: /Pin here/ }).click();
  await page.waitForSelector(`.pin:has-text("MATH 381 · ${term}")`);
  await page.waitForFunction(() => !document.querySelector(".stale"));
});
await step("no console errors in the main journey", async () => assert.deepEqual(page.errors, []));

// 2 ─ infeasible goal -> explanation -> one-click fix
const p2 = await freshPage();
await step("an impossible graduation date is explained, then fixed in one click", async () => {
  await p2.selectOption("#first", "Spring 2027");
  await p2.selectOption("#grad", "Spring 2028");
  await build(p2);
  await p2.waitForSelector(".infeasible .fix");
  assert.match(await p2.textContent(".causes"), /prerequisite chain|UNC requires 120/);
  await shot(p2, "06-infeasible", { fullPage: true });
  await p2.click(".infeasible .fix");
  await p2.waitForSelector(".result-title", { timeout: 60_000 });
  assert.equal(p2.errors.length, 0);
});

// 3 ─ API unavailable -> clear error with retry
const p3 = await browser.newContext().then((c) => c.newPage());
await step("service outage shows a retryable error state", async () => {
  await p3.route("**/api/programs*", (route) => route.abort());
  await p3.goto(BASE);
  await p3.waitForSelector(".state-card");
  assert.match(await p3.textContent(".state-card"), /Can't reach the planner/);
  await p3.unroute("**/api/programs*");
  await p3.click(".state-card button");
  await p3.waitForSelector("#program");
});

// 4 ─ mobile
const m = await freshPage({ width: 390, height: 844 });
await step("mobile: builds a plan, sticky action bar, no horizontal overflow", async () => {
  assert.ok(await m.isVisible(".form-actions .primary"));
  await shot(m, "07-mobile-form");
  await build(m);
  assert.equal(await m.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
  // let the smooth scroll to the results settle before capturing
  await m.waitForFunction(() => new Promise((ok) => { const y = scrollY; setTimeout(() => ok(scrollY === y), 250); }));
  await shot(m, "08-mobile-plan");
  assert.equal(m.errors.length, 0);
});

await browser.close();
console.log(results.join("\n"));
console.log(process.exitCode ? "\nE2E FAILED" : `\nE2E passed (${results.length} checks)`);
