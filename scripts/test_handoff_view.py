"""The maintenance-handoff page: built from a real one_map build, self-contained, and faithful to the records.

Stdlib only; builds the fictional pasteurizer map into a temporary folder (no network, no model call).
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTEURIZER = ROOT / "examples" / "one-map" / "inputs" / "pasteurizer"
RENDER = ROOT / "examples" / "maintenance-handoff" / "render_handoff.py"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, capture_output=True, text=True, timeout=300)


class HandoffPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        built = run(ROOT / "scripts" / "one_map.py", "build", PASTEURIZER / "site-moc-close.json",
                    "--out", cls.out / "after", "--decisions", PASTEURIZER / "walkdown_rulings.csv")
        assert built.returncode == 0, built.stdout + built.stderr
        cls.page_path = cls.out / "HANDOFF.html"
        done = run(RENDER, "--after", cls.out / "after", "--tag", "FDV-2210", "--out", cls.page_path)
        assert done.returncode == 0, done.stdout + done.stderr
        cls.page = cls.page_path.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_shows_each_record_side_by_side_with_its_file(self):
        for text in ("AV-88412", "AV-51007", "DN50", "DN65", "WO-HISTORY", "CMMS-2026-10", "VALVE-DATASHEETS",
                     "lists/maintenance_equipment-moc.csv", "lists/valve_datasheets.csv", "row 7"):
            self.assertIn(text, self.page)

    def test_serial_is_settled_by_the_ruling_and_size_stays_open(self):
        self.assertIn("settled by field ruling: AV-88412", self.page)
        self.assertRegex(self.page, r'class="old"><span class="val">AV-51007')
        self.assertRegex(self.page, r'class="differs"><span class="val">DN50')
        self.assertIn("records disagree", self.page)

    def test_names_owners_and_does_not_decide_moc(self):
        self.assertRegex(self.page, r'<span class="who">Maintenance</span> · Change the serial number')
        self.assertRegex(self.page, r'<span class="who">Engineering</span> · Settle size')
        self.assertIn("Not decided here", self.page)
        self.assertNotRegex(self.page, r"(?i)moc (is|was) (required|not required)")

    def test_self_contained(self):
        self.assertNotRegex(self.page, r"(?i)<script|<link|@import|https?://|src=|url\(")

    def test_same_input_gives_same_bytes(self):
        again = self.out / "again.html"
        self.assertEqual(run(RENDER, "--after", self.out / "after", "--out", again).returncode, 0)
        self.assertEqual(again.read_bytes(), self.page_path.read_bytes())

    def test_missing_build_is_a_clear_error(self):
        r = run(RENDER, "--after", self.out / "nope", "--out", self.out / "x.html")
        self.assertEqual(r.returncode, 2)
        self.assertIn("missing", r.stderr)
        self.assertFalse((self.out / "x.html").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
