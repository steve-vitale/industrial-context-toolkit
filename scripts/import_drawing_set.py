"""Several local P&ID sheets + existing extractions -> one unverified review bundle.

The drawing-set sibling of import_site_drawing.py. It validates each sheet exactly as the one-sheet intake does,
builds one model across the set (build_twin.py), and pairs off-page connectors across sheets. It never calls a
model, scores or approves operations; the code tracing it does (line layers, flow marks, signal lines) reads only
the supplied sheet images. Input schema: site-drawing-set-1. See --help.

Cross-sheet pairing runs in two passes, each recorded on the pair as its method:
  1. build_twin.py's own in-model pass, for references written like "PID 140-1".
  2. scripts/offpage_pairing.py, the one cross-sheet rule, on the connectors pass 1 left: literal matching on the
     drawing numbers and titles supplied in the manifest, for references written any other way ("REF SHT P-204",
     "DWG 10-PI-003", "PID 140?1" with an unreadable separator). Its methods (reciprocal_supplied_numbers,
     one_way_number_plus_sheet_title, one_way_number_plus_system_code) and evidence are kept on each pair;
     equally good candidates are never decided by order and stay unpaired with the candidates named.
Every pair stays unverified and is listed in the review queue with its method.

The bundle also gets the drawn line layers (scripts/line_layers.py): pipe segments between consecutive items
(`piped_to` in the graph), instrument connections, actuator stems and junctions, re-traced from each sheet image
with the tracer's default options. This needs OpenCV and NumPy (requirements.txt). Without them, or when the links
can't be re-traced (an extraction written by hand rather than traced), the bundle is still written and
meta.line_layers_status says why the layers were skipped. --no-line-layers turns them off.

With the line layers, each pipe segment gets a flow direction only where the drawing shows one, read by
scripts/flow_direction.py's detectors (unchanged): an arrowhead on the segment, an off-page flag's point, a pump's
top discharge and side suction port, or continuity through an in-line valve from one of those. A directed segment
has from -> to in the flow direction, direction "forward" and direction_evidence (basis, confidence, the evidence
kinds and where each was found). A segment with no such evidence stays exactly as the line layers wrote it:
undirected. Flow through a valve with exactly two pipe segments is continuous, so each maximal run of segments
joined through such valves (a path or a ring, valve_runs) must carry one sense of flow: every mark and every
continuity direction on it, however far apart and whatever unknown segments lie between, must agree with one
traversal (one rotation on a ring). A run where any two disagree gets no direction at all: each segment evidence
reached gets a direction_conflict record (local disagreement when its own marks point both ways, withdrawn
otherwise) with the run's segments and valves in order and every observation on it, so a disagreement is never
mistaken for missing evidence. Any other item, a junction or a valve with three or more segments ends a run. Nothing is inferred from layout (left to right, top to bottom),
and a flow direction is not isolation or lockout guidance. meta.flow_direction_status counts all three.
--no-flow-direction turns it off.

Control loops and signal relations (scripts/loop_assembly.py) are added as `control_loops`: instruments grouped by
their ISA-5.1 loop identity (area prefix and loop number read from the tag), roles from the ISA letters, and signal
lines traced from each sheet image (dashed lines between symbols) and from the line layer (instrument lines with an
instrument at both ends), joined across sheets only through paired off-page connectors. A signal_to relation needs
a traced line; controls (controller -> final element) needs a confirmed loop, a traced measurement into the
controller and a traced output to the element; sets_point_of joins a cascade's outer controller to the inner one.
Tag grouping without a traced line stays an unconfirmed loop member, never a relation; nothing comes from layout.
Every relation carries its evidence and an ordinal confidence tier. meta.loops_status counts them. When no tag reads
as an ISA-5.1 instrument with a loop role, nothing is written. --no-loops turns it off.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import build_twin
import generate
import import_site_drawing as one
import offpage_pairing
import pi_mapping

SCHEMA = "site-drawing-set-1"
MAX_SHEETS = 200
LIMITATIONS = one.LIMITATIONS + [
    "Cross-sheet pairs are matched from connector text and the supplied drawing numbers, titles and system codes; a "
    "pair is a review candidate, not an established continuation.",
]
SHEET_KEYS = {"drawing_id", "revision", "page", "image", "extraction", "drawing_number", "system_code",
              "system_name", "title"}


def number_pattern(number):
    """A supplied drawing number as offpage_pairing reads it; refuses a number with no letters or digits."""
    try:
        return offpage_pairing.number_pattern(number)
    except ValueError as error:
        raise ValueError(f"drawing_number {number!r} has no letters or digits") from error


def pair_by_supplied_numbers(model, numbers, titles, codes=None):
    """Second pairing pass (module docstring): offpage_pairing.pair over the connectors build_twin left unpaired.
    Mutates the model's connectors, pairs and streams in place; returns the number of pairs added."""
    sheet_of = {c["id"]: c["provenance"][0]["sheet"] for c in model["offpage_connectors"]}
    open_ = [c for c in model["offpage_connectors"] if not c["pair"]]
    sheets = {s: {"number": numbers.get(s), "title": titles.get(s), "system_code": (codes or {}).get(s)}
              for s in sorted({*numbers, *titles, *(codes or {}), *sheet_of.values()})}
    result = offpage_pairing.pair([{"id": c["id"], "sheet": sheet_of[c["id"]], "text": c.get("text")} for c in open_],
                                  sheets)
    by_id = {c["id"]: c for c in model["offpage_connectors"]}
    named = result["names"]
    for p in result["pairs"]:
        x, y = by_id[p["a"]], by_id[p["b"]]
        x["pair"], y["pair"] = y["id"], x["id"]
        for c in (x, y):
            c["pair_method"], c["pair_status"] = p["method"], "paired"
            c["pair_description_similarity"] = p["description_similarity"]
            if not c.get("refers_to_drawing") and named.get(c["id"]):
                c["refers_to_drawing"] = numbers[named[c["id"]][0]]
        pid = f"XP-{len(model['offpage_pairs']) + 1:03d}"
        model["offpage_pairs"].append({"id": pid, "a": x["id"], "b": y["id"], "sheet_a": p["sheet_a"],
                                       "sheet_b": p["sheet_b"], "text_a": x["text"], "text_b": y["text"],
                                       "method": p["method"], "description_similarity": p["description_similarity"],
                                       "alternatives": p["alternatives"], "evidence": p["evidence"],
                                       "verification": {"status": "unverified"}})
        model["streams"].append({"id": pid, "name": f"off-page {x['text']} <-> {y['text']}", "kind": "cross_sheet",
                                 "from": x["id"], "to": y["id"], "sheet": None, "direction": "unknown",
                                 "confidence": None, "verification": {"status": "unverified"}})
    for c in open_:
        if c["pair"] or not named[c["id"]]:
            continue
        c["refers_to_drawing"] = c.get("refers_to_drawing") or numbers[named[c["id"]][0]]
        c["pair_status"] = result["status"][c["id"]]
    return len(result["pairs"])


def load_set(manifest_path, out):
    manifest_path = Path(manifest_path).resolve()
    raw_manifest = one.read_bounded(manifest_path, one.MAX_JSON_BYTES)
    manifest = one.strict_json(raw_manifest)
    one.require(isinstance(manifest, dict), "Manifest must be an object")
    one.require(manifest.get("schema_version") == SCHEMA, f"schema_version must be {SCHEMA}")
    set_id = one.text_field(manifest, "set_id")
    fmt = manifest.get("extraction_format")
    one.require(fmt in ("prediction", "run-record"), "extraction_format must be prediction or run-record")
    producer = manifest.get("producer")
    one.require(isinstance(producer, dict), "producer must describe the supplied extractions")
    producer = {k: one.text_field(producer, k, optional=k == "model") for k in ("method", "tool", "model")}
    sheets = manifest.get("sheets")
    one.require(isinstance(sheets, list) and 1 <= len(sheets) <= MAX_SHEETS, f"sheets must list 1 to {MAX_SHEETS} sheets")
    out = Path(out).absolute()
    one.require(not out.exists() and not out.is_symlink(), f"Output already exists: {out}")
    one.require(out.parent.is_dir(), "Output parent directory must already exist")
    resolved_out = out.resolve()
    loaded, seen_numbers, seen_ids = [], set(), set()
    for index, sheet in enumerate(sheets):
        one.require(isinstance(sheet, dict), f"sheets[{index}] must be an object")
        unknown = set(sheet) - SHEET_KEYS
        one.require(not unknown, f"sheets[{index}] has unsupported fields: {sorted(unknown)}")
        identity = {k: one.text_field(sheet, k) for k in ("drawing_id", "revision")}
        one.require((identity["drawing_id"], identity["revision"]) not in seen_ids,
                    f"sheets[{index}] repeats drawing {identity['drawing_id']} revision {identity['revision']}")
        seen_ids.add((identity["drawing_id"], identity["revision"]))
        page = sheet.get("page")
        one.require(type(page) is int and page > 0, f"sheets[{index}].page must be a positive integer")
        identity["page"] = page
        paths = {k: (manifest_path.parent / one.text_field(sheet, k)).resolve() for k in ("image", "extraction")}
        for source in (manifest_path, *paths.values()):
            one.require(source != resolved_out and not source.is_relative_to(resolved_out), "Output overlaps an input")
        image = one.read_bounded(paths["image"], one.MAX_IMAGE_BYTES)
        dimensions = one.png_dimensions(image)
        original = one.read_bounded(paths["extraction"], one.MAX_JSON_BYTES)
        record = one.strict_json(original)
        one.require(isinstance(record, dict), f"sheets[{index}] extraction JSON must be an object")
        if fmt == "run-record":
            one.require(not record.get("error") and not record.get("parse_error"),
                        f"sheets[{index}]: a failed extraction record cannot be imported")
            if record.get("image_sha256") is not None:
                one.require(record["image_sha256"] == one.digest(image), f"sheets[{index}]: run record image_sha256 does not match image")
            prediction = one.validate_prediction(record.get("prediction"))
        else:
            prediction = one.validate_prediction(record)
        register = {k: one.text_field(sheet, k, optional=True) for k in ("drawing_number", "system_code", "system_name")}
        title = one.text_field(sheet, "title", optional=True)
        if title and not register["system_name"]:
            register["system_name"] = title  # name the sheet's system after its title block, not "Sheet 0"
        if register["drawing_number"]:
            key = re.sub(r"[^A-Z0-9]", "", register["drawing_number"].upper())
            one.require(key not in seen_numbers, f"sheets[{index}] repeats drawing_number {register['drawing_number']}")
            seen_numbers.add(key)
            number_pattern(register["drawing_number"])
        n = str(index)
        sources = {k: {"original_filename": paths[k].name, "sha256": one.digest(content), "bytes": len(content),
                       "bundle_path": f"source/{n}.png" if k == "image" else f"source/extraction-original-{n}.json"}
                   for k, content in (("image", image), ("extraction", original))}
        loaded.append({"internal_sheet": n, "drawing": identity, "image": image, "original": original,
                       "prediction": prediction, "register": register, "title": title, "image_size_px": dimensions,
                       "record_producer": {k: record.get(k) for k in ("tool", "model")} if fmt == "run-record" else None,
                       "sources": sources})
    provenance = {"schema_version": SCHEMA, "set_id": set_id, "manifest_sha256": one.digest(raw_manifest),
                  "supplied_producer": producer, "extraction_format": fmt,
                  "original_manifest": "source/set-manifest-original.json", "limitations": LIMITATIONS,
                  "sheets": [{"internal_sheet": s["internal_sheet"], "drawing": s["drawing"], "title": s["title"],
                              "supplied_register": s["register"], "sources": s["sources"],
                              "image_size_px": s["image_size_px"], "supplied_record_producer": s["record_producer"],
                              "normalized_record": f"source/{s['internal_sheet']}.json"} for s in loaded],
                  "normalization": "Only supported symbols and connections are converted. Extra input fields remain in the preserved originals; tag whitespace and box precision follow build_twin.",
                  "pairing": "build_twin.py rules first, then scripts/offpage_pairing.py (supplied drawing numbers, titles and system codes).",
                  "pairing_rule_sha256": one.digest(Path(offpage_pairing.__file__).read_bytes()),
                  "importer_sha256": one.digest(Path(__file__).read_bytes()),
                  "sheet_validator_sha256": one.digest(Path(one.__file__).read_bytes()),
                  "converter_sha256": one.digest(Path(build_twin.__file__).read_bytes()),
                  "generator_sha256": one.digest(Path(generate.__file__).read_bytes()),
                  "pi_mapping_sha256": one.digest(Path(pi_mapping.__file__).read_bytes())}
    return out, raw_manifest, producer, loaded, provenance


def add_line_layers(model, source):
    """Add the drawn pipe and instrument layers in place; return a status record (never raises for a skip)."""
    try:
        import line_layers
        line_layers.enrich(model, {s["sheet"]: str(source / f"{s['sheet']}.png") for s in model["systems"]})
    except ImportError as error:
        return {"status": "skipped", "reason": f"needs OpenCV and NumPy (pip install -r requirements.txt): {error}"}
    except ValueError as error:
        return {"status": "skipped", "reason": str(error)}
    layers = model["line_layers"]
    dropped = [x for v in layers["sheets"].values() for x in v.get("dropped_inconsistent_lines", [])]
    return {"status": "added", "pipe_segments": len(layers["segments"]),
            "instrument_connections": len(layers["instrument_lines"]), "junctions": len(layers["junctions"]),
            "dropped_inconsistent_lines": sum(x["layer"] != "junctions" for x in dropped),
            "dropped_orphan_junctions": sum(x["layer"] == "junctions" for x in dropped)}


FLOW_SOURCES = ("arrowhead", "offpage_flag", "pump_ports", "valve_chain")


def _far_items(adj, seg, other, junctions):
    """Items at the far end of a pipe segment: `other` itself, or every item reached from that junction through
    junctions only (never through an item, never back along `seg`)."""
    if other not in junctions:
        return {other}
    found, seen, todo = set(), {other}, [other]
    while todo:
        node = todo.pop()
        for s, nxt in adj[node]:
            if s is seg or nxt in seen:
                continue
            seen.add(nxt)
            (todo.append(nxt) if nxt in junctions else found.add(nxt))
    return found


def segment_flow_evidence(model, per_sheet):
    """{segment id: [(sign, source, confidence, detail)]} from flow_direction.py's per-sheet arrowheads, off-page
    flags and pumps. sign +1: flow from the segment's `from` to its `to`. Only the segment the evidence is drawn on
    gets it: an arrowhead orients the segment of the nearest item behind it that leads to what lies ahead (and the
    nearest item ahead that leads back to what lies behind), a flag every segment at the flag, a pump the segment at
    its top (discharge) or side (suction) port. A segment that can't be singled out gets nothing."""
    import flow_direction as fd
    layers = model["line_layers"]
    junctions = {j["id"] for j in layers["junctions"]}
    syms = fd.model_symbols(model)
    adj = {}  # sheet -> node -> [(segment, node at its other end)]
    for s in layers["segments"]:
        for a, b in ((s["from"], s["to"]), (s["to"], s["from"])):
            adj.setdefault(s["sheet"], {}).setdefault(a, []).append((s, b))
    evidence = {}

    def add(sheet, item, toward, away, sign_out, source, detail):
        """Orient the one segment at `item` whose far side reaches `toward` and none of `away`."""
        here = adj.get(sheet, {})
        hits = []
        for s, b in here.get(item, []):
            far = _far_items(here, s, b, junctions) - {item}
            if (toward is None or far & toward) and not (away and far & away):
                hits.append(s)
        if toward is not None and len(hits) != 1:
            return
        for s in hits:
            out_of_item = s["from"] == item
            evidence.setdefault(s["id"], []).append(
                (sign_out if out_of_item else -sign_out, source, fd.confidence(source), detail))

    for sheet, p in sorted(per_sheet.items(), key=lambda kv: int(kv[0])):
        W, H = p["size_px"]
        asset = {sid: v["asset"] for sid, v in syms[sheet].items()}
        box = lambda b: [round(1000 * b[0] / W, 1), round(1000 * b[1] / H, 1),  # noqa: E731
                         round(1000 * b[2] / W, 1), round(1000 * b[3] / H, 1)]
        for a in p["arrows"]:
            if a.get("status") != "orients links":
                continue
            ahead, behind = {asset[x] for x in a["ahead"]}, {asset[x] for x in a["behind"]}
            detail = {"kind": "arrowhead", "sheet": sheet, "box_0_1000": box(a["box_px"]),
                      "points": ("+" if a["dir"] > 0 else "-") + a["axis"]}
            for u in sorted({asset[x] for x in a["near_behind"]}):
                add(sheet, u, ahead, behind, +1, "arrowhead", detail)
            for v in sorted({asset[x] for x in a["near_ahead"]}):
                add(sheet, v, behind, ahead, -1, "arrowhead", detail)
        for sid, f in sorted(p["flags"].items()):
            if f["role"] in ("source", "sink"):
                add(sheet, asset[sid], None, None, +1 if f["role"] == "source" else -1, "offpage_flag",
                    {"kind": "offpage_flag", "sheet": sheet, "box_0_1000": box(f["box_px"]), "tip": f["tip"],
                     "role": f["role"]})
        for sid, pump in sorted(p["pumps"].items()):
            if not pump["fires"]:
                continue
            top, side = {asset[x] for x in pump["discharge_to"]}, {asset[x] for x in pump["suction_from"]}
            for toward, away, sign, port in ((top, side, +1, "discharge (top)"), (side, top, -1, "suction (side)")):
                add(sheet, asset[sid], toward, away, sign, "pump_ports",
                    {"kind": "pump_ports", "sheet": sheet, "box_0_1000": box(pump["box_px"]), "port": port})
    for sid in evidence:  # the same drawn mark reached from both of its sides counts once
        seen, keep = set(), []
        for e in evidence[sid]:
            key = (e[0], e[1], json.dumps(e[3], sort_keys=True))
            if key not in seen:
                seen.add(key)
                keep.append(e)
        evidence[sid] = keep
    return evidence


def _says(segment, e):
    """One observation as recorded on a segment: which way it says the flow goes, and what was drawn."""
    a, b = (segment["from"], segment["to"]) if e[0] > 0 else (segment["to"], segment["from"])
    return {**e[3], "flow_from": a, "flow_to": b}


def valve_runs(segments, valves):
    """Maximal runs of pipe segments joined through two-port valves (a valve with exactly two pipe segments), in
    traversal order. Each run is {"kind": "path" | "ring", "steps": [(segment, +1 if the segment's from -> to follows
    the traversal else -1)], "valves": [the valves passed, in order]}. Anything else at a segment end (an item that
    is not a valve, a valve with one or three or more segments, a junction) ends a run, so continuity is never
    assumed through it. Every segment is in exactly one run."""
    ends = {}
    for s in segments:
        for n in {s["from"], s["to"]}:
            ends.setdefault(n, []).append(s)
    two_port = {v for v in valves if len(ends.get(v, [])) == 2}

    def other_end(s, n):
        return s["to"] if s["from"] == n else s["from"]

    def walk(s, start):
        steps, vs, node, seen = [], [], start, set()
        while s is not None and s["id"] not in seen:
            seen.add(s["id"])
            steps.append((s, 1 if s["from"] == node else -1))
            node = other_end(s, node)
            if node not in two_port:
                break
            nxt = next(x for x in ends[node] if x is not s)
            if nxt["id"] in seen:  # back to the start: a ring
                vs.append(node)
                break
            vs.append(node)
            s = nxt
        return steps, vs
    runs, placed = [], set()
    for s in segments:  # paths first, from an end that is not a two-port valve
        if s["id"] in placed or s["from"] == s["to"]:
            continue
        for start in (s["from"], s["to"]):
            if start not in two_port:
                steps, vs = walk(s, start)
                runs.append({"kind": "path", "steps": steps, "valves": vs})
                placed |= {x["id"] for x, _ in steps}
                break
    for s in segments:  # what is left closes on itself through two-port valves
        if s["id"] in placed:
            continue
        steps, vs = walk(s, s["from"])
        runs.append({"kind": "ring" if s["from"] != s["to"] else "path", "steps": steps, "valves": vs})
        placed |= {x["id"] for x, _ in steps}
    return runs


def decide_flow(segments, evidence, valves):
    """({segment id: decision}, {segment id: segment}) for every segment that drawn evidence reached. A decision is
    {"direction": forward | reverse, "confidence", "basis", "used"} or {"direction": "conflict", "seen", "local",
    "contradictions"}.

    Flow through a two-port valve is continuous, so along one run (valve_runs) every direction must agree with one
    traversal sense, on a ring with one rotation. Each segment's own drawn marks, and continuity carried one hop
    through a valve from a segment whose own marks agree (flow_direction.propagate_valves, unchanged), are oriented
    to the run's traversal. If they all agree, the segments they reach are directed; if any two disagree, however far
    apart and whatever unknown segments lie between, the run admits no consistent flow: every direction in it is
    withdrawn, and each segment it reached records the run (its segments and valves in order) and every observation
    on it. Runs never share a segment, so one run's contradiction withdraws nothing elsewhere."""
    import flow_direction as fd
    by_id = {s["id"]: s for s in segments}
    first = {sid: fd.combine(e) for sid, e in evidence.items()}
    seeds = {sid: d for sid, d in first.items() if d[0] in ("forward", "reverse")}
    proposals = {sid: [(*e, sid) for e in obs] for sid, obs in evidence.items()}
    for sid, more in fd.propagate_valves(segments, seeds, valves, fd.confidence("valve_chain")).items():
        proposals.setdefault(sid, []).extend(
            (e[0], e[1], e[2], {"kind": "valve_chain", "through": e[3]["through"], "from_segment": e[3]["from_link"]},
             e[3]["from_link"]) for e in more)
    out = {}
    for run in valve_runs(segments, valves):
        along = {s["id"]: sense for s, sense in run["steps"]}
        reached = [s["id"] for s, _ in run["steps"] if proposals.get(s["id"])]
        if not reached:
            continue
        senses = {x[0] * along[sid] for sid in reached for x in proposals[sid]}
        if len(senses) == 1:
            for sid in reached:
                direction, confidence, basis = fd.combine([x[:4] for x in proposals[sid]])
                tier = (lambda k: k != "valve_chain") if basis == "first_hand" else (lambda k: k == "valve_chain")
                out[sid] = {"direction": direction, "confidence": confidence, "basis": basis,
                            "used": [x[:4] for x in proposals[sid] if tier(x[1])]}
            continue
        cause = {"rule": f"directions along one {run['kind']} of two-port valves disagree"
                         + (" (no single rotation)" if run["kind"] == "ring" else ""),
                 "kind": run["kind"], "segments": [s["id"] for s, _ in run["steps"]], "valves": run["valves"],
                 "seeds": sorted({x[4] for sid in reached for x in proposals[sid] if x[1] != "valve_chain"}),
                 "observations": [(sid, x, x[0] * along[sid]) for sid in reached for x in proposals[sid]]}
        for sid in reached:
            own = evidence.get(sid, [])
            out[sid] = {"direction": "conflict", "seen": proposals[sid], "local": len({x[0] for x in own}) > 1,
                        "contradictions": [cause]}
    return out, by_id


def _conflict_record(s, d, by_id):
    """direction_conflict for one segment: its own observations, whether its own marks disagree
    (local_disagreement) or its direction is withdrawn because the run it is on admits no consistent flow
    (withdrawn), and the run that caused it: segments and valves in traversal order, the seed segments, and every
    observation on the run with the segment it is on, the flow it claims, its sense along the run (+1 / -1) and, for
    continuity, the valve it passed through and the segment it came from."""
    def obs(sid, x, sense):
        return {**_says(by_id[sid], x), "segment": sid, "along_run": sense}
    own = d["seen"]
    return {
        "status": "local_disagreement" if d["local"] else "withdrawn",
        "qualification": ("the drawn marks on this segment point both ways; its direction is unknown" if d["local"]
                          else "this segment's own observations agree, but the run of two-port valves it is on "
                               "admits no consistent flow (caused_by), so its direction is withdrawn and unknown"),
        "kinds": sorted({x[1] for x in own}, key=FLOW_SOURCES.index),
        "found": [_says(s, x) for x in own],
        "caused_by": [{"rule": c["rule"], "run": c["kind"], "segments": c["segments"], "valves": c["valves"],
                       "seeds": c["seeds"], "observations": [obs(*o) for o in c["observations"]]}
                      for c in d["contradictions"]]}


def apply_flow(segments, evidence, valves):
    """Write decide_flow()'s result onto the segments in place; return (counts, by basis, by kind, conflict ids).
    A conflict keeps no direction (the graph's `unknown`) and gets direction_conflict (_conflict_record); a segment
    with no evidence is not touched."""
    decided, by_id = decide_flow(segments, evidence, valves)
    records = {sid: _conflict_record(by_id[sid], d, by_id) for sid, d in decided.items()
               if d["direction"] == "conflict"}  # before any directed segment's ends are swapped
    counts = {"directed": 0, "undirected": 0, "conflict": 0}
    by_basis, by_kind, conflicts = {}, {}, []
    for s in segments:
        d = decided.get(s["id"])
        if d and d["direction"] == "conflict":
            counts["conflict"] += 1
            conflicts.append(s["id"])
            s["direction_conflict"] = records[s["id"]]
            continue
        if not d or d["direction"] not in ("forward", "reverse"):
            counts["undirected"] += 1
            continue
        counts["directed"] += 1
        used = d["used"]
        if d["direction"] == "reverse":
            s["from"], s["to"] = s["to"], s["from"]
        s["direction"] = "forward"
        s["direction_evidence"] = {"basis": d["basis"], "confidence": d["confidence"],
                                   "kinds": sorted({x[1] for x in used}, key=FLOW_SOURCES.index),
                                   "found": [x[3] for x in used]}
        by_basis[d["basis"]] = by_basis.get(d["basis"], 0) + 1
        for k in s["direction_evidence"]["kinds"]:
            by_kind[k] = by_kind.get(k, 0) + 1
    return counts, by_basis, by_kind, conflicts


def add_flow_direction(model, source):
    """Direct the pipe segments that drawn evidence orients, in place (module docstring); return a status record
    (never raises for a skip). Undirected segments are left byte for byte as the line layers wrote them."""
    try:
        import flow_direction as fd
        _, per_sheet = fd.infer(model, source)
    except ImportError as error:
        return {"status": "skipped", "reason": f"needs OpenCV and NumPy (pip install -r requirements.txt): {error}"}
    except SystemExit as error:  # flow_direction.infer refuses links it can't re-trace
        return {"status": "skipped", "reason": str(error)}
    segments = model["line_layers"]["segments"]
    valves = [x["id"] for x in model["line_items"] if x["class"] == "valve"]
    counts, by_basis, by_kind, conflicts = apply_flow(segments, segment_flow_evidence(model, per_sheet), valves)
    arrows = {sheet: [{"box_0_1000": [round(1000 * a["box_px"][i] / p["size_px"][i % 2], 1) for i in range(4)],
                       "points": ("+" if a["dir"] > 0 else "-") + a["axis"], "status": a.get("status")}
                      for a in p["arrows"]] for sheet, p in sorted(per_sheet.items(), key=lambda kv: int(kv[0]))}
    return {"status": "added", "method": "scripts/flow_direction.py detectors on each sheet image; evidence placed "
                                         "on the pipe segment it is drawn on",
            "pipe_segments": len(segments), **counts, "directed_by_basis": by_basis, "directed_by_evidence": by_kind,
            "conflict_segments": conflicts, "arrowheads_found": arrows,
            "not_used": "no direction is inferred from layout; a segment without drawn evidence stays undirected",
            "limit": "drawn flow direction for review, not isolation or lockout guidance"}


def add_loops(model, source, crossing_answers=None):
    """Control loops and signal relations (scripts/loop_assembly.py, module docstring); a status record.
    crossing_answers: a scripts/crossing_question.py answers file for lines joined through a crossing."""
    import loop_assembly
    return loop_assembly.add_loops(model, source, crossing_answers)


def import_set(manifest_path, out, check_only=False, line_layers=True, flow_direction=True, loops=True,
               crossing_answers=None):
    out, raw_manifest, producer, loaded, provenance = load_set(manifest_path, out)
    drawings = [s["drawing"] for s in loaded]
    if check_only:
        return {"inputs_valid": True, "exports_written": False, "set_id": provenance["set_id"], "drawings": drawings,
                "limitations": LIMITATIONS}
    stage = Path(tempfile.mkdtemp(prefix=".site-set-intake-", dir=out.parent))
    try:
        source = stage / "source"
        source.mkdir()
        (source / "set-manifest-original.json").write_bytes(raw_manifest)
        for s in loaded:
            n = s["internal_sheet"]
            (source / f"{n}.png").write_bytes(s["image"])
            (source / f"extraction-original-{n}.json").write_bytes(s["original"])
            one.write_json(source / f"{n}.json", {"tool": producer["tool"], "model": producer["model"],
                           "prediction": s["prediction"], "image_sha256": one.digest(s["image"]),
                           "intake": {"set_id": provenance["set_id"], "drawing": s["drawing"]}})
        sheet_list = [s["internal_sheet"] for s in loaded]
        register = {s["internal_sheet"]: s["register"] for s in loaded}
        model = build_twin.build("supplied-extraction", source, sheet_list, source, register,
                                 "site-drawing-set", parent_rule="linked")
        numbers = {s["internal_sheet"]: s["register"]["drawing_number"] for s in loaded if s["register"]["drawing_number"]}
        titles = {s["internal_sheet"]: s["title"] for s in loaded if s["title"]}
        codes = {s["internal_sheet"]: s["register"]["system_code"] for s in loaded if s["register"]["system_code"]}
        added = pair_by_supplied_numbers(model, numbers, titles, codes)
        model["summary"] = build_twin.summary(model)
        model["meta"]["source_document"] = f"{provenance['set_id']}: " + "; ".join(
            f"{d['drawing_id']} rev {d['revision']} p{d['page']}" for d in drawings)
        model["meta"]["extraction_method"] = "Imported supplied extractions; no model or tracer executed by this intake"
        model["meta"]["intake"] = provenance
        model["meta"]["review_requirements"] = {"draft_review_exports_allowed": True, "operational_export_allowed": False,
                    "status_scope": "Descriptive intake readiness only; not an enforced deployment interlock", "blockers": LIMITATIONS[2:6]}
        evidence = {s["internal_sheet"]: {"source_manifest": "intake_manifest.json", "source_drawing": s["drawing"],
                                          "image_sha256": one.digest(s["image"]), "extraction_sha256": one.digest(s["original"])}
                    for s in loaded}
        for system in model["systems"]:
            system["source_run"] = f"source/{system['sheet']}.json"
            system.update(evidence[system["sheet"]])
        for collection in ("units", "instruments", "line_items", "offpage_connectors"):
            for item in model[collection]:
                for appearance in item["provenance"]:
                    appearance["source_run"] = f"source/{appearance['sheet']}.json"
                    appearance.update(evidence[appearance["sheet"]])
        for stream in model["streams"]:
            stream["source_evidence"] = evidence[stream["sheet"]] if stream.get("sheet") in evidence else \
                {"source_manifest": "intake_manifest.json", "cross_sheet": True}
        one.require(not model["dropped"]["symbols"] and not model["dropped"]["connections"], "Converter dropped input items")
        problems = generate.validate_twin(model)
        one.require(not problems, f"Converted model is invalid: {problems}")
        generate.export_twin(model, stage, images_dir=source)
        layers = add_line_layers(model, source) if line_layers else {"status": "not requested"}
        model["meta"]["line_layers_status"] = layers
        if flow_direction and layers["status"] == "added":
            model["meta"]["flow_direction_status"] = add_flow_direction(model, source)
        loop_status = add_loops(model, source, crossing_answers) if loops else {"status": "not requested"}
        if loop_status["status"] == "added":
            model["meta"]["loops_status"] = loop_status
        one.write_json(stage / "plant_model.json", model)
        one.write_json(stage / "intake_manifest.json", provenance)
        (stage / "READ_ME.txt").write_text("UNVERIFIED LOCAL REVIEW BUNDLE (DRAWING SET)\n\n" + "\n".join(LIMITATIONS)
                    + "\n\nSource paths are relative to this bundle. Keep source/ with the model and SVG files.\n", encoding="utf-8")
        one.require(not out.exists() and not out.is_symlink(), f"Output appeared while preparing bundle: {out}")
        os.rename(stage, out)
        return {"inputs_valid": True, "exports_written": True, "output": str(out), "summary": model["summary"],
                "pairs_from_supplied_numbers": added, "line_layers": layers,
                **({"flow_direction": {k: v for k, v in model["meta"]["flow_direction_status"].items()
                                       if k not in ("arrowheads_found", "conflict_segments")}}
                   if "flow_direction_status" in model["meta"] else {}),
                **({"loops": loop_status} if loops else {}),
                "operational_export_allowed": False, "limitations": LIMITATIONS}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=(
        "Manifest fields: schema_version=site-drawing-set-1, set_id, extraction_format=prediction|run-record, "
        "producer={method,tool,model}, sheets=[{drawing_id, revision, page, image, extraction; optional "
        "drawing_number, title, system_code, system_name}]. Supply each sheet's drawing number and title from its "
        "title block so cross-sheet references can be matched. Paths are relative to the manifest. Output must be "
        "new, with an existing parent."))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--check-only", action="store_true", help="validate inputs without writing")
    parser.add_argument("--no-line-layers", action="store_true", help="skip the drawn pipe and instrument layers")
    parser.add_argument("--no-flow-direction", action="store_true",
                        help="leave every pipe segment undirected (no drawn flow-direction evidence)")
    parser.add_argument("--no-loops", action="store_true",
                        help="no control loops or signal relations (the bundle is then increment 2's, except "
                             "meta.intake.importer_sha256, which hashes this file)")
    parser.add_argument("--crossing-answers", help="a scripts/crossing_question.py answers file: the blind crossing "
                             "evaluator's answers for signal lines joined through a crossing (corroboration channel b)")
    args = parser.parse_args(argv)
    try:
        result = import_set(args.manifest, args.out, args.check_only, line_layers=not args.no_line_layers,
                            flow_direction=not args.no_flow_direction, loops=not args.no_loops,
                            crossing_answers=args.crossing_answers)
    except (ValueError, OSError, TypeError, KeyError, OverflowError, RecursionError) as error:
        parser.exit(2, f"Drawing set intake failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
