"""Original-source and explicit-interpretation checks for the context intake."""
import csv
import io
import unittest
import tempfile
from pathlib import Path

import context_basis as cb
import context_intake as ci


def contributions(value, quote, kind="number"):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=["Subject", "Predicate", "Source", "Locator",
                                             "Quote", "Value", "Type"], lineterminator="\n")
    writer.writeheader()
    writer.writerow({"Subject": "X/U/P", "Predicate": "value", "Source": "S", "Locator": "line 1",
                     "Quote": quote, "Value": value, "Type": kind})
    return text.getvalue().encode("utf-8")


def source_basis(raw):
    b = cb.Builder("X")
    b.source("S", "1", cb.raw_sha(raw), path="source.txt")
    b.entity("X/U/P", "P", "X/U")
    return b.finish()


class IntakeReviewRegressions(unittest.TestCase):
    def test_numeric_contribution_must_not_silently_round(self):
        for token in ("1e-999", "9007199254740993.0"):
            with self.subTest(token=token):
                original = (token + "\n").encode("utf-8")
                with self.assertRaisesRegex(cb.ContextError, "lossy numeric"):
                    ci.add_contributions(source_basis(original), {"source.txt": original},
                                         contributions(token, token))

    def test_quotation_must_match_declared_original_bytes(self):
        real, forged = b"REAL SOURCE\n", b"FORGED SOURCE\n"
        with self.assertRaisesRegex(cb.ContextError, "raw-byte binding mismatch"):
            ci.add_contributions(source_basis(real), {"source.txt": forged},
                                 contributions("An interpretation", "FORGED SOURCE", "text"))

    def test_open_order_physical_item_is_not_a_reported_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "work.csv").write_bytes(b"Area,Equipment,Order,Closed,Installed Item ID,Installed Serial\nU,P-1,WO-2,,FUTURE-ID,FUTURE-SERIAL\n")
            basis, _, _ = ci.prepare(root, "X", "P1")
            self.assertFalse([r for r in basis["relationships"] if r["predicate"] == "reported_installation_at"])
            self.assertFalse([e for e in basis["entities"] if e["identity_role"] == "physical_item"])
            self.assertTrue(any(r["value"] == "FUTURE-SERIAL" and r["predicate"] == "proposed_serial_number"
                                for r in basis["claims"]))


if __name__ == "__main__":
    unittest.main()
