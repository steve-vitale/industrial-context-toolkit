"""Every lockout/tagout (LOTO) or isolation output stays non-directive (docs/GOAL_ISOLATION_POC.md).

Reads the committed outputs of both LOTO design mockups and their documentation:
  - OPEN100: out/open100_structural/loto_isolation_points.csv, the isolation points in plant_structure.json, the
    legend and frame of the sheet 7 still (scripts/render_open100_structural.py) and the table in
    docs/OPEN100_STRUCTURAL.md;
  - TE: the LOTO valve crossings in out/scene/te_scene.json, the LOTO labels the Blender still drew
    (drafts/3d-tour/label_boxes.json) and the LOTO panel and data of the interactive tour page;
  - docs/DELIVERABLES.md's "Lockout/tagout isolation view" row.
Fails when any note, label, caption or legend says where to isolate, tells a person to operate a device, claims zero
energy or isolation, gives a step or sequence, or names a device as the isolation point; when a control, check or
relief valve is listed without "not positive isolation"; or when a status is not the fixed wording of
scripts/isolation_wording.py (whose header must match GOAL_ISOLATION_POC.md byte for byte). A control checks that
the phrase check catches the old, directive wording. Stdlib only.
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

# Banned in any note, label, caption or legend of an isolation output (the fixed header and MOCKUP_STATUS are
# checked by exact comparison instead, since they name lockout/tagout in order to deny it).
DIRECTIVE = [
    (r"\bisolate (at|there|or|on|the|it at|from|by)\b", "names where to isolate"),
    (r"\bisolation (at|by)\b", "names where to isolate"),
    (r"\b(close|open|shut|lock|tag) (the|valve|it|its)\b", "an instruction to operate a device"),
    (r"\block(ed|ing)? out\b", "a lockout instruction"),   # the noun "lockout/tagout" is allowed
    (r"\bzero[ -]energy\b", "a zero-energy claim"),
    (r"\bprocedure step\b|\bstep \d|\bsteps?\b|\bsequence\b|\bin reverse order\b", "a step or sequence"),
    (r"\b(safe to|is isolated|are isolated|isolated\b(?! from))", "a statement that something is isolated or safe"),
    (r"\bisolate all\b", "an instruction to isolate"),
    (r"\btry[ -]start\b|\bverif(y|ication) (of )?zero\b", "a verification instruction"),
    (r"\b(isolation|block) (point|candidate)s?\b(?! not)", "names a device as the isolation point"),
    (r"\bcandidate (block|isolation)\b", "names a device as the isolation point"),
]


def directive_findings(text):
    """The banned phrases in `text`, as (matched text, reason) pairs; empty when the text is non-directive."""
    low = text.lower()
    return [(m.group(0), why) for pat, why in DIRECTIVE for m in re.finditer(pat, low)]


FAILS = []


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
    # 0. the wording itself, and a control that the phrase check bites
    check("the fixed header matches docs/GOAL_ISOLATION_POC.md byte for byte", W.FIXED_HEADER == goal_header(),
          (W.FIXED_HEADER, goal_header()))
    check("the mockup status is 'DESIGN MOCKUP, NOT A PROCEDURE.' plus the header from its third sentence on",
          W.MOCKUP_STATUS.startswith("DESIGN MOCKUP, NOT A PROCEDURE. THIS IS NOT AN ISOLATION OR LOCKOUT/TAGOUT")
          and W.FIXED_HEADER.endswith(W.MOCKUP_STATUS[len("DESIGN MOCKUP, NOT A PROCEDURE. "):]))
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
           "A real isolation is verified at the point (try-start, zero pressure and temperature)"]
    check("control: the phrase check flags every piece of the old directive wording", all(directive_findings(t)
                                                                                          for t in old),
          [t for t in old if not directive_findings(t)])
    fine = ["Boundary: a line continues to another system (X); energy can enter here. Not assessed: which device "
            "isolates it.", "Motor-driven: electrical energy is not shown on this drawing (not assessed).",
            "Control valve: not positive isolation."]
    check("control: the new observation wording passes the phrase check", not bad(fine), bad(fine))

    # 1. OPEN100 CSV and plant structure
    with (ROOT / "out" / "open100_structural" / "loto_isolation_points.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    check("OPEN100 CSV: has rows", len(rows) > 100, len(rows))
    check("OPEN100 CSV: every row's status is the fixed mockup wording", all(r["status"] == W.MOCKUP_STATUS
                                                                             for r in rows))
    check("OPEN100 CSV: no note is directive", not bad(r["note"] for r in rows), bad(r["note"] for r in rows)[:5])
    nonpos = [r for r in rows if r["kind"] in ("control_valve", "relief_device", "check_valve")]
    check("OPEN100 CSV: every control, relief or check valve says 'not positive isolation'",
          nonpos and all(W.NOT_POSITIVE in r["note"] for r in nonpos))
    check("OPEN100 CSV: no other kind claims to isolate or to be an isolation device",
          not [r for r in rows if r["kind"] not in ("control_valve", "relief_device")
               and re.search(r"\b(is|an) (isolation|isolating) (point|device)\b", r["note"].lower())])
    sdoc = json.loads((ROOT / "out" / "open100_structural" / "plant_structure.json").read_text(encoding="utf-8"))
    pts = sdoc["isolation_points"]
    check("OPEN100 plant structure: the isolation points carry the fixed mockup status",
          sdoc.get("isolation_points_status") == W.MOCKUP_STATUS)
    check("OPEN100 plant structure: no note is directive", not bad(p["note"] for p in pts), bad(p["note"] for p in pts)[:5])
    check("OPEN100 plant structure and CSV carry the same notes",
          sorted((p["id"], p["note"]) for p in pts) == sorted((r["id"], r["note"]) for r in rows))

    # 2. OPEN100 sheet 7 still: frame and legend (the generator's text; the PNG is its output)
    import render_open100_structural as R
    check("OPEN100 still: the frame starts with the fixed mockup wording and is printed whole",
          R.LOTO_FRAME.startswith(W.MOCKUP_STATUS) and "lines[:3]" not in (ROOT / "scripts" /
                                                                           "render_open100_structural.py").read_text(
              encoding="utf-8"))
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
    check("TE scene data: the LOTO status is the fixed mockup wording", scene["meta"]["loto"] == W.MOCKUP_STATUS)

    # 4. TE Blender still: the LOTO labels it drew, and the shot's caption and card
    boxes = json.loads((ROOT / "drafts" / "3d-tour" / "label_boxes.json").read_text(encoding="utf-8"))
    still = next(s for s in boxes["stills"] if s["name"] == "40_loto_mockup")
    labels = [l["text"] for l in still["labels"] if l["kind"] == "loto"]
    check("TE still: the LOTO labels were drawn", len(labels) >= 8, len(labels))
    check("TE still: no LOTO label is directive or names a valve", not bad(labels) and
          not [t for t in labels if "valve" in t.lower()], [t for t in labels if bad([t]) or "valve" in t.lower()])
    others = [l["text"] for l in still["labels"] if l["kind"] in ("overlay_card", "overlay_caption")]
    check("TE still: no card or caption on it is directive", not bad(others), bad(others))

    # 5. TE interactive tour page: the LOTO data and panel
    page = (ROOT / "drafts" / "interactive-tour" / "page" / "te-tour.html").read_text(encoding="utf-8")
    i = page.index("const TOUR = ") + len("const TOUR = ")
    tour, _ = json.JSONDecoder().raw_decode(page, i)
    loto = tour["data"]["loto"]
    check("TE interactive tour: the LOTO status is the fixed mockup wording", loto["status"] == W.MOCKUP_STATUS)
    ptexts = [p["text"] for p in loto["points"]]
    check("TE interactive tour: no point text is directive or names a valve",
          not bad(ptexts) and not [t for t in ptexts if "valve" in t.lower()], ptexts)
    m = re.search(r'<div class="tour-loto"[^>]*>(.*?)</div>\s*</section>', page, re.S)
    panel = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""
    panel = panel.replace(W.MOCKUP_STATUS[len("DESIGN MOCKUP, NOT A PROCEDURE. "):], "")
    check("TE interactive tour: the LOTO panel is found and carries the fixed wording",
          bool(m) and W.MOCKUP_STATUS[len("DESIGN MOCKUP, NOT A PROCEDURE. "):] in html.unescape(m.group(1)))
    check("TE interactive tour: no LOTO panel text is directive", not bad([panel]), bad([panel]))
    live = (ROOT / "drafts" / "interactive-tour" / "live.js").read_text(encoding="utf-8")
    shown = re.findall(r"<strong>([^<]*)</strong>|`(LOTO mockup[^`]*)`|\. ([A-Z][^.<`]*\.)</p>`", live)
    shown = [re.sub(r"\$\{[^}]*\}", "N", " ".join(x for x in t if x)) for t in shown]   # template code is not text
    check("TE interactive tour: no readout heading or note in live.js is directive", not bad(shown), bad(shown))

    # 6. documentation of the two views
    doc = (ROOT / "docs" / "OPEN100_STRUCTURAL.md").read_text(encoding="utf-8")
    sec = doc[doc.index("## 5. LOTO isolation view"):doc.index("## Reproduce")]
    table = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| Kind")]
    check("docs/OPEN100_STRUCTURAL.md: the LOTO table has a row per kind and none is directive",
          len(table) == 8 and not bad(table), bad(table))
    row = next(l for l in (ROOT / "docs" / "DELIVERABLES.md").read_text(encoding="utf-8").splitlines()
               if l.startswith("| Lockout/tagout isolation view"))
    check("docs/DELIVERABLES.md: the LOTO row is not directive", not bad([row]), bad([row]))

    print(f"{'PASS' if not FAILS else 'FAIL'}  LOTO wording: {len(FAILS)} failing check(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
