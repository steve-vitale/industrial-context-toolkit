"""Check selected draft privacy and source/direction qualifications."""
import json
import unittest

import context_basis as cb
import context_components as cc
from test_context_basis import fixture, PUMP, OTHER, FIC, FT


class ComponentReviewRegressions(unittest.TestCase):
    def test_selected_draft_does_not_disclose_another_items_note(self):
        basis = fixture()
        note = cc.new_annotation(basis, OTHER, "private_note", "PRIVATE PROCESS DETAIL",
                                 "Only relevant to the other unit")
        basis["corrections"].append(note)
        draft = cc.generate(basis, item=PUMP)
        self.assertNotIn("PRIVATE PROCESS DETAIL", json.dumps(draft))
        self.assertNotIn("PRIVATE PROCESS DETAIL", cc.render(draft)["datasheets.md"])
        self.assertEqual(basis["corrections"][0]["value"], "PRIVATE PROCESS DETAIL")

    def test_readable_outline_retains_unknown_direction(self):
        basis = fixture()
        b = cb.Builder("CF/P1", basis)
        b.occurrence(FIC, "class", "INST", "CSV record 3; column Type", value="controller")
        basis = b.finish()
        next(e for e in basis["relationships"] if e["predicate"] == "reads")["direction"] = "unknown"
        output = cc.render(cc.generate(basis))["control-outline.md"]
        self.assertIn(FT, output)
        self.assertRegex(output.lower(), r"direction[ =:]unknown")


if __name__ == "__main__":
    unittest.main()

