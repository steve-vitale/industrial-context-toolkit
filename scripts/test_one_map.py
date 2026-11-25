"""Tests for scripts/one_map.py: the two-plant fictional example (both starts), identity, shared utilities, loops,
mentions, based_on reopen, conflicts and routing, owner-split queues, incremental batch and backward compatibility.
Stdlib only.

Usage:  python -m unittest scripts/test_one_map.py      (or python scripts/test_one_map.py)
"""
import contextlib
import csv
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_export as gx  # noqa: E402
import loop_audit  # noqa: E402
import one_map as om  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples" / "one-map"
EXPECTED = EX / "expected"


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def read_rows(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding="utf-8"))))


class OneMapExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.g, cls.run_info, cls.rows, _ = om.build(EX / "inputs" / "site.json", cls.dir / "start")
        cls.nodes = {n["id"]: n for n in cls.g["nodes"]}
        cls.edges = cls.g["edges"]
        cls.conf = [n["conflict"] for n in cls.g["nodes"] if n["kind"] == "conflict"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def conflicts(self, ctype):
        return [c for c in self.conf if c["type"] == ctype]

    def test_expected_outputs_regenerate_byte_for_byte(self):
        quiet(om.build, EX / "inputs" / "site-after-review.json", self.dir / "after-review")
        quiet(om.draft_lists, EX / "inputs" / "site.json", self.dir / "drafts")
        text, _ = om.loops_from_graph(ROOT / "examples" / "graph-export" / "sheet0_graph.json")
        (self.dir / "open100-sheet0-loops.md").write_text(text, encoding="utf-8", newline="\n")
        for exp in sorted(p for p in EXPECTED.rglob("*") if p.is_file() and "office" not in p.parts
                         and "pasteurizer" not in p.parts and "pasteurizer-moc" not in p.parts):
            # test_ontology.py regenerates the pasteurizer, test_plant_workflows.py its MOC walk-through
            rel = exp.relative_to(EXPECTED)
            got = self.dir / rel
            self.assertTrue(got.exists(), rel)
            self.assertEqual(got.read_bytes().replace(b"\r\n", b"\n"), exp.read_bytes().replace(b"\r\n", b"\n"), rel)

    def test_graph_checks_with_both_checkers(self):
        self.assertEqual(om.problems(self.g), [])
        self.assertEqual(self.g["schema"], "twin-graph-2")
        # graph_export.py is unchanged: it keeps refusing a schema it does not know
        self.assertEqual(gx.problems(self.g)[0], "schema is 'twin-graph-2', not twin-graph-1")
        bad = json.loads(json.dumps(self.g))
        bad["edges"].append(dict(bad["edges"][0], id="dangling", to="S1/NOWHERE"))
        self.assertTrue(any("is not a node" in p for p in om.problems(bad)))

    def test_identity_namespace_and_aliases(self):
        self.assertIn("S1/P1/200/P-101", self.nodes)
        self.assertIn("S1/P2/300/P-101", self.nodes)  # same legacy tag, two plants, never renumbered
        self.assertEqual(self.nodes["S1/P1/200/P-101"]["tag"], "P-101")
        self.assertIn("FP-01", self.nodes["S1/P1/200/P-101"]["aliases"])
        for nid in self.nodes:
            self.assertTrue(nid == "S1" or nid.startswith("S1/"), nid)
        kinds = {self.nodes[x]["kind"] for x in ("S1", "S1/P1", "S1/P1/200", "S1/UTIL")}
        self.assertEqual(kinds, {"site", "plant", "unit", "scope"})

    def test_shared_utility_has_one_owner_and_is_referenced_across_boundaries(self):
        parents = [e["from"] for e in self.edges if e["type"] == "contains" and e["to"] == "S1/UTIL/CW"]
        self.assertEqual(parents, ["S1/UTIL"])
        refs = {(e["from"], e["to"]) for e in self.edges if e["type"] == "references"}
        self.assertIn(("S1/P1/BND-CW", "S1/UTIL/CW"), refs)
        self.assertIn(("S1/P2/BND-CW", "S1/UTIL/CW"), refs)
        claim = [c for c in self.conflicts("boundary") if c["attribute"] == "owner_scope"]
        self.assertEqual(len(claim), 1)
        self.assertEqual(claim[0]["record_owner"], "Site utilities")
        # a graph that gives the system a second owner is refused by the check
        g = json.loads(json.dumps(self.g))
        g["edges"].append({"id": "x", "type": "contains", "from": "S1/P2", "to": "S1/UTIL/CW", "status": "unverified",
                           "source": {"kind": "document"}})
        self.assertTrue(any("exactly one owning scope" in p for p in om.problems(g)))

    def test_listed_loop_imported_located_and_consistent(self):
        e = {(x["type"], x["from"], x["to"]): x for x in self.edges}
        a = e[("controls", "S1/P1/200/FT-2203", "S1/P1/200/FIC-2203")]
        self.assertEqual(a["source"]["document"], "DCS-LOOPS-200")
        self.assertEqual(a["how_found"], ["loop_list", "drawing:signal_line"])
        loops = {lp["controller"]: lp for lp in self.g["loops"]}
        self.assertEqual(loops["FIC-2203"]["outcome"], "located and consistent")
        self.assertEqual(loops["FIC-2203"]["zones"], ["200-01:C1", "200-01:C2"])

    def test_listed_loop_not_found_and_partly_located_are_routed(self):
        loops = {lp["controller"]: lp for lp in self.g["loops"]}
        self.assertEqual(loops["LIC-2204"]["outcome"], "not found on any sheet")
        self.assertEqual(loops["LIC-2204"]["route"], "Doc control")  # every tag is held by a list: drawings lack them
        self.assertEqual(loops["PIC-2210"]["outcome"], "partly located")
        self.assertEqual(loops["PIC-2210"]["route"], "I&C")  # PV-2211 is held by no list
        pairing = self.conflicts("loop_pairing")
        self.assertEqual([(c["subject"], c["record_owner"]) for c in pairing], [("S1/P1/200/PIC-2210", "I&C")])

    def test_drawing_only_loop_is_flagged_not_asserted(self):
        flagged = self.conflicts("unlisted_loop")
        self.assertEqual([(c["subject"], c["record_owner"]) for c in flagged], [("S1/P1/200/TIC-2205", "I&C")])
        self.assertFalse([x for x in self.edges if x["type"] == "controls" and "TIC-2205" in x["from"] + x["to"]])
        self.assertFalse([x for x in self.edges if x["type"] == "controls" and "FIC-3101" in x["from"] + x["to"]])

    def test_list_drawing_mismatches_both_directions(self):
        presence = {(c["subject"], c["attribute"], c["record_owner"]) for c in self.conflicts("asset_presence")}
        self.assertIn(("S1/P1/200/P-103", "drawn", "Doc control"), presence)    # listed, on no sheet
        self.assertIn(("S1/P1/200/P-102", "listed", "Maintenance"), presence)   # drawn, in no list
        self.assertIn(("S1/P1/200/PV-2210", "listed", "Maintenance"), presence)

    def test_values_follow_the_authority_map_and_pid_values_are_reference(self):
        # rated flow: the datasheet (authoritative for ratings) against the maintenance equipment export, routed to
        # the export's owner; the P&ID prints the datasheet's 45 m3/h and raises nothing
        value = self.conflicts("value_disagreement")
        self.assertEqual([(c["subject"], c["attribute"], c["source_a"]["source"]["document"], c["source_a"]["says"],
                           c["source_b"]["source"]["document"], c["source_b"]["says"], c["record_owner"])
                          for c in value],
                         [("S1/P1/200/P-101", "rated_flow", "EQUIPMENT-DATASHEETS", "45 m3/h", "CMMS-EQUIPMENT",
                           "40 m3/h", "Maintenance")])
        rated = [a for a in self.nodes["S1/P1/200/P-101"]["attributes"] if a["name"] == "rated_flow"]
        self.assertEqual([(a["value"], a["source"]["document"]) for a in rated], [("45 m3/h", "EQUIPMENT-DATASHEETS")])
        # a P&ID value that differs from the datasheet is a low-priority note to the P&ID owner, never a conflict
        notes = [r for r in self.rows if r["kind"] == om.PID_NOTE]
        self.assertEqual([(r["item"], r["tier"], r["owner"]) for r in notes],
                         [("S1/P1/200/V-204", "amber", "Doc control")])
        self.assertIn("12 barg printed on sheet 200-01, 10 barg in the datasheet", notes[0]["why"])
        amber = [r["kind"] for r in self.rows if r["tier"] == "amber"]
        self.assertEqual(amber[-1], om.PID_NOTE)  # notes sort after every other amber row
        self.assertFalse([c for c in self.conf if c["subject"] == "S1/P1/200/V-204"])

    def test_authority_defaults_overrides_and_refusals(self):
        self.assertEqual(om.default_fact_kind("rated_flow"), "rating")
        self.assertEqual(om.default_fact_kind("line_size"), "size")
        self.assertEqual(om.default_fact_kind("body_material"), "material")
        self.assertEqual(om.default_fact_kind("calibrated_range"), "instrument_range")
        self.assertIsNone(om.default_fact_kind("colour"))
        tmp = Path(self.tmp.name) / "authority"
        shutil.copytree(EX / "inputs", tmp)
        site = json.loads((tmp / "site.json").read_text(encoding="utf-8"))
        site["authority"] = {"rating": "maintenance_export"}  # this site trusts its maintenance records for ratings
        (tmp / "site.json").write_text(json.dumps(site), encoding="utf-8")
        g, _, _, _ = quiet(om.build, tmp / "site.json", tmp / "out")
        c = [n["conflict"] for n in g["nodes"] if n["kind"] == "conflict" and n["conflict"]["type"] == "value_disagreement"]
        self.assertEqual([(x["source_a"]["says"], x["record_owner"]) for x in c], [("40 m3/h", "Process")])
        site["authority"] = {"rating": "spreadsheet"}
        (tmp / "site.json").write_text(json.dumps(site), encoding="utf-8")
        with self.assertRaisesRegex(om.InputError, "not a record type"):
            om.load_site(tmp / "site.json")
        site["authority"], site["fact_kinds"] = {}, {"rated_flow": "colour"}
        (tmp / "site.json").write_text(json.dumps(site), encoding="utf-8")
        with self.assertRaisesRegex(om.InputError, "not a fact kind"):
            om.load_site(tmp / "site.json")

    def test_datasheet_for_an_item_nobody_holds_is_a_review_item(self):
        tmp = Path(self.tmp.name) / "orphan-datasheet"
        shutil.copytree(EX / "inputs", tmp)
        ds = tmp / "lists" / "equipment_datasheets.csv"
        ds.write_text(ds.read_text(encoding="utf-8") + "P-999,P1,200,Unknown pump datasheet,10 m3/h,\n",
                      encoding="utf-8")
        _, _, rows, _ = quiet(om.build, tmp / "site.json", tmp / "out")
        hit = [r for r in rows if r["item"] == "S1/P1/200/P-999"]
        self.assertEqual([(r["kind"], r["owner"], r["tier"]) for r in hit],
                         [("datasheet without an item", "Process", "amber")])

    def test_matches_go_to_spot_check_not_full_review(self):
        green = [r for r in self.rows if r["tier"] == "green"]
        self.assertIn("S1/P1/200/V-204", {r["item"] for r in green})
        self.assertTrue(any(r["spot_check"] == "sample" for r in green))
        self.assertFalse(any(r["spot_check"] for r in self.rows if r["tier"] != "green"))

    def test_mentions_assert_only_unambiguous_matches(self):
        m = {(e["from"], e["to"]): {c["name"]: c["value"] for c in e["attributes"]}
             for e in self.edges if e["type"] == "mentions"}
        self.assertEqual(m[("S1/DOC/DB-P101", "S1/P1/200/P-101")]["confidence"], "exact in covered scope")
        self.assertEqual(m[("S1/DOC/CK-300-01", "S1/P2/300/P-101")]["confidence"], "exact in covered scope")
        self.assertEqual(m[("S1/DOC/CW-N-01", "S1/P2/300/P-101")]["confidence"], "site-qualified exact")
        self.assertNotIn(("S1/DOC/CW-N-01", "S1/P1/200/P-101"), m)  # ambiguous: not asserted
        self.assertEqual([c["record_owner"] for c in self.conflicts("ambiguous_reference")], ["Site utilities"])
        for key in m.values():
            self.assertTrue({"file", "locator", "matched_text", "confidence"} <= set(key))
        whys = " ".join(r["why"] for r in self.rows if r["kind"] == om.CONFIRM)
        for near in ("'P101'", "'P-101A'"):  # P101: Unit 200 and Unit 300 both have P-101; P-101A: suffix nowhere
            self.assertIn(near, whys)
        psv = m[("S1/DOC/OP-200-07", "S1/P1/200/PSV-204")]  # 'PSV 204' is one map tag in another style
        self.assertEqual((psv["matched_text"], psv["matched"]), ("PSV 204", "format-insensitive"))
        self.assertNotIn("matched", m[("S1/DOC/OP-200-07", "S1/P1/200/P-102")])  # exact links carry no flag

    def test_match_mentions_false_positive_guards(self):
        exact = {"P-101": {("S1/A/1/P-101", "tag")}, "P-101A": {("S1/A/1/P-101A", "tag")}}
        by_norm = {"P101": {"S1/A/1/P-101"}, "P101A": {"S1/A/1/P-101A"}}
        by_base = {"P101": {"S1/A/1/P-101A"}}
        text = "See P&ID 200-01 rev D and OP-200-07; pump P-101A (not P-101B), Unit 200, ISO 9001, xP-101."
        asserted, findings = om.match_mentions(text, exact, by_norm, by_base, [], {})
        self.assertEqual([a["node"] for a in asserted], ["S1/A/1/P-101A"])  # P-101A never matches P-101
        kinds = {f["matched_text"]: f["kind"] for f in findings}
        self.assertEqual(kinds["P-101B"], "near miss (suffix not on the map)")
        self.assertNotIn("ID 200", kinds)

    def test_format_insensitive_links_only_one_map_tag(self):
        exact = {"P-101": {("S1/A/1/P-101", "tag")}, "P-1010": {("S1/A/1/P-1010", "tag")},
                 "TT-2207": {("S1/A/1/TT-2207", "tag")}, "FP-01": {("S1/A/1/P-101", "alias (former tag)")},
                 "AT-2207": {("S1/A/1/AT-2207", "tag")}}
        by_norm = {"P101": {"S1/A/1/P-101"}, "P1010": {"S1/A/1/P-1010"}, "TT2207": {"S1/A/1/TT-2207"},
                   "FP01": {"S1/A/1/P-101"}, "AT2207": {"S1/A/1/AT-2207"}}
        nodes = {i: {"tag": i.rsplit("/", 1)[1]} for ids in by_norm.values() for i in ids}
        text = "Start P101, P 101 and p-101; TT2207 high; old tag FP01; P-1010 is another pump; at 2207 hours; P1010."
        asserted, findings = om.match_mentions(text, exact, by_norm, {}, [], nodes)
        got = [(a["matched_text"], a["node"], a.get("matched")) for a in asserted]
        self.assertEqual(got, [
            ("P101", "S1/A/1/P-101", "format-insensitive"), ("P 101", "S1/A/1/P-101", "format-insensitive"),
            ("p-101", "S1/A/1/P-101", "format-insensitive"), ("TT2207", "S1/A/1/TT-2207", "format-insensitive"),
            ("FP01", "S1/A/1/P-101", "format-insensitive"), ("P-1010", "S1/A/1/P-1010", None),
            ("P1010", "S1/A/1/P-1010", "format-insensitive")])  # P-101 and P-1010 never cross
        self.assertIn("via alias (former tag)", asserted[4]["confidence"])
        # 'at 2207' (lower-case letters and a space) could be prose: confirm, never link
        self.assertEqual([(f["matched_text"], f["kind"], f.get("confirm")) for f in findings],
                         [("at 2207", "lower-case letters and a space; could be ordinary words", True)])
        # ordinary lower-case words that are no map tag are not findings at all
        self.assertEqual(om.match_mentions("see page 12, step 30, unit 200", exact, by_norm, {}, [], nodes), ([], []))

    def test_format_insensitive_ambiguity_and_near_misses_go_to_review(self):
        exact = {"P-101": {("S1/A/1/P-101", "tag"), ("S1/B/2/P-101", "tag")}, "P-102A": {("S1/A/1/P-102A", "tag")}}
        by_norm = {"P101": {"S1/A/1/P-101", "S1/B/2/P-101"}, "P102A": {"S1/A/1/P-102A"}}
        by_base = {"P102": {"S1/A/1/P-102A"}}
        text = "P101 in Unit 1; p102 seal; P-101A spare"
        asserted, findings = om.match_mentions(text, exact, by_norm, by_base, ["S1/A/1"], {})
        self.assertEqual(asserted, [])  # covers do not turn a format-only match in two units into a link
        self.assertEqual([(f["matched_text"], f["kind"], f["confirm"]) for f in findings], [
            ("P101", "same tag in another format, in more than one scope", True),
            ("p102", "near miss (the map has only suffixed tags)", True),
            ("P-101A", "near miss (suffix not on the map)", True)])
        self.assertEqual(findings[0]["covered"], ["S1/A/1/P-101"])
        # a unique format-only match in another unit than the document covers is confirmed, not linked
        asserted, findings = om.match_mentions("P102A", exact, by_norm, by_base, ["S1/B/2"], {})
        self.assertEqual((asserted, findings[0]["kind"]),
                         ([], "same tag in another format, outside the units the document covers"))
        asserted, _ = om.match_mentions("P102A", exact, by_norm, by_base, ["S1/A/1/P-101"], {})
        self.assertEqual([a["node"] for a in asserted], ["S1/A/1/P-102A"])  # equipment cover counts as its unit

    def test_superseded_basis_and_routing_to_document_owner(self):
        c = self.conflicts("superseded_basis")
        self.assertEqual([(x["subject"], x["record_owner"]) for x in c], [("S1/DOC/DB-P101", "Process")])
        self.assertEqual(self.nodes["S1/DOC/DB-P101"]["document"]["status"], "released")
        self.assertEqual(self.nodes["S1/DOC/CW-N-01"]["document"]["status"], "draft")

    def test_mention_of_unlisted_tag_is_a_register_conflict(self):
        c = self.conflicts("mention_not_in_register")
        self.assertEqual([(x["subject"], x["record_owner"]) for x in c], [("S1/P1/200/P-102", "Maintenance")])

    def test_owner_split_queues_keep_order_and_safety_floor(self):
        base = self.dir / "start" / "queues"
        for f in base.rglob("*.csv"):
            rows = read_rows(f)
            self.assertEqual(om.floor_problems(rows), [], f)
            ranks = [int(r["rank"]) for r in rows]
            self.assertEqual(ranks, sorted(ranks), f)
        maint = {r["item"]: r for r in read_rows(base / "by-owner" / "maintenance.csv")}
        self.assertEqual(maint["S1/P1/200/PSV-204"]["tier"], "amber")
        self.assertEqual(maint["S1/P1/200/PSV-204"]["safety"], "relief device")
        total = sum(len(read_rows(f)) for f in (base / "by-owner").glob("*.csv"))
        self.assertEqual(total, len(read_rows(base / "review_queue.csv")))


class TwoStarts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        shutil.copytree(EX / "inputs", self.dir / "inputs")
        self.inputs = self.dir / "inputs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_mixed_start_drawings_only_plant_is_reviewed_not_conflicted(self):
        g, _, rows, _ = om.build(self.inputs / "site.json", self.dir / "out")
        conf = [n["conflict"] for n in g["nodes"] if n["kind"] == "conflict"]
        self.assertFalse([c for c in conf if c["type"] == "asset_presence" and "/P2/" in c["subject"]])
        drafts = {r["item"] for r in rows if r["kind"].startswith("on the P&ID, not in the ")}
        self.assertEqual(drafts, {"S1/P2/300/FIC-3101", "S1/P2/300/FT-3101", "S1/P2/300/FV-3101",
                                  "S1/P2/300/P-101", "S1/P2/300/V-301"})

    def test_partial_loop_rows_are_kept_with_the_empty_fields_as_review_items(self):
        # a DCS export routinely leaves a field blank; the row is kept, the blank is visible and never filled in
        loops_csv = self.inputs / "lists" / "dcs_loops_unit200.csv"
        loops_csv.write_text(loops_csv.read_text(encoding="utf-8")
                             + "FIC-2203B,,FV-2203,Feed flow trim (no measurement exported),unverified\n"
                             + ",LT-2204,,Level indication only,unverified\n", encoding="utf-8", newline="\n")
        with self.assertRaises(loop_audit.InputError):  # the grader still refuses an incomplete answer key
            loop_audit.read_loops(loops_csv)
        g, _, rows, _ = om.build(self.inputs / "site.json", self.dir / "out")
        got = {lp["line"]: lp for lp in g["loops"] if lp.get("empty_fields")}
        self.assertEqual({k: v["empty_fields"] for k, v in got.items()}, {6: ["measurement"], 7: ["controller", "output"]})
        trim, level = got[6], got[7]
        self.assertNotEqual(trim["outcome"], "located and consistent")
        self.assertEqual(trim["route"], "I&C")  # the loop list's owner explains its own blank
        self.assertIn("measurement: empty in the loop list (not filled in)", trim["missing"])
        self.assertEqual(level["item"], "S1/P1/200/DCS-LOOPS-200-line-7")
        # nothing is invented for a blank: no edge from or to a guessed tag, no pairing conflict against a blank
        self.assertFalse([e for e in g["edges"] if e["type"] == "controls" and e["to"].endswith("/FIC-2203B")])
        self.assertFalse([n for n in g["nodes"] if n["kind"] == "conflict" and n["conflict"]["type"] == "loop_pairing"
                          and n["conflict"]["subject"].endswith("/FIC-2203B")])
        queue = {r["item"]: r for r in rows if r["kind"] == "listed loop"}
        self.assertEqual(queue["loop FIC-2203B (DCS-LOOPS-200 line 6)"]["tier"], "amber")
        self.assertEqual(queue["loop (no controller) (DCS-LOOPS-200 line 7)"]["tier"], "amber")
        self.assertEqual(om.problems(g), [])

    def test_generated_loop_list_round_trips_through_the_import_path(self):
        counts = om.draft_lists(self.inputs / "site.json", self.dir / "drafts")
        self.assertEqual(counts, {"p2-300/equipment.csv": 3, "p2-300/instrument_index.csv": 2,
                                  "p2-300/loops.csv": 1})
        loops, _ = loop_audit.read_loops(self.dir / "drafts" / "p2-300" / "loops.csv")
        self.assertEqual([(lp["controller"], lp["measurement"], lp["output"]) for lp in loops],
                         [("FIC-3101", "FT-3101", "FV-3101")])

    def test_generated_lists_reimported_as_confirmed_lists(self):
        om.draft_lists(self.inputs / "site.json", self.dir / "drafts")
        dst = self.inputs / "lists" / "regen"
        dst.mkdir()
        for f in (self.dir / "drafts" / "p2-300").glob("*.csv"):
            (dst / f.name).write_text(f.read_text(encoding="utf-8").replace(",unverified,", ",confirmed,"),
                                      encoding="utf-8", newline="\n")
        site = json.loads((self.inputs / "site.json").read_text(encoding="utf-8"))
        site["maintenance_export"] = [site["maintenance_export"], {"id": "P2-EQ", "path": "lists/regen/equipment.csv",
                                                                   "revision": "1", "scopes": ["S1/P2"]}]
        site["instrument_index"] = [site["instrument_index"], {"id": "P2-II", "path": "lists/regen/instrument_index.csv",
                                                               "revision": "1", "scopes": ["S1/P2"]}]
        site["loop_lists"].append({"id": "P2-LL", "path": "lists/regen/loops.csv", "scope": "S1/P2/300",
                                   "revision": "1"})
        (self.inputs / "site2.json").write_text(json.dumps(site), encoding="utf-8")
        g, _, rows, _ = om.build(self.inputs / "site2.json", self.dir / "out2")
        nodes = {n["id"]: n for n in g["nodes"]}
        self.assertEqual(nodes["S1/P2/300/V-301"]["status"], "confirmed")
        edge = next(e for e in g["edges"] if e["id"] == "controls:S1/P2/300/FIC-3101->S1/P2/300/FV-3101")
        self.assertEqual(edge["status"], "confirmed")
        lp = next(x for x in g["loops"] if x["controller"] == "FIC-3101")
        self.assertEqual(lp["outcome"], "located and consistent")
        self.assertFalse([r for r in rows if r["kind"].startswith("on the P&ID, not in the ")])

    def test_incremental_batch_rebuilds_only_changed_sheets_and_reopens_dependents(self):
        out = self.dir / "out"
        _, run, _, _ = om.build(self.inputs / "site.json", out)
        self.assertEqual(len(run["rebuilt"]), 4)
        _, run, _, reopened = om.build(self.inputs / "site.json", out)
        self.assertEqual((run["rebuilt"], len(run["reused"])), ([], 4))
        self.assertEqual(reopened, [])
        sheet = self.inputs / "sheets" / "P2-300-01.json"
        sheet.write_text(sheet.read_text(encoding="utf-8").replace('"zone": "C2"', '"zone": "C3"'), encoding="utf-8")
        basis = self.inputs / "docs" / "p101-design-basis-rev3.txt"
        basis.write_text(basis.read_text(encoding="utf-8") + "Added a line.\n", encoding="utf-8")
        _, run, _, reopened = om.build(self.inputs / "site.json", out)
        self.assertEqual(run["rebuilt"], ["PID-P2-300-01"])
        self.assertEqual(len(run["reused"]), 3)
        self.assertTrue(any(r.startswith("document OP-200-07: its basis DB-P101 changed") for r in reopened), reopened)

    def test_register_answer_citing_a_dependent_document_reopens(self):
        import context_register as cr
        q = self.dir / "q.json"
        q.write_text(json.dumps({"questions": [{"id": "q-flow", "question": "What design flow does P-101 have?",
                                                "assets": []}]}), encoding="utf-8")
        args = ["--model", str(ROOT / "data" / "te_process_model.json"), "--questions", str(q),
                "--sources", str(self.inputs / "documents.json")]
        quiet(cr.main, ["prepare"] + args + ["--out", str(self.dir / "ctx")])
        choice = next(r for r in read_rows(self.dir / "ctx" / "evidence_choices.csv") if r["source_id"] == "OP-200-07")
        answers = self.dir / "answers.csv"
        answers.write_text(",".join(cr.COLUMNS) + "\n" + ",".join([
            "q-flow", "a1", "design-flow", "45 m3/h", "procedure assumes the design basis flow", "partial",
            "proposed", "", "", "", "", "", "OP-200-07", "whole", "unknown", "unknown", "",
            choice["evidence_fingerprint"]]) + "\n", encoding="utf-8")
        self.assertEqual(quiet(cr.main, ["apply"] + args + ["--answers", str(answers), "--out",
                                                             str(self.dir / "ctx2")]), 0)
        register = self.dir / "ctx2" / "context.json"
        out = self.dir / "out"
        om.build(self.inputs / "site.json", out, register_path=register)
        basis = self.inputs / "docs" / "p101-design-basis-rev3.txt"
        basis.write_text(basis.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
        _, _, _, reopened = om.build(self.inputs / "site.json", out, register_path=register)
        self.assertIn("answer q-flow/a1: cites OP-200-07, whose content or basis changed; reopen it with "
                      "context_register.py apply", reopened)

    def test_human_decisions_persist_and_nothing_auto_resolves(self):
        out = self.dir / "out"
        g, _, _, _ = om.build(self.inputs / "site.json", out)
        value = next(n["conflict"] for n in g["nodes"] if n["kind"] == "conflict"
                     and n["conflict"]["type"] == "value_disagreement")
        dec = self.dir / "decisions.csv"
        dec.write_text(f"conflict_id,status,by,on,note\n{value['id']},disputed,A. Reviewer (fictional),2026-11-03,"
                       "pump curve pending\n", encoding="utf-8")
        g, _, _, _ = om.build(self.inputs / "site.json", out, decisions=dec)
        c = {n["conflict"]["id"]: n["conflict"] for n in g["nodes"] if n["kind"] == "conflict"}
        self.assertEqual(c[value["id"]]["status"], "disputed")
        lst = self.inputs / "lists" / "maintenance_equipment.csv"
        lst.write_text(lst.read_text(encoding="utf-8").replace("40 m3/h", "45 m3/h"), encoding="utf-8")
        g, _, _, _ = om.build(self.inputs / "site.json", out)
        c = {n["conflict"]["id"]: n["conflict"] for n in g["nodes"] if n["kind"] == "conflict"}
        self.assertEqual((c[value["id"]]["status"], c[value["id"]]["detected"]), ("disputed", False))

    def test_cross_unit_loop_numbers_never_group(self):
        site = json.loads((self.inputs / "site.json").read_text(encoding="utf-8"))
        site["plants"][1]["units"].append({"id": "400", "name": "Unit 400"})
        (self.inputs / "site.json").write_text(json.dumps(site), encoding="utf-8")
        (self.inputs / "sheets" / "P2-400-01.json").write_text(json.dumps({
            "schema": "one-map-sheet-1", "instruments": [{"tag": "FT-3101"}, {"tag": "FV-3101B"}]}), encoding="utf-8")
        with (self.inputs / "drawing_register.csv").open("a", encoding="utf-8", newline="") as f:
            f.write("400-01,A,P2,400,Doc control,sheets/P2-400-01.json,draft\n")
        counts = om.draft_lists(self.inputs / "site.json", self.dir / "drafts")
        loops = (self.dir / "drafts" / "p2-300" / "loops.csv").read_text(encoding="utf-8")
        self.assertNotIn("FV-3101B", loops)
        self.assertNotIn("p2-400/loops.csv", counts)  # no controller in unit 400: nothing grouped across units


class Units(unittest.TestCase):
    def test_loop_candidates_ab_suffix_and_split_range(self):
        members = {"u/FIC-10": "FIC-10", "u/FT-10A": "FT-10A", "u/FV-10A": "FV-10A", "u/FV-10B": "FV-10B",
                   "u/TE-11A": "TE-11A", "u/TE-11B": "TE-11B"}
        cands, report = om.loop_candidates(members, set())
        self.assertEqual(set(cands["u/FIC-10"]["out"]), {"u/FV-10A", "u/FV-10B"})
        self.assertEqual(set(cands["u/FIC-10"]["in"]), {"u/FT-10A"})
        te = next(r for r in report if r["loop"] == "11")
        self.assertEqual(te["members"], ["TE-11A", "TE-11B"])
        self.assertIn("no controller", te["note"])

    def test_signal_line_alone_pairs_different_numbers(self):
        cands, _ = om.loop_candidates({"u/PT-11": "PT-11", "u/PIC-22": "PIC-22"}, {frozenset(("u/PT-11", "u/PIC-22"))})
        self.assertEqual(cands["u/PIC-22"]["in"], {"u/PT-11": {"signal_line"}})

    def test_open100_sheet0_has_groups_but_no_controllers(self):
        text, total = om.loops_from_graph(ROOT / "examples" / "graph-export" / "sheet0_graph.json")
        self.assertEqual(total, 0)
        self.assertIn("| 14089 | TE 14089A, TE 14089B | no controller", text)

    def test_split_existing_queue_keeps_order_and_refuses_broken_floor(self):
        with tempfile.TemporaryDirectory() as d:
            q = Path(d) / "q.csv"
            q.write_text("rank,tier,why,belongs_to\n1,red,x,U1\n2,amber,safety-relevant (relief device): always "
                         "checked,U2\n3,green,y,U1\n", encoding="utf-8")
            self.assertEqual(om.split_existing(q, "belongs_to", Path(d) / "s"), {"U1": 2, "U2": 1})
            self.assertEqual([r["rank"] for r in read_rows(Path(d) / "s" / "u1.csv")], ["1", "3"])
            q.write_text("rank,tier,why,belongs_to\n1,green,safety-relevant (relief device),U1\n", encoding="utf-8")
            with self.assertRaises(om.InputError):
                om.split_existing(q, "belongs_to", Path(d) / "s2")

    def test_twin_graph_1_keeps_its_vocabulary_and_existing_exports_check(self):
        for p in sorted((ROOT / "examples" / "graph-export").glob("*.json")):
            g = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(g, dict) and g.get("schema") == "twin-graph-1":
                self.assertEqual(gx.problems(g), [], p.name)
        g = {"schema": "twin-graph-1", "nodes": [{"id": "D", "kind": "document", "status": "unverified",
                                                   "attributes": []}], "edges": []}
        self.assertTrue(any("unknown kind 'document'" in x for x in om.problems(g)))

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(EX / "inputs", Path(d) / "in")
            site = json.loads((Path(d) / "in" / "site.json").read_text(encoding="utf-8"))
            site["shared_systems"][0]["owner_scope"] = "S1/NOWHERE"
            (Path(d) / "in" / "site.json").write_text(json.dumps(site), encoding="utf-8")
            with self.assertRaises(om.InputError):
                om.build(Path(d) / "in" / "site.json", Path(d) / "out")
            site["shared_systems"][0]["owner_scope"] = "S1/UTIL"
            site["drawing_register"] = "../outside.csv"
            (Path(d) / "in" / "site.json").write_text(json.dumps(site), encoding="utf-8")
            with self.assertRaises(om.InputError):
                om.build(Path(d) / "in" / "site.json", Path(d) / "out")


def load_office_maker():
    spec = importlib.util.spec_from_file_location("make_office_docs", EX / "make_office_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OneMapDocumentText(unittest.TestCase):
    """Documents are read by extract_text.py: Office mentions with locators, and statuses that become notes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.inputs = Path(self.tmp.name) / "in"
        shutil.copytree(EX / "inputs", self.inputs, ignore=shutil.ignore_patterns("office"))
        load_office_maker().build(self.inputs / "docs" / "office")

    def tearDown(self):
        self.tmp.cleanup()

    def mentions(self, g):
        return {(e["from"], e["to"]): dict({c["name"]: c["value"] for c in e["attributes"]},
                                           more=e.get("more_locators", []))
                for e in g["edges"] if e["type"] == "mentions"}

    def test_office_example_regenerates_and_mentions_carry_locators(self):
        out = Path(self.tmp.name) / "office"
        g, _, rows, _ = quiet(om.build, self.inputs / "site-office.json", out)
        for exp in sorted(p for p in (EXPECTED / "office").rglob("*") if p.is_file()):
            rel = exp.relative_to(EXPECTED / "office")
            self.assertEqual((out / rel).read_bytes().replace(b"\r\n", b"\n"),
                             exp.read_bytes().replace(b"\r\n", b"\n"), rel)
        m = self.mentions(g)
        su, pm = "S1/DOC/SU-200-03", "S1/DOC/PM-200"
        self.assertEqual(m[(su, "S1/P1/200/TT-2205")]["locator"], "paragraph 2, column 41")
        self.assertEqual(m[(su, "S1/P1/200/FT-2203")]["locator"], "table 1 row 2, column 1")
        self.assertNotIn("matched", m[(su, "S1/P1/200/PSV-204")])  # written exactly
        self.assertEqual(m[(pm, "S1/P1/200/FV-2203")]["locator"], "sheet 'PM plan' cell A3, column 1")
        former = m[(su, "S1/P1/200/P-101")]
        self.assertEqual((former["matched_text"], former["matched"]), ("FP01", "format-insensitive"))
        self.assertIn("via alias (former tag)", former["confidence"])
        confirm = [r for r in rows if r["kind"] == om.CONFIRM and r["item"] in (su, pm)]
        self.assertEqual(len(confirm), 1)
        self.assertIn("'P 101' at paragraph 1, column 26", confirm[0]["why"])
        self.assertEqual(confirm[0]["owner"], "Operations")
        docs = {n["id"]: n["document"] for n in g["nodes"] if n["kind"] == "document"}
        self.assertEqual((docs[pm]["text"]["format"], docs[pm]["text"]["status"]), ("xlsx", "ok"))
        self.assertEqual(om.problems(g), [])

    def test_unread_documents_become_low_priority_notes_to_their_owner(self):
        docs = self.inputs / "docs"
        (docs / "haccp-2019.doc").write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 56)
        (docs / "broken.docx").write_bytes(b"PK this is not a real archive")
        (docs / "blank.txt").write_bytes(b"")
        (docs / "both.txt").write_text("FT2203 first, then FT-2203.\n", encoding="utf-8")
        man = json.loads((self.inputs / "documents.json").read_text(encoding="utf-8"))
        for did, path, owner in (("HACCP-2019", "docs/haccp-2019.doc", "Quality"),
                                 ("BROKEN", "docs/broken.docx", "Maintenance"),
                                 ("BLANK", "docs/blank.txt", "Operations"), ("BOTH", "docs/both.txt", "I&C")):
            man["documents"].append({"id": did, "revision": "1", "path": path, "owner": owner, "status": "draft",
                                     "locators": [{"id": "whole", "locator": "whole document"}]})
        (self.inputs / "documents.json").write_text(json.dumps(man), encoding="utf-8")
        g, _, rows, _ = quiet(om.build, self.inputs / "site.json", Path(self.tmp.name) / "out")
        notes = {r["item"]: r for r in rows if r["kind"] == om.DOC_TEXT_NOTE}
        self.assertEqual(sorted(notes), ["S1/DOC/BLANK", "S1/DOC/BROKEN", "S1/DOC/HACCP-2019"])
        self.assertEqual(notes["S1/DOC/HACCP-2019"]["owner"], "Quality")
        self.assertIn("text unsupported (legacy Word .doc is not read; convert it to .docx",
                      notes["S1/DOC/HACCP-2019"]["why"])
        self.assertIn("text error", notes["S1/DOC/BROKEN"]["why"])
        self.assertIn("no text found", notes["S1/DOC/BLANK"]["why"])
        amber = [r["kind"] for r in rows if r["tier"] == "amber" and not r["safety"]]
        low = [i for i, k in enumerate(amber) if k in om.LOW_PRIORITY_KINDS]
        self.assertEqual(low, list(range(len(amber) - len(low), len(amber))))  # last of the amber rows
        both = self.mentions(g)[("S1/DOC/BOTH", "S1/P1/200/FT-2203")]
        self.assertEqual((both["locator"], both.get("matched"), both["more"]),
                         ("line 1, column 20", None, ["line 1, column 1"]))  # the exact mention leads
        statuses = {n["id"]: n["document"]["text"]["status"] for n in g["nodes"]
                    if n["kind"] == "document" and "text" in n["document"]}
        self.assertEqual((statuses["S1/DOC/HACCP-2019"], statuses["S1/DOC/BROKEN"]), ("unsupported", "error"))


if __name__ == "__main__":
    unittest.main()
