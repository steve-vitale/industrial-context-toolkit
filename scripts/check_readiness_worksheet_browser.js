// Opens examples/readiness-audit/worksheet.html (the environment inventory) from disk in a real browser and checks:
//  1. "Try the example" fills the form and gives the expected table, flags and first job (reconcile);
//  2. the four first-job rules and their priority, run on the page's own logic;
//  3. each flag fires on its own trigger and not otherwise;
//  4. reach comes from the embedded table, with "check with IT" on unverified entries, and "None yet" gives No everywhere;
//  5. no tier or level words in the page text;
//  6. "Save as file" downloads a readable text summary;
//  7. no network request, no page error, and Print gives one page.
// It writes examples/readiness-audit/worksheet.png (1280 wide, deviceScaleFactor 1, example loaded).
// Run: NODE_PATH=<dir with playwright>/node_modules node scripts/check_readiness_worksheet_browser.js
// Not part of run_tests.py: it needs a browser. Exit 1 on any failed check.
const fs = require("fs");
const path = require("path");
const os = require("os");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const page_path = path.join(root, "examples", "readiness-audit", "worksheet.html");
const png = path.join(root, "examples", "readiness-audit", "worksheet.png");
const pdf = path.join(os.tmpdir(), "readiness-worksheet-check.pdf");
let failed = 0, passed = 0;
function check(ok, msg) { console.log((ok ? "PASS  " : "FAIL  ") + msg); if (ok) passed++; else failed++; }

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 1, acceptDownloads: true });
  const page = await ctx.newPage();
  const requests = [], errors = [];
  page.on("request", r => { const u = r.url(); if (!/^(file|data|blob):/.test(u)) requests.push(u); });
  page.on("pageerror", e => errors.push(String(e)));
  await page.goto(pathToFileURL(page_path).href);

  // 1. the example
  await page.click("#example");
  const ex = await page.evaluate(() => {
    const rows = [...document.querySelectorAll("#out table tr")].slice(1).map(tr => [...tr.cells].map(c => c.textContent));
    return { rows, flags: [...document.querySelectorAll("#out .flags li")].map(l => l.textContent), job: (document.querySelector("#out .job") || {}).textContent, href: (document.querySelector("#out .job a") || {}).getAttribute("href"), assistant: document.querySelector("#out h3").textContent, caveat: [...document.querySelectorAll("#out ul.small li")].map(l => l.textContent).join(" ") };
  });
  console.log("\nExample table:\n" + ex.rows.map(r => "  " + r.join(" | ")).join("\n") + "\nFlags:\n" + ex.flags.map(f => "  " + f).join("\n") + "\nJob: " + ex.job + "\n");
  const row = n => ex.rows.find(r => r[0] === n);
  check(/Microsoft 365 Copilot/.test(ex.assistant), "example assistant is Microsoft 365 Copilot");
  check(row("Maintenance")[1] === "SAP PM / S/4HANA" && /Usually, by a report or export/.test(row("Maintenance")[3]), "Maintenance: SAP PM, exportable by report");
  check(row("Drawings")[1] === "Shared network drive" && /Already files/.test(row("Drawings")[3]) && /Working copies/.test(row("Drawings")[4]), "Drawings: shared drive, already files, working copies noted");
  check(/Spreadsheets on a shared drive/.test(row("Equipment and instrument data")[1]), "Equipment data: spreadsheets on a shared drive");
  check(row("Process safety and quality")[1] === "SharePoint" && /^Yes/.test(row("Process safety and quality")[2]), "Process safety: SharePoint, reachable by Copilot");
  check(row("Control and process data")[1] === "None" && row("Control and process data")[2] === "-", "Control data: none, nothing to reach");
  check(row("Vendor and project records")[1] === "Not answered", "kinds left blank show Not answered");
  check(/Only if your IT has turned on or added a connector/.test(row("Drawings")[2]), "Drawings on a shared drive: connector, as verified for Microsoft 365 Copilot");
  check(/No ready-made connector/.test(row("Maintenance")[2]), "Maintenance in SAP PM: no ready-made connector (custom)");
  check(ex.flags.length === 4 && /No assistant has a ready-made connector to SAP PM \/ S\/4HANA\. Start from an export\./.test(ex.flags[0]), "the no-connector flag comes first (" + ex.flags[0] + ")");
  check(ex.caveat && /The 'yes' cells need a Microsoft 365 Copilot licence\. The free Copilot Chat only reads files you upload\./.test(ex.caveat), "the Copilot licence caveat is shown under the table");
  check(ex.flags.some(f => /working copy instead of the released one/.test(f)) && ex.flags.some(f => /Nobody can say which drawing is current/.test(f)) && ex.flags.some(f => /fall behind after every job/.test(f)), "example flags: working copies, no current drawing, records fall behind");
  check(/Reconcile the equipment list against the work orders/.test(ex.job) && /MAINTENANCE_START\.md$/.test(ex.href), "example first job: reconcile the equipment list (MAINTENANCE_START.md)");

  // 2. first-job rules and priority, on the page's own compute()
  const base = () => ({ unit: "", assistant: "m365", homes: D.families.map(() => ({ sys: "", other: "", wc: "" })), drawings: { formats: [], master: "", register: "" }, changes: { update: "", why: "" } });
  const jobFor = fn => page.evaluate(([src]) => { const D2 = D; const st = { unit: "", assistant: "m365", homes: D2.families.map(() => ({ sys: "", other: "", wc: "" })), drawings: { formats: [], master: "", register: "" }, changes: { update: "", why: "" } }; (new Function("st", "idx", src))(st, D2.familyIndex); const j = compute(st).job; return j ? j.id : null; }, [fn]);
  const j1 = await jobFor('st.homes[idx["Maintenance"]].sys = "maximo"; st.homes[idx["Equipment and instrument data"]].sys = "insidecmms";');
  check(j1 === "reconcile", "rule 1: CMMS that exports + equipment data in files or a system -> reconcile (" + j1 + ")");
  const j1b = await jobFor('st.homes[idx["Maintenance"]].sys = "sheets"; st.homes[idx["Equipment and instrument data"]].sys = "sheets_drive"; st.drawings.formats = ["pdf"]; st.drawings.register = "no";');
  check(j1b === "drawing-register", "rule 2: PDFs and no register, no CMMS -> drawing register (" + j1b + ")");
  const j1c = await jobFor('st.homes[idx["Maintenance"]].sys = "sap"; st.homes[idx["Equipment and instrument data"]].sys = "paper"; st.drawings.formats = ["scans"]; st.drawings.register = "unsure";');
  check(j1c === "drawing-register", "rule 2: scans and Not sure on the register -> drawing register (" + j1c + ")");
  const j1d = await jobFor('st.homes[idx["Maintenance"]].sys = "sap"; st.homes[idx["Equipment and instrument data"]].sys = "sheets_drive"; st.drawings.formats = ["pdf"]; st.drawings.register = "no";');
  check(j1d === "reconcile", "priority: reconcile beats drawing register when both apply (" + j1d + ")");
  const j3 = await jobFor('st.homes[idx["Maintenance"]].sys = "sheets"; st.homes[idx["Drawings"]].sys = "sharepoint"; st.drawings.formats = ["cad"]; st.drawings.register = "yes";');
  check(j3 === "ask-one-question", "rule 3: assistant allowed and a kind of record is reachable -> ask one question (" + j3 + ")");
  const j3b = await jobFor('st.assistant = "none"; st.homes[idx["Maintenance"]].sys = "sheets"; st.homes[idx["Drawings"]].sys = "sharepoint"; st.drawings.formats = ["cad"]; st.drawings.register = "yes";');
  check(j3b === "list-records", "rule 4: no assistant -> list the records for one unit (" + j3b + ")");
  const j4 = await jobFor('st.homes[idx["Maintenance"]].sys = "paper"; st.homes[idx["Drawings"]].sys = "netdrive"; st.drawings.formats = ["cad"]; st.drawings.register = "yes";');
  check(j4 === "list-records", "rule 4: nothing reachable -> list the records (" + j4 + ")");
  const j0 = await jobFor("");
  check(j0 === null, "no homes picked -> no suggestion yet");
  const one = await page.evaluate(() => document.querySelectorAll("#out .job").length);
  check(one <= 1, "never more than one suggested job");

  // 3. flags, each on its own trigger
  const flags = await page.evaluate(() => {
    const mk = patch => { const st = { unit: "", assistant: "m365", homes: D.families.map(() => ({ sys: "", other: "", wc: "" })), drawings: { formats: [], master: "yes", register: "yes" }, changes: { update: "doccontrol", why: "moc" } }; patch(st); return computeFlags(st).map(f => f.id); };
    return {
      none: mk(() => {}), wc: mk(s => { s.homes[0].sys = "netdrive"; s.homes[0].wc = "yes"; }), master: mk(s => { s.drawings.master = "no"; }), reg: mk(s => { s.drawings.register = "unsure"; }),
      whoever: mk(s => { s.changes.update = "whoever"; }), nobody: mk(s => { s.changes.update = "nobody"; }), ask: mk(s => { s.changes.why = "ask"; }), cannot: mk(s => { s.changes.why = "cannot"; }),
      cad: mk(s => { s.drawings.formats = ["cad"]; }), scans: mk(s => { s.drawings.formats = ["scans"]; }), pdfOnly: mk(s => { s.drawings.formats = ["pdf"]; }),
      custom: mk(s => { s.homes[2].sys = "maximo"; s.homes[5].sys = "pi"; s.homes[0].sys = "opentext"; s.drawings.master = "no"; }), customChat: mk(s => { s.assistant = "chatgpt"; s.homes[2].sys = "sap"; }),
      engineer: mk(s => { s.changes.update = "engineer"; s.changes.why = "email"; }), noasst: mk(s => { s.assistant = "none"; }), paper: mk(s => { s.homes[3].sys = "paper"; })
    };
  });
  check(flags.none.length === 0, "no flags when everything is in order");
  check(flags.wc.join() === "working-copies", "working copies on a shared drive -> flag");
  check(flags.master.join() === "no-current-drawing" && flags.reg.join() === "no-current-drawing", "no master copy, or no register -> 'Nobody can say which drawing is current'");
  check(flags.whoever.join() === "records-fall-behind" && flags.nobody.join() === "records-fall-behind", "'Whoever remembers' or 'Nobody formally' -> records fall behind");
  check(flags.ask.join() === "reasons-in-heads" && flags.cannot.join() === "reasons-in-heads", "'Ask someone' or 'couldn't find out' -> reasons live in people's heads");
  check(flags.cad.join() === "cad-files" && flags.scans.join() === "scanned-drawings" && flags.pdfOnly.length === 0, "CAD files and scans each raise their own flag; PDFs alone raise none");
  check(flags.custom.join() === "no-connector,no-connector,no-current-drawing", "CMMS and historian with 'custom' raise the no-connector flag first, one per system (" + flags.custom.join() + ")");
  check(flags.customChat.join() === "no-connector", "ChatGPT: a CMMS also has no ready-made connector");
  check(flags.engineer.length === 0, "the engineer who did the work, and a search of email, raise no flag");
  check(flags.noasst.join() === "no-assistant" && flags.paper.join() === "paper-or-unknown", "no assistant, and paper kinds, each raise their own flag");

  // 4. reach
  const reach = await page.evaluate(() => ({ m365sp: reachOf("m365", "sharepoint"), none: reachOf("none", "sharepoint"), nonePaper: reachOf("none", "paper"), unsure: reachOf("unsure", "sharepoint"), hist: reachOf("m365", "pi"), na: reachOf("m365", "nohist"), hex: reachOf("m365", "hexagon"), moc: reachOf("m365", "moc"), gd: reachOf("gemini", "gdrive") }));
  check(reach.m365sp.v === "yes" && !reach.m365sp.unverified && /^https:\/\/learn\.microsoft\.com\//.test(reach.m365sp.source), "reach comes from the verified table, with a source");
  check(reach.none.v === "unknown" && reach.nonePaper.v === "no" && reach.unsure.v === "unknown", "None yet and Not sure: everything unknown except paper = no");
  check(reach.hist.v === "custom" && reach.na.v === "na" && reach.gd.v === "yes", "historian -> custom, 'None' -> nothing to reach, Gemini reads Google Drive");
  check(reach.hex.v === "custom" && reach.hex.unverified === true && reach.moc.v === "unknown", "Hexagon Meridian keeps its unconfirmed marker; MOC software is unknown");
  const hdr = await page.evaluate(() => { setRadio("assistant", "none"); update(); const h = document.querySelector("#out table th:nth-child(3)").textContent; setRadio("assistant", "m365"); update(); return h; });
  check(hdr === "An assistant would need these routes", "None yet changes the reach column header");

  // 5. no tier or level words
  const body = await page.evaluate(() => document.querySelector("main").innerText);
  check(!/\btier\b|Visible \d|level \d/i.test(body), "no tiers or levels in the page text");

  // 6. save as file
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#save")]);
  const saved = fs.readFileSync(await dl.path(), "utf8");
  check(dl.suggestedFilename() === "where-our-records-live.txt" && /Suggested first job: Reconcile/.test(saved) && /Lakeside/.test(saved) && /Things to know:/.test(saved), "Save as file writes a readable summary (" + saved.length + " characters)");

  // 7. screenshot, print, network
  await page.screenshot({ path: png, fullPage: true });
  console.log("\nScreenshot: " + png + " (" + fs.statSync(png).size + " bytes)");
  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: pdf, format: "Letter", printBackground: true });
  const pages = (fs.readFileSync(pdf, "latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
  check(pages === 1, "Print gives " + pages + " page(s) with the example loaded");
  await page.emulateMedia({ media: "screen" });
  await page.evaluate(() => { D.families.forEach((f, i) => { document.getElementById("home" + i).value = "other"; document.getElementById("other" + i).value = "A long home name typed by the engineer for kind " + i; }); update(); });
  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: pdf, format: "Letter", printBackground: true });
  const pagesFull = (fs.readFileSync(pdf, "latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
  check(pagesFull === 1, "Print gives " + pagesFull + " page(s) with all eight kinds filled in");
  check(requests.length === 0, "no network requests (" + requests.length + ")");
  check(errors.length === 0, "no page errors" + (errors.length ? ": " + errors.join("; ") : ""));
  await browser.close();
  console.log("\n" + passed + " passed, " + failed + " failed");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
