"""Original-source and explicit-interpretation checks for the context intake."""
import csv
import io
import unittest
import tempfile
from pathlib import Path

import context_basis as cb
import context_intake as ci
import context_packet as cp


def contributions(value, quote, kind="number"):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=["Subject", "Predicate", "Source", "Locator",
                                             "Quote", "Value", "Type"], lineterminator="\n")
    writer.writeheader()
    writer.writerow({"Subject": "X/U/P", "Predicate": "value", "Source": "S", "Locator": "line 1",
                     "Quote": quote, "Value": value, "Type": kind})
    return text.getvalue().encode("utf-8")


def source_basis(raw):
    b = cb.Builder("X")
    b.source("S", "1", cb.raw_sha(raw), path="source.txt")
    b.entity("X/U/P", "P", "X/U")
    return b.finish()


class IntakeReviewRegressions(unittest.TestCase):
    def test_numeric_contribution_must_not_silently_round(self):
        for token in ("1e-999", "9007199254740993.0"):
            with self.subTest(token=token):
                original = (token + "\n").encode("utf-8")
                with self.assertRaisesRegex(cb.ContextError, "lossy numeric"):
                    ci.add_contributions(source_basis(original), {"source.txt": original},
                                         contributions(token, token))

    def test_quotation_must_match_declared_original_bytes(self):
        real, forged = b"REAL SOURCE\n", b"FORGED SOURCE\n"
        with self.assertRaisesRegex(cb.ContextError, "raw-byte binding mismatch"):
            ci.add_contributions(source_basis(real), {"source.txt": forged},
                                 contributions("An interpretation", "FORGED SOURCE", "text"))

    def test_open_order_physical_item_is_not_a_reported_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "work.csv").write_bytes(b"Area,Equipment,Order,Closed,Installed Item ID,Installed Serial\nU,P-1,WO-2,,FUTURE-ID,FUTURE-SERIAL\n")
            basis, _, _ = ci.prepare(root, "X", "P1")
            self.assertFalse([r for r in basis["relationships"] if r["predicate"] == "reported_installation_at"])
            self.assertFalse([e for e in basis["entities"] if e["identity_role"] == "physical_item"])
            self.assertTrue(any(r["value"] == "FUTURE-SERIAL" and r["predicate"] == "proposed_serial_number"
                                for r in basis["claims"]))


class IntakeDialectRegressions(unittest.TestCase):
    def test_consumed_second_dialect_retains_closed_and_open_work_records(self):
        # This genuine failed transfer case is DEVELOPMENT, never a new transfer pass.
        records = (Path(__file__).resolve().parents[1] / "examples/map-component-cycle/inputs/"
                   "procedural-transfers/second-record-dialect-01/records/r1")
        basis, originals, mappings = ci.prepare(records, "DIALECT2", "P2", date_format="DMY")
        self.assertEqual(sorted(e["tag"] for e in basis["entities"] if e["identity_role"] == "physical_item"),
                         ["BODY-E1", "BODY-E2", "BODY-W1"])
        self.assertEqual(sorted(e["tag"] for e in basis["entities"] if e["identity_role"] == "maintenance_record"),
                         ["WO-E-01", "WO-E-02"])
        self.assertEqual(mappings["WO-D2"]["delimiter"], ";")
        self.assertTrue(any(c["predicate"] == "closed_on" and c["value"] == "2026-11-05" for c in basis["claims"]))
        self.assertTrue(any(c["predicate"] == "proposed_serial_number" and c["value"] == "00019" for c in basis["claims"]))
        for name, raw in originals.items():
            self.assertEqual(raw, (records / name).read_bytes())
        source = next(c for c in basis["claims"] if c["source"] == "WO-D2" and c["value"] == "00018")
        self.assertEqual(source["locator"], "CSV record 2; physical lines 2-2; column Installed Serial")

    def test_four_delimiters_preserve_quoted_separators_and_blank_cells(self):
        for delimiter in (",", ";", "\t", "|"):
            with self.subTest(delimiter=delimiter):
                text = io.StringIO(newline="")
                writer = csv.writer(text, delimiter=delimiter, lineterminator="\r\n")
                writer.writerows([["Area", "Equipment", "Memo", "Unused"],
                                  ["U", "Q", "quoted" + delimiter + "cell", ""], ["U", "R", "plain", ""]])
                fields, rows, actual = ci.csv_rows(text.getvalue().encode())
                self.assertEqual(actual, delimiter)
                self.assertEqual(fields, ["Area", "Equipment", "Memo", "Unused"])
                self.assertEqual(rows[0], ({"Area": "U", "Equipment": "Q", "Memo": "quoted" + delimiter + "cell", "Unused": ""}, 2, 2, 2))
                self.assertEqual(rows[1][0]["Unused"], "")

    def test_multiline_crlf_quoted_field_keeps_physical_line_locators(self):
        raw = b'Area;Equipment;Memo\r\nU;Q;"first;line\r\nsecond line"\r\nU;R;plain\r\n'
        fields, rows, delimiter = ci.csv_rows(raw)
        self.assertEqual(delimiter, ";")
        self.assertEqual(rows[0], ({"Area": "U", "Equipment": "Q", "Memo": "first;line\r\nsecond line"}, 2, 2, 3))
        self.assertEqual(rows[1][1:], (3, 4, 4))

    def test_ambiguous_valid_delimiters_request_explicit_source_choice(self):
        with self.assertRaisesRegex(cb.ContextError, "CSV delimiter ambiguous"):
            ci.csv_rows(b"Area;Equipment,Detail\nU;P-9,part\n")

    def test_existing_source_mapping_delimiter_replays_ambiguous_csv_in_packet(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); records = root / "records"; records.mkdir()
            raw = b"Area;Equipment,Detail\r\nU;P-9,part\r\n"
            (records / "asset.csv").write_bytes(raw)
            mapping = {"asset.csv": {"headers": ["Area", "Equipment,Detail"],
                       "mapping": {"Area": "unit", "Equipment,Detail": "tag"}, "delimiter": ";"}}
            path = root / "mapping.json"; path.write_bytes(cp.encode(mapping))
            packet = cp.prepare(records, root / "packet", "X", "P1", mapping=path)
            opened = cp.open_packet(packet)
            self.assertEqual(opened["basis"]["entities"][0]["tag"], "P-9,part")
            self.assertEqual((packet / "originals/asset.csv").read_bytes(), raw)
            self.assertEqual(cb.read_json(packet / "mappings.json")["asset.csv"]["delimiter"], ";")
            successor = cp.prepare(records, root / "next", "X", "P1", previous=packet)
            self.assertEqual(cb.read_json(successor / "mappings.json"), cb.read_json(packet / "mappings.json"))
            self.assertEqual(cp.open_packet(successor)["basis"], opened["basis"])

    def test_crosswalk_reuses_its_existing_source_delimiter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "equipment.csv").write_bytes(b"Equipment,Area\nQ,U\n")
            raw = b"Position;Area;Alias;Meta,Note\nQ;U;A;one,two\n"
            (root / "crosswalk.csv").write_bytes(raw)
            saved = {"crosswalk.csv": {"mode": "source_bound_identity_crosswalk",
                     "headers": ["Position", "Area", "Alias", "Meta,Note"], "delimiter": ";",
                     "encoding": "utf-8-sig", "unmapped_columns": ["Meta,Note"]}}
            basis, originals, mappings = ci.prepare(root, "X", "P1", previous_mapping=saved,
                                                   identity_crosswalk="crosswalk.csv")
            self.assertEqual(cb.View(basis).resolve("A"), "X/P1/U/Q")
            self.assertEqual(originals["crosswalk.csv"], raw)
            self.assertEqual(mappings["crosswalk.csv"]["delimiter"], ";")

    def test_malformed_multicolumn_rows_and_quotes_do_not_collapse_to_one_header(self):
        for raw in [b"Area;Equipment\nU;Q;extra\n", b'Area;Equipment\nU;"unterminated\n']:
            with self.subTest(raw=raw), self.assertRaises(cb.ContextError):
                ci.csv_rows(raw)

    def test_invalid_saved_delimiters_are_rejected_as_mapping_clarification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "a.csv").write_bytes(b"Area,Equipment\nU,Q\n")
            for delimiter in (None, False, 1, "", "||", " "):
                with self.subTest(delimiter=delimiter), self.assertRaisesRegex(cb.ContextError, "saved source delimiter"):
                    ci.prepare(root, "X", "P1", previous_mapping={"a.csv": {
                        "headers": ["Area", "Equipment"], "mapping": {"Area": "unit", "Equipment": "tag"},
                        "delimiter": delimiter}})

    def test_genuine_single_column_csv_remains_retained_without_inferred_fields(self):
        fields, rows, delimiter = ci.csv_rows(b'Note\r\n"one; note,with|separators"\r\n')
        self.assertEqual(fields, ["Note"])
        self.assertEqual(rows[0][0], {"Note": "one; note,with|separators"})
        self.assertEqual(delimiter, ",")


if __name__ == "__main__":
    unittest.main()
