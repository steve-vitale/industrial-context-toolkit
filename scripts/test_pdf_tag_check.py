"""Synthetic word-layout controls for pdf_tag_check.py; no PDF library, public data or model calls."""
import unittest

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
        words = [word(100, 100, "FIT-403"), word(200, 100, "MB-01")] + bubble(400, 100, "FOR", ["2021"]) \
            + [word(500, 100, "P-204")]
        self.assertEqual(set(t.drawing_tags(words)), {"FIT403", "MB01"})

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


if __name__ == "__main__":
    unittest.main()
