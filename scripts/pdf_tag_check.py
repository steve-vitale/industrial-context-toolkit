"""Cross-check a bundle's instrument and equipment tags against the PDF's own text layer.

Most P&IDs exported from CAD keep their text: every tag on the drawing is in the PDF as words with positions. This
compares that text with the tags the reader extracted, sheet by sheet, and lists three things for review:

  missed_by_reader      a tag printed on the drawing that no extracted item carries;
  not_in_text_layer     an extracted tag the drawing's text does not contain (a possible misread);
  matched               tags found in both.

Instrument bubbles print letters above the loop number ("LI" over "401", "ZIO" over "500, 101"); those are joined
from their positions. Single-word tags such as "FIT-403" or "MB-01" are read as they are. Tags are compared on
their letters and digits only, so "LI 401", "LI-401" and "LI401" agree.

A page with no usable text layer (outlined CAD text, or a scan) is reported as not checked: it needs OCR, and
nothing is inferred from its absence. The check never edits the bundle. Needs PyMuPDF (pip install pymupdf).

Optional OCR hints (--ocr auto): on a page that is not checked, the page image is read by the separately installed
Tesseract program and the same tag rules run on its words. The results are HINTS, kept apart from the text-layer
lists under "ocr_hints": each carries its OCR confidence and box, the page stays "not checked", and an OCR hint is
never reported as a matched, missed or misread tag. Tesseract (with its own language data, offline) is found the
way extract_text.py finds it; OCR also needs NumPy and OpenCV (requirements.txt). With the default --ocr off the
output is exactly what it was before OCR hints existed; with --ocr auto and no engine, the sheets are unchanged and
"ocr" says what is missing. Reading tags from the page image as hints is an idea credited in docs/DEPENDENCIES.md;
no outside tool is used.

Usage:
    python scripts/pdf_tag_check.py --bundle work/plant/bundle --pdf drawing.pdf --pages 21 --out work/plant/tag-check
    python scripts/pdf_tag_check.py --bundle work/plant/set-bundle --pdf set.pdf --pages 13,21,22 --out ...
    python scripts/pdf_tag_check.py ... --ocr auto     # OCR hints for pages without a text layer
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

LETTERS = re.compile(r"[A-Z]{2,5}")
NUMBER = re.compile(r"\d[\d,\s-]*[A-Z]?")
SINGLE = re.compile(r"[A-Z]{2,5}-?\d{2,7}[A-Z]?")  # one-letter forms (P-101) are skipped: they collide with drawing numbers
MIN_WORDS_FOR_TEXT_LAYER = 150  # Pahala: title-block-only pages carry 118-121 words, P&ID text pages 207-263
STOP = {"FOR", "REV", "NO", "DATE", "SHEET", "SHT", "OF", "DWG", "SCALE", "PAGE", "JOB", "SIZE", "NTS"}
MAX_NUMBER_WIDTH = 4.5  # a bubble's number line is at most this many letter-heights wide
TAG_GROUPS = ("units", "instruments", "line_items")

# OCR hints (--ocr auto). Settings chosen on the TE revision A and D sheets only (attempt A411, data/attempts.json).
OCR_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-,./()"  # tags are printed in capitals
OCR_PSM = 11                # Tesseract page segmentation: sparse text, the way a drawing carries it
OCR_GLYPH_PX = 22           # characters are scaled to about this height before OCR (measured on each page)
OCR_MAX_SCALE = 4
OCR_INTERP = "linear"       # upscaling interpolation ("linear" or "cubic")
OCR_INK_SHARE = 0.375       # ink: darker than the paper by this share of the paper-to-darkest range (160 on white)
OCR_DPI = 300               # render resolution for a page without one dominant image
OCR_MAX_PIXELS = 150_000_000
OCR_TIMEOUT = 300
OCR_PAD = 0.25              # an OCR box hugs the ink; pad it by this share of its height to a type-sized box
OCR_LABEL = ("OCR hints, not verified tags: read from the page image by OCR, each with the engine's confidence "
             "(0-100) and its box. Check each one on the drawing; nothing here is a text-layer match.")


def key(text):
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def is_number_word(text):
    return bool(re.fullmatch(r"[\d,\-]+[A-Z]?", text.upper()) and re.search(r"\d", text))


def number_below(letters, words):
    """The loop number printed under an instrument's letters: number words on the next line, grown outward from
    the bubble's centre while they touch, never wider than one bubble (two bubbles side by side stay apart)."""
    x0, y0, x1, y1 = letters[:4]
    height, centre = y1 - y0, (x0 + x1) / 2
    line = [w for w in words if is_number_word(w[4]) and 0 <= w[1] - y1 <= 1.2 * height]
    if not line:
        return None
    top = min(w[1] for w in line)
    line = sorted((w for w in line if abs(w[1] - top) < 0.3 * height), key=lambda w: w[0])
    seed = min(range(len(line)), key=lambda i: abs((line[i][0] + line[i][2]) / 2 - centre))
    lo = hi = seed
    while True:
        options = []
        for nxt in (lo - 1, hi + 1):
            if not 0 <= nxt < len(line):
                continue
            a, b = (line[nxt], line[lo]) if nxt < lo else (line[hi], line[nxt])
            left, right = min(line[lo][0], line[nxt][0]), max(line[hi][2], line[nxt][2])
            if b[0] - a[2] < 0.8 * height and right - left <= MAX_NUMBER_WIDTH * height:
                options.append((abs((left + right) / 2 - centre), nxt))
        if not options:
            break
        nxt = min(options)[1]  # grow toward the side that keeps the number centred under the letters
        lo, hi = min(lo, nxt), max(hi, nxt)
    cluster = line[lo:hi + 1]
    cx0, cx1 = cluster[0][0], cluster[-1][2]
    if abs((cx0 + cx1) / 2 - centre) >= 0.6 * max(x1 - x0, cx1 - cx0):
        return None
    return cx0, min(w[1] for w in cluster), cx1, max(w[3] for w in cluster), " ".join(w[4] for w in cluster)


def tags_with_words(words):
    """drawing_tags, also returning the words each tag was built from ("words": the letters and the number line)."""
    found = {}
    for w in words:
        text = w[4].upper()
        if LETTERS.fullmatch(text) and text not in STOP:
            c = number_below(w, words)
            if c and NUMBER.fullmatch(c[4].upper()):
                tag = f"{text} {c[4]}"
                line = [x for x in words if is_number_word(x[4]) and x[0] >= c[0] and x[2] <= c[2]
                        and x[1] >= c[1] and x[3] <= c[3]]
                found.setdefault(key(tag), {"text": tag, "box": [min(w[0], c[0]), w[1], max(w[2], c[2]), c[3]],
                                            "words": [w] + line})
        elif SINGLE.fullmatch(text):
            found.setdefault(key(text), {"text": w[4], "box": list(w[:4]), "words": [w]})
    return found


def drawing_tags(words):
    """Tags printed on a page: stacked instrument bubbles plus single-word tags. words are PyMuPDF
    get_text('words') tuples (x0, y0, x1, y1, text, ...). Returns {key: {"text", "box"}} in page units."""
    return {k: {"text": v["text"], "box": v["box"]} for k, v in tags_with_words(words).items()}


def tag_shaped(text):
    k = key(text)
    return bool(re.search(r"[A-Z]", k) and re.search(r"\d", k))


def model_tags(model, sheet):
    tags = {}
    for group in TAG_GROUPS:
        for item in model.get(group, []):
            for prov in item.get("provenance", []):
                if prov.get("sheet") == sheet and item.get("tag") and tag_shaped(item["tag"]):
                    tags.setdefault(key(item["tag"]), []).append({"id": item["id"], "tag": item["tag"],
                                                                  "box_0_1000": prov.get("box_0_1000")})
    return tags


def compare(drawn, extracted, page_size, word_count):
    if word_count < MIN_WORDS_FOR_TEXT_LAYER:
        return {"checked": False, "reason": f"no usable text layer ({word_count} words); the drawing text is outlined "
                "or scanned and needs OCR. Nothing is inferred from this page.", "words": word_count}
    w, h = page_size

    def scaled(box):
        return [round(box[0] * 1000 / w, 1), round(box[1] * 1000 / h, 1), round(box[2] * 1000 / w, 1),
                round(box[3] * 1000 / h, 1)]
    return {"checked": True, "words": word_count,
            "matched": sorted(drawn[k]["text"] for k in drawn if k in extracted),
            "missed_by_reader": [{"tag": drawn[k]["text"], "box_0_1000": scaled(drawn[k]["box"])}
                                 for k in sorted(drawn) if k not in extracted],
            "not_in_text_layer": [x for k in sorted(extracted) if k not in drawn for x in extracted[k]]}


def ocr_engine():
    """(tesseract program, version, None) when OCR hints can run, else (None, None, reason). Tesseract is found the way
    extract_text.py finds it (TESSERACT_CMD, PATH, standard install folders); its language data is installed with it
    and nothing is downloaded."""
    try:
        import cv2  # noqa: F401  (text isolation and scaling)
        import numpy  # noqa: F401
    except ImportError:
        return None, None, "OCR hints not made: NumPy and OpenCV are not installed (pip install -r requirements.txt)"
    import extract_text
    tess = extract_text._tesseract()
    if not tess:
        return None, None, "OCR hints not made: " + extract_text._not_found("tesseract", "Tesseract OCR")
    return tess, extract_text._tool_version(tess, "--version", r"tesseract v?([\w.\-]+)"), None


def render_page(page):
    """The page as a greyscale image and its resolution in dpi: at the resolution of an image covering most of the
    page (a scan's own pixels), else OCR_DPI; reduced if over OCR_MAX_PIXELS."""
    import numpy as np
    dpi, best = OCR_DPI, 0.0
    for img in page.get_images(full=True):
        for rect in page.get_image_rects(img[0]):
            if rect.width > 0 and rect.get_area() > best:
                # the longer sides pair up even when the image is placed rotated by 90 degrees
                best, dpi = rect.get_area(), max(img[2], img[3]) * 72 / max(rect.width, rect.height)
    if best < 0.5 * page.rect.get_area():
        dpi = OCR_DPI
    pixels = page.rect.width * page.rect.height * (dpi / 72) ** 2
    if pixels > OCR_MAX_PIXELS:
        dpi *= (OCR_MAX_PIXELS / pixels) ** 0.5
    pix = page.get_pixmap(dpi=max(36, round(dpi)), colorspace="gray", alpha=False)
    gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
    return gray, pix.width * 72 / page.rect.width


def isolate_text(gray):
    """Keep only character-sized ink (pipes, bubbles and frames are larger connected shapes, which OCR reads as
    noise) and measure the character height. A degraded scan is first cleaned to black on white by scan_cleanup.py's
    frozen round-4 step (clean drawings are left as they are). Returns (image, glyph height in pixels, cleaned)."""
    import cv2
    import numpy as np
    import scan_cleanup
    gray, cleaned = scan_cleanup.prepare(gray, clean="auto")
    paper, darkest = float(np.median(gray)), float(np.percentile(gray, 0.5))  # ink is a small share of a drawing
    ink = (gray < paper - OCR_INK_SHARE * (paper - darkest)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    h, w = stats[1:, cv2.CC_STAT_HEIGHT], stats[1:, cv2.CC_STAT_WIDTH]
    plausible = (h >= 4) & (h <= 120) & (w <= 2 * h)
    glyph = float(np.median(h[plausible])) if plausible.any() else 10.0
    keep = np.zeros(n, bool)
    keep[1:] = (h <= 2.2 * glyph) & (w <= 3 * glyph) & (h >= 0.3 * glyph)
    return np.where(keep[labels], gray, 255).astype(np.uint8), glyph, cleaned


def parse_tsv(tsv, scale):
    """Tesseract TSV -> word tuples (x0, y0, x1, y1, text, confidence) in the image's pixels before scaling. Each box
    is padded vertically by OCR_PAD of its height, so it compares with the tag rules like a text layer's type box."""
    words = []
    for line in tsv.splitlines()[1:]:
        c = line.split("\t")
        if len(c) < 12 or c[0] != "5" or not c[11].strip():
            continue
        left, top, width, height, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
        pad = OCR_PAD * height
        words.append((left / scale, (top - pad) / scale, (left + width) / scale, (top + height + pad) / scale,
                      c[11].strip(), conf))
    return words


def ocr_words(gray, tess):
    """OCR one page image -> (word tuples in the image's pixels, the measured glyph height and scale)."""
    import cv2
    import extract_text
    text, glyph, cleaned = isolate_text(gray)
    OCR_INTERPOLATION = cv2.INTER_LINEAR if OCR_INTERP == "linear" else cv2.INTER_CUBIC
    scale = min(OCR_MAX_SCALE, max(1.0, OCR_GLYPH_PX / glyph))
    scale = min(scale, max(1.0, (OCR_MAX_PIXELS / (text.shape[0] * text.shape[1])) ** 0.5))  # pixel cap after scaling
    if scale > 1:
        text = cv2.resize(text, None, fx=scale, fy=scale, interpolation=OCR_INTERPOLATION)
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "page.png"
        cv2.imwrite(str(image), text)
        cmd = [tess, str(image), "stdout", "-l", "eng", "--psm", str(OCR_PSM), "--dpi", "300",
               "-c", f"tessedit_char_whitelist={OCR_CHARS}", "tsv"]
        try:
            run = extract_text._run(cmd, OCR_TIMEOUT, dict(os.environ, OMP_THREAD_LIMIT="1"))
        except subprocess.TimeoutExpired:
            raise ValueError(f"tesseract did not finish within {OCR_TIMEOUT} s") from None
        if run.returncode != 0:
            raise ValueError("tesseract could not read the page image: " + extract_text._last_line(run))
    return parse_tsv(run.stdout.decode("utf-8", "replace"), scale), {"scan_cleaned": cleaned,
                                                                     "glyph_px": round(glyph, 1), "scale": round(scale, 2)}


def hints_from_words(words, dpi, page_size):
    """OCR word tuples (image pixels at dpi) -> {key: {"tag", "ocr_text", "confidence", "box_0_1000"}}. A hint's
    confidence is the lowest of the words it was built from."""
    w, h = page_size
    to_page = 72 / dpi
    hints = {}
    for k, v in tags_with_words(words).items():
        box = [c * to_page for c in v["box"]]
        hints[k] = {"tag": v["text"], "ocr_text": " ".join(x[4] for x in v["words"]),
                    "confidence": round(min(x[5] for x in v["words"]), 1),
                    "box_0_1000": [round(box[0] * 1000 / w, 1), round(box[1] * 1000 / h, 1),
                                   round(box[2] * 1000 / w, 1), round(box[3] * 1000 / h, 1)]}
    return hints


def page_hints(page, tess):
    """OCR hints for one PDF page, and how the page was read."""
    gray, dpi = render_page(page)
    words, settings = ocr_words(gray, tess)
    return hints_from_words(words, dpi, (page.rect.width, page.rect.height)), {"dpi": round(dpi, 1), **settings}


def compare_hints(hints, extracted, render):
    """OCR hints against the extracted tags, in lists named apart from the text-layer ones. A hint that agrees with
    an extracted tag is still a hint: the page stays not checked."""
    return {"label": OCR_LABEL, "render": render, "hints": len(hints),
            "hint_matches_extracted": [{**hints[k], "extracted": extracted[k]} for k in sorted(hints) if k in extracted],
            "hint_not_extracted": [hints[k] for k in sorted(hints) if k not in extracted],
            "extracted_without_hint": [x for k in sorted(extracted) if k not in hints for x in extracted[k]]}


def check(bundle, pdf, pages, ocr="off"):
    try:
        import pymupdf
    except ImportError:
        raise SystemExit("pdf_tag_check.py needs PyMuPDF: pip install pymupdf")
    bundle = Path(bundle)
    model = json.loads((bundle / "plant_model.json").read_text(encoding="utf-8"))
    sheets = [s["sheet"] for s in model["systems"]]
    if len(pages) != len(sheets):
        raise ValueError(f"--pages lists {len(pages)} page(s) but the bundle has {len(sheets)} sheet(s): {sheets}")
    doc = pymupdf.open(pdf)
    result = {"pdf": Path(pdf).name, "bundle": bundle.as_posix(), "sheets": []}
    tess = None
    if ocr == "auto":
        tess, version, reason = ocr_engine()
        result["ocr"] = ({"engine": f"tesseract {version}", "language": "eng", "psm": OCR_PSM, "label": OCR_LABEL}
                         if tess else {"engine": None, "unavailable": reason})
    for sheet, page in zip(sheets, pages):
        if not 1 <= page <= doc.page_count:
            raise ValueError(f"page {page} is outside the PDF (1 to {doc.page_count})")
        p = doc[page - 1]
        words = p.get_text("words")
        extracted = model_tags(model, sheet)
        entry = compare(drawing_tags(words), extracted, (p.rect.width, p.rect.height), len(words))
        if tess and not entry["checked"]:
            try:
                hints, render = page_hints(p, tess)
                entry["ocr_hints"] = compare_hints(hints, extracted, render)
            except Exception as error:  # noqa: BLE001  any OCR failure (cv2.error, MemoryError, a tesseract
                # refusal) leaves this page's "needs OCR" entry and every text-layer result as they are
                result["ocr"].setdefault("errors", []).append(
                    {"sheet": sheet, "page": page, "error": f"{type(error).__name__}: {error}"})
        result["sheets"].append({"sheet": sheet, "page": page, **entry})
    doc.close()
    return result


def markdown(result):
    lines = [f"# Tag cross-check: {result['pdf']}", "",
             "Tags printed in the PDF's text layer compared with the tags the reader extracted. Every line is a "
             "review candidate: open the drawing at the box shown (0-1000 page coordinates).", ""]
    for s in result["sheets"]:
        lines.append(f"## Sheet {s['sheet']} (PDF page {s['page']})")
        if not s["checked"]:
            lines += ["", f"Not checked: {s['reason']}", ""]
            if "ocr_hints" in s:
                lines += hint_markdown(s["ocr_hints"])
            continue
        lines += ["", f"{len(s['matched'])} matched · {len(s['missed_by_reader'])} on the drawing but not extracted · "
                  f"{len(s['not_in_text_layer'])} extracted but not in the text layer", ""]
        if s["missed_by_reader"]:
            lines += ["**On the drawing, not extracted:**", ""]
            lines += [f"- `{x['tag']}` at {x['box_0_1000']}" for x in s["missed_by_reader"]] + [""]
        if s["not_in_text_layer"]:
            lines += ["**Extracted, not in the text layer (possible misread):**", ""]
            lines += [f"- `{x['tag']}` ({x['id']}) at {x['box_0_1000']}" for x in s["not_in_text_layer"]] + [""]
    return "\n".join(lines) + "\n"


def hint_markdown(o):
    lines = ["### OCR hints (not verified tags)", "", o["label"], "",
             f"{o['hints']} hints · {len(o['hint_matches_extracted'])} agree with an extracted tag · "
             f"{len(o['hint_not_extracted'])} not extracted · {len(o['extracted_without_hint'])} extracted tags "
             "with no hint (OCR misses tags, so this is not a sign of a misread)", ""]
    if o["hint_not_extracted"]:
        lines += ["**OCR hint, not extracted (look on the drawing):**", ""]
        lines += [f"- `{x['tag']}` (OCR read `{x['ocr_text']}`, confidence {x['confidence']}) at {x['box_0_1000']}"
                  for x in o["hint_not_extracted"]] + [""]
    if o["hint_matches_extracted"]:
        lines += ["**OCR hint agrees with an extracted tag (still unverified):**", ""]
        lines += [f"- `{x['tag']}` (confidence {x['confidence']}) at {x['box_0_1000']}"
                  for x in o["hint_matches_extracted"]] + [""]
    return lines


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", required=True, help="a review bundle from import_site_drawing.py or import_drawing_set.py")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="1-based PDF page per bundle sheet, in sheet order, e.g. 13,21,22")
    ap.add_argument("--out", required=True, help="new or empty folder for tag_check.json and tag_check.md")
    ap.add_argument("--ocr", choices=("off", "auto"), default="off",
                    help="auto: OCR hints (never verified tags) for pages without a text layer, when Tesseract is "
                         "installed; off (default): those pages are only reported as needing OCR")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        ap.exit(2, f"{out} is not empty\n")
    try:
        result = check(a.bundle, a.pdf, [int(x) for x in a.pages.split(",")], ocr=a.ocr)
    except (ValueError, OSError, KeyError) as error:
        ap.exit(2, f"Tag check failed: {error}\n")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tag_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "tag_check.md").write_text(markdown(result), encoding="utf-8", newline="\n")
    if result.get("ocr", {}).get("unavailable"):
        print(result["ocr"]["unavailable"], file=sys.stderr)
    for e in result.get("ocr", {}).get("errors", []):
        print(f"OCR hints not made for sheet {e['sheet']} (page {e['page']}): {e['error']}", file=sys.stderr)
    for s in result["sheets"]:
        hint = s.get("ocr_hints")
        print(f"sheet {s['sheet']} (page {s['page']}): " + (
            f"{len(s['matched'])} matched, {len(s['missed_by_reader'])} missed by reader, "
            f"{len(s['not_in_text_layer'])} not in text layer" if s["checked"] else "not checked (needs OCR)" + (
                f"; {hint['hints']} OCR hints, {len(hint['hint_matches_extracted'])} agreeing with extracted tags "
                "(hints, not verified)" if hint else "")))
    print(f"wrote {out / 'tag_check.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
