"""scripts/context_map.py: the context-map-1 reader/writer and its converters (standard library only).

Converts the committed OPEN100 sheet 0 outputs (the one-map twin-graph-2 graph and the twin-graph-1 export) and every
other committed twin-graph file, validates each map, checks that `connects` is read by its layer and never as
piped_to, that twin-graph-1 comes back unchanged, and that the validator refuses broken maps.
"""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import context_basis
import context_map as cm
import graph_export

ROOT = Path(__file__).resolve().parents[1]
OPEN100_MAP = ROOT / "examples" / "drawing-to-map" / "expected" / "map" / "graph.json"  # twin-graph-2, sheet 0
OPEN100_TG1 = ROOT / "examples" / "graph-export" / "sheet0_graph.json"                   # twin-graph-1, sheet 0
PASTEURIZER = ROOT / "examples" / "one-map" / "expected" / "pasteurizer" / "graph.json"


def committed_graphs(schema):
    out = []
    for p in sorted((ROOT / "examples").rglob("*.json")):
        try:
            g = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(g, dict) and g.get("schema") == schema:
            out.append((p, g))
    return out


class OneMapToContextMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = cm.load_json(OPEN100_MAP)
        cls.map = cm.from_one_map(cls.graph)

    def test_open100_map_validates(self):
        self.assertEqual(cm.check(self.map), [])
        self.assertEqual((self.map["format"], self.map["format_version"]), ("context-map-1", cm.VERSION))

    def test_identity_status_and_provenance_carry_through(self):
        items = {i["id"]: i for i in self.map["plant"]["items"]}
        nodes = {n["id"]: n for n in self.graph["nodes"]}
        for nid, n in nodes.items():
            if n["kind"] in cm.ITEM_KINDS:
                self.assertEqual(items[nid]["status"], n["status"], nid)
        tcv = items["O100/NPP/MSS/TCV-1401"]
        self.assertEqual(tcv["scope"], "O100/NPP/MSS")
        self.assertEqual(tcv["appearances"][0]["zone"], nodes["O100/NPP/MSS/TCV-1401"]["appearances"][0]["zone"])
        sources = {s["id"]: s for s in self.map["sources"]}
        self.assertEqual(sources[tcv["appearances"][0]["source"]]["record_type"], "pid")
        run = next(r for r in self.map["plant"]["relations"] if r["id"] == "O100/NPP/MSS/@140/L-s1-s54")
        self.assertEqual((run["from"], run["to"]), ("O100/NPP/MSS/MSS-XSS-140", "O100/NPP/MSS/MSCV-XXX"))
        self.assertEqual(run["attributes"]["through"]["value"], "2 valves and 3 other in-line symbols")
        self.assertEqual(run["attributes"]["through"]["status"], "unverified")
        self.assertIn(run["attributes"]["through"]["source"], sources)
        self.assertNotIn("directed", run, "co-membership has no direction")

    def test_runs_read_as_network_membership_never_piped_to(self):
        runs = [e for e in self.graph["edges"] if e["type"] == "connects"]
        self.assertEqual(len(runs), 38)
        by_id = {r["id"]: r for r in self.map["plant"]["relations"]}
        self.assertEqual({by_id[e["id"]]["type"] for e in runs}, {"network_member"})
        self.assertNotIn("piped_to", {r["type"] for r in self.map["plant"]["relations"]})

    def test_pasteurizer_documents_records_loops_and_expectations(self):
        g = cm.load_json(PASTEURIZER)
        m = cm.from_one_map(g)
        self.assertEqual(cm.check(m), [])
        docs = {d["id"]: d for d in m["documents"]}
        haccp = docs["S1/DOC/HACCP-PLAN-P1"]
        self.assertEqual(haccp["based_on"], [{"id": "S1/DOC/PID-P1-PAST1-01", "revision": "C"}])
        self.assertIn("S1/P1/PAST1", haccp["covers"])
        self.assertTrue(any(mt.get("match") == "glossary" and mt["term"] == "HTST" for mt in haccp["mentions"]))
        self.assertEqual(sum(len(r) for r in m["records"].values()), sum(len(r) for r in g["records"].values()))
        loop = next(lp for lp in m["plant"]["loops"] if lp["controller"] == "S1/P1/PAST1/TIC-2207")
        self.assertEqual(loop["outcome"], "located_and_consistent")
        self.assertEqual(loop["measurements"], ["S1/P1/PAST1/TT-2207"])
        sources = {s["id"]: s for s in m["sources"]}
        self.assertEqual(sources[loop["source"]]["record_type"], "loop_list")
        self.assertEqual(len(m["expectations"]["results"]), len(g["expectations"]["results"]))
        # a measurement's controls edge reads as signal_to; the controller's controls stays controls
        rel = {(r["from"], r["to"], r["type"]) for r in m["plant"]["relations"]}
        self.assertIn(("S1/P1/PAST1/FIC-2203", "S1/P1/PAST1/P-101", "controls"), rel)

    def test_every_committed_one_map_graph_converts_to_a_valid_map_and_twin_graph_1_view(self):
        graphs = committed_graphs("twin-graph-2")
        self.assertGreater(len(graphs), 10)
        for p, g in graphs:
            m = cm.from_one_map(g)
            self.assertEqual(cm.check(m), [], p)
            view = cm.to_twin_graph_1(m)
            self.assertEqual(graph_export.problems(view), [], p)
            # nothing silently dropped: every edge is a relation, a document link or counted with its reason
            report = m["extensions"][cm.REPORT]
            kept = sum(report["edges_kept_out"].values())
            self.assertEqual(len(m["plant"]["relations"]) + report["document_links"] + kept, len(g["edges"]), p)


class TwinGraph1RoundTrip(unittest.TestCase):
    def test_open100_sheet0_round_trip_is_exact(self):
        g = cm.load_json(OPEN100_TG1)
        m = cm.from_twin_graph_1(g, site="O100")
        self.assertEqual(cm.check(m), [])
        self.assertEqual(cm.to_twin_graph_1(m), g)
        kinds = {r["type"] for r in m["plant"]["relations"]}
        self.assertEqual(kinds, {"contains", "network_member", "piped_to", "actuated_by", "nozzle_of"})
        # the 345 network pairs and 174 on_network links are membership; the 92 pipe segments stay piped_to
        self.assertEqual(sum(r["type"] == "network_member" for r in m["plant"]["relations"]), 345 + 174)
        self.assertEqual(sum(r["type"] == "piped_to" for r in m["plant"]["relations"]), 92)
        report = m["extensions"][cm.REPORT]
        self.assertEqual(sum(report["edges_kept_out"].values()), 20)  # drawn instrument lines: no relation claimed
        self.assertEqual(report["statuses_read_as_unverified"], {"extracted": 445})

    def test_every_committed_twin_graph_1_file_round_trips(self):
        graphs = committed_graphs("twin-graph-1")
        self.assertGreater(len(graphs), 20)
        for p, g in graphs:
            m = cm.from_twin_graph_1(g)
            self.assertEqual(cm.check(m), [], p)
            self.assertEqual(cm.to_twin_graph_1(m), g, p)

    def test_hand_built_streams_interlocks_and_limits_are_kept_out_with_reasons(self):
        g = cm.load_json(ROOT / "examples" / "graph-export" / "bayer_graph.json")
        m = cm.from_twin_graph_1(g)
        report = m["extensions"][cm.REPORT]
        rel = cm.relations_doc()
        key = f"connects/stream: {rel['twin_graph_1_not_mapped']['connects/stream']}"
        self.assertEqual(report["edges_kept_out"][key],
                         sum(1 for e in g["edges"] if e["type"] == "connects"))
        self.assertTrue(any(k.startswith("interlock:") for k in report["nodes_kept_out"]))
        self.assertTrue(any(k.startswith("limit:") for k in report["nodes_kept_out"]))
        self.assertNotIn("network_member", {r["type"] for r in m["plant"]["relations"]})


class EdgeTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rel = cm.relations_doc()
        cls.names = {r["name"] for r in cls.rel["relations"]}

    def test_connects_is_read_by_layer(self):
        er = cm.edge_relation
        for fmt, layer, want in (("twin-graph-1", "network_pair", "network_member"),
                                 ("twin-graph-1", "offpage_pair", "references"),
                                 ("twin-graph-1", "stream", None),
                                 ("twin-graph-1", "no_such_layer", None),
                                 ("twin-graph-2", "stream", "network_member"),
                                 ("twin-graph-2", "offpage_pair", "references")):
            self.assertEqual(er({"type": "connects", "layer": layer}, None, fmt, self.rel), want, (fmt, layer))
        self.assertEqual(er({"type": "on_network"}, "equipment", "twin-graph-1", self.rel), "network_member")
        self.assertEqual(er({"type": "piped_to"}, "junction", "twin-graph-1", self.rel), "piped_to")
        self.assertEqual(er({"type": "controls"}, "instrument", "twin-graph-1", self.rel), "signal_to")
        self.assertEqual(er({"type": "controls"}, "controller", "twin-graph-1", self.rel), "controls")
        self.assertEqual(er({"type": "signal_line"}, "instrument", "twin-graph-2", self.rel), "signal_to")

    def test_no_table_reads_co_membership_as_pipe_adjacency(self):
        for key in ("twin_graph_1_edges_by_layer", "twin_graph_2_edges_by_layer"):
            self.assertNotIn("piped_to", self.rel[key]["connects"].values(), key)
        self.assertNotEqual(self.rel["twin_graph_2_edges"]["connects"], "piped_to")
        self.assertEqual(self.rel["engineering_context_basis_1_relations"]["network_member"], "network_member")

    def test_tables_name_only_frozen_relations_and_every_gap_has_a_reason(self):
        for key in ("twin_graph_1_edges", "twin_graph_2_edges", "engineering_context_basis_1_relations"):
            for edge, r in self.rel[key].items():
                self.assertTrue(r is None or r in self.names, (key, edge, r))
        for table in ("twin_graph_1_edges_by_layer", "twin_graph_2_edges_by_layer"):
            for edge, layers in self.rel[table].items():
                for layer, r in layers.items():
                    self.assertTrue(r is None or r in self.names, (table, edge, layer))
        self.assertEqual(set(self.rel["twin_graph_1_edges"]), set(graph_export.EDGE_TYPES))
        self.assertEqual(set(self.rel["twin_graph_1_edges_by_layer"]["connects"]), set(graph_export.CONNECTS_LAYERS))
        reasons = self.rel["twin_graph_1_not_mapped"]
        for edge, r in self.rel["twin_graph_1_edges"].items():
            if r is None and edge != "connects":
                self.assertIn(edge, reasons)
        for layer, r in self.rel["twin_graph_1_edges_by_layer"]["connects"].items():
            if r is None:
                self.assertIn(f"connects/{layer}", reasons)

    def test_basis_table_covers_every_basis_relation(self):
        table = self.rel["engineering_context_basis_1_relations"]
        self.assertEqual(set(table), set(context_basis.RELATIONS))
        self.assertTrue(set(self.rel["engineering_context_basis_1_reversed"]) <= set(table))
        self.assertEqual((table["reads"], table["commands"]), ("signal_to", "controls"))
        for pred, r in table.items():
            if r is None:
                self.assertIn(pred, self.rel["engineering_context_basis_1_not_mapped"])

    def test_network_member_does_not_collide_with_loop_membership(self):
        rels = {r["name"]: r for r in self.rel["relations"]}
        self.assertEqual(rels["member_of"]["range"], ["@loop"])
        self.assertIn("@network", rels["network_member"]["range"])
        self.assertNotIn("@loop", rels["network_member"]["range"])
        self.assertIn("@network", self.rel["pseudo_classes"])


class Validator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = cm.from_one_map(cm.load_json(OPEN100_MAP))

    def test_refuses_broken_maps(self):
        cases = (
            (lambda m: m["plant"]["relations"][0].update(type="connects"), "not a context-map relation name"),
            (lambda m: m["plant"]["relations"][0].update(to="O100/NPP/MSS/NOT-ON-MAP"), "relation end not on the map"),
            (lambda m: m["plant"]["relations"][0].update(source="nowhere"), "undeclared source"),
            (lambda m: m["plant"]["items"][0].pop("scope"), "item without scope"),
            (lambda m: m["plant"]["items"][0].update(scope="O100/NOWHERE"), "item in an unknown scope"),
            (lambda m: m["plant"]["items"].append(copy.deepcopy(m["plant"]["items"][0])), "duplicate item id"),
            (lambda m: m["plant"]["items"][0].update(status="extracted"), "status outside the format"),
            (lambda m: m["plant"]["items"][0].update(tag="A/B"), "slash in a tag"),
            (lambda m: m.update(format_version="2.0.0"), "a major version is context-map-2"),
            (lambda m: m["plant"]["relations"][0].update(attributes={"x": {"value": {"nested": 1}}}),
             "a fact's value must be plain"),
        )
        self.assertEqual(cm.check(self.good), [])
        for mutate, why in cases:
            bad = copy.deepcopy(self.good)
            mutate(bad)
            self.assertTrue(cm.check(bad), why)

    def test_cli_round_trip_and_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cm.main(["from-one-map", str(OPEN100_MAP), "--out", str(out)]), 0)
                self.assertEqual(cm.main(["validate", str(out)]), 0)
            self.assertEqual(cm.check(cm.load_json(out)), [])
            bad = cm.load_json(out)
            bad["plant"]["relations"][0]["type"] = "connects"
            (Path(tmp) / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cm.main(["validate", str(Path(tmp) / "bad.json")]), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(cm.main(["from-one-map", str(OPEN100_TG1), "--out", str(Path(tmp) / "x.json")]), 2)
            self.assertFalse((Path(tmp) / "x.json").exists())

    def test_public_files_name_no_private_product(self):
        private = "change" + "pilot"  # spelled in parts so this file passes its own check
        for p in (Path(cm.__file__), Path(__file__), cm.RELATIONS_PATH, cm.SCHEMA_PATH):
            self.assertNotIn(private, p.read_text(encoding="utf-8").lower(), p.name)


if __name__ == "__main__":
    unittest.main()
