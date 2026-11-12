"""Round 6 increment 3: loop assembly, the dashed signal-line tracer and the loop scorer, on synthetic inputs.

The pure assembly tests need only the standard library; the drawn-line tests and the end-to-end intake test need
OpenCV and NumPy and are skipped without them."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import loop_assembly as la
import loop_score as ls

try:
    import cv2
    import numpy as np
    HAVE_CV2 = True
except ImportError:
    HAVE_CV2 = False


def inst(iid, tag, sheet="0", **extra):
    return {"id": iid, "tag": tag, "provenance": [{"sheet": sheet}], **extra}


def model(instruments, connectors=(), pairs=(), line_items=()):
    return {"instruments": list(instruments), "line_items": list(line_items),
            "offpage_connectors": list(connectors), "offpage_pairs": list(pairs)}


def line(lid, members, sheet="0"):
    return {"id": lid, "sheet": sheet, "line_kind": "dashed_signal_line", "members": sorted(members),
            "box_0_1000": [10.0, 10.0, 20.0, 20.0], "dashes": 5}


def rel(block, typ):
    return {(r["from"], r["to"]) for r in block["relations"] if r["type"] == typ}


def loop(block, ctrl):
    return next(lp for lp in block["loops"] if lp["controller"] == ctrl)


class TagsAndRoles(unittest.TestCase):
    def test_loop_identity_reads_area_number_and_suffix(self):
        self.assertEqual(la.loop_identity("FIC 101"), ("", "101", "", "FIC"))
        self.assertEqual(la.loop_identity("FIC-101"), ("", "101", "", "FIC"))
        self.assertEqual(la.loop_identity("10-FIC-101"), ("10", "101", "", "FIC"))
        self.assertEqual(la.loop_identity("U1 FT 101"), ("U1", "101", "", "FT"))
        self.assertEqual(la.loop_identity("AIC 123A"), ("", "123", "A", "AIC"))
        self.assertEqual(la.loop_identity("PIC 4712.02"), ("", "4712.02", "", "PIC"))
        self.assertIsNone(la.role_of(la.loop_identity("R-101")[3]))  # reads as a tag, with no loop role
        for bad in ("", None, "BATTERY LIMIT / A FEED", "ZSO 500, 101", "P-101A/B"):
            self.assertIsNone(la.loop_identity(bad), bad)

    def test_roles_from_the_isa_letters(self):
        cases = {"FIC": "controller", "TIC": "controller", "SC": "controller", "FV": "final_element",
                 "PSV": "final_element", "PCV": "final_element", "FT": "transmitter", "PDT": "transmitter",
                 "TE": "primary_element", "LSHH": "switch", "FY": "relay", "FI": "indicator", "PI": "indicator",
                 "LAH": "indicator", "F": None}
        for letters, role in cases.items():
            self.assertEqual(la.role_of(letters), role, letters)

    def test_a_plant_coded_tag_gets_no_role_and_untagged_valves_are_not_candidates(self):
        m = model([inst("A", "MOV 101", instrument_kind="operated valve"), inst("B", "FT 101")],
                  line_items=[{"id": "V1", "tag": "FV 101", "provenance": [{"sheet": "0"}]},
                              {"id": "V2", "tag": None, "provenance": [{"sheet": "0"}]},
                              {"id": "V3", "tag": "HS 101", "provenance": [{"sheet": "0"}]}])
        c = la.candidates(m)
        self.assertIsNone(c["A"]["role"])
        self.assertIn("no_role", c["A"])
        self.assertEqual(c["V1"]["role"], "final_element")  # a control valve the reader drew as a valve
        self.assertNotIn("V2", c)
        self.assertNotIn("V3", c)  # an in-line item only joins as a final element


class Assembly(unittest.TestCase):
    def basic(self):
        return model([inst("FT", "FT 101"), inst("FIC", "FIC 101"), inst("FV", "FV 101")])

    def test_a_loop_traced_both_ways_is_confirmed_and_controls_its_valve(self):
        b = la.assemble(self.basic(), [line("L1", ["FT", "FIC"]), line("L2", ["FIC", "FV"])])
        self.assertEqual(rel(b, "signal_to"), {("FT", "FIC"), ("FIC", "FV")})
        self.assertEqual(rel(b, "controls"), {("FIC", "FV")})
        lp = loop(b, "FIC")
        self.assertEqual(lp["status"], "confirmed")
        for r in b["relations"]:
            self.assertEqual(r["confidence"], "traced_and_grouped")
            self.assertTrue(any(e["kind"] == "traced_line" for e in r["evidence"]))
            self.assertEqual(r["verification"], {"status": "unverified"})
        ctrl = next(r for r in b["relations"] if r["type"] == "controls")
        self.assertTrue(any(e["kind"] == "loop_confirmed" for e in ctrl["evidence"]))

    def test_tag_grouping_without_a_traced_line_asserts_nothing(self):
        b = la.assemble(self.basic(), [])
        self.assertEqual(b["relations"], [])
        lp = loop(b, "FIC")
        self.assertEqual(lp["status"], "unconfirmed")
        self.assertEqual({x["id"] for x in lp["tag_grouping_unconfirmed"]}, {"FT", "FV"})

    def test_a_traced_output_without_a_traced_measurement_is_partly_confirmed_and_controls_nothing(self):
        b = la.assemble(self.basic(), [line("L2", ["FIC", "FV"])])
        self.assertEqual(loop(b, "FIC")["status"], "partly_confirmed")
        self.assertEqual(rel(b, "signal_to"), {("FIC", "FV")})
        self.assertEqual(rel(b, "controls"), set())

    def test_shared_loop_numbers_in_two_units_stay_two_loops(self):
        m = model([inst("A1", "10-FT-101"), inst("A2", "10-FIC-101"), inst("A3", "10-FV-101"),
                   inst("B1", "20-FT-101"), inst("B3", "20-FV-101")])
        b = la.assemble(m, [line("L1", ["A1", "A2"]), line("L2", ["A2", "A3"])])
        lp = loop(b, "A2")
        self.assertEqual(lp["loop_identity"], "10-101")
        self.assertEqual(lp["status"], "confirmed")
        self.assertEqual(lp["tag_grouping_unconfirmed"], [])  # unit 20's 101 is not a member of unit 10's loop
        self.assertEqual([g["loop_identity"] for g in b["tag_groups_without_controller"]], ["20-101"])
        self.assertFalse({"B1", "B3"} & {x for r in b["relations"] for x in (r["from"], r["to"])})

    def test_a_missing_controller_gives_no_loop_and_no_controls(self):
        m = model([inst("FT", "FT 201"), inst("FV", "FV 201")])
        b = la.assemble(m, [line("L1", ["FT", "FV"])])
        self.assertEqual(b["loops"], [])
        self.assertEqual(rel(b, "controls"), set())
        self.assertEqual(rel(b, "signal_to"), {("FT", "FV")})  # the drawn line itself is still reported
        self.assertEqual(b["tag_groups_without_controller"][0]["loop_identity"], "201")

    def test_a_signal_line_across_a_loop_boundary_is_kept_as_a_conflict(self):
        m = model([inst("T1", "FT 301"), inst("C1", "FIC 301"), inst("V1", "FV 301"),
                   inst("T2", "FT 302"), inst("C2", "FIC 302"), inst("V2", "FV 302")])
        b = la.assemble(m, [line("L1", ["T1", "C2"]), line("L2", ["C2", "V2"]), line("L3", ["C1", "V1"])])
        l2 = loop(b, "C2")
        self.assertEqual(l2["status"], "confirmed")
        self.assertEqual([x["id"] for x in l2["measurements"]], ["T1"])
        self.assertFalse(l2["measurements"][0]["same_loop_identity"])
        self.assertEqual([x["id"] for x in l2["tag_grouping_unconfirmed"]], ["T2"])
        l1 = loop(b, "C1")
        self.assertEqual(l1["status"], "partly_confirmed")
        self.assertEqual([x["id"] for x in l1["tag_grouping_refuted"]], ["T1"])
        kinds = {(c["kind"], c["item"]) for c in b["conflicts"]}
        self.assertIn(("loop_identity", "T1"), kinds)
        self.assertIn(("tag_grouping_refuted", "T1"), kinds)
        self.assertEqual(rel(b, "controls"), {("C2", "V2")})  # FIC 301 has no traced measurement
        t1 = next(r for r in b["relations"] if r["from"] == "T1")
        self.assertEqual(t1["confidence"], "traced")

    def test_a_cross_sheet_flag_joins_a_signal_only_through_a_paired_connector(self):
        m = model([inst("T", "FT 401"), inst("C", "FIC 401"), inst("V", "FV 401", sheet="1")],
                  connectors=[{"id": "OP0", "text": "SIG PID 2 / TO FV 401"}, {"id": "OP1", "text": "SIG PID 1 / FROM FIC 401"}],
                  pairs=[{"id": "XP-001", "a": "OP0", "b": "OP1", "sheet_a": "0", "sheet_b": "1",
                          "text_a": "SIG PID 2 / TO FV 401", "text_b": "SIG PID 1 / FROM FIC 401",
                          "method": "reciprocal_drawing_refs", "verification": {"status": "unverified"}}])
        lines = [line("L1", ["T", "C"]), line("L2", ["C", "OP0"]), line("L3", ["OP1", "V"], sheet="1")]
        b = la.assemble(m, lines)
        self.assertEqual(rel(b, "controls"), {("C", "V")})
        r = next(r for r in b["relations"] if r["type"] == "signal_to" and r["to"] == "V")
        self.assertEqual(r["confidence"], "traced_cross_sheet")
        flag = next(e for e in r["evidence"] if e["kind"] == "cross_sheet_flag")
        self.assertEqual(flag["pair"], "XP-001")
        self.assertEqual({x["names"] for x in flag["text_names_reached_instrument"]}, {"FV 401", "FIC 401"})
        unpaired = la.assemble({**m, "offpage_pairs": []}, lines)  # no pair: the two halves stay apart
        self.assertEqual(rel(unpaired, "controls"), set())
        self.assertNotIn(("C", "V"), rel(unpaired, "signal_to"))

    def test_a_cascade_points_from_the_outer_controller_to_the_inner_one(self):
        m = model([inst("TT", "TT 501"), inst("TIC", "TIC 501"), inst("FT", "FT 502"), inst("FIC", "FIC 502"),
                   inst("FV", "FV 502")])
        b = la.assemble(m, [line("L1", ["TT", "TIC"]), line("L2", ["FIC", "TIC"]), line("L3", ["FT", "FIC"]),
                            line("L4", ["FIC", "FV"])])
        self.assertEqual(rel(b, "sets_point_of"), {("TIC", "FIC")})
        self.assertIn(("TIC", "FIC"), rel(b, "signal_to"))
        self.assertEqual(loop(b, "TIC")["loop_type"], "cascade")
        self.assertEqual(loop(b, "TIC")["status"], "confirmed")
        self.assertEqual(rel(b, "controls"), {("FIC", "FV")})

    def test_two_controllers_with_no_final_element_leave_the_signal_undirected(self):
        m = model([inst("A", "TIC 601"), inst("B", "TIC 602")])
        b = la.assemble(m, [line("L1", ["A", "B"])])
        r = b["relations"][0]
        self.assertEqual((r["type"], r["direction"]), ("signal_to", "unknown"))
        self.assertNotIn("direction_basis", r)
        self.assertEqual(rel(b, "sets_point_of"), set())

    def test_a_branching_line_needs_a_single_sender(self):
        m = model([inst("AT", "AT 700"), inst("A", "AIC 700A"), inst("B", "AIC 700B"), inst("V", "FV 700")])
        star = la.assemble(m, [line("L1", ["AT", "A", "B"])])
        self.assertEqual(rel(star, "signal_to"), {("AT", "A"), ("AT", "B")})
        self.assertEqual(loop(star, "A")["tag_grouping_refuted"], [])  # a sibling controller is not a member
        mixed = la.assemble(m, [line("L1", ["A", "B", "V"])])
        self.assertEqual(mixed["relations"], [])
        self.assertEqual(len(mixed["unresolved_signal_networks"]), 1)

    def test_a_solid_line_between_measuring_instruments_is_not_a_signal(self):
        m = model([inst("A", "PT 900A"), inst("B", "PT 900B"), inst("C", "FIC 901"), inst("T", "FT 901")])
        solid = {"id": "L1", "sheet": "0", "line_kind": "instrument_line", "members": ["A", "B"], "lines": ["S0-IL001"]}
        b = la.assemble(m, [solid, {**solid, "id": "L2", "members": ["C", "T"]}])
        self.assertEqual(rel(b, "signal_to"), {("T", "C")})  # with a controller on it, a solid line is a signal
        self.assertEqual(b["unresolved_signal_networks"][0]["members"], ["A", "B"])
        short = {**line("L3", ["A", "B"]), "dashes": 1}  # a stroke between two stacked transmitters
        self.assertEqual(la.assemble(m, [short])["relations"], [])

    def test_nothing_comes_from_layout(self):
        def with_boxes(shift):
            m = self.basic()
            for n, i in enumerate(m["instruments"]):
                i["provenance"][0]["box_0_1000"] = [100 * n + shift, 50, 100 * n + shift + 20, 70]
            return m
        lines = [line("L1", ["FT", "FIC"]), line("L2", ["FIC", "FV"])]
        self.assertEqual(la.assemble(with_boxes(0), lines), la.assemble(with_boxes(500), lines))

    def test_a_final_element_two_controllers_drive_is_a_conflict(self):
        m = model([inst("T1", "FT 801"), inst("C1", "FIC 801"), inst("T2", "FT 802"), inst("C2", "FIC 802"),
                   inst("V", "FV 801")])
        b = la.assemble(m, [line("L1", ["T1", "C1"]), line("L2", ["C1", "V"]), line("L3", ["T2", "C2"]),
                            line("L4", ["C2", "V"])])
        self.assertIn("final_element_shared", {c["kind"] for c in b["conflicts"]})

    def test_nothing_is_written_when_no_tag_reads_as_an_isa_instrument(self):
        m = model([inst("A", "R-101"), inst("B", None)])
        before = json.dumps(m, sort_keys=True)
        self.assertEqual(la.add_loops(m, Path("unused"))["status"], "nothing to assemble")
        self.assertEqual(json.dumps(m, sort_keys=True), before)


@unittest.skipUnless(HAVE_CV2, "needs OpenCV and NumPy")
class DashedLines(unittest.TestCase):
    """A synthetic sheet: bubbles 50 px, dashes 13 on 6 off, like this repository's generated sheets."""
    W, H = 1000, 600

    def sheet(self, draw):
        img = np.full((self.H, self.W), 255, np.uint8)
        draw(img)
        return img

    def dashed(self, img, pts, dash=13, gap=6):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            length = abs(x1 - x0) + abs(y1 - y0)
            sx, sy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            t = 0
            while t < length:
                e = min(length, t + dash)
                cv2.line(img, (x0 + sx * t, y0 + sy * t), (x0 + sx * (e - 1), y0 + sy * (e - 1)), 0, 2)
                t = e + gap

    def bubble(self, img, x, y):
        cv2.circle(img, (x, y), 24, 0, 2)
        return [x - 25, y - 25, x + 25, y + 25]

    def trace(self, img, boxes):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.png"
            cv2.imwrite(str(p), img)
            syms = [{"id": k, "class": "instrumentation",
                     "box": [1000 * b[0] / self.W, 1000 * b[1] / self.H, 1000 * b[2] / self.W, 1000 * b[3] / self.H]}
                    for k, b in boxes.items()]
            return {tuple(x["members"]) for x in la.dashed_signal_lines(p, syms)["lines"]}

    def test_a_dashed_line_with_a_corner_joins_two_bubbles(self):
        boxes = {}

        def draw(img):
            boxes["A"] = self.bubble(img, 100, 100)
            boxes["B"] = self.bubble(img, 400, 300)
            self.dashed(img, [(125, 100), (400, 100), (400, 275)])
        self.assertEqual(self.trace(self.sheet(draw), boxes), {("A", "B")})

    def test_two_dashed_lines_that_cross_are_not_joined(self):
        boxes = {}

        def draw(img):
            for k, (x, y) in {"A": (100, 300), "B": (700, 300), "C": (400, 60), "D": (400, 540)}.items():
                boxes[k] = self.bubble(img, x, y)
            self.dashed(img, [(125, 300), (675, 300)])
            self.dashed(img, [(400, 85), (400, 515)], dash=13, gap=6)
        self.assertEqual(self.trace(self.sheet(draw), boxes), {("A", "B"), ("C", "D")})

    def test_a_dashed_line_crossing_a_solid_pipe_is_not_joined_to_it(self):
        boxes = {}

        def draw(img):
            boxes["A"] = self.bubble(img, 100, 300)
            boxes["B"] = self.bubble(img, 700, 300)
            boxes["P"] = [380, 520, 420, 560]
            cv2.rectangle(img, (380, 520), (420, 560), 0, 2)
            cv2.line(img, (400, 20), (400, 520), 0, 4)  # a solid pipe from the top into P
            self.dashed(img, [(125, 300), (675, 300)])
        self.assertEqual(self.trace(self.sheet(draw), boxes), {("A", "B")})

    def test_a_tee_joins_three_bubbles_in_one_network(self):
        boxes = {}

        def draw(img):
            for k, (x, y) in {"T": (100, 500), "A": (500, 100), "B": (500, 300)}.items():
                boxes[k] = self.bubble(img, x, y)
            self.dashed(img, [(100, 475), (100, 100), (475, 100)])
            self.dashed(img, [(100, 300), (475, 300)])
        self.assertEqual(self.trace(self.sheet(draw), boxes), {("A", "B", "T")})

    def test_solid_lines_and_lone_strokes_are_not_signal_lines(self):
        boxes = {}

        def draw(img):
            boxes["A"] = self.bubble(img, 100, 300)
            boxes["B"] = self.bubble(img, 700, 300)
            cv2.line(img, (125, 300), (675, 300), 0, 2)  # solid: a pipe or leader, the line layer's business
            cv2.putText(img, "I-I-I", (300, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
        self.assertEqual(self.trace(self.sheet(draw), boxes), set())


@unittest.skipUnless(HAVE_CV2, "needs OpenCV and NumPy")
class Intake(unittest.TestCase):
    def test_the_bundle_carries_loops_and_no_loops_restores_increment_two(self):
        import import_drawing_set as dset
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            img = np.full((600, 1000), 255, np.uint8)
            d = DashedLines()
            boxes = {"ft": d.bubble(img, 150, 400), "fic": d.bubble(img, 150, 150), "fv": d.bubble(img, 500, 150)}
            cv2.line(img, (20, 500), (980, 500), 0, 4)
            cv2.line(img, (150, 425), (150, 500), 0, 2)  # the transmitter's leader to the pipe (solid)
            cv2.line(img, (500, 175), (500, 500), 0, 2)
            d.dashed(img, [(150, 375), (150, 175)])
            d.dashed(img, [(175, 150), (475, 150)])
            cv2.imwrite(str(root / "0.png"), img)
            tags = {"ft": "FT 101", "fic": "FIC 101", "fv": "FV 101"}
            pred = {"symbols": [{"id": k, "class": "instrumentation", "tag": tags[k], "confidence": 1.0,
                                 "box": [b[0], b[1] * 1000 / 600, b[2], b[3] * 1000 / 600]} for k, b in boxes.items()],
                    "connections": []}
            (root / "0.json").write_text(json.dumps(pred), encoding="utf-8")
            man = {"schema_version": dset.SCHEMA, "set_id": "loops", "extraction_format": "prediction",
                   "producer": {"method": "authored synthetic test", "tool": "manual", "model": None},
                   "sheets": [{"drawing_id": "D", "revision": "A", "page": 1, "image": "0.png", "extraction": "0.json"}]}
            (root / "set.json").write_text(json.dumps(man), encoding="utf-8")
            result = dset.import_set(root / "set.json", root / "with")
            dset.import_set(root / "set.json", root / "without", loops=False)
            a = json.loads((root / "with" / "plant_model.json").read_text(encoding="utf-8"))
            b = json.loads((root / "without" / "plant_model.json").read_text(encoding="utf-8"))
            self.assertEqual(result["loops"]["status"], "added")
            self.assertEqual(result["loops"]["confirmed"], 1)
            self.assertEqual(ls.without_loops(a), b)
            self.assertNotIn("control_loops", b)
            tag = {i["id"]: i["tag"] for i in a["instruments"]}
            self.assertEqual({(tag[r["from"]], tag[r["to"]]) for r in a["control_loops"]["relations"]
                              if r["type"] == "controls"}, {("FIC 101", "FV 101")})
            import graph_export  # graph_export.py is hash-pinned (N122): loops are listed, never dropped silently
            g = graph_export.build(root / "with" / "plant_model.json")
            self.assertEqual(graph_export.problems(g), [])
            self.assertIn("control_loops", {x["section"] for x in g["not_exported"]})
            plain = graph_export.build(root / "without" / "plant_model.json")
            self.assertNotIn("control_loops", {x["section"] for x in plain["not_exported"]})
            self.assertEqual(plain["edges"], g["edges"])


class Scorer(unittest.TestCase):
    def test_perfect_and_empty_controls(self):
        key = ls.key_loops()
        self.assertEqual(len(key), 19)
        self.assertEqual(ls.score(ls.perfect(key), key)["loops"]["recall"], 1.0)
        self.assertEqual(ls.score(ls.perfect(key), key)["loops"]["valve_loops"], "11/11")
        self.assertEqual(ls.score(ls.perfect(key), key)["loops"]["cascades"], "8/8")
        e = ls.score(ls.empty(), key)
        self.assertEqual((e["loops"]["recall"], e["loops"]["precision"]), (0.0, None))

    def test_held_out_or_unknown_sets_are_refused_before_any_input_is_read(self):
        for name in ("open100-holdout", "dexpi-holdout", "pahala-p204", "te-c"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stop:
                ls.main(["--sets", name, "--out", "unused"])
            self.assertEqual(stop.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
