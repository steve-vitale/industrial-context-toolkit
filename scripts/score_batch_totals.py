"""Frozen scorer: recorded feed totals from scripts/batch_analysis.py against a publisher-logged running cumulative.

Rules (fixed 2026-11-12 for attempt A418, before the first scored run on any industrial-yeast batch; changing them
is a visible commit and a new attempt):

Key. One item per supplied window: the logged cumulative at the window's end minus the logged cumulative at its
start (the publisher's README: "delta TFS equals the sum of hourly sugar feed"). Two levels, each its own key file:
  batch   one window per batch, from its first to its last logged hour (the plan's whole-batch window);
  hourly  one window per logged hour (k-1 to k), so a method that gets the batch total right but puts feed in the
          wrong hour, or an answer that is the same for every batch, is caught.
The key is read from total_fermentable_sugar_kg, a column the tool is never given.

Answer. A batch_analysis.py report (batch-analysis-result-2): for each key item, the window with the same id and
the signal the key names; the answer is its full_window_integral in the key's unit. A window that is missing, has
no complete integral (coverage incomplete) or reports another integral unit is unanswered, never zero.

Match. |answer - key| <= tolerance_kg (0.5 kg, half the 1 kg resolution of the logged column). Reported per level:
matched / key items (the primary rate), answered / key items, and the mean absolute error over answered items.
Precision is matched / answered.

Stated difference, before the first run (the plan's note): the tool's adjacent-sample trapezoid (linear, its V1
method) integrates a ramp between hourly samples, while the logged cumulative adds each hour's logged feed in
full. On an hourly log whose hour-0 feed is blank, the trapezoid cannot cover the first hour (incomplete: no total)
and, over the hours it covers, differs from the logged sum by (first feed + last feed) / 2. If the blank hour-0 feed
is written as 0 (the README says feed had not started), the trapezoid covers the batch and falls short of the logged
sum by exactly half the last hour's feed. Only an interval-ending hold (`next`: each logged rate applies to the hour
it closes) reproduces the logged sum. The scorer does not correct for any of these; it compares what the tool
reports.

Controls, reported in every table (built here from the key and from a published README constant, never from a
tool run): perfect (the key itself), empty (no windows), shuffled (each batch given the next batch's values, in
key order, wrapping), recipe-constant (every batch total 22,700 kg = the README's "about 300 kg at t=0 to about
23,000 kg at harvest"; each hour that total spread evenly over the batch's logged hours). Tool-run controls
(trapezoid; trapezoid with the blank hour-0 feed written as 0; previous-value hold; the unit declared kg/s) are
scored as answers by the case runner (scripts/industrial_yeast_case.py).

Decision rule (fixed with the rules above): the method is kept only if, on the sealed held-out batches, the batch
level matches at least 4 of 5 and the hourly level at least 0.95 of key items, and each level's match rate is above
every control's except perfect. Development results never change the rule.

Stdlib only; no network; reads only the files it is given.
"""
import json
import math
import sys
from pathlib import Path

KEY_SCHEMA = "logged-cumulative-key-1"
LEVELS = ("batch", "hourly")
TOLERANCE_KG = 0.5
RECIPE_START_KG = 300      # README: "running cumulative about 300 kg at t=0"
RECIPE_HARVEST_KG = 23000  # README: "about 23,000 kg at harvest"
CONTROL_ORDER = ("perfect", "empty", "shuffled", "recipe_constant")
KEEP_BATCH_MIN = 4 / 5
KEEP_HOURLY_MIN = 0.95


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def validate_key(key):
    if not isinstance(key, dict) or key.get("schema") != KEY_SCHEMA:
        raise ValueError(f"key schema must be {KEY_SCHEMA}")
    if key.get("level") not in LEVELS:
        raise ValueError("key level must be batch or hourly")
    if key.get("tolerance_kg") != TOLERANCE_KG or key.get("unit") != "kg" or not isinstance(key.get("signal"), str):
        raise ValueError("key needs signal, unit kg and the frozen tolerance")
    items = key.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("key needs items")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "batch_id", "start_s", "end_s", "logged_delta_kg"}:
            raise ValueError("key item needs exactly id, batch_id, start_s, end_s, logged_delta_kg")
        if item["id"] in seen:
            raise ValueError("duplicate key item")
        seen.add(item["id"])
        _finite(item["logged_delta_kg"], "logged_delta_kg")
        if _finite(item["end_s"], "end_s") <= _finite(item["start_s"], "start_s"):
            raise ValueError("key item needs start_s < end_s")
    return key


def check_input(key, plan):
    """The supplied plan's windows must be exactly the key's windows; the key column must not be a plan signal."""
    windows = {w["id"]: (w["batch_id"], w["start_s"], w["end_s"]) for w in plan["windows"]}
    wanted = {i["id"]: (i["batch_id"], i["start_s"], i["end_s"]) for i in key["items"]}
    if windows != wanted:
        raise ValueError("plan windows differ from the key's items")
    if key["signal"] not in plan["signals"]:
        raise ValueError("plan does not carry the key's signal")
    if any("total_fermentable_sugar" in name for name in plan["signals"]):
        raise ValueError("the key column must be withheld from the tool's input")


def answers(key, report):
    """{item id: answered value or None} read from a batch_analysis report (or a report-shaped control)."""
    if report is None:
        return {i["id"]: None for i in key["items"]}
    if not isinstance(report, dict) or not isinstance(report.get("windows"), list):
        raise ValueError("answer must be a batch_analysis report with windows")
    by_id = {}
    for w in report["windows"]:
        if not isinstance(w, dict) or "id" not in w:
            raise ValueError("report window without id")
        if w["id"] in by_id:
            raise ValueError("duplicate report window")
        by_id[w["id"]] = w
    out = {}
    for item in key["items"]:
        w = by_id.get(item["id"])
        signal = (w or {}).get("signals", {}).get(key["signal"]) if w else None
        value = None
        if (signal and w["batch_id"] == item["batch_id"] and w["start_s"] == item["start_s"]
                and w["end_s"] == item["end_s"] and signal.get("integral_unit") == key["unit"]):
            v = signal.get("full_window_integral")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                value = v
        out[item["id"]] = value
    return out


def score(key, report):
    validate_key(key)
    got = answers(key, report)
    rows, errors = [], []
    for item in key["items"]:
        value = got[item["id"]]
        error = None if value is None else value - item["logged_delta_kg"]
        matched = error is not None and abs(error) <= TOLERANCE_KG
        if error is not None:
            errors.append(abs(error))
        rows.append({"id": item["id"], "batch_id": item["batch_id"], "key_kg": item["logged_delta_kg"],
                     "answer_kg": value, "error_kg": error, "matched": matched})
    n = len(rows)
    matched = sum(r["matched"] for r in rows)
    return {"level": key["level"], "items": n, "matched": matched, "answered": len(errors),
            "match_rate": matched / n, "answered_rate": len(errors) / n,
            "precision": matched / len(errors) if errors else None,
            "mean_abs_error_kg": math.fsum(errors) / len(errors) if errors else None,
            "max_abs_error_kg": max(errors) if errors else None, "rows": rows}


def _report(key, values):
    """A report-shaped control answer: one complete window per key item with the given value (None = no window)."""
    windows = []
    for item in key["items"]:
        v = values.get(item["id"])
        if v is None:
            continue
        windows.append({"id": item["id"], "batch_id": item["batch_id"], "start_s": item["start_s"],
                        "end_s": item["end_s"],
                        "signals": {key["signal"]: {"integral_unit": key["unit"], "full_window_integral": v}}})
    return {"schema": "scorer-control", "windows": windows}


def controls(key):
    validate_key(key)
    items = key["items"]
    batches = list(dict.fromkeys(i["batch_id"] for i in items))
    by_batch = {b: [i for i in items if i["batch_id"] == b] for b in batches}
    shuffled = {}
    for n, b in enumerate(batches):
        donor = by_batch[batches[(n + 1) % len(batches)]]
        for k, item in enumerate(by_batch[b]):
            shuffled[item["id"]] = donor[k]["logged_delta_kg"] if k < len(donor) else None
    constant = {}
    for b in batches:
        share = (RECIPE_HARVEST_KG - RECIPE_START_KG) / len(by_batch[b])
        for item in by_batch[b]:
            constant[item["id"]] = share
    answers_by = {"perfect": _report(key, {i["id"]: i["logged_delta_kg"] for i in items}),
                  "empty": {"schema": "scorer-control", "windows": []},
                  "shuffled": _report(key, shuffled),
                  "recipe_constant": _report(key, constant)}
    out = {name: score(key, answers_by[name]) for name in CONTROL_ORDER}
    if out["perfect"]["match_rate"] != 1 or out["empty"]["matched"] != 0 or out["empty"]["answered"] != 0:
        raise ValueError("known-answer control failed: perfect must match every item and empty none")
    return out


def decide(held_out):
    """held_out: {level: {"method": score, "controls": {name: score}}} -> (kept, reasons)."""
    reasons = []
    floors = {"batch": KEEP_BATCH_MIN, "hourly": KEEP_HOURLY_MIN}
    for level in LEVELS:
        m = held_out[level]["method"]["match_rate"]
        if m < floors[level]:
            reasons.append(f"{level} match rate {m:.4f} below {floors[level]:.2f}")
        for name, c in held_out[level]["controls"].items():
            if name != "perfect" and c["match_rate"] >= m:
                reasons.append(f"{level}: control {name} ({c['match_rate']:.4f}) not below the method ({m:.4f})")
    return not reasons, reasons


def benchmark_counts(key, report):
    """For scripts/benchmark.py: counts(tp, predicted, truth) per level, plus row diagnostics."""
    s = score(key, report)
    counts = {"tp": s["matched"], "predicted": s["answered"], "truth": s["items"]}
    return {f"{key['level']}_feed_totals": counts}, {
        "mismatched_or_unanswered": [r for r in s["rows"] if not r["matched"]],
        "mean_abs_error_kg": s["mean_abs_error_kg"]}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--key", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path, help="batch_analysis.json written by scripts/batch_analysis.py")
    a = ap.parse_args(argv)
    try:
        key = validate_key(json.loads(a.key.read_text(encoding="utf-8")))
        result = score(key, json.loads(a.report.read_text(encoding="utf-8")))
        result["controls"] = {k: {f: v[f] for f in ("matched", "answered", "items", "match_rate")}
                              for k, v in controls(key).items()}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"score refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
