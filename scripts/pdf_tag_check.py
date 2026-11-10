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

Usage:
    python scripts/pdf_tag_check.py --bundle work/plant/bundle --pdf drawing.pdf --pages 21 --out work/plant/tag-check
    python scripts/pdf_tag_check.py --bundle work/plant/set-bundle --pdf set.pdf --pages 13,21,22 --out ...
"""
import argparse
import json
from pathlib import Path
import re
import sys

LETTERS = re.compile(r"[A-Z]{2,5}")
NUMBER = re.compile(r"\d[\d,\s-]*[A-Z]?")
SINGLE = re.compile(r"[A-Z]{2,5}-?\d{2,7}[A-Z]?")  # one-letter forms (P-101) are skipped: they collide with drawing numbers
MIN_WORDS_FOR_TEXT_LAYER = 150  # Pahala: title-block-only pages carry 118-121 words, P&ID text pages 207-263
STOP = {"FOR", "REV", "NO", "DATE", "SHEET", "SHT", "OF", "DWG", "SCALE", "PAGE", "JOB", "SIZE", "NTS"}
MAX_NUMBER_WIDTH = 4.5  # a bubble's number line is at most this many letter-heights wide
TAG_GROUPS = ("units", "instruments", "line_items")


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


def drawing_tags(words):
    """Tags printed on a page: stacked instrument bubbles plus single-word tags. words are PyMuPDF
    get_text('words') tuples (x0, y0, x1, y1, text, ...). Returns {key: {"text", "box"}} in page units."""
    found = {}
    for w in words:
        text = w[4].upper()
        if LETTERS.fullmatch(text) and text not in STOP:
            c = number_below(w, words)
            if c and NUMBER.fullmatch(c[4].upper()):
                tag = f"{text} {c[4]}"
                found.setdefault(key(tag), {"text": tag, "box": [min(w[0], c[0]), w[1], max(w[2], c[2]), c[3]]})
        elif SINGLE.fullmatch(text):
            found.setdefault(key(text), {"text": w[4], "box": list(w[:4])})
    return found


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


def check(bundle, pdf, pages):
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
    for sheet, page in zip(sheets, pages):
        if not 1 <= page <= doc.page_count:
            raise ValueError(f"page {page} is outside the PDF (1 to {doc.page_count})")
        p = doc[page - 1]
        words = p.get_text("words")
        entry = compare(drawing_tags(words), model_tags(model, sheet), (p.rect.width, p.rect.height), len(words))
        result["sheets"].append({"sheet": sheet, "page": page, **entry})
    return result


def markdown(result):
    lines = [f"# Tag cross-check: {result['pdf']}", "",
             "Tags printed in the PDF's text layer compared with the tags the reader extracted. Every line is a "
             "review candidate: open the drawing at the box shown (0-1000 page coordinates).", ""]
    for s in result["sheets"]:
        lines.append(f"## Sheet {s['sheet']} (PDF page {s['page']})")
        if not s["checked"]:
            lines += ["", f"Not checked: {s['reason']}", ""]
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


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", required=True, help="a review bundle from import_site_drawing.py or import_drawing_set.py")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="1-based PDF page per bundle sheet, in sheet order, e.g. 13,21,22")
    ap.add_argument("--out", required=True, help="new or empty folder for tag_check.json and tag_check.md")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        ap.exit(2, f"{out} is not empty\n")
    try:
        result = check(a.bundle, a.pdf, [int(x) for x in a.pages.split(",")])
    except (ValueError, OSError, KeyError) as error:
        ap.exit(2, f"Tag check failed: {error}\n")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tag_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "tag_check.md").write_text(markdown(result), encoding="utf-8", newline="\n")
    for s in result["sheets"]:
        print(f"sheet {s['sheet']} (page {s['page']}): " + (
            f"{len(s['matched'])} matched, {len(s['missed_by_reader'])} missed by reader, "
            f"{len(s['not_in_text_layer'])} not in text layer" if s["checked"] else "not checked (needs OCR)"))
    print(f"wrote {out / 'tag_check.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
