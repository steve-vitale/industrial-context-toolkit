"""Summarize recorded batches in supplied phase windows, with units and observed-time coverage.

Offline standard-library tool. See examples/batch-analysis/README.md for the strict CSV/plan contract.
No phase inference, model calls, plant connection, prediction, control or automatic graph mutation.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

from output_paths import protect_outputs

# Unit -> (integrated unit, scale for value * seconds). None: summary only.
UNITS = {u: None for u in ("degC", "pH", "%", "rpm", "bar", "g/L", "kg/L", "kg", "L")}
UNITS.update({"kg/h": ("kg", 1 / 3600), "g/h": ("g", 1 / 3600),
              "kg/s": ("kg", 1), "L/h": ("L", 1 / 3600), "L/s": ("L", 1),
              "kW": ("kWh", 1 / 3600), "W": ("kWh", 1 / 3600000)})


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def fields(obj, required, label):
    if not isinstance(obj, dict) or set(obj) != set(required):
        raise ValueError(f"{label} requires exactly these fields: {', '.join(required)}")


def text(value, label):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label} must be nonempty single-line text")


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON field {key}")
        obj[key] = value
    return obj


def validate_plan(plan):
    fields(plan, ("schema", "context", "max_gap_s", "signals", "windows"), "plan")
    if plan["schema"] not in ("batch-analysis-1", "batch-analysis-2"):
        raise ValueError("plan schema must be batch-analysis-1 or batch-analysis-2")
    explicit = plan["schema"] == "batch-analysis-2"
    fields(plan["context"], ("site_id", "asset_id", "model_revision", "recipe_id", "recipe_revision"), "context")
    for key, value in plan["context"].items():
        text(value, key)
    if number(plan["max_gap_s"], "max_gap_s") <= 0:
        raise ValueError("max_gap_s must be positive")
    if not isinstance(plan["signals"], dict) or not plan["signals"]:
        raise ValueError("signals must be a nonempty object")
    for tag, spec in plan["signals"].items():
        text(tag, "signal name")
        if tag in ("batch_id", "time_s"):
            raise ValueError("signal name conflicts with CSV identity/time columns")
        required = ("unit", "asset_id", "source_ref", "interpolation", "quality") if explicit else ("unit", "asset_id", "source_ref")
        fields(spec, required, f"signal {tag}")
        if not isinstance(spec["unit"], str) or spec["unit"] not in UNITS:
            raise ValueError(f"unsupported unit for {tag}: {spec['unit']!r}")
        for key in ("asset_id", "source_ref"):
            text(spec[key], f"{tag} {key}")
        if explicit:
            if spec["interpolation"] not in ("linear", "previous", "next"):
                raise ValueError(f"{tag} interpolation must be linear, previous or next")
            quality = spec["quality"]
            if quality is not None:
                fields(quality, ("column", "good_values"), f"{tag} quality")
                text(quality["column"], f"{tag} quality column")
                if quality["column"] in ("batch_id", "time_s") or quality["column"] in plan["signals"]:
                    raise ValueError("quality column conflicts with an identity, time or signal column")
                tokens = quality["good_values"]
                if not isinstance(tokens, list) or not tokens:
                    raise ValueError("quality good_values must be a nonempty string list")
                for token in tokens:
                    text(token, "quality token")
                if len(set(tokens)) != len(tokens):
                    raise ValueError("duplicate quality good_values token")
    if not isinstance(plan["windows"], list) or not plan["windows"]:
        raise ValueError("windows must be a nonempty list")
    ids, earlier = set(), {}
    for window in plan["windows"]:
        fields(window, ("id", "batch_id", "phase", "start_s", "end_s", "source_ref"), "window")
        for key in ("id", "batch_id", "phase", "source_ref"):
            text(window[key], key)
        if window["id"] in ids:
            raise ValueError("duplicate window id")
        ids.add(window["id"])
        start = number(window["start_s"], "start_s")
        end = number(window["end_s"], "end_s")
        if start < 0 or end <= start:
            raise ValueError("window requires 0 <= start_s < end_s")
        for a, b in earlier.get(window["batch_id"], []):
            if max(a, start) < min(b, end):
                raise ValueError("overlapping windows in one batch")
        earlier.setdefault(window["batch_id"], []).append((start, end))


def read_csv(raw, plan):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    header = next(reader, [])
    quality_columns = {spec["quality"]["column"] for spec in plan["signals"].values() if spec.get("quality") is not None}
    expected = ["batch_id", "time_s", *plan["signals"], *sorted(quality_columns)]
    if len(set(header)) != len(header) or set(header) != set(expected) or len(header) != len(expected):
        raise ValueError("CSV header must contain batch_id, time_s and exactly the planned signals")
    batches = {}
    for row in reader:
        line = reader.line_num
        if len(row) != len(header):
            raise ValueError(f"CSV record ending at line {line}: wrong cell count")
        cells = dict(zip(header, row))
        batch = cells["batch_id"]
        text(batch, f"CSV batch_id at line {line}")
        try:
            time = float(cells["time_s"])
        except ValueError as exc:
            raise ValueError(f"invalid time_s at line {line}") from exc
        if not math.isfinite(time) or time < 0:
            raise ValueError(f"time_s at line {line} must be finite and nonnegative")
        previous = batches.setdefault(batch, [])
        if previous and time <= previous[-1]["time_s"]:
            raise ValueError(f"time_s must strictly increase within batch {batch}, line {line}")
        values, issues = {}, {}
        for tag, spec in plan["signals"].items():
            reasons = []
            try:
                value = float(cells[tag])
            except ValueError:
                value = None
                reasons.append("non_numeric_value")
            if value is not None and not math.isfinite(value):
                reasons.append("non_finite_value")
            quality = spec.get("quality")
            if quality is not None and cells[quality["column"]] not in quality["good_values"]:
                reasons.append("quality_not_accepted")
            values[tag] = value if not reasons else None
            if reasons:
                issues[tag] = {"record_end_line": line, "raw_value": cells[tag], "reasons": reasons}
                if quality is not None:
                    issues[tag].update(quality_column=quality["column"], quality_value=cells[quality["column"]])
        previous.append({"time_s": time, "line": line, "values": values, "issues": issues})
    if set(batches) != {w["batch_id"] for w in plan["windows"]}:
        raise ValueError("CSV batches must match the planned batches exactly")
    return batches


def summarize(rows, tag, unit, duration, max_gap, interpolation="linear"):
    good = [r["values"][tag] for r in rows if r["values"][tag] is not None]
    intervals, areas = [], []
    for left, right in zip(rows, rows[1:]):
        dt = right["time_s"] - left["time_s"]
        a, b = left["values"][tag], right["values"][tag]
        # "next" is an interval-ending hold (a log whose value is the rate over the interval it closes, such as an
        # hourly total): only the closing sample's value is used, so the opening row supplies its time alone.
        if dt <= max_gap and b is not None and (a is not None or interpolation == "next"):
            intervals.append(dt)
            areas.append((b if interpolation == "next" else a if interpolation == "previous" else a / 2 + b / 2) * dt)
    covered = math.fsum(intervals)
    area = math.fsum(areas) if intervals else None
    # All adjacent intervals must be admitted; the caller separately checks exact boundaries.
    complete = len(rows) >= 2 and len(intervals) == len(rows) - 1
    integration = UNITS[unit]
    observed = area * integration[1] if area is not None and integration else None
    return {"unit": unit, "sample_count": len(rows), "good_samples": len(good),
            "bad_sample_lines": [r["line"] for r in rows if r["values"][tag] is None],
            "sample_min": min(good) if good else None, "sample_max": max(good) if good else None,
            "covered_s": covered, "coverage_fraction": covered / duration,
            "coverage_status": "complete" if complete else "incomplete",
            "time_weighted_mean_observed": area / covered if covered else None,
            "integral_unit": integration[0] if integration else None,
            "observed_integral": observed,
            "full_window_integral": observed if complete else None}


def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest()


def bind_graph(graph_raw, plan):
    """Resolve supplied IDs in an explicitly selected graph; never infer installed signal identity."""
    if graph_raw is None:
        return {"status": "not selected; asset IDs are supplied labels only"}
    import graph_export
    try:
        graph = json.loads(graph_raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise ValueError("graph requires an object with nodes")
        issues = graph_export.problems(graph)
        if issues:
            raise ValueError("; ".join(issues))
        nodes = {n["id"]: n for n in graph["nodes"]}
        refs = [("context", plan["context"]["asset_id"], "equipment")]
        refs += [(tag, spec["asset_id"], "instrument") for tag, spec in plan["signals"].items()]
        matched = []
        for role, identity, kind in refs:
            n = nodes.get(identity)
            if n is None or n["kind"] != kind or n["status"] == "rejected":
                raise ValueError(f"{role}: graph asset {identity!r} must be a non-rejected {kind}")
            matched.append({"role": role, "asset_id": identity, "kind": kind, "status": n["status"]})
        return {"status": "IDs resolved in selected graph; mappings, units and installed identity remain supplied",
                "graph_sha256": fingerprint(graph_raw), "assets": matched,
                "validator_sha256_lf": fingerprint(Path(graph_export.__file__).read_bytes().replace(b"\r\n", b"\n"))}
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("malformed twin-graph-1 input") from exc


def analyze(csv_raw, plan_raw, graph_raw=None):
    plan = json.loads(plan_raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
    validate_plan(plan)
    graph_binding = bind_graph(graph_raw, plan)
    batches = read_csv(csv_raw, plan)
    explicit = plan["schema"] == "batch-analysis-2"
    windows = []
    for window in plan["windows"]:
        duration = window["end_s"] - window["start_s"]
        rows = [r for r in batches[window["batch_id"]]
                if window["start_s"] <= r["time_s"] <= window["end_s"]]
        # Complete coverage also requires both actual phase boundaries.
        signals = {tag: summarize(rows, tag, spec["unit"], duration, plan["max_gap_s"], spec.get("interpolation", "linear"))
                   for tag, spec in plan["signals"].items()}
        if explicit:
            for tag, result in signals.items():
                spec = plan["signals"][tag]
                result.update(interpolation=spec["interpolation"],
                              quality_policy="explicit exact-token filter" if spec["quality"] is not None else "no external quality filter selected; quality not checked",
                              excluded_samples=[r["issues"][tag] for r in rows if tag in r["issues"]])
        for result in signals.values():
            if not rows or rows[0]["time_s"] != window["start_s"] or rows[-1]["time_s"] != window["end_s"]:
                result["coverage_status"] = "incomplete"
                result["full_window_integral"] = None
        windows.append({**window, "duration_s": duration, "signals": signals})
    report = {"schema": "batch-analysis-result-2" if explicit else "batch-analysis-result-1", "context": plan["context"],
              "context_status": "supplied identities and revisions; not verified against installed assets",
              "inputs": {"csv_sha256": fingerprint(csv_raw), "plan_sha256": fingerprint(plan_raw)},
              "method": {"name": "adjacent-sample-trapezoid-v1", "max_gap_s": plan["max_gap_s"],
                         "tool_sha256_lf": fingerprint(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
                         "assumption": "linear between adjacent good observations; no extrapolation or gap filling"},
              "signal_definitions": plan["signals"], "windows": windows,
              "graph_binding": graph_binding,
              "limits": ["Descriptive recorded-data calculation; no diagnosis, prediction or acceptance.",
                         "Sample extrema can miss excursions between observations.",
                         "Observed integrals over incomplete coverage are not full-phase totals.",
                         "Supplied phase labels, units and mappings require engineering review."]}
    # Fail rather than publish infinities caused by extreme but finite inputs.
    json.dumps(report, allow_nan=False)
    if explicit:
        report["method"].update(name="adjacent-sample-selected-interpolation-v1",
                                assumption="per-signal linear or previous-value hold between adjacent admitted observations; both endpoints required; no extrapolation or gap filling")
        report["limits"].append("Accepted numeric samples and complete coverage do not verify source quality or original sensor continuity.")
        if any(spec["interpolation"] == "next" for spec in plan["signals"].values()):
            report["method"]["assumption"] = ("per-signal linear, previous-value or interval-ending (next) hold between "
                                              "adjacent observations; linear and previous need both endpoints good, next "
                                              "needs only the closing sample good (its value covers the interval it ends; "
                                              "the opening row supplies only its time); no extrapolation or gap filling")
            report["limits"].append("An interval-ending hold is right only for a log whose value covers the interval "
                                    "it closes (an hourly total or average); confirm the source's convention.")
    return report


def markdown(report):
    def escape(value):
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace("|", "&#124;")

    explicit = report["schema"] == "batch-analysis-result-2"
    assumption = "each signal's declared interpolation" if explicit else "linear interpolation"
    lines = ["# Recorded batch phase analysis", "", report["context_status"], "",
             escape(report["graph_binding"]["status"]), "",
             "Context: " + ", ".join(f"{k}={escape(v)}" for k, v in report["context"].items()), "",
             f"A complete integral covers the supplied window under {assumption}; it is not a verified plant total.", "",
             f"| Window / batch / phase | Signal | Unit | {'Accepted' if explicit else 'Good'} / all samples | Covered s / phase s | Coverage | Observed mean | Observed integral | Full-window integral | Integral unit |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    def show(value):
        return "unknown" if value is None else f"{value:.9g}"
    for w in report["windows"]:
        for tag, r in w["signals"].items():
            lines.append(f"| {escape(w['id'])} / {escape(w['batch_id'])} / {escape(w['phase'])} | {escape(tag)} | {r['unit']} | "
                         f"{r['good_samples']} / {r['sample_count']} | {show(r['covered_s'])} / {show(w['duration_s'])} | "
                         f"{r['coverage_status']} | {show(r['time_weighted_mean_observed'])} | {show(r['observed_integral'])} | "
                         f"{show(r['full_window_integral'])} | {r['integral_unit'] or 'not integrated'} |")
    lines += ["", "Bad sample locations, source references, exact input hashes and method fingerprint are in the JSON.", ""]
    if explicit:
        lines += ["## Supplied signal semantics", "",
                  "| Signal | Interpolation | Quality policy |", "|---|---|---|"]
        for tag, spec in report["signal_definitions"].items():
            quality = spec["quality"]
            policy = (f"exact tokens {json.dumps(quality['good_values'], ensure_ascii=False)} in {quality['column']}"
                      if quality is not None else "no external quality filter selected; quality not checked")
            lines.append(f"| {escape(tag)} | {spec['interpolation']} | {escape(policy)} |")
        if any(spec["interpolation"] == "next" for spec in report["signal_definitions"].values()):
            lines += ["", "Linear and previous-value hold require both good endpoints. Interval-ending hold (next) uses the "
                          "closing sample's value for the interval it ends and needs only that sample good; the opening row "
                          "supplies its time. This is not an OPC historian aggregate implementation.", ""]
        else:
            lines += ["", "Both good endpoints are required even for previous-value hold; this is not an OPC historian aggregate implementation.", ""]
    lines += [f"- {line}" for line in report["limits"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--graph", type=Path, help="optional selected twin-graph-1; resolve exact equipment/instrument IDs")
    parser.add_argument("--out", required=True, type=Path, help="new report directory; existing report files refuse")
    args = parser.parse_args(argv)
    outputs = [args.out / "batch_analysis.json", args.out / "batch_analysis.md"]
    try:
        protect_outputs(outputs, [args.csv, args.plan, args.graph])
        if any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError("report already exists; choose a new output directory")
        report = analyze(args.csv.read_bytes(), args.plan.read_bytes(), args.graph.read_bytes() if args.graph else None)
        rendered = [json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", markdown(report)]
        args.out.mkdir(parents=True, exist_ok=True)
        for path, content in zip(outputs, rendered):
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except (OSError, ValueError, OverflowError, csv.Error, RecursionError) as exc:
        print(f"batch analysis refused: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {len(report['windows'])} supplied phase windows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
