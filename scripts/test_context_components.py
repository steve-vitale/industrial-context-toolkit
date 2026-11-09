"""Check selected draft privacy and source/direction qualifications."""
import json
import copy
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

    def test_relationship_edit_tracks_actual_roots_and_rebases_on_changed_link(self):
        basis = fixture()
        edit = cc.new_annotation(basis, FIC, "reads", "Verify measurement connection", "Check revised input")
        with self.subTest(check="relationship roots"):
            self.assertEqual(edit["roots"], ["NOTE"])
        before = copy.deepcopy(basis)
        basis["corrections"].append(edit)
        edge = next(e for e in basis["relationships"] if e["predicate"] == "reads")
        edge["object"] = OTHER
        edge["id"] = cb.record_id("relation", edge)
        next(s for s in basis["sources"] if s["id"] == "NOTE").update(revision="2", sha256="b" * 64)
        # History is supplied as retained source context, not a replacement claim.
        with self.subTest(check="changed relationship rebase"):
            self.assertEqual(cc.generate(basis, history_bases={cb.digest(before): before})["annotations"][0]["state"], "needs_rebase")

    def test_fabricated_correction_basis_or_lineage_is_refused(self):
        for change in ({"roots": ["NONEXISTENT"]}, {"basis_sha256": "0" * 64}, {"expected_content_fingerprint": None}):
            with self.subTest(change=change):
                basis = fixture()
                edit = cc.new_annotation(basis, PUMP, "manufacturer", "Fabricated", "Supplied proposal")
                edit.update(change)
                edit["id"] = "edit-" + cb.digest({k: v for k, v in edit.items() if k != "id"})[:24]
                basis["corrections"].append(edit)
                with self.assertRaisesRegex(cb.ContextError, "correction|editorial"):
                    cc.generate(basis)

    def test_readable_outline_retains_withdrawn_relationship_evidence(self):
        b = cb.Builder("CF/P1", fixture())
        b.occurrence(FIC, "class", "INST", "CSV record 3; column Type", value="controller")
        basis = b.finish()
        next(s for s in basis["sources"] if s["id"] == "NOTE")["status"] = "withdrawn"
        draft = cc.generate(basis)
        field = draft["components"]["loop_control_narrative_outline"]["items"][FIC]["fields"]["reads"]
        with self.subTest(check="state"):
            self.assertEqual(field["state"], "inactive_evidence")
        with self.subTest(check="readable source"):
            output = cc.render(draft)["control-outline.md"]
            self.assertIn(FT, output)
            self.assertIn("INACTIVE", output)


if __name__ == "__main__":
    unittest.main()
