"""Synthetic word-layout controls for pdf_tag_check.py; no public data or model calls. The PDF-level tests skip
without PyMuPDF; the OCR end-to-end test skips without the Tesseract program."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pdf_tag_check as t


def word(x0, y0, text, w=None, h=10):
    return (x0, y0, x0 + (w if w is not None else 6 * len(text)), y0 + h, text)


def bubble(x, y, letters, number_words):
    """Letters centred over a number line, as CAD exports an ISA bubble."""
    words = [word(x - 3 * len(letters), y, letters)]
    widths = [6 * len(n) for n in number_words]
    left = x - (sum(widths) + 3 * (len(number_words) - 1)) / 2
    for n, wd in zip(number_words, widths):
        words.append(word(left, y + 13, n))
        left += wd + 3
    return words


def model(*tags, sheet="0"):
    return {"instruments": [{"id": f"S{sheet}-IN{i:03d}", "tag": tag,
                             "provenance": [{"sheet": sheet, "box_0_1000": [0, 0, 1, 1]}]} for i, tag in enumerate(tags)]}


FILLER = [word(10 * i, 900, "NOTE") for i in range(160)]  # enough words to count as a usable text layer


class TagCheck(unittest.TestCase):
    def test_stacked_bubbles_are_joined_and_neighbours_stay_apart(self):
        words = bubble(100, 100, "ZSO", ["500,", "101"]) + bubble(128, 100, "ZSC", ["500,", "101"]) \
            + bubble(300, 100, "LI", ["401"])
        found = {v["text"] for v in t.drawing_tags(words).values()}
        self.assertEqual(found, {"ZSO 500, 101", "ZSC 500, 101", "LI 401"})

    def test_single_word_tags_and_title_block_words(self):
        words = [word(100, 100, "FIT-403"), word(200, 100, "MB-01"), word(300, 100, "PMP-080101")] + bubble(400, 100, "FOR", ["2021"]) \
            + [word(500, 100, "P-204")]
        self.assertEqual(set(t.drawing_tags(words)), {"FIT403", "MB01", "PMP080101"})

    def test_compare_lists_misses_and_possible_misreads_and_ignores_descriptive_labels(self):
        words = bubble(100, 100, "LI", ["401"]) + bubble(200, 100, "LAH", ["402"]) + FILLER
        extracted = t.model_tags(model("LI-401", "LAH 420", "TANK", "M"), "0")
        r = t.compare(t.drawing_tags(words), extracted, (1000, 1000), len(words))
        self.assertTrue(r["checked"])
        self.assertEqual(r["matched"], ["LI 401"])
        self.assertEqual([x["tag"] for x in r["missed_by_reader"]], ["LAH 402"])
        self.assertEqual([x["tag"] for x in r["not_in_text_layer"]], ["LAH 420"])

    def test_page_without_a_text_layer_is_not_checked(self):
        words = bubble(100, 100, "LI", ["401"])
        r = t.compare(t.drawing_tags(words), t.model_tags(model("PT 101"), "0"), (1000, 1000), len(words))
        self.assertFalse(r["checked"])
        self.assertIn("needs OCR", r["reason"])
        self.assertNotIn("not_in_text_layer", r)

    def test_tags_compare_on_letters_and_digits_only(self):
        self.assertEqual(t.key("LI 401"), t.key("li-401"))
        self.assertEqual(t.key("ZIO 500, 101"), t.key("ZIO 500,101"))
        self.assertNotEqual(t.key("LI 401"), t.key("LI 410"))

    def test_markdown_reports_unchecked_pages_plainly(self):
        result = {"pdf": "set.pdf", "sheets": [
            {"sheet": "0", "page": 13, "checked": False, "reason": "no usable text layer (118 words)"},
            {"sheet": "1", "page": 21, "checked": True, "matched": ["LI 401"], "missed_by_reader": [],
             "not_in_text_layer": []}]}
        text = t.markdown(result)
        self.assertIn("Not checked: no usable text layer (118 words)", text)
        self.assertIn("1 matched · 0 on the drawing but not extracted", text)


def ocr_word(x0, y0, text, conf, h=10):
    return (x0, y0, x0 + 6 * len(text), y0 + h, text, conf)


TEXT_LAYER_KEYS = {"matched", "missed_by_reader", "not_in_text_layer"}


class OcrHints(unittest.TestCase):
    """OCR hints stay hints: separate lists, the page stays not checked, confidence and box kept."""

    def test_hints_carry_the_lowest_word_confidence_and_a_page_box(self):
        words = [ocr_word(100, 100, "LI", 91.0), ocr_word(97, 113, "401", 72.5), ocr_word(300, 100, "FIT-403", 88.0)]
        hints = t.hints_from_words(words, 72, (1000, 500))
        self.assertEqual(set(hints), {"LI401", "FIT403"})
        self.assertEqual(hints["LI401"]["confidence"], 72.5)
        self.assertEqual(hints["LI401"]["ocr_text"], "LI 401")
        self.assertEqual(hints["LI401"]["box_0_1000"], [97.0, 200.0, 115.0, 246.0])  # y scaled by the page height

    def test_hint_lists_never_use_the_text_layer_names_and_the_page_stays_unchecked(self):
        words = bubble(100, 100, "LI", ["401"])  # too few words: no text layer
        extracted = t.model_tags(model("LI-401", "PT 101"), "0")
        entry = t.compare(t.drawing_tags(words), extracted, (1000, 1000), len(words))
        hints = t.hints_from_words([ocr_word(100, 100, "LI", 90), ocr_word(100, 113, "401", 90),
                                    ocr_word(300, 100, "LAH", 40), ocr_word(300, 113, "402", 40)], 72, (1000, 1000))
        entry["ocr_hints"] = t.compare_hints(hints, extracted, {"dpi": 72})
        self.assertFalse(entry["checked"])
        self.assertFalse(TEXT_LAYER_KEYS & set(entry))
        o = entry["ocr_hints"]
        self.assertIn("not verified", o["label"])
        self.assertEqual([x["tag"] for x in o["hint_matches_extracted"]], ["LI 401"])
        self.assertEqual([x["tag"] for x in o["hint_not_extracted"]], ["LAH 402"])
        self.assertEqual([x["tag"] for x in o["extracted_without_hint"]], ["PT 101"])
        text = t.markdown({"pdf": "scan.pdf", "sheets": [{"sheet": "0", "page": 1, **entry}]})
        self.assertIn("Not checked: no usable text layer", text)
        self.assertIn("OCR hints (not verified tags)", text)
        self.assertNotIn(" matched · ", text)  # the text-layer summary line never appears for a hint page

    def test_tesseract_tsv_is_read_with_boxes_padded_and_scaled_back(self):
        tsv = ("level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
               "1\t1\t0\t0\t0\t0\t0\t0\t600\t400\t-1\t\n"
               "5\t1\t1\t1\t1\t1\t60\t40\t30\t20\t95.5\tFIC\n"
               "5\t1\t1\t1\t1\t2\t90\t40\t30\t20\t12.0\t \n")
        self.assertEqual(t.parse_tsv(tsv, 2.0), [(30.0, 17.5, 45.0, 32.5, "FIC", 95.5)])

    def test_default_output_has_no_ocr_fields_and_a_missing_engine_changes_no_sheet(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("SKIP PyMuPDF not installed")
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp, "bundle")
            bundle.mkdir()
            (bundle / "plant_model.json").write_text(json.dumps({"systems": [{"sheet": "0"}], **model("LI 401")}))
            doc = pymupdf.open()
            doc.new_page().insert_text((100, 100), "LI")  # a page with almost no text: needs OCR
            pdf = os.path.join(tmp, "p.pdf")
            doc.save(pdf)
            off = t.check(bundle, pdf, [1])
            self.assertNotIn("ocr", off)
            self.assertEqual(set(off["sheets"][0]), {"sheet", "page", "checked", "reason", "words"})
            with mock.patch("extract_text._tesseract", return_value=None):
                missing = t.check(bundle, pdf, [1], ocr="auto")
            self.assertEqual(missing["sheets"], off["sheets"])
            self.assertIn("tesseract", missing["ocr"]["unavailable"])
            self.assertEqual(t.markdown(missing), t.markdown(off))
            with mock.patch.object(t, "ocr_engine", return_value=("tesseract", "5", None)),                     mock.patch.object(t, "page_hints", side_effect=ValueError("tesseract could not read the page")):
                failed = t.check(bundle, pdf, [1], ocr="auto")
            self.assertEqual(failed["sheets"], off["sheets"])  # a failed OCR run leaves the page as "needs OCR"
            self.assertEqual(failed["ocr"]["errors"][0]["error"], "ValueError: tesseract could not read the page")
            self.assertTrue(missing["ocr"]["unavailable"].startswith("OCR hints not made: no tesseract program found"))
            for crash in (MemoryError("render too large"), RuntimeError("cv2.error: resize failed")):
                with mock.patch.object(t, "ocr_engine", return_value=("tesseract", "5", None)),                         mock.patch.object(t, "page_hints", side_effect=crash):
                    crashed = t.check(bundle, pdf, [1], ocr="auto")
                self.assertEqual(crashed["sheets"], off["sheets"])  # the run completes; the page stays "needs OCR"
                self.assertEqual(crashed["ocr"]["errors"][0]["error"], f"{type(crash).__name__}: {crash}")


class RenderResolution(unittest.TestCase):
    def test_a_rotated_scan_is_rendered_at_its_own_resolution(self):
        try:
            import pymupdf
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("SKIP PyMuPDF/NumPy not installed")
        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "wide.png")
            pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 400, 200), False).save(png)  # 400 x 200 px
            doc = pymupdf.open()
            page = doc.new_page(width=100, height=200)  # placed turned a quarter: 200 pt tall for the 400 px side
            page.insert_image(page.rect, filename=png, rotate=90)
            gray, dpi = t.render_page(page)
            doc.close()
        self.assertAlmostEqual(dpi, 144, delta=1)  # 400 px over 200 pt, not 400 px over 100 pt
        self.assertEqual(gray.shape[1], 200)


def tesseract_found():
    try:
        return bool(t.ocr_engine()[0])
    except Exception:
        return False


@unittest.skipUnless(tesseract_found(), "SKIP Tesseract (or NumPy/OpenCV) not installed: OCR hint end-to-end test")
class OcrHintsWithTesseract(unittest.TestCase):
    def test_an_image_only_page_gets_hints_and_stays_not_checked(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as tmp:
            text_pdf = pymupdf.open()
            page = text_pdf.new_page(width=400, height=300)
            page.draw_circle((100, 100), 22)
            page.insert_text((93, 97), "LI", fontsize=10)
            page.insert_text((90, 110), "401", fontsize=10)
            page.insert_text((240, 200), "FIT-403", fontsize=10)
            png = os.path.join(tmp, "scan.png")
            page.get_pixmap(dpi=200).save(png)
            scan = pymupdf.open()
            scan.new_page(width=400, height=300).insert_image(pymupdf.Rect(0, 0, 400, 300), filename=png)
            pdf = os.path.join(tmp, "scan.pdf")
            scan.save(pdf)
            bundle = Path(tmp, "bundle")
            bundle.mkdir()
            (bundle / "plant_model.json").write_text(json.dumps({"systems": [{"sheet": "0"}], **model("LI-401", "PT 9")}))
            r = t.check(bundle, pdf, [1], ocr="auto")
        s = r["sheets"][0]
        self.assertFalse(s["checked"])
        self.assertFalse(TEXT_LAYER_KEYS & set(s))
        self.assertTrue(r["ocr"]["engine"].startswith("tesseract"))
        o = s["ocr_hints"]
        self.assertEqual([x["tag"] for x in o["hint_matches_extracted"]], ["LI 401"])
        self.assertIn("FIT403", [t.key(x["tag"]) for x in o["hint_not_extracted"]])
        for x in o["hint_matches_extracted"] + o["hint_not_extracted"]:
            self.assertTrue(0 <= x["confidence"] <= 100)
            self.assertEqual(len(x["box_0_1000"]), 4)


if __name__ == "__main__":
    unittest.main()
