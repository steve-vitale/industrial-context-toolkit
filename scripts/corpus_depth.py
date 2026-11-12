"""The corpus depth register: every acquired public-source group and its disposition under docs/DEPTH_GOAL.md.

  python scripts/corpus_depth.py            # print the counts and the UNPLANNED groups
  python scripts/corpus_depth.py --write    # write docs/CORPUS_DEPTH.md
  python scripts/corpus_depth.py --check    # exit 1 if a rule is broken or docs/CORPUS_DEPTH.md is stale
  python scripts/corpus_depth.py --strict   # --check, and also exit 1 while any group is UNPLANNED (the goal's gate)

Nothing here is a second source registry. It reads the existing ones:

- the acquisition registries `data/public_sources_*.json` (one entry per download group; the additive `depth` field
  holds the key availability, a dated plan or a retirement, each with the file it comes from);
- `docs/DEPTH_GOAL.md` for each group's area (its "Areas and the sources already acquired" table);
- `data/corpus.json` and `out/generalization/matrix.json` for what a group actually feeds: a corpus input whose
  `fetch` command or `local_path` names the group, and that input's matrix cells;
- `benchmarks/registry.json` for any registered suite whose files sit under the group's `data/external/` folder;
- `data/features.json` and the matrix rows' tool files (`scripts/corpus_matrix.py`) for the features a row exercises.

The status is derived, never typed: **feeds** needs a scored matrix cell (pass or fail) or a registered benchmark;
**planned** needs a `depth.plan` with a date, the named key, the task and evidence files that exist; **retired**
needs a `depth.retired` reason with evidence; anything else is **UNPLANNED**. Stdlib only, no network.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import corpus_matrix  # noqa: E402  (row names and row tool files only; importing runs nothing)

REGISTRY_GLOB = "data/public_sources_*.json"
GOAL = "docs/DEPTH_GOAL.md"
CORPUS = "data/corpus.json"
MATRIX = "out/generalization/matrix.json"
PINS = "data/corpus_pins.json"
FEATURES = "data/features.json"
BENCHMARKS = "benchmarks/registry.json"
TARGET = ROOT / "docs" / "CORPUS_DEPTH.md"
PREFIX = "../"  # repository-relative paths; CORPUS_DEPTH.md sits in docs/

FEEDS, PLANNED, RETIRED, UNPLANNED = "feeds a scored task", "dated plan with named key", "retired", "UNPLANNED"
STATUS_ORDER = (FEEDS, PLANNED, RETIRED, UNPLANNED)
SCORED = ("pass", "fail")
HAND_SET = ("status", "feeds", "scored", "evaluated")  # derived only; a registry may not assert them
# Key availability vocabulary, in the order the next-to-wire ranking prefers (a key in hand first).
KEY_STATUSES = ("publisher labels retained, unopened", "source structure (candidate)", "unknown",
                "no key in source", "withheld by publisher")

# Which existing matrix rows and features a group's acquisition categories could exercise once an adapter and a key
# exist. A candidate fit by category, not a verified applicability: it ranks what to wire next, nothing more.
# Every category used by a registry must appear here (an empty fit is an explicit "no existing feature").
CATEGORY_FIT = {
    "pid": ([1, 2, 3, 8], ["drawing-to-bundle", "drawing-set-to-bundle", "pid-port-review", "pid-path-review"]),
    "drawings": ([1, 3], ["drawing-to-bundle", "drawing-set-to-bundle"]),
    "electrical": ([], []),
    "scanned-documents": ([], ["document-text"]),
    "documents": ([], ["document-text", "one-map"]),
    "technical-documents": ([], ["document-text"]),
    "document-text": ([], ["document-text"]),
    "equipment-reference": ([], ["document-text"]),
    "context": ([], ["context-register"]),
    "historian": ([6], ["historian-csv"]),
    "process-measurements": ([6], ["historian-csv"]),
    "condition-monitoring": ([6], ["historian-csv"]),
    "historian-mapping": ([], ["review-and-mapping"]),
    "alarm-events": ([], []),
    "energy": ([], ["opportunity-screen", "impact-estimate"]),
    "opportunity-screen": ([], ["opportunity-screen"]),
    "maintenance": ([], ["maintenance-intake", "maintenance-history"]),
    "maintenance-context": ([], ["maintenance-history"]),
    "work-orders": ([], ["maintenance-intake", "maintenance-history"]),
    "parts-transactions": ([], ["maintenance-history"]),
    "labor": ([], ["maintenance-history"]),
    "parts": ([], []),
    "equipment-records": ([], ["photo-to-record", "one-map"]),
    "photo": ([], ["photo-to-record"]),
    "batch": ([], ["batch-analysis"]),
    "laboratory": ([], ["batch-analysis"]),
    "quality": ([], []),
    "manufacturing": ([], []),
    "process-model": ([5], ["description-to-model", "graph-export", "platform-exports"]),
    "flowsheets": ([5], ["description-to-model"]),
    "exchange-model": ([], ["dexpi-xml-to-model"]),
    "controls": ([4], ["loop-audit"]),
    "cad": ([], ["cad-handoff"]),
}

UNRESOLVED_TERMS = re.compile(r"unresolved|not established|conflicts|no open|copyright", re.I)
RECORD_TERMS = re.compile(r"public regulatory|public u\.s\.|public doe|federal|not separately cleared|"
                          r"individual review|local originals only", re.I)


def read_json(rel, root=ROOT):
    return json.loads((root / rel).read_bytes())


def licence_status(text):
    """Licence/terms status from the acquisition record's own licence string."""
    if UNRESOLVED_TERMS.search(text):
        return "terms unresolved"
    if RECORD_TERMS.search(text):
        return "public record, rights retained, local only"
    return "open licence stated"


def load_groups(root=ROOT):
    """Every acquisition group: id -> (registry path, record). Duplicates across registries are problems."""
    groups, problems = {}, []
    for path in sorted(root.glob(REGISTRY_GLOB)):
        rel = path.relative_to(root).as_posix()
        for sid, record in json.loads(path.read_bytes())["sources"].items():
            if sid in groups:
                problems.append(f"{sid}: in both {groups[sid][0]} and {rel}")
            groups[sid] = (rel, record)
    return groups, problems


def goal_areas(groups, root=ROOT):
    """docs/DEPTH_GOAL.md area table -> ({group: area}, {area: candidate key}, problems)."""
    text = (root / GOAL).read_text(encoding="utf-8")
    areas, keys, problems = {}, {}, []
    rows = re.findall(r"^\| (?!Area |---)([^|]+?) \| ([^|]+?) \| ([^|]+?) \|$", text, re.M)
    if not rows:
        return areas, keys, [f"{GOAL}: no area table found"]
    by_registry = {}
    for sid, (rel, _) in groups.items():
        by_registry.setdefault(rel, []).append(sid)
    for area, cell, key in rows:
        keys[area] = key
        named = [t for t in re.findall(r"[a-z0-9][a-z0-9-]*[a-z0-9]", cell) if t in groups]
        m = re.search(r"the (\w+) pass-5 groups", cell)
        if m:
            fifth = by_registry.get("data/public_sources_20261107_round5.json", [])
            words = {"nine": 9, "ten": 10, "eight": 8}
            if words.get(m.group(1)) != len(fifth):
                problems.append(f"{GOAL}: '{m.group(0)}' but the pass-5 registry has {len(fifth)} groups")
            named += fifth
        for sid in named:
            if sid in areas:
                problems.append(f"{sid}: in two areas of {GOAL} ({areas[sid]}, {area})")
            areas[sid] = area
    for sid in sorted(set(groups) - set(areas)):
        problems.append(f"{sid}: acquired but in no area of {GOAL}")
    return areas, keys, problems


def linked_inputs(sid, corpus):
    """Corpus inputs that come from this group: its fetch command names it, or its local_path is its folder."""
    out = []
    for inp in corpus["inputs"]:
        fetch = inp.get("fetch") or ""
        path = (inp.get("local_path") or "").replace("\\", "/")
        if (re.search(r"(fetch_corpus|fetch_sources)\.py\s+" + re.escape(sid) + r"(\s|$|;|&)", fetch)
                or path == f"data/external/{sid}" or path.startswith(f"data/external/{sid}/")):
            out.append(inp["id"])
    return out


def benchmark_suites(sid, root=ROOT):
    """Registered benchmark suites that reference a file under this group's data/external folder."""
    needle = f"data/external/{sid}/"
    found = []
    for report in read_json(BENCHMARKS, root)["reports"]:
        suite = root / report["suite"]
        if suite.is_file() and needle in suite.read_text(encoding="utf-8", errors="replace"):
            found.append(report["suite"])
    return found


def row_features(features):
    """Matrix row -> features whose tools include one of the row's tool files."""
    return {row: sorted(f["id"] for f in features["features"] if set(f["tools"]) & set(tools))
            for row, tools in corpus_matrix.ROW_TOOL_FILES.items()}


def fit(categories):
    rows, feats = set(), set()
    for c in categories:
        r, f = CATEGORY_FIT.get(c, ([], []))
        rows.update(r)
        feats.update(f)
    return sorted(rows), sorted(feats)


def dated(value):
    try:
        return date.fromisoformat(value) <= date.today()
    except (TypeError, ValueError):
        return False


def evidence_problems(sid, what, paths, root):
    out = []
    if not paths:
        out.append(f"{sid}: {what} cites no evidence file")
    for p in paths:
        if not (root / p.split("#", 1)[0]).exists():
            out.append(f"{sid}: {what} evidence {p} does not exist")
    return out


def build(root=ROOT):
    """All rows, the earlier pinned sources, and every rule problem."""
    groups, problems = load_groups(root)
    areas, area_keys, area_problems = goal_areas(groups, root)
    problems += area_problems
    corpus, matrix = read_json(CORPUS, root), read_json(MATRIX, root)
    features = read_json(FEATURES, root)
    feature_ids = {f["id"] for f in features["features"]}
    by_row = row_features(features)
    cells = {}
    for c in matrix["cells"]:
        cells.setdefault(c["input"], []).append(c)
    for cat, (rows, feats) in CATEGORY_FIT.items():
        problems += [f"CATEGORY_FIT {cat}: unknown matrix row {r}" for r in rows if r not in corpus_matrix.ROWS]
        problems += [f"CATEGORY_FIT {cat}: unknown feature {f}" for f in feats if f not in feature_ids]

    def feeding(sid):
        inputs = linked_inputs(sid, corpus)
        found = [c for i in inputs for c in sorted(cells.get(i, []), key=lambda c: c["row"])]
        return inputs, found, benchmark_suites(sid, root)

    out = []
    for sid, (rel, rec) in groups.items():
        depth = rec.get("depth") or {}
        for word in HAND_SET:
            if word in depth:
                problems.append(f"{sid}: depth.{word} is derived from the matrix and benchmarks, never set by hand")
        for cat in rec.get("categories", []):
            if cat not in CATEGORY_FIT:
                problems.append(f"{sid}: category {cat!r} has no CATEGORY_FIT entry in scripts/corpus_depth.py")
        key = depth.get("key")
        if not key:
            problems.append(f"{sid}: no depth.key (use status 'unknown' when the records say nothing)")
            key = {"status": "unknown", "what": "", "evidence": ""}
        elif key.get("status") not in KEY_STATUSES:
            problems.append(f"{sid}: depth.key.status {key.get('status')!r} not one of {', '.join(KEY_STATUSES)}")
        else:
            problems += evidence_problems(sid, "depth.key", [key.get("evidence")] if key.get("evidence") else [], root)
        plan, retired = depth.get("plan"), depth.get("retired")
        if plan and retired:
            problems.append(f"{sid}: both a plan and a retirement")
        plan_ok = bool(plan) and dated(plan.get("date")) and plan.get("key") and plan.get("task")
        if plan and not plan_ok:
            problems.append(f"{sid}: depth.plan needs a past ISO date, the key and the task")
        if plan:
            problems += evidence_problems(sid, "depth.plan", plan.get("evidence") or [], root)
        if retired:
            if not retired.get("reason"):
                problems.append(f"{sid}: depth.retired needs a reason")
            problems += evidence_problems(sid, "depth.retired", retired.get("evidence") or [], root)
        inputs, found, suites = feeding(sid)
        scored = [c for c in found if c["status"] in SCORED]
        if retired and (scored or suites):
            problems.append(f"{sid}: retired but still feeds {len(scored)} scored cells / {len(suites)} suites")
        if rec.get("evidence_role", "acquired-unscored") != "acquired-unscored" and not (scored or suites):
            problems.append(f"{sid}: evidence_role {rec['evidence_role']!r} claims evaluation that no scored matrix "
                            "cell or registered benchmark backs")
        status = (RETIRED if retired else FEEDS if (scored or suites) else PLANNED if plan_ok else UNPLANNED)
        cats = rec.get("categories", [])
        fit_rows, fit_feats = fit(cats)
        out.append({
            "id": sid, "registry": rel, "name": rec.get("name", ""), "family": rec.get("source_family", sid),
            "area": areas.get(sid, "?"), "area_key": area_keys.get(areas.get(sid), ""),
            "licence": licence_status(rec.get("license", "")), "licence_text": rec.get("license", ""),
            "origin": rec.get("origin", ""), "categories": cats, "key": key, "plan": plan, "retired": retired,
            "note": depth.get("note", ""), "inputs": inputs, "cells": found, "suites": suites,
            "features": sorted({f for c in found for f in by_row.get(c["row"], [])}),
            "fit_rows": fit_rows, "fit_features": fit_feats, "status": status})
    earlier = []
    pins = read_json(PINS, root)
    for sid in pins:
        if sid == "about" or sid in groups:
            continue
        inputs, found, suites = feeding(sid)
        earlier.append({"id": sid, "inputs": inputs, "cells": found, "suites": suites,
                        "features": sorted({f for c in found for f in by_row.get(c["row"], [])})})
    return out, earlier, problems


KEY_BLOCKED = ("no key in source", "withheld by publisher")


def ranked(rows):
    """UNPLANNED groups by the existing features they could exercise, then key in hand, then open licence.

    A group whose own record says it has no key, or whose publisher withholds it, cannot feed a scored task however
    many features it fits, so it ranks after every group that may have one."""
    pool = [r for r in rows if r["status"] == UNPLANNED]
    return sorted(pool, key=lambda r: (r["key"]["status"] in KEY_BLOCKED, -len(r["fit_features"]), -len(r["fit_rows"]),
                                       KEY_STATUSES.index(r["key"]["status"]) if r["key"]["status"] in KEY_STATUSES
                                       else len(KEY_STATUSES), r["licence"] != "open licence stated", r["id"]))


def esc(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def link(path, prefix=PREFIX):
    base = path.split("#", 1)[0]
    return f"[{Path(base).name}]({prefix}{base})"


def row_label(n):
    return f"row {n} {corpus_matrix.ROWS[n]['short']}"


def cell_text(cells):
    if not cells:
        return "none"
    return "; ".join(f"{row_label(c['row'])} / {c['input']}: {c['status']}" for c in cells)


def fit_text(r):
    rows = ", ".join(row_label(n) for n in r["fit_rows"]) or "no matrix row"
    return f"{rows}; features {', '.join(r['fit_features']) or 'none'}"


def disposition_text(r, prefix=PREFIX):
    if r["status"] == PLANNED:
        p = r["plan"]
        ev = ", ".join(link(e, prefix) for e in p["evidence"])
        text = f"{p['date']}: key {p['key']}; task {p['task']} ({ev})"
        return text + (f". {p['note']}" if p.get("note") else "")
    if r["status"] == RETIRED:
        return r["retired"]["reason"] + " (" + ", ".join(link(e, prefix) for e in r["retired"]["evidence"]) + ")"
    if r["status"] == FEEDS:
        return "scored through " + (cell_text([c for c in r["cells"] if c["status"] in SCORED]) or
                                    ", ".join(r["suites"]))
    return r["note"] or "no plan, key or retirement recorded"


def page(rows, earlier, prefix=PREFIX):
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUS_ORDER}
    unplanned = [r for r in rows if r["status"] == UNPLANNED]
    lines = [
        "# Corpus depth: every acquired source group and its disposition", "",
        f"*Generated by `scripts/corpus_depth.py` from the acquisition registries (`{REGISTRY_GLOB}`, additive "
        f"`depth` field), [{Path(GOAL).name}]({prefix}{GOAL}) (areas), [corpus.json]({prefix}{CORPUS}) and "
        f"[matrix.json]({prefix}{MATRIX}) (what each group feeds), [registry.json]({prefix}{BENCHMARKS}) and "
        f"[features.json]({prefix}{FEATURES}). Edit those, then run `python scripts/corpus_depth.py --write`; "
        "`--check` runs in the test suite.*", "",
        f"The standing goal ([DEPTH_GOAL.md]({prefix}{GOAL})): before any further acquisition, every acquired "
        "source either feeds a scored task through the product path, or has a dated plan naming its key, or is "
        "retired with its reason. The status below is derived, not typed: **feeds** needs a scored matrix cell "
        "(pass or fail) or a registered benchmark; **planned** needs a dated plan with its key, task and evidence; "
        "**retired** needs a reason with evidence. Everything else is **UNPLANNED**.", "",
        f"**{len(rows)} groups: {counts[FEEDS]} feed a scored task, {counts[PLANNED]} have a dated plan with a "
        f"named key, {counts[RETIRED]} retired, {counts[UNPLANNED]} UNPLANNED.**", "",
        f"## UNPLANNED: {len(unplanned)} of {len(rows)}", "",
        "No new acquisition pass while this list is not empty (`python scripts/corpus_depth.py --strict` fails "
        "until it is).", "",
        ", ".join(f"`{r['id']}`" for r in sorted(unplanned, key=lambda r: (r["area"], r["id"]))) or "None.", "",
        "## Next to wire: the ten highest-value UNPLANNED groups", "",
        "Ranked by how many existing features the group's acquisition categories could exercise, then by the "
        "matrix rows, then by key in hand (publisher labels first), then open licence. A group whose own record "
        "says it has no key, or whose publisher withholds it, ranks after all the others: it cannot feed a scored "
        "task until someone authors a key. The fit is by category: a "
        "candidate, not a verified applicability. Each still needs an adapter, a frozen key and a split before "
        "it scores anything.", "",
        "| # | Group | Area | Could exercise (matrix row / features) | Key availability | Licence |",
        "|---|---|---|---|---|---|"]
    for n, r in enumerate(ranked(rows)[:10], 1):
        lines.append(f"| {n} | `{r['id']}` | {esc(r['area'])} | {esc(fit_text(r))} | "
                     f"{esc(r['key']['status'])}: {esc(r['key']['what'])} | {esc(r['licence'])} |")
    labelled = [r for r in ranked(rows) if r["key"]["status"] == KEY_STATUSES[0]]
    lines += ["", f"### UNPLANNED groups with publisher labels in hand: {len(labelled)}", "",
              "Fewer features fit these, but a key already exists in their own files (unopened; verify before "
              "freezing it). In the ranked order above.", "",
              "| Group | Area | Could exercise (matrix row / features) | Labels | Note |", "|---|---|---|---|---|"]
    for r in labelled:
        lines.append(f"| `{r['id']}` | {esc(r['area'])} | {esc(fit_text(r))} | {esc(r['key']['what'])} | "
                     f"{esc(r['note'])} |")
    lines += ["", "## The register", "",
              "One row per acquisition group. *Feeds now* lists the group's corpus inputs and matrix cells with "
              "their status; *features* are those whose tools the fed matrix rows run.", "",
              "| Group | Family | Area | Licence / terms | What it is | Feeds now (matrix cells; features) | "
              "Key availability | Status | Disposition |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["area"], STATUS_ORDER.index(r["status"]), r["id"])):
        feeds = cell_text(r["cells"]) + (f"; suites {', '.join(r['suites'])}" if r["suites"] else "")
        if r["features"]:
            feeds += f"; features {', '.join(r['features'])}"
        status = f"**{r['status']}**" if r["status"] == UNPLANNED else r["status"]
        lines.append(
            f"| `{r['id']}` | {esc(r['family'])} | {esc(r['area'])} | {esc(r['licence'])} | "
            f"{esc(r['name'])} ({esc(r['origin'])}) | {esc(feeds)} | {esc(r['key']['status'])}: "
            f"{esc(r['key']['what'])} | {status} | {esc(disposition_text(r, prefix))} |")
    lines += ["", "## Earlier pinned sources (outside the 49-group goal)", "",
              f"Sources pinned in [corpus_pins.json]({prefix}{PINS}) before the 2026-11-07 passes. They are "
              "listed so the feeding rule above is seen to find real matrix cells; they carry no disposition here.",
              "", "| Source | Corpus inputs | Matrix cells | Features |", "|---|---|---|---|"]
    for e in earlier:
        lines.append(f"| `{e['id']}` | {esc(', '.join(e['inputs']) or 'none')} | {esc(cell_text(e['cells']))} | "
                     f"{esc(', '.join(e['features']) or 'none')} |")
    lines += ["", "## Limits", "",
              "- Areas come from the DEPTH_GOAL table; key availability comes from each group's own acquisition "
              "record (its limits and exposure text), not from opening the files. A label marked retained is "
              "unverified until a key is frozen from it.",
              "- A dated plan is not depth: depth is the six checks in DEPTH_GOAL.md. Development runs on a planned "
              "group (the plan's note) are not a sealed held-out result.",
              "- The next-to-wire fit is a category match. It does not say an adapter exists or that the result "
              "would hold.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="write docs/CORPUS_DEPTH.md")
    g.add_argument("--check", action="store_true", help="exit 1 on a broken rule or a stale docs/CORPUS_DEPTH.md")
    g.add_argument("--strict", action="store_true", help="--check, and exit 1 while any group is UNPLANNED")
    a = ap.parse_args(argv)
    rows, earlier, bad = build()
    text = page(rows, earlier)
    if a.check or a.strict:
        current = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n") if TARGET.exists() else None
        if current != text:
            bad.append("docs/CORPUS_DEPTH.md is stale or missing: run python scripts/corpus_depth.py --write")
        if a.strict:
            bad += [f"{r['id']}: UNPLANNED" for r in rows if r["status"] == UNPLANNED]
        print("\n".join(bad) if bad else "corpus depth: rules hold and docs/CORPUS_DEPTH.md is current")
        return 1 if bad else 0
    if bad:
        print("\n".join(bad))
        return 1
    if a.write:
        TARGET.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {TARGET.relative_to(ROOT).as_posix()}")
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUS_ORDER}
    print(", ".join(f"{s}: {n}" for s, n in counts.items()))
    print("UNPLANNED:", " ".join(r["id"] for r in rows if r["status"] == UNPLANNED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
