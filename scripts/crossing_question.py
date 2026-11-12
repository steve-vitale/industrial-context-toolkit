"""A blind second evaluator for crossed-line cases in loop assembly (corroboration channel b).

scripts/loop_assembly.py joins two dashed runs through a pipe or another line only when their dash pattern is in step,
and marks the line merged_through_crossing with its crossing points. Geometry alone cannot tell one line crossing a
pipe from two lines drawn to it from either side, so everything resting on such a line carries the weakest tier,
traced_through_crossing, until an independent channel promotes it (or this evaluator, enabled, demotes it with a
confident "two lines"). This is one such channel, built as a separate evaluator:

  Blind. For each crossing it shows only a crop centred on the crossing, with everything outside two narrow bands
  blanked: the dashed line's band (blue) and the crossed line's band (green). No tag, no symbol, no tracer verdict
  and no loop hypothesis is shown. One question (extraction/crossing_prompt.md): does the dashed line continue across,
  or do two lines end here? Answers: continues / two_lines / cannot_tell, with a confidence.
  Configurable model. --tool/--model pick the judge; by default it is a different model from the bundle's reader when
  one is available. Every answer records the judge model and whether it is the reader's own model (weaker
  independence). Today only the claude path runs here, so same-family runs are flagged as such.
  Its own scorecard (`scorecard`): measured alone against ground truth before it is allowed to count: TE revision D's
  true crossings, every merge in the 60-placement sweep (two lines drawn to a pipe, in step by chance), merges in
  re-drawn reviewer fixtures, and three controls (an obvious crossing, obvious separate ends, a blank crop). Two runs
  for spread. The scorecard decides `assert_enabled`: the judge's "continues" may support a loop only if, in every
  run, it supported no false merge and no negative control, and supported at least one true crossing. Otherwise its
  answers are attached as advice and neither promote nor demote anything.
  Unanswered crossings ("cannot_tell", below THRESHOLD, no answer) leave the line at traced_through_crossing, with
  its review question.

    python scripts/crossing_question.py scorecard [--tool claude] [--runs 2]   # spends model calls
    python scripts/crossing_question.py ask --bundle <bundle dir> --out <answers.json> --scorecard <scorecard.json>
    python scripts/import_drawing_set.py <manifest> <out> --crossing-answers <answers.json>

Answers are keyed by sheet image sha256 and crossing pixel, so they apply only to the exact image they were asked of.
The model call reuses scripts/run_extraction.py's subscription CLI paths (run_claude, run_codex).
"""
import argparse
import hashlib
import json
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = ROOT / "extraction" / "crossing_prompt.md"
OUT = ROOT / "out" / "round6"
THRESHOLD = 0.8      # an answer counts only at this confidence or above (the A412 bar, fixed before the first run)
BATCH = 8            # crops per call
PANEL = 360          # px per panel side
TOOLS = {"claude": "claude-opus-5-5", "codex": "gpt-6.1-sol"}
VERDICTS = ("continues", "two_lines", "cannot_tell")
BLUE, GREEN = (200, 80, 0), (0, 150, 0)  # BGR: the dashed line's band, the crossed line's band


def key(image_sha, crossing):
    """loop_assembly.crossing_key: sha:axis:gap_lo-gap_hi:x,y."""
    import loop_assembly as la
    return la.crossing_key(image_sha, crossing)


def crop_panel(gray, crossing, n):
    """The blind panel: a crop centred on the crossing, about three symbol sides across, keeping only the ink in the
    dashed line's band (blue) and the crossed line's band (green); everything else is blanked, so no tag or symbol
    shows. Numbered in the corner."""
    import cv2
    import numpy as np
    x, y = crossing["at_px"]
    half = int(max(30, 1.5 * (crossing.get("side_px") or 40)))
    band = max(3, int(crossing.get("stroke_px") or 4))
    pad = cv2.copyMakeBorder(gray, half, half, half, half, cv2.BORDER_CONSTANT, value=255)
    crop = pad[y:y + 2 * half, x:x + 2 * half]
    ink = crop < 128
    c = half
    rows, cols = np.indices(crop.shape)
    along = (np.abs(cols - c) <= band) if crossing.get("axis", "v") == "v" else (np.abs(rows - c) <= band)
    across = (np.abs(rows - c) <= band + 2) if crossing.get("axis", "v") == "v" else (np.abs(cols - c) <= band + 2)
    panel = np.full(crop.shape + (3,), 255, np.uint8)
    panel[ink & along] = BLUE
    panel[ink & across] = GREEN
    panel = cv2.resize(panel, (PANEL, PANEL), interpolation=cv2.INTER_NEAREST)
    cv2.rectangle(panel, (0, 0), (PANEL - 1, PANEL - 1), (160, 160, 160), 1)
    cv2.putText(panel, str(n), (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    return panel


def contact_sheet(panels, path):
    import cv2
    import numpy as np
    cols = min(4, len(panels))
    rows = (len(panels) + cols - 1) // cols
    sheet = np.full((rows * PANEL, cols * PANEL, 3), 255, np.uint8)
    for i, p in enumerate(panels):
        r, c = divmod(i, cols)
        sheet[r * PANEL:(r + 1) * PANEL, c * PANEL:(c + 1) * PANEL] = p
    cv2.imwrite(str(path), sheet)


def parse(text, n):
    from run_extraction import parse_json
    doc, err = parse_json(text)
    out = {}
    for a in (doc or {}).get("items", []) if isinstance(doc, dict) else []:
        try:
            i = int(a.get("n"))
            conf = float(a.get("confidence"))
        except (TypeError, ValueError):
            continue
        if 1 <= i <= n and a.get("verdict") in VERDICTS:
            out[i] = {"verdict": a["verdict"], "confidence": round(conf, 3), "reason": str(a.get("reason", ""))[:300]}
    return out, err


def judge_model(tool, model=None, reader_model=None):
    """(tool, model, same_model_as_reader). The default judge is a different model from the reader when one exists."""
    chosen = model or TOOLS[tool]
    same = bool(reader_model) and chosen.split("[")[0].split("-")[0] == str(reader_model).split("[")[0].split("-")[0]
    return tool, chosen, same


def default_tool(reader_model, available=("claude",)):
    """Prefer a judge from another family than the reader; fall back to the only one available."""
    for tool in available:
        if not reader_model or not str(reader_model).startswith(TOOLS[tool].split("-")[0]):
            return tool
    return available[0]


def ask(items, tool="claude", model=None, reader_model=None, call=None):
    """items: [{"key", "image" (path) or "gray" (array), "at_px", "axis", "side_px", "stroke_px"}].
    Returns ({key: answer}, [call records]). `call(png, prompt)` replaces the model call (tests)."""
    import cv2
    tool, chosen, same = judge_model(tool, model, reader_model)
    if call is None:
        import run_extraction as rx

        def call(png, prompt):
            return (rx.run_claude if tool == "claude" else rx.run_codex)(png, chosen, prompt)
    prompt_base = PROMPT_FILE.read_text(encoding="utf-8")
    answers, calls = {}, []
    items = list({it["key"]: it for it in items}.values())  # one question per key: an answer is never overwritten
    for b in range(0, len(items), BATCH):
        batch = items[b:b + BATCH]
        panels = [crop_panel(it["gray"] if "gray" in it else cv2.imread(str(it["image"]), cv2.IMREAD_GRAYSCALE), it, n)
                  for n, it in enumerate(batch, 1)]
        with tempfile.TemporaryDirectory() as t:
            png = Path(t) / "panels.png"
            contact_sheet(panels, png)
            prompt = prompt_base + "\n".join(f"{n}. panel {n}" for n in range(1, len(batch) + 1))
            t0 = time.time()
            try:
                res = call(png, prompt)
            except Exception as e:  # a failed call leaves its crossings unanswered (they go to review)
                res = {"text": None, "error": f"{type(e).__name__}: {e}"}
            seconds = round(time.time() - t0, 1)
        got, err = parse(res.get("text"), len(batch))
        calls.append({"items": len(batch), "seconds": seconds, "model": res.get("model") or chosen,
                      "cost_usd_notional": res.get("cost_usd_notional"), "error": res.get("error"),
                      "parse_error": err, "raw_text": res.get("text")})
        for n, it in enumerate(batch, 1):
            answers[it["key"]] = {**got.get(n, {"verdict": "cannot_tell", "confidence": 0.0, "reason": "no answer"}),
                                  "judge_tool": tool, "judge_model": res.get("model") or chosen,
                                  "same_model_as_reader": same}
    return answers, calls


def supports(answer, assert_enabled=True):
    """True when an answer may corroborate a merged line: a confident "continues" from a judge whose scorecard
    enabled it. Anything else (two_lines, cannot_tell, below THRESHOLD, no answer, judge not enabled) goes to review."""
    return bool(assert_enabled and answer and answer.get("verdict") == "continues"
                and answer.get("confidence", 0) >= THRESHOLD)


# ---------------------------------------------------------------- the scorecard

def _sheet(draw):
    import numpy as np
    img = np.full((600, 1000), 255, np.uint8)
    boxes = {}
    draw(img, boxes)
    return img, boxes


def _bub(img, boxes, k, x, y, r=24):
    import cv2
    cv2.circle(img, (x, y), r, 0, 2)
    boxes[k] = [x - r - 1, y - r - 1, x + r + 1, y + r + 1]


def _dsh(img, pts, dash=13, gap=6):
    import cv2
    import numpy as np
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = float(np.hypot(x1 - x0, y1 - y0))
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        t = 0.0
        while t < L:
            e = min(L, t + dash)
            cv2.line(img, (int(round(x0 + ux * t)), int(round(y0 + uy * t))),
                     (int(round(x0 + ux * (e - 1))), int(round(y0 + uy * (e - 1)))), 0, 2)
            t = e + gap


def _merges(name, img, boxes, truth, pair=None):
    """The crossings of every merged line the tracer finds on a drawn sheet, labelled with the drawing's truth."""
    import cv2
    import loop_assembly as la
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "s.png"
        cv2.imwrite(str(p), img)
        r = la.dashed_signal_lines(p, [{"id": k, "class": "instrumentation",
                                        "box": [b[0] / 1.0, b[1] * 1000 / 600, b[2] / 1.0, b[3] * 1000 / 600]}
                                       for k, b in boxes.items()])
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
    return [{"key": key(sha, c), "gray": img, **c, "truth": truth, "source": name}
            for x in r["lines"] if x.get("merged_through_crossing") and (pair is None or sorted(x["members"]) == pair)
            for c in x["crossings"]]


def sweep_merges(n=60, seed=1):
    """Every merge in the reviewer's 60-placement sweep (a_inphase.py): two lines drawn to a pipe from either side;
    any merge of them is false."""
    import cv2
    rng, out = random.Random(seed), []
    for k in range(n):
        yc, yd = 100 + rng.randint(0, 30), 500 - rng.randint(0, 30)

        def draw(img, b, yc=yc, yd=yd):
            _bub(img, b, "C", 400, yc)
            _bub(img, b, "D", 400, yd)
            cv2.line(img, (50, 300), (950, 300), 0, 2)
            _bub(img, b, "TT", 150, yc)
            _dsh(img, [(175, yc), (375, yc)])
            _dsh(img, [(400, yc + 25), (400, 299)])
            _dsh(img, [(400, yd - 25), (400, 301)])
        out += _merges(f"sweep#{k}", *_sheet(draw), "two_lines", ["C", "D"])
    return out


def fixture_merges():
    """Merges in re-drawn reviewer fixtures (loops-rereview/, loops-rereview3/ b_merge.py): a true dashed crossing
    (b_cross_cc) and the false open cases. A fixture whose lines the tracer keeps apart contributes nothing."""
    import cv2

    def cross_cc(img, b):
        _bub(img, b, "C", 400, 100)
        _bub(img, b, "D", 400, 500)
        _bub(img, b, "L", 100, 300)
        _bub(img, b, "R", 700, 300)
        _dsh(img, [(125, 300), (675, 300)])
        _dsh(img, [(400, 125), (400, 475)])

    def dashed_h_cc(img, b):
        _bub(img, b, "C", 400, 100)
        _bub(img, b, "D", 400, 500)
        _bub(img, b, "L", 100, 300)
        _bub(img, b, "R", 700, 300)
        _dsh(img, [(125, 300), (675, 300)])
        _dsh(img, [(400, 125), (400, 294)])
        _dsh(img, [(400, 306), (400, 475)])

    def open_case_pipe(img, b):
        _bub(img, b, "C", 400, 100)
        _bub(img, b, "D", 400, 500)
        cv2.line(img, (50, 300), (950, 300), 0, 4)
        _dsh(img, [(400, 125), (400, 296)])
        _dsh(img, [(400, 304), (400, 475)])
    return (_merges("b_cross_cc", *_sheet(cross_cc), "continues", ["C", "D"])
            + _merges("b_dashedH_cc", *_sheet(dashed_h_cc), "two_lines", ["C", "D"])
            + _merges("open_case_pipe", *_sheet(open_case_pipe), "two_lines", ["C", "D"]))


def controls():
    """Positive: an obvious crossing (one dashed line, the pipe in a dash gap). Negative: obvious separate ends (two
    dashed lines stopping well short of the pipe, out of step). Blank: an empty crop."""
    import cv2
    import numpy as np

    def item(name, img, truth):
        sha = hashlib.sha256(img.tobytes()).hexdigest()
        c = {"at_px": [400, 300], "axis": "v", "side_px": 50.0, "stroke_px": 6, "crosses": "pipe"}
        return {"key": key(sha, c), "gray": img, **c, "truth": truth, "source": name}
    pos = np.full((600, 1000), 255, np.uint8)
    _dsh(pos, [(400, 120), (400, 296)], dash=13, gap=8)
    _dsh(pos, [(400, 305), (400, 480)], dash=13, gap=8)
    cv2.line(pos, (50, 300), (950, 300), 0, 2)
    neg = np.full((600, 1000), 255, np.uint8)
    _dsh(neg, [(400, 120), (400, 284)])
    _dsh(neg, [(400, 480), (400, 318)])
    cv2.line(neg, (50, 300), (950, 300), 0, 2)
    blank = np.full((600, 1000), 255, np.uint8)
    return [item("control:obvious_crossing", pos, "continues"), item("control:obvious_separate_ends", neg, "two_lines"),
            item("control:blank", blank, "cannot_tell")]


def te_d_merges(bundle):
    """TE revision D's merged-line crossings: the key draws each as one signal line, so every one is a true crossing."""
    import cv2
    import loop_assembly as la
    bundle = Path(bundle)
    model = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
    out, seen = [], set()
    for x in la.sheet_signal_lines(model, bundle / "source"):
        png = bundle / "source" / f"{x['sheet']}.png"
        sha = hashlib.sha256(png.read_bytes()).hexdigest()
        for c in x.get("crossings", []):
            k = key(sha, c)
            if k not in seen:
                seen.add(k)
                out.append({"key": k, "gray": cv2.imread(str(png), cv2.IMREAD_GRAYSCALE), **c, "truth": "continues",
                            "source": f"te_d:{x['id']}"})
    return out


def score_run(items, answers, bar=THRESHOLD):
    rows = []
    for it in items:
        a = answers.get(it["key"]) or {}
        rows.append({"source": it["source"], "truth": it["truth"], "verdict": a.get("verdict"),
                     "confidence": a.get("confidence"), "supports": supports(a)})

    def part(sel):
        xs = [r for r in rows if sel(r)]
        answered = [r for r in xs if r["verdict"] in ("continues", "two_lines") and (r["confidence"] or 0) >= bar]
        return {"n": len(xs), "answered_at_bar": len(answered),
                "correct_at_bar": sum(r["verdict"] == r["truth"] for r in answered),
                "accuracy_at_bar": round(sum(r["verdict"] == r["truth"] for r in answered) / len(answered), 3)
                if answered else None,
                "cannot_tell_or_below_bar": len(xs) - len(answered),
                "supported_continues": sum(r["supports"] for r in xs)}
    return {"true_crossings_te_d": part(lambda r: r["source"].startswith("te_d")),
            "false_merges_sweep": part(lambda r: r["source"].startswith("sweep")),
            "fixtures_true": part(lambda r: not r["source"].startswith(("te_d", "sweep", "control"))
                                  and r["truth"] == "continues"),
            "fixtures_false": part(lambda r: not r["source"].startswith(("te_d", "sweep", "control"))
                                   and r["truth"] == "two_lines"),
            "controls": {r["source"]: {"verdict": r["verdict"], "confidence": r["confidence"]}
                         for r in rows if r["source"].startswith("control")},
            "rows": rows}


def enabled(runs):
    """The pre-set gate: the judge may support loops only if, in every run, it supported no false merge (sweep and
    fixtures) and not the negative control, and supported at least one true crossing."""
    def ok(s):
        false = s["false_merges_sweep"]["supported_continues"] + s["fixtures_false"]["supported_continues"]
        neg = s["controls"].get("control:obvious_separate_ends") or {}
        true = s["true_crossings_te_d"]["supported_continues"] + s["fixtures_true"]["supported_continues"]
        return false == 0 and not supports(neg) and true > 0
    return bool(runs) and all(ok(r["score"]) for r in runs)


def scorecard(te_bundle, tool="claude", model=None, n_runs=2, call=None):
    items = te_d_merges(te_bundle) + sweep_merges() + fixture_merges() + controls()
    random.Random(7).shuffle(items)  # mix the kinds across panels and calls
    runs = []
    for r in range(n_runs):
        answers, calls = ask(items, tool, model, call=call)
        runs.append({"run": r + 1, "calls": len(calls), "seconds": round(sum(c["seconds"] for c in calls), 1),
                     "errors": sum(bool(c["error"] or c["parse_error"]) for c in calls),
                     "judge_model": calls[0]["model"] if calls else None,
                     "score": score_run(items, answers), "answers": answers})
    return {"script": "scripts/crossing_question.py", "prompt_sha256": hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(),
            "threshold": THRESHOLD, "tool": tool, "model": model or TOOLS[tool],
            "items": [{k: v for k, v in it.items() if k != "gray"} for it in items],
            "runs": runs, "assert_enabled": enabled(runs)}


def build_te_d_bundle(folder):
    """The TE revision D key-symbols bundle, built the way scripts/loop_score.py builds it."""
    import flow_direction_score as fds
    import import_drawing_set as dset
    folder = Path(folder)
    _, _, _, src = fds.revision_inputs("d", folder)
    key_doc = json.loads((src / "key.json").read_text(encoding="utf-8"))
    rows = []
    for page, s in enumerate(fds.TE_SHEETS, 1):
        png = src / f"{s}.png"
        text = {k: v.get("text") for k, v in key_doc["sheets"][s]["symbols"].items()}
        rows.append({"drawing_id": f"TE-{s}", "revision": "D", "page": page, "image": str(png),
                     "extraction": str(fds.key_reader(png, src / f"{s}.graphml", text, folder, s)),
                     "drawing_number": key_doc["sheets"][s]["drawing"], "title": key_doc["sheets"][s]["title"]})
    manifest = fds.write_manifest(folder, "TE revision D", {"method": "key symbols + tracer", "tool": "key",
                                                            "model": None}, rows, "prediction")
    dset.import_set(manifest, folder / "bundle", loops=True)
    return folder / "bundle"


def markdown(doc):
    lines = ["# Crossing evaluator scorecard (development)", "",
             f"Judge: {doc['tool']} / {doc['model']}; bar {doc['threshold']}; prompt sha256 {doc['prompt_sha256'][:12]}. "
             f"assert_enabled: **{doc['assert_enabled']}**.", "",
             "| Run | Set | n | answered at bar | correct | accuracy | can't tell or below bar | supported 'continues' |",
             "|---|---|---|---|---|---|---|---|"]
    for r in doc["runs"]:
        for name in ("true_crossings_te_d", "false_merges_sweep", "fixtures_true", "fixtures_false"):
            s = r["score"][name]
            lines.append(f"| {r['run']} | {name} | {s['n']} | {s['answered_at_bar']} | {s['correct_at_bar']} | "
                         f"{s['accuracy_at_bar']} | {s['cannot_tell_or_below_bar']} | {s['supported_continues']} |")
    lines += ["", "| Run | Calls | Seconds | Errors | Controls (verdict, confidence) |", "|---|---|---|---|---|"]
    for r in doc["runs"]:
        c = "; ".join(f"{k.split(':')[1]}: {v['verdict']} {v['confidence']}" for k, v in r["score"]["controls"].items())
        lines.append(f"| {r['run']} | {r['calls']} | {r['seconds']} | {r['errors']} | {c} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask", help="ask the crossing question for every merged line in a bundle")
    a.add_argument("--bundle", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--scorecard", required=True, help="the judge's scorecard JSON; its assert_enabled is copied")
    a.add_argument("--tool", choices=sorted(TOOLS))
    a.add_argument("--model")
    s = sub.add_parser("scorecard", help="measure the judge alone against ground truth (spends model calls)")
    s.add_argument("--tool", default="claude", choices=sorted(TOOLS))
    s.add_argument("--model")
    s.add_argument("--runs", type=int, default=2)
    s.add_argument("--out", default=str(OUT / "crossing_judge_dev"))
    args = ap.parse_args(argv)
    if args.cmd == "scorecard":
        with tempfile.TemporaryDirectory() as t:
            doc = scorecard(build_te_d_bundle(Path(t)), args.tool, args.model, args.runs)
        doc["command"] = "python scripts/crossing_question.py " + " ".join(argv if argv is not None else sys.argv[1:])
        Path(args.out + ".json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        Path(args.out + ".md").write_text(markdown(doc), encoding="utf-8")
        print(markdown(doc))
        return
    bundle = Path(args.bundle)
    model = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
    reader = ((model.get("meta") or {}).get("intake") or {}).get("supplied_producer", {}).get("model")
    tool = args.tool or default_tool(reader)
    card = json.loads(Path(args.scorecard).read_text(encoding="utf-8"))
    items = []
    for x in (model.get("control_loops") or {}).get("signal_lines", []):
        png = bundle / "source" / f"{x['sheet']}.png"
        sha = hashlib.sha256(png.read_bytes()).hexdigest()
        items += [{"key": key(sha, c), "image": str(png), **c} for c in x.get("crossings", [])]
    items = list({it["key"]: it for it in items}.values())
    answers, calls = ask(items, tool, args.model, reader_model=reader)
    doc = {"prompt_sha256": hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(), "threshold": THRESHOLD,
           "assert_enabled": bool(card.get("assert_enabled")) and card.get("prompt_sha256") ==
           hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(),
           "scorecard": str(args.scorecard), "reader_model": reader, "answers": answers, "calls": calls}
    Path(args.out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"{len(items)} crossings, {len(calls)} calls, {sum(c['seconds'] for c in calls):.0f} s -> {args.out}")


if __name__ == "__main__":
    main()
