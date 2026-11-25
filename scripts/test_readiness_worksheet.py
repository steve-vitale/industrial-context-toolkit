"""The environment inventory page (examples/readiness-audit/worksheet.html) is offline, asks only facts people know, and its
embedded data is consistent: every assistant x system reach cell exists with a source field, every home it offers exists,
the first-job priority order and the flags are the agreed ones, and every relative link resolves. A small Python mirror of
the documented first-job rule checks the example. The page's own behaviour is exercised in a real browser by
scripts/check_readiness_worksheet_browser.js. Stdlib only."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "examples" / "readiness-audit" / "worksheet.html"
LINKEDIN = "https://www.linkedin.com/in/steve-vitale/"
REAL = ["m365", "chatgpt", "gemini", "other"]


def page_text():
    return PAGE.read_text(encoding="utf-8")


def data():
    m = re.search(r'<script type="application/json" id="inventory-data">(.*?)</script>', page_text(), re.S)
    assert m
    return json.loads(m.group(1).replace("<\\/", "</"))


SOURCE_HOSTS = ("learn.microsoft.com", "help.openai.com", "openai.com", "docs.cloud.google.com", "support.google.com")


def outside_data(html):
    """The page with the embedded data block removed: only visible text and code remain."""
    return re.sub(r'<script type="application/json" id="inventory-data">.*?</script>', "", html, flags=re.S)


def choose_job(d, st):
    """Python mirror of the page's documented first-job priority: reconcile, drawing-register, ask-one-question, list-records."""
    sysd = {s["id"]: s for s in d["systems"]}
    homes = st["homes"]
    if not any(h.get("sys") for h in homes.values()):
        return None
    m = sysd.get(homes.get("Maintenance", {}).get("sys"))
    e = sysd.get(homes.get("Equipment and instrument data", {}).get("sys"))
    if m and m["group"] == "cmms" and m["export"] == "report" and e and e["export"] in ("report", "files"):
        return "reconcile"
    if ({"pdf", "scans"} & set(st.get("formats", []))) and st.get("register") in ("no", "unsure"):
        return "drawing-register"
    reachable = any(d["reach"].get(st["assistant"], {}).get(h["sys"], {}).get("v") == "yes" for h in homes.values() if h.get("sys"))
    if st["assistant"] in REAL and reachable:
        return "ask-one-question"
    return "list-records"


class OfflineTest(unittest.TestCase):
    def test_no_network_references(self):
        html = page_text()
        page = outside_data(html)
        # Outside the data block the one permitted URL is the owner's LinkedIn link, as a plain anchor (on screen and on the printout).
        self.assertEqual(re.findall(r"https?://[^\s\"'<>]+", page), [LINKEDIN] * 4)
        self.assertEqual(page.count('<a href="%s">%s</a>' % (LINKEDIN, LINKEDIN)), 2)
        self.assertEqual(page.count("Want a second look at your setup? Send me this page on LinkedIn: "), 2)
        stripped = page.replace('<a href="%s">%s</a>' % (LINKEDIN, LINKEDIN), "")
        self.assertIsNone(re.search(r"https?:|//[a-z0-9.-]+\.[a-z]{2,}", stripped, re.I), "no other URLs outside the data")
        # Inside the data block the only URLs are vendor-documentation sources, kept as text and never fetched or linked.
        for u in re.findall(r"https?://[^\s\"'<>]+", json.dumps(data())):
            self.assertTrue(u.startswith("https://") and u.split("/")[2] in SOURCE_HOSTS, u)
        self.assertIsNone(re.search(r"<script[^>]*\bsrc\s*=", html, re.I), "no <script src>")
        self.assertIsNone(re.search(r"<link\b|<img\b|<iframe\b", html, re.I), "no <link>, <img> or <iframe>")
        self.assertIsNone(re.search(r"@import|url\(|fetch\(|XMLHttpRequest|WebSocket|sendBeacon|FileReader|\.href\s*=|window\.open|location\s*=", page), "no network or navigation calls")

    def test_no_other_contact_line(self):
        self.assertIsNone(re.search(r"mailto:|@[a-z0-9-]+\.[a-z]{2,}", page_text(), re.I))

    def test_relative_links_resolve(self):
        text = page_text()
        links = re.findall(r'(\.\./\.\./[A-Za-z0-9_./-]+?\.md)(?:#[^"\s]*)?"', text)
        self.assertGreaterEqual(len(set(links)), 5)
        for href in set(links):
            self.assertTrue((PAGE.parent / href).exists(), href)
        self.assertIn("../../docs/READINESS_AUDIT.md", text)


class DataTest(unittest.TestCase):
    def test_reach_table_shape(self):
        d = data()
        ids = [s["id"] for s in d["systems"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(d["reach"]), sorted(REAL))
        for a in REAL:
            self.assertEqual(sorted(d["reach"][a]), sorted(ids), a)
            for sid, cell in d["reach"][a].items():
                self.assertIn(cell["v"], ("yes", "connector", "custom", "no", "unknown"), (a, sid))
                self.assertIn("source", cell, (a, sid))
                self.assertIsInstance(cell["unverified"], bool)
                if cell["v"] in ("yes", "connector", "custom") or (cell["v"] == "no" and a != "other" and sid not in ("nohist", "none")):
                    self.assertTrue(cell["source"].startswith("https://"), "every known cell has a source: %s %s" % (a, sid))
                if cell["v"] == "unknown":
                    self.assertEqual(cell["source"], "", (a, sid))

    def test_verified_values_from_the_brief(self):
        r = data()["reach"]
        for sid in ("sharepoint", "notes", "email", "chat"):
            self.assertEqual(r["m365"][sid]["v"], "yes", sid)
        for sid in ("netdrive", "sheets_drive", "opentext"):
            self.assertEqual(r["m365"][sid]["v"], "connector", sid)
        for sid in ("sap", "maximo", "infor", "emaint", "fiix", "upkeep", "limble", "insidecmms", "projectwise", "autodesk", "instrdb", "pi", "ignition", "canary", "dcs"):
            for a in ("m365", "chatgpt"):
                self.assertEqual(r[a][sid]["v"], "custom", (a, sid))
        self.assertEqual(r["m365"]["hexagon"], {"v": "custom", "unverified": True, "source": r["m365"]["hexagon"]["source"]})
        self.assertEqual([k for k, c in r["m365"].items() if c["unverified"]], ["hexagon"])
        for sid in ("moc", "quality"):
            for a in REAL:
                self.assertEqual(r[a][sid]["v"], "unknown", (a, sid))
        for a in ("m365", "chatgpt", "gemini"):
            self.assertEqual((r[a]["paper"]["v"], r[a]["vendorportal"]["v"]), ("no", "no"))
        for sid in ("sharepoint", "notes", "email", "chat"):
            self.assertEqual(r["chatgpt"][sid]["v"], "connector", sid)
            self.assertEqual(r["gemini"][sid]["v"], "connector", sid)
        self.assertEqual(r["gemini"]["gdrive"]["v"], "yes")
        self.assertEqual(r["gemini"]["netdrive"]["v"], "custom")
        self.assertTrue(all(c["v"] in ("unknown", "no") for c in r["other"].values()))
        self.assertEqual(r["other"]["paper"]["v"], "no")

    def test_caveats(self):
        c = data()["caveats"]
        self.assertIn("The 'yes' cells need a Microsoft 365 Copilot licence. The free Copilot Chat only reads files you upload.", c["m365"])

    def test_every_offered_home_exists_and_lists_match_the_brief(self):
        d = data()
        sysd = {s["id"]: s for s in d["systems"]}
        want = {
            "Maintenance": ["SAP PM / S/4HANA", "IBM Maximo", "Infor EAM", "eMaint", "Fiix", "UpKeep", "Limble", "Spreadsheets"],
            "Drawings": ["SharePoint", "OpenText", "Hexagon", "Bentley ProjectWise", "Autodesk Vault", "Shared network drive"],
            "Equipment and instrument data": ["Spreadsheets on a shared drive", "SharePoint", "Instrument database", "Inside the CMMS"],
            "Operations": ["SharePoint", "Document control system", "Shared network drive"],
            "Process safety and quality": ["MOC software", "Quality system", "SharePoint", "Shared network drive"],
            "Control and process data": ["AVEVA PI", "Ignition", "Canary", "DCS / PLC historian", "None"],
            "Vendor and project records": ["SharePoint", "Shared network drive", "Vendor portals", "Project folders on a drive"],
            "Decisions and conversations": ["Email", "Teams / Slack chat", "Meeting notes on SharePoint / OneNote", "Notebooks"],
        }
        self.assertEqual([f["name"] for f in d["families"]], ["Drawings", "Equipment and instrument data", "Maintenance", "Operations",
                         "Process safety and quality", "Control and process data", "Vendor and project records", "Decisions and conversations"])
        for f in d["families"]:
            labels = [sysd[o]["label"] for o in f["options"]]
            for w in want[f["name"]]:
                self.assertTrue(any(l.startswith(w) for l in labels), (f["name"], w))
            for generic in ("Other (type it)", "Paper / binders", "Don't know", "We don't keep these"):
                self.assertIn(generic, labels, f["name"])
            self.assertTrue(f["hint"])

    def test_assistants_and_choices(self):
        d = data()
        self.assertEqual([a[1] for a in d["assistants"]], ["Microsoft 365 Copilot", "ChatGPT Enterprise / Team / Edu", "Gemini in Google Workspace",
                                                           "Another approved assistant", "None yet", "Not sure"])
        self.assertEqual([x[1] for x in d["formats"]], ["CAD files", "PDFs made from CAD", "Scans", "Paper"])
        self.assertEqual([x[1] for x in d["updateOptions"]], ["Doc control on a request", "The engineer who did the work", "Whoever remembers", "Nobody formally", "Not sure"])
        self.assertEqual([x[1] for x in d["whyOptions"]], ["MOC record", "Search email", "Ask someone", "We couldn't find out"])

    def test_first_job_priority_order_and_links(self):
        d = data()
        self.assertEqual([j["id"] for j in d["jobs"]], ["reconcile", "drawing-register", "ask-one-question", "list-records"])
        self.assertEqual([j["link"] for j in d["jobs"]], ["../../docs/MAINTENANCE_START.md", "../../docs/DRAWING_RECOVERY.md",
                                                          "../../examples/first-pilot/README.md", "../../docs/ORGANIZATION_START.md"])
        for j in d["jobs"]:
            self.assertTrue((PAGE.parent / j["link"]).exists(), j["link"])
            self.assertTrue(j["name"] and j["why"])

    def test_flag_sentences(self):
        f = data()["flags"]
        self.assertEqual(f["working-copies"], "Your assistant may find a working copy instead of the released one.")
        self.assertEqual(f["no-current-drawing"], "Nobody can say which drawing is current.")
        self.assertEqual(f["records-fall-behind"], "Records fall behind after every job.")
        self.assertEqual(f["reasons-in-heads"], "The reasons for changes live in people's heads.")
        self.assertEqual(f["cad-files"], "Assistants read the PDF, not the CAD file. A connector indexes a CAD file's name only.")
        self.assertEqual(f["scanned-drawings"], "Scanned drawings need text recognition before an assistant can read them. SharePoint can add it to new uploads, but check whether your assistant uses it.")
        self.assertEqual(f["no-connector"], "No assistant has a ready-made connector to {system}. Start from an export.")

    def test_no_rating_or_tier_in_the_main_flow(self):
        html = page_text()
        body = html[html.index("<main>"):html.index('<script type="application/json"')]
        self.assertIsNone(re.search(r"\b[Tt]ier\b|Visible \d|level \d|\brating\b", body.replace("No quality ratings", "")), "no tiers or levels")


class ExampleTest(unittest.TestCase):
    def test_example_is_the_fictional_lakeside_case(self):
        ex = data()["example"]
        self.assertIn("Lakeside", ex["unit"])
        self.assertEqual(ex["assistant"], "m365")
        h = ex["homes"]
        self.assertEqual((h["Maintenance"]["sys"], h["Drawings"]["sys"], h["Drawings"]["wc"], h["Equipment and instrument data"]["sys"],
                          h["Process safety and quality"]["sys"], h["Control and process data"]["sys"]),
                         ("sap", "netdrive", "yes", "sheets_drive", "sharepoint", "nohist"))
        self.assertEqual(ex["formats"], ["pdf"])
        self.assertEqual(ex["update"], "whoever")

    def test_example_first_job_is_reconcile(self):
        d = data()
        self.assertEqual(choose_job(d, d["example"]), "reconcile")

    def test_priority_rules(self):
        d = data()
        base = {"assistant": "m365", "formats": [], "register": "", "homes": {"Maintenance": {"sys": "sap"}, "Equipment and instrument data": {"sys": "sheets_drive"},
                                                                                 "Drawings": {"sys": "sharepoint"}}}
        self.assertEqual(choose_job(d, base), "reconcile")
        no_cmms = json.loads(json.dumps(base)); no_cmms["homes"]["Maintenance"]["sys"] = "sheets"
        no_cmms["formats"], no_cmms["register"] = ["pdf"], "no"
        self.assertEqual(choose_job(d, no_cmms), "drawing-register")
        no_cmms["register"] = "yes"
        self.assertEqual(choose_job(d, no_cmms), "ask-one-question")      # m365 reads SharePoint
        no_cmms["assistant"] = "none"
        self.assertEqual(choose_job(d, no_cmms), "list-records")
        self.assertIsNone(choose_job(d, {"assistant": "m365", "formats": [], "homes": {}}))
        both = json.loads(json.dumps(base)); both["formats"], both["register"] = ["scans"], "unsure"
        self.assertEqual(choose_job(d, both), "reconcile")               # priority: reconcile beats drawing-register


if __name__ == "__main__":
    unittest.main()
