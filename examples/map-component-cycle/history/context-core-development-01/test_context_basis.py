"""Source-keyed core checks. Fixtures/key predate this implementation; no product acceptance."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

import context_basis as cb

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "examples/map-component-cycle/inputs"
KEY = json.loads((INPUTS / "EXPECTED.json").read_bytes())
PUMP, OTHER, TANK, FT, FIC, FV = KEY["subjects"]


def rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fixture(revision=1):
    folder = INPUTS / "development" / ("rev" + str(revision))
    builder = cb.Builder("CF/P1")
    for source in rows(folder / "source-register.csv"):
        builder.source(source["DocumentID"], source["Revision"],
                       cb.raw_sha((folder / source["File"]).read_bytes()),
                       owner=source["Owner"], status=source["Status"],
                       applicability=source["Applicability"], path=source["File"])
    for identifier in KEY["subjects"]:
        builder.entity(identifier, identifier.rsplit("/", 1)[1], identifier.rsplit("/", 1)[0])
    for number, row in enumerate(rows(folder / "equipment.csv"), 2):
        subject = cb.qualified("CF", "P1", row["Area"], row["Equipment"])
        for field, column, unit in (("class", "Class", None), ("serial_number", "Serial", None),
                                    ("rated_flow", "RatedFlow", row["FlowUnit"] or None)):
            if row[column]:
                builder.occurrence(subject, field, "EQ", f"CSV record {number}; column {column}",
                                   value=row[column], unit=unit, role="equipment_export")
    for number, row in enumerate(rows(folder / "datasheet.csv"), 2):
        subject = cb.qualified("CF", "P1", row["Area"], row["Tag"])
        builder.occurrence(subject, "rated_flow", "DS", f"CSV record {number}; column RatedFlow",
                           value=row["RatedFlow"], unit=row["FlowUnit"], role="datasheet")
    builder.occurrence(FIC, "reads", "NOTE", "line 4", target=FT, direction="known")
    builder.occurrence(FIC, "commands", "NOTE", "line 4", target=FV, direction="known")
    return builder.finish()


class ContextBasisTests(unittest.TestCase):
    def test_original_scoped_identity_and_ambiguity(self):
        view = cb.View(fixture())
        self.assertEqual(view.resolve(PUMP), PUMP)
        with self.assertRaisesRegex(cb.ContextError, "ambiguous item; choose qualified id"):
            view.resolve("P-101")
        self.assertEqual(view.field(OTHER, "serial_number")["alternatives"][0]["value"], "OTHER-101")

    def test_same_source_occurrence_refuses_changed_value(self):
        b = cb.Builder("X")
        b.source("S", "1", "a" * 64)
        b.entity("X/U/P", "P", "X/U")
        b.occurrence("X/U/P", "flow", "S", "row 1", value=0)
        with self.assertRaisesRegex(cb.ContextError, "source occurrence has conflicting values"):
            b.occurrence("X/U/P", "flow", "S", "row 1", value=False)

    def test_literal_flow_alternatives_from_frozen_key(self):
        view = cb.View(fixture())
        flow = view.field(PUMP, "rated_flow")
        self.assertEqual(flow["state"], "disputed")
        self.assertEqual(sorted(c["value"] for c in flow["alternatives"]),
                         KEY["revisions"][0]["flow_alternatives"])
        self.assertTrue(all(c["source_record"]["sha256"] for c in flow["alternatives"]))
        self.assertEqual(view.field(FV, "fail_position")["state"], "unknown")

    def test_withdrawn_evidence_is_retained_without_being_current(self):
        view = cb.View(fixture(3))
        flow = view.field(PUMP, "rated_flow")
        self.assertEqual(flow["state"], "sourced_unreviewed")
        active = [r["value"] for r in flow["alternatives"] if r["active_source"]]
        self.assertEqual(active, KEY["revisions"][2]["flow_alternatives_current"])
        withdrawn = [r for r in flow["alternatives"] if not r["active_source"]]
        self.assertEqual(withdrawn[0]["value"], KEY["revisions"][2]["withdrawn_alternative"])
        self.assertEqual(withdrawn[0]["source_record"]["status"], "withdrawn")

    def test_original_typed_json_is_not_coerced(self):
        original = json.loads((INPUTS / "development/typed-source.json").read_bytes())
        b = cb.Builder("CF/P1", fixture())
        b.source("TYPED", "1", cb.raw_sha((INPUTS / "development/typed-source.json").read_bytes()))
        for n, value in enumerate(original["values"]):
            b.occurrence(PUMP, "value_" + str(n), "TYPED", "/values/" + str(n), value=value)
        v = cb.View(b.finish())
        for n, value in enumerate(KEY["typed_controls"]):
            observed = v.field(PUMP, "value_" + str(n))["alternatives"][0]["value"]
            self.assertEqual(cb.canonical(observed), cb.canonical(value))
            self.assertIs(type(observed), type(value))
        self.assertNotEqual(cb.canonical(False), cb.canonical(0))
        self.assertNotEqual(cb.canonical(1), cb.canonical(1.0))
        self.assertNotEqual(cb.canonical(0.0), cb.canonical(-0.0))

    def test_declared_quantities_compare_without_losing_originals(self):
        b = cb.Builder("Q")
        for source in ("A", "B"):
            b.source(source, "1", ("a" if source == "A" else "b") * 64)
        b.entity("Q/U/P", "P", "Q/U")
        b.occurrence("Q/U/P", "flow", "A", "row 1", value="45", unit="m3/h")
        b.occurrence("Q/U/P", "flow", "B", "row 1", value="12.5", unit="L/s")
        field = cb.View(b.finish()).field("Q/U/P", "flow")
        self.assertEqual(field["state"], "sourced_unreviewed")
        self.assertCountEqual([(r["value"], r["unit"]) for r in field["alternatives"]],
                         [("45", "m3/h"), ("12.5", "L/s")])
        b.occurrence("Q/U/P", "flow", "B", "row 2", value="45", unit="bar")
        self.assertEqual(cb.View(b.finish()).field("Q/U/P", "flow")["state"], "disputed")

    def test_false_zero_unqualified_numbers_are_different_claims(self):
        b = cb.Builder("Q")
        b.source("S", "1", "a" * 64)
        b.entity("Q/U/P", "P", "Q/U")
        for n, value in enumerate((False, 0, 1, 1.0)):
            b.occurrence("Q/U/P", "state", "S", "row " + str(n), value=value)
        self.assertEqual(cb.View(b.finish()).field("Q/U/P", "state")["state"], "disputed")

    def test_generated_copy_reuses_roots_and_cannot_create_self_root(self):
        basis = fixture()
        b = cb.Builder("CF/P1", basis)
        b.source("COPY", "1", "b" * 64, status="derived", roots=["NOTE"])
        b.occurrence(FIC, "reads", "COPY", "/derived/control", target=FT)
        v = cb.View(b.finish())
        self.assertEqual([r["roots"] for r in v.inspect(FIC)["relationships"]
                          if r["predicate"] == "reads"], [["NOTE"], ["NOTE"]])
        bad = copy.deepcopy(b.basis)
        next(s for s in bad["sources"] if s["id"] == "COPY")["roots"] = ["COPY"]
        with self.assertRaisesRegex(cb.ContextError, "derived source cannot declare itself independent"):
            cb.validate(bad)

    def test_lineage_cycle_and_fabricated_claim_roots_refuse(self):
        basis = fixture()
        basis["claims"][0]["roots"] = ["NOTE"]
        with self.assertRaisesRegex(cb.ContextError, "lineage disagrees"):
            cb.validate(basis)
        b = cb.Builder("X")
        b.source("A", "1", "a" * 64, roots=["B"])
        b.source("B", "1", "b" * 64, roots=["A"])
        with self.assertRaisesRegex(cb.ContextError, "source lineage cycle"):
            b.finish()

    def test_revision_content_and_evidence_impact_are_distinct(self):
        first, second = cb.View(fixture()), cb.View(fixture(2))
        self.assertNotEqual(first.field(PUMP, "rated_flow")["content_fingerprint"],
                            second.field(PUMP, "rated_flow")["content_fingerprint"])
        self.assertEqual(first.field(PUMP, "serial_number"), second.field(PUMP, "serial_number"))
        revision_only = fixture()
        next(s for s in revision_only["sources"] if s["id"] == "EQ")["revision"] = "new-label"
        changed = cb.View(revision_only)
        self.assertEqual(first.field(PUMP, "serial_number")["content_fingerprint"],
                         changed.field(PUMP, "serial_number")["content_fingerprint"])
        self.assertNotEqual(first.field(PUMP, "serial_number")["evidence_fingerprint"],
                            changed.field(PUMP, "serial_number")["evidence_fingerprint"])

    def test_declared_signals_are_not_physical_routes(self):
        v = cb.View(fixture())
        self.assertEqual(v.traverse(FIC, "commands")["nodes"], sorted([FIC, FV]))
        self.assertEqual(v.traverse(FIC, "piped_to")["nodes"], [FIC])
        self.assertEqual(v.traverse(FIC, "network_member")["nodes"], [FIC])
        self.assertEqual(v.traverse(FIC, "commands", limit=1)["truncated"], True)

    def test_source_change_or_rejection_does_not_erase_history(self):
        basis = fixture()
        before = len(basis["claims"])
        basis["claims"][0]["review"] = {"status": "rejected", "by": "declared fixture reviewer"}
        v = cb.View(basis)
        self.assertFalse(v.active(basis["claims"][0]))
        self.assertEqual(len(v.basis["claims"]), before)
        self.assertEqual(v.inspect(PUMP)["entity"]["identity_role"], "functional_position")

    def test_relevant_correction_is_retrievable_from_same_basis(self):
        basis = fixture()
        basis["corrections"].append(dict(KEY["manual_edit_control"], id="C1", version="1",
                                        source="NOTE", rationale="Fixture editorial correction"))
        found = cb.View(basis).inspect(PUMP)["corrections"]
        self.assertEqual(found[0]["value"], KEY["manual_edit_control"]["value"])
        self.assertFalse(cb.View(basis).inspect(OTHER)["corrections"])

    def test_input_bounds_duplicate_keys_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "test.json"
            p.write_text('{"x":false,"x":0}', encoding="utf-8")
            with self.assertRaisesRegex(cb.ContextError, "duplicate JSON key"):
                cb.read_json(p)
            p.write_text('{"x":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(cb.ContextError, "non-finite JSON constant"):
                cb.read_json(p)
            p.write_text('{"x":0}', encoding="utf-8")
            with self.assertRaisesRegex(cb.ContextError, "exceeds declared byte limit"):
                cb.read_json(p, limit=2)
        with self.assertRaisesRegex(cb.ContextError, "non-finite JSON number"):
            cb.json_value(float("nan"))

    def chain(self, middle="derived"):
        b = cb.Builder("X")
        b.source("A", "1", "a" * 64)
        b.source("B", "1", "b" * 64, status=middle, roots=["A"])
        b.source("C", "1", "c" * 64, status="derived", roots=["B"])
        b.entity("X/U/P", "P", "X/U")
        b.occurrence("X/U/P", "description", "C", "line 1", value="Copied description")
        return b.finish()

    def test_withdrawn_intermediate_source_invalidates_derivation(self):
        view = cb.View(self.chain("withdrawn"))
        self.assertFalse(view.field("X/U/P", "description")["alternatives"][0]["active_source"])

    def test_root_source_revision_changes_derived_evidence_basis(self):
        basis = self.chain()
        before = cb.View(copy.deepcopy(basis)).field("X/U/P", "description")
        basis["sources"][0].update(revision="2", sha256="d" * 64)
        after = cb.View(basis).field("X/U/P", "description")
        self.assertEqual(before["content_fingerprint"], after["content_fingerprint"])
        self.assertNotEqual(before["evidence_fingerprint"], after["evidence_fingerprint"])

    def test_declared_namespace_cannot_hide_foreign_entity(self):
        builder = cb.Builder("CUSTOMER/A")
        builder.entity("OTHER/B/U/P", "P", "OTHER/B/U")
        with self.assertRaisesRegex(cb.ContextError, "outside.*namespace"):
            builder.finish()


if __name__ == "__main__":
    unittest.main()

