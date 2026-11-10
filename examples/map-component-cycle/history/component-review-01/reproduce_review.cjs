/** Actual desktop/390px component-review interactions and downloaded-edit roundtrip.
 * Optional Playwright is required for this development runner, not for toolkit use.
 * PLAYWRIGHT_PACKAGE may select an existing install; BROWSER_EXE a local browser.
 * Uses only the frozen fictional development records; no company/product accounts.
 */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE || "playwright");

const root = path.resolve(__dirname, "../..");
const destination = process.argv[2];
assert(destination, "Give a new output directory");
const out = path.resolve(destination);
assert(!fs.existsSync(out), "Output exists; retain it and choose another");
fs.mkdirSync(out, { recursive: true });
const python = process.env.PYTHON || "python";
const key = JSON.parse(fs.readFileSync(path.join(__dirname, "inputs/EXPECTED.json"), "utf8"));
const calls = [], observations = [];
const sha = data => crypto.createHash("sha256").update(data).digest("hex");
const pins = Object.fromEntries([
  "scripts/context_basis.py", "scripts/context_components.py", "scripts/context_intake.py",
  "scripts/context_packet.py", "scripts/context_workflow.py", "scripts/context_review.py",
  "scripts/context_review_html.py", "examples/map-component-cycle/reproduce_review.cjs",
  "examples/map-component-cycle/inputs/EXPECTED.json", "examples/map-component-cycle/UI-PLAN.md",
].map(name => [name, sha(fs.readFileSync(path.join(root, name)).toString("utf8").replaceAll("\r\n", "\n"))]));
function persist(extra = {}) {
  fs.writeFileSync(path.join(out, "run.json"), JSON.stringify({
    schema: "component-review-browser-development-1", pins_sha256_lf: pins,
    calls, observations, node: process.version, platform: process.platform,
    qualification: "Actual fictional-source browser/software execution; no human/plant/product acceptance",
    ...extra,
  }, null, 2) + "\n");
}
function cli(args, exit = 0, reason) {
  const began = performance.now();
  const run = spawnSync(python, ["-B", "-S", path.join(root, "scripts/context_workflow.py"), ...args],
    { cwd: out, encoding: "utf8", timeout: 60000 });
  calls.push({ args, exit: run.status, stdout: run.stdout, stderr: run.stderr,
    milliseconds: performance.now() - began });
  persist();
  assert.equal(run.status, exit, run.stderr || String(run.error));
  if (reason) assert(run.stderr.includes(reason), run.stderr);
  return JSON.parse(exit === 0 ? run.stdout : run.stderr);
}
let browser, server;
(async () => {
  const contributions = path.join(out, "contributions.csv");
  fs.writeFileSync(contributions, "Subject,Predicate,Source,Locator,Quote,Target\n" +
    `${key.subjects[4]},reads,NOTE,line 4,FIC-101 reads FT-101 and adjusts FV-101.,${key.subjects[3]}\n` +
    `${key.subjects[4]},commands,NOTE,line 4,FIC-101 reads FT-101 and adjusts FV-101.,${key.subjects[5]}\n`);
  const initial = path.join(out, "initial");
  cli(["prepare", "--records", path.join(__dirname, "inputs/development/rev1"),
    "--site", key.site, "--plant", key.plant, "--contributions", contributions, "--out", initial]);
  let servedHtml = path.join(out, "review.html");
  cli(["review", initial, "--out", servedHtml]);
  cli(["verify-review", initial, servedHtml]);
  server = http.createServer((req, res) => {
    if (req.method !== "GET" || req.url !== "/review.html") { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
    res.end(fs.readFileSync(servedHtml));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const url = `http://127.0.0.1:${server.address().port}/review.html`;
  browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_EXE ?
    { executablePath: process.env.BROWSER_EXE } : {}) });
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, acceptDownloads: true });
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on("pageerror", error => errors.push(String(error)));
    page.on("request", request => requests.push(request.url()));
    servedHtml = path.join(out, "review.html");
    await page.goto(url);
    await page.getByLabel("Find a tag or scoped item").fill("P-101");
    const choices = await page.locator("#items button").allTextContents();
    assert.deepEqual(choices.sort(), [key.subjects[0], key.subjects[1]].sort());
    await page.getByRole("button", { name: key.subjects[0], exact: true }).click();
    await page.getByLabel("Component draft").selectOption("item_datasheet_scaffold");
    const flow = page.locator('[data-field="rated_flow"]');
    const flowText = await flow.innerText();
    assert(flowText.includes("Sources disagree"));
    for (const value of key.revisions[0].flow_alternatives) assert(flowText.includes(value));
    assert(flowText.includes("EQ") && flowText.includes("DS"));
    await flow.getByText("Source version, review and lineage", { exact: true }).last().click();
    const expandedSource = await flow.innerText();
    assert(expandedSource.includes('"revision":"1"'));
    assert((await page.locator('[data-field="operating_limits"]').innerText()).includes("Not supplied"));
    assert(!(await page.locator("#fields").innerText()).includes("Recorded direction: null"));
    await page.screenshot({ path: path.join(out, `${width}-pump.png`), fullPage: true });
    await page.getByLabel("Find a tag or scoped item").fill("FIC-101");
    await page.getByRole("button", { name: key.subjects[4], exact: true }).click();
    await page.getByLabel("Component draft").selectOption("loop_control_narrative_outline");
    assert((await page.locator('[data-field="reads"]').innerText()).includes(key.subjects[3]));
    assert((await page.locator('[data-field="commands"]').innerText()).includes(key.subjects[5]));
    assert((await page.locator('[data-field="trip_settings"]').innerText()).includes("Not supplied"));
    await page.screenshot({ path: path.join(out, `${width}-controller.png`), fullPage: true });
    await page.getByLabel("Find a tag or scoped item").fill("P-101");
    await page.getByRole("button", { name: key.subjects[0], exact: true }).click();
    await page.getByRole("button", { name: "Download proposed edit", exact: true }).click();
    assert((await page.getByRole("status").innerText()).includes("Add a reason"));
    await page.getByLabel("Proposed text or review note").fill("é".repeat(32768));
    await page.getByLabel("Reason and evidence still needed").fill("é".repeat(32768));
    const overLimit = page.waitForEvent("download", { timeout: 1000 }).catch(() => null);
    await page.getByRole("button", { name: "Download proposed edit", exact: true }).click();
    const rejectedDownload = await overLimit;
    if (rejectedDownload) await rejectedDownload.saveAs(path.join(out, `${width}-unexpected-overlimit-edit.json`));
    assert.equal(rejectedDownload, null, "Over-limit proposal must refuse before downloading an unapplyable edit");
    assert((await page.getByRole("status").innerText()).includes("Shorten"));
    await page.getByLabel("Proposed text or review note").fill(key.manual_edit_control.value);
    await page.getByLabel("Reason and evidence still needed").fill("Awaiting permitted nameplate evidence");
    const [download] = await Promise.all([page.waitForEvent("download"),
      page.getByRole("button", { name: "Download proposed edit", exact: true }).click()]);
    const edit = path.join(out, `${width}-downloaded-edit.json`);
    await download.saveAs(edit);
    const downloaded = JSON.parse(fs.readFileSync(edit, "utf8"));
    assert.equal(downloaded.value, key.manual_edit_control.value);
    assert.equal(downloaded.subject, key.subjects[0]);
    const edited = path.join(out, `${width}-edited`);
    cli(["apply-review", initial, "--edit", edit, "--out", edited]);
    cli(["verify", edited]);
    const before = JSON.parse(fs.readFileSync(path.join(initial, "basis.json"), "utf8"));
    const after = JSON.parse(fs.readFileSync(path.join(edited, "basis.json"), "utf8"));
    assert.deepEqual(after.claims, before.claims);
    assert.deepEqual(after.sources, before.sources);
    assert.equal(after.corrections[0].value, key.manual_edit_control.value);
    const reopened = path.join(out, `${width}-reopened.html`);
    cli(["review", edited, "--out", reopened]);
    servedHtml = reopened;
    await page.reload();
    await page.getByLabel("Find a tag or scoped item").fill("P-101");
    await page.getByRole("button", { name: key.subjects[0], exact: true }).click();
    assert((await page.locator("#notes").innerText()).includes(key.manual_edit_control.value));
    assert((await page.locator("#notes").innerText()).includes("Proposed edit"));
    const next = path.join(out, `${width}-revision2`);
    cli(["prepare", "--records", path.join(__dirname, "inputs/development/rev2"),
      "--site", key.site, "--plant", key.plant, "--contributions", contributions,
      "--previous", edited, "--out", next]);
    cli(["apply-review", next, "--edit", edit, "--out", path.join(out, `${width}-stale-refused`)],
      2, "packet changed");
    const geometry = await page.evaluate(() => ({ viewport: innerWidth,
      page: document.documentElement.scrollWidth,
      unreachable: [...document.querySelectorAll('input,select,textarea,button')].filter(n => {
        const r = n.getBoundingClientRect(); return r.width && (r.left < 0 || r.right > innerWidth + 1);
      }).map(n => n.id || n.textContent) }));
    assert(geometry.page <= width + 1 && !geometry.unreachable.length, JSON.stringify(geometry));
    assert.deepEqual(errors, []);
    assert(requests.every(request => request === url), "Unexpected external request");
    await page.screenshot({ path: path.join(out, `${width}-retained-edit.png`), fullPage: true });
    observations.push({ width, choices, flowText, expandedSource, download_sha256: sha(fs.readFileSync(edit)),
      geometry, errors, request_count: requests.length, browser_version: browser.version(), result: "pass" });
    persist({ outcome: "in_progress" });
    await context.close();
  }
  persist({ outcome: "pass" });
  console.log(JSON.stringify({ outcome: "pass", output: out, widths: observations.map(o => o.width) }));
})().catch(error => {
  persist({ outcome: "failed", error: String(error.stack || error) });
  console.error(String(error.stack || error)); process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
});
