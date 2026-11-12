"""A412: a narrow model re-check of the symbols the pipeline already flags, judged by review load.

Idea credited to the public MIT repository ScottDuncanAI/PID-to-Knowledge-Graph, whose QA report describes a
model re-check loop. Nothing here uses or depends on that tool; this is a separate, smaller implementation.

What it does, on the development sheets OPEN100 0-5 only (any other sheet is refused, with no override):
  1. Flagged items. A symbol is flagged when scripts/confidence.py rates it amber or red, or when it carries one of
     the explicit pipeline flags dup_box (a double detection) or tag_placeholder. Green, unflagged symbols are never
     sent and never changed. Links are not re-checked here (a link has no single crop); they follow the symbols.
  2. Ask. For each flagged symbol a crop of the sheet (its box in red, other detections nearby in blue) and its
     current reading (class, tag) go to the SAME model that made the reading, with extraction/recheck_prompt.md.
     Items are sent in batches of up to BATCH crops per call. The model can only confirm, correct the class,
     reject, or call the item a duplicate of a blue box. It cannot add, move or resize anything.
  3. Apply (rules fixed before the first run). A reading changes only on a confident answer (confidence >=
     THRESHOLD): "correct" with a valid, different class relabels; "reject" removes; "duplicate" removes only if an
     overlapping symbol is still kept (so a pair of duplicates never both disappear). Everything else is unchanged.
     Every flagged item gets a record: before, after, verdict, confidence, reason and whether it was applied.
  4. Re-trace. The connections are re-traced from the updated symbols with scripts/trace_connections.py defaults,
     exactly as the saved traced reading was made (retracing the saved symbols reproduces its links exactly).

Controls scored beside it on the same keys: the saved reading unchanged ("accept every flagged item"), "reject every
flagged item", and the scorer controls (perfect, every class wrong, every box shifted, empty).

    python scripts/recheck_flagged.py run --tool claude --run r1        # spends model calls (subscription CLIs)
    python scripts/recheck_flagged.py report                            # scores everything saved, writes the table

Raw replies go to runs/a412-recheck-<run>/<tool>/<sheet>.json (gitignored, like every raw record). The parsed
answers, the change records and the resulting prediction go to out/recheck_a412/<run>/<tool>/<sheet>.json.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import confidence as cf  # noqa: E402
import score_pid2graph as sc  # noqa: E402
import trace_connections as tc  # noqa: E402
from run_extraction import SYSTEM_LINE, parse_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "external" / "pid2graph" / "PID2Graph" / "Complete" / "PID2Graph OPEN100"
PRED = ROOT / "predictions"
OUT = ROOT / "out" / "recheck_a412"
RUNS = ROOT / "runs"
PROMPT_FILE = ROOT / "extraction" / "recheck_prompt.md"
DEV_SHEETS = [str(i) for i in range(6)]          # development only; GOAL_ROUND6.md seals 6-11
READING = "r2-tiles-trace"                       # the saved traced reading being re-checked
SYMBOL_LABEL = "r2-tiles-2x2"                    # its symbol source (the traced run names it in source_label)
REPEAT_LABEL = "r2-tiles-2x2-repeat"             # a second saved reading, for the reader's own run spread
MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6.1-sol"}  # the models that made the saved reading
THRESHOLD = 0.8
BATCH = 8
EXPLICIT_FLAGS = ("dup_box", "tag_placeholder")
VERDICTS = {"confirm", "correct", "reject", "duplicate"}
TIMEOUT_S = 900


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check_sheets(sheets):
    bad = [s for s in sheets if s not in DEV_SHEETS]
    if bad:
        sys.exit(f"refusing sheets {bad}: A412 runs on the development sheets OPEN100 0-5 only (docs/GOAL_ROUND6.md)")


def load_pred(label, tool, sheet):
    return json.loads((PRED / label / tool / f"{sheet}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 1. flagged items

def flagged(tool, sheet):
    """{symbol id: [reasons]} for the symbols the pipeline flags on the saved reading. Uses confidence.py on the
    committed predictions (no answer key)."""
    cf.RUN_ROOTS = [PRED]
    rated = cf.rate_run(READING, tool, sheet, DATA, cf.load_model())
    out = {}
    for sid, r in rated["symbols"].items():
        why = []
        if r["tier"] != "green":
            why.append(f"tier {r['tier']} (risk {r['risk']})")
        why += [f for f in EXPLICIT_FLAGS if r["features"][f] >= 1]
        if why:
            out[sid] = why
    return out


# ---------------------------------------------------------------- 2. crops and the model call

def px_box(box, w, h):
    return [box[0] * w / 1000, box[1] * h / 1000, box[2] * w / 1000, box[3] * h / 1000]


def make_crop(im, sym, others, path):
    from PIL import ImageDraw
    w, h = im.size
    x0, y0, x1, y1 = px_box(sym["box"], w, h)
    m = max(x1 - x0, y1 - y0, 40)
    cx0, cy0, cx1, cy1 = (int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(w, x1 + m)), int(min(h, y1 + m)))
    crop = im.crop((cx0, cy0, cx1, cy1)).convert("RGB")
    k = max(1.0, min(3.0, 420 / max(crop.size)))
    crop = crop.resize((int(crop.size[0] * k), int(crop.size[1] * k)))
    d = ImageDraw.Draw(crop)
    tr = lambda b: [(b[0] - cx0) * k, (b[1] - cy0) * k, (b[2] - cx0) * k, (b[3] - cy0) * k]  # noqa: E731
    for o in others:
        ob = px_box(o["box"], w, h)
        if ob[2] > cx0 and ob[0] < cx1 and ob[3] > cy0 and ob[1] < cy1:
            b = tr(ob)
            d.rectangle([b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], outline=(0, 90, 255), width=1)
    b = tr([x0, y0, x1, y1])
    d.rectangle([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], outline=(230, 0, 0), width=2)
    crop.save(path)


def item_lines(items):
    return "\n".join(f'{n}. image item{n}.png: class "{s["class"]}", tag {json.dumps(s.get("tag"))}'
                     for n, s in enumerate(items, 1))


def call_claude(work, n_items, prompt):
    prompt += (f"\n\nThe images are the files item1.png to item{n_items}.png in the current folder. "
               "Open each with the Read tool.")
    cmd = ["claude", "-p", "--output-format", "json", "--system-prompt", SYSTEM_LINE, "--allowedTools", "Read",
           "--strict-mcp-config", "--disable-slash-commands", "--model", MODELS["claude"]]
    p = subprocess.run(cmd, cwd=work, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       timeout=TIMEOUT_S, shell=(os.name == "nt"))
    if not p.stdout.strip():
        return {"text": None, "error": (p.stderr or "no output")[-2000:]}
    out = json.loads(p.stdout)
    return {"text": out.get("result"), "model": ",".join((out.get("modelUsage") or {}).keys()) or MODELS["claude"],
            "cost_usd_notional": out.get("total_cost_usd"), "usage": out.get("usage"),
            "error": out.get("result") if out.get("is_error") else None}


def call_codex(work, n_items, prompt):
    prompt += f"\n\nThe {n_items} attached images are item1.png to item{n_items}.png, in that order."
    last = work / "last.txt"
    cmd = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check", "-s", "read-only",
           "-C", str(work), "-o", str(last), "-m", MODELS["codex"]]
    for n in range(1, n_items + 1):
        cmd += ["-i", str(work / f"item{n}.png")]
    cmd.append("-")
    p = subprocess.run(cmd, cwd=work, input=prompt, capture_output=True, text=True, encoding="utf-8",
                       timeout=TIMEOUT_S, shell=(os.name == "nt"))
    m = re.search(r"^model:\s*(\S+)", p.stderr + p.stdout, flags=re.M)
    tok = re.search(r"tokens used\s*:?\s*([\d,]+)", p.stderr + p.stdout, flags=re.I)
    text = last.read_text(encoding="utf-8") if last.exists() else None
    return {"text": text, "model": m.group(1) if m else MODELS["codex"],
            "usage": {"total_tokens": int(tok.group(1).replace(",", ""))} if tok else None,
            "error": None if text else (p.stderr[-2000:] or "no output")}


CALLS = {"claude": call_claude, "codex": call_codex}


def ask_batch(tool, im, batch, all_syms, base_prompt):
    work = Path(tempfile.mkdtemp(prefix="a412-"))
    try:
        for n, s in enumerate(batch, 1):
            make_crop(im, s, [o for o in all_syms if o["id"] != s["id"]], work / f"item{n}.png")
        prompt = base_prompt + item_lines(batch)
        t0 = time.time()
        try:
            res = CALLS[tool](work, len(batch), prompt)
        except Exception as e:  # a failed call is recorded; its items stay unchanged
            res = {"text": None, "error": f"{type(e).__name__}: {e}"}
        parsed, perr = parse_json(res.get("text"))
        answers = {}
        for a in (parsed or {}).get("items", []) if isinstance(parsed, dict) else []:
            try:
                n = int(a.get("n"))
            except (TypeError, ValueError):
                continue
            if 1 <= n <= len(batch):
                answers[batch[n - 1]["id"]] = a
        return {"ids": [s["id"] for s in batch], "seconds": round(time.time() - t0, 1), "model": res.get("model"),
                "cost_usd_notional": res.get("cost_usd_notional"), "usage": res.get("usage"),
                "error": res.get("error"), "parse_error": perr, "raw_text": res.get("text"), "answers": answers}
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- 3. apply

def symbols_with_box(pred):
    """The prediction's symbols, each with a 0-1000 "box" read the way the scorer reads it (None if unreadable)."""
    return [dict(s, box=cf.read_box(s)) for s in pred.get("symbols", [])]


def apply_answers(symbols, flags, answers):
    """(new symbol list, change records). Only flagged ids can change; nothing is added or moved."""
    by_id = {str(s["id"]): s for s in symbols}
    kept_ids = set(by_id)
    new_class, records = {}, []
    # Duplicates are settled least-sure first, so of a pair the item the model itself was less sure of goes.
    order = sorted(flags, key=lambda i: (by_id[i].get("confidence") if isinstance(by_id[i].get("confidence"),
                                                                                (int, float)) else 1.0, i))
    for sid in order:
        s, a = by_id[sid], answers.get(sid)
        rec = {"id": sid, "flags": flags[sid], "before": {"class": s.get("class"), "tag": s.get("tag")},
               "verdict": None, "class": None, "confidence": None, "reason": None, "applied": False,
               "after": {"class": s.get("class"), "kept": True}, "note": ""}
        if a is None:
            rec["note"] = "no answer: unchanged"
            records.append(rec)
            continue
        v = str(a.get("verdict", "")).strip().lower()
        conf = a.get("confidence")
        conf = float(conf) if isinstance(conf, (int, float)) else None
        rec.update({"verdict": v, "class": a.get("class"), "confidence": conf, "reason": a.get("reason")})
        confident = conf is not None and conf >= THRESHOLD
        if v not in VERDICTS:
            rec["note"] = "invalid verdict: unchanged"
        elif v == "confirm":
            rec["note"] = "confirmed: unchanged"
        elif not confident:
            rec["note"] = f"confidence below {THRESHOLD}: unchanged"
        elif v == "correct":
            if a.get("class") in sc.SCORED and a.get("class") != s.get("class"):
                new_class[sid] = a["class"]
                rec.update(applied=True, after={"class": a["class"], "kept": True}, note="class corrected")
            else:
                rec["note"] = "correction names no valid different class: unchanged"
        elif v == "reject":
            kept_ids.discard(sid)
            rec.update(applied=True, after={"class": None, "kept": False}, note="removed")
        elif v == "duplicate":
            partner = [o for o in kept_ids if o != sid and by_id[o]["box"] and s["box"]
                       and sc.iou(s["box"], by_id[o]["box"]) >= 0.1]
            if partner:
                kept_ids.discard(sid)
                rec.update(applied=True, after={"class": None, "kept": False},
                           note=f"removed as a duplicate of {sorted(partner)[0]}")
            else:
                rec["note"] = "duplicate with no overlapping symbol still kept: unchanged"
        records.append(rec)
    out = []
    for s in symbols:
        sid = str(s["id"])
        if sid not in kept_ids:
            continue
        orig = {k: v for k, v in s.items() if k != "box"} if "bbox" in s else dict(s)
        if sid in new_class:
            orig = dict(orig, **{"class": new_class[sid]})
        out.append(orig)
    # Invariants: nothing new, and every unflagged symbol is byte-for-byte as it was.
    assert {str(s["id"]) for s in out} <= set(by_id)
    for s in out:
        if str(s["id"]) not in flags:
            o = by_id[str(s["id"])]
            assert {k: v for k, v in s.items()} == {k: v for k, v in o.items() if k != "box" or "bbox" not in o}
    return out, sorted(records, key=lambda r: r["id"])


def link_changes(before, after, removed):
    """Links the re-trace changed beyond simply dropping the removed symbols' own links. Removing a symbol un-erases
    its box, so the tracer can join two networks there and add a link between kept symbols: recorded, never silent."""
    key = lambda c: tuple(sorted((str(c["from"]), str(c["to"]))))  # noqa: E731
    b, a = {key(c) for c in before}, {key(c) for c in after}
    expected = {l for l in b if not set(l) & set(removed)}
    return {"dropped_with_removed_symbols": sorted(map(list, b - expected)), "added": sorted(map(list, a - expected)),
            "lost_otherwise": sorted(map(list, expected - a))}


def retrace(sheet, symbols):
    return [{"from": str(c["from"]), "to": str(c["to"])} for c in tc.trace(DATA / f"{sheet}.png", symbols)]


# ---------------------------------------------------------------- run

def run(tool, run_label, sheets, workers):
    from PIL import Image
    check_sheets(sheets)
    base_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    for sheet in sheets:
        out_path = OUT / run_label / tool / f"{sheet}.json"
        raw_path = RUNS / f"a412-recheck-{run_label}" / tool / f"{sheet}.json"
        if out_path.exists():
            print(f"skip {tool} {sheet}: {out_path.relative_to(ROOT)} exists")
            continue
        src = load_pred(SYMBOL_LABEL, tool, sheet)
        symbols = symbols_with_box(src["prediction"])
        flags = flagged(tool, sheet)
        items = [s for s in symbols if str(s["id"]) in flags]
        valid = [s for s in symbols if s["box"]]
        batches = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
        t0 = time.time()
        with Image.open(DATA / f"{sheet}.png") as im:
            im.load()
            with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
                calls = list(ex.map(lambda b: ask_batch(tool, im, b, valid, base_prompt), batches))
        answers = {k: v for c in calls for k, v in c["answers"].items()}
        new_syms, records = apply_answers(symbols, flags, answers)
        pred = {"symbols": new_syms, "connections": retrace(sheet, new_syms)}
        removed = [r["id"] for r in records if r["applied"] and not r["after"]["kept"]]
        links = link_changes(load_pred(READING, tool, sheet)["prediction"]["connections"], pred["connections"], removed)
        meta = {"tool": tool, "sheet": sheet, "run": run_label, "reading": READING, "symbol_source": SYMBOL_LABEL,
                "model_requested": MODELS[tool], "models_reported": sorted({str(c["model"]) for c in calls}),
                "prompt_file": "extraction/recheck_prompt.md", "prompt_sha256": sha(base_prompt.encode()),
                "image_sha256": sha((DATA / f"{sheet}.png").read_bytes()),
                "threshold": THRESHOLD, "batch": BATCH, "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "seconds": round(time.time() - t0, 1), "calls": len(calls),
                "calls_failed": sum(1 for c in calls if not c["answers"]),
                "cost_usd_notional": round(sum(c["cost_usd_notional"] or 0 for c in calls), 4)
                if any(c["cost_usd_notional"] is not None for c in calls) else None,
                "tokens": sum(((c["usage"] or {}).get("total_tokens") or 0) for c in calls) or None,
                "n_symbols": len(symbols), "n_flagged": len(flags), "n_answered": len(answers),
                "n_changed": sum(1 for r in records if r["applied"])}
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(dict(meta, calls=calls), indent=1), encoding="utf-8")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        public_calls = [{k: c[k] for k in ("ids", "seconds", "model", "error", "parse_error")} for c in calls]
        out_path.write_text(json.dumps(dict(meta, call_summary=public_calls, changes=records, link_changes=links,
                                            prediction=pred),
                                       indent=1), encoding="utf-8")
        print(f"{tool} sheet {sheet}: {len(flags)} flagged of {len(symbols)}, {len(answers)} answered, "
              f"{meta['n_changed']} changed, {meta['calls_failed']} failed calls, {meta['seconds']}s, "
              f"models {meta['models_reported']}")


# ---------------------------------------------------------------- report

def score_set(preds):
    """Micro-averaged over the sheets, as scripts/scorecard.py does."""
    acc = {"loc": [0, 0, 0], "cls": [0, 0, 0], "conn": [0, 0, 0], "corr": 0, "items": 0}
    for sheet, pred in preds.items():
        s = sc.score(DATA / f"{sheet}.graphml", pred, DATA / f"{sheet}.png")
        for k, part in (("loc", s["rough"]["located"]), ("cls", s["rough"]["classified"]), ("conn", s["connections"])):
            acc[k] = [acc[k][0] + part["tp"], acc[k][1] + part["predicted"], acc[k][2] + part["in_key"]]
        acc["corr"] += s["review_load"]["corrections"]
        acc["items"] += s["review_load"]["key_items"]
    return {"review_load": round(100 * acc["corr"] / acc["items"], 2),
            "symbol_f1_rough": sc.prf(*acc["loc"])["f1"], "symbol_class_f1_rough": sc.prf(*acc["cls"])["f1"],
            "connection_f1": sc.prf(*acc["conn"])["f1"], "corrections": acc["corr"], "key_items": acc["items"]}


def oracle_recheck(sheet, symbols, flags):
    """Diagnostic ceiling on development only: what a perfect re-check of exactly the flagged items could reach.
    Each flagged symbol is kept, relabelled to the key's class or removed by the scorer's own rough match. Reads the
    answer key, so it is never a method and never runs outside sheets 0-5."""
    check_sheets([sheet])
    w, h = sc.png_size(DATA / f"{sheet}.png")
    nodes, _ = sc.load_key(DATA / f"{sheet}.graphml", w, h)
    keys = {k: v for k, v in nodes.items() if v["class"] in sc.SCORED}
    valid = [{"id": str(x["id"]), "class": x.get("class"), "box": x["box"]} for x in symbols
             if x["box"] and x.get("class") in sc.SCORED and x.get("id") is not None]
    hit = sc.match(valid, keys, False, sc.THRESHOLDS["rough"])
    out = []
    for x in symbols:
        sid = str(x["id"])
        y = {k: v for k, v in x.items() if k != "box" or "bbox" not in x}
        if sid in flags:
            if sid not in hit:
                continue
            y = dict(y, **{"class": keys[hit[sid]]["class"]})
        out.append(y)
    return {"symbols": out, "connections": retrace(sheet, out)}


def controls():
    import test_scorer_controls as tsc
    rot = {c: sc.SCORED[(i + 1) % len(sc.SCORED)] for i, c in enumerate(sc.SCORED)}
    sets = {"perfect": {}, "wrong_class": {}, "shifted": {}, "empty": {}}
    for sheet in DEV_SHEETS:
        p = tsc.perfect_prediction(DATA / f"{sheet}.graphml", DATA / f"{sheet}.png")
        sets["perfect"][sheet] = p
        sets["wrong_class"][sheet] = {"symbols": [dict(s, **{"class": rot[s["class"]]}) for s in p["symbols"]],
                                      "connections": []}
        sets["shifted"][sheet] = {"symbols": [dict(s, box=tsc.shift(s["box"])) for s in p["symbols"]],
                                  "connections": []}
        sets["empty"][sheet] = {"symbols": [], "connections": []}
    return {k: score_set(v) for k, v in sets.items()}


def report():
    rows, detail = {}, {}
    for tool in MODELS:
        base = {s: load_pred(READING, tool, s)["prediction"] for s in DEV_SHEETS}
        rep = {}
        for s in DEV_SHEETS:
            syms = symbols_with_box(load_pred(REPEAT_LABEL, tool, s)["prediction"])
            rep[s] = {"symbols": [{k: v for k, v in x.items() if k != "box" or "bbox" not in x} for x in syms],
                      "connections": []}
            rep[s]["connections"] = retrace(s, rep[s]["symbols"])
        rej = {}
        for s in DEV_SHEETS:
            syms = symbols_with_box(load_pred(SYMBOL_LABEL, tool, s)["prediction"])
            fl = flagged(tool, s)
            kept = [{k: v for k, v in x.items() if k != "box" or "bbox" not in x} for x in syms
                    if str(x["id"]) not in fl]
            rej[s] = {"symbols": kept, "connections": retrace(s, kept)}
        orc = {}
        for s in DEV_SHEETS:
            syms = symbols_with_box(load_pred(SYMBOL_LABEL, tool, s)["prediction"])
            orc[s] = oracle_recheck(s, syms, flagged(tool, s))
        rows[tool] = {"saved reading = accept every flagged item": score_set(base),
                      "repeat reading (reader run spread)": score_set(rep),
                      "reject every flagged item": score_set(rej),
                      "oracle re-check (reads the key; ceiling, not a method)": score_set(orc)}
        runs = sorted(p.name for p in OUT.iterdir() if p.is_dir() and (p / tool).is_dir()) if OUT.exists() else []
        for r in runs:
            files = {s: json.loads((OUT / r / tool / f"{s}.json").read_text(encoding="utf-8")) for s in DEV_SHEETS
                     if (OUT / r / tool / f"{s}.json").exists()}
            if len(files) != len(DEV_SHEETS):
                continue
            rows[tool][f"re-check {r}"] = score_set({s: f["prediction"] for s, f in files.items()})
            ch = [c for f in files.values() for c in f["changes"]]
            lc = [link_changes(load_pred(READING, tool, s)["prediction"]["connections"], f["prediction"]["connections"],
                               [c["id"] for c in f["changes"] if c["applied"] and not c["after"]["kept"]])
                  for s, f in files.items()]
            per = lambda pred: sum(1 for c in ch if pred(c))  # noqa: E731
            detail[f"{tool} {r}"] = {
                "flagged": len(ch), "answered": per(lambda c: c["verdict"] is not None),
                "confirm": per(lambda c: c["verdict"] == "confirm"),
                "correct_applied": per(lambda c: c["verdict"] == "correct" and c["applied"]),
                "reject_applied": per(lambda c: c["verdict"] == "reject" and c["applied"]),
                "duplicate_applied": per(lambda c: c["verdict"] == "duplicate" and c["applied"]),
                "not_applied_low_conf": per(lambda c: "below" in c["note"]),
                "links_dropped_with_symbols": sum(len(x["dropped_with_removed_symbols"]) for x in lc),
                "links_added_by_retrace": sum(len(x["added"]) for x in lc),
                "links_lost_otherwise": sum(len(x["lost_otherwise"]) for x in lc),
                "calls": sum(f["calls"] for f in files.values()),
                "calls_failed": sum(f["calls_failed"] for f in files.values()),
                "seconds": round(sum(f["seconds"] for f in files.values()), 1),
                "cost_usd_notional": round(sum(f["cost_usd_notional"] or 0 for f in files.values()), 2),
                "tokens": sum(f["tokens"] or 0 for f in files.values()),
                "models_reported": sorted({m for f in files.values() for m in f["models_reported"]})}
    ctl = controls()
    res = {"rows": rows, "detail": detail, "controls": ctl, "threshold": THRESHOLD, "batch": BATCH,
           "prompt_sha256": sha(PROMPT_FILE.read_text(encoding="utf-8").encode())}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    fmt = lambda m: (f'| {m["review_load"]:.2f} | {m["symbol_f1_rough"]:.3f} | {m["symbol_class_f1_rough"]:.3f} | '  # noqa: E731
                     f'{m["connection_f1"]:.3f} |')
    lines = ["# A412: model re-check of flagged symbols, OPEN100 development sheets 0-5", "",
             "Generated by `python scripts/recheck_flagged.py report`. Micro-averaged over sheets 0-5 with the frozen "
             "scorer (`scripts/score_pid2graph.py`). Review load is corrections per 100 key items (lower is better).",
             "", "| Reader | Condition | Review load | Symbol F1 (rough) | Symbol + class F1 (rough) | Connection F1 |",
             "|---|---|---|---|---|---|"]
    for tool, conds in rows.items():
        for name, m in conds.items():
            lines.append(f"| {tool} ({MODELS[tool]}) | {name} " + fmt(m))
    for name, m in ctl.items():
        lines.append(f"| control | {name} " + fmt(m))
    lines += ["", "## What each re-check run did", "",
              "| Run | Flagged | Answered | Confirmed | Class corrected | Rejected | Duplicate removed | Not applied (low confidence) | Links dropped with removed symbols / added by re-trace / lost otherwise | Calls (failed) | Seconds | Notional cost | Tokens | Models |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, d in detail.items():
        lines.append(f'| {k} | {d["flagged"]} | {d["answered"]} | {d["confirm"]} | {d["correct_applied"]} | '
                     f'{d["reject_applied"]} | {d["duplicate_applied"]} | {d["not_applied_low_conf"]} | '
                     f'{d["links_dropped_with_symbols"]} / {d["links_added_by_retrace"]} / {d["links_lost_otherwise"]} | '
                     f'{d["calls"]} ({d["calls_failed"]}) | {d["seconds"]} | ${d["cost_usd_notional"]:.2f} | '
                     f'{d["tokens"] or "n/a"} | {", ".join(d["models_reported"])} |')
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tool", choices=sorted(MODELS), required=True)
    r.add_argument("--run", required=True, help="run label, e.g. r1")
    r.add_argument("--sheets", default=",".join(DEV_SHEETS))
    r.add_argument("--workers", type=int, default=4)
    sub.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.tool, a.run, [s.strip() for s in a.sheets.split(",") if s.strip()], a.workers)
    else:
        report()


if __name__ == "__main__":
    main()
