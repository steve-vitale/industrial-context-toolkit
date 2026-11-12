"""Reader adapter for an external knowledge-graph reader: a pid-to-kg graph.json -> the documented prediction format.

pid-to-kg (MIT, (c) the pid-to-kg contributors; repository by Scott Duncan,
https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph) is a public P&ID skill:
a model reads each sheet into a page file, and its own scripts build one process graph (graph.json, schema 1.0).
This adapter is that graph's part of the reader slot (docs/PLUG_IN_A_READER.md). It reads one sheet's items out of
graph.json, maps them onto the six scored classes, collapses the graph's pipe segments into symbol-to-symbol
connections and hands the result to scripts/reader_template.py's own conversion and the intake's validator, so a
file it writes is importable and scorable exactly like any other reader's. It changes the format only; it is a
measured comparison and a source of ideas, not a dependency of the toolkit.

Rules (fixed 2026-11-11 before any pid-to-kg output was scored; changing them is a visible commit):

  Symbols   every node with a provenance box on the selected page, one symbol per box, classed by CLASS_RULES
            below, which follow extraction/prompt_v2.md's definitions (the same ones our readers are given):
              Equipment          pumps, compressors, blowers and fans -> pump; drives, agitators, samplers and
                                 in-line static mixers -> general; every other kind -> tank
              Component          valves (every *_valve kind, backflow preventer, pressure regulator, vacuum breaker)
                                 -> valve; a pipe tee -> not a symbol (line plumbing, like a bend); any other kind,
                                 known or not -> general
              Instrument         -> instrumentation
              OffPageConnector   -> inlet/outlet
              Boundary           source or sink -> inlet/outlet; an area (a room the gas detectors watch) -> none
              PipeSegment, Sheet, Plant, ControlLoop -> not symbols
            A node without a box on the page (an instrument the graph created from a signal end only) is not a
            symbol and is listed. The box is the graph's normalized [x0, y0, x1, y1] scaled to the PNG's pixels.
  Tags      the graph's tag (normalized by its builder, e.g. "FI-101"); for an off-page connector or boundary with
            no tag, its printed name. --printed-tags PAGE_JSON substitutes the tag exactly as the reader printed it in
            its page file (matched through the provenance local_id), since the graph's normalization is not a misread.
  Links     the drawn lines only: FLOWS_TO (not derived, not cross-sheet), MEASURES (not derived) and SIGNAL_TO, with
            both ends on the page. Two symbols are connected when a path joins them through pipe segments (and tees)
            only: the same pass-through rule scripts/score_pid2graph.py applies to the key's connector nodes. A
            derived edge (FEEDS, ACTUATES, MEMBER_OF, TRIPS, an inherited MEASURES) is not a drawn line and is not
            used. Links attach to a node's first box on the page.
  Direction the same walk along FLOWS_TO only, kept in --flow-out: each ordered symbol pair (upstream, downstream)
            with the graph's flow_direction ("shown" when every edge on the path says shown, else "inferred").
            The prediction format itself is undirected; the side file is for a direction comparison.

Usage
  python scripts/reader_external_kg.py work/plant/kg/graph.json --page 1 --image sheet.png --out prediction.json \\
      [--printed-tags work/plant/extract/page_01.json] [--flow-out flow.json] [--loops-out loops.json]
Prints a JSON report of what was kept and dropped. Exit 0 written; 1 bad input (nothing written). Stdlib only.
"""
import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_site_drawing as intake  # noqa: E402
import reader_template  # noqa: E402

FORMAT = "pid-to-kg graph.json, schema 1.0"
PUMP_KINDS = {"pump", "centrifugal_pump", "positive_displacement_pump", "metering_pump", "slurry_pump", "sump_pump",
              "compressor", "blower", "fan"}
EQUIPMENT_GENERAL = {"motor", "agitator", "sampler", "static_mixer"}
VALVE_KINDS = {"backflow_preventer", "pressure_regulator", "vacuum_breaker"}
NOT_SYMBOL_COMPONENTS = {"tee"}
PASS_THROUGH = {"PipeSegment"}
DRAWN_EDGES = {"FLOWS_TO", "MEASURES", "SIGNAL_TO"}


def symbol_class(node):
    """The scored class for a graph node, or None when it is not a drawn symbol (CLASS_RULES in the docstring)."""
    t, kind = node.get("type"), (node.get("kind") or "other")
    if t == "Equipment":
        return "pump" if kind in PUMP_KINDS else "general" if kind in EQUIPMENT_GENERAL else "tank"
    if t == "Component":
        if kind in NOT_SYMBOL_COMPONENTS:
            return None
        return "valve" if kind.endswith("_valve") or kind in VALVE_KINDS else "general"
    if t == "Instrument":
        return "instrumentation"
    if t == "OffPageConnector":
        return "inlet/outlet"
    if t == "Boundary":
        return "inlet/outlet" if (node.get("attributes") or {}).get("direction") in ("source", "sink") else None
    return None


def safe_id(raw, used):
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", str(raw))[:120] or "n"
    if not sid[0].isalnum():
        sid = "n" + sid
    base, k = sid, 1
    while sid in used:
        k += 1
        sid = f"{base}_{k}"
    used.add(sid)
    return sid


def load_graph(path):
    g = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not (isinstance(g, dict) and g.get("schema_version") == "1.0" and str(g.get("generator", "")).startswith("pid-to-kg")
            and isinstance(g.get("nodes"), list) and isinstance(g.get("edges"), list)):
        raise ValueError(f"not a {FORMAT} (schema_version 1.0, generator pid-to-kg, nodes and edges)")
    return g


def printed_tags(page_file):
    """{local id: tag exactly as printed} from a pid-to-kg page extraction file."""
    page = json.loads(Path(page_file).read_text(encoding="utf-8-sig"))
    out = {}
    for group in ("equipment", "components", "instruments", "off_page_connectors", "boundaries"):
        for it in page.get(group) or []:
            if isinstance(it, dict) and it.get("id") is not None and isinstance(it.get("tag"), str) and it["tag"].strip():
                out[str(it["id"])] = it["tag"].strip()
    return out


def sheet_nodes(graph, page):
    sheets = [n["id"] for n in graph["nodes"] if n.get("type") == "Sheet" and (n.get("attributes") or {}).get("page") == page]
    if len(sheets) != 1:
        raise ValueError(f"graph has {len(sheets)} sheets for page {page}; need exactly one")
    sheet = sheets[0]
    return sheet, {n["id"]: n for n in graph["nodes"] if sheet in (n.get("sheets") or [])}


def convert(graph, page, image_px, tags_as_printed=None):
    """-> (prediction, report, flow pairs, loops). Raises ValueError on input that cannot be converted at all."""
    width, height = image_px
    sheet, nodes = sheet_nodes(graph, page)
    report = {"format": FORMAT, "sheet": sheet, "nodes_on_sheet": len(nodes), "by_class": defaultdict(int),
              "not_symbols": defaultdict(int), "no_box": [], "extra_boxes": 0, "printed_tags_used": 0}
    used, first, symbols = set(), {}, []
    for nid, n in nodes.items():
        cls = symbol_class(n)
        if cls is None:
            report["not_symbols"][f"{n.get('type')}:{n.get('kind') or ''}".rstrip(":")] += 1
            continue
        boxes = [p for p in n.get("provenance") or [] if p.get("sheet") == sheet and p.get("page") == page and p.get("bbox")]
        if not boxes:
            report["no_box"].append(nid)
            continue
        for k, p in enumerate(boxes):
            sid = safe_id(nid if k == 0 else f"{nid}.box{k + 1}", used)
            if k == 0:
                first[nid] = sid
            else:
                report["extra_boxes"] += 1
            tag = n.get("tag")
            if tags_as_printed and p.get("local_id") in tags_as_printed:
                tag = tags_as_printed[p["local_id"]]
                report["printed_tags_used"] += 1
            if not tag and n.get("type") in ("OffPageConnector", "Boundary"):
                tag = n.get("name")
            x0, y0, x1, y1 = p["bbox"]
            symbols.append({"id": sid, "type": cls, "tag": tag, "score": n.get("confidence"),
                            "box_px": [x0 * width, y0 * height, x1 * width, y1 * height]})
            report["by_class"][cls] += 1
    adj, flow_out, flow_kind = defaultdict(set), defaultdict(set), {}
    used_edges = defaultdict(int)
    for e in graph["edges"]:
        a, b, t, at = e.get("source"), e.get("target"), e.get("type"), e.get("attributes") or {}
        if t not in DRAWN_EDGES or a not in nodes or b not in nodes or e.get("derived") or at.get("off_page"):
            continue
        used_edges[t] += 1
        adj[a].add(b)
        adj[b].add(a)
        if t == "FLOWS_TO":
            flow_out[a].add(b)
            flow_kind[(a, b)] = at.get("flow_direction") or "unknown"
    passable = {nid for nid, n in nodes.items()
                if n.get("type") in PASS_THROUGH or (n.get("type") == "Component" and (n.get("kind") or "") in NOT_SYMBOL_COMPONENTS)}
    lines = set()
    for start in first:
        seen, todo = {start}, deque([start])
        while todo:
            cur = todo.popleft()
            for nxt in adj[cur]:
                if nxt in seen:
                    continue
                seen.add(nxt)
                if nxt in first:
                    lines.add(frozenset((first[start], first[nxt])))
                elif nxt in passable:
                    todo.append(nxt)
    pairs = []
    for start in first:  # directed walk along FLOWS_TO through pass-through nodes only
        seen, todo = {start}, deque([(start, ())])
        while todo:
            cur, kinds = todo.popleft()
            for nxt in sorted(flow_out[cur]):
                if nxt in seen:
                    continue
                seen.add(nxt)
                k = kinds + (flow_kind[(cur, nxt)],)
                if nxt in first:
                    pairs.append({"from": first[start], "to": first[nxt],
                                  "flow_direction": "shown" if all(x == "shown" for x in k) else "inferred"})
                elif nxt in passable:
                    todo.append((nxt, k))
    data = {"schema": reader_template.SCHEMA, "image_px": [width, height], "symbols": symbols,
            "lines": [{"from": a, "to": b} for a, b in sorted(tuple(sorted(x)) for x in lines)]}
    prediction, conv = reader_template.convert(data, [width, height])
    kept = {s["id"] for s in prediction["symbols"]}
    pairs = [p for p in pairs if p["from"] in kept and p["to"] in kept]
    loops = []
    for n in nodes.values():
        if n.get("type") != "ControlLoop":
            continue
        a = n.get("attributes") or {}
        tag = lambda ids: [graph_tag(graph, i) for i in ids]  # noqa: E731
        loops.append({"loop": n.get("label"), "kind": n.get("kind"), "variable": a.get("variable"),
                      "sensors": tag(a.get("sensors", [])), "controllers": tag(a.get("controllers", [])),
                      "final_elements": tag(a.get("final_elements", [])), "cascade_slaves": a.get("cascade_slaves", [])})
    report.update(by_class=dict(report["by_class"]), not_symbols=dict(report["not_symbols"]), drawn_edges_used=dict(used_edges),
                  conversion=conv, connections=len(prediction["connections"]), directed_pairs=len(pairs),
                  directed_pairs_shown=sum(p["flow_direction"] == "shown" for p in pairs), loops=len(loops))
    return prediction, report, pairs, loops


def graph_tag(graph, nid):
    for n in graph["nodes"]:
        if n["id"] == nid:
            return n.get("tag") or n.get("label") or nid
    return nid


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("graph", help="pid-to-kg graph.json")
    ap.add_argument("--page", type=int, default=1, help="1-based page of the sheet in the reader's PDF (default 1)")
    ap.add_argument("--image", required=True, help="the sheet PNG the scorer and intake use (gives the pixel size)")
    ap.add_argument("--out", required=True, help="prediction JSON to write")
    ap.add_argument("--printed-tags", help="the reader's page file (extract/page_NN.json): use tags as printed")
    ap.add_argument("--flow-out", help="write the directed symbol pairs here")
    ap.add_argument("--loops-out", help="write the graph's control loops (tags) here")
    a = ap.parse_args(argv)
    try:
        graph = load_graph(a.graph)
        size = intake.png_dimensions(Path(a.image).read_bytes())
        tags = printed_tags(a.printed_tags) if a.printed_tags else None
        prediction, report, pairs, loops = convert(graph, a.page, size, tags)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"reader_external_kg: {e}", file=sys.stderr)
        return 1
    write = lambda path, obj: Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n",  # noqa: E731
                                                    encoding="utf-8", newline="\n")
    write(a.out, prediction)
    if a.flow_out:
        write(a.flow_out, {"format": "directed symbol pairs from pid-to-kg FLOWS_TO", "pairs": pairs})
    if a.loops_out:
        write(a.loops_out, {"format": "pid-to-kg ControlLoop nodes, members as tags", "loops": loops})
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
