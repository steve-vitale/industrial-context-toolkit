"""Round 6 increment 3: loop assembly, the dashed signal-line tracer and the loop scorer, on synthetic inputs.

The pure assembly tests need only the standard library; the drawn-line tests and the end-to-end intake test need
OpenCV and NumPy and are skipped without them."""
import contextlib
import hashlib
import io
import json
import random
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
            "box_0_1000": [10.0, 10.0, 20.0, 20.0], "dashes": 5, "stroke_px": 2, "pipe_px": 4.0, "outline_px": 2.0}


def rel(block, typ):
    return {(r["from"], r["to"]) for r in block["relations"] if r["type"] == typ}


def loop(block, ctrl):
    return next(lp for lp in block["loops"] if lp["controller"] == ctrl)


FUZZ_LETTERS = ["TT", "TIC", "TV", "FT", "FIC", "FV", "PT", "PIC", "PV", "TY", "FE", "FY", "LT", "LIC", "LV", "TI"]


def _fuzz_line(lid, ms, merged=False, ncross=1):
    d = line(lid, ms)
    if merged:
        d["merged_through_crossing"] = True
        d["crossings"] = [{"key": f"sha:{lid}:{j}", "at_0_1000": [1.0, 1.0], "crosses": "pipe"} for j in range(ncross)]
    return d


def _partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for p in _partitions(rest):
        for i in range(len(p)):
            yield p[:i] + [[first] + p[i]] + p[i + 1:]
        yield [[first]] + p


def _readings(x):
    """Every reading of one merged line: as drawn (one plain line), not a signal line at all, or cut at its crossings
    into any number of pieces (every set partition of its members into two or more blocks; a one-member piece is a
    stub)."""
    plain = {k: v for k, v in x.items() if k not in ("merged_through_crossing", "crossings")}
    return [[plain], []] + [[{**plain, "id": f"{x['id']}p{j}", "members": sorted(b)} for j, b in enumerate(p)]
                            for p in _partitions(list(x["members"])) if len(p) >= 2]


def _fuzz_model(rng, rich):
    """A random model and its lines. rich: loop-shaped (per loop a transmitter, controller, valve, sometimes a relay
    or a second valve; controller-to-controller lines for cascades, split-range tees, stray 2-3 member lines, lines
    with two crossings, up to two off-page pairs, some of them cutting one line in two at the sheet edge)."""
    if not rich:
        ids = [f"I{i}" for i in range(rng.randint(3, 8))]
        m = model([inst(i, f"{rng.choice(FUZZ_LETTERS)} {rng.randint(1, 3)}", rng.choice("01")) for i in ids])
        lines = []
        for k in range(rng.randint(1, 8)):
            ms = rng.sample(ids, 2)
            if rng.random() < 0.15:
                ms.append(rng.choice([x for x in ids if x not in ms]))
            lines.append(_fuzz_line(f"L{k}", ms, rng.random() < 0.4))
        if rng.random() < 0.35 and len(lines) >= 2:
            m["offpage_connectors"] = [{"id": "X1", "text": ""}, {"id": "X2", "text": ""}]
            l1, l2 = rng.sample(lines, 2)
            l1["members"], l2["members"] = sorted(l1["members"] + ["X1"]), sorted(l2["members"] + ["X2"])
            m["offpage_pairs"] = [{"id": "P1", "a": "X1", "b": "X2", "sheet_a": "0", "sheet_b": "1"}]
        return m, lines, ids
    ids, insts, kinds = [], [], {}
    for li in range(rng.randint(2, 4)):
        v = rng.choice("TFPL")
        for suf in ["T", "IC", "V"] + (["Y"] if rng.random() < 0.3 else []) + (["V"] if rng.random() < 0.2 else []):
            iid = f"{v}{suf}{li + 1}_{len(ids)}"
            ids.append(iid)
            insts.append(inst(iid, f"{v}{suf} {li + 1}", rng.choice("01")))
            kinds.setdefault(suf, []).append(iid)
    m = model(insts)
    T, C, V, Y = (kinds.get(k, []) for k in ("T", "IC", "V", "Y"))
    pool = []
    for c in C:
        if rng.random() < 0.8:
            pool.append([rng.choice(T), c])
        if rng.random() < 0.8:
            pool.append([c, rng.choice(V + Y)])
    pool += [[y, rng.choice(V)] for y in Y]
    pool += [rng.sample(C, 2) if len(C) > 1 else rng.sample(ids, 2) for _ in range(rng.randint(1, 3))]
    pool += [rng.sample(ids, rng.choice([2, 2, 3])) for _ in range(rng.randint(0, 2))]
    if rng.random() < 0.3 and len(V) > 1:
        pool.append([rng.choice(C)] + rng.sample(V, 2))
    lines = []
    for k, ms in enumerate(pool):
        r = rng.random()
        lines.append(_fuzz_line(f"L{k}", ms, r < 0.35, 2 if r < 0.1 else 1))
    for p in range(rng.choice([0, 1, 1, 2])):
        if len(lines) < 2:
            break
        a, b = f"X{2 * p}", f"X{2 * p + 1}"
        m["offpage_connectors"] += [{"id": a, "text": ""}, {"id": b, "text": ""}]
        l1, l2 = rng.sample(lines, 2)
        if rng.random() < 0.3:  # one line cut in two at the sheet edge
            l1 = rng.choice(lines)
            ms = l1["members"]
            l1["members"] = sorted(ms[:1] + [a])
            l2 = _fuzz_line(f"L{len(lines)}", ms[1:] + [b], rng.random() < 0.4)
            lines.append(l2)
        else:
            l1["members"], l2["members"] = sorted(l1["members"] + [a]), sorted(l2["members"] + [b])
        m["offpage_pairs"].append({"id": f"P{p}", "a": a, "b": b, "sheet_a": "0", "sheet_b": "1"})
    return m, lines, ids


def _fuzz_promoted(mod, m, lines, co):
    """Merged lines an independent channel confirms, computed here from the channels themselves (signal_networks,
    signal_conditions and _channels), not from the assembly's own bookkeeping: a network that passes every condition
    and that a channel corroborates promotes every merged line in it."""
    cand = mod.candidates(m)
    role = {k: v["role"] for k, v in cand.items()}
    out = set()
    for net in mod.signal_networks(m, lines):
        ms = [x for x in net["members"] if x in cand]
        merged = [x["id"] for x in net["lines"] if x.get("merged_through_crossing")]
        if merged and len(ms) >= 2 and not mod.signal_conditions(net, cand, role) and mod._channels(net, ms, cand, co)[0]:
            out.update(merged)
    return out


def loop_fuzz(mod, seed, n_base=900, n_rich=1100, cap=24):
    """([defect], readings checked) for `mod` (a loop_assembly module). For every model: each strict relation of the
    full assembly must hold in every reading of each unconfirmed merged line (an undirected one keeps its pair), and
    each confirmed loop at tier traced must stay confirmed with at least its measurements and final elements. At
    most `cap` readings per model, sampled with the same seeded generator."""
    import itertools
    rng = random.Random(seed)
    key = lambda r: (r["type"], r["from"], r["to"], r["direction"])  # noqa: E731
    defects, n = [], 0
    for it in range(n_base + n_rich):
        m, lines, ids = _fuzz_model(rng, it >= n_base)
        co = None
        if rng.random() < 0.3:
            co = {"crossing_answers": {c["key"]: {"verdict": rng.choice(["two_lines", "continues"]), "confidence": 0.95}
                                       for x in lines if x.get("merged_through_crossing") for c in x["crossings"]
                                       if rng.random() < 0.7},
                  "assert_enabled": rng.random() < 0.5}
            if rng.random() < 0.3:
                co["reader_pairs"] = {frozenset(rng.sample(ids, 2)) for _ in range(3)}
        full = mod.assemble(m, lines, corroboration=co)
        strict = [r for r in full["relations"] if r["confidence"] in mod.STRICT_TIERS]
        traced = [lp for lp in full["loops"] if lp["tier"] == "traced" and lp["status"] == "confirmed"]
        prom = _fuzz_promoted(mod, m, lines, co)
        fixed = [{k: v for k, v in x.items() if k != "merged_through_crossing"} for x in lines
                 if not x.get("merged_through_crossing") or x["id"] in prom]
        open_ = [x for x in lines if x.get("merged_through_crossing") and x["id"] not in prom]
        combos = list(itertools.product(*[_readings(x) for x in open_]))
        for combo in (rng.sample(combos, cap) if len(combos) > cap else combos):
            b = mod.assemble(m, fixed + [y for part in combo for y in part])
            got = {key(r) for r in b["relations"]}
            pairs = {(r["type"], frozenset((r["from"], r["to"]))) for r in b["relations"]}
            lps = {lp["controller"]: lp for lp in b["loops"]}
            defects += [(it, "relation", key(r)) for r in strict if key(r) not in got and not (
                r["direction"] == "unknown" and (r["type"], frozenset((r["from"], r["to"]))) in pairs)]
            for lp in traced:
                o = lps.get(lp["controller"])
                if not o or o["status"] != "confirmed" or any(
                        not {x["id"] for x in lp[f]} <= {x["id"] for x in o[f]}
                        for f in ("measurements", "final_elements")):
                    defects.append((it, "loop", lp["controller"]))
            n += 1
    return defects, n


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
                 "PSV": "relief_device", "PCV": "final_element", "HS": "hand_switch", "FT": "transmitter", "PDT": "transmitter",
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
        self.assertEqual(b["relations"], [])  # a transmitter does not signal a valve: the line is for review
        self.assertEqual(b["unresolved_signal_networks"][0]["failed_conditions"], ["role_order"])
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

    def test_a_solid_instrument_line_is_never_signal_evidence(self):
        m = model([inst("A", "PT 900A"), inst("B", "PT 900B"), inst("C", "FIC 901"), inst("T", "FT 901")])
        solid = {"id": "L1", "sheet": "0", "line_kind": "instrument_line", "members": ["A", "B"], "lines": ["S0-IL001"]}
        b = la.assemble(m, [solid, {**solid, "id": "L2", "members": ["C", "T"]}])
        self.assertEqual(b["relations"], [])  # an impulse line or a shared leader, even with a controller on it
        self.assertEqual([u["members"] for u in b["unresolved_signal_networks"]], [["A", "B"], ["C", "T"]])
        self.assertTrue(all("dashed_line" in u["failed_conditions"] for u in b["unresolved_signal_networks"]))
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

    def syms(self, boxes):
        return [{"id": k, "class": "instrumentation",
                 "box": [1000 * b[0] / self.W, 1000 * b[1] / self.H, 1000 * b[2] / self.W, 1000 * b[3] / self.H]}
                for k, b in boxes.items()]

    def trace(self, img, boxes):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.png"
            cv2.imwrite(str(p), img)
            return {tuple(x["members"]) for x in la.dashed_signal_lines(p, self.syms(boxes))["lines"]
                    if len(x["members"]) >= 2 and not x.get("ambiguous_ends")}

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

    # Independent review of e1d8302 (adv_image.py cases 1, 1b and 2): regression tests.
    def test_a_controllers_input_and_output_meeting_at_its_box_stay_two_lines(self):
        for y_in, x_out in ((315, 380), (322, 378)):
            boxes = {}

            def draw(img):
                boxes["T"] = self.bubble(img, 100, y_in)
                boxes["C"] = self.bubble(img, 400, 300)
                boxes["V"] = self.bubble(img, 400, 520)
                self.dashed(img, [(125, y_in), (375, y_in)])
                self.dashed(img, [(x_out, 325), (x_out, 495)])
            got = self.trace(self.sheet(draw), boxes)
            self.assertNotIn(("T", "V"), got)  # a line never skips the bubble it ends on
            self.assertEqual(got, {("C", "T"), ("C", "V")})

    def test_an_end_between_two_bubbles_attaches_to_neither_and_is_listed(self):
        boxes = {}

        def draw(img):
            boxes["T"] = self.bubble(img, 100, 300)
            boxes["C1"] = self.bubble(img, 400, 275)
            boxes["C2"] = self.bubble(img, 400, 325)
            self.dashed(img, [(125, 300), (375, 300)])
        img = self.sheet(draw)
        self.assertEqual(self.trace(img, boxes), set())
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.png"
            cv2.imwrite(str(p), img)
            r = la.dashed_signal_lines(p, self.syms(boxes))
        self.assertEqual([x.get("ambiguous_ends") for x in r["lines"]], [[["C1", "C2"]]])

    def test_moving_the_whole_drawing_changes_nothing(self):
        def drawing(dx, dy):
            boxes = {}

            def draw(img):
                boxes["T"] = self.bubble(img, 100 + dx, 100 + dy)
                boxes["C"] = self.bubble(img, 400 + dx, 100 + dy)
                boxes["V"] = self.bubble(img, 400 + dx, 400 + dy)
                self.dashed(img, [(125 + dx, 100 + dy), (375 + dx, 100 + dy)])
                self.dashed(img, [(400 + dx, 125 + dy), (400 + dx, 375 + dy)])
                boxes["X"] = self.bubble(img, 700 + dx, 100 + dy)  # a bubble near no line end
            return self.trace(self.sheet(draw), boxes)
        base = drawing(0, 0)
        self.assertEqual(base, {("C", "T"), ("C", "V")})
        for dx, dy in ((37, 11), (150, 120), (5, 160)):
            self.assertEqual(drawing(dx, dy), base, (dx, dy))

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


class ReviewFindings(unittest.TestCase):
    """Regression tests for the independent review of e1d8302 (adv_assembly.py)."""

    def test_a_branching_line_sends_only_to_the_next_role(self):
        m = model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", "FV 1")])
        b = la.assemble(m, [line("a", ["T", "C", "V"])])
        self.assertEqual(b["relations"], [])  # never T -> V
        self.assertEqual(b["unresolved_signal_networks"][0]["members"], ["C", "T", "V"])
        split = la.assemble(model([inst("C", "PIC 2"), inst("V1", "PV 2A"), inst("V2", "PV 2B")]),
                            [line("b", ["C", "V1", "V2"])])
        self.assertEqual(rel(split, "signal_to"), {("C", "V1"), ("C", "V2")})  # split range stays

    def test_a_very_short_line_between_two_stacked_controllers_is_still_a_cascade(self):
        m = model([inst("T1", "TT 109"), inst("C1", "TIC 109"), inst("T2", "TT 121"), inst("C2", "TIC 121"),
                   inst("V", "TV 121")])
        short = {**line("s", ["C1", "C2"]), "dashes": 2}  # TE revision D draws TIC 109 -> TIC 121 this way
        b = la.assemble(m, [line("a", ["T1", "C1"]), short, line("c", ["T2", "C2"]), line("d", ["C2", "V"])])
        self.assertEqual(rel(b, "sets_point_of"), {("C1", "C2")})

    def test_a_line_between_items_with_no_loop_role_is_not_a_signal(self):
        m = model([inst("A", "MOV 1651", instrument_kind="operated valve"),
                   inst("B", "MOV 1652", instrument_kind="operated valve")])
        b = la.assemble(m, [line("a", ["A", "B"])])
        self.assertEqual(b["relations"], [])
        self.assertEqual(len(b["unresolved_signal_networks"]), 1)

    def test_a_dashed_line_between_two_items_of_one_role_is_not_a_signal(self):
        # OPEN100 sheet 3 (claude reading) read one MOV 1651 twice, joined by a 3-dash line; MOV now has no ISA role,
        # so the same shape is kept here with a valve that has one
        for where, tags in (("line_items", ("XV 1651", "XV 1651")), ("instruments", ("FT 90", "PT 91"))):
            m = model([])
            m[where] = [inst("A", tags[0]), inst("B", tags[1])]
            b = la.assemble(m, [line("a", ["A", "B"])])
            self.assertEqual(b["relations"], [], tags)
            self.assertEqual(len(b["unresolved_signal_networks"]), 1, tags)

    def test_a_solid_line_that_skips_a_role_is_not_a_signal(self):
        m = model([inst("T", "ZT 70"), inst("V", "XV 70")])
        solid = {"id": "S", "sheet": "0", "line_kind": "instrument_line", "members": ["T", "V"], "lines": ["x"]}
        self.assertEqual(la.assemble(m, [solid])["relations"], [])

    def test_the_same_loop_number_in_two_units_without_a_prefix(self):
        m = model([inst("U1T", "FT 101", "0"), inst("U1C", "FIC 101", "0"), inst("U1V", "FV 101", "0"),
                   inst("U2T", "FT 101", "1"), inst("U2C", "FIC 101", "1"), inst("U2V", "FV 101", "1")])
        b = la.assemble(m, [line("a", ["U1T", "U1C"]), line("b", ["U1C", "U1V"]),
                            line("c", ["U2T", "U2C"], "1"), line("d", ["U2C", "U2V"], "1")])
        ids = [lp["id"] for lp in b["loops"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([lp["tag_grouping_refuted"] for lp in b["loops"]], [[], []])
        self.assertEqual(b["conflicts"], [])
        cross = la.assemble(m, [line("a", ["U1T", "U2C"]), line("d", ["U2C", "U2V"], "1")])
        r = next(r for r in cross["relations"] if r["from"] == "U1T")
        self.assertEqual(r["confidence"], "traced")  # not the same-loop tier across units
        self.assertIn("loop_identity", {c["kind"] for c in cross["conflicts"]})

    def test_the_sheet_system_code_scopes_a_loop_number_without_a_prefix(self):
        m = model([inst("A", "FIC 5", "0", system="SYS-0"), inst("B", "FV 5", "1", system="SYS-1")])
        m["systems"] = [{"id": "SYS-0", "system_code": "FWS"}, {"id": "SYS-1", "system_code": "MSS"}]
        c = la.candidates(m)
        self.assertNotEqual(c["A"]["loop_identity"], c["B"]["loop_identity"])

    def test_relief_valves_hand_switches_and_odd_letter_orders(self):
        self.assertEqual(la.role_of("PSV"), "relief_device")
        self.assertEqual(la.role_of("TSV"), "relief_device")
        self.assertEqual(la.role_of("PRV"), "relief_device")
        self.assertEqual(la.role_of("HS"), "hand_switch")
        self.assertIsNone(la.role_of("LVC"))
        m = model([inst("P", "PSV 60"), inst("C", "PIC 60"), inst("T", "PT 60")])
        b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "P"])])
        self.assertEqual(rel(b, "controls"), set())
        m = model([inst("H", "HS 50"), inst("C", "HIC 50"), inst("V", "HV 50")])
        b = la.assemble(m, [line("a", ["H", "C"]), line("b", ["C", "V"])])
        self.assertNotEqual(loop(b, "C")["status"], "confirmed")
        c = la.candidates(model([inst("X", "LVC 7")]))
        self.assertIn("letters_not_isa_order", c["X"])

    def test_an_inferred_cascade_direction_has_its_own_tier_and_a_tag_veto(self):
        m = model([inst("AT", "AT 10"), inst("A", "AIC 10"), inst("FT", "FT 12"), inst("F", "FIC 12"),
                   inst("FV", "FV 12")])
        b = la.assemble(m, [line("a", ["AT", "A"]), line("b", ["A", "F"]), line("e", ["FT", "F"]),
                            line("f", ["F", "FV"])])
        sp = next(r for r in b["relations"] if r["type"] == "sets_point_of")
        self.assertEqual((sp["from"], sp["to"], sp["confidence"]), ("A", "F", "traced_direction_inferred"))
        # the would-be outer controller has an untraced final element of its own loop number: no direction
        m = model([inst("T", "FT 3"), inst("C", "FIC 3"), inst("V", "FV 3"), inst("T2", "FT 4"), inst("C2", "FIC 4"),
                   inst("V2", "FV 4")])
        b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "V"]), line("c", ["C", "C2"]),
                            line("d", ["T2", "C2"])])
        self.assertEqual(rel(b, "sets_point_of"), set())

    def test_every_line_at_a_paired_connector_joins(self):
        m = model([inst("T", "FT 401"), inst("C", "FIC 401"), inst("V", "FV 401", sheet="1")],
                  connectors=[{"id": "OP0", "text": "TO FV 401"}, {"id": "OP1", "text": "FROM FIC 401"}],
                  pairs=[{"id": "XP-001", "a": "OP0", "b": "OP1", "sheet_a": "0", "sheet_b": "1", "method": "x"}])
        b = la.assemble(m, [line("L0", ["T", "OP0"]), line("L1", ["T", "C"]), line("L2", ["C", "OP0"]),
                            line("L3", ["OP1", "V"], "1")])
        self.assertNotIn(("T", "V"), rel(b, "signal_to"))
        self.assertTrue(any(set(u["members"]) == {"T", "C", "V"} for u in b["unresolved_signal_networks"]))

    def test_an_ambiguous_line_end_leaves_its_network_unresolved(self):
        m = model([inst("T", "FT 9"), inst("C", "FIC 9")])
        x = {**line("a", ["T", "C"]), "ambiguous_ends": [["C", "C2"]]}
        b = la.assemble(m, [x])
        self.assertEqual(b["relations"], [])
        self.assertEqual(len(b["unresolved_signal_networks"]), 1)


    def test_the_bundle_keeps_a_traced_lines_ambiguous_ends(self):
        # the tracer's ambiguous_ends must reach the assembly through the intake path, not stop at the tracer
        import line_layers as ll
        syms = {"0": {k: {"asset": k, "box": [0, 0, 1, 1], "class": "instrumentation"} for k in ("T", "C", "V1", "V2")}}
        traced = {"lines": [{"members": ["C", "T"], "dashes": 5, "ambiguous_ends": [["V1", "V2"]],
                             "box_0_1000": [1.0, 1.0, 2.0, 2.0]},
                            {"members": ["V1"], "dashes": 5, "ambiguous_ends": [["C", "T"]],
                             "box_0_1000": [3.0, 3.0, 4.0, 4.0]}]}
        old = ll._sheet_symbols, la.dashed_signal_lines
        ll._sheet_symbols, la.dashed_signal_lines = (lambda m: syms), (lambda *a, **k: traced)
        try:
            lines = la.sheet_signal_lines({"instruments": []}, ".")
        finally:
            ll._sheet_symbols, la.dashed_signal_lines = old
        self.assertEqual([x.get("ambiguous_ends") for x in lines], [[["V1", "V2"]], [["C", "T"]]])
        m = model([inst("T", "FT 9"), inst("C", "FIC 9"), inst("V1", "FV 9"), inst("V2", "FV 9B")])
        self.assertEqual(la.assemble(m, lines)["relations"], [])


class ReReview(unittest.TestCase):
    """The second independent review's drawings and models (fixtures adv.py, adv2.py, adv3.py), kept as permanent
    tests. The false ones asserted wrong relations at the top tier before the positive list; the true ones must
    still confirm. Each relation is asserted only when every signal_conditions() condition holds."""
    D = DashedLines()
    W, H = 1000, 600

    def image(self, draw, tags, flip=None):
        img, boxes = np.full((self.H, self.W), 255, np.uint8), {}
        draw(img, boxes)
        if flip == "h":
            img = img[:, ::-1].copy()
            boxes = {k: [self.W - b[2], b[1], self.W - b[0], b[3]] for k, b in boxes.items()}
        if flip == "v":
            img = img[::-1, :].copy()
            boxes = {k: [b[0], self.H - b[3], b[2], self.H - b[1]] for k, b in boxes.items()}
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.png"
            cv2.imwrite(str(p), img)
            r = la.dashed_signal_lines(p, self.D.syms(boxes))
        lines = [{"id": f"L{i}", "sheet": "0", "line_kind": "dashed_signal_line", **x} for i, x in enumerate(r["lines"])]
        return la.assemble(model([inst(k, v) for k, v in tags.items()]), lines)

    def bub(self, img, boxes, k, x, y):
        boxes[k] = self.D.bubble(img, x, y)

    def dsh(self, img, pts, **k):
        self.D.dashed(img, pts, **k)

    def assert_false_case_unresolved(self, b, *pairs):
        got = {(r["from"], r["to"]) for r in b["relations"]} | {(r["to"], r["from"]) for r in b["relations"]}
        for pair in pairs:
            self.assertNotIn(pair, got)

    # ---- false relations the review found: now unresolved
    def test_open_case_two_dashed_lines_ending_at_a_pipe_from_either_side_stay_apart(self):
        for gap in (4, 10):
            def draw(img, b):
                self.bub(img, b, "C", 400, 100)
                self.bub(img, b, "D", 400, 500)
                cv2.line(img, (50, 300), (950, 300), 0, 4)
                self.dsh(img, [(400, 125), (400, 300 - gap)])
                self.dsh(img, [(400, 300 + gap), (400, 475)])
            b = self.image(draw, {"C": "FIC 10", "D": "FV 11"})
            self.assertEqual(b["relations"], [], gap)

    def test_open_case_does_not_confirm_a_loop_through_a_pipe(self):
        def draw(img, b):
            self.bub(img, b, "T", 100, 100)
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "D", 400, 500)
            cv2.line(img, (50, 300), (950, 300), 0, 4)
            self.dsh(img, [(125, 100), (375, 100)])
            self.dsh(img, [(400, 125), (400, 296)])
            self.dsh(img, [(400, 304), (400, 475)])
        b = self.image(draw, {"T": "FT 10", "C": "FIC 10", "D": "FV 10"})
        self.assertEqual(rel(b, "controls"), set())
        self.assert_false_case_unresolved(b, ("C", "D"))
        self.assertEqual(loop(b, "C")["status"], "partly_confirmed")  # the measurement is still traced

    def test_a_dashed_line_crossing_a_pipe_in_step_is_still_one_line(self):
        def draw(img, b):
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "V", 400, 500)
            self.dsh(img, [(400, 125), (400, 475)])
            cv2.line(img, (50, 300), (950, 300), 0, 4)  # the pipe drawn over the signal line
        b = self.image(draw, {"C": "FIC 12", "V": "FV 12"})
        self.assertEqual(rel(b, "signal_to"), {("C", "V")})

    def test_one_stroke_between_stacked_controllers_is_not_a_cascade(self):
        def draw(img, b):
            self.bub(img, b, "A", 400, 100)
            self.bub(img, b, "B", 400, 170)
            cv2.line(img, (400, 127), (400, 143), 0, 2)
            self.bub(img, b, "TA", 100, 100)
            self.dsh(img, [(125, 100), (375, 100)])
            self.bub(img, b, "VB", 700, 170)
            self.dsh(img, [(425, 170), (675, 170)])
        b = self.image(draw, {"A": "TIC 50", "B": "FIC 51", "TA": "TT 50", "VB": "FV 51"})
        self.assertEqual(rel(b, "sets_point_of"), set())
        self.assert_false_case_unresolved(b, ("A", "B"))
        self.assertIn(["A", "B"], [u["members"] for u in b["unresolved_signal_networks"]])
        m = model([inst("T1", "TT 50"), inst("A", "TIC 50"), inst("T2", "FT 51"), inst("B", "FIC 51"),
                   inst("V", "FV 51")])
        b = la.assemble(m, [line("a", ["T1", "A"]), {**line("s", ["A", "B"]), "dashes": 1}, line("c", ["T2", "B"]),
                            line("d", ["B", "V"])])
        self.assertEqual(rel(b, "sets_point_of"), set())
        self.assertEqual(loop(b, "A")["status"], "partly_confirmed")

    def test_a_thick_broken_process_line_is_not_a_signal(self):
        for tags in ({"C": "PIC 71", "V": "PV 72"}, {"C": "FT 70", "V": "FV 70"}):
            def draw(img, b):
                self.bub(img, b, "C", 100, 300)
                self.bub(img, b, "V", 700, 300)
                for x in range(125, 675, 17):
                    cv2.line(img, (x, 300), (x + 13, 300), 0, 4)
            b = self.image(draw, tags)
            self.assertEqual(b["relations"], [], tags)
            self.assertIn("thin_stroke", b["unresolved_signal_networks"][0]["failed_conditions"])

    def test_position_switches_on_an_on_off_valve_are_switches_not_a_controller(self):
        self.assertEqual(la.role_of("ZSC"), "switch")
        self.assertEqual(la.role_of("ZSO"), "switch")
        self.assertEqual(la.role_of("PSC"), "switch")
        m = model([inst("O", "ZSO 7"), inst("C", "ZSC 7"), inst("V", "XV 7")])
        b = la.assemble(m, [{**line("a", ["O", "C"]), "dashes": 2}, line("b", ["C", "V"])])
        self.assertEqual(b["relations"], [])
        self.assertEqual(b["loops"], [])

        def draw(img, b):
            self.bub(img, b, "ZO", 300, 150)
            self.bub(img, b, "ZC", 300, 220)
            cv2.line(img, (300, 177), (300, 193), 0, 2)
            self.bub(img, b, "XV", 600, 220)
            self.dsh(img, [(325, 220), (575, 220)])
            self.bub(img, b, "HS", 600, 450)
            self.dsh(img, [(600, 425), (600, 245)])
        b = self.image(draw, {"ZO": "ZSO 101", "ZC": "ZSC 101", "XV": "XV 101", "HS": "HS 101"})
        self.assertEqual(b["relations"], [])

    def test_off_page_text_naming_other_instruments_does_not_join_a_loop(self):
        def m3(text_a, text_b):
            return model([inst("T", "FT 401"), inst("C", "FIC 401"), inst("V", "LV 777", sheet="1")],
                         connectors=[{"id": "O0", "text": text_a}, {"id": "O1", "text": text_b}],
                         pairs=[{"id": "XP", "a": "O0", "b": "O1", "sheet_a": "0", "sheet_b": "1", "method": "x",
                                 "text_a": text_a, "text_b": text_b}])
        lines = [line("a", ["T", "C"]), line("b", ["C", "O0"]), line("c", ["O1", "V"], "1")]
        b = la.assemble(m3("TO FV 401", "FROM LIC 777"), lines)
        self.assertEqual(rel(b, "controls"), set())
        self.assert_false_case_unresolved(b, ("C", "V"))
        bad = next(u for u in b["unresolved_signal_networks"] if "V" in u["members"])
        self.assertEqual(bad["failed_conditions"], ["connector_text_agrees", "connector_text_agrees"])
        b = la.assemble(m3("SIG PID 2 / TO LV 777", "FROM FIC 401"), lines)  # the texts agree with the lines
        self.assertEqual(rel(b, "controls"), {("C", "V")})
        b = la.assemble(m3("SIG PID 2", "SIG PID 1"), lines)  # no ISA tag named: the pair alone decides
        self.assertEqual(rel(b, "controls"), {("C", "V")})

    def test_a_relief_valve_or_a_plant_coded_valve_on_a_controller_line_is_not_a_signal(self):
        for item in (inst("P", "PSV 80"), inst("P", "MOV 81", instrument_kind="operated valve"),
                     inst("P", "TW 82")):
            b = la.assemble(model([inst("C", "PIC 80"), item]), [line("a", ["C", "P"])])
            self.assertEqual(b["relations"], [], item["tag"])
            self.assertEqual(b["unresolved_signal_networks"][0]["failed_conditions"], ["known_roles"])
        b = la.assemble(model([inst("H", "HS 82"), inst("V", "HV 82")]), [line("a", ["H", "V"])])
        self.assertEqual(b["relations"], [])

    # ---- true loops: still confirmed
    def test_a_transmitter_through_an_indicator_to_a_controller_confirms(self):
        m = model([inst("T", "LT 7"), inst("I", "LI 7"), inst("C", "LIC 7"), inst("V", "LV 7")])
        b = la.assemble(m, [line("a", ["T", "I"]), line("b", ["I", "C"]), line("c", ["C", "V"])])
        self.assertEqual(loop(b, "C")["status"], "confirmed")
        self.assertEqual(rel(b, "controls"), {("C", "V")})

    def test_an_i_p_relay_on_the_way_to_the_valve_is_traced_not_refuted(self):
        m = model([inst("T", "FT 8"), inst("C", "FIC 8"), inst("Y", "FY 8"), inst("V", "FV 8")])
        b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "Y"]), line("c", ["Y", "V"])])
        lp = loop(b, "C")
        self.assertEqual(lp["status"], "confirmed")
        self.assertEqual(lp["final_elements"][0]["via"], ["Y"])
        self.assertEqual(lp["tag_grouping_refuted"], [])
        self.assertEqual(b["conflicts"], [])

    def test_frc_fcv_ait_and_a_suffixed_tic_confirm(self):
        for tags in (("FT 12", "FRC 12", "FCV 12"), ("AIT 14", "AIC 14", "AV 14"), ("TT 13", "TIC 13A", "TV 13"),
                     ("PDT 15", "PDIC 15", "PDV 15"), ("FT 16", "FFIC 16", "FV 16")):
            m = model([inst("T", tags[0]), inst("C", tags[1]), inst("V", tags[2])])
            b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "V"])])
            self.assertEqual(loop(b, "C")["status"], "confirmed", tags)
            self.assertEqual(rel(b, "controls"), {("C", "V")}, tags)

    def test_mirrored_straight_and_dog_leg_loops_confirm(self):
        def straight(img, b):
            self.bub(img, b, "T", 100, 100)
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "V", 400, 400)
            self.dsh(img, [(125, 100), (375, 100)])
            self.dsh(img, [(400, 125), (400, 375)])

        def dogleg(img, b):
            self.bub(img, b, "T", 100, 500)
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "V", 800, 400)
            self.dsh(img, [(100, 475), (100, 100), (375, 100)])
            self.dsh(img, [(425, 100), (800, 100), (800, 375)])
        for draw in (straight, dogleg):
            for flip in (None, "h", "v"):
                b = self.image(draw, {"T": "FT 60", "C": "FIC 60", "V": "FV 60"}, flip)
                self.assertEqual(rel(b, "controls"), {("C", "V")}, (draw.__name__, flip))
                self.assertEqual(loop(b, "C")["status"], "confirmed", (draw.__name__, flip))

    # ---- known partial cases (unresolved is the accepted answer; listed in the README)
    def test_known_partial_redundant_transmitters_and_a_low_select_stay_unresolved(self):
        m = model([inst("A", "FT 3A"), inst("B", "FT 3B"), inst("C", "FIC 3"), inst("V", "FV 3")])
        b = la.assemble(m, [line("a", ["A", "B", "C"]), line("b", ["C", "V"])])
        self.assertEqual(rel(b, "controls"), set())
        self.assertIn(["A", "B", "C"], [u["members"] for u in b["unresolved_signal_networks"]])
        m = model([inst("T1", "PT 4"), inst("P", "PIC 4"), inst("T2", "FT 4"), inst("F", "FIC 4"), inst("Y", "FY 4"),
                   inst("V", "FV 4")])
        b = la.assemble(m, [line("a", ["T1", "P"]), line("b", ["T2", "F"]), line("c", ["P", "F", "Y"]),
                            line("d", ["Y", "V"])])
        self.assertEqual(rel(b, "controls"), set())
        self.assertIn(["F", "P", "Y"], [u["members"] for u in b["unresolved_signal_networks"]])


class ThirdReview(unittest.TestCase):
    """The third independent review's fixtures (a_inphase.py, b2.py, b_merge.py, attacks.py, letters.py), kept as
    permanent tests. A line the tracer joined through a crossing may support signal_to at tier traced at most, never
    controls, sets_point_of or a confirmed loop."""
    R = ReReview()

    def image(self, draw, tags):
        return self.R.image(draw, tags)

    def bub(self, img, b, k, x, y):
        self.R.bub(img, b, k, x, y)

    def dsh(self, img, pts):
        self.R.dsh(img, pts)

    def loop_relations(self, b):
        return {(r["type"], r["from"], r["to"]) for r in b["relations"] if r["type"] in ("controls", "sets_point_of")}

    def test_random_placements_of_two_lines_ending_at_a_pipe_assert_nothing_strictly_traced(self):
        # Two lines drawn to a pipe and in step by chance are, to within a pixel, one line crossing it: inherently
        # ambiguous, read as a qualified reader reads them, at tier traced_through_crossing with the question attached.
        # A defect would be a loop relation at a strictly traced tier: there must be none.
        rng = random.Random(1)
        defects, ambiguous = 0, 0
        for _ in range(60):
            yc, yd = 100 + rng.randint(0, 30), 500 - rng.randint(0, 30)

            def draw(img, b):
                self.bub(img, b, "C", 400, yc)
                self.bub(img, b, "D", 400, yd)
                cv2.line(img, (50, 300), (950, 300), 0, 2)
                self.bub(img, b, "TT", 150, yc)
                self.dsh(img, [(175, yc), (375, yc)])
                self.dsh(img, [(400, yc + 25), (400, 299)])
                self.dsh(img, [(400, yd - 25), (400, 301)])
            b = self.image(draw, {"C": "TIC 20", "TT": "TT 20", "D": "TV 20"})
            for r in b["relations"]:
                if {r["from"], r["to"]} == {"C", "D"} or r["type"] in ("controls", "sets_point_of"):
                    if r["confidence"] in la.STRICT_TIERS:
                        defects += 1
                    else:
                        ambiguous += r["type"] == "controls"
                        self.assertTrue(r["merged_through_crossing"])
                        self.assertEqual(r["review_question"], la.CROSSING_QUESTION)
        self.assertEqual(defects, 0)
        self.assertGreater(ambiguous, 0)  # the sweep does reach the chance merge it guards against

    def test_lines_ending_on_a_dashed_line_from_either_side_confirm_nothing(self):
        def lines_to_a_dashed(img, b):
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "TT", 150, 100)
            self.dsh(img, [(175, 100), (375, 100)])
            self.bub(img, b, "V", 400, 500)
            self.bub(img, b, "L", 100, 300)
            self.bub(img, b, "R", 700, 300)
            self.dsh(img, [(125, 300), (675, 300)])
            self.dsh(img, [(400, 125), (400, 294)])
            self.dsh(img, [(400, 306), (400, 475)])
        for v in ("FV 99", "TV 20"):
            b = self.image(lines_to_a_dashed, {"C": "TIC 20", "TT": "TT 20", "V": v, "L": "FT 30", "R": "FIC 30"})
            self.assertEqual(self.loop_relations(b), set(), v)
            self.assertFalse({r["from"] for r in b["relations"] if r["to"] in ("C", "V")} & {"L", "C"}, v)

        def false_cascade(img, b):
            self.bub(img, b, "C", 400, 100)
            self.bub(img, b, "TT", 150, 100)
            self.dsh(img, [(175, 100), (375, 100)])
            self.bub(img, b, "D", 400, 500)
            self.bub(img, b, "FV", 650, 500)
            self.dsh(img, [(425, 500), (625, 500)])
            self.bub(img, b, "FT", 150, 500)
            self.dsh(img, [(175, 500), (375, 500)])
            self.bub(img, b, "L", 60, 300)
            self.bub(img, b, "R", 900, 300)
            self.dsh(img, [(85, 300), (875, 300)])
            self.dsh(img, [(400, 125), (400, 294)])
            self.dsh(img, [(400, 306), (400, 475)])
        b = self.image(false_cascade, {"C": "TIC 20", "TT": "TT 20", "D": "FIC 21", "FT": "FT 21", "FV": "FV 21",
                                       "L": "FT 30", "R": "FIC 30"})
        self.assertEqual(self.loop_relations(b), {("controls", "D", "FV")})
        self.assertFalse([r for r in b["relations"] if r["from"] == "L" and r["to"] in ("C", "D")])

    def test_a_merged_line_asserts_only_at_its_own_tier(self):
        m = model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", "FV 1"), inst("T2", "TT 2"), inst("C2", "TIC 2")])
        merged = {**line("b", ["C", "V"]), "merged_through_crossing": True}
        b = la.assemble(m, [line("a", ["T", "C"]), merged, line("c", ["T2", "C2"]),
                            {**line("d", ["C2", "C"]), "merged_through_crossing": True}])
        self.assertEqual(self.loop_relations(b), {("controls", "C", "V"), ("sets_point_of", "C2", "C")})
        for r in b["relations"]:
            resting = (r["from"], r["to"]) in {("C", "V"), ("C2", "C")} or r["type"] != "signal_to"
            self.assertEqual(r["confidence"] == "traced_through_crossing", resting, r)
        self.assertEqual(loop(b, "C")["tier"], "traced_through_crossing")
        self.assertEqual(loop(b, "C2")["tier"], "traced_through_crossing")
        self.assertEqual(b["counts"]["relations_by_tier"]["traced_through_crossing"], 4)
        b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "V"])])  # the same lines unmerged
        self.assertEqual(next(r for r in b["relations"] if r["type"] == "controls")["confidence"], "traced_and_grouped")
        self.assertEqual(loop(b, "C")["tier"], "traced")

    def test_a_transmitter_misread_as_a_controller_is_not_an_outer_loop(self):
        for tags in ({"T": "FC 101", "C": "FIC 101", "V": "FV 101"}, {"T": "FT 101", "C": "FIC 101", "V": "FC 101"}):
            def basic(img, b):
                self.bub(img, b, "T", 100, 100)
                self.bub(img, b, "C", 400, 100)
                self.bub(img, b, "V", 400, 400)
                self.dsh(img, [(125, 100), (375, 100)])
                self.dsh(img, [(400, 125), (400, 375)])
            b = self.image(basic, tags)
            self.assertEqual([r for r in b["relations"] if r["type"] == "sets_point_of"], [], tags)
        m = model([inst("T1", "TT 1"), inst("C1", "TIC 1"), inst("T2", "FT 2"), inst("C2", "FIC 2"),
                   inst("V", "FV 2")])  # a real cascade: the outer controller has its own measurement
        b = la.assemble(m, [line("a", ["T1", "C1"]), line("b", ["C1", "C2"]), line("c", ["T2", "C2"]),
                            line("d", ["C2", "V"])])
        self.assertEqual(rel(b, "sets_point_of"), {("C1", "C2")})
        b = la.assemble(m, [line("b", ["C1", "C2"]), line("c", ["T2", "C2"]), line("d", ["C2", "V"])])
        self.assertEqual(rel(b, "sets_point_of"), set())

    def test_a_line_drawn_through_bubbles_it_does_not_end_at_is_unresolved(self):
        def through(img, b):
            self.bub(img, b, "T", 60, 300)
            self.bub(img, b, "X", 300, 300)
            self.bub(img, b, "C", 550, 300)
            self.bub(img, b, "V", 900, 300)
            self.dsh(img, [(85, 300), (875, 300)])
            self.bub(img, b, "CT", 550, 100)
            self.dsh(img, [(550, 125), (550, 275)])
        b = self.image(through, {"T": "FT 7", "X": "LI 8", "C": "FIC 9", "V": "FV 9", "CT": "FT 9"})
        self.assertEqual(rel(b, "signal_to"), {("CT", "C")})
        self.assertEqual(rel(b, "controls"), set())
        self.assertTrue(any("not_through_a_symbol" in u["failed_conditions"] for u in b["unresolved_signal_networks"]))

        for shift in range(0, 19, 3):  # a controller's input and output drawn in one row still confirm
            def drawn(img, b, s=shift):
                self.bub(img, b, "T", 100, 300)
                self.bub(img, b, "C", 450, 300)
                self.bub(img, b, "V", 800, 300)
                self.dsh(img, [(125, 300), (425, 300)])
                self.dsh(img, [(475 + s, 300), (775, 300)])
            b = self.image(drawn, {"T": "FT 1", "C": "FIC 1", "V": "FV 1"})
            self.assertEqual(rel(b, "controls"), {("C", "V")}, shift)

    def test_letters_out_of_isa_order_and_shut_down_valves(self):
        self.assertEqual(la.role_of("ESDV"), "final_element")
        self.assertEqual(la.role_of("SDV"), "final_element")
        for letters in ("FCI", "FTC", "FIV", "LVC"):
            self.assertIsNone(la.role_of(letters), letters)
            self.assertTrue(la.letters_out_of_order(letters), letters)
        self.assertEqual(la.role_of("FICA"), "controller")
        self.assertEqual(la.role_of("PDIT"), "transmitter")
        m = model([inst("E", "FE 12"), inst("T", "FT 12"), inst("C", "FIC 12"), inst("V", "FV 12")])
        b = la.assemble(m, [line("a", ["E", "T"]), line("b", ["T", "C"]), line("c", ["C", "V"])])
        self.assertIn(("E", "T"), rel(b, "signal_to"))  # a primary element to its transmitter
        self.assertEqual(loop(b, "C")["status"], "confirmed")


class MergedLineChannels(unittest.TestCase):
    """A line joined through a crossing (in step) is read as a qualified reader reads it, one line crossing, and
    asserted at its own tier traced_through_crossing with the crossing question attached. An independent channel
    promotes it (the reader's own link, or the blind crossing evaluator when its scorecard enabled it); a confident
    "two lines" from an enabled evaluator demotes it to review. Tag agreement plays no part. Every loop the assembly
    cannot prove is a review candidate, never hidden."""

    def m(self):
        return model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", "FV 1")])

    def lines(self):
        merged = {**line("b", ["C", "V"]), "merged_through_crossing": True,
                  "crossings": [{"key": "img:10,20", "at_0_1000": [10.0, 20.0], "crosses": "pipe"}]}
        return [line("a", ["T", "C"]), merged]

    def loop_rel(self, b):
        return {(r["type"], r["from"], r["to"]) for r in b["relations"] if r["type"] in ("controls", "sets_point_of")}

    def test_without_a_channel_a_merged_line_asserts_at_its_own_tier_and_tags_play_no_part(self):
        for valve in ("FV 1", "FV 2"):  # the same loop number at both ends, or not: no difference
            m = model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", valve)])
            b = la.assemble(m, self.lines())
            r = next(r for r in b["relations"] if r["type"] == "controls")
            self.assertEqual((r["confidence"], r["review_question"]), ("traced_through_crossing", la.CROSSING_QUESTION))
            ev = next(e for e in r["evidence"] if e["kind"] == "through_crossing")
            self.assertEqual(ev["tag_agreement"], valve == "FV 1")  # recorded for the reviewer only
            self.assertEqual(b["candidate_loops"], [])

    def test_a_confident_continues_from_an_enabled_judge_promotes(self):
        yes = {"verdict": "continues", "confidence": 0.9}
        b = la.assemble(self.m(), self.lines(), corroboration={"crossing_answers": {"img:10,20": yes},
                                                                "assert_enabled": True})
        self.assertEqual(self.loop_rel(b), {("controls", "C", "V")})
        r = next(r for r in b["relations"] if r["type"] == "signal_to" and r["to"] == "V")
        self.assertEqual((r["corroborated_by"], r["confidence"]), (["crossing_judge"], "traced_and_grouped"))
        self.assertEqual(loop(b, "C")["tier"], "traced")
        self.assertEqual(b["candidate_loops"], [])

    def test_a_confident_two_lines_from_an_enabled_judge_demotes_and_anything_else_leaves_the_tier(self):
        no = {"verdict": "two_lines", "confidence": 0.9}
        b = la.assemble(self.m(), self.lines(), corroboration={"crossing_answers": {"img:10,20": no},
                                                                "assert_enabled": True})
        self.assertEqual(self.loop_rel(b), set())
        self.assertEqual(b["unresolved_signal_networks"][0]["failed_conditions"], ["demoted_by_crossing_judge"])
        self.assertEqual([c["kind"] for c in b["candidate_loops"]], ["merged_line_needs_review"])
        for answer, enabled in ((no, False), ({"verdict": "continues", "confidence": 0.9}, False),
                                ({"verdict": "continues", "confidence": 0.7}, True),
                                ({"verdict": "cannot_tell", "confidence": 0.9}, True)):
            b = la.assemble(self.m(), self.lines(), corroboration={"crossing_answers": {"img:10,20": answer},
                                                                    "assert_enabled": enabled})
            r = next(r for r in b["relations"] if r["type"] == "controls")
            self.assertEqual(r["confidence"], "traced_through_crossing", (answer, enabled))

    def test_the_readers_own_link_promotes(self):
        b = la.assemble(self.m(), self.lines(), corroboration={"reader_pairs": {frozenset(("C", "V"))}})
        r = next(r for r in b["relations"] if r["type"] == "controls")
        self.assertEqual(r["confidence"], "traced_and_grouped")
        b = la.assemble(self.m(), self.lines(), corroboration={"reader_pairs": {frozenset(("T", "V"))}})
        r = next(r for r in b["relations"] if r["type"] == "controls")
        self.assertEqual(r["confidence"], "traced_through_crossing")

    def test_a_loop_resting_on_its_tag_group_is_a_candidate(self):
        b = la.assemble(self.m(), [])
        self.assertEqual([(c["controller"], c["kind"]) for c in b["candidate_loops"]], [("C", "grouped_by_tag")])
        self.assertEqual(b["relations"], [])

    def test_the_scorer_reports_strict_asserted_and_candidate_levels_apart(self):
        m = self.m()
        m["control_loops"] = la.assemble(m, self.lines())
        tagged = {k: la.compact(v["tag"]) for k, v in la.candidates(m).items()}
        self.assertEqual(ls.asserted(m)["final"], {(tagged["C"], tagged["V"])})
        self.assertEqual(ls.asserted(m, strict=True)["final"], set())
        self.assertEqual(ls.asserted(m, strict=True)["loops"], [])
        m2 = self.m()
        m2["control_loops"] = la.assemble(m2, [line("a", ["T", "C"])])  # the output is not traced
        self.assertEqual(ls.asserted(m2)["final"], set())
        self.assertEqual(ls.with_candidates(m2)["final"], {(tagged["C"], tagged["V"])})  # a grouped_by_tag candidate


@unittest.skipUnless(HAVE_CV2, "needs OpenCV and NumPy")
class CrossingEvaluator(unittest.TestCase):
    """The blind second evaluator (scripts/crossing_question.py), with the model call replaced."""

    def test_the_panel_shows_only_the_two_lines_never_a_tag_or_symbol(self):
        import crossing_question as cq
        img = np.full((600, 1000), 255, np.uint8)
        cv2.circle(img, (440, 260), 24, 0, 2)  # a bubble beside the crossing
        cv2.putText(img, "FIC", (420, 262), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)
        cv2.line(img, (50, 300), (950, 300), 0, 2)
        DashedLines().dashed(img, [(400, 120), (400, 480)])
        panel = cq.crop_panel(img, {"at_px": [400, 300], "axis": "v", "side_px": 50.0, "stroke_px": 6}, 1)
        body = panel[40:, 40:]  # the number sits in the top-left corner
        colours = {tuple(int(v) for v in px) for px in body.reshape(-1, 3)}
        self.assertLessEqual(colours, {(255, 255, 255), cq.BLUE, cq.GREEN, (160, 160, 160)})
        self.assertIn(cq.BLUE, colours)
        self.assertIn(cq.GREEN, colours)

    def test_answers_record_the_judge_and_unanswered_items_go_to_review(self):
        import crossing_question as cq
        img = np.full((600, 1000), 255, np.uint8)
        items = [{"key": f"k{n}", "gray": img, "at_px": [400, 300], "axis": "v", "side_px": 50.0, "stroke_px": 6}
                 for n in range(3)]
        reply = {"text": json.dumps({"items": [{"n": 1, "verdict": "continues", "confidence": 0.95, "reason": "r"}]}),
                 "model": "judge-x"}
        answers, calls = cq.ask(items, "claude", reader_model="claude-opus-5-5", call=lambda png, prompt: reply)
        self.assertTrue(cq.supports(answers["k0"]))
        self.assertFalse(cq.supports(answers["k1"]))  # no answer: review
        self.assertEqual(answers["k1"]["verdict"], "cannot_tell")
        self.assertEqual(answers["k0"]["judge_model"], "judge-x")
        self.assertTrue(answers["k0"]["same_model_as_reader"])  # flagged: weaker independence
        self.assertEqual(len(calls), 1)

    def test_the_scorecard_gate_refuses_a_judge_that_supports_a_false_merge(self):
        import crossing_question as cq
        always = lambda png, prompt: {"text": json.dumps({"items": [  # noqa: E731
            {"n": n, "verdict": "continues", "confidence": 0.9, "reason": "r"} for n in range(1, 9)]})}
        items = cq.sweep_merges(n=12) + cq.controls()
        self.assertTrue(any(it["truth"] == "two_lines" for it in items))
        answers, _ = cq.ask(items, call=always)
        run = {"score": cq.score_run(items, answers)}
        self.assertFalse(cq.enabled([run]))  # it says "continues" to everything, so it may assert nothing


class FourthReview(unittest.TestCase):
    """The fourth independent review's fixtures (loops-rereview4: ted_dep.py, c18_sweep.py, tier_attacks.py): a derived
    relation or loop takes the weakest tier of every input that made it possible (_tier_by_derivation)."""

    def strict(self, b, typ):
        return {(r["from"], r["to"]) for r in b["relations"] if r["type"] == typ and r["confidence"] in la.STRICT_TIERS}

    def weak(self, lid, ms):
        return {**line(lid, ms), "merged_through_crossing": True,
                "crossings": [{"key": f"sha:{lid}", "at_0_1000": [1.0, 1.0], "crosses": "pipe"}]}

    def test_a_cascade_whose_direction_rests_on_a_crossing_line_takes_its_tier(self):
        m = model([inst("T1", "TT 1"), inst("C1", "TIC 1"), inst("C2", "FIC 2"), inst("V2", "FV 2")])
        b = la.assemble(m, [line("a", ["T1", "C1"]), line("b", ["C1", "C2"]), self.weak("w", ["C2", "V2"])])
        self.assertEqual(rel(b, "sets_point_of"), {("C1", "C2")})
        self.assertEqual(self.strict(b, "sets_point_of"), set())  # direction needed C2's crossing-tier valve line
        self.assertEqual(self.strict(b, "signal_to"), {("T1", "C1")})  # C1-C2 is directed only through the crossing
        self.assertEqual(loop(b, "C1")["tier"], "traced_through_crossing")
        self.assertEqual(b["counts"]["loops_by_tier"]["strict"]["sets_point_of"], 0)

    def test_an_outer_measurement_that_exists_only_through_a_crossing_line_takes_its_tier(self):
        # FE 5 read as a controller's measurement only through a weak line (FT read as FC: FC 5 has no real measurement)
        m = model([inst("E5", "FE 5"), inst("C1", "FC 5"), inst("C2", "FIC 6"), inst("V6", "FV 6"), inst("T6", "FT 6")])
        base = [line("b", ["C1", "C2"]), line("c", ["C2", "V6"]), line("d", ["T6", "C2"])]
        self.assertEqual(rel(la.assemble(m, base), "sets_point_of"), set())
        b = la.assemble(m, base + [self.weak("w", ["E5", "C1"])])
        self.assertEqual(self.strict(b, "sets_point_of"), set())
        self.assertEqual(self.strict(b, "controls"), {("C2", "V6")})  # C2's own loop is strictly traced
        self.assertEqual(loop(b, "C2")["tier"], "traced")

    def test_a_loop_at_tier_traced_never_rests_on_crossing_support(self):
        m = model([inst("T1", "TT 1"), inst("C1", "TIC 1"), inst("C2", "FIC 2"), inst("V2", "FV 2"), inst("T2", "FT 2")])
        for extra in ([], [self.weak("w", ["C2", "V2"])], [self.weak("w", ["T2", "C2"])]):
            b = la.assemble(m, [line("a", ["T1", "C1"]), line("b", ["C1", "C2"]), line("c", ["T2", "C2"]),
                                line("d", ["C2", "V2"])][:3 + (not extra)] + extra)
            weak = {(r["from"], r["to"]) for r in b["relations"] if r["confidence"] not in la.STRICT_TIERS}
            for lp in b["loops"]:
                if lp["tier"] == "traced":
                    c = lp["controller"]
                    self.assertFalse({(x["id"], c) for x in lp["measurements"]} & weak, extra)
                    self.assertFalse({(c, x["id"]) for x in lp["final_elements"] + lp["sets_point_of"]} & weak, extra)

    @unittest.skipUnless(HAVE_CV2, "needs OpenCV and NumPy")
    def test_a_valve_line_ending_at_a_pipe_in_step_by_chance_gives_no_strict_cascade(self):
        # c18_sweep.py: the inner controller's valve line is drawn to a pipe from both sides; at offsets 7-11 the two
        # halves are in step by chance and merge, and the cascade direction rests on that merge
        R = ReReview()
        for off in range(7, 12):
            def draw(img, b, off=off):
                R.bub(img, b, "T1", 100, 100)
                R.bub(img, b, "C1", 400, 100)
                R.bub(img, b, "C2", 700, 100)
                R.bub(img, b, "V2", 700, 500)
                R.dsh(img, [(125, 100), (375, 100)])
                R.dsh(img, [(425, 100), (675, 100)])
                cv2.line(img, (500, 300), (900, 300), 0, 2)
                R.dsh(img, [(700, 125), (700, 294)])
                R.dsh(img, [(700, 306 + off), (700, 475)])
            b = R.image(draw, {"T1": "TT 1", "C1": "TIC 1", "C2": "FIC 2", "V2": "FV 2"})
            self.assertEqual(self.strict(b, "sets_point_of"), set(), off)
            self.assertEqual(self.strict(b, "controls"), set(), off)

    def test_two_lines_joined_at_one_pixel_are_two_questions(self):
        h = {"at_px": [500, 300], "axis": "h", "gap_px": [490, 510]}
        v = {"at_px": [500, 300], "axis": "v", "gap_px": [290, 310]}
        self.assertNotEqual(la.crossing_key("sha", h), la.crossing_key("sha", v))

    def test_the_evaluator_gate_is_recomputed_at_import_never_read_from_the_answers_file(self):
        import crossing_question as cq
        prompt = hashlib.sha256(cq.PROMPT_FILE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as t:
            card = Path(t) / "card.json"
            bad_run = {"score": {"false_merges_sweep": {"supported_continues": 1}, "fixtures_false":
                                 {"supported_continues": 0}, "controls": {}, "true_crossings_te_d":
                                 {"supported_continues": 3}, "fixtures_true": {"supported_continues": 0}}}
            card.write_text(json.dumps({"prompt_sha256": prompt, "assert_enabled": True, "runs": [bad_run]}))
            ans = Path(t) / "answers.json"
            ans.write_text(json.dumps({"prompt_sha256": prompt, "assert_enabled": True, "scorecard": str(card),
                                       "answers": {}}))
            self.assertFalse(la.load_crossing_answers(ans)["assert_enabled"])  # the file says True; the runs say no
            good_run = json.loads(json.dumps(bad_run))
            good_run["score"]["false_merges_sweep"]["supported_continues"] = 0
            card.write_text(json.dumps({"prompt_sha256": prompt, "runs": [good_run]}))
            self.assertTrue(la.load_crossing_answers(ans)["assert_enabled"])
            card.write_text(json.dumps({"prompt_sha256": "other", "runs": [good_run]}))
            self.assertFalse(la.load_crossing_answers(ans)["assert_enabled"])  # another prompt's scorecard
            ans.write_text(json.dumps({"prompt_sha256": prompt, "scorecard": str(Path(t) / "gone.json"), "answers": {}}))
            self.assertFalse(la.load_crossing_answers(ans)["assert_enabled"])

    @unittest.skipUnless(HAVE_CV2 and (Path(__file__).resolve().parent.parent / "data" / "te_pid").is_dir(),
                         "needs OpenCV and the TE sheets")
    def test_te_revision_d_strict_view_holds_only_strictly_traced_loops(self):
        # ted_dep.py: TIC 109 -> TIC 121 is a cascade whose direction rests on TV 121's line across a pipe
        import crossing_question as cq
        with tempfile.TemporaryDirectory() as t:
            bundle = cq.build_te_d_bundle(Path(t))
            model_ = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
        cl = model_["control_loops"]
        tag = {k: la.compact(v["tag"]) for k, v in la.candidates(model_).items()}
        strict = ls.score(ls.asserted(model_, strict=True), ls.key_loops())["loops"]
        self.assertEqual((strict["valve_loops"], strict["cascades"], strict["precision"]), ("7/11", "3/8", 1.0))
        self.assertEqual(ls.score(ls.asserted(model_), ls.key_loops())["loops"]["recall"], 1.0)
        r = next(r for r in cl["relations"] if r["type"] == "sets_point_of" and tag[r["from"]] == "TIC109")
        self.assertEqual((tag[r["to"]], r["confidence"]), ("TIC121", "traced_through_crossing"))
        self.assertEqual(cl["counts"]["loops_by_tier"]["strict"]["confirmed_loops"], 10)


class FifthReview(unittest.TestCase):
    """The fifth independent review (loops-rereview5: offpage_poison.py, fuzz.py): the strict pass is assembled from
    the drawing's lines with every unconfirmed merged line, and the plain lines an off-page pair joins to it, removed
    before networks are formed; a cascade whose chain touches such a network is not strict."""

    def merged(self, lid, ms):
        return {**line(lid, ms), "merged_through_crossing": True,
                "crossings": [{"key": f"sha:{lid}", "at_0_1000": [1.0, 1.0], "crosses": "pipe"}]}

    def poison(self, extra):
        m = model([inst("T", "FT 5"), inst("A", "FIC 5"), inst("B", "TIC 7"), inst("V2", "TV 7"), inst("V", "PV 9"),
                   inst("Q", "LT 11")], connectors=[{"id": "X1", "text": ""}, {"id": "X2", "text": ""}],
                  pairs=[{"id": "P1", "a": "X1", "b": "X2", "sheet_a": "0", "sheet_b": "1"}])
        base = [line("L0", ["T", "A"]), line("L1", ["A", "B"]), line("L2", ["B", "V2"]), line("L3", ["A", "X1"])]
        return la.assemble(m, base + extra)

    def test_an_unresolved_merged_network_hiding_an_output_gives_no_strict_cascade(self):
        # offpage_poison.py: A's line runs off-page to X2, where a line merged through a pipe reaches PV 9 and LT 11.
        # The joined network fails role_order, so A's real output (reading 1: A -> PV 9) is hidden, and A -> B read
        # as a cascade only because A seemed to have no output.
        b = self.poison([self.merged("L4", ["V", "Q", "X2"])])
        strict = {(r["type"], r["from"], r["to"]) for r in b["relations"] if r["confidence"] in la.STRICT_TIERS}
        self.assertNotIn(("sets_point_of", "A", "B"), strict)
        self.assertNotIn(("signal_to", "A", "B"), strict)
        self.assertEqual(loop(b, "A")["tier"], "traced_through_crossing")
        u = next(u for u in b["unresolved_signal_networks"] if set(u["members"]) == {"A", "Q", "V"})
        self.assertEqual(u["review_question"], la.CROSSING_QUESTION)  # a merged line's network carries the question
        # reading 1 (two lines, V-X2 and a Q stub) is the drawing that gives A its output; no cascade there
        r1 = self.poison([line("L4", ["V", "X2"])])
        self.assertEqual(rel(r1, "controls"), {("A", "V")})
        self.assertEqual(rel(r1, "sets_point_of"), set())

    def test_a_strict_line_and_a_merged_line_on_one_pair_take_the_strict_tier(self):
        m = model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", "FV 1")])
        b = la.assemble(m, [self.merged("w", ["T", "C"]), line("a", ["T", "C"]), line("b", ["C", "V"])])
        r = next(r for r in b["relations"] if r["type"] == "signal_to" and (r["from"], r["to"]) == ("T", "C"))
        self.assertEqual(r["confidence"], "traced_and_grouped")
        self.assertEqual(len(loop(b, "C")["measurements"]), 1)  # one member, not two

    def test_final_elements_are_listed_once(self):
        m = model([inst("T", "FT 1"), inst("C", "FIC 1"), inst("V", "FV 1")])
        b = la.assemble(m, [line("a", ["T", "C"]), line("b", ["C", "V"]), line("c", ["C", "V"])])
        self.assertEqual([x["id"] for x in loop(b, "C")["final_elements"]], ["V"])

    def test_seeded_fuzz_no_strict_relation_or_traced_loop_depends_on_a_merged_line(self):
        # loop_fuzz (module level): loop-shaped models plus random ones, every set partition of each merged line, and
        # the loop-shape check. Seed 3 is the recorded RED: on 524bdbe's loop_assembly.py the same body finds
        # defects (A410); here it must find none.
        defects, n = loop_fuzz(la, seed=3)
        self.assertGreater(n, 15000)
        self.assertEqual(defects[:5], [])

    def test_a_taint_that_cannot_move_a_cascade_leaves_it_strict(self):
        # sixth review: the merged line only gives the INNER controller (TIC 2, which has its valve) a measurement, so
        # no reading of it can change which controller is outer; TIC 3 -> TIC 2 stays strict
        m = model([inst("I0", "TIC 3"), inst("I1", "FIC 3"), inst("I2", "PT 1"), inst("I3", "FV 1"),
                   inst("I4", "TIC 2"), inst("I5", "TT 2")])
        b = la.assemble(m, [line("a", ["I0", "I1", "I2"]), line("b", ["I0", "I4"]), line("c", ["I3", "I4"]),
                            line("d", ["I0", "I5"]), self.merged("w", ["I2", "I4"])])
        tier = {(r["type"], r["from"], r["to"]): r["confidence"] for r in b["relations"]}
        self.assertEqual(tier[("sets_point_of", "I0", "I4")], "traced_direction_inferred")
        self.assertEqual(tier[("signal_to", "I0", "I4")], "traced_direction_inferred")
        self.assertEqual(tier[("signal_to", "I2", "I4")], "traced_through_crossing")
        # a merged line from the outer controller to a valve could move the depths: never strict
        b = la.assemble(m, [line("a", ["I0", "I1", "I2"]), line("b", ["I0", "I4"]), line("c", ["I3", "I4"]),
                            line("d", ["I0", "I5"]), self.merged("w", ["I0", "I3"])])
        tier = {(r["type"], r["from"], r["to"]): r["confidence"] for r in b["relations"]}
        self.assertNotIn(tier.get(("sets_point_of", "I0", "I4")), la.STRICT_TIERS)


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
