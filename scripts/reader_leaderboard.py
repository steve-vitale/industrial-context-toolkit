"""Generate benchmarks/LEADERBOARD.md: every drawing reader registered in benchmarks/registry.json, per source family
and split, beside the known-answer controls scored on the same keys.

    python scripts/reader_leaderboard.py           # write benchmarks/LEADERBOARD.md
    python scripts/reader_leaderboard.py --check   # exit 1 if the page is missing or differs from a fresh render

A reader is a model or method with its recipe (prompt, tiling, tracer) and interface; each registered group is one
row. Inputs are only the registered reports (benchmarks/results/*.json), their suites and the committed predictions
they reference. Symbol and connection F1 come from the reports. Review load is recomputed per replicate from the same
committed predictions with the frozen scorer (scripts/evaluate_vendor.py, so it matches that kit's numbers), and the
rescoring must reproduce the report's own F1 counts, or the script stops. Controls are the vendor-evaluation kit's
(perfect, every class wrong, every box moved half a sheet, empty) on the drawing tasks and the task's own reference
and empty answers on tag reading.

Claim levels come from each case's declared split: development (seen while the method was built or tuned),
validation (used to choose between methods) and held-out (sealed until a frozen method is scored once). Rows are
ranked only inside one comparison cohort of a validation or held-out table; development tables are never ranked.
Only tasks that score a drawing reader are listed (drawing-extraction, tag-reading); other registered tasks are
named with the reason they are not on the board. Stdlib only, offline, deterministic (no clock).
"""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_vendor as ev  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "benchmarks" / "registry.json"
OUT = ROOT / "benchmarks" / "LEADERBOARD.md"
READER_TASKS = ("drawing-extraction", "tag-reading")
LEVELS = {"development": "development", "validation": "validation", "held-out": "held-out", "holdout": "held-out",
          "test": "held-out"}
LEVEL_ORDER = ("held-out", "validation", "development")
LEVEL_TEXT = {
    "held-out": "Sealed until a frozen method was scored once. The only level that supports a generalization claim, "
                "and then only for the family it covers.",
    "validation": "Used to choose between methods, so a rank here is optimistic: the winner was picked on these "
                  "sheets. Ranked inside one cohort only.",
    "development": "Seen while the method was built or tuned. Shows that a reader runs and where it fails; not "
                   "ranked and not a claim about unseen drawings.",
}
TEXT_EXT = {".json", ".md", ".txt", ".csv", ".graphml", ".py", ".xml", ".svg"}
F1_TOLERANCE = 1e-9


class LeaderboardError(ValueError):
    pass


def rel(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def file_sha(path):
    raw = Path(path).read_bytes()
    return hashlib.sha256(raw.replace(b"\r\n", b"\n") if Path(path).suffix.lower() in TEXT_EXT else raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def level_of(split):
    level = LEVELS.get(str(split).lower())
    if level is None:
        raise LeaderboardError(f"unknown split {split!r}: declare development, validation or held-out")
    return level


def stats(values):
    vals = [v for v in values if v is not None and v == v]
    if not vals:
        return None
    return {"mean": statistics.fmean(vals), "min": min(vals), "max": max(vals), "n": len(vals), "values": vals,
            "sd": statistics.stdev(vals) if len(vals) > 1 else None}


def fmt(s, digits, unit=""):
    if s is None:
        return "n/a"
    m = f"{s['mean']:.{digits}f}{unit}"
    if s["n"] == 1:
        return f"{m} (single run)"
    if s["sd"] == 0:
        return f"{m} (same in all {s['n']})"
    return f"{m} ± {s['sd']:.{digits}f} ({s['min']:.{digits}f}–{s['max']:.{digits}f})"


def reader_name(group):
    model = group["model"]
    return f"{model['id']} ({model['provider']}) · {group['method']} · {group['interface']}"


def run_dates(results):
    dates = sorted({(row.get("recorded_run_at") or r.get("ran_at") or "")[:10] for r in results for row in r["rows"]}
                   - {""})
    if not dates:
        return "not recorded"
    return dates[0] if dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}"


def links(entry):
    report = Path(entry["report"]).name
    suite = (ROOT / entry["suite"]).resolve().relative_to((ROOT / "benchmarks").resolve()).as_posix()
    return f"[report](results/{report}.md), [JSON](results/{report}.json), [suite]({suite})"


# ---------------------------------------------------------------- drawing extraction

def drawing_keys(case):
    key = ROOT / case["files"]["key"]["path"]
    return key.parent, key.stem


def load_answer(row):
    """The committed prediction a report row scored, checked against its recorded hash. None = scored empty."""
    ref = row.get("prediction_ref")
    if row.get("status") != "ok" or not ref:
        return None
    path = ROOT / ref["path"]
    if not path.is_file():
        raise LeaderboardError(f"missing committed prediction {ref['path']}")
    if file_sha(path) != ref["sha256"]:
        raise LeaderboardError(f"{ref['path']} changed since its report was registered")
    pred, status, note = ev.load_prediction(path)
    if status != "ok":
        raise LeaderboardError(f"{ref['path']}: {note}")
    return pred


def drawing_run(result, cases):
    counts = []
    for row in result["rows"]:
        keys_dir, sheet = drawing_keys(cases[row["case"]])
        c, _ = ev.score_sheet(keys_dir, sheet, load_answer(row))
        counts.append(c)
    m = ev.metrics(ev.total(counts))
    registered = result["metrics"]
    for ours, theirs in (("symbol_f1_rough_classified", "symbols_rough"),
                         ("symbol_f1_strict_classified", "symbols_strict"), ("connection_f1", "networks")):
        if abs(m[ours] - registered[theirs]["f1"]) > F1_TOLERANCE:
            raise LeaderboardError(f"run {result['run']}: rescored {theirs} F1 {m[ours]:.6f} differs from the "
                                   f"registered {registered[theirs]['f1']:.6f}")
    return m


def drawing_controls(case_list):
    pooled = {c: [] for c in ev.CONTROL_ORDER}
    for case in case_list:
        keys_dir, sheet = drawing_keys(case)
        for name, pred in ev.controls_for(keys_dir / f"{sheet}.graphml", keys_dir / f"{sheet}.png").items():
            pooled[name].append(ev.score_sheet(keys_dir, sheet, pred)[0])
    return {name: ev.metrics(ev.total(rows)) for name, rows in pooled.items()}


def drawing_tables(entry, report, suite):
    cases = {c["id"]: c for c in suite["cases"]}
    results = {r["run"]: r for r in report["results"]}
    tables = {}
    for group in report["summary"]:
        runs = [results[name] for name in group["runs"]]
        case_ids = sorted({row["case"] for r in runs for row in r["rows"]})
        per_run = [drawing_run(r, cases) for r in runs]
        key = (report["task"], group["family"], level_of(group["split"]), group["split"], group["cohort"])
        table = tables.setdefault(key, {"entry": entry, "case_ids": case_ids, "rows": [],
                                        "controls": drawing_controls([cases[c] for c in case_ids])})
        table["rows"].append({
            "reader": reader_name(group), "runs": len(runs), "cases": len(case_ids),
            "review": stats([m["review_load_per_100"] for m in per_run]),
            "rough": stats([m["symbol_f1_rough_classified"] for m in per_run]),
            "strict": stats([m["symbol_f1_strict_classified"] for m in per_run]),
            "conn": stats([m["connection_f1"] for m in per_run]),
            "tags": "not keyed",
            "dates": run_dates(runs), "evidence": group["evidence"]})
    return tables


# ---------------------------------------------------------------- tag reading

def tag_controls(report, case_ids, kind):
    out = {}
    for name in ("reference", "empty"):
        if kind == "geometry":
            correct = sum(report["controls"][c][name]["strict"]["correct"] for c in case_ids)
            truth = sum(report["controls"][c][name]["strict"]["with_truth"] for c in case_ids)
        else:
            correct = sum(report["controls"][c][name]["all"]["found"] for c in case_ids)
            truth = sum(report["controls"][c][name]["all"]["listed"] for c in case_ids)
        out[name] = correct / truth if truth else None
    return out


def tag_tables(entry, report):
    results = {(r["run"], r["tag_key_kind"]): r for r in report["results"]}  # one run spans both key kinds
    tables = {}
    for group in report["summary"]:
        kind = group["tag_key_kind"]
        runs = [results[(name, kind)] for name in group["runs"]]
        case_ids = sorted({row["case"] for r in runs for row in r["rows"]})
        key = (f"{report['task']} ({kind})", group["family"], level_of(group["split"]), group["split"],
               group["cohort"])
        table = tables.setdefault(key, {"entry": entry, "case_ids": case_ids, "rows": [], "kind": kind,
                                        "controls": tag_controls(report, case_ids, kind)})
        metric = group["metrics"]
        primary, secondary = (("strict_end_to_end_recall", "strict_accuracy_on_found") if kind == "geometry"
                              else ("identifier_recall", "found_identifier_class_agreement"))

        def summ(name):
            s = metric[name]
            if not s.get("defined_replicates") or s.get("mean") is None:
                return None  # no denominator in any replicate: shown as n/a, never as zero
            return {"mean": s["mean"], "min": s["min"], "max": s["max"], "n": s["defined_replicates"],
                    "sd": s["stdev"] if s["defined_replicates"] > 1 else None}
        table["rows"].append({"reader": reader_name(group), "runs": len(runs), "cases": len(case_ids),
                              "primary": summ(primary), "secondary": summ(secondary),
                              "dates": run_dates(runs), "evidence": group["evidence"]})
    return tables


# ---------------------------------------------------------------- render

def ranked(rows, level, sort_key):
    """Validation and held-out rows are ranked by sort_key; development rows keep reader-name order, unranked."""
    if level not in ("validation", "held-out"):
        return [("not ranked", r) for r in sorted(rows, key=lambda r: r["reader"])]
    rows = sorted(rows, key=lambda r: (sort_key(r), r["reader"]))
    return [(str(i), r) for i, r in enumerate(rows, 1)]


def sentence(text):
    return text[:1].upper() + text[1:]


def heading(family, split, level, suffix=""):
    claim = "" if split == level else f" · {level}"
    return f"### {family} · split `{split}`{claim}{suffix}"


def rank_note(level, metric):
    return f"Ranked by mean {metric}." if level in ("validation", "held-out") else "Development: not ranked."


def render_drawing(key, table):
    task, family, level, split, cohort = key
    c = table["controls"]
    lines = [heading(family, split, level), "",
             f"Task `{task}`; {len(table['case_ids'])} cases ({', '.join(table['case_ids'])}); cohort "
             f"`{cohort[:12]}`. Evidence: {links(table['entry'])}. {sentence(table['rows'][0]['evidence'])}. "
             f"{rank_note(level, 'review load')} Tag reading is not keyed for this family.", "",
             "| Rank | Reader (model · method · interface) | Runs × cases | Review load per 100 key items (lower is "
             "better) | Symbol F1 rough | Symbol F1 strict | Connection F1 | Tag reading | Run dates |",
             "|---|---|---|---|---|---|---|---|---|"]
    for rank, r in ranked(table["rows"], level, lambda r: r["review"]["mean"]):
        lines.append(f"| {rank} | {r['reader']} | {r['runs']} × {r['cases']} | {fmt(r['review'], 1)} | "
                     f"{fmt(r['rough'], 3)} | {fmt(r['strict'], 3)} | {fmt(r['conn'], 3)} | {r['tags']} | "
                     f"{r['dates']} |")
    for name in ev.CONTROL_ORDER:
        m = c[name]
        lines.append(f"| control | {ev.CONTROL_LABELS[name]} | — × {len(table['case_ids'])} | "
                     f"{m['review_load_per_100']:.1f} | {m['symbol_f1_rough_classified']:.3f} | "
                     f"{m['symbol_f1_strict_classified']:.3f} | {m['connection_f1']:.3f} | — | — |")
    return lines


def render_tags(key, table):
    task, family, level, split, cohort = key
    geometry = table["kind"] == "geometry"
    head = (("Strict tag recall (labelled symbols)", "Strict accuracy on found symbols") if geometry else
            ("Identifier recall (partial list, lenient substring)", "Class agreement on found identifiers"))
    lines = [heading(family, split, level, f" · `{task}`"), "",
             f"{len(table['case_ids'])} cases ({', '.join(table['case_ids'])}); cohort `{cohort[:12]}`. Evidence: "
             f"{links(table['entry'])}. {sentence(table['rows'][0]['evidence'])}. "
             f"{rank_note(level, head[0].split(' (')[0].lower())} Symbol and connection F1 are not part of this "
             "task.", "",
             f"| Rank | Reader (model · method · interface) | Runs × cases | {head[0]} | {head[1]} | Run dates |",
             "|---|---|---|---|---|---|"]
    for rank, r in ranked(table["rows"], level, lambda r: -r["primary"]["mean"] if r["primary"] else float("inf")):
        lines.append(f"| {rank} | {r['reader']} | {r['runs']} × {r['cases']} | {fmt(r['primary'], 3)} | "
                     f"{fmt(r['secondary'], 3)} | {r['dates']} |")
    for name, label in (("reference", "Control: reference answer (the key itself)"),
                        ("empty", "Control: empty answer")):
        v = table["controls"][name]
        lines.append(f"| control | {label} | — × {len(table['case_ids'])} | "
                     f"{'n/a' if v is None else f'{v:.3f}'} | — | — |")
    return lines


def build(registry_path=REGISTRY):
    registry = read(registry_path)
    sections = {level: [] for level in LEVEL_ORDER}
    skipped = []
    for entry in registry["reports"]:
        report = read(ROOT / f"{entry['report']}.json")
        suite = read(ROOT / entry["suite"])
        if report["task"] not in READER_TASKS:
            skipped.append((entry, report["task"]))
            continue
        if report["task"] == "drawing-extraction":
            for key, table in sorted(drawing_tables(entry, report, suite).items(), key=lambda kv: kv[0]):
                sections[key[2]].append(render_drawing(key, table))
        else:
            for key, table in sorted(tag_tables(entry, report).items(), key=lambda kv: kv[0]):
                sections[key[2]].append(render_tags(key, table))
    return render(sections, skipped)


def render(sections, skipped):
    out = ["# Reader leaderboard", "",
           "Generated by `scripts/reader_leaderboard.py` from [the registry](registry.json); do not edit by hand. "
           "`python scripts/reader_leaderboard.py --check` confirms this page matches the registered results.", "",
           "**Prototype evidence, not a product ranking.** Today's reader drafts: a general model on drawing tiles "
           "plus a code line tracer. Trained models (such as PID2Graph's) and commercial readers very likely read "
           "lines better ([PRIOR_ART.md](../docs/PRIOR_ART.md)); none has been registered here yet. To add one, "
           "follow [PLUG_IN_A_READER.md](../docs/PLUG_IN_A_READER.md).", "",
           "How to read it:", "",
           "- A row is one reader: model identifier (contributor-declared, not provider-attested), method with its "
           "recipe, and interface. Runs × cases counts replicate runs and the sheets each run attempted.",
           "- Uncertainty is mean ± standard deviation (min–max) over replicate runs on the same fixed sheets. It "
           "is run-to-run spread, not a significance test, and says nothing about other drawings.",
           "- Review load counts corrections (false, missed and relabelled symbols, false and missed links) per 100 "
           "key items. It is recomputed from the committed predictions with the frozen scorer; it is not measured "
           "reviewer time.",
           "- A rank orders the means inside one table; it is not a significance test. With a handful of sheets, "
           "sheet-to-sheet variation is far larger than run-to-run spread. For example, the round-5 GPT and Claude "
           "methods on OPEN100 sheets 6-11 differ beyond run noise but tie across drawings under a sheet bootstrap "
           "([EVALUATION.md §4a](../docs/EVALUATION.md#4a-later-rounds-at-a-glance)).",
           "- Every table carries its controls scored on the same keys: a reader that cannot clearly beat the "
           "deliberately wrong answers has not shown anything.",
           "- Only rows inside one table are comparable. Different families, splits, cases or scorer contracts are "
           "different tables, and a number from one is never ranked against another.", ""]
    for level in LEVEL_ORDER:
        out += [f"## {level.capitalize()}", "", f"*{LEVEL_TEXT[level]}*", ""]
        if not sections[level]:
            note = {"held-out": "No reader result is registered on a held-out split yet. Older one-time held-out "
                                "scorecards (round 2, PID2Graph holdout B, `out/scorecard_hb-*.md`) are not "
                                "registered here: their keys are downloaded, not committed, so they cannot be "
                                "re-scored offline. A first sealed held-out result for any reader is the most "
                                "useful next addition.",
                    "validation": "No reader result is registered on a validation split yet.",
                    "development": "No reader result is registered on a development split yet."}[level]
            out += [note, ""]
        for lines in sections[level]:
            out += lines + [""]
    out += ["## Registered results not on this board", ""]
    if skipped:
        for entry, task in skipped:
            out.append(f"- `{task}` ({links(entry)}): scores descriptions, models, claims or maintenance records, not a drawing reader.")
    else:
        out.append("- None.")
    out += ["", "Generated from the registered reports only; adding a reader means registering its run manifests "
            "and report (see [benchmarks/README.md](README.md) and [CONTRIBUTING.md](../CONTRIBUTING.md#submit-model-and-method-results)), "
            "then regenerating this page.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare with the committed page instead of writing it")
    args = ap.parse_args(argv)
    try:
        text = build()
    except (LeaderboardError, OSError, KeyError, ValueError) as e:
        print(f"reader_leaderboard: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if args.check:
        if not OUT.is_file():
            print(f"{rel(OUT)} is missing; run python scripts/reader_leaderboard.py", file=sys.stderr)
            return 1
        if OUT.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
            print(f"{rel(OUT)} is stale: it differs from the registered results; run python scripts/reader_leaderboard.py",
                  file=sys.stderr)
            return 1
        print(f"{rel(OUT)} matches the registered results")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"wrote {rel(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
