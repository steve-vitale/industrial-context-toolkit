"""Every lockout/tagout (LOTO) or isolation output stays non-directive and carries the fixed status
(docs/GOAL_ISOLATION_POC.md).

Reads the committed outputs of both LOTO design mockups and the documents that describe them:
  - OPEN100: out/open100_structural/loto_isolation_points.csv, the isolation points in plant_structure.json, the
    legend and frame of the sheet 7 still (scripts/render_open100_structural.py);
  - TE: the LOTO valve crossings in out/scene/te_scene.json, the labels, card and caption the Blender still drew
    (drafts/3d-tour/label_boxes.json, and the OCR ground truth and read-back built from it);
  - the interactive browser tour, which must carry no LOTO content at all (both themes);
  - the LOTO-related lines of every document listed in DOCS below.
Fails when any of them says where to isolate, tells a person to operate a device (close, open, lock, set closed,
depressurize, bleed, de-energize, rack out), claims zero energy, absent energy, safety or isolation, gives a step
or sequence, names a device as the isolation point, or numbers the TE tags; when a control, check or relief valve is
listed without "not positive isolation"; or when a status is not scripts/isolation_wording.MOCKUP_STATUS exactly
(whose header part must match GOAL_ISOLATION_POC.md byte for byte). Text is compared with whitespace and line breaks
collapsed. Documents that state the prohibitions or keep their history are allowlisted by name, each with its
reason. A control checks that the phrase check catches the old, directive wording. Stdlib only.
"""
import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import isolation_wording as W  # noqa: E402

# Banned in any note, label, caption, legend or LOTO-related document line. The fixed header and MOCKUP_STATUS
# are removed before matching (they name lockout/tagout in order to deny it) and checked by exact comparison.
DIRECTIVE = [
    (r"\bisolate (at|there|on|the|it at|from|by|all)\b|\bisolate or verify\b", "names where or what to isolate"),
    (r"\bisolation (at|by)\b", "names where to isolate"),
    (r"\b(close|open|shut|lock|tag|set|leave) (the|valve|it|its|them|closed|open|shut)\b",
     "an instruction to operate a device"),
    (r"\bset (it |the \w+ )?(closed|open)\b", "an instruction to set a position"),
    (r"\block(ed|ing)? out\b|\brack(ed|ing)? out\b", "a lockout or racking instruction"),
    (r"\bde-?pressuri[sz]e|\bbleed\b|\bbleed (off|down)\b|\bde-?energi[sz]e", "an energy-removal instruction"),
    (r"\bzero[ -]energy\b|\benergy is (absent|removed|gone)\b|\bno energy remains\b", "a zero-energy claim"),
    (r"\bprocedure step\b|\bstep \d|\bsteps?\b|\bsequence\b|\bin reverse order\b", "a step or sequence"),
    (r"\bsafe to\b|\bis safe\b|\bisolated\b", "a statement that something is isolated or safe"),
    (r"\btry[ -]start\b|\bverif(y|ication) (of )?zero\b", "a verification instruction"),
    (r"\b(an|the) isolation point (for|of|at)\b|\bisolation points? (are |is )?(inferred|read|listed|marked)\b"
     r"|\bmarks? isolation points\b|\bcandidate isolation points?\b|\bblock candidates?\b",
     "names a device as the isolation point"),
    (r"\bcandidate (block|isolation)\b", "names a device as the isolation point"),
]

# Documents whose LOTO-related lines are scanned (a line counts when it mentions LOTO, lockout or isolation).
DOCS = ["docs/OPEN100_STRUCTURAL.md", "docs/DELIVERABLES.md", "docs/DATA_LINEAGE.md", "docs/MODELS.md",
        "docs/review-kit/README.md", "docs/review-kit/OPS_REVIEWER_BRIEF.md", "docs/review-kit/CHECKLIST_3D_STILLS.md",
        "docs/review-kit/FOLLOW_THE_DATA.md", "docs/review-kit/TIMING_LOG.csv", "drafts/3d-tour/README.md",
        "drafts/3d-tour/REVIEW_NOTES.md", "drafts/interactive-tour/README.md",
        "drafts/interactive-tour/audit/report.md", "drafts/interactive-tour/audit/report.json"]
# Not scanned, by name and reason. Each must exist, so the list cannot rot silently.
ALLOW = {
    "docs/GOAL_ISOLATION_POC.md": "defines the prohibitions, so it quotes the banned phrases",
    "docs/3D_TOUR_PLAN.md": "history: records the withdrawn steps and zero-energy idea and the old labels",
    "docs/CONTEXT_MAP_FORMAT.md": "the format of a site's own reviewed isolation_point register (sequence, position)",
    "docs/JOURNAL.md": "dated history of earlier wording",
}
LOTO_LINE = re.compile(r"loto|lockout|isolat", re.I)

FAILS = []


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def directive_findings(text):
    """The banned phrases in `text`, as (matched text, reason) pairs; empty when the text is non-directive."""
    low = norm(text).replace(W.MOCKUP_STATUS, " ").replace(W.FIXED_HEADER, " ").lower()
    return [(m.group(0), why) for pat, why in DIRECTIVE for m in re.finditer(pat, low)]


def check(name, ok, detail=None):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok or detail is None else f"  {str(detail)[:600]}"))
    if not ok:
        FAILS.append(name)


def bad(texts):
    return [(t, directive_findings(t)) for t in texts if directive_findings(t)]


def goal_header():
    text = (ROOT / "docs" / "GOAL_ISOLATION_POC.md").read_text(encoding="utf-8")
    sec = text[text.index("## The fixed header"):]
    quote, started = [], False
    for line in sec.splitlines()[1:]:
        if line.startswith("> "):
            quote.append(line[2:])
            started = True
        elif started:
            break
    return " ".join(quote)


def main():
    # 0. the wording itself, and controls that the phrase check bites and does not over-fire
    check("the fixed header matches docs/GOAL_ISOLATION_POC.md byte for byte", W.FIXED_HEADER == goal_header(),
          (W.FIXED_HEADER, goal_header()))
    lead = ("DESIGN MOCKUP FOR A PROOF OF CONCEPT AND TESTING GROUND. NOT A PROCEDURE. All results must be verified "
            "by a qualified professional. ")
    check("the mockup status: proof of concept and testing ground, qualified professional, then the header from "
          "'THIS IS NOT AN ISOLATION' on, byte for byte",
          W.MOCKUP_STATUS.startswith(lead) and W.MOCKUP_STATUS[len(lead):] == W.FIXED_HEADER[
              W.FIXED_HEADER.index("THIS IS NOT AN ISOLATION"):] and "MUST NOT BE USED AS ONE" in W.MOCKUP_STATUS
          and "a point it does not list may exist, and a point it lists may not isolate" in W.MOCKUP_STATUS
          and "gravity and thermal energy are not assessed" in W.MOCKUP_STATUS)
    old = ["Line crosses to another system (X): energy can come in from there; isolate at the first block valve on "
           "this side or on that drawing.",
           "Motor-driven: electrical isolation at its breaker or disconnect (not on this drawing), plus the suction "
           "and discharge block valves.",
           "Line from another system: isolate there or at the first block valve",
           "Manual valve in a line: a candidate block (isolation) valve.",
           "Motor-operated valve: an isolation point for the line",
           "Line leaves to a vent or drain system (X): isolate or verify it on that drawing.",
           "Isolate all", "isolation in steps", "verification of zero energy", "restoration in reverse order",
           "close the block valve", "lock out the pump", "open the drain", "procedure step 3", "the pump is isolated",
           "the vessel is isolated from the header", "set closed", "set the valve closed", "depressurize the line",
           "bleed the trapped pressure", "de-energize the motor", "rack out the breaker", "energy is absent",
           "it is safe to\nopen", "isolate\n  at the first valve",
           "A real isolation is verified at the point (try-start, zero pressure and temperature)"]
    check("control: the phrase check flags every piece of the old directive wording (and wrapped text)",
          all(directive_findings(t) for t in old), [t for t in old if not directive_findings(t)])
    fine = ["Boundary: a line continues to another system (X); energy can enter here. Not assessed: which device "
            "isolates it.", "Motor-driven: electrical energy is not shown on this drawing (not assessed).",
            "Control valve: not positive isolation.", W.MOCKUP_STATUS, "Lockout/tagout view: design mockup only"]
    check("control: the observation wording and the fixed status pass the phrase check", not bad(fine), bad(fine))

    # 1. OPEN100 CSV and plant structure
    with (ROOT / "out" / "open100_structural" / "loto_isolation_points.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    check("OPEN100 CSV: has rows", len(rows) > 100, len(rows))
    check("OPEN100 CSV: every row's status equals MOCKUP_STATUS exactly",
          all(r["status"] == W.MOCKUP_STATUS for r in rows))
    check("OPEN100 CSV: no note is directive", not bad(r["note"] for r in rows), bad(r["note"] for r in rows)[:5])
    nonpos = [r for r in rows if r["kind"] in ("control_valve", "relief_device", "check_valve")]
    check("OPEN100 CSV: every control, relief or check valve says 'not positive isolation'",
          nonpos and all(W.NOT_POSITIVE in r["note"] for r in nonpos))
    check("OPEN100 CSV: no other kind claims to be an isolation point or device",
          not [r for r in rows if r["kind"] not in ("control_valve", "relief_device")
               and re.search(r"\b(is|an) (isolation|isolating) (point|device)\b", r["note"].lower())])
    sdoc = json.loads((ROOT / "out" / "open100_structural" / "plant_structure.json").read_text(encoding="utf-8"))
    pts = sdoc["isolation_points"]
    check("OPEN100 plant structure: the isolation points' status equals MOCKUP_STATUS exactly",
          sdoc.get("isolation_points_status") == W.MOCKUP_STATUS)
    check("OPEN100 plant structure: no note is directive", not bad(p["note"] for p in pts),
          bad(p["note"] for p in pts)[:5])
    check("OPEN100 plant structure and CSV carry the same notes",
          sorted((p["id"], p["note"]) for p in pts) == sorted((r["id"], r["note"]) for r in rows))

    # 2. OPEN100 sheet 7 still: frame and legend (the generator's text; the PNG is its output)
    import render_open100_structural as R
    src = (ROOT / "scripts" / "render_open100_structural.py").read_text(encoding="utf-8")
    check("OPEN100 still: the frame starts with MOCKUP_STATUS exactly and is printed whole",
          R.LOTO_FRAME.startswith(W.MOCKUP_STATUS) and "lines[:3]" not in src)
    legend = [t for _, t in R.LOTO_STYLE.values()]
    check("OPEN100 still: no legend entry is directive", not bad(legend), bad(legend))
    check("OPEN100 still: control valves and relief devices are labelled not positive isolation",
          all(W.NOT_POSITIVE in R.LOTO_STYLE[k][1].lower() for k in ("control_valve", "relief_device")))

    # 3. TE scene data: control valves are crossings, never candidates
    scene = json.loads((ROOT / "out" / "scene" / "te_scene.json").read_text(encoding="utf-8"))
    raw = json.dumps(scene)
    check("TE scene data: no 'isolation_candidate' or 'loto_candidates' remains",
          "isolation_candidate" not in raw and "loto_candidates" not in raw)
    cross = scene.get("loto_valve_crossings", [])
    check("TE scene data: every control valve listed is marked not positive isolation",
          cross and all(c["isolation"].startswith(W.NOT_POSITIVE) for c in cross))
    check("TE scene data: the LOTO status equals MOCKUP_STATUS exactly", scene["meta"]["loto"] == W.MOCKUP_STATUS)

    # 4. TE Blender still: what the renderer reports it drew, and the OCR ground truth derived from it
    for name, path in (("label boxes", "drafts/3d-tour/label_boxes.json"),
                       ("OCR ground truth", "drafts/3d-tour/label_truth.json")):
        boxes = json.loads((ROOT / path).read_text(encoding="utf-8"))
        still = next(s for s in boxes["stills"] if s["name"] == "40_loto_mockup")
        drawn = [l for l in still["labels"] if l.get("shown", True)]
        labels = [l["text"] for l in drawn if l["kind"] == "loto"]
        check(f"TE still ({name}): the LOTO tags were drawn", len(labels) >= 8, len(labels))
        check(f"TE still ({name}): no LOTO tag is directive, names a valve or starts with a number",
              not bad(labels) and not [t for t in labels if "valve" in t.lower() or re.match(r"\s*\d", t)],
              [t for t in labels if bad([t]) or "valve" in t.lower() or re.match(r"\s*\d", t)])
        check(f"TE still ({name}): every LOTO tag says 'not assessed'",
              all("not assessed" in t for t in labels), [t for t in labels if "not assessed" not in t])
        card = [l["text"] for l in drawn if l["id"] == "overlay:loto"]
        check(f"TE still ({name}): the card's text equals MOCKUP_STATUS exactly (line breaks aside)",
              len(card) == 1 and norm(card[0]) == W.MOCKUP_STATUS, card)
        others = [l["text"] for l in drawn if l["kind"].startswith("overlay")]
        check(f"TE still ({name}): no card or caption on it is directive", not bad(others), bad(others))
    ocr = (ROOT / "drafts" / "3d-tour" / "ocr_readback.json").read_text(encoding="utf-8")
    truth_texts = {norm(l["text"]) for s in json.loads((ROOT / "drafts" / "3d-tour" / "label_truth.json").read_text(
        encoding="utf-8"))["stills"] for l in s["labels"]}
    check("TE still OCR read-back: run on the current ground truth (its 40_loto_mockup truth texts are current)",
          W.MOCKUP_STATUS in truth_texts and "battery-limit block valve" not in ocr)

    # 5. TE interactive tour: no LOTO content on either theme's page
    for page_name in ("te-tour.html", "te-tour-light.html"):
        page = (ROOT / "drafts" / "interactive-tour" / "page" / page_name).read_text(encoding="utf-8")
        i = page.index("const TOUR = ") + len("const TOUR = ")
        tour, _ = json.JSONDecoder().raw_decode(page, i)
        check(f"TE interactive tour ({page_name}): no LOTO data, mode, panel, pins or drawn battery-limit valves",
              "loto" not in tour["data"] and "loto" not in tour["live"] and "data-loto" not in page
              and "Lockout/tagout mockup" not in page and "tour-loto" not in page and ".handwheel" not in page
              and not re.search(r"BL-S\d+\.valve", page))
    for path in ("drafts/interactive-tour/live.js", "drafts/interactive-tour/model.mjs"):
        src = (ROOT / path).read_text(encoding="utf-8")
        check(f"TE interactive tour ({path}): no LOTO mode or reachability model remains",
              not re.search(r"loto|energized|isolated", src, re.I))

    # 6. documents: the LOTO-related lines of every listed document; the allowlist names real files
    hits = []
    for path in DOCS:
        for n, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
            if LOTO_LINE.search(line) and directive_findings(line):
                hits.append((path, n, directive_findings(line)))
    check("documents: no LOTO-related line is directive", not hits, hits[:8])
    check("documents: every allowlisted file exists and is not also scanned",
          all((ROOT / p).exists() for p in ALLOW) and not set(ALLOW) & set(DOCS))
    doc = (ROOT / "docs" / "OPEN100_STRUCTURAL.md").read_text(encoding="utf-8")
    sec = doc[doc.index("## 5. LOTO isolation view"):doc.index("## Reproduce")]
    table = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| Kind")]
    check("docs/OPEN100_STRUCTURAL.md: the LOTO table has a row per kind and none is directive",
          len(table) == 8 and not bad(table), bad(table))

    print(f"{'PASS' if not FAILS else 'FAIL'}  LOTO wording: {len(FAILS)} failing check(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
