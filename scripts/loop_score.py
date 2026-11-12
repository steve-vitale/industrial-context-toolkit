"""Score the control loops and signal relations in the bundle import_drawing_set.py writes (round 6, increment 3).

Product-path rule (docs/GOAL_ROUND6.md): every number is read from the plant_model.json `control_loops` block that the
drawing-set intake wrote. The bundles are built exactly as scripts/flow_direction_score.py builds them (its helpers
are reused: the same manifests, the same recorded readings, the key's symbols with the code tracer); this script only
reads them back and compares.

Key: data/te_control_loops.json, the 19 loops the Tennessee Eastman closed-loop code runs (11 that move a valve, 8
cascades that move an inner controller's setpoint; C22 is defined but never called and is left out). Matched on
printed tags (spaces and hyphens ignored). Development sets only:
  te-a      revision A (data/te_pid/rev-a): the recorded te-clean-trace runs r1-r5 (claude, codex) and the key's
            symbols with the code tracer. Revision A draws no controllers and no signal lines, so nothing can be
            confirmed there: it checks that nothing is asserted without a drawn line.
  te-d      revision D (data/te_pid, current): the key's symbols with the code tracer (no model has read revision D).
  open100   OPEN100 sheets 0-5 (three recorded readings): no loop key; counts only (these sheets draw no controllers).
  pahala    Pahala P-401 and P-501 (--pahala-manifest, as flow_direction_score.py): no loop key; counts only.

Scores per run, each beside the same deliberately wrong controls:
  controller    key loops whose controller heads a confirmed loop (recall); confirmed loops whose controller is in
                the key (precision)
  sensor        (controller, measurement) pairs of confirmed loops against the key's
  final element `controls` relations (controller -> valve) against the key's 11 valve loops
  cascade       `sets_point_of` relations (outer -> inner) against the key's 8 cascades
  loop          a key loop is recovered when a confirmed loop has its controller, its measurement and its output
                (the valve, or the inner controller); reported as valve loops x/11 and cascades y/8
  signal lines  (revision D, diagnostic) signal_to pairs against the key's drawn signal_edges by tag, cross-sheet
                flags followed
Controls: perfect (the key itself), empty (no loops), shuffled roles (the same traced lines, ISA roles permuted among
the instruments with a fixed seed), tag-only (every controller's tag group asserted as a loop, no line read: the
evidence-free rule this increment refuses).

TE sheets are drawn by this repository from its own model with clean, consistent tags, so every TE score is an upper
bound for clean drawings, and the tag-only control is strong there for the same reason.

    python scripts/loop_score.py --out out/round6/loops_dev
    python scripts/loop_score.py --sets te-d --out <scratch>/te-d

No model calls, no network. Needs OpenCV and NumPy, and git history for revision A's drawer.
"""
import argparse
import json
import random
import statistics
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import flow_direction_score as fds  # noqa: E402
import loop_assembly as la  # noqa: E402

KEY = ROOT / "data" / "te_control_loops.json"
SETS = ("te-a", "te-d", "open100", "pahala")
SHUFFLE_SEED = 0


def key_loops(path=KEY):
    """[{id, controller, measurement, output, kind}] for the loops the TE code runs, tags compacted."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"id": lp["id"], "controller": la.compact(lp["controller_tag"]),
             "measurement": la.compact(lp["measurement"]["tag"]), "output": la.compact(lp["output"]["tag"]),
             "kind": "valve" if lp["output"]["kind"] == "final_element" else "cascade"}
            for lp in doc["loops"] if lp.get("runs") and lp.get("controller_tag")]


def asserted(model, block=None):
    """What a control_loops block asserts, by compacted tag: confirmed loops, their measurement pairs, controls and
    sets_point_of relations."""
    cl = block if block is not None else (model.get("control_loops") or {})
    tag = {k: la.compact(v["tag"]) for k, v in la.candidates(model).items()}
    loops = [lp for lp in cl.get("loops", []) if lp["status"] == "confirmed"]
    return {"controllers": {tag[lp["controller"]] for lp in loops},
            "sensor": {(tag[lp["controller"]], tag[m["id"]]) for lp in loops for m in lp["measurements"]},
            "final": {(tag[r["from"]], tag[r["to"]]) for r in cl.get("relations", []) if r["type"] == "controls"},
            "cascade": {(tag[r["from"]], tag[r["to"]]) for r in cl.get("relations", []) if r["type"] == "sets_point_of"},
            "loops": [{"controller": tag[lp["controller"]], "measurements": {tag[m["id"]] for m in lp["measurements"]},
                       "outputs": {tag[x["id"]] for x in lp["final_elements"] + lp["sets_point_of"]}} for lp in loops]}


def prf(pred, truth):
    tp = len(pred & truth)
    return {"tp": tp, "asserted": len(pred), "key": len(truth),
            "precision": round(tp / len(pred), 3) if pred else None,
            "recall": round(tp / len(truth), 3) if truth else None}


def score(a, key):
    truth = {"controllers": {k["controller"] for k in key},
             "sensor": {(k["controller"], k["measurement"]) for k in key},
             "final": {(k["controller"], k["output"]) for k in key if k["kind"] == "valve"},
             "cascade": {(k["controller"], k["output"]) for k in key if k["kind"] == "cascade"}}
    out = {name: prf(a[name], truth[name]) for name in truth}
    found = [k for k in key if any(lp["controller"] == k["controller"] and k["measurement"] in lp["measurements"]
                                   and k["output"] in lp["outputs"] for lp in a["loops"])]
    exact = sum(any(lp["controller"] == k["controller"] and k["measurement"] in lp["measurements"]
                    and k["output"] in lp["outputs"] for k in key) for lp in a["loops"])
    out["loops"] = {"valve_loops": f"{sum(k['kind'] == 'valve' for k in found)}/{sum(k['kind'] == 'valve' for k in key)}",
                    "cascades": f"{sum(k['kind'] == 'cascade' for k in found)}/{sum(k['kind'] == 'cascade' for k in key)}",
                    "recall": round(len(found) / len(key), 3), "asserted": len(a["loops"]),
                    "precision": round(exact / len(a["loops"]), 3) if a["loops"] else None,
                    "missed": sorted(k["id"] for k in key if k not in found)}
    return out


# ---------------------------------------------------------------- the deliberately wrong controls

def perfect(key):
    return {"controllers": {k["controller"] for k in key}, "sensor": {(k["controller"], k["measurement"]) for k in key},
            "final": {(k["controller"], k["output"]) for k in key if k["kind"] == "valve"},
            "cascade": {(k["controller"], k["output"]) for k in key if k["kind"] == "cascade"},
            "loops": [{"controller": k["controller"], "measurements": {k["measurement"]}, "outputs": {k["output"]}}
                      for k in key]}


def empty():
    return {"controllers": set(), "sensor": set(), "final": set(), "cascade": set(), "loops": []}


def shuffled_roles(model):
    """The bundle's own traced signal lines, re-assembled with the ISA roles permuted among the instruments."""
    cand = la.candidates(model)
    ids = sorted(cand)
    roles = [cand[k]["role"] for k in ids]
    random.Random(SHUFFLE_SEED).shuffle(roles)
    block = la.assemble(model, (model.get("control_loops") or {}).get("signal_lines", []), roles=dict(zip(ids, roles)))
    return asserted(model, block)


def tag_only(model):
    """Every controller's tag group asserted as a loop: its same-identity measurements and final elements, no line."""
    cand = la.candidates(model)
    groups = defaultdict(list)
    for k, c in cand.items():
        groups[(c["area"], c["number"])].append(c)
    a = empty()
    for c in cand.values():
        if c["role"] != "controller":
            continue
        g = groups[(c["area"], c["number"])]
        ms = {la.compact(x["tag"]) for x in g if x["role"] in la.MEASUREMENTS}
        fs = {la.compact(x["tag"]) for x in g if x["role"] == "final_element"}
        t = la.compact(c["tag"])
        a["controllers"].add(t)
        a["sensor"] |= {(t, m) for m in ms}
        a["final"] |= {(t, f) for f in fs}
        a["loops"].append({"controller": t, "measurements": ms, "outputs": fs})
    return a


def signal_diagnostic(model, key_doc, sheets):
    """signal_to pairs (by tag, unordered) against the key's drawn signal_edges, flags followed across sheets."""
    truth = set()
    flags = {}
    for s in sheets:
        sy = key_doc["sheets"][s]["symbols"]
        for a, b in key_doc["sheets"][s].get("signal_edges", []):
            ta, tb = sy[a], sy[b]
            if ta.get("model_kind") == "signal_flag" or tb.get("model_kind") == "signal_flag":
                f, o = (ta, tb) if ta.get("model_kind") == "signal_flag" else (tb, ta)
                far = la.compact(f.get("signal_to") or f.get("signal_from"))
                flags.setdefault(frozenset((far, la.compact(o.get("text")))), True)
                continue
            truth.add(frozenset((la.compact(ta.get("text")), la.compact(tb.get("text")))))
    truth |= set(flags)
    tag = {k: la.compact(v["tag"]) for k, v in la.candidates(model).items()}
    pred = {frozenset((tag[r["from"]], tag[r["to"]])) for r in (model.get("control_loops") or {}).get("relations", [])
            if r["type"] == "signal_to"}
    return prf(pred, truth)


# ---------------------------------------------------------------- runs

def without_loops(model):
    m = json.loads(json.dumps(model))
    m.pop("control_loops", None)
    m["meta"].pop("loops_status", None)
    return m


def record(result, model, key, key_doc=None, sheets=None, no_loops_model=None):
    rec = {"loops_status": result.get("loops"), "counts": (model.get("control_loops") or {}).get("counts")}
    if no_loops_model is not None:
        rec["bundle_identical_without_loops"] = without_loops(model) == no_loops_model
    if key is not None:
        rec["score"] = score(asserted(model), key)
        rec["controls"] = {"perfect": score(perfect(key), key), "empty": score(empty(), key),
                           "shuffled_roles": score(shuffled_roles(model), key) if model.get("control_loops") else
                           score(empty(), key),
                           "tag_only": score(tag_only(model), key)}
        if key_doc is not None:
            rec["signal_lines_vs_drawn"] = signal_diagnostic(model, key_doc, sheets)
    return rec


def _bundle_pair(manifest, folder):
    """The bundle with loops, and the same inputs through --no-loops (to show nothing else moved)."""
    import import_drawing_set as dset
    result = dset.import_set(manifest, folder / "bundle")
    model = json.loads((folder / "bundle" / "plant_model.json").read_text(encoding="utf-8"))
    dset.import_set(manifest, folder / "bundle-no-loops", loops=False)
    plain = json.loads((folder / "bundle-no-loops" / "plant_model.json").read_text(encoding="utf-8"))
    return result, model, plain


def run_te(rev, tmp, key):
    _, model_path, layout_path, folder = fds.revision_inputs(rev, tmp)
    key_doc = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    readers = {"key symbols + tracer": None}
    if rev == "a":
        for r in range(1, 6):
            for tool in ("claude", "codex"):
                readers[f"te-clean-trace-r{r}/{tool}"] = (f"te-clean-trace-r{r}", tool)
    runs = {}
    for name, src in readers.items():
        sub = tmp / f"loops-te-{rev}-{name.replace('/', '-').replace(' ', '_').replace('+', '')}"
        sub.mkdir()
        rows = []
        for page, s in enumerate(fds.TE_SHEETS, 1):
            png = folder / f"{s}.png"
            if src is None:
                text = {k: v.get("text") for k, v in key_doc["sheets"][s]["symbols"].items()}
                ext = fds.key_reader(png, folder / f"{s}.graphml", text, sub, s)
            else:
                ext = ROOT / "predictions" / src[0] / src[1] / f"{s}.json"
            rows.append({"drawing_id": f"TE-{s}", "revision": rev.upper(), "page": page, "image": str(png),
                         "extraction": str(ext), "drawing_number": key_doc["sheets"][s]["drawing"],
                         "title": key_doc["sheets"][s]["title"]})
        producer = {"method": name, "tool": "key" if src is None else src[1], "model": None}
        manifest = fds.write_manifest(sub, f"TE revision {rev.upper()}", producer, rows,
                                      "prediction" if src is None else "run-record")
        try:
            result, model, plain = _bundle_pair(manifest, sub)
        except ValueError as error:
            runs[name] = {"refused_by_intake": str(error)}
            continue
        runs[name] = record(result, model, key, key_doc, fds.TE_SHEETS, plain)
        if rev == "d":
            runs[name]["per_sheet"] = per_sheet(model, key, key_doc)
    return {"key": "data/te_control_loops.json (19 running loops: 11 valve, 8 cascade)",
            "drawn": "no controllers or signal lines" if rev == "a" else "controllers, dashed signal lines, flags",
            "runs": runs}


def per_sheet(model, key, key_doc):
    """Loop recall by the sheet the key's controller is drawn on (the sheet spread)."""
    where = {}
    for n, s in enumerate(fds.TE_SHEETS):
        for v in key_doc["sheets"][s]["symbols"].values():
            if v.get("model_kind") == "controller":
                where[la.compact(v.get("text"))] = s
    out = {}
    a = asserted(model)
    for s in fds.TE_SHEETS:
        ks = [k for k in key if where.get(k["controller"]) == s]
        sub = score({**a, "loops": [lp for lp in a["loops"] if where.get(lp["controller"]) == s]}, ks)["loops"]
        out[s] = {"key_loops": len(ks), "recall": sub["recall"], "precision": sub["precision"]}
    return out


def run_open100(tmp):
    base = json.loads((ROOT / "examples/own-drawing/set-manifest.json").read_text(encoding="utf-8"))
    sheets = list(base["sheets"])
    if [s["drawing_id"] for s in sheets] != [f"OPEN100-{i}" for i in fds.DEV_OPEN100]:
        raise SystemExit("examples/own-drawing/set-manifest.json is no longer OPEN100 sheets 0-5")
    runs = {}
    for tool in ("claude", "codex", "gemini"):
        rows = [{**s, "image": str(fds.OPEN100 / f"{i}.png"),
                 "extraction": str(ROOT / "predictions/r2-tiles-trace" / tool / f"{i}.json")}
                for i, s in zip(fds.DEV_OPEN100, sheets)]
        folder = tmp / f"loops-open100-{tool}"
        manifest = fds.write_manifest(folder, base["set_id"], {**base["producer"], "tool": tool, "model": None}, rows)
        try:
            result, model, plain = _bundle_pair(manifest, folder)
        except ValueError as error:
            runs[f"r2-tiles-trace/{tool}"] = {"refused_by_intake": str(error)}
            continue
        runs[f"r2-tiles-trace/{tool}"] = record(result, model, None, no_loops_model=plain)
    return {"key": None, "note": "no loop key; these sheets draw no controllers: counts only", "runs": runs}


def run_pahala(manifest_path, tmp):
    man_path = Path(manifest_path).resolve()
    man = json.loads(man_path.read_text(encoding="utf-8"))
    rows = [{**s, "image": str((man_path.parent / s["image"]).resolve()),
             "extraction": str((man_path.parent / s["extraction"]).resolve())}
            for s in man["sheets"] if s["drawing_id"] in fds.DEV_PAHALA]
    if [r["drawing_id"] for r in rows] != list(fds.DEV_PAHALA):
        raise SystemExit(f"--pahala-manifest must hold {', '.join(fds.DEV_PAHALA)}")
    folder = tmp / "loops-pahala"
    manifest = fds.write_manifest(folder, man["set_id"] + " (development sheets P-401, P-501)", man["producer"], rows,
                                  man["extraction_format"])
    name = f"{man['producer'].get('tool')} reading"
    try:
        result, model, plain = _bundle_pair(manifest, folder)
    except ValueError as error:
        return {"key": None, "runs": {name: {"refused_by_intake": str(error)}}}
    return {"key": None, "note": "no loop key: counts only", "runs": {name: record(result, model, None, no_loops_model=plain)}}


def spread(values):
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"n": len(v), "mean": round(statistics.mean(v), 3), "min": min(v), "max": max(v),
            "sd": round(statistics.stdev(v), 3) if len(v) > 1 else 0.0}


def summarize(results):
    out = {}
    for name, r in results.items():
        runs = [x for x in r["runs"].values() if "refused_by_intake" not in x]
        s = {"runs_attempted": len(r["runs"]), "runs_scored": len(runs),
             "bundle_identical_without_loops": all(x.get("bundle_identical_without_loops") for x in runs)}
        scored = [x for x in runs if "score" in x]
        if scored:
            for m in ("controller", "sensor", "final", "cascade"):
                key = "controllers" if m == "controller" else m
                s[f"{m}_recall"] = spread([x["score"][key]["recall"] for x in scored])
                s[f"{m}_precision"] = spread([x["score"][key]["precision"] for x in scored])
            s["loop_recall"] = spread([x["score"]["loops"]["recall"] for x in scored])
            s["loop_precision"] = spread([x["score"]["loops"]["precision"] for x in scored])
            s["loop_recall_by_sheet"] = spread([v["recall"] for x in scored for v in x.get("per_sheet", {}).values()])
            s["controls_loop_recall"] = {c: spread([x["controls"][c]["loops"]["recall"] for x in scored])
                                         for c in ("perfect", "empty", "shuffled_roles", "tag_only")}
            s["controls_loop_precision"] = {c: spread([x["controls"][c]["loops"]["precision"] for x in scored])
                                            for c in ("perfect", "empty", "shuffled_roles", "tag_only")}
        else:
            s["confirmed_loops"] = spread([(x.get("counts") or {}).get("confirmed", 0) for x in runs])
            s["signal_to"] = spread([(x.get("counts") or {}).get("signal_to", 0) for x in runs])
        out[name] = s
    return out


def markdown(doc):
    lines = ["# Control loops and signals, read from the drawing-set bundle (round 6, increment 3)", "",
             "Development sets only. Every number is read from the `control_loops` block of the `plant_model.json` that "
             "`scripts/import_drawing_set.py` wrote (`scripts/loop_score.py`), against `data/te_control_loops.json` "
             "(19 running loops: 11 valve loops, 8 cascades). A loop counts when a confirmed loop has the key's "
             "controller, measurement and output; P = share of confirmed loops that are a key loop. TE sheets are drawn "
             "by this repository from its own model, so TE scores are upper bounds for clean drawings.", "",
             "| Set | Run | Confirmed / loops | Valve loops | Cascades | Loop P | Sensor P / R | Final element P / R | "
             "Cascade P / R | Shuffled roles (loop R / P) | Tag-only (loop R / P) | Empty | Rest of bundle unchanged |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def pr(x):
        return f"{x['precision'] if x['precision'] is not None else '-'} / {x['recall']}"
    for name, r in doc["sets"].items():
        for run, x in r["runs"].items():
            if "refused_by_intake" in x:
                why = " ".join(str(x["refused_by_intake"]).split()).replace("|", "/")
                lines.append(f"| {name} | {run} | refused by the intake: {why} |" + " - |" * 11)
                continue
            c = x.get("counts") or {}
            conf = f"{c.get('confirmed', 0)} / {c.get('loops', 0)}" if c else "0 / 0 (nothing to assemble)"
            same = x.get("bundle_identical_without_loops")
            if "score" not in x:
                lines.append(f"| {name} | {run} | {conf} | no key | no key | - | - | - | - | - | - | - | {same} |")
                continue
            s, k = x["score"], x["controls"]
            lines.append(f"| {name} | {run} | {conf} | {s['loops']['valve_loops']} | {s['loops']['cascades']} | "
                         f"{s['loops']['precision'] if s['loops']['precision'] is not None else '-'} | {pr(s['sensor'])} | "
                         f"{pr(s['final'])} | {pr(s['cascade'])} | "
                         f"{k['shuffled_roles']['loops']['recall']} / {k['shuffled_roles']['loops']['precision'] or '-'} | "
                         f"{k['tag_only']['loops']['recall']} / {k['tag_only']['loops']['precision'] or '-'} | "
                         f"{k['empty']['loops']['recall']} | {same} |")
    lines += ["", "Diagnostic, TE revision D: `signal_to` pairs against the drawn signal lines of the key (`signal_edges`, "
              "cross-sheet flags followed), unordered, by tag.", "", "| Run | Asserted | Correct | Drawn | P | R |",
              "|---|---|---|---|---|---|"]
    for run, x in (doc["sets"].get("te-d") or {}).get("runs", {}).items():
        d = x.get("signal_lines_vs_drawn")
        if d:
            lines.append(f"| {run} | {d['asserted']} | {d['tp']} | {d['key']} | {d['precision']} | {d['recall']} |")
    lines += ["", "## Spread (runs, then sheets)", "", "```", json.dumps(doc["summary"], indent=1), "```", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sets", default="te-a,te-d,open100,pahala")
    ap.add_argument("--pahala-manifest", help="site-drawing-set-1 manifest holding Pahala P-401 and P-501")
    ap.add_argument("--out", required=True, help="output prefix: writes <prefix>.json and <prefix>.md")
    a = ap.parse_args(argv)
    chosen = [s for s in a.sets.split(",") if s]
    bad = [s for s in chosen if s not in SETS]
    if bad:
        ap.error(f"unknown or held-out set(s) {bad}; development sets: {', '.join(SETS)}")
    key = key_loops()
    results = {}
    with tempfile.TemporaryDirectory(prefix="loop-score-") as t:
        tmp = Path(t)
        for name in chosen:
            if name in ("te-a", "te-d"):
                results[name] = run_te(name[-1], tmp, key)
            elif name == "open100":
                results[name] = run_open100(tmp)
            elif a.pahala_manifest:
                results[name] = run_pahala(a.pahala_manifest, tmp)
            else:
                results[name] = {"key": None, "runs": {}, "note": "not run: give --pahala-manifest"}
    doc = {"script": "scripts/loop_score.py", "goal": "docs/GOAL_ROUND6.md increment 3",
           "held_out_not_read": "OPEN100 sheets 6-11, the DEXPI held-out renders, Pahala sheets other than P-401/P-501",
           "key_loops": len(key), "shuffle_seed": SHUFFLE_SEED, "sets": results, "summary": summarize(results)}
    page = markdown(doc)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{out}.json").write_text(json.dumps(doc, indent=1, default=sorted) + "\n", encoding="utf-8")
    Path(f"{out}.md").write_text(page, encoding="utf-8")
    print(json.dumps(doc["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
