"""The pid-to-kg graph.json adapter (scripts/reader_external_kg.py), checked the way the reader slot asks.

  - the answer key, written as a pid-to-kg graph (symbols as items, the key's connector/crossing/arrow nodes as pipe
    segments), converts through the adapter to a perfect score with the frozen scorer: review load 0, every F1 1.0
    (docs/PLUG_IN_A_READER.md: "convert the answer key through it and expect a perfect score")
  - the class rules follow extraction/prompt_v2.md; a tee, a sheet, a loop and an area boundary are not symbols
  - derived edges (FEEDS, inherited MEASURES) and cross-sheet flows never become drawn links; links pass through
    pipe segments only, never through another item
  - flow pairs follow FLOWS_TO only, and say "inferred" when any edge on the way was
  - the converted file passes the intake's validator, and a graph that is not pid-to-kg's is refused
Stdlib only, offline, no model.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import import_site_drawing as intake  # noqa: E402
import reader_external_kg as rk  # noqa: E402
import score_pid2graph as sc  # noqa: E402

OPEN100 = ROOT / "data" / "external" / "pid2graph" / "PID2Graph" / "Complete" / "PID2Graph OPEN100"
TE_A = ROOT / "data" / "te_pid" / "rev-a"
TYPE_OF = {"tank": ("Equipment", "tank"), "pump": ("Equipment", "centrifugal_pump"), "valve": ("Component", "gate_valve"),
           "instrumentation": ("Instrument", None), "inlet/outlet": ("OffPageConnector", None),
           "general": ("Component", "strainer")}


def key_as_graph(graphml, png):
    """The key as a pid-to-kg graph: each scored key symbol an item with its normalized box, every pass-through node
    a pipe segment, every key edge a drawn FLOWS_TO edge."""
    w, h = sc.png_size(png)
    nodes, adj = sc.load_key(graphml, w, h)
    sheet = "SHEET:P01"
    out = [{"id": sheet, "type": "Sheet", "label": "key", "sheets": [sheet], "attributes": {"page": 1}}]
    for nid, n in nodes.items():
        if n["class"] in sc.SCORED:
            t, kind = TYPE_OF[n["class"]]
            out.append({"id": f"K-{nid}", "type": t, "label": nid, "kind": kind, "sheets": [sheet], "confidence": 1.0,
                        "provenance": [{"sheet": sheet, "page": 1, "local_id": nid,
                                        "bbox": [v / 1000 for v in n["box"]]}]})
        elif n["class"] in sc.PASS_THROUGH:
            out.append({"id": f"K-{nid}", "type": "PipeSegment", "label": nid, "sheets": [sheet]})
    keep = {n["id"] for n in out}
    edges, seen = [], set()
    for a, bs in adj.items():
        for b in bs:
            pair = frozenset((a, b))
            if pair in seen or f"K-{a}" not in keep or f"K-{b}" not in keep:
                continue
            seen.add(pair)
            edges.append({"id": f"E{len(edges)}", "source": f"K-{a}", "target": f"K-{b}", "type": "FLOWS_TO",
                          "attributes": {"flow_direction": "shown"}})
    return {"schema_version": "1.0", "generator": "pid-to-kg 0.1.0", "nodes": out, "edges": edges}


def tiny_graph():
    s = "SHEET:P01"
    box = lambda x: [{"sheet": s, "page": 1, "local_id": x, "bbox": [0.1, 0.1, 0.2, 0.2]}]  # noqa: E731
    nodes = [{"id": s, "type": "Sheet", "label": "t", "sheets": [s], "attributes": {"page": 1}},
             {"id": "TK-1", "type": "Equipment", "kind": "tank", "label": "TK-1", "tag": "TK-1", "sheets": [s], "provenance": box("TK-1")},
             {"id": "P-1", "type": "Equipment", "kind": "centrifugal_pump", "label": "P-1", "tag": "P-1", "sheets": [s], "provenance": box("P-1")},
             {"id": "V-1", "type": "Component", "kind": "gate_valve", "label": "V-1", "sheets": [s], "provenance": box("V-1")},
             {"id": "T-1", "type": "Component", "kind": "tee", "label": "tee", "sheets": [s], "provenance": box("T-1")},
             {"id": "FI-1", "type": "Instrument", "label": "FI-1", "tag": "FI-1", "sheets": [s], "provenance": box("FI-1")},
             {"id": "FT-9", "type": "Instrument", "label": "FT-9", "tag": "FT-9", "sheets": [s], "provenance": [{"sheet": s, "page": 1}]},
             {"id": "BOUNDARY:ROOM", "type": "Boundary", "label": "room", "sheets": [s], "attributes": {"direction": "area"},
              "provenance": box("room")},
             {"id": "LOOP:F-1", "type": "ControlLoop", "kind": "monitoring", "label": "F-1", "sheets": [s],
              "attributes": {"sensors": ["FI-1"]}},
             {"id": "S1", "type": "PipeSegment", "label": "L1", "sheets": [s]},
             {"id": "S2", "type": "PipeSegment", "label": "L1", "sheets": [s]},
             {"id": "S3", "type": "PipeSegment", "label": "L2", "sheets": [s]}]
    e = lambda a, b, t="FLOWS_TO", **k: {"source": a, "target": b, "type": t, **k}  # noqa: E731
    edges = [e("TK-1", "S1", attributes={"flow_direction": "shown"}), e("S1", "P-1", attributes={"flow_direction": "shown"}),
             e("P-1", "S2", attributes={"flow_direction": "inferred"}), e("S2", "V-1", attributes={"flow_direction": "shown"}),
             e("S2", "T-1", attributes={"flow_direction": "shown"}), e("T-1", "S3", attributes={"flow_direction": "shown"}),
             e("FI-1", "S1", "MEASURES"), e("TK-1", "V-1", "FEEDS", derived=True),
             e("FI-1", "V-1", "MEASURES", derived=True), e("TK-1", "P-1", attributes={"off_page": True})]
    return {"schema_version": "1.0", "generator": "pid-to-kg 0.1.0", "nodes": nodes, "edges": edges}


class PerfectThroughAdapter(unittest.TestCase):
    def check(self, keys, sheet):
        png, graphml = keys / f"{sheet}.png", keys / f"{sheet}.graphml"
        if not png.exists():
            self.skipTest(f"{png} not in this checkout")
        pred, report, _, _ = rk.convert(key_as_graph(graphml, png), 1, sc.png_size(png))
        r = sc.score(graphml, pred, png)
        self.assertEqual(r["review_load"]["per_100"], 0.0, report)
        for name in ("strict", "rough"):
            self.assertEqual(r[name]["classified"]["f1"], 1.0)
        self.assertEqual(r["connections"]["f1"], 1.0)

    def test_open100_sheet0_key_scores_perfect(self):
        self.check(OPEN100, "0")

    def test_te_revision_a_key_scores_perfect(self):
        self.check(TE_A, "101")


class Rules(unittest.TestCase):
    def setUp(self):
        self.pred, self.report, self.pairs, self.loops = rk.convert(tiny_graph(), 1, (1000, 1000))
        self.by = {s["id"]: s for s in self.pred["symbols"]}

    def test_classes_and_non_symbols(self):
        self.assertEqual({k: v["class"] for k, v in self.by.items()},
                         {"TK-1": "tank", "P-1": "pump", "V-1": "valve", "FI-1": "instrumentation"})
        self.assertEqual(self.report["no_box"], ["FT-9"])
        self.assertIn("Component:tee", self.report["not_symbols"])
        self.assertIn("Boundary", self.report["not_symbols"])

    def test_links_pass_pipe_and_tee_only_and_skip_derived_and_cross_sheet(self):
        links = {frozenset((c["from"], c["to"])) for c in self.pred["connections"]}
        self.assertEqual(links, {frozenset(("TK-1", "P-1")), frozenset(("TK-1", "FI-1")), frozenset(("P-1", "FI-1")),
                                 frozenset(("P-1", "V-1"))})

    def test_flow_pairs_follow_flows_to(self):
        got = {(p["from"], p["to"]): p["flow_direction"] for p in self.pairs}
        self.assertEqual(got, {("TK-1", "P-1"): "shown", ("P-1", "V-1"): "inferred"})

    def test_loops_reported_with_member_tags(self):
        self.assertEqual(self.loops[0]["sensors"], ["FI-1"])

    def test_output_is_importable(self):
        intake.validate_prediction(self.pred)

    def test_refuses_other_graphs(self):
        with self.assertRaises(ValueError):
            rk.load_graph(self._tmp({"nodes": [], "edges": []}))

    def test_printed_tags_replace_normalized(self):
        page = self._tmp({"page": 1, "instruments": [{"id": "FI-1", "tag": "FI 1"}]})
        pred, report, _, _ = rk.convert(tiny_graph(), 1, (1000, 1000), rk.printed_tags(page))
        self.assertEqual({s["id"]: s["tag"] for s in pred["symbols"]}["FI-1"], "FI 1")
        self.assertEqual(report["printed_tags_used"], 1)

    def _tmp(self, obj):
        d = Path(tempfile.mkdtemp())
        p = d / "x.json"
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p


if __name__ == "__main__":
    unittest.main()
