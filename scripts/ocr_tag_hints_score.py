"""Score pdf_tag_check.py's optional OCR tag hints on the round-6 development sets, beside deliberately wrong controls.

The hints are made exactly as `pdf_tag_check.py --ocr auto` makes them (page_hints on a PDF page with no text layer).
Each development input is turned into such a page first, so a known truth is available:

  te-a       generated Tennessee Eastman sheets 101-103, revision A (data/te_pid/rev-a): the PNG wrapped as an
             image-only PDF page. Truth: the key's symbol texts the tag rules can produce (two to five letters and a
             number, e.g. "FIC 101"); one-letter equipment tags (R-101) are skipped by the check by design and counted
             separately; off-page connector texts are not tags.
  te-d       revision D (data/te_pid, current), the same way.
  te-a-scan  revision A degraded with scripts/degrade_scans.py's own levels and seeds (L1-L3), written to a
             temporary folder; same truth (the degradation keeps geometry).
  pahala     Pahala WWTP P-401 and P-501 (PDF pages 21 and 22 of the public EPA docket file, checked against its
             pinned sha256 in data/corpus_pins.json; not in this repository, --pahala-pdf names it). Each page is
             rendered to an image (text layer removed) at 300 and 200 dpi. Truth: the tags pdf_tag_check.py reads from
             the same page's own text layer. No other page of the file is read.
  open100-scan  OPEN100 development sheets 0-5, clean and degraded (L1-L3, temporary folder). No tag key exists for
             OPEN100, so these are counts and clean-to-degraded agreement only, never precision or recall.

Held-out inputs are sealed (docs/GOAL_ROUND6.md): OPEN100 sheets 6-11 (including the committed scan-L1..L3 folders),
the DEXPI held-out renders and every other Pahala sheet are never opened; asking for another set is refused.

Scores, per set: text precision and recall (a hint whose letters and digits equal a truth tag), and located precision
and recall (the same, with the hint's box centre inside the truth box widened by LOCATE_MARGIN of the page on each
side). Controls on the same truth: perfect (the truth itself), empty (no hints), random (as many tag-shaped random
strings as there are hints, in the hints' boxes) and shifted (the real hints with every box moved SHIFT of the page
width: text scores stay, located scores should fall).

    python scripts/ocr_tag_hints_score.py --pahala-pdf <pahala-wwtp-design-build-drawings-2021-07-23.pdf> --out out/round6/ocr_tag_hints_dev
    python scripts/ocr_tag_hints_score.py --sets te-a --out <scratch>/te-a

Needs PyMuPDF, NumPy, OpenCV, Pillow and the Tesseract program. No model calls, no network.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdf_tag_check as ptc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SETS = ("te-a", "te-d", "te-a-scan", "pahala", "open100-scan")
TE = {"te-a": ROOT / "data" / "te_pid" / "rev-a", "te-d": ROOT / "data" / "te_pid"}
TE_SHEETS = ("101", "102", "103")
OPEN100 = ROOT / "data" / "external" / "pid2graph" / "PID2Graph" / "Complete" / "PID2Graph OPEN100"
OPEN100_DEV = (0, 1, 2, 3, 4, 5)  # development only; 6-11 are held out
PAHALA_PAGES = {"P-401": 21, "P-501": 22}  # development only; every other sheet is held out
PAHALA_DPI = (300, 200)
WRAP_DPI = 300  # a PNG is wrapped as a page of this resolution
TRUTH_TAG = re.compile(r"[A-Z]{2,5}\d+[A-Z]?")  # what the tag rules can produce, compared on letters and digits
LOCATE_MARGIN = 15  # 0-1000 page units
SHIFT = 150
SEED = 20261111


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def image_page(png):
    """An image-only one-page PDF holding the PNG at WRAP_DPI (no text layer)."""
    import pymupdf
    from PIL import Image
    with Image.open(png) as im:
        w, h = im.size
    doc = pymupdf.open()
    page = doc.new_page(width=w * 72 / WRAP_DPI, height=h * 72 / WRAP_DPI)
    page.insert_image(page.rect, filename=str(png))
    return doc


def scaled(box, w, h):
    return [box[0] * 1000 / w, box[1] * 1000 / h, box[2] * 1000 / w, box[3] * 1000 / h]


def te_truth(folder, sheet):
    key = json.loads((Path(folder) / "key.json").read_text(encoding="utf-8"))["sheets"][sheet]
    w, h = key["size_px"]
    truth, one_letter = {}, 0
    for s in key["symbols"].values():
        text = s.get("text") or ""
        k = ptc.key(text)
        if TRUTH_TAG.fullmatch(k):
            truth.setdefault(k, []).append({"tag": text, "box_0_1000": scaled(s["box"], w, h)})
        elif re.fullmatch(r"[A-Z]-?\d+[A-Z]?", text.strip()):
            one_letter += 1
    return truth, one_letter


def text_layer_truth(page):
    w, h = page.rect.width, page.rect.height
    return {k: [{"tag": v["text"], "box_0_1000": scaled(v["box"], w, h)}]
            for k, v in ptc.drawing_tags(page.get_text("words")).items()}


def located(hint_box, truth_boxes):
    cx, cy = (hint_box[0] + hint_box[2]) / 2, (hint_box[1] + hint_box[3]) / 2
    return any(b[0] - LOCATE_MARGIN <= cx <= b[2] + LOCATE_MARGIN and b[1] - LOCATE_MARGIN <= cy <= b[3] + LOCATE_MARGIN
               for b in truth_boxes)


def score(hints, truth):
    """hints {key: {"box_0_1000", "confidence"?}}; truth {key: [{"box_0_1000"}]} -> counts."""
    text = [k for k in hints if k in truth]
    loc = [k for k in text if located(hints[k]["box_0_1000"], [t["box_0_1000"] for t in truth[k]])]
    confident = [k for k in hints if hints[k].get("confidence", 100) >= 80]
    return {"truth": len(truth), "hints": len(hints), "text_tp": len(text), "located_tp": len(loc),
            "confident_hints": len(confident), "confident_text_tp": sum(1 for k in confident if k in truth)}


def controls(hints, truth, rng):
    perfect = {k: {"box_0_1000": v[0]["box_0_1000"]} for k, v in truth.items()}
    random_hints = {}
    for v in hints.values():
        s = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(rng.choice((2, 3)))) + \
            "".join(rng.choice("0123456789") for _ in range(3))
        random_hints[s] = {"box_0_1000": v["box_0_1000"]}
    shifted = {}
    for k, v in hints.items():
        b = v["box_0_1000"]
        dx = SHIFT if b[2] + SHIFT <= 1000 else -SHIFT
        shifted[k] = {**v, "box_0_1000": [b[0] + dx, b[1], b[2] + dx, b[3]]}
    return {"perfect": score(perfect, truth), "empty": score({}, truth), "random": score(random_hints, truth),
            "shifted": score(shifted, truth)}


def run_page(page, tess):
    start = time.perf_counter()
    hints, render = ptc.page_hints(page, tess)
    return hints, {**render, "seconds": round(time.perf_counter() - start, 1)}


def add(total, part):
    for k, v in part.items():
        total[k] = total.get(k, 0) + v
    return total


def keyed_set(name, pages, tess, rng):
    """pages: [(label, pymupdf page, truth, note)] -> per-page and total scores with controls."""
    rows, total, ctl = [], {}, {}
    for label, page, truth, note in pages:
        hints, render = run_page(page, tess)
        s = score(hints, truth)
        c = controls(hints, truth, rng)
        add(total, s)
        for cname, cs in c.items():
            ctl[cname] = add(ctl.get(cname, {}), cs)
        rows.append({"page": label, **s, "render": render, "note": note,
                     "missed": sorted(truth[k][0]["tag"] for k in truth if k not in hints),
                     "wrong": sorted(f"{hints[k]['tag']} ({hints[k]['confidence']})" for k in hints if k not in truth)})
    return {"set": name, "pages": rows, "total": total, "controls": ctl}


def open100_set(tmp, tess):
    import degrade_scans
    import pymupdf  # noqa: F401
    dest = Path(tmp) / "open100-dev-scan"
    degrade_scans.degrade_set(OPEN100, OPEN100_DEV, dest)
    rows = []
    for d in OPEN100_DEV:
        clean, _ = run_page(image_page(OPEN100 / f"{d}.png")[0], tess)
        row = {"sheet": d, "clean_hints": len(clean)}
        for level in (1, 2, 3):
            hints, render = run_page(image_page(Path(f"{dest}-L{level}") / f"{d}.png")[0], tess)
            agree = [k for k in hints if k in clean and located(hints[k]["box_0_1000"], [clean[k]["box_0_1000"]])]
            row[f"L{level}"] = {"hints": len(hints), "also_clean_same_place": len(agree), "seconds": render["seconds"]}
        rows.append(row)
    return {"set": "open100-scan", "no_key": "OPEN100 has no tag key: counts and clean-to-degraded agreement only, "
            "not accuracy", "sheets": rows}


def ratio(a, b):
    return round(a / b, 3) if b else None


def prf(t):
    return {"text_precision": ratio(t["text_tp"], t["hints"]), "text_recall": ratio(t["text_tp"], t["truth"]),
            "located_precision": ratio(t["located_tp"], t["hints"]), "located_recall": ratio(t["located_tp"], t["truth"]),
            "confident_precision": ratio(t["confident_text_tp"], t["confident_hints"])}


def fmt(v):
    return "-" if v is None else f"{v:.2f}"


def markdown(doc):
    lines = ["# OCR tag hints on the round-6 development sets", "",
             f"Made by `pdf_tag_check.py --ocr auto`'s page_hints ({doc['engine']}), scored by "
             "`scripts/ocr_tag_hints_score.py`. Hints are never verified tags; this measures how often they are right. "
             "Text = letters and digits equal a truth tag; located = also inside the truth box (widened by "
             f"{LOCATE_MARGIN}/1000 of the page). Confident = hints with OCR confidence 80 or more. Held-out sets "
             "were not opened.", "",
             "| Set | Run | Truth | Hints | Text P | Text R | Located P | Located R | Confident P |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in doc["sets"]:
        if "total" not in s:
            continue
        for run, t in [("hints", s["total"])] + [(f"control: {c}", v) for c, v in s["controls"].items()]:
            m = prf(t)
            lines.append(f"| {s['set']} | {run} | {t['truth']} | {t['hints']} | {fmt(m['text_precision'])} | "
                         f"{fmt(m['text_recall'])} | {fmt(m['located_precision'])} | {fmt(m['located_recall'])} | "
                         f"{fmt(m['confident_precision'])} |")
    lines += ["", "## Per page", ""]
    for s in doc["sets"]:
        if "pages" not in s:
            continue
        for p in s["pages"]:
            lines.append(f"- **{s['set']} {p['page']}**: {p['text_tp']}/{p['truth']} found, {p['hints']} hints, "
                         f"{p['hints'] - p['text_tp']} wrong; render {p['render']}"
                         + (f"; {p['note']}" if p.get("note") else ""))
            if p["missed"]:
                lines.append(f"  - missed: {', '.join(p['missed'])}")
            if p["wrong"]:
                lines.append(f"  - wrong (confidence): {', '.join(p['wrong'])}")
    for s in doc["sets"]:
        if s["set"] == "open100-scan":
            lines += ["", "## OPEN100 sheets 0-5, clean and degraded (no key)", "", s["no_key"], "",
                      "| Sheet | Clean hints | L1 hints (same as clean) | L2 | L3 |", "|---|---|---|---|---|"]
            for r in s["sheets"]:
                lines.append(f"| {r['sheet']} | {r['clean_hints']} | " + " | ".join(
                    f"{r[f'L{n}']['hints']} ({r[f'L{n}']['also_clean_same_place']})" for n in (1, 2, 3)) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sets", default=",".join(SETS), help="comma list from " + ", ".join(SETS))
    ap.add_argument("--pahala-pdf", help="the EPA docket PDF holding P-401 and P-501 (checked against its pin)")
    ap.add_argument("--out", required=True, help="output prefix; writes <out>.json and <out>.md")
    a = ap.parse_args(argv)
    sets = [s for s in a.sets.split(",") if s]
    refused = [s for s in sets if s not in SETS]
    if refused:
        ap.exit(2, f"refused: {refused} are not development sets (held-out sets stay sealed)\n")
    tess, version, reason = ptc.ocr_engine()
    if not tess:
        ap.exit(2, reason + "\n")
    rng = random.Random(SEED)
    doc = {"script": "scripts/ocr_tag_hints_score.py", "engine": f"tesseract {version}",
           "settings": {"psm": ptc.OCR_PSM, "glyph_px": ptc.OCR_GLYPH_PX, "pad": ptc.OCR_PAD, "chars": ptc.OCR_CHARS},
           "pdf_tag_check_sha256": sha256(Path(ptc.__file__)), "sets": []}
    with tempfile.TemporaryDirectory() as tmp:
        for name in sets:
            if name in TE:
                pages = []
                for sheet in TE_SHEETS:
                    truth, one = te_truth(TE[name], sheet)
                    pages.append((sheet, image_page(TE[name] / f"{sheet}.png")[0], truth,
                                  f"{one} one-letter equipment tags skipped by design"))
                doc["sets"].append(keyed_set(name, pages, tess, rng))
            elif name == "te-a-scan":
                import degrade_scans
                dest = Path(tmp) / "te-a-scan"
                degrade_scans.degrade_set(TE["te-a"], [int(s) for s in TE_SHEETS], dest)
                for level in (1, 2, 3):
                    pages = [(sheet, image_page(Path(f"{dest}-L{level}") / f"{sheet}.png")[0],
                              te_truth(TE["te-a"], sheet)[0], "") for sheet in TE_SHEETS]
                    doc["sets"].append(keyed_set(f"te-a-scan-L{level}", pages, tess, rng))
            elif name == "pahala":
                if not a.pahala_pdf:
                    print("pahala skipped: --pahala-pdf not given", file=sys.stderr)
                    continue
                pin = json.loads((ROOT / "data" / "corpus_pins.json").read_text(encoding="utf-8"))
                want = json.dumps(pin).split('"pahala-drawings"')[1].split('"sha256": "')[1][:64]
                if sha256(a.pahala_pdf) != want:
                    ap.exit(2, "refused: --pahala-pdf does not match the pinned EPA docket file\n")
                import pymupdf
                src = pymupdf.open(a.pahala_pdf)
                for dpi in PAHALA_DPI:
                    pages = []
                    for label, number in PAHALA_PAGES.items():
                        original = src[number - 1]
                        truth = text_layer_truth(original)
                        pix = original.get_pixmap(dpi=dpi, colorspace="gray", alpha=False)
                        png = Path(tmp) / f"pahala-{label}-{dpi}.png"
                        pix.save(str(png))
                        doc_img = pymupdf.open()
                        page = doc_img.new_page(width=original.rect.width, height=original.rect.height)
                        page.insert_image(page.rect, filename=str(png))
                        pages.append((label, page, truth, f"rendered at {dpi} dpi, text layer removed"))
                        assert not page.get_text("words")
                    doc["sets"].append(keyed_set(f"pahala-{dpi}dpi", pages, tess, rng))
            elif name == "open100-scan":
                doc["sets"].append(open100_set(tmp, tess))
    for s in doc["sets"]:
        if "total" in s:
            s["scores"] = prf(s["total"])
            s["control_scores"] = {c: prf(v) for c, v in s["controls"].items()}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{out}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    Path(f"{out}.md").write_text(markdown(doc), encoding="utf-8", newline="\n")
    print(markdown(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
