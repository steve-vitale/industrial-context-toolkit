"""scripts/review_page.py: the offline review page and the decisions file it downloads.

Builds the quick-start bundle (import_site_drawing.py on examples/own-drawing) into a temporary folder, writes the
page, checks it is self-contained, lists every queue row and is byte-for-byte repeatable, then feeds the download
format (review_page.decisions_csv, which the page's JavaScript mirrors) to scripts/apply_review.py. A headless
browser check runs only when node and the playwright package are available (NODE_PATH); it presses the keys and
compares the page's own download with decisions_csv.
"""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import review_page  # noqa: E402


def py(script, *args):
    return subprocess.run([sys.executable, "-S", str(ROOT / "scripts" / script), *args],
                          capture_output=True, text=True, timeout=300)


class ReviewPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.bundle = cls.dir / "my-bundle"
        r = py("import_site_drawing.py", "--manifest", str(ROOT / "examples/own-drawing/manifest.json"),
               "--out", str(cls.bundle))
        assert r.returncode == 0, r.stderr
        cls.page = cls.dir / "review.html"
        r = py("review_page.py", str(cls.bundle), "--out", str(cls.page))
        assert r.returncode == 0, r.stderr
        cls.text = cls.page.read_text(encoding="utf-8")
        with open(cls.bundle / "review_queue.csv", encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            cls.cols = next(rd)
            cls.rows = list(rd)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def data(self):
        m = re.search(r'<script id="review-data" type="application/json">(.*?)</script>', self.text, re.S)
        return json.loads(m.group(1))

    def test_self_contained(self):
        self.assertNotRegex(self.text, r"https?://")
        self.assertNotIn("<link", self.text)
        self.assertNotRegex(self.text, r"<script[^>]*\ssrc=")
        self.assertIn("Nothing leaves this computer", self.text)
        self.assertIn("default-src 'none'", self.text)
        self.assertIn("data:image/", self.text)

    def test_every_queue_row_is_in_the_page(self):
        d = self.data()
        self.assertEqual(d["cols"], self.cols)
        self.assertEqual(d["rows"], self.rows)
        self.assertEqual(len(d["rows"]), 445)
        self.assertEqual(self.text.count("</script>"), 2)  # embedded text cannot close the data script

    def test_deterministic(self):
        again = self.dir / "again.html"
        self.assertEqual(py("review_page.py", str(self.bundle), "--out", str(again)).returncode, 0)
        self.assertEqual(again.read_bytes(), self.page.read_bytes())

    def test_refuses_a_stale_queue(self):
        bad = self.dir / "bad-bundle"
        shutil.copytree(self.bundle, bad)
        q = bad / "review_queue.csv"
        q.write_text(q.read_text(encoding="utf-8").replace("S0-IN001", "S0-IN001x", 1), encoding="utf-8")
        r = py("review_page.py", str(bad), "--out", str(self.dir / "bad.html"))
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.dir / "bad.html").exists())

    def decisions(self):
        ix = self.cols.index("item_id")
        ids = [r[ix] for r in self.rows]
        return ids, {ids[0]: {"d": "confirm", "n": "ok, matches the drawing"},
                     ids[1]: {"d": "reject"},
                     ids[2]: {"d": "correct", "v": [["tag", "TCV-1401"]], "n": "typo, a; semicolon"},
                     ids[3]: {"d": "correct", "v": [["tag", ""]]}}  # no value: left blank

    def test_download_format_is_accepted_by_apply_review(self):
        ids, dec = self.decisions()
        text = review_page.decisions_csv(self.cols, self.rows, dec)
        rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"), newline="")))
        self.assertEqual(len(rows), len(self.rows))
        self.assertEqual([r["OPS_confirm_or_correct"] for r in rows[:5]], ["confirm", "reject", "correct", "", ""])
        self.assertEqual(rows[2]["OPS_correct_value"], "tag=TCV-1401")
        model = self.dir / "model.json"
        shutil.copy(self.bundle / "plant_model.json", model)
        sheet = self.dir / "review_decisions.csv"
        sheet.write_bytes(text.encode("utf-8"))
        r = py("apply_review.py", str(model), str(sheet), "--reviewer", "Test, tester", "--date", "2026-01-01",
               "--record-dir", str(self.dir / "record"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        after = json.loads(model.read_text(encoding="utf-8"))
        items = {i["id"]: i for g in ("units", "instruments", "final_elements", "line_items", "offpage_connectors")
                 for i in after.get(g, [])}
        self.assertEqual(items[ids[0]]["ops_review"]["status"], "confirmed")
        self.assertEqual(items[ids[1]]["ops_review"]["status"], "rejected")
        self.assertEqual(items[ids[2]]["ops_review"]["status"], "corrected")
        self.assertEqual(items[ids[2]]["tag"], "TCV-1401")
        self.assertNotIn("ops_review", items[ids[3]])

    @unittest.skipUnless(shutil.which("node") and os.environ.get("NODE_PATH"),
                         "needs node and the playwright package (set NODE_PATH)")
    def test_browser_keys_and_download(self):
        out = self.dir / "dl"
        out.mkdir()
        r = subprocess.run(["node", str(ROOT / "scripts/review_page_browser_check.js"), str(self.page), str(out)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode:
            self.skipTest("playwright is not usable here: " + r.stderr[-200:])
        got = json.loads(r.stdout)
        self.assertEqual(got["requests"], [])
        self.assertEqual(got["csv"], got["mirror"])
        rows = list(csv.DictReader(io.StringIO(got["csv"].lstrip("﻿"), newline="")))
        by = {r["item_id"]: r for r in rows}
        first, second, third = got["items"]
        self.assertEqual(by[first]["OPS_confirm_or_correct"], "confirm")
        self.assertEqual(by[second]["OPS_confirm_or_correct"], "reject")
        self.assertEqual(by[third]["OPS_correct_value"], "tag=TCV-1401")
        self.assertEqual(by[third]["OPS_notes"], "checked against the original")
        ids = [r["item_id"] for r in rows]
        self.assertEqual(ids, [r[self.cols.index("item_id")] for r in self.rows])
        self.assertEqual(got["progress"], got["after"])  # decisions survive a reload


if __name__ == "__main__":
    unittest.main()
