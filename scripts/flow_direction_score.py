"""Score the flow direction on piped_to in the bundle import_drawing_set.py writes, on the round-6 development sets.

Round 6's product-path rule (docs/GOAL_ROUND6.md): a score counts only when it is computed from the bundle the
drawing-set intake writes. This script builds that bundle for each development input with
scripts/import_drawing_set.py (in a temporary folder) and reads plant_model.json back. It never computes a direction
itself: the directions are the bundle's.

Development inputs only (the held-out sets stay sealed; asking for one is refused):
  open100   OPEN100 sheets 0-5, as the recorded r2-tiles-trace readers left them (claude, codex, gemini). No
            direction truth: the PID2Graph keys are undirected. Scored: share of pipe segments directed, and arrowhead
            DETECTION against the keys' arrow nodes (position only, sheets 0-5).
  te-a      generated Tennessee Eastman sheets 101-103, revision A (data/te_pid/rev-a): the recorded te-clean-trace
            runs r1-r5 (claude, codex) and the key's symbols with the code tracer.
  te-d      revision D (data/te_pid, current): the key's symbols with the code tracer (no model has read revision D).
  pahala    Pahala WWTP P-401 and P-501 (public EPA docket; not in this repository: --pahala-manifest names a
            site-drawing-set-1 manifest holding them; any other sheet in it is excluded and never read). No direction truth.

Direction truth (TE only): the model's streams (data/te_process_model.json, every one "forward") as the drawer laid
them out: each stream route runs from the stream's source to its destination, so consecutive items on it are ordered
the way the stream flows. Derived from the same drawer run as line_layers.drawn_truth (its anchors, kept in route
order); revision A is re-derived with the drawer, model and layout it was drawn with (git commit REV_A_COMMIT, checked
against data/te_pid/rev-a/manifest.json). Routes that carry no model stream (the reactor header, cooling water,
steam, the compressor spill-back) have no truth here; a diagnostic scores every drawn route in the drawer's own
order as well (self-generated, so not a model truth). A bundle segment is scored when its two ends, matched to the key
(symbols by box, rough IoU; junctions by position, as line_layers.score_pipe), form a truth segment with a direction.

Controls beside every scored run: perfect (the truth's own direction on each scorable segment), reversed (every
bundle direction turned round), layout (N012's rejected rule: every segment pointed left to right, or top to bottom
when it runs vertically) and empty (no direction).

    python scripts/flow_direction_score.py --out out/round6/flow_direction_dev
    python scripts/flow_direction_score.py --sets te-d --out <scratch>/te-d   # one set

No model calls, no network. Needs OpenCV and NumPy, and git history for revision A's drawer.
"""
import argparse
import importlib.util
import json
import os
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import import_drawing_set as dset  # noqa: E402
import line_layers as ll  # noqa: E402
import score_pid2graph as sc  # noqa: E402

OPEN100 = ROOT / "data" / "external" / "pid2graph" / "PID2Graph" / "Complete" / "PID2Graph OPEN100"
DEV_OPEN100 = ["0", "1", "2", "3", "4", "5"]
DEV_PAHALA = ("P-401", "P-501")
TE_SHEETS = ["101", "102", "103"]
REV_A_COMMIT = "3c0101d"  # the drawer, model and layout of data/te_pid/rev-a/manifest.json
SETS = ("open100", "te-a", "te-d", "pahala")


# ---------------------------------------------------------------- bundles through the product path

def write_manifest(folder, set_id, producer, sheets, fmt="run-record"):
    folder.mkdir(parents=True, exist_ok=True)
    rows = [{**s, "image": os.path.relpath(s["image"], folder), "extraction": os.path.relpath(s["extraction"], folder)}
            for s in sheets]
    path = folder / "set.json"
    path.write_text(json.dumps({"schema_version": dset.SCHEMA, "set_id": set_id, "extraction_format": fmt,
                                "producer": producer, "sheets": rows}, indent=1), encoding="utf-8")
    return path


def bundle(manifest, out):
    result = dset.import_set(manifest, out)
    model = json.loads((out / "plant_model.json").read_text(encoding="utf-8"))
    return result, model


def key_reader(png, graphml, key_symbols_text, folder, name):
    """The key's symbols (boxes rounded as the intake rounds them) with the code tracer's links: a perfect symbol
    reader, so the direction is read by code alone."""
    import trace_connections as tc
    syms = []
    for s in ll.key_symbols(graphml, png):
        b = [round(v, 1) for v in s["box"]]
        syms.append({"id": s["id"], "class": s["class"], "box": b, "tag": key_symbols_text.get(s["id"]),
                     "confidence": 1.0})
    links = tc.trace(png, [{"id": s["id"], "class": s["class"], "box": s["box"]} for s in syms])
    path = folder / f"{name}.json"
    path.write_text(json.dumps({"symbols": syms, "connections": [{"from": l["from"], "to": l["to"]} for l in links]}),
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------- TE direction truth

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def revision_inputs(rev, tmp):
    """(drawer module, model path, layout path, sheet folder) for revision A or D."""
    if rev == "d":
        import draw_pid_from_model as dp
        return dp, ROOT / "data" / "te_process_model.json", ROOT / "data" / "te_pid_layout.json", ROOT / "data" / "te_pid"
    folder = tmp / "rev-a-drawer"
    folder.mkdir()
    for f in ("scripts/draw_pid_from_model.py", "data/te_process_model.json", "data/te_pid_layout.json"):
        data = subprocess.run(["git", "show", f"{REV_A_COMMIT}:{f}"], cwd=ROOT, capture_output=True, check=True).stdout
        (folder / Path(f).name).write_bytes(data)
    dp = load_module(folder / "draw_pid_from_model.py", "draw_pid_rev_a")
    man = json.loads((ROOT / "data/te_pid/rev-a/manifest.json").read_text(encoding="utf-8"))
    for f, k in (("draw_pid_from_model.py", "generator_sha256"), ("te_process_model.json", "model_sha256"),
                 ("te_pid_layout.json", "layout_sha256")):
        if dp.sha_file(folder / f) != man[k]:
            raise SystemExit(f"revision A: {f} at {REV_A_COMMIT} is not the version that drew data/te_pid/rev-a")
    return dp, folder / "te_process_model.json", folder / "te_pid_layout.json", ROOT / "data" / "te_pid" / "rev-a"


def te_truth(dp, model_path, layout_path, key_path, every_route=False):
    """{sheet: truth} as line_layers.drawn_truth builds it (the same anchors, contract() and junction names), plus
    "flow": {sorted segment: (upstream, downstream)} for segments on routes that carry a model stream, ordered by the
    route (the drawer lays each stream route out from its source to its destination). Checks that the line networks
    are exactly the key's, as drawn_truth does. every_route: every drawn route counts, in the drawer's own order (a
    diagnostic: routes that carry no model stream have no truth from the model)."""
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))
    forward = {s["id"] for s in model["streams"] if s.get("direction") == "forward"}
    seen, mounts = {}, defaultdict(list)
    orig_connect, orig_group = dp.Sheet.connect, dp.Sheet.link_group

    def spy_connect(self, routes, unit_nodes, flag_nodes):
        seen[self.spec["id"]] = (self, routes, unit_nodes, flag_nodes)
        self._in_connect = True
        return orig_connect(self, routes, unit_nodes, flag_nodes)

    def spy_group(self, members, at):
        if not getattr(self, "_in_connect", False):
            mounts[self.spec["id"]].append([m for m in members if m])
        return orig_group(self, members, at)
    dp.Sheet.connect, dp.Sheet.link_group = spy_connect, spy_group
    try:
        dp.generate(model_path, layout_path, None, write=False)
    finally:
        dp.Sheet.connect, dp.Sheet.link_group = orig_connect, orig_group
    out = {}
    for sid, (sh, routes, unit_nodes, flag_nodes) in seen.items():
        all_routes = sh.spec["routes"] + getattr(sh, "extra_routes", [])
        stream_route = ({r["id"] for r in all_routes} if every_route else
                        {r["id"] for r in sh.spec["routes"] if r.get("stream") in forward})
        anchors, adj, items, pos, along = defaultdict(list), defaultdict(dict), set(), {}, {}

        def joint(p):
            k = ("pt", round(p[0]), round(p[1]))
            pos[k] = (p[0], p[1])
            return k

        def end_node(end, p):
            if "unit" in end:
                items.add(unit_nodes[end["unit"]])
                return unit_nodes[end["unit"]]
            if "flag" in end:
                items.add(flag_nodes[end["flag"]])
                return flag_nodes[end["flag"]]
            return joint(p)
        net_routes = defaultdict(list)
        for r in all_routes:
            for key in ("from", "to"):
                if "net" in r[key]:
                    net_routes[r[key]["net"]].append(r["id"])
        for r in all_routes:
            rid, rr = r["id"], routes[r["id"]]
            pts, L = rr["pts"], dp.length(rr["pts"])
            anchors[rid].append((0.0, end_node(r["from"], pts[0])))
            anchors[rid].append((L, end_node(r["to"], pts[-1])))
            for t, nid in rr["valves"]:
                anchors[rid].append((t, nid))
                items.add(nid)
            for t, bid in rr["taps"]:
                j = joint(dp.point_at(pts, t)[0])
                anchors[rid].append((t, j))
                adj[j][bid] = adj[bid][j] = rid
                items.add(bid)
            for key, p in (("from", pts[0]), ("to", pts[-1])):
                end = r[key]
                targets = [end["tee"]] if "tee" in end else net_routes.get(end.get("net"), []) if "net" in end else []
                for tid in targets:
                    if tid == rid:
                        continue
                    loc = dp.locate(routes[tid]["pts"], tuple(end["at"]) if "at" in end else tuple(p))
                    if loc is not None:
                        anchors[tid].append((loc[0], joint(end["at"] if "at" in end else p)))
        for rid, an in anchors.items():
            an.sort(key=lambda x: x[0])
            for (_, a), (_, b) in zip(an, an[1:]):
                if a != b:
                    adj[a][b] = adj[b][a] = rid
                    if rid in stream_route:
                        along[(a, b)] = rid
        for ms in mounts[sid]:
            for a in ms[1:]:
                adj[ms[0]][a] = adj[a][ms[0]] = "mount"
                items.update((ms[0], a))
        segs, arms = ll.contract(adj, items)
        names = {j: f"T{n + 1:03d}" for n, j in enumerate(sorted(arms, key=lambda k: (pos[k][1], pos[k][0])))}
        out[sid] = {"items": items, "junctions": {names[j]: pos[j] for j in arms},
                    "arms": {names[j]: n for j, n in arms.items()},
                    "segments": {tuple(sorted((names.get(a, a), names.get(b, b)))) for a, b in segs},
                    "networks": ll.pipe_networks([tuple(s) for s in segs], set(arms)),
                    "_adj": adj, "_along": along, "_names": names}
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    for sid, t in out.items():
        groups = defaultdict(set)
        for a, b in key["sheets"][sid]["edges"]:
            c, m = (a, b) if a.startswith("connector") else (b, a)
            groups[c].add(m)
        if {frozenset(v) for v in groups.values()} != {frozenset(n["members"]) for n in t["networks"]}:
            raise SystemExit(f"sheet {sid}: the pipe truth's line networks are not the key's")
    return out


def flow_of(truth, a, b, ends):
    """(a, b) or (b, a) when the drawn line from a to b (passing only points that end no pipe segment) runs along
    one stream route's order the whole way; None otherwise."""
    back = {v: k for k, v in truth["_names"].items()}
    ra, rb = back.get(a, a), back.get(b, b)
    adj, along = truth["_adj"], truth["_along"]
    prev, todo = {ra: None}, [ra]
    while todo:
        u = todo.pop(0)
        if u == rb:
            break
        for v in adj.get(u, {}):
            if v in prev:
                continue
            if v != rb and (v in truth["items"] or v in ends):
                continue
            prev[v] = u
            todo.append(v)
    if rb not in prev:
        return None
    path, n = [], rb
    while n is not None:
        path.append(n)
        n = prev[n]
    path.reverse()
    steps = list(zip(path, path[1:]))
    if steps and all(s in along for s in steps):
        return (a, b)
    if steps and all((y, x) in along for x, y in steps):
        return (b, a)
    return None


def classified_truth(truth, png, graphml):
    """Split the truth into pipe and instrument lines by the key symbols' roles (line_layers.classify_truth), then
    direct every pipe segment that runs along one stream route."""
    pred = ll.traced_layers(png, ll.key_symbols(graphml, png))
    c = ll.classify_truth(truth, pred["roles"])
    back = {v: k for k, v in truth["_names"].items()}
    ends = {back.get(x, x) for s in c["segments"] for x in s}
    c["flow"] = {}
    for a, b in c["segments"]:
        f = flow_of(truth, a, b, ends)
        if f:
            c["flow"][tuple(sorted((a, b)))] = f
    c["segment_keys"] = {tuple(sorted(s)) for s in c["segments"]}
    return c


# ---------------------------------------------------------------- reading the bundle back

def segment_ends(model):
    """{sheet: {node: (x, y) on the 0-1000 scale}} for items (box centre) and junctions."""
    out = defaultdict(dict)
    for key in ("units", "instruments", "line_items", "offpage_connectors"):
        for it in model[key]:
            for p in it["provenance"]:
                b = p["box_0_1000"]
                out[str(p["sheet"])].setdefault(it["id"], ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    for j in model["line_layers"]["junctions"]:
        out[j["sheet"]][j["id"]] = tuple(j["at_0_1000"])
    return out


def share(model, sheets=None):
    segs = [s for s in model["line_layers"]["segments"] if sheets is None or s["sheet"] in sheets]
    d = sum(s.get("direction") == "forward" for s in segs)
    return {"pipe_segments": len(segs), "directed": d, "share": round(d / len(segs), 3) if segs else None}


def per_sheet_share(model):
    return {s: share(model, {s}) for s in sorted({x["sheet"] for x in model["line_layers"]["segments"]}, key=int)}


def map_to_truth(model, sheet, truth, png, graphml):
    """{bundle node: truth node} on one sheet: items by box (score_pid2graph.match, rough IoU, class-free), junctions
    by position (line_layers.match_junctions)."""
    w, h = sc.png_size(png)
    nodes, _ = sc.load_key(graphml, w, h)
    keys = {k: v for k, v in nodes.items() if v["class"] in sc.SCORED}
    preds = []
    for key in ("units", "instruments", "line_items", "offpage_connectors"):
        for it in model[key]:
            for p in it["provenance"]:
                if str(p["sheet"]) == sheet:
                    preds.append({"id": it["id"], "class": p.get("class"), "box": p["box_0_1000"]})
    items = sc.match(preds, keys, False, sc.THRESHOLDS["rough"])
    side = model["line_layers"]["sheets"][sheet]["side_px"]
    pj = {j["id"]: {"x": j["at_0_1000"][0] * w / 1000, "y": j["at_0_1000"][1] * h / 1000}
          for j in model["line_layers"]["junctions"] if j["sheet"] == sheet}
    m = lambda x: items.get(x, x if x in pj else "pred:" + x)  # noqa: E731
    segs = [(m(s["from"]), m(s["to"])) for s in model["line_layers"]["segments"] if s["sheet"] == sheet]
    jm = ll.match_junctions({"junctions": pj, "segments": segs}, truth, side)
    return {**items, **jm}


def score_directions(model, truths, sheet_of, controls=True):
    """Direction precision on the scorable segments, per sheet and in total, with the controls."""
    ends = segment_ends(model)
    rows = {}
    for sheet, (truth, png, gml) in truths.items():
        b = sheet_of[sheet]
        mp = map_to_truth(model, b, truth, png, gml)
        res = defaultdict(int)
        for s in (x for x in model["line_layers"]["segments"] if x["sheet"] == b):
            a, z = mp.get(s["from"]), mp.get(s["to"])
            key = tuple(sorted((a, z))) if a and z else None
            flow = truth["flow"].get(key) if key else None
            res["segments"] += 1
            res["on_a_truth_segment"] += key in truth["segment_keys"] if key else 0
            if flow is None:
                res["directed_not_scorable"] += s.get("direction") == "forward"
                continue
            res["truth_directed"] += 1
            if s.get("direction") == "forward":
                res["directed"] += 1
                res["correct"] += (a, z) == flow
            # layout control: left to right, or top to bottom when the segment runs vertically
            pa, pz = ends[b].get(s["from"]), ends[b].get(s["to"])
            if pa and pz:
                dx, dy = pz[0] - pa[0], pz[1] - pa[1]
                forward = dx > 0 if abs(dx) >= abs(dy) else dy > 0
                res["layout_correct"] += forward == ((a, z) == flow)
        rows[sheet] = dict(res)
    tot = defaultdict(int)
    for r in rows.values():
        for k, v in r.items():
            tot[k] += v

    def summary(r):
        p = r.get("correct", 0) / r["directed"] if r.get("directed") else None
        out = {**r, "precision": round(p, 3) if p is not None else None,
               "recall_of_truth_directed": round(r.get("correct", 0) / r["truth_directed"], 3)
               if r.get("truth_directed") else None}
        if controls:
            out["controls"] = {
                "perfect": {"directed": r.get("truth_directed", 0), "precision": 1.0 if r.get("truth_directed") else None},
                "reversed": {"directed": r.get("directed", 0),
                             "precision": round(1 - p, 3) if p is not None else None},
                "layout": {"directed": r.get("truth_directed", 0),
                           "precision": round(r.get("layout_correct", 0) / r["truth_directed"], 3)
                           if r.get("truth_directed") else None},
                "empty": {"directed": 0, "precision": None}}
        return out
    return {"sheets": {k: summary(v) for k, v in rows.items()}, "total": summary(dict(tot))}


def arrow_detection(model, sheet_of):
    """Arrowheads the bundle found vs the OPEN100 key's arrow nodes (position only), development sheets only; the
    rule of flow_direction.score_arrows: a detection counts inside a key arrow box grown by 0.3 symbol sides."""
    st = model["meta"]["flow_direction_status"]["arrowheads_found"]
    tp = n_det = hit = n_key = 0
    per = {}
    for sheet, b in sheet_of.items():
        if sheet not in DEV_OPEN100:
            raise SystemExit(f"OPEN100 sheet {sheet} is held out")
        png = OPEN100 / f"{sheet}.png"
        w, h = sc.png_size(png)
        nodes, _ = sc.load_key(OPEN100 / f"{sheet}.graphml", w, h)
        keys = [v["box"] for v in nodes.values() if v["class"] == "arrow"]
        tol = 0.3 * model["line_layers"]["sheets"][b]["side_px"] * 1000 / w
        tol_y = 0.3 * model["line_layers"]["sheets"][b]["side_px"] * 1000 / h
        got, t = set(), 0
        for a in st[b]:
            x, y = (a["box_0_1000"][0] + a["box_0_1000"][2]) / 2, (a["box_0_1000"][1] + a["box_0_1000"][3]) / 2
            m = [k for k, kb in enumerate(keys) if kb[0] - tol <= x <= kb[2] + tol and kb[1] - tol_y <= y <= kb[3] + tol_y]
            t += bool(m)
            got |= set(m)
        per[sheet] = {"detections": len(st[b]), "on_a_key_arrow": t, "key_arrows": len(keys), "found": len(got)}
        tp, n_det, hit, n_key = tp + t, n_det + len(st[b]), hit + len(got), n_key + len(keys)
    return {"sheets": per, "precision": round(tp / n_det, 3) if n_det else None,
            "recall": round(hit / n_key, 3) if n_key else None, "detections": n_det, "key_arrows": n_key}


# ---------------------------------------------------------------- the sets

def run_open100(tmp):
    base = json.loads((ROOT / "examples/own-drawing/set-manifest.json").read_text(encoding="utf-8"))
    sheets = [s for s in base["sheets"]]
    if [s["drawing_id"] for s in sheets] != [f"OPEN100-{i}" for i in DEV_OPEN100]:
        raise SystemExit("examples/own-drawing/set-manifest.json is no longer OPEN100 sheets 0-5")
    runs = {}
    for tool in ("claude", "codex", "gemini"):
        rows = [{**s, "image": str(OPEN100 / f"{i}.png"),
                 "extraction": str(ROOT / "predictions/r2-tiles-trace" / tool / f"{i}.json")}
                for i, s in zip(DEV_OPEN100, sheets)]
        folder = tmp / f"open100-{tool}"
        manifest = write_manifest(folder, base["set_id"], {**base["producer"], "tool": tool, "model": None}, rows)
        try:
            result, model = bundle(manifest, folder / "bundle")
        except ValueError as error:  # e.g. a failed run record: the intake refuses it, so nothing is scored
            runs[f"r2-tiles-trace/{tool}"] = {"refused_by_intake": str(error)}
            continue
        sheet_of = {i: str(n) for n, i in enumerate(DEV_OPEN100)}
        runs[f"r2-tiles-trace/{tool}"] = {"line_layers": result["line_layers"]["status"],
                                          "flow_direction": result.get("flow_direction"), **share(model),
                                          "per_sheet": per_sheet_share(model),
                                          "arrow_detection": arrow_detection(model, sheet_of)}
    return {"truth": None, "note": "PID2Graph keys are undirected: share directed and arrowhead detection only",
            "runs": runs}


def run_te(rev, tmp):
    dp, model_path, layout_path, folder = revision_inputs(rev, tmp)
    key_doc = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    raw = te_truth(dp, model_path, layout_path, folder / "key.json")
    truths = {s: (classified_truth(raw[s], folder / f"{s}.png", folder / f"{s}.graphml"),
                  folder / f"{s}.png", folder / f"{s}.graphml") for s in TE_SHEETS}
    drawn = te_truth(dp, model_path, layout_path, folder / "key.json", every_route=True)
    drawn = {s: (classified_truth(drawn[s], folder / f"{s}.png", folder / f"{s}.graphml"),
                 folder / f"{s}.png", folder / f"{s}.graphml") for s in TE_SHEETS}
    if rev == "d":  # the copied anchors give exactly line_layers.drawn_truth's segments on the current drawer
        dt = ll.drawn_truth(model_path, layout_path, folder / "manifest.json", folder / "key.json")
        for s in TE_SHEETS:
            if dt[s]["segments"] != raw[s]["segments"]:
                raise SystemExit(f"revision D sheet {s}: truth segments differ from line_layers.drawn_truth")
    readers = {"key symbols + tracer": None}
    if rev == "a":
        for r in range(1, 6):
            for tool in ("claude", "codex"):
                readers[f"te-clean-trace-r{r}/{tool}"] = (f"te-clean-trace-r{r}", tool)
    runs = {}
    for name, src in readers.items():
        sub = tmp / f"te-{rev}-{name.replace('/', '-').replace(' ', '_').replace('+', '')}"
        sub.mkdir()
        rows = []
        for page, s in enumerate(TE_SHEETS, 1):
            png = folder / f"{s}.png"
            if src is None:
                text = {k: v.get("text") for k, v in key_doc["sheets"][s]["symbols"].items()}
                ext = key_reader(png, folder / f"{s}.graphml", text, sub, s)
            else:
                ext = ROOT / "predictions" / src[0] / src[1] / f"{s}.json"
            rows.append({"drawing_id": f"TE-{s}", "revision": rev.upper(), "page": page, "image": str(png),
                         "extraction": str(ext), "drawing_number": key_doc["sheets"][s]["drawing"],
                         "title": key_doc["sheets"][s]["title"]})
        fmt = "prediction" if src is None else "run-record"
        producer = {"method": name, "tool": "key" if src is None else src[1], "model": None}
        manifest = write_manifest(sub, f"TE revision {rev.upper()}", producer, rows, fmt)
        try:
            result, model = bundle(manifest, sub / "bundle")
        except ValueError as error:  # the intake refuses the reading: nothing is scored, the refusal is reported
            runs[name] = {"refused_by_intake": str(error)}
            continue
        rec = {"line_layers": result["line_layers"]["status"], "flow_direction": result.get("flow_direction"),
               **share(model)}
        if result["line_layers"]["status"] == "added":
            rec["per_sheet"] = per_sheet_share(model)
            rec["direction_vs_truth"] = score_directions(model, truths, {s: str(n) for n, s in enumerate(TE_SHEETS)})
            rec["diagnostic_vs_every_drawn_route"] = score_directions(
                model, drawn, {s: str(n) for n, s in enumerate(TE_SHEETS)}, controls=False)["total"]
        runs[name] = rec
    return {"truth": "data/te_process_model.json streams as the drawer laid them out"
                     + (f" (drawer, model, layout at {REV_A_COMMIT})" if rev == "a" else ""),
            "truth_directed_segments": {s: len(truths[s][0]["flow"]) for s in TE_SHEETS},
            "truth_pipe_segments": {s: len(truths[s][0]["segments"]) for s in TE_SHEETS}, "runs": runs}


def run_pahala(manifest_path, tmp):
    man_path = Path(manifest_path).resolve()
    man = json.loads(man_path.read_text(encoding="utf-8"))
    rows = []
    for s in man["sheets"]:
        if s["drawing_id"] not in DEV_PAHALA:
            continue  # other Pahala sheets: not development (P-204 has no text layer; the rest are held out)
        rows.append({**s, "image": str((man_path.parent / s["image"]).resolve()),
                     "extraction": str((man_path.parent / s["extraction"]).resolve())})
    if [r["drawing_id"] for r in rows] != list(DEV_PAHALA):
        raise SystemExit(f"--pahala-manifest must hold {', '.join(DEV_PAHALA)}")
    folder = tmp / "pahala"
    manifest = write_manifest(folder, man["set_id"] + " (development sheets P-401, P-501)", man["producer"], rows,
                              man["extraction_format"])
    name = f"{man['producer'].get('tool')} reading"
    try:
        result, model = bundle(manifest, folder / "bundle")
    except ValueError as error:
        return {"truth": None, "note": "no direction or topology key: share directed only",
                "runs": {name: {"refused_by_intake": str(error)}}}
    rec = {"line_layers": result["line_layers"]["status"], "flow_direction": result.get("flow_direction"), **share(model)}
    if result["line_layers"]["status"] == "added":
        rec["per_sheet"] = per_sheet_share(model)
    return {"truth": None, "note": "no direction or topology key: share directed only",
            "runs": {name: rec}}


def spread(values):
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"n": len(v), "mean": round(statistics.mean(v), 3), "min": min(v), "max": max(v),
            "sd": round(statistics.stdev(v), 3) if len(v) > 1 else 0.0}


def summarize(results):
    out = {}
    for name, r in results.items():
        refused = [k for k, x in r["runs"].items() if "refused_by_intake" in x]
        runs = [x for x in r["runs"].values() if "refused_by_intake" not in x]
        s = {"runs_attempted": len(r["runs"]), "runs_scored": len(runs), "runs_refused_by_intake": len(refused),
             **({"refused": refused} if refused else {}),
             "share_directed": spread([x.get("share") for x in runs]),
             "share_directed_by_sheet": spread([v["share"] for x in runs for v in x.get("per_sheet", {}).values()])}
        prec = [x["direction_vs_truth"]["total"]["precision"] for x in runs if "direction_vs_truth" in x]
        if prec:
            s["precision"] = spread(prec)
            s["precision_by_sheet"] = spread([v["precision"] for x in runs if "direction_vs_truth" in x
                                              for v in x["direction_vs_truth"]["sheets"].values()])
            s["controls_precision"] = {c: spread([x["direction_vs_truth"]["total"]["controls"][c]["precision"]
                                                  for x in runs if "direction_vs_truth" in x])
                                       for c in ("perfect", "reversed", "layout")}
        det = [x["arrow_detection"] for x in runs if "arrow_detection" in x]
        if det:
            s["arrow_detection_precision"] = spread([d["precision"] for d in det])
            s["arrow_detection_recall"] = spread([d["recall"] for d in det])
        out[name] = s
    return out


def markdown(doc):
    lines = ["# Flow direction on `piped_to`, read from the drawing-set bundle (round 6, increment 2)", "",
             "Development sets only. Every number is read from the `plant_model.json` that "
             "`scripts/import_drawing_set.py` wrote (`scripts/flow_direction_score.py`). Share = pipe segments with a "
             "direction / all pipe segments. Precision = directed segments pointing the truth's way / directed "
             "segments the truth directs (TE only). A drawn flow direction is review evidence, not isolation or "
             "lockout guidance.", "",
             "| Set | Run | Pipe segments | Directed | Conflicts | Share | Precision (scored) | Reversed control | Layout control | Arrow detection P / R |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in doc["sets"].items():
        for run, x in r["runs"].items():
            if "refused_by_intake" in x:
                why = " ".join(str(x["refused_by_intake"]).split()).replace("|", "/")
                lines.append(f"| {name} | {run} | refused by the intake: {why} | - | - | - | - | - | - | - |")
                continue
            t = (x.get("direction_vs_truth") or {}).get("total") or {}
            c = t.get("controls") or {}
            det = x.get("arrow_detection")
            lines.append(f"| {name} | {run} | {x['pipe_segments']} | {x['directed']} | "
                         f"{(x.get('flow_direction') or {}).get('conflict', '-')} | {x['share']} | "
                         + (f"{t['precision']} ({t.get('correct', 0)}/{t.get('directed', 0)})" if t else "no truth")
                         + f" | {(c.get('reversed') or {}).get('precision', '-')} | "
                         + f"{(c.get('layout') or {}).get('precision', '-')} | "
                         + (f"{det['precision']} / {det['recall']}" if det else "-") + " |")
    lines += ["", "Diagnostic, TE only: the same directed segments against every drawn route in the drawer's own order "
              "(cooling water, steam, the reactor header and the spill-back included; self-generated, not a model "
              "truth).", "", "| Set | Run | Directed and scorable | Correct | Precision |", "|---|---|---|---|---|"]
    for name, r in doc["sets"].items():
        for run, x in r["runs"].items():
            dg = x.get("diagnostic_vs_every_drawn_route")
            if dg:
                lines.append(f"| {name} | {run} | {dg.get('directed', 0)} | {dg.get('correct', 0)} | {dg['precision']} |")
    lines += ["", "Runs per set: " + "; ".join(
        f"{n} {s['runs_scored']} scored of {s['runs_attempted']} attempted, {s['runs_refused_by_intake']} refused"
        for n, s in doc["summary"].items())]
    lines += ["", "## Spread (runs, then sheets)", "", "```", json.dumps(doc["summary"], indent=1), "```", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sets", default="open100,te-a,te-d,pahala")
    ap.add_argument("--pahala-manifest", help="site-drawing-set-1 manifest holding Pahala P-401 and P-501")
    ap.add_argument("--out", required=True, help="output prefix: writes <prefix>.json and <prefix>.md")
    a = ap.parse_args(argv)
    chosen = [s for s in a.sets.split(",") if s]
    bad = [s for s in chosen if s not in SETS]
    if bad:
        ap.error(f"unknown or held-out set(s) {bad}; development sets: {', '.join(SETS)}")
    results = {}
    with tempfile.TemporaryDirectory(prefix="flow-direction-score-") as t:
        tmp = Path(t)
        for name in chosen:
            if name == "open100":
                results[name] = run_open100(tmp)
            elif name in ("te-a", "te-d"):
                results[name] = run_te(name[-1], tmp)
            elif a.pahala_manifest:
                results[name] = run_pahala(a.pahala_manifest, tmp)
            else:
                results[name] = {"truth": None, "runs": {}, "note": "not run: give --pahala-manifest"}
    doc = {"script": "scripts/flow_direction_score.py", "goal": "docs/GOAL_ROUND6.md increment 2",
           "held_out_not_read": "OPEN100 sheets 6-11, the DEXPI held-out renders, Pahala sheets other than P-401/P-501",
           "sets": results, "summary": summarize(results)}
    page = markdown(doc)  # rendered before anything is written, so a failure leaves no partial report
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{out}.json").write_text(json.dumps(doc, indent=1, default=str) + "\n", encoding="utf-8")
    Path(f"{out}.md").write_text(page, encoding="utf-8")
    print(json.dumps(doc["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
