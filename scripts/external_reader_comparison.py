"""Compare an external reader that entered through the reader slot with our readers, on the development sets only.

The first external reader is pid-to-kg (Scott Duncan's public MIT skill,
https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph), run headless as its README describes, its graph.json
converted by scripts/reader_external_kg.py. Its readings are committed like any reader's: three replicate runs per
development sheet (predictions/ext-pidkg-r1..r3, ext-pidkg-te-a-r1..r3, ext-pidkg-te-d-r1..r3) and two runs of
each ablation (ext-pidkg-noocr-*, ext-pidkg-noqa-*, ext-pidkg-2x2-*). The relations its own builder assembled across
each set (loops, off-page links, directed pairs) are in out/ext_pidkg/relations/, the run costs and recipe in
out/ext_pidkg/runs.json. This script writes no scorer of its own for symbols, connections, tags or directions:

  symbols, connections, review load   scripts/evaluate_vendor.py (the frozen scorer beside the four controls, replicate
                                      runs as replicates), per sheet and per class, beside our committed readings
  tags (TE)                           score_te_roundtrip.score_sheet's tag rows (printed text, letters and digits)
  tags (Pahala, optional)             the drawing-set bundle, then scripts/pdf_tag_check.py against the PDF text layer
  product path                        scripts/import_drawing_set.py on run 1, and on run 1's symbols with our tracer's
                                      links ("hybrid", trace_connections.trace with its defaults)
  flow direction (TE)                 flow_direction_score's truth and flow_of, on the external reader's directed pairs
  off-page links (OPEN100 0-5)        examples/own-drawing/offpage-key.json, connectors matched by box to the key's ids
  control loops (TE)                  data/te_control_loops.json; ours builds no loops yet, so there is no row of ours

Decision rule (docs/GOAL_ROUND6.md: a difference counts only beyond the run and sheet spread). Two readers' review
loads differ only when both hold: (1) their run ranges do not overlap (one run is a range of one value), and (2) the
95% interval of a paired bootstrap over sheets of the difference (2,000 draws, seed 7: sheets resampled with
replacement, each reader's corrections averaged over its runs per sheet, divided by the same key items) excludes 0.
Otherwise the comparison says "within spread". Run spread on six or three fixed sheets is not a significance test.

Development sets only: OPEN100 sheets 0-5, TE revisions A and D (sheets 101-103), Pahala P-401/P-501 (not in the
repository; give --pahala-images, --pahala-ext-root, --pahala-ours and --pahala-pdf). Held-out sheets are refused.

    python scripts/external_reader_comparison.py --out out/ext_pidkg/comparison \\
        [--pahala-images DIR --pahala-ext-root DIR --pahala-ours DIR --pahala-pdf pahala.pdf]

Needs OpenCV and NumPy (the tracer, line layers and direction truth) and git history for revision A's drawer.
No model calls, no network.
"""
import argparse
import json
import random
import re
import statistics
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
BASE = f"{EXT} (its own links)"
VARIANT_NAMES = {"": BASE, "noocr": f"{EXT}, OCR off", "noqa": f"{EXT}, QA re-check loop off",
                 "2x2": f"{EXT}, 2x2 tiles"}
PART = {"open100-dev": "", "te-a": "-te-a", "te-d": "-te-d"}
ABLATIONS = {"open100-dev": ("noqa", "2x2"), "te-a": ("noocr",), "te-d": ("noocr", "noqa")}
OURS = {
    "open100-dev": {"r2-tiles-trace (tiles + our tracer)": {t: ["r2-tiles-trace"] for t in ("claude", "codex", "gemini")},
                    "r2-tiles-2x2 (tiles, model links)": {t: ["r2-tiles-2x2", "r2-tiles-2x2-repeat"] for t in ("claude", "codex", "gemini")}},
    "te-a": {"te-clean-trace (tiles + our tracer)": {t: [f"te-clean-trace-r{r}" for r in range(1, 6)] for t in ("claude", "codex")},
             "te-clean-tiles (tiles, model links)": {t: [f"te-clean-tiles-r{r}" for r in range(1, 6)] for t in ("claude", "codex")}},
    "te-d": {},
}
KEYS = {"open100-dev": OPEN100, **TE_DIR}
SHEETS = {"open100-dev": ["0", "1", "2", "3", "4", "5"], "te-a": fds.TE_SHEETS, "te-d": fds.TE_SHEETS}
HELD_OUT = {"6", "7", "8", "9", "10", "11"}
LENIENT = lambda t: re.sub(r"[^A-Z0-9]", "", str(t or "").upper())  # noqa: E731
B, SEED = 2000, 7


def refuse_held_out(keys, sheets):
    if Path(keys) == OPEN100 and set(sheets) & HELD_OUT:
        raise SystemExit("OPEN100 sheets 6-11 are held out")


def preds_dir(label, tool=EXT):
    return ROOT / "predictions" / label / tool


def ext_labels(set_id, abl=""):
    reps = ("r1", "r2") if abl else ("r1", "r2", "r3")
    pre = f"ext-pidkg-{abl}" if abl else "ext-pidkg"
    return [f"{pre}{PART[set_id]}-{r}" for r in reps]


def variants(set_id):
    """{reader name: (labels, relation-file variants)} for the external reader on one set."""
    out = {BASE: (ext_labels(set_id), ["r1", "r2", "r3"])}
    for abl in ABLATIONS[set_id]:
        out[VARIANT_NAMES[abl]] = (ext_labels(set_id, abl), [f"{abl}-r1", f"{abl}-r2"])
    return out


def spread(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"mean": round(statistics.fmean(vals), 4), "min": min(vals), "max": max(vals), "n": len(vals)}


# ---------------------------------------------------------------- symbols, connections, review load

def by_class(keys, sheets, folder):
    """Per-class rough F1, plus a convention diagnostic from the scorer's own class-free rough match: predicted valves
    paired with a key instrument bubble (a control valve read as one item where the key draws a valve body and an
    actuator bubble), and key valves left unpaired."""
    acc = {c: {"tp": 0, "predicted": 0, "in_key": 0} for c in sc.SCORED}
    diag = {"predicted_valves": 0, "valve_paired_with_key_instrument": 0, "key_valves": 0, "key_valves_unpaired": 0}
    for s in sheets:
        pred, _, _ = ev.load_prediction(folder / f"{s}.json")
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
    classes = [by_class(keys, sheets, Path(f)) for f in folders]
    row = {"name": name, "runs": len(folders), "controls_ok": r["controls_ok"],
           "metrics": {m: {k: rep[m][k] for k in ("mean", "min", "max")} for m, _ in ev.HEADLINE},
           "sheet_bootstrap_95": {m: rep[m].get("bootstrap_95") for m, _ in ev.HEADLINE},
           "per_sheet": {s: r["per_sheet"][s]["vendor_mean"] for s in sheets},
           "per_class_rough_f1": {c: spread([cl[0][c]["f1"] for cl in classes]) for c in sc.SCORED},
           "valve_convention_first_run": classes[0][1], "missing_or_failed": r["missing_or_failed"],
           "_corrections": {s: [run["per_sheet"][s]["corrections"] for run in r["runs"]] for s in sheets},
           "_key_items": {s: r["runs"][0]["per_sheet"][s]["key_items"] for s in sheets}}
    return row, r["controls"]


def decide(a, b, sheets):
    """The decision rule in the module docstring, on review load: a (the external reader) against b."""
    ra, rb = a["metrics"]["review_load_per_100"], b["metrics"]["review_load_per_100"]
    overlap = not (ra["max"] < rb["min"] or rb["max"] < ra["min"])
    ca = {s: statistics.fmean(a["_corrections"][s]) for s in sheets}
    cb = {s: statistics.fmean(b["_corrections"][s]) for s in sheets}
    k = a["_key_items"]
    diff = lambda pick: 100 * (sum(ca[s] for s in pick) - sum(cb[s] for s in pick)) / sum(k[s] for s in pick)  # noqa: E731
    rng = random.Random(SEED)
    draws = sorted(diff([rng.choice(sheets) for _ in sheets]) for _ in range(B))
    lo, hi = draws[int(0.025 * B)], draws[int(0.975 * B) - 1]
    beyond = not overlap and (lo > 0 or hi < 0)
    d = diff(sheets)
    return {"against": b["name"], "difference": round(d, 1), "sheet_bootstrap_95": [round(lo, 1), round(hi, 1)],
            "run_ranges_overlap": overlap,
            "verdict": ("higher review load" if d > 0 else "lower review load") + " beyond run and sheet spread"
            if beyond else "within spread"}


def hybrid_folder(set_id, label, tmp):
    """One external run's symbols with our tracer's links (trace_connections defaults), as run records."""
    import trace_connections as tc
    out = tmp / f"hybrid-{label}" / EXT
    out.mkdir(parents=True)
    for s in SHEETS[set_id]:
        rec = json.loads((preds_dir(label) / f"{s}.json").read_text(encoding="utf-8"))
        rec.pop("schema", None)
        links = tc.trace(KEYS[set_id] / f"{s}.png", rec["prediction"]["symbols"])
        rec["prediction"] = {"symbols": rec["prediction"]["symbols"],
                             "connections": [{"from": l["from"], "to": l["to"]} for l in links]}
        rec["source_label"] = label
        rec["tracer"] = {"script": "scripts/trace_connections.py", "mode": "replace"}
        (out / f"{s}.json").write_text(json.dumps(rec), encoding="utf-8")
    return out


def symbol_tables(tmp):
    out = {}
    for set_id in SHEETS:
        keys, sheets = KEYS[set_id], SHEETS[set_id]
        refuse_held_out(keys, sheets)
        rows, controls = [], None
        for name, (labels, _) in variants(set_id).items():
            row, ctl = reader_row(keys, sheets, [preds_dir(l) for l in labels], name)
            controls = controls or ctl
            rows.append(row)
        hyb = [hybrid_folder(set_id, l, tmp) for l in ext_labels(set_id)]
        rows.insert(1, reader_row(keys, sheets, hyb, f"{EXT} symbols + our tracer (hybrid)")[0])
        for name, tools in OURS[set_id].items():
            for tool, labels in tools.items():
                rows.append(reader_row(keys, sheets, [preds_dir(l, tool) for l in labels], f"ours: {name}, {tool}")[0])
        base = rows[0]
        decisions = [decide(base, r, sheets) for r in rows[1:]]
        for r in rows:
            r.pop("_corrections"), r.pop("_key_items")
        out[set_id] = {"keys": str(keys.relative_to(ROOT)).replace("\\", "/"), "sheets": sheets, "rows": rows,
                       "controls": controls, "decisions": decisions, "hybrid_dir": hyb[0]}
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
        rows = {name: te_tags(set_id, [preds_dir(l) for l in labels]) for name, (labels, _) in variants(set_id).items()}
        for name, tools in OURS[set_id].items():
            for tool, labels in tools.items():
                rows[f"ours: {name}, {tool}"] = te_tags(set_id, [preds_dir(l, tool) for l in labels])
        out[set_id] = rows
    return out


# ---------------------------------------------------------------- the product path (drawing-set bundle), run 1

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
    for set_id in SHEETS:
        rows = {}
        for name, folder in ((f"{BASE}, run 1", preds_dir(ext_labels(set_id)[0])),
                             (f"{EXT} symbols + our tracer (hybrid), run 1", symbols[set_id]["hybrid_dir"])):
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
                rec.update(fds.share(model))
                if set_id in truths:
                    sheet_of = {s: str(n) for n, s in enumerate(fds.TE_SHEETS)}
                    rec["direction_scored"] = fds.score_directions(model, truths[set_id], sheet_of)["total"]
            rows[name] = rec
        out[set_id] = rows
    return out, truths


# ---------------------------------------------------------------- the external reader's own relations, per run

def relations(set_id, v):
    name = f"{set_id}.json" if v == "r1" else f"{set_id}@{v}.json"
    return json.loads((ROOT / "out/ext_pidkg/relations" / name).read_text(encoding="utf-8"))


def directions_one(set_id, label, rel, truths):
    res = defaultdict(int)
    for s in SHEETS[set_id]:
        raw = truths[set_id + "/raw"][s]
        png, gml = KEYS[set_id] / f"{s}.png", KEYS[set_id] / f"{s}.graphml"
        pred, _, _ = ev.load_prediction(preds_dir(label) / f"{s}.json")
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
    r["layout_control"] = round(r.get("layout_correct", 0) / r["scorable"], 3) if r.get("scorable") else None
    r["reversed_control"] = round(1 - r["precision"], 3) if r["precision"] is not None else None
    return r


def own_directions(truths):
    return {set_id: {name: [directions_one(set_id, l, relations(set_id, v), truths) for l, v in zip(labels, vs)]
                     for name, (labels, vs) in variants(set_id).items()} for set_id in ("te-a", "te-d")}


def loops_one(rel):
    truth = json.loads((ROOT / "data/te_control_loops.json").read_text(encoding="utf-8"))
    valve = [(l["id"], l["measurement"]["tag"], l["output"]["tag"]) for l in truth["loops"]
             if l["runs"] and l["output"]["kind"] == "final_element"]
    casc = [(l["id"], l["measurement"]["tag"], l["output"]["tag"]) for l in truth["loops"]
            if l["runs"] and l["output"]["kind"] == "setpoint"]
    L = [{**x, "S": {LENIENT(t) for t in x["sensors"]}, "C": {LENIENT(t) for t in x["controllers"]},
          "F": {LENIENT(t) for t in x["final_elements"]}} for x in rel["loops"]]
    by_label = {x["loop"]: x for x in L}
    got_valve = [lid for lid, s, f in valve if any(LENIENT(s) in x["S"] and LENIENT(f) in x["F"] for x in L)]
    pairs = {(a, b) for x in L if x["kind"] in ("control", "interlock") for a in x["S"] for b in x["F"]}
    truth_pairs = {(LENIENT(s), LENIENT(f)) for _, s, f in valve}
    got_casc = [lid for lid, s, ctl in casc
                if any((m := by_label.get(c["master"])) and (v := by_label.get(c["slave"])) and LENIENT(s) in m["S"]
                       and LENIENT(ctl) in v["C"] for c in rel["cascades"])]
    return {"truth_valve_loops": len(valve), "valve_loops_found": len(got_valve), "found_ids": got_valve,
            "sensor_final_pairs": len(pairs), "pairs_correct": len(pairs & truth_pairs),
            "truth_cascades": len(casc), "cascades_found": len(got_casc), "cascade_ids": got_casc,
            "loops_by_kind": rel["stats"].get("loops_by_type")}


def loops():
    out = {set_id: {name: [loops_one(relations(set_id, v)) for v in vs] for name, (_, vs) in variants(set_id).items()}
           for set_id in ("te-a", "te-d")}
    out["ours"] = "no loops: round 6 increment 3 (signal_to, controls, loops) is not built"
    return out


def offpage_one(rel, truth, to_key):
    pairs = []
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
        pairs.append({"ends": ends, "labels": [link["from"]["label"], link["to"]["label"]],
                      "correct": bool(all(ends) and frozenset(ends) in truth)})
    return {"links": len(pairs), "correct": sum(p["correct"] for p in pairs),
            "continuations_found": len({frozenset(p["ends"]) for p in pairs if p["correct"]}), "pairs": pairs}


def offpage():
    key = json.loads((ROOT / "examples/own-drawing/offpage-key.json").read_text(encoding="utf-8"))
    truth = {frozenset((c["a"], c["b"])) for c in key["continuations"]}
    to_key = {}
    for s in fds.DEV_OPEN100:
        ref, _, _ = ev.load_prediction(ROOT / "predictions/r2-tiles-trace/codex" / f"{s}.json")
        to_key[s] = {x["id"]: x for x in sc.valid_symbols(ref) if x["class"] == "inlet/outlet"}
    return {"key": "examples/own-drawing/offpage-key.json", "continuations": len(truth),
            "runs": {name: [offpage_one(relations("open100-dev", v), truth, to_key) for v in vs]
                     for name, (_, vs) in variants("open100-dev").items()},
            "ours_A407": "drawing-set import 5 pairs, 5 correct, 5/6 continuations; offpage_pairing alone 2/2, 2/6"}


def pahala(images, ext_root, ours_dir, pdf, tmp):
    """Optional: Pahala P-401/P-501 through the drawing-set bundle, then pdf_tag_check against the text layer, for
    every external run and ablation run found under ext_root (pahala, pahala@r2, ...) and ours."""
    import pdf_tag_check as ptc
    readers = [(f"{BASE}, run 1", Path(ext_root) / "pahala")]
    readers += [(f"{BASE}, run {v[1]}" if v.startswith("r") else f"{VARIANT_NAMES[v.split('-')[0]]}, run {v[-1]}",
                 Path(ext_root) / f"pahala@{v}") for v in ("r2", "r3", "noocr-r1", "noocr-r2")]
    if ours_dir:
        readers.append(("ours: tiles + our tracer, claude", Path(ours_dir)))
    out = {}
    for name, folder in readers:
        if not (folder / "1.json").exists():
            continue
        rows = [{"drawing_id": did, "revision": "Design/build 2021-07", "page": page,
                 "image": str(Path(images) / f"{n}.png"), "extraction": str(folder / f"{n}.json"),
                 "drawing_number": did, "title": title}
                for page, n, did, title in ((21, "1", "P-401", "Irrigation Equalization Tank P&ID"),
                                            (22, "2", "P-501", "Subsurface Drip Effluent Disposal P&ID"))]
        sub = tmp / f"pahala-{len(out)}"
        manifest = fds.write_manifest(sub, "Pahala WWTP P&IDs (public, EPA docket)", {"method": name, "tool": EXT, "model": None}, rows)
        result, _ = fds.bundle(manifest, sub / "bundle")
        check = ptc.check(sub / "bundle", Path(pdf), [21, 22])
        out[name] = {"line_layers": result["line_layers"]["status"],
                     "tag_check": [{"sheet": s["sheet"], "page": s["page"], "matched": len(s.get("matched", [])),
                                    "missed_by_reader": len(s.get("missed_by_reader", [])),
                                    "not_in_text_layer": len(s.get("not_in_text_layer", []))} for s in check["sheets"]]}
    return out


def costs(runs):
    groups = defaultdict(list)
    for r in runs.values():
        v = r["variant"]
        groups[(r["set"], "replicates r1-r3" if "-" not in v else v.split("-")[0])].append(r)
    return {f"{s} | {g}": {"runs": len(rs), "wall_s_per_run": spread([r["wall_s"] for r in rs]),
                           "turns": spread([r["num_turns"] for r in rs]),
                           "usd_per_run": spread([r["cost_usd_list_equivalent"] for r in rs]),
                           "usd_total": round(sum(r["cost_usd_list_equivalent"] for r in rs), 2),
                           "output_tokens": sum(r["tokens"]["output"] for r in rs),
                           "cache_read_tokens": sum(r["tokens"]["cache_read"] for r in rs),
                           "tiles_opened_share": spread([r["image_reads"]["tiles"] / r["coverage"]["non_blank_tiles"]
                                                         for r in rs if r["coverage"]["non_blank_tiles"]])}
            for (s, g), rs in sorted(groups.items())}


# ---------------------------------------------------------------- report

def num(v, rl=False):
    return f"{v:.1f}" if rl else f"{v:.3f}"


def cell(m, rl=False):
    return num(m["mean"], rl) + ("" if m["min"] == m["max"] else f" ({num(m['min'], rl)}-{num(m['max'], rl)})")


def frac(runs, a, b):
    vals = [r[a] / r[b] for r in runs if r[b]]
    s = spread(vals)
    tot = f"{sum(r[a] for r in runs)}/{sum(r[b] for r in runs)}"
    return f"{tot} ({s['min']:.2f}-{s['max']:.2f})" if s and s["min"] != s["max"] else tot


def rng_txt(vals, fmt="{}"):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"
    lo, hi = min(vals), max(vals)
    return fmt.format(lo) if lo == hi else f"{fmt.format(lo)}-{fmt.format(hi)}"


def markdown(doc):
    rec = doc["runs"]["recipe"]
    L = ["# An external reader through the reader slot: pid-to-kg on the development sets", "",
         "Generated by `scripts/external_reader_comparison.py`; do not edit by hand. Development sets only (OPEN100 0-5, "
         "TE revisions A and D, Pahala P-401/P-501): every number here was seen while comparing, none is a "
         "generalization claim. pid-to-kg is [Scott Duncan's public MIT skill]"
         "(https://github.com/ScottDuncanAI/PID-to-Knowledge-Graph); it is a measured comparison and a source of ideas "
         "here, not a dependency. Its graph.json enters through `scripts/reader_external_kg.py`; the adapter's rules were "
         "fixed before any score was seen, and the key converted through it scores perfect "
         "(`scripts/test_reader_external_kg.py`). Readings of OPEN100 sheets are CC BY-SA 4.0 derived data "
         "(`predictions/README.md`); the Pahala readings are not in this repository, only their counts.", "",
         "## How it was run, and where that differs from a person using it", "",
         f"- Commit `{doc['runs']['commit'][:7]}`, {doc['runs']['model_requested']}, Claude Code headless (`claude -p`), "
         "the skill copied into a fresh project folder per run, Python 3.12 with its requirements (OCR on). Exact prompt, "
         "flags and harness hashes: `out/ext_pidkg/runs.json`.",
         "- Three runs per development sheet with the identical recipe; ablations two runs each.",
         "- Not how its README describes a person using it: (1) OPEN100 and TE sheets are PNGs, saved as one-page PDFs at a "
         "declared 300 dpi because the skill reads PDFs, so they take its scanned-page route (upscaling, contrast); "
         "(2) headless, so nobody answered its questions (it was told to choose and note); (3) Python and packages were "
         "installed beforehand, not by the skill; (4) one run per sheet, with each set assembled afterwards by its own "
         "builder (no model), so its model never re-checked cross-sheet links; (5) shell access was limited to "
         "`python -I` and `ls`, so a few shell calls per run were refused and it worked around them.",
         f"- Ablations, each a user-level setting with no change to its code: OCR off = {rec['variants']['noocr']}; "
         f"QA loop off = {rec['variants']['noqa']}; 2x2 tiles = {rec['variants']['2x2']}", "",
         "## Decision rule", "",
         "Review loads differ only when the run ranges do not overlap and the 95% paired sheet-bootstrap interval of the "
         "difference excludes 0 (module docstring). Our OPEN100 traced readings are one run each, so their run range is "
         "a single value; our validation-set replicates (the leaderboard: claude 27.2-31.6 over five runs on other "
         "sheets) show a run spread of a few points.", ""]
    L += ["## Symbols, connections and review load (frozen scorer, beside the controls)", "",
          "Mean over runs with the run range. Review load counts corrections per 100 key items (lower is better). "
          "Connections are network co-membership, the key's own definition.", ""]
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
        L += ["", f"Decision rule, {t['rows'][0]['name']} against each row:", "",
              "| Against | Difference in review load | Sheet bootstrap 95% | Run ranges overlap | Verdict |", "|---|---|---|---|---|"]
        for d in t["decisions"]:
            L.append(f"| {d['against']} | {d['difference']:+.1f} | {d['sheet_bootstrap_95'][0]:+.1f} to {d['sheet_bootstrap_95'][1]:+.1f} | "
                     f"{'yes' if d['run_ranges_overlap'] else 'no'} | {d['verdict']} |")
        L += ["", "Per sheet, review load (mean of runs):", "",
              "| Reader | " + " | ".join(t["sheets"]) + " |", "|---|" + "---|" * len(t["sheets"])]
        for r in t["rows"]:
            L.append(f"| {r['name']} | " + " | ".join(f"{r['per_sheet'][s]['review_load_per_100']:.1f}" for s in t["sheets"]) + " |")
        L += ["", "Per class, rough F1 with the class required (mean of runs, range when it varies):", "",
              "| Reader | " + " | ".join(sc.SCORED) + " |", "|---|" + "---|" * len(sc.SCORED)]
        for r in t["rows"]:
            L.append(f"| {r['name']} | " + " | ".join(cell(r["per_class_rough_f1"][c]).replace(".000", ".00")
                                                      for c in sc.SCORED) + " |")
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
          "Totals over runs, with the per-run share range when it varies.", "",
          "| Set | Reader | Runs | Tags read exactly | Read, if the symbol was found | Misread as another real tag | Off-page refs read |",
          "|---|---|---|---|---|---|---|"]
    for set_id, rows in doc["tags"].items():
        for name, runs in rows.items():
            L.append(f"| {set_id} | {name} | {len(runs)} | {frac(runs, 'read', 'tags')} | {frac(runs, 'read_if_found', 'found')} | "
                     f"{sum(r['another_real_tag'] for r in runs)} | {frac(runs, 'offpage_refs_read', 'offpage_refs')} |")
    L += ["", "## Flow direction (TE)", "",
          "pid-to-kg's own directed symbol pairs along its FLOWS_TO edges, scored against the TE stream truth "
          "(`flow_direction_score.te_truth`); per-run ranges. TE is drawn left to right, so the layout control is nearly as "
          "precise: these sheets cannot separate drawn evidence from layout. Our bundle directs pipe segments, a different "
          "unit (`out/round6/flow_direction_dev.md`: TE A 22/22 correct, 22/25 of the truth covered, on every run; TE D, "
          "key symbols with our tracer, 16/16, 16/53).", "",
          "| Set | Reader | Runs | Directed pairs | Where the truth reaches | Correct | Precision | Layout control |",
          "|---|---|---|---|---|---|---|---|"]
    for set_id, rows in doc["own_directions"].items():
        for name, runs in rows.items():
            L.append(f"| {set_id} | {name} | {len(runs)} | {rng_txt([r.get('pairs') for r in runs])} | "
                     f"{rng_txt([r.get('scorable') for r in runs])} | {rng_txt([r.get('correct') for r in runs])} | "
                     f"{rng_txt([r['precision'] for r in runs], '{:.3f}')} | {rng_txt([r['layout_control'] for r in runs], '{:.3f}')} |")
    L += ["", "Run 1 through our bundle (product path): its own links are accepted when our tracer re-traces exactly the "
          "same links, otherwise the line layers are skipped; its symbols with our tracer always get them.", "",
          "| Set | Reading | Line layers | Pipe segments | Directed | Direction precision | Note |", "|---|---|---|---|---|---|---|"]
    for set_id, rows in doc["product_path"].items():
        for name, p in rows.items():
            if "refused_by_intake" in p:
                L.append(f"| {set_id} | {name} | refused | - | - | - | {p['refused_by_intake'][:100]} |")
                continue
            d = p.get("direction_scored")
            prec = f"{d['correct']}/{d['directed']}, truth covered {d['correct']}/{d['truth_directed']}" if d else "-"
            L.append(f"| {set_id} | {name} | {p['line_layers']} | {p.get('pipe_segments', '-')} | {p.get('directed', '-')} | "
                     f"{prec} | {(p.get('line_layers_reason') or '')[:100]} |")
    lp = doc["loops"]
    L += ["", "## Control loops (TE, truth `data/te_control_loops.json`: 11 valve loops and 8 cascades that run)", "",
          "A valve loop counts when one pid-to-kg loop holds both its sensor tag and its valve tag; a cascade when the "
          "loop holding the master's sensor cascades to the loop holding the slave controller. A provisional comparison "
          "rule, not a registered scorer; the TE sheets are drawn by this repository from the model the truth comes from, "
          "so these are upper bounds. TE A draws no controllers or signal lines, so its loop truth is not on the drawing. "
          "Ours: " + lp["ours"] + ".", "",
          "| Set | Reader | Runs | Valve loops found | Sensor-final pairs | ...correct | Cascades found |", "|---|---|---|---|---|---|---|"]
    for set_id in ("te-a", "te-d"):
        for name, runs in lp[set_id].items():
            L.append(f"| {set_id} | {name} | {len(runs)} | {rng_txt([r['valve_loops_found'] for r in runs])}/11 | "
                     f"{rng_txt([r['sensor_final_pairs'] for r in runs])} | {rng_txt([r['pairs_correct'] for r in runs])} | "
                     f"{rng_txt([r['cascades_found'] for r in runs])}/8 |")
    o = doc["offpage"]
    L += ["", "## Off-page links on OPEN100 0-5 (key `examples/own-drawing/offpage-key.json`, 6 continuations)", "",
          "| Reader | Runs | Links | Correct | Continuations found |", "|---|---|---|---|---|"]
    for name, runs in o["runs"].items():
        L.append(f"| {name} | {len(runs)} | {rng_txt([r['links'] for r in runs])} | {rng_txt([r['correct'] for r in runs])} | "
                 f"{rng_txt([r['continuations_found'] for r in runs])}/6 |")
    L += ["", f"Ours (A407, one reading): {o['ours_A407']}.", ""]
    if doc.get("pahala"):
        L += ["## Pahala P-401 and P-501 (scripts/pdf_tag_check.py against the PDF text layer, through the bundle)", "",
              "| Reader | P-401 matched / missed / not in text layer | P-501 matched / missed / not in text layer |", "|---|---|---|"]
        for name, p in doc["pahala"].items():
            c = {s["page"]: s for s in p["tag_check"]}
            L.append(f"| {name} | " + " | ".join(f"{c[g]['matched']} / {c[g]['missed_by_reader']} / {c[g]['not_in_text_layer']}"
                                                 for g in (21, 22)) + " |")
        L += ["", "The readers saw different inputs: ours a PNG render of each page, pid-to-kg the PDF page itself, whose text "
              "layer its own QA uses as hints. A run that rewrites a printed tag into another order (P-501 prints 'ZSO 500, "
              "101'; a run may record '500-ZSO-101') reads as not printed. No symbol key exists for Pahala.", ""]
    L += ["## Run cost (pid-to-kg)", "",
          "List-price equivalent as the CLI reports it; the runs used a subscription. Tiles opened is the share of non-blank "
          "tiles the run actually opened as images; every run listed all of them as reviewed.", "",
          "| Set and variant | Runs | Wall s per run | Turns | USD per run | USD total | Output tokens | Cache-read tokens | Tiles opened |",
          "|---|---|---|---|---|---|---|---|---|"]
    for g, c in doc["costs"].items():
        L.append(f"| {g} | {c['runs']} | {c['wall_s_per_run']['mean']:.0f} ({c['wall_s_per_run']['min']}-{c['wall_s_per_run']['max']}) | "
                 f"{c['turns']['mean']:.0f} ({c['turns']['min']}-{c['turns']['max']}) | {c['usd_per_run']['mean']:.2f} | {c['usd_total']:.2f} | "
                 f"{c['output_tokens']} | {c['cache_read_tokens']} | {c['tiles_opened_share']['mean']:.2f} "
                 f"({c['tiles_opened_share']['min']:.2f}-{c['tiles_opened_share']['max']:.2f}) |")
    tot = doc["runs"]["runs"]
    vo = rec.get("voided")
    L += ["", f"Scored runs: {len(tot)}, {sum(r['wall_s'] for r in tot.values())} s of run time (several at once: "
          f"{rec['concurrency']}), {sum(r['cost_usd_list_equivalent'] for r in tot.values()):.2f} USD list-price "
          "equivalent. Our claude reading of OPEN100 0-5 (r2-tiles-trace): 547 s, 2.84 USD notional, one run."]
    if vo:
        L += ["", f"Set aside unscored: {vo['runs']} runs, {vo['wall_s']} s, {vo['usd_list_equivalent']:.2f} USD. {vo['why']}"]
    L.append("")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output prefix: writes <prefix>.json and <prefix>.md")
    ap.add_argument("--pahala-images", help="folder with the Pahala renders 1.png (P-401) and 2.png (P-501)")
    ap.add_argument("--pahala-ext-root", help="folder holding pahala/, pahala@r2/, ...: the external runs, converted")
    ap.add_argument("--pahala-ours", help="folder with our reading's run records 1.json and 2.json")
    ap.add_argument("--pahala-pdf", help="the Pahala PDF (pages 21 and 22)")
    a = ap.parse_args(argv)
    runs = json.loads((ROOT / "out/ext_pidkg/runs.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        symbols = symbol_tables(tmp)
        product, truths = product_path(symbols, tmp)
        doc = {"runs": runs, "symbols": {k: {kk: vv for kk, vv in v.items() if kk != "hybrid_dir"} for k, v in symbols.items()},
               "tags": tag_tables(), "product_path": product, "own_directions": own_directions(truths), "loops": loops(),
               "offpage": offpage(), "costs": costs(runs["runs"]),
               "pahala": pahala(a.pahala_images, a.pahala_ext_root, a.pahala_ours, a.pahala_pdf, tmp)
               if a.pahala_images and a.pahala_pdf and a.pahala_ext_root else None}
    out = Path(a.out)
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8", newline="\n")
    out.with_suffix(".md").write_text(markdown(doc), encoding="utf-8", newline="\n")
    print(markdown(doc))


if __name__ == "__main__":
    sys.exit(main())
