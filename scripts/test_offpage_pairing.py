"""Tests for scripts/offpage_pairing.py, the one cross-sheet off-page pairing rule, and its two callers.

The OPEN100 control scores the rule against a key taken from the drawings' own printed references (PID2Graph's
answer keys hold no cross-sheet links); the key and how it was read are in examples/own-drawing/offpage-key.json."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import offpage_pairing as op  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KEY = ROOT / "examples/own-drawing/offpage-key.json"


def c(cid, sheet, text):
    return {"id": cid, "sheet": sheet, "text": text}


class Rule(unittest.TestCase):
    def test_numbers_match_literally_with_any_separator_and_leading_zeros_but_not_inside_longer_numbers(self):
        pattern = op.number_pattern("P-204")
        for text in ("REF SHT P-204", "P 204", "SEE P204.", "(P-204)", "P\N{EN DASH}204", "P�204"):
            self.assertTrue(pattern.search(text.upper()), text)
        for text in ("P-2045", "XP-204", "P-20", "P-2041"):
            self.assertFalse(pattern.search(text.upper()), text)
        self.assertTrue(op.number_pattern("120-1").search("RHRS PID-120-01"))
        self.assertFalse(op.number_pattern("120-1").search("PID 120-12"))

    def test_a_bare_numeric_number_needs_a_drawing_word(self):
        pattern = op.number_pattern("180")
        self.assertTrue(pattern.search("ES PID 180-1"))
        self.assertTrue(pattern.search("SEE DWG 180"))
        self.assertFalse(pattern.search("TE 180 HIGH"))
        self.assertFalse(pattern.search("PID 1801-1"))

    def test_reciprocal_references_pair_and_record_method_and_evidence(self):
        sheets = {"A": {"number": "P-101"}, "B": {"number": "P-102"}}
        out = op.pair([c("x", "A", "TO REACTOR P-102"), c("y", "B", "FROM FEED P-101"), c("z", "B", "VENT")], sheets)
        self.assertEqual(len(out["pairs"]), 1)
        p = out["pairs"][0]
        self.assertEqual((p["a"], p["b"], p["method"], p["alternatives"]), ("x", "y", "reciprocal_supplied_numbers", 0))
        self.assertEqual(p["evidence"]["chosen_by"], "only candidate")
        self.assertEqual(out["status"]["z"], "unpaired: names no sheet of this set")

    def test_one_way_needs_the_title_or_a_matching_system_code(self):
        sheets = {"A": {"number": "P-101", "title": "Crude Feed Header"}, "B": {"number": "P-102"}}
        out = op.pair([c("x", "A", "TO P-102"), c("y", "B", "FROM CRUDE FEED HEADER")], sheets)
        self.assertEqual([p["method"] for p in out["pairs"]], ["one_way_number_plus_sheet_title"])
        out = op.pair([c("x", "A", "TO P-102"), c("y", "B", "FROM CRUDE FEED")], sheets)
        self.assertEqual(out["pairs"], [])
        self.assertEqual(out["status"]["x"],
                         "unpaired: target sheet is in this set but no matching connector was found")
        sheets = {"A": {"system_code": "CWS"}, "B": {"number": "P-102"}}
        out = op.pair([c("x", "A", "TO P-102"), c("y", "B", "CWS PID 900-1 RETURN")], sheets)
        self.assertEqual([p["method"] for p in out["pairs"]], ["one_way_number_plus_system_code"])

    def test_a_tie_is_never_decided_by_input_order(self):
        sheets = {"A": {"number": "P-101"}, "B": {"number": "P-102"}}
        out = op.pair([c("x", "A", "P-102 DRAIN"), c("y1", "B", "P-101 VENT"), c("y2", "B", "P-101 SAMPLE")], sheets)
        self.assertEqual(out["pairs"], [])
        self.assertTrue(out["status"]["x"].startswith("unpaired: tied with equally likely candidates (y1, y2)"))
        self.assertEqual(out["candidates"]["x"], ["y1", "y2"])
        # two identical connectors on each side: nobody pairs, not even the last two left over
        twins = [c("x1", "A", "P-102 DRAIN"), c("x2", "A", "P-102 DRAIN"), c("y1", "B", "P-101 DRAIN"),
                 c("y2", "B", "P-101 DRAIN")]
        self.assertEqual(op.pair(twins, sheets)["pairs"], [])
        out = op.pair([c("x", "A", "P-102 DRAIN"), c("y1", "B", "P-101 VENT"), c("y2", "B", "P-101 DRAIN")], sheets)
        p = out["pairs"][0]
        self.assertEqual((p["b"], p["alternatives"], p["evidence"]["chosen_by"]),
                         ("y2", 1, "highest description similarity"))
        self.assertEqual(out["status"]["y1"], "unpaired: its candidates paired elsewhere or wait on a tie")

    def test_naming_two_sheets_never_pairs(self):
        sheets = {"A": {"number": "P-101"}, "B": {"number": "P-102"}, "C": {"number": "P-103"}}
        out = op.pair([c("x", "A", "P-102 / P-103"), c("y", "B", "P-101")], sheets)
        self.assertEqual(out["pairs"], [])
        self.assertEqual(out["status"]["x"], "unpaired: names more than one sheet in this set")


class Open100(unittest.TestCase):
    """The committed measurement: the rule and both callers on the recorded reader's OPEN100 sheets 0-5, scored on
    the printed-reference key."""

    def setUp(self):
        self.key = json.loads(KEY.read_text(encoding="utf-8"))
        self.manifest = json.loads((ROOT / self.key["set_manifest"]).read_text(encoding="utf-8"))
        self.accept = {frozenset(p["accept"]): p["continuation"] for p in self.key["acceptable_pairs"]}

    def test_import_drawing_set_adds_the_continuation_the_first_pass_misses(self):
        import import_drawing_set as dset
        with tempfile.TemporaryDirectory() as tmp:
            result = dset.import_set(ROOT / self.key["set_manifest"], Path(tmp) / "bundle", line_layers=False)
            model = json.loads((Path(tmp) / "bundle/plant_model.json").read_text(encoding="utf-8"))
        where = {c["id"]: f"{c['provenance'][0]['sheet']}/{c['provenance'][0]['symbol']}"
                 for c in model["offpage_connectors"]}
        found = {self.accept.get(frozenset((where[p["a"]], where[p["b"]]))): p["method"]
                 for p in model["offpage_pairs"]}
        self.assertEqual(result["pairs_from_supplied_numbers"], 1)
        self.assertEqual(found["G1"], "reciprocal_supplied_numbers")
        self.assertNotIn(None, found)
        recorded = self.key["measured"]["import_drawing_set_after_change"]
        self.assertEqual((len(model["offpage_pairs"]), sorted(found)),
                         (recorded["pairs"], ["G1", "G3", "G4", "G5", "G6"]))

    def test_one_map_pairs_only_what_the_rule_decides_and_names_the_ties(self):
        import one_map as om

        class Map:
            def __init__(self):
                self.nodes, self.edges, self.review = {}, [], []

            def edge(self, e):
                self.edges.append(e)
        m, by_ref = Map(), {}
        for i, sheet in enumerate(self.manifest["sheets"]):
            read = om.sheet_from_prediction(ROOT / "examples/own-drawing" / sheet["extraction"],
                                            sheet=sheet["drawing_number"], revision="public", plant="P1")
            for o in read["offpage"]:
                node = f"{i}/{o['id']}"
                m.nodes[node] = {"source": {"kind": "test"}}
                by_ref[("P1", sheet["drawing_number"], o["id"])] = {
                    "id": o["id"], "name": o.get("name"), "to": {}, "attrs": o.get("attributes") or {}, "node": node,
                    "owner": "Doc control", "plant": "P1", "sheet": sheet["drawing_number"]}
        om.pair_by_reference(m, by_ref)
        self.assertEqual(sorted(self.accept[frozenset((e["from"], e["to"]))] for e in m.edges), ["G1", "G3"])
        unclear = {r["item"] for r in m.review if r["kind"] == "off-page pairing unclear"}
        self.assertLessEqual({"1/s17", "1/s39", "2/s4", "1/s37", "2/s1", "2/s107", "4/s1", "4/s12"}, unclear)

    def test_rule_scores_on_the_printed_reference_key(self):
        key, manifest = self.key, self.manifest
        connectors, sheets = [], {}
        for i, sheet in enumerate(manifest["sheets"]):
            sheets[str(i)] = {"number": sheet["drawing_number"], "title": sheet["title"],
                              "system_code": sheet["system_code"]}
            record = json.loads((ROOT / "examples/own-drawing" / sheet["extraction"]).read_text(encoding="utf-8"))
            connectors += [c(f"{i}/{s['id']}", str(i), s.get("tag") or "") for s in record["prediction"]["symbols"]
                           if s["class"] == "inlet/outlet"]
        accept = {frozenset(p["accept"]): p["continuation"] for p in key["acceptable_pairs"]}
        pairs = op.pair(connectors, sheets)["pairs"]
        found = [accept.get(frozenset((p["a"], p["b"]))) for p in pairs]
        self.assertNotIn(None, found, "a pair the printed key does not accept")
        self.assertEqual(sorted(set(found)), ["G1", "G3"])
        recorded = key["measured"]["offpage_pairing"]
        self.assertEqual((len(pairs), len(set(found)), sorted({a["continuation"] for a in key["acceptable_pairs"]}
                                                              - set(found))),
                         (recorded["pairs"], recorded["continuations_found"], recorded["missed"]))


if __name__ == "__main__":
    unittest.main()
