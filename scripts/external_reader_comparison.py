"""Compare an external reader that entered through the reader slot with our readers, on the development sets only.

The first external reader is pid-to-kg (Scott Duncan's public MIT skill,
https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph), run headless as its README describes, its graph.json
converted by scripts/reader_external_kg.py. Its readings are committed like any reader's
(predictions/ext-pidkg-r1, ext-pidkg-te-a-r1, ext-pidkg-te-d-r1); the relations its own builder assembled across
each set (loops, off-page links, directed pairs) are in out/ext_pidkg/relations/, and the run costs in
out/ext_pidkg/runs.json. This script writes no scorer of its own for symbols, connections, tags or directions:

  symbols, connections, review load   scripts/evaluate_vendor.py (the frozen scorer beside the four controls), per
                                      sheet and per class, beside our readers' committed predictions on the same sheets
  tags (TE)                           score_te_roundtrip.score_sheet's tag rows (printed text, letters and digits)
  tags (Pahala, optional)             the drawing-set bundle, then scripts/pdf_tag_check.py against the PDF text layer
  product path                        scripts/import_drawing_set.py on the external reading, and on its symbols with our
                                      tracer's links ("hybrid", trace_connections.trace with its defaults), so the
                                      bundle's line layers and flow direction can be scored by flow_direction_score
  flow direction (TE)                 flow_direction_score's truth (the model's streams as drawn) and flow_of, applied
                                      to the external reader's own directed symbol pairs; key symbols by rough IoU
  off-page links (OPEN100 0-5)        examples/own-drawing/offpage-key.json, connectors matched by box to the key's ids
  control loops (TE)                  data/te_control_loops.json; ours builds no loops yet, so there is no row of ours

Development sets only: OPEN100 sheets 0-5, TE revisions A and D (sheets 101-103), Pahala P-401/P-501 (not in the
repository; give --pahala-dir and --pahala-pdf). Held-out sheets are refused.

    python scripts/external_reader_comparison.py --out out/ext_pidkg/comparison \\
        [--pahala-images DIR --pahala-ext DIR --pahala-ours DIR --pahala-pdf pahala.pdf]

Needs OpenCV and NumPy (the tracer, line layers and direction truth) and git history for revision A's drawer.
No model calls, no network.
"""
import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_vendor as ev  # noqa: E402
import flow_direction_score as fds  # noqa: E402
import score_pid2graph as sc  # noqa: E402
import score_te_roundtrip as te  # noqa: E402

OPEN100 = fds.OPEN100
TE_DIR = {"te-a": ROOT / "data/te_pid/rev-a", "te-d": ROOT / "data/te_pid"}
EXT = "pid-to-kg"
SETS = {
    "open100-dev": {"keys": OPEN100, "sheets": ["0", "1", "2", "3", "4", "5"], "external": "ext-pidkg-r1",
                    "ours": {"r2-tiles-trace (tiles + our tracer)": [("r2-tiles-trace", t) for t in ("claude", "codex", "gemini")],
                             "r2-tiles-2x2 (tiles, model links)": [("r2-tiles-2x2", t) for t in ("claude", "codex", "gemini")]}},
    "te-a": {"keys": TE_DIR["te-a"], "sheets": fds.TE_SHEETS, "external": "ext-pidkg-te-a-r1",
             "ours": {"te-clean-trace (tiles + our tracer)": [(f"te-clean-trace-r{r}", t) for t in ("claude", "codex") for r in range(1, 6)],
                      "te-clean-tiles (tiles, model links)": [(f"te-clean-tiles-r{r}", t) for t in ("claude", "codex") for r in range(1, 6)]}},
    "te-d": {"keys": TE_DIR["te-d"], "sheets": fds.TE_SHEETS, "external": "ext-pidkg-te-d-r1", "ours": {}},
}
HELD_OUT = {"open100": {"6", "7", "8", "9", "10", "11"}}
LENIENT = lambda t: re.sub(r"[^A-Z0-9]", "", str(t or "").upper())  # noqa: E731


def refuse_held_out(keys, sheets):
    if Path(keys) == OPEN100 and set(sheets) & HELD_OUT["open100"]:
        raise SystemExit("OPEN100 sheets 6-11 are held out")


def preds_dir(label, tool):
    return ROOT / "predictions" / label / tool


# ---------------------------------------------------------------- symbols, connections, review load

def by_class(keys, sheets, folder):
    """Per-class rough F1, plus a convention diagnostic from the scorer's own class-free rough match: predicted valves
    paired with a key instrument bubble (a control valve read as one item where the key draws a valve body and an
    actuator bubble), and key valves left unpaired."""
    acc = {c: {"tp": 0, "predicted": 0, "in_key": 0} for c in sc.SCORED}
    diag = {"predicted_valves": 0, "valve_paired_with_key_instrument": 0, "key_valves": 0, "key_valves_unpaired": 0}
    for s in sheets:
        pred, status, _ = ev.load_prediction(folder / f"{s}.json")
        pred = pred or {"symbols": [], "connections": []}
        r = sc.score(keys / f"{s}.graphml", pred, keys / f"{s}.png")
        for c in sc.SCORED:
            for k in acc[c]:
                acc[c][k] += r["rough"]["by_class"][c][k]
        w, h = sc.png_size(keys / f"{s}.png")
        nodes, _ = sc.load_key(keys / f"{s}.graphml", w, h)
        kk = {k: v for k, v in nodes.items() if v["class"] in sc.SCORED}
        syms = sc.valid_symbols(pred)
        m = sc.match(syms, kk, False, sc.THRESHOLDS["rough"])
        valves = [x["id"] for x in syms if x["class"] == "valve"]
        diag["predicted_valves"] += len(valves)
        diag["valve_paired_with_key_instrument"] += sum(kk[m[v]]["class"] == "instrumentation" for v in valves if v in m)
        key_valves = [k for k, v in kk.items() if v["class"] == "valve"]
        diag["key_valves"] += len(key_valves)
        diag["key_valves_unpaired"] += sum(k not in set(m.values()) for k in key_valves)
    return {c: sc.prf(v["tp"], v["predicted"], v["in_key"]) for c, v in acc.items()}, diag


def reader_row(keys, sheets, folders, name):
    r = ev.evaluate(keys, folders, sheets, name)
    rep = r["replicates"]
    classes, diag = by_class(keys, sheets, Path(folders[0]))
    row = {"name": name, "runs": len(folders), "controls_ok": r["controls_ok"],
           "metrics": {m: {k: rep[m][k] for k in ("mean", "min", "max")} for m, _ in ev.HEADLINE},
           "per_sheet": {s: r["per_sheet"][s]["vendor_mean"] for s in sheets},
           "per_class_rough_f1_first_run": {c: v["f1"] for c, v in classes.items()},
           "valve_convention_first_run": diag, "missing_or_failed": r["missing_or_failed"]}
    return row, r["controls"]


def hybrid_folder(cfg, tmp):
    """The external reader's symbols with our tracer's links (trace_connections defaults), as run records."""
    import trace_connections as tc
    out = tmp / f"hybrid-{cfg['external']}" / EXT
    out.mkdir(parents=True)
    for s in cfg["sheets"]:
        rec = json.loads((preds_dir(cfg["external"], EXT) / f"{s}.json").read_text(encoding="utf-8"))
        rec.pop("schema", None)
        png = cfg["keys"] / f"{s}.png"
        links = tc.trace(png, rec["prediction"]["symbols"])
        rec["prediction"] = {"symbols": rec["prediction"]["symbols"],
                             "connections": [{"from": l["from"], "to": l["to"]} for l in links]}
        rec["source_label"] = cfg["external"]
        rec["tracer"] = {"script": "scripts/trace_connections.py", "mode": "replace"}
        (out / f"{s}.json").write_text(json.dumps(rec), encoding="utf-8")
    return out


def symbol_tables(tmp):
    out = {}
    for set_id, cfg in SETS.items():
        refuse_held_out(cfg["keys"], cfg["sheets"])
        rows, controls = [], None
        row, controls = reader_row(cfg["keys"], cfg["sheets"], [preds_dir(cfg["external"], EXT)], f"{EXT} (its own links)")
        rows.append(row)
        hyb = hybrid_folder(cfg, tmp)
        rows.append(reader_row(cfg["keys"], cfg["sheets"], [hyb], f"{EXT} symbols + our tracer (hybrid)")[0])
        for name, srcs in cfg["ours"].items():
            by_tool = defaultdict(list)
            for label, tool in srcs:
                by_tool[tool].append(preds_dir(label, tool))
            for tool, folders in by_tool.items():
                rows.append(reader_row(cfg["keys"], cfg["sheets"], folders, f"ours: {name}, {tool}")[0])
        out[set_id] = {"keys": str(cfg["keys"].relative_to(ROOT)).replace("\\", "/"), "sheets": cfg["sheets"],
                       "rows": rows, "controls": controls, "hybrid_dir": hyb}
    return out


# ---------------------------------------------------------------- tags on TE (printed text, letters and digits)

def te_tags(set_id, folders):
    keys = TE_DIR[set_id]
    key = json.loads((keys / "key.json").read_text(encoding="utf-8"))
    te.KEYS = keys
    runs = []
    for folder in folders:
        rows, refs = [], []
        for s in fds.TE_SHEETS:
            pred, _, _ = ev.load_prediction(folder / f"{s}.json")
            _, t, r = te.score_sheet(s, {"prediction": pred}, key)
            rows += t
            refs += r
        found = [x for x in rows if x["found"]]
        runs.append({"tags": len(rows), "read": sum(x["read"] for x in rows), "found": len(found),
                     "read_if_found": sum(x["read"] for x in found),
                     "another_real_tag": sum(x["is_another_real_tag"] for x in rows),
                     "offpage_refs": len(refs), "offpage_refs_read": sum(x["read"] for x in refs),
                     "not_read": [{"printed": x["printed"], "extracted": x["extracted"]} for x in rows if not x["read"]]})
    return runs


def tag_tables():
    out = {}
    for set_id in ("te-a", "te-d"):
        cfg = SETS[set_id]
        rows = {f"{EXT}": te_tags(set_id, [preds_dir(cfg["external"], EXT)])}
        for name, srcs in cfg["ours"].items():
            by_tool = defaultdict(list)
            for label, tool in srcs:
                by_tool[tool].append(preds_dir(label, tool))
            for tool, folders in by_tool.items():
                rows[f"ours: {name}, {tool}"] = te_tags(set_id, folders)
        out[set_id] = rows
    return out


# ---------------------------------------------------------------- the product path (drawing-set bundle)

def set_rows(set_id, folder):
    if set_id == "open100-dev":
        base = json.loads((ROOT / "examples/own-drawing/set-manifest.json").read_text(encoding="utf-8"))
        return base["set_id"], [{**s, "image": str(OPEN100 / f"{i}.png"), "extraction": str(folder / f"{i}.json")}
                                for i, s in zip(fds.DEV_OPEN100, base["sheets"])]
    keys = TE_DIR[set_id]
    key = json.loads((keys / "key.json").read_text(encoding="utf-8"))
    rev = set_id[-1].upper()
    return f"TE revision {rev}", [{"drawing_id": f"TE-{s}", "revision": rev, "page": n, "image": str(keys / f"{s}.png"),
                                   "extraction": str(folder / f"{s}.json"), "drawing_number": key["sheets"][s]["drawing"],
                                   "title": key["sheets"][s]["title"]} for n, s in enumerate(fds.TE_SHEETS, 1)]


def product_path(symbols, tmp):
    out, truths = {}, {}
    for set_id in ("te-a", "te-d"):
        dp, model_path, layout_path, folder = fds.revision_inputs(set_id[-1], tmp)
        raw = fds.te_truth(dp, model_path, layout_path, folder / "key.json")
        truths[set_id] = {s: (fds.classified_truth(raw[s], folder / f"{s}.png", folder / f"{s}.graphml"),
                              folder / f"{s}.png", folder / f"{s}.graphml") for s in fds.TE_SHEETS}
        truths[set_id + "/raw"] = raw
    for set_id, cfg in SETS.items():
        rows = {}
        for name, folder in ((f"{EXT} (its own links)", preds_dir(cfg["external"], EXT)),
                             (f"{EXT} symbols + our tracer (hybrid)", symbols[set_id]["hybrid_dir"])):
            sub = tmp / f"bundle-{set_id}-{'hyb' if 'hybrid' in name else 'own'}"
            set_name, rows_in = set_rows(set_id, folder)
            manifest = fds.write_manifest(sub, set_name, {"method": name, "tool": EXT, "model": None}, rows_in)
            try:
                result, model = fds.bundle(manifest, sub / "bundle")
            except ValueError as error:
                rows[name] = {"refused_by_intake": str(error)}
                continue
            rec = {"line_layers": result["line_layers"]["status"],
                   "line_layers_reason": result["line_layers"].get("reason"), "summary": {
                       k: result["summary"].get(k) for k in ("equipment", "instruments", "line_items",
                                                             "offpage_connectors", "offpage_pairs", "placeholder_tags")}}
            if result["line_layers"]["status"] == "added":
                rec["flow_direction"] = {k: v for k, v in (result.get("flow_direction") or {}).items()
                                         if k in ("pipe_segments", "directed", "conflicts", "status")}
                rec.update(fds.share(model))
                if set_id in truths:
                    sheet_of = {s: str(n) for n, s in enumerate(fds.TE_SHEETS)}
                    rec["direction_scored"] = fds.score_directions(model, truths[set_id], sheet_of)["total"]
            rows[name] = rec
        out[set_id] = rows
    return out, truths


# ---------------------------------------------------------------- the external reader's own relations

def own_directions(truths):
    """Its directed symbol pairs (FLOWS_TO through pipe segments) against the TE stream truth, with controls."""
    out = {}
    for set_id in ("te-a", "te-d"):
        rel = json.loads((ROOT / f"out/ext_pidkg/relations/{set_id}.json").read_text(encoding="utf-8"))
        cfg, res = SETS[set_id], defaultdict(int)
        for s in cfg["sheets"]:
            raw = truths[set_id + "/raw"][s]
            png, gml = cfg["keys"] / f"{s}.png", cfg["keys"] / f"{s}.graphml"
            pred, _, _ = ev.load_prediction(preds_dir(cfg["external"], EXT) / f"{s}.json")
            w, h = sc.png_size(png)
            nodes, _ = sc.load_key(gml, w, h)
            keys = {k: v for k, v in nodes.items() if v["class"] in sc.SCORED}
            syms = sc.valid_symbols(pred)
            m = sc.match(syms, keys, False, sc.THRESHOLDS["rough"])
            centre = {x["id"]: sc.centre(x["box"]) for x in syms}
            for p in rel["directed_pairs_by_drawing"][s]:
                res["pairs"] += 1
                res["pairs_shown"] += p["flow_direction"] == "shown"
                a, b = m.get(p["from"]), m.get(p["to"])
                f = fds.flow_of(raw, a, b, set()) if a and b else None
                if f is None:
                    continue
                ok = (a, b) == f
                res["scorable"] += 1
                res["correct"] += ok
                if p["flow_direction"] == "shown":
                    res["scorable_shown"] += 1
                    res["correct_shown"] += ok
                # layout control (N012's rule): left to right, or top to bottom when the pair runs vertically
                (xa, ya), (xb, yb) = centre[p["from"]], centre[p["to"]]
                layout_forward = (xb > xa) if abs(xb - xa) >= abs(yb - ya) else (yb > ya)
                res["layout_correct"] += layout_forward == ok
        r = dict(res)
        r["precision"] = round(r["correct"] / r["scorable"], 3) if r.get("scorable") else None
        r["precision_shown"] = round(r["correct_shown"] / r["scorable_shown"], 3) if r.get("scorable_shown") else None
        r["controls"] = {"reversed": round(1 - r["precision"], 3) if r["precision"] is not None else None,
                         "layout": round(r.get("layout_correct", 0) / r["scorable"], 3) if r.get("scorable") else None,
                         "perfect": 1.0 if r.get("scorable") else None}
        out[set_id] = r
    return out


def loops():
    truth = json.loads((ROOT / "data/te_control_loops.json").read_text(encoding="utf-8"))
    valve = [(l["id"], l["measurement"]["tag"], l["output"]["tag"]) for l in truth["loops"]
             if l["runs"] and l["output"]["kind"] == "final_element"]
    casc = [(l["id"], l["measurement"]["tag"], l["output"]["tag"]) for l in truth["loops"]
            if l["runs"] and l["output"]["kind"] == "setpoint"]
    out = {}
    for set_id in ("te-a", "te-d"):
        rel = json.loads((ROOT / f"out/ext_pidkg/relations/{set_id}.json").read_text(encoding="utf-8"))
        L = [{**x, "S": {LENIENT(t) for t in x["sensors"]}, "C": {LENIENT(t) for t in x["controllers"]},
              "F": {LENIENT(t) for t in x["final_elements"]}} for x in rel["loops"]]
        by_label = {x["loop"]: x for x in L}
        got_valve = [lid for lid, s, f in valve if any(LENIENT(s) in x["S"] and LENIENT(f) in x["F"] for x in L)]
        pairs = {(a, b) for x in L if x["kind"] in ("control", "interlock") for a in x["S"] for b in x["F"]}
        truth_pairs = {(LENIENT(s), LENIENT(f)) for _, s, f in valve}
        got_casc = []
        for lid, s, ctl in casc:
            for c in rel["cascades"]:
                m, v = by_label.get(c["master"]), by_label.get(c["slave"])
                if m and v and LENIENT(s) in m["S"] and LENIENT(ctl) in v["C"]:
                    got_casc.append(lid)
                    break
        out[set_id] = {"truth_valve_loops": len(valve), "valve_loops_found": len(got_valve), "found_ids": got_valve,
                       "sensor_final_pairs": len(pairs), "pairs_correct": len(pairs & truth_pairs),
                       "truth_cascades": len(casc), "cascades_found": len(got_casc), "cascade_ids": got_casc,
                       "loops_by_kind": rel["stats"].get("loops_by_type"), "cascade_edges": len(rel["cascades"])}
    out["ours"] = "no loops: round 6 increment 3 (signal_to, controls, loops) is not built"
    return out


def offpage():
    key = json.loads((ROOT / "examples/own-drawing/offpage-key.json").read_text(encoding="utf-8"))
    rel = json.loads((ROOT / "out/ext_pidkg/relations/open100-dev.json").read_text(encoding="utf-8"))
    truth = {frozenset((c["a"], c["b"])) for c in key["continuations"]}
    to_key = {}
    for s in fds.DEV_OPEN100:
        ref, _, _ = ev.load_prediction(ROOT / "predictions/r2-tiles-trace/codex" / f"{s}.json")
        flags = {x["id"]: x for x in sc.valid_symbols(ref) if x["class"] == "inlet/outlet"}
        to_key[s] = flags
    pairs, mapped = [], 0
    for link in rel["offpage_links"]:
        ends = []
        for side in ("from", "to"):
            e = link[side]
            if not e["bbox_0_1"] or e["drawing"] is None:
                ends.append(None)
                continue
            box = [v * 1000 for v in e["bbox_0_1"]]
            m = sc.match([{"id": "x", "class": "inlet/outlet", "box": box}], to_key[e["drawing"]], False, sc.THRESHOLDS["rough"])
            ends.append(f"{e['drawing']}/{m['x']}" if "x" in m else None)
        mapped += all(ends)
        pairs.append({"ends": ends, "labels": [link["from"]["label"], link["to"]["label"]], "linked_by": link["linked_by"],
                      "correct": bool(all(ends) and frozenset(ends) in truth)})
    correct = {frozenset(p["ends"]) for p in pairs if p["correct"]}
    return {"key": "examples/own-drawing/offpage-key.json", "continuations": len(truth), "links": len(pairs),
            "links_mapped_to_key_connectors": mapped, "correct": sum(p["correct"] for p in pairs),
            "continuations_found": len(correct), "pairs": pairs,
            "ours_A407": "drawing-set import 5 pairs, 5 correct, 5/6 continuations; offpage_pairing alone 2/2, 2/6"}


def pahala(images, ext_dir, ours_dir, pdf, tmp):
    """Optional: Pahala P-401/P-501 through the drawing-set bundle, then pdf_tag_check against the text layer, for the
    external reading and ours (claude, 2x2 tiles + our tracer) on the same two sheets."""
    import pdf_tag_check as ptc
    out = {}
    for name, folder in ((EXT, ext_dir), ("ours: tiles + our tracer, claude", ours_dir)):
        if not folder:
            continue
        rows = []
        for page, (n, did, title) in ((21, ("1", "P-401", "Irrigation Equalization Tank P&ID")),
                                      (22, ("2", "P-501", "Subsurface Drip Effluent Disposal P&ID"))):
            rows.append({"drawing_id": did, "revision": "Design/build 2021-07", "page": page,
                         "image": str(Path(images) / f"{n}.png"), "extraction": str(Path(folder) / f"{n}.json"),
                         "drawing_number": did, "title": title})
        sub = tmp / f"pahala-{len(out)}"
        manifest = fds.write_manifest(sub, "Pahala WWTP P&IDs (public, EPA docket)", {"method": name, "tool": name, "model": None}, rows)
        result, model = fds.bundle(manifest, sub / "bundle")
        check = ptc.check(sub / "bundle", Path(pdf), [21, 22])
        out[name] = {"line_layers": result["line_layers"]["status"], "flow_direction": {
                         k: v for k, v in (result.get("flow_direction") or {}).items() if k in ("pipe_segments", "directed")},
                     "tag_check": [{"sheet": s["sheet"], "page": s["page"], "matched": len(s.get("matched", [])),
                                    "missed_by_reader": len(s.get("missed_by_reader", [])),
                                    "not_in_text_layer": len(s.get("not_in_text_layer", []))} for s in check["sheets"]]}
    return out


# ---------------------------------------------------------------- report

def num(v, rl=False):
    return f"{v:.1f}" if rl else f"{v:.3f}"


def cell(m, rl=False):
    return num(m["mean"], rl) + ("" if m["min"] == m["max"] else f" ({num(m['min'], rl)}-{num(m['max'], rl)})")


def markdown(doc):
    L = ["# An external reader through the reader slot: pid-to-kg on the development sets", "",
         "Generated by `scripts/external_reader_comparison.py`; do not edit by hand. Development sets only (OPEN100 0-5, "
         "TE revisions A and D, Pahala P-401/P-501): every number here was seen while comparing, none is a "
         "generalization claim. pid-to-kg is [Scott Duncan's public MIT skill]"
         "(https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph), run headless as its README describes "
         f"(commit `{doc['runs']['commit'][:7]}`, {doc['runs']['model_requested']}, one run per sheet). Its graph.json "
         "enters through `scripts/reader_external_kg.py`; the adapter's rules were fixed before any score was seen, and "
         "the key converted through it scores perfect (`scripts/test_reader_external_kg.py`). It is a measured "
         "comparison and a source of ideas, not a dependency. Readings of OPEN100 sheets are CC BY-SA 4.0 derived data "
         "(`predictions/README.md`); the Pahala readings are not in this repository, only their counts.", ""]
    L += ["## Symbols, connections and review load (frozen scorer, beside the controls)", "",
          "Mean over replicate runs with min-max; pid-to-kg and the hybrid are one run. Review load counts corrections per "
          "100 key items (lower is better). Connections are network co-membership, the key's own definition.", ""]
    for set_id, t in doc["symbols"].items():
        L += [f"### {set_id} (keys `{t['keys']}`, sheets {', '.join(t['sheets'])})", "",
              "| Reader | Runs | Review load | Symbol F1 rough | Symbol F1 strict | Connection F1 |", "|---|---|---|---|---|---|"]
        for r in t["rows"]:
            m = r["metrics"]
            L.append(f"| {r['name']} | {r['runs']} | {cell(m['review_load_per_100'], True)} | {cell(m['symbol_f1_rough_classified'])} | "
                     f"{cell(m['symbol_f1_strict_classified'])} | {cell(m['connection_f1'])} |")
        for c, lab in ev.CONTROL_LABELS.items():
            m = t["controls"][c]
            L.append(f"| {lab} | - | {m['review_load_per_100']:.1f} | {m['symbol_f1_rough_classified']:.3f} | "
                     f"{m['symbol_f1_strict_classified']:.3f} | {m['connection_f1']:.3f} |")
        L += ["", "Per sheet, review load (mean of runs):", "",
              "| Reader | " + " | ".join(t["sheets"]) + " |", "|---|" + "---|" * len(t["sheets"])]
        for r in t["rows"]:
            L.append(f"| {r['name']} | " + " | ".join(f"{r['per_sheet'][s]['review_load_per_100']:.1f}" for s in t["sheets"]) + " |")
        L += ["", "Per class, rough F1 with the class required (first run of each reader):", "",
              "| Reader | " + " | ".join(sc.SCORED) + " |", "|---|" + "---|" * len(sc.SCORED)]
        for r in t["rows"]:
            L.append(f"| {r['name']} | " + " | ".join(f"{r['per_class_rough_f1_first_run'][c]:.2f}" for c in sc.SCORED) + " |")
        L += ["", "Valve convention (first run; the scorer's class-free rough match): the key draws a control valve as an "
              "untagged valve body plus a tagged actuator bubble (instrumentation).", "",
              "| Reader | Predicted valves | ...paired with a key instrument bubble | Key valves | ...left unpaired |",
              "|---|---|---|---|---|"]
        for r in t["rows"]:
            d = r["valve_convention_first_run"]
            L.append(f"| {r['name']} | {d['predicted_valves']} | {d['valve_paired_with_key_instrument']} | {d['key_valves']} | "
                     f"{d['key_valves_unpaired']} |")
        L.append("")
    L += ["## Tags on the TE sheets (printed text; letters and digits compared)", "",
          "| Set | Reader | Runs | Tags read exactly | Read, if the symbol was found | Misread as another real tag | Off-page refs read |",
          "|---|---|---|---|---|---|---|"]
    for set_id, rows in doc["tags"].items():
        for name, runs in rows.items():
            tot = lambda k: sum(r[k] for r in runs)  # noqa: E731
            L.append(f"| {set_id} | {name} | {len(runs)} | {tot('read')}/{tot('tags')} | {tot('read_if_found')}/{tot('found')} | "
                     f"{tot('another_real_tag')} | {tot('offpage_refs_read')}/{tot('offpage_refs')} |")
    L += ["", "## Flow direction", "",
          "Two different units, so the rows are not ranked against each other. pid-to-kg directs symbol-to-symbol "
          "pairs along its own FLOWS_TO edges; our bundle directs pipe segments from drawn evidence only. Both are "
          "scored against the same TE truth (the model's streams as drawn, `flow_direction_score.te_truth`).", "",
          "| Set | What | Directed | Directed where the truth reaches | Correct | Precision | Truth covered | Reversed control | Layout control |",
          "|---|---|---|---|---|---|---|---|---|"]
    for set_id, r in doc["own_directions"].items():
        L.append(f"| {set_id} | pid-to-kg's own directed pairs (all) | {r.get('pairs', 0)} | {r.get('scorable', 0)} | "
                 f"{r.get('correct', 0)} | {r['precision']} | - | {r['controls']['reversed']} | {r['controls']['layout']} |")
        L.append(f"| {set_id} | pid-to-kg's own directed pairs, drawn arrows only ('shown') | {r.get('pairs_shown', 0)} | "
                 f"{r.get('scorable_shown', 0)} | {r.get('correct_shown', 0)} | {r['precision_shown']} | - | - | - |")
        for name, p in doc["product_path"][set_id].items():
            d = p.get("direction_scored")
            if d:
                L.append(f"| {set_id} | our bundle on {name}: pipe segments | {p.get('directed', 0)} of {p.get('pipe_segments', 0)} | "
                         f"{d.get('directed', 0)} | {d.get('correct', 0)} | {d['precision']} | "
                         f"{d.get('correct', 0)}/{d.get('truth_directed', 0)} | {d['controls']['reversed']['precision']} | "
                         f"{d['controls']['layout']['precision']} |")
    L += ["", "Our readers' own bundle numbers on the same sets are in `out/round6/flow_direction_dev.md`: TE A 32 of 42 "
          "segments directed, 22/22 correct, 22/25 of the truth covered, on every run; TE D (key symbols with our tracer, "
          "no model reading) 22 of 101, 16/16, 16/53.", "", "## The drawing-set bundle (product path)", "",
          "| Set | Reading | Line layers | Pipe segments | Directed | Note |", "|---|---|---|---|---|---|"]
    for set_id, rows in doc["product_path"].items():
        for name, p in rows.items():
            if "refused_by_intake" in p:
                L.append(f"| {set_id} | {name} | refused | - | - | {p['refused_by_intake'][:120]} |")
                continue
            L.append(f"| {set_id} | {name} | {p['line_layers']} | {p.get('pipe_segments', '-')} | {p.get('directed', '-')} | "
                     f"{(p.get('line_layers_reason') or '')[:120]} |")
    lp = doc["loops"]
    L += ["", "## Control loops (TE, truth `data/te_control_loops.json`, 11 valve loops and 8 cascades that run)", "",
          "A valve loop counts when one pid-to-kg loop holds both its sensor tag and its valve tag; a cascade when the "
          "loop holding the master's sensor cascades to the loop holding the slave controller. Ours: " + lp["ours"] + ".", "",
          "| Set | Valve loops found | Sensor-final pairs (correct) | Cascades found | Loops by kind |", "|---|---|---|---|---|"]
    for set_id in ("te-a", "te-d"):
        r = lp[set_id]
        L.append(f"| {set_id} | {r['valve_loops_found']}/{r['truth_valve_loops']} | {r['sensor_final_pairs']} ({r['pairs_correct']}) | "
                 f"{r['cascades_found']}/{r['truth_cascades']} | {r['loops_by_kind']} |")
    o = doc["offpage"]
    L += ["", "## Off-page links on OPEN100 0-5 (key `examples/own-drawing/offpage-key.json`, 6 continuations)", "",
          f"pid-to-kg's builder across the six sheets: {o['links']} links, {o['correct']} correct, "
          f"{o['continuations_found']}/{o['continuations']} continuations ({o['links_mapped_to_key_connectors']} links "
          f"had both ends matched to a key connector by box). Ours (A407): {o['ours_A407']}.", ""]
    if doc.get("pahala"):
        L += ["## Pahala P-401 and P-501 (scripts/pdf_tag_check.py against the PDF text layer, through the bundle)", "",
              "| Reader | PDF page | Matched | Tag-shaped text the reader missed | Read, not in the text layer | Line layers |",
              "|---|---|---|---|---|---|"]
        for name, p in doc["pahala"].items():
            for s in p["tag_check"]:
                L.append(f"| {name} | {s['page']} | {s['matched']} | {s['missed_by_reader']} | {s['not_in_text_layer']} | {p['line_layers']} |")
        L += ["", "The readers saw different inputs: ours a PNG render of each page, pid-to-kg the PDF page itself, whose text "
              "layer its own QA uses as hints. No symbol key exists for Pahala.", ""]
    L += ["## Run cost (pid-to-kg, per sheet)", "",
          "| Sheet | Wall s | Turns | Output tokens | Cache read | Cache write | List-price equivalent $ | Tiles read / non-blank |",
          "|---|---|---|---|---|---|---|---|"]
    for name, r in doc["runs"]["runs"].items():
        t, c = r["tokens"], r["coverage"]
        L.append(f"| {name} | {r['wall_s']} | {r['num_turns']} | {t['output']} | {t['cache_read']} | {t['cache_creation']} | "
                 f"{r['cost_usd_list_equivalent']:.2f} | {r['image_reads']['tiles']}/{c['non_blank_tiles']} |")
    L.append("")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output prefix: writes <prefix>.json and <prefix>.md")
    ap.add_argument("--pahala-images", help="folder with the Pahala renders 1.png (P-401) and 2.png (P-501)")
    ap.add_argument("--pahala-ext", help="folder with the external reader's converted 1.json and 2.json")
    ap.add_argument("--pahala-ours", help="folder with our reading's run records 1.json and 2.json")
    ap.add_argument("--pahala-pdf", help="the Pahala PDF (pages 21 and 22)")
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        symbols = symbol_tables(tmp)
        tags = tag_tables()
        product, truths = product_path(symbols, tmp)
        doc = {"runs": json.loads((ROOT / "out/ext_pidkg/runs.json").read_text(encoding="utf-8")),
               "symbols": {k: {kk: vv for kk, vv in v.items() if kk != "hybrid_dir"} for k, v in symbols.items()},
               "tags": tags, "product_path": product, "own_directions": own_directions(truths), "loops": loops(),
               "offpage": offpage(),
               "pahala": pahala(a.pahala_images, a.pahala_ext, a.pahala_ours, a.pahala_pdf, tmp)
               if a.pahala_images and a.pahala_pdf else None}
    out = Path(a.out)
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    out.with_suffix(".md").write_text(markdown(doc), encoding="utf-8", newline="\n")
    print(markdown(doc))


if __name__ == "__main__":
    sys.exit(main())
