"""Fixed-source case runner: the industrial-yeast batches through scripts/batch_analysis.py, scored offline.

    python scripts/industrial_yeast_case.py --split development --out NEW_DIR [--external DIR]
    python scripts/industrial_yeast_case.py --split development --check   # re-run; compare with the committed results

The scored numbers come from the product tool (scripts/batch_analysis.py, run as its CLI). This runner only does
what a user does before running it: verify the pinned originals, select the split's batches (data/corpus_depth.json,
decided 2026-11-12 before any result), copy the hourly sugar feed into the tool's CSV contract and author the plans.
It never gives the tool the logged cumulative (total_fermentable_sugar_kg): that column becomes the key, in a
separate file, and scripts/score_batch_totals.py compares the tool's report with it. Rules, controls and the
decision rule are fixed in that scorer's docstring.

Source: Zhao et al., An industrial baker's-yeast fed-batch fermentation dataset of 59 production batches, figshare
10.6084/m9.figshare.33201579, CC BY 4.0. The originals stay in data/external/industrial-yeast (fetch-by-hash:
python scripts/fetch_corpus.py industrial-yeast); only derived plans, keys, tool reports and scores are written.
The tool's input CSV is written to a temporary folder and only its hash is kept. Stdlib only; no network.
"""
import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import score_batch_totals as scorer  # noqa: E402

SOURCE = "industrial-yeast"
EXTERNAL = ROOT / "data" / "external" / SOURCE
RESULTS = ROOT / "examples" / "batch-analysis" / "industrial-yeast" / "results"
TOOL = ROOT / "scripts" / "batch_analysis.py"
SERIES, META = "fermentation_timeseries.csv", "batch_metadata.csv"
FEED, KEY_COLUMN = "sugar_feed_rate_kg_rs_h", "total_fermentable_sugar_kg"
SPLITS = {"development": "development", "held-out": "held_out"}
HOUR = 3600
# Tool runs scored: the frozen method and three deliberately wrong declarations (controls natural to the task).
# (interpolation, declared unit, hour-0 blank feed written as 0). The README says the hour-0 feed is blank because
# feed had not started; writing it as 0 is the adaptation that lets the trapezoid cover the whole batch.
VARIANTS = {"method": ("next", "kg/h", False), "trapezoid": ("linear", "kg/h", False),
            "trapezoid_zero_start": ("linear", "kg/h", True), "previous_hold": ("previous", "kg/h", False),
            "wrong_unit": ("next", "kg/s", False)}
VARIANT_LABELS = {"method": "Method: interval-ending hold (`next`), kg/h",
                  "trapezoid": "Control: trapezoid (`linear`, the tool's V1 rule)",
                  "trapezoid_zero_start": "Control: trapezoid, blank hour-0 feed written as 0",
                  "previous_hold": "Control: previous-value hold (`previous`)",
                  "wrong_unit": "Control: unit declared kg/s instead of kg/h",
                  "perfect": "Control: perfect (the key itself)", "empty": "Control: empty answer",
                  "shuffled": "Control: shuffled (next batch's values)",
                  "recipe_constant": "Control: recipe constant (22,700 kg per batch, README)"}
CONTEXT = {"site_id": "industrial baker's-yeast plant (publisher does not name it)",
           "asset_id": "fed-batch fermenter, about 150 m3 geometric (publisher README)",
           "model_revision": "not supplied", "recipe_id": "not supplied (strain 167, publisher README)",
           "recipe_revision": "not supplied"}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def lf_sha256(path):
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def pinned(external):
    """Read the two originals the case uses, after checking their pinned bytes and sha256."""
    pins = json.loads((ROOT / "data" / "corpus_pins.json").read_text(encoding="utf-8"))[SOURCE]
    out = {}
    for name in (SERIES, META):
        raw = (Path(external) / name).read_bytes()
        if len(raw) != pins[name]["bytes"] or sha256(raw) != pins[name]["sha256"]:
            raise ValueError(f"{name}: bytes differ from data/corpus_pins.json; refusing")
        out[name] = raw
    return out


def split_batches(split):
    plan = json.loads((ROOT / "data" / "corpus_depth.json").read_text(encoding="utf-8"))["groups"][SOURCE]["plan"]
    return list(plan["split"][SPLITS[split]])


def selected_rows(raw, batches):
    """Rows of the selected batches only, in file order; no other batch's values are kept."""
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    rows = {b: [] for b in batches}
    for row in reader:
        if row["batch_id"] in rows:
            rows[row["batch_id"]].append({k: row[k] for k in ("batch_id", "time_h", FEED, KEY_COLUMN)})
    for b, r in rows.items():
        if len(r) < 2:
            raise ValueError(f"{b}: fewer than two hourly rows")
    return rows


def check_metadata(raw, batches):
    meta = {r["batch_id"]: r for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            if r["batch_id"] in batches}
    for b in batches:
        if meta.get(b, {}).get("data_completeness") != "full_process":
            raise ValueError(f"{b}: not a full_process batch in {META}")
    return {b: {"time_start_h": meta[b]["time_start_h"], "time_end_h": meta[b]["time_end_h"],
                "n_records": meta[b]["n_records"]} for b in batches}


def seconds(time_h, label):
    value = Decimal(time_h) * HOUR
    if value != value.to_integral_value() or value < 0:
        raise ValueError(f"{label}: time_h {time_h!r} is not a whole nonnegative second")
    return int(value)


def number(text):
    value = Decimal(text)
    return int(value) if value == value.to_integral_value() else float(value)


def tool_csv(rows, zero_start=False):
    """The tool's CSV contract: batch_id, time_s and the feed column copied as text. The key column is not written.
    zero_start (a control only): a blank feed in a batch's first row is written as 0."""
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["batch_id", "time_s", FEED])
    for b, rs in rows.items():
        for r in rs:
            value = "0" if zero_start and r is rs[0] and not r[FEED].strip() else r[FEED]
            w.writerow([b, seconds(r["time_h"], b), value])
    return buf.getvalue().encode("utf-8")


def windows(rows, level):
    out = []
    for b, rs in rows.items():
        times = [seconds(r["time_h"], b) for r in rs]
        if level == "batch":
            out.append({"id": b, "batch_id": b, "phase": "whole logged batch", "start_s": times[0], "end_s": times[-1],
                        "row_index": (0, len(rs) - 1)})
        else:
            for k in range(1, len(rs)):
                out.append({"id": f"{b}-h{k:02d}", "batch_id": b, "phase": f"logged hour {k}",
                            "start_s": times[k - 1], "end_s": times[k], "row_index": (k - 1, k)})
    return out


def plan(rows, level, interpolation, unit):
    return {"schema": "batch-analysis-2", "context": CONTEXT, "max_gap_s": HOUR,
            "signals": {FEED: {"unit": unit, "asset_id": "sugar feed (publisher log)",
                               "source_ref": "figshare 10.6084/m9.figshare.33201579 fermentation_timeseries.csv "
                                             "sugar_feed_rate_kg_rs_h; logged hourly by operators, kg RS/h",
                               "interpolation": interpolation, "quality": None}},
            "windows": [{"id": w["id"], "batch_id": w["batch_id"], "phase": w["phase"], "start_s": w["start_s"],
                         "end_s": w["end_s"], "source_ref": "publisher hourly log rows (time_h)"}
                        for w in windows(rows, level)]}


def key(rows, level, split):
    """The logged-cumulative key; read only here, never given to the tool."""
    items = []
    for w in windows(rows, level):
        a, b = (rows[w["batch_id"]][i][KEY_COLUMN] for i in w["row_index"])
        if not a.strip() or not b.strip():
            raise ValueError(f"{w['id']}: logged cumulative blank; no key for this window")
        items.append({"id": w["id"], "batch_id": w["batch_id"], "start_s": w["start_s"], "end_s": w["end_s"],
                      "logged_delta_kg": number(str(Decimal(b) - Decimal(a)))})
    return {"schema": scorer.KEY_SCHEMA, "source": f"figshare 10.6084/m9.figshare.33201579 {SERIES} {KEY_COLUMN}",
            "split": split, "level": level, "signal": FEED, "unit": "kg", "tolerance_kg": scorer.TOLERANCE_KG,
            "items": items}


def logged_sum(rows, level):
    """Diagnostic: the Decimal sum of the logged feed under the interval-ending reading, from the tool's input
    column only. Equal to the key where the publisher's cumulative is internally consistent."""
    out = {}
    for w in windows(rows, level):
        rs = rows[w["batch_id"]]
        lo, hi = w["row_index"]
        cells = [rs[i][FEED] for i in range(lo + 1, hi + 1)]
        out[w["id"]] = None if any(not c.strip() for c in cells) else number(str(sum(Decimal(c) for c in cells)))
    return out


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def run(split, out, external=EXTERNAL):
    out = Path(out)
    if out.exists():
        raise ValueError(f"{out} exists; choose a new output directory")
    raws = pinned(external)
    batches = split_batches(split)
    meta = check_metadata(raws[META], batches)
    rows = selected_rows(raws[SERIES], batches)
    csv_raw, zero_raw = tool_csv(rows), tool_csv(rows, zero_start=True)
    if KEY_COLUMN.encode() in csv_raw or KEY_COLUMN.encode() in zero_raw:
        raise ValueError("key column leaked into the tool input")
    receipt = {"source": SOURCE, "split": split, "batches": batches, "metadata": meta,
               "originals": {n: {"bytes": len(r), "sha256": sha256(r)} for n, r in raws.items()},
               "tool_input_csv": {"sha256": sha256(csv_raw), "zero_start_control_sha256": sha256(zero_raw),
                                  "columns": ["batch_id", "time_s", FEED],
                                  "rows": sum(len(r) for r in rows.values()), "withheld": KEY_COLUMN,
                                  "kept": "temporary folder only; rebuilt from the pinned original"},
               "code_sha256_lf": {p: lf_sha256(ROOT / p) for p in
                                  ("scripts/batch_analysis.py", "scripts/score_batch_totals.py",
                                   "scripts/industrial_yeast_case.py")},
               "runs": {}}
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "batch.csv").write_bytes(csv_raw)
        (tmp / "batch.zero-start.csv").write_bytes(zero_raw)
        for level in scorer.LEVELS:
            k = key(rows, level, split)
            dump(out / "key" / f"key.{level}.json", k)
            results[level] = {"tool": {}, "controls": scorer.controls(k), "logged_sum_vs_key": {}}
            sums = logged_sum(rows, level)
            results[level]["logged_sum_vs_key"] = {
                "items": len(k["items"]),
                "consistent": sum(sums[i["id"]] is not None and abs(sums[i["id"]] - i["logged_delta_kg"])
                                  <= scorer.TOLERANCE_KG for i in k["items"]),
                "inconsistent": [{"id": i["id"], "logged_feed_sum_kg": sums[i["id"]], "key_kg": i["logged_delta_kg"]}
                                 for i in k["items"] if sums[i["id"]] is None
                                 or abs(sums[i["id"]] - i["logged_delta_kg"]) > scorer.TOLERANCE_KG]}
            for name, (interp, unit, zero) in VARIANTS.items():
                source = tmp / ("batch.zero-start.csv" if zero else "batch.csv")
                p = plan(rows, level, interp, unit)
                plan_path = out / "plans" / f"{name}.{level}.plan.json"
                dump(plan_path, p)
                scorer.check_input(k, p)
                report_dir = out / "reports" / f"{name}.{level}"
                argv = [sys.executable, "-B", str(TOOL), "--csv", str(source), "--plan", str(plan_path),
                        "--out", str(report_dir)]
                done = subprocess.run(argv, capture_output=True, text=True, timeout=120)
                if done.returncode != 0:
                    raise ValueError(f"{name}.{level}: batch_analysis.py exit {done.returncode}: {done.stderr.strip()}")
                report = json.loads((report_dir / "batch_analysis.json").read_text(encoding="utf-8"))
                if report["inputs"]["csv_sha256"] != sha256(source.read_bytes()):
                    raise ValueError("the report was not made from this input")
                results[level]["tool"][name] = scorer.score(k, report)
                receipt["runs"][f"{name}.{level}"] = {
                    "command": f"python -B scripts/batch_analysis.py --csv <temporary {source.name}> --plan "
                               f"plans/{name}.{level}.plan.json --out reports/{name}.{level}",
                    "interpolation": interp, "unit": unit, "hour0_blank_written_as_zero": zero}
    summary = {"split": split, "batches": batches, "levels": results}
    if split == "held-out":
        kept, why = scorer.decide({lvl: {"method": results[lvl]["tool"]["method"],
                                         "controls": {**{n: s for n, s in results[lvl]["tool"].items() if n != "method"},
                                                      **results[lvl]["controls"]}} for lvl in scorer.LEVELS})
        summary["decision"] = {"kept": kept, "reasons": why}
    dump(out / "score.json", summary)
    dump(out / "RECEIPT.json", receipt)
    (out / "SCORE.md").write_text(markdown(summary), encoding="utf-8", newline="\n")
    return summary


def fmt(v, digits=1):
    return "unknown" if v is None else f"{v:,.{digits}f}"


def markdown(summary):
    lines = [f"# industrial-yeast, {summary['split']} batches {', '.join(summary['batches'])}", "",
             "Generated by `scripts/industrial_yeast_case.py`; scored by `scripts/score_batch_totals.py` (rules in its "
             "docstring). The method and the tool-run controls are reports written by `scripts/batch_analysis.py`; "
             "the other controls are built by the scorer. Matched = within 0.5 kg of the logged cumulative's change.",
             ""]
    for level in scorer.LEVELS:
        r = summary["levels"][level]
        lines += [f"## {'Whole-batch totals' if level == 'batch' else 'Hourly increments'}", "",
                  "| Answer | Matched / items | Answered | Mean abs error, kg | Max abs error, kg |", "|---|---|---|---|---|"]
        for name, s in list(r["tool"].items()) + list(r["controls"].items()):
            lines.append(f"| {VARIANT_LABELS[name]} | {s['matched']} / {s['items']} ({s['match_rate']:.3f}) | "
                         f"{s['answered']} | {fmt(s['mean_abs_error_kg'])} | {fmt(s['max_abs_error_kg'])} |")
        c = r["logged_sum_vs_key"]
        lines += ["", f"Source check (not a score): the logged feed summed by hour equals the logged cumulative's change "
                      f"on {c['consistent']} of {c['items']} items" +
                  ("." if not c["inconsistent"] else "; differing: " + ", ".join(
                      f"{x['id']} feed sum {fmt(x['logged_feed_sum_kg'])} vs {fmt(x['key_kg'])}" for x in c["inconsistent"]) + "."), ""]
    if "decision" in summary:
        d = summary["decision"]
        lines += ["## Decision (rule fixed before the run)", "",
                  "**kept**" if d["kept"] else "**not kept**: " + "; ".join(d["reasons"]), ""]
    return "\n".join(lines)


def check(split, external=EXTERNAL):
    committed = RESULTS / split
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "run"
        run(split, fresh, external)
        names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file())
        have = sorted(p.relative_to(committed).as_posix() for p in committed.rglob("*") if p.is_file())
        changed = [n for n in names if n not in have or
                   (fresh / n).read_bytes() != (committed / n).read_bytes().replace(b"\r\n", b"\n")]
        extra = [n for n in have if n not in names]
        return changed + [f"{n} (not produced)" for n in extra]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--split", required=True, choices=sorted(SPLITS))
    ap.add_argument("--external", type=Path, default=EXTERNAL)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", type=Path, help="new results directory")
    mode.add_argument("--check", action="store_true", help="re-run and compare with the committed results")
    a = ap.parse_args(argv)
    try:
        if a.check:
            bad = check(a.split, a.external)
            if bad:
                print("differs from committed results: " + ", ".join(bad), file=sys.stderr)
                return 1
            print(f"{a.split}: re-run matches {RESULTS.relative_to(ROOT).as_posix()}/{a.split}")
            return 0
        s = run(a.split, a.out, a.external)
    except (OSError, ValueError, KeyError) as exc:
        print(f"industrial-yeast case refused: {exc}", file=sys.stderr)
        return 2
    for level in scorer.LEVELS:
        m = s["levels"][level]["tool"]["method"]
        print(f"{a.split} {level}: {m['matched']}/{m['items']} matched")
    if "decision" in s:
        print("decision:", "kept" if s["decision"]["kept"] else "not kept", s["decision"]["reasons"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
