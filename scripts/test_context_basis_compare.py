"""Whole-basis revision controls, fixed before implementation; not a public transfer."""
import copy
import csv
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import context_basis as cb
import context_components as cc
import context_packet as cp

ROOT = Path(__file__).resolve().parents[1]
A, B = "CMP/P1/U/A", "CMP/P1/U/B"


def basis():
    b = cb.Builder("CMP/P1")
    b.source("S", "1", "a" * 64)
    b.source("T", "1", "b" * 64)
    b.entity(A, "A", "CMP/P1/U")
    b.entity(B, "B", "CMP/P1/U")
    b.occurrence(A, "arbitrary_vendor_fact", "S", "line 1", value="alpha")
    b.occurrence(B, "independent_fact", "T", "line 2", value="unchanged")
    return b.finish()


def compare(before, after):
    return importlib.import_module("context_basis_compare").changes(before, after)


def field(result, predicate="arbitrary_vendor_fact", collection="claims"):
    return next(row for row in result[collection] if row["predicate"] == predicate)


class BasisComparisonTests(unittest.TestCase):
    def test_actual_source_bound_drawing_custom_field_cli_retains_component_comparison(self):
        source = ROOT / "examples/cad-handoff/qualification/validation-2/authored"
        returns = [ROOT / "examples/cad-handoff/qualification/full-ui-22/concurrent-review-1/validation-braces/native-return.dxf",
                   ROOT / "examples/drawing-handoff/native-second-revision/native-returns/validation-braces.dxf"]
        expected_returns = ["25aa6294826284917784d54ed8241a55738a4f4c3c74b4b93ff51d6add6622f2",
                            "8f67fea4ac5aa04a65a6fa13ecbd386d04ca48d935f475cdfa7b3a140ab8ded0"]
        with tempfile.TemporaryDirectory(prefix="basis-drawing-compare-") as temporary:
            folder, packets = Path(temporary), []
            for n, returned in enumerate(returns, 1):
                self.assertEqual(cb.raw_sha(returned.read_bytes()), expected_returns[n - 1])
                records = folder / ("records-" + str(n)); records.mkdir()
                shutil.copyfile(source / "validation-braces.dxf", records / "original.dxf")
                shutil.copyfile(source / "validation-braces.plan.json", records / "requested.plan.json")
                shutil.copyfile(returned, records / "returned.dxf")
                with (records / "source-register.csv").open("w", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, lineterminator="\n")
                    writer.writerow(["File", "DocumentID", "Revision", "Status", "Owner", "Applicability"])
                    writer.writerows([["original.dxf", "ORIGINAL", "0", "supplied", "unknown", "authored development"],
                                      ["requested.plan.json", "REQUEST", "1", "supplied", "unknown", "authored request"],
                                      ["returned.dxf", "RETURN", str(n), "supplied", "unknown", "authored/native return; unaccepted"]])
                prepared = folder / ("interpretation-" + str(n) + ".csv")
                with prepared.open("w", encoding="utf-8", newline="") as output:
                    writer = csv.writer(output, lineterminator="\n")
                    writer.writerow(["Subject", "Predicate", "Source", "Locator", "Quote", "Value", "Type"])
                    writer.writerow(["DRAW/P1/validation-braces/asset-1", "returned_model", "RETURN",
                                     "line " + str(4996 if n == 1 else 4968),
                                     "OTHER-CHOICE" if n == 1 else "Assembly {D}",
                                     "OTHER-CHOICE" if n == 1 else "Assembly {D}", "text"])
                packets.append(cp.prepare(records, folder / ("packet-" + str(n)), "DRAW", "P1",
                                          contribution=prepared, previous=packets[-1] if packets else None))
            before, after = [cp.open_packet(packet) for packet in packets]
            inventories = [cp.inventory(packet) for packet in packets]
            run = subprocess.run([sys.executable, "-B", "-S", str(ROOT / "scripts/context_workflow.py"),
                                  "compare", *map(str, packets)], capture_output=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr.decode("utf-8"))
            result = json.loads(run.stdout)
            changes = result.get("basis_changes", {}).get("claims", [])
            self.assertEqual([(r["subject"], r["predicate"], r["change"]) for r in changes],
                             [("DRAW/P1/validation-braces/asset-1", "returned_model", "content_changed")])
            self.assertEqual(changes[0]["before"]["alternatives"][0]["value"], "OTHER-CHOICE")
            self.assertEqual(changes[0]["after"]["alternatives"][0]["value"], "Assembly {D}")
            del result["basis_changes"]
            self.assertEqual(cb.canonical(result), cb.canonical(cc.changes(before["draft"], after["draft"])))
            self.assertEqual([cp.inventory(packet) for packet in packets], inventories)

    def test_arbitrary_field_changes_leave_independent_subjects_out(self):
        before = basis(); after = copy.deepcopy(before)
        after["claims"][0]["value"] = "beta"
        row = field(compare(before, after))
        self.assertEqual(row["change"], "content_changed")
        self.assertEqual(row["before"]["alternatives"][0]["value"], "alpha")
        self.assertEqual(row["after"]["alternatives"][0]["value"], "beta")
        self.assertEqual(len(compare(before, after)["claims"]), 1)

    def test_exact_typed_values_and_units_do_not_collapse(self):
        for old, new in [(False, 0), (0, 0.0), (None, ""), (1, 1.0), (-0.0, 0.0),
                         ([False, {"x": 0}], [0, {"x": False}]), (9007199254740993, 9007199254740994)]:
            with self.subTest(old=repr(old), new=repr(new)):
                before = basis(); before["claims"][0]["value"] = old
                after = copy.deepcopy(before); after["claims"][0]["value"] = new
                row = field(compare(before, after))
                self.assertEqual(row["change"], "content_changed")
                self.assertEqual(cb.canonical(row["before"]["alternatives"][0]["value"]), cb.canonical(old))
                self.assertEqual(cb.canonical(row["after"]["alternatives"][0]["value"]), cb.canonical(new))
        before = basis(); before["claims"][0]["value"] = 1000; before["claims"][0]["unit"] = "mm"
        after = copy.deepcopy(before); after["claims"][0]["value"] = 1; after["claims"][0]["unit"] = "m"
        self.assertEqual(field(compare(before, after))["change"], "content_changed")

    def test_revision_only_evidence_changes_are_distinct_from_content(self):
        before = basis(); after = copy.deepcopy(before); after["sources"][0]["revision"] = "2"
        result = compare(before, after); row = field(result)
        self.assertEqual(row["change"], "basis_changed")
        self.assertEqual(row["before"]["content_fingerprint"], row["after"]["content_fingerprint"])
        self.assertNotEqual(row["before"]["evidence_fingerprint"], row["after"]["evidence_fingerprint"])
        self.assertEqual([r["id"] for r in result["sources"]], ["S"])
        self.assertEqual(len(result["claims"]), 1)

    def test_swapped_values_of_retained_source_occurrences_are_content_changes(self):
        b = cb.Builder("CMP/P1", basis())
        b.occurrence(A, "arbitrary_vendor_fact", "T", "line 9", value="beta")
        before = b.finish(); after = copy.deepcopy(before)
        after["claims"][0]["value"] = "beta"
        after["claims"][-1]["value"] = "alpha"
        row = field(compare(before, after))
        self.assertEqual(row["change"], "content_changed")
        self.assertEqual({r["value"] for r in row["before"]["alternatives"]},
                         {r["value"] for r in row["after"]["alternatives"]})
        self.assertEqual({r["source"]: r["value"] for r in row["after"]["alternatives"]},
                         {"S": "beta", "T": "alpha"})

    def test_withdrawal_and_rejection_retain_inactive_values_and_show_availability(self):
        for mutate in [lambda b: b["sources"][0].update(status="withdrawn"),
                       lambda b: b["claims"][0]["review"].update(status="rejected")]:
            before = basis(); after = copy.deepcopy(before); mutate(after)
            row = field(compare(before, after))
            self.assertEqual(row["change"], "availability_changed")
            self.assertEqual(row["after"]["state"], "inactive_evidence")
            self.assertEqual(row["after"]["alternatives"][0]["value"], "alpha")
            self.assertFalse(row["after"]["alternatives"][0]["active_source"])

    def test_added_removed_null_claims_keep_unknown_and_subject_unavailable_distinct(self):
        before = basis(); after = copy.deepcopy(before); after["claims"] = after["claims"][1:]
        row = field(compare(before, after))
        self.assertEqual(row["change"], "removed")
        self.assertEqual(row["after"]["state"], "unknown")
        b = cb.Builder("CMP/P1", after); b.occurrence(A, "null_is_explicit", "S", "line 3", value=None)
        row = field(compare(after, b.finish()), "null_is_explicit")
        self.assertEqual(row["change"], "added")
        self.assertEqual(row["before"]["state"], "unknown")
        self.assertIsNone(row["after"]["alternatives"][0]["value"])
        after["entities"] = [r for r in after["entities"] if r["id"] != A]
        row = field(compare(before, after))
        self.assertEqual(row["after"]["state"], "subject_unavailable")
        self.assertTrue(any(r["id"] == A and r["change"] == "removed" for r in compare(before, after)["identities"]))

    def test_relation_direction_target_and_source_availability_are_all_retained(self):
        b = cb.Builder("CMP/P1", basis()); b.occurrence(A, "associated_with", "S", "line 4", target=B, direction="unknown")
        before = b.finish(); after = copy.deepcopy(before); after["relationships"][0]["direction"] = "known"
        row = field(compare(before, after), "associated_with", "relationships")
        self.assertEqual(row["change"], "content_changed")
        self.assertEqual(row["before"]["relationships"][0]["direction"], "unknown")
        self.assertEqual(row["after"]["relationships"][0]["direction"], "known")
        after = copy.deepcopy(before); after["sources"][0]["status"] = "withdrawn"
        row = field(compare(before, after), "associated_with", "relationships")
        self.assertEqual(row["change"], "availability_changed")
        self.assertEqual(row["after"]["state"], "inactive_evidence")
        self.assertEqual(row["after"]["relationships"][0]["object"], B)
        after = copy.deepcopy(before); relation = after["relationships"][0]; relation["object"] = A
        relation["id"] = cb.record_id("relation", relation)
        self.assertEqual(field(compare(before, after), "associated_with", "relationships")["change"], "content_changed")

    def test_relationship_target_swap_uses_unambiguous_source_occurrence_not_target_id(self):
        def represented(swapped):
            b = cb.Builder("CMP/P1", basis())
            c = "CMP/P1/U/C"; b.entity(c, "C", "CMP/P1/U")
            for source, locator, target in [("S", "line 4", c if swapped else B),
                                             ("T", "line 7", B if swapped else c)]:
                b.occurrence(A, "associated_with", source, locator, target=target, direction="known")
            return b.finish()
        before, after = represented(False), represented(True)
        self.assertTrue({r["id"] for r in before["relationships"]}.isdisjoint(
                        {r["id"] for r in after["relationships"]}))
        row = field(compare(before, after), "associated_with", "relationships")
        self.assertEqual(row["change"], "content_changed")
        self.assertEqual({r["source"]: r["object"] for r in row["after"]["relationships"]},
                         {"S": "CMP/P1/U/C", "T": B})

    def test_ambiguous_relationship_occurrences_are_explicit_without_arbitrary_pairing(self):
        def represented(swapped):
            b = cb.Builder("CMP/P1", basis())
            names = [B, "CMP/P1/U/C", "CMP/P1/U/D", "CMP/P1/U/E"]
            for name in names[1:]: b.entity(name, name.rsplit("/", 1)[-1], "CMP/P1/U")
            for source, targets in [("S", names[2:] if swapped else names[:2]),
                                     ("T", names[:2] if swapped else names[2:])]:
                for target in targets:
                    b.occurrence(A, "associated_with", source, "same source line", target=target, direction="unknown")
            return b.finish()
        row = field(compare(represented(False), represented(True)), "associated_with", "relationships")
        self.assertEqual(len(row["before"]["relationships"]), 4)
        self.assertEqual(len(row["after"]["relationships"]), 4)
        ambiguous = row["occurrence_matching"]["ambiguous_anchors"]
        self.assertEqual({r["anchor"]["source"] for r in ambiguous}, {"S", "T"})
        self.assertTrue(all(len(r["before_occurrence_ids"]) == len(r["after_occurrence_ids"]) == 2
                            for r in ambiguous))
        self.assertEqual(row["change"], "basis_changed")

    def test_relationship_role_change_retains_both_declarations(self):
        b = cb.Builder("CMP/P1", basis())
        b.occurrence(A, "associated_with", "S", "line 4", target=B, direction="known")
        before = b.finish(); after = copy.deepcopy(before)
        relation = after["relationships"][0]; relation["role"] = "supplied_interpretation"
        relation["id"] = cb.record_id("relation", relation)
        row = field(compare(before, after), "associated_with", "relationships")
        self.assertEqual(row["change"], "basis_changed")
        self.assertEqual(row["before"]["relationships"][0]["role"], "source_statement")
        self.assertEqual(row["after"]["relationships"][0]["role"], "supplied_interpretation")

    def test_intermediate_source_lineage_withdrawal_is_visible_without_minting_truth(self):
        b = cb.Builder("CMP/P1", basis()); b.source("D", "1", "c" * 64, status="derived", roots=["S"])
        b.occurrence(A, "copied_fact", "D", "line 5", value="declared derivative")
        before = b.finish(); after = copy.deepcopy(before); after["sources"][0]["status"] = "withdrawn"
        row = field(compare(before, after), "copied_fact")
        self.assertEqual(row["change"], "availability_changed")
        self.assertFalse(row["after"]["alternatives"][0]["active_source"])
        self.assertEqual({r["id"] for r in compare(before, after)["sources"]}, {"S", "D"})

    def test_identity_boundary_and_unused_source_metadata_changes_are_not_lost(self):
        before = basis(); before["boundaries"].append({"id": "outside", "reason": "not supplied"})
        after = copy.deepcopy(before); after["entities"][0]["aliases"] = ["alias"]
        after["boundaries"][0]["reason"] = "new boundary declaration"
        after["sources"].append({**after["sources"][1], "id": "UNUSED", "roots": ["UNUSED"]})
        result = compare(before, after)
        self.assertEqual({(r["kind"], r["id"]) for r in result["identities"]}, {("entity", A), ("boundary", "outside")})
        self.assertTrue(any(r["id"] == "UNUSED" and r["change"] == "added" for r in result["sources"]))
        self.assertEqual(result["claims"], [])

    def test_corrections_and_other_retained_metadata_never_become_source_claims(self):
        before = basis(); after = copy.deepcopy(before)
        after["corrections"].append(cc.new_annotation(before, A, "arbitrary_vendor_fact", "proposal", "Need original evidence"))
        after["omissions"].append({"source": "S", "reason": "not interpreted"})
        before["extension"] = False; after["extension"] = 0
        result = compare(before, after)
        self.assertEqual({r["field"] for r in result["metadata"]}, {"corrections", "omissions", "extension"})
        self.assertEqual(result["claims"], [])

    def test_deterministic_no_mutation_and_namespace_refusal(self):
        before = basis(); frozen = cb.canonical(before)
        result = compare(before, before)
        self.assertTrue(all(not result[name] for name in ["claims", "relationships", "identities", "sources", "metadata"]))
        self.assertEqual(cb.canonical(result), cb.canonical(compare(before, before)))
        self.assertEqual(cb.canonical(before), frozen)
        with self.assertRaisesRegex(cb.ContextError, "same.*namespace"):
            compare(before, cb.empty("OTHER/P1"))


if __name__ == "__main__":
    unittest.main()
