"""The context-map-1 drafts parse and agree with each other (standard library only).

Checks schemas/context-map/: the JSON Schema, the register catalogue (registers.json), every CSV template, the
standards-mapping table and the fictional example map. The local validator (scripts/context_map.py) covers the JSON
Schema keywords the draft uses, so no third-party package is needed; if `jsonschema` happens to be installed it is
used as well.
"""
import copy
import csv
import io
import json
import re
import unittest
from pathlib import Path

from context_map import validate  # the format's own validator (scripts/context_map.py)

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "schemas" / "context-map"
SCHEMA = DIR / "context-map-1.schema.json"
REGISTERS = DIR / "registers.json"
MAPPING = DIR / "standards-mapping.csv"
EXAMPLE = DIR / "example-map.json"
DOC = ROOT / "docs" / "CONTEXT_MAP_FORMAT.md"
CLASSES = DIR / "classes.json"
RELATIONS = DIR / "relations.json"
RULES = DIR / "templates" / "expectations.json"

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    text = path.read_text(encoding="utf-8")
    return list(csv.reader(io.StringIO(text)))


# Relation names frozen in context-map-1 (decided 2026-11-04). Renaming or removing one needs context-map-2.
FROZEN_RELATIONS = {"contains", "piped_to", "measures", "controls", "sets_point_of", "acts_on", "protects", "signal_to",
                    "actuated_by", "nozzle_of", "references", "member_of",
                    "network_member"}  # appended in 1.2
FROZEN_DOCUMENT_RELATIONS = {"covers", "mentions", "based_on"}
# Example tags every new register template draws on (the HTST pasteurizer unit PAST1).
PASTEURIZER_TAGS = {"P-101", "TT-2207", "FDV-2210", "HT-100"}
UOM = re.compile(r"^([a-z0-9_]+)(?:\[([^\[\]]+)\])?$")


def row_errors(register, row, where):
    """Errors in one register row given as {field: text}, by the rules of registers.json."""
    errors = []
    fields = {f["name"]: f for f in register["fields"]}
    for name in row:
        if name not in fields:
            errors.append(f"{where}: unknown column {name}")
    for name, f in fields.items():
        value = row.get(name, "")
        if f["required"] is True and not value.strip():
            errors.append(f"{where}: required {name} empty")
        if not value:
            continue
        if value != value.strip():
            errors.append(f"{where}: {name} has surrounding space")
        if f["type"] == "enum" and value not in f["values"]:
            errors.append(f"{where}: {name}={value!r} not in {f['values']}")
        elif f["type"] == "date" and not DATE.match(value):
            errors.append(f"{where}: {name}={value!r} is not a date")
        elif f["type"] == "number":
            try:
                float(value)
            except ValueError:
                errors.append(f"{where}: {name}={value!r} is not a number")
        elif f["type"] == "bool" and value not in ("yes", "no"):
            errors.append(f"{where}: {name}={value!r} is not yes/no")
    return errors


def wide_to_long(form, wide_cfg, path_rows):
    """The documented wide -> long datasheet conversion (registers.json datasheet_wide_forms.conversion)."""
    header, body = path_rows[0], path_rows[1:]
    ident, trailing = wide_cfg["identity_columns"], wide_cfg["trailing_columns"]
    kinds = {p["name"]: p["fact_kind"] for p in form["properties"]}
    long_rows = []
    for n, row in enumerate(body, 2):
        cells = dict(zip(header, row))
        for col in header:
            if col in ident or col in trailing or not cells.get(col):
                continue
            m = UOM.match(col)
            assert m, f"bad property header {col!r}"
            prop, uom = m.group(1), m.group(2) or ""
            long_rows.append({
                "tag": cells.get("tag", ""), "plant": cells.get("plant", ""), "unit": cells.get("unit", ""),
                "property": prop, "value": cells[col], "uom": uom, "fact_kind": kinds.get(prop, ""),
                "sheet_type": form["sheet_type"], "document": cells.get("document", ""),
                "revision": cells.get("revision", ""), "cfihos_property": "",
                "locator": f"{cells.get('locator') or f'row {n}'}; column {col}",
                "status": cells.get("status", ""), "note": cells.get("note", "")})
    return long_rows


def _covers(source_scopes, scope):
    return any(scope == s or scope.startswith(s + "/") for s in source_scopes)


def record_type_present(rec, scope, m):
    """registers.json authority_rule: is this record type the record for this scope in map m?"""
    rows_by_source = {}
    for rid, rows in m.get("records", {}).items():
        for row in rows:
            rows_by_source.setdefault(row["source"], []).append((rid, row))
    want = "datasheet" if rec == "instrument_spec_sheet" else rec
    for s in m.get("sources", []):
        if s["record_type"] != want:
            continue
        rows = rows_by_source.get(s["id"], [])
        scopes = s.get("scopes") or sorted({r["item"].rsplit("/", 1)[0] for _, r in rows if "item" in r})
        if not _covers(scopes, scope):
            continue
        if rec == "instrument_spec_sheet":
            def sheet_type(row):
                v = row["values"].get("sheet_type")
                return v["value"] if isinstance(v, dict) else v
            if not any(rid == "datasheet" and sheet_type(r) == "instrument_spec_sheet" for rid, r in rows):
                continue
        return True
    return False


def authority_for(kind, scope, m, catalogue):
    """First record type in the ordered authority list that is present for the scope; None = authority gap."""
    order = m.get("settings", {}).get("authority", {}).get(kind, catalogue["default_authority"].get(kind, []))
    if isinstance(order, str):
        order = [order]
    for rec in order:
        if record_type_present(rec, scope, m):
            return rec
    return None


class ContextMapFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load(SCHEMA)
        cls.catalogue = load(REGISTERS)
        cls.registers = {r["id"]: r for r in cls.catalogue["registers"]}
        cls.example = load(EXAMPLE)

    # ---------------------------------------------------------------- schema
    def test_schema_is_draft_2020_12_and_every_ref_resolves(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        refs = re.findall(r'"\$ref": "#/\$defs/([A-Za-z0-9_]+)"', SCHEMA.read_text(encoding="utf-8"))
        self.assertTrue(refs)
        missing = sorted(set(refs) - set(self.schema["$defs"]))
        self.assertEqual(missing, [], "unresolved $ref")

    def test_schema_register_names_match_the_catalogue(self):
        names = self.schema["$defs"]["RecordsLayer"]["propertyNames"]["enum"]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(self.registers))

    # ---------------------------------------------------------------- registers and templates
    def test_register_ids_unique_and_complete(self):
        ids = [r["id"] for r in self.catalogue["registers"]]
        self.assertEqual(len(ids), len(set(ids)))
        for r in self.catalogue["registers"]:
            for key in ("name", "layer", "department", "default_owner", "authority_for", "key", "template", "fields"):
                self.assertIn(key, r, f"{r['id']} lacks {key}")
            self.assertIn(r["layer"], ("plant", "records", "documents", "decisions"))
            self.assertIn(r["department"], self.catalogue["departments"])
            names = [f["name"] for f in r["fields"]]
            self.assertEqual(len(names), len(set(names)), f"{r['id']}: duplicate field")
            self.assertTrue(set(r["key"]) <= set(names), f"{r['id']}: key not in fields")
            words = re.findall(r"[a-z]+", r["name"].lower())
            for i, w in enumerate(words):  # never a bare "list": always a named record (loop list, line list...)
                if w == "list":
                    self.assertTrue(i > 0 and words[i - 1] in ("loop", "line", "alarm", "interlock", "io"),
                                    f"{r['id']}: use an explicit record name")

    def test_every_template_matches_its_register_column_for_column(self):
        for rid, r in self.registers.items():
            path = DIR / r["template"]
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), f"{path.name}: BOM")
            rows = read_csv(path)
            header = rows[0]
            self.assertEqual(header, [f["name"] for f in r["fields"]], f"{path.name}: header differs from registers.json")
            examples = rows[1:]
            self.assertTrue(1 <= len(examples) <= 4, f"{path.name}: needs one to four example rows")
            for n, row in enumerate(examples, 2):
                where = f"{path.name} line {n}"
                self.assertEqual(len(row), len(header), f"{where}: column count")
                self.assertEqual(row_errors(r, dict(zip(header, row)), where), [])

    def test_no_stray_templates(self):
        expected = {Path(r["template"]).name for r in self.registers.values()}
        present = {p.name for p in (DIR / "templates").glob("*.csv")}
        self.assertEqual(present, expected)

    def test_authority_map_points_at_real_record_types(self):
        record_types = set(self.registers) | set(self.catalogue["pseudo_record_types"])
        authority = self.catalogue["default_authority"]
        for kind, order in authority.items():
            self.assertIsInstance(order, list, f"authority {kind} must be an ordered list")
            self.assertTrue(order, f"authority {kind} is empty")
            self.assertEqual(len(order), len(set(order)), f"authority {kind} repeats a record type")
            for rec in order:
                self.assertIn(rec, record_types, f"authority {kind} -> {rec}")
        used = {f["fact_kind"] for r in self.registers.values() for f in r["fields"] if "fact_kind" in f}
        self.assertEqual(sorted(used - set(authority)), [], "fact kind without an authority entry")
        for rid, r in self.registers.items():
            for kind in r["authority_for"]:
                self.assertIn(rid, authority.get(kind, []), f"{rid} claims authority for {kind}")
        for kind, order in authority.items():
            for rec in order:
                if rec in self.registers:
                    self.assertIn(kind, self.registers[rec]["authority_for"], f"{rec} not marked for {kind}")
        # the decided defaults
        for kind, rec in {"connectivity": ["pid"], "tags": ["pid"], "rating": ["datasheet"], "size": ["datasheet"],
                          "material": ["datasheet"],
                          "instrument_range": ["instrument_spec_sheet", "instrument_index"],
                          "instrument_model": ["instrument_spec_sheet", "instrument_index"],
                          "installed": ["maintenance_export"], "ccp_limit": ["ccp"], "isolation": ["isolation_point"],
                          "corrective_action": ["capa"], "criticality": ["criticality_ranking"],
                          "inspection_status": ["inspection_record"]}.items():
            self.assertEqual(authority[kind], rec, kind)
        self.assertIn("first record type", self.catalogue["authority_rule"])

    def test_instrument_authority_spec_sheet_first_then_instrument_index(self):
        """Decision 3: the instrument spec sheet wins where the site supplies one for that scope, else the index."""
        past1, cip = "S1/P1/PAST1", "S1/P1/CIP1"
        base = copy.deepcopy(self.example)
        base["sources"].append({"id": "IDX-P1", "record_type": "instrument_index", "scopes": ["S1/P1"]})
        for kind in ("instrument_range", "instrument_model"):
            # the example supplies a spec sheet for PAST1 with an instrument_spec_sheet row
            self.assertEqual(authority_for(kind, past1, base, self.catalogue), "instrument_spec_sheet", kind)
            # another unit of the plant has no spec sheet: the instrument index is the authority there
            self.assertEqual(authority_for(kind, cip, base, self.catalogue), "instrument_index", kind)
        # spec sheet source present but holding only equipment datasheet rows: not a spec sheet
        equip = copy.deepcopy(base)
        for row in equip["records"]["datasheet"]:
            row["values"]["sheet_type"] = "equipment_datasheet"
        self.assertEqual(authority_for("instrument_range", past1, equip, self.catalogue), "instrument_index")
        # spec sheet rows removed: falls through to the instrument index
        no_sheet = copy.deepcopy(base)
        del no_sheet["records"]["datasheet"]
        self.assertEqual(authority_for("instrument_range", past1, no_sheet, self.catalogue), "instrument_index")
        # neither supplied: no authority (a disagreement there is an authority_gap)
        neither = copy.deepcopy(no_sheet)
        neither["sources"] = [s for s in neither["sources"] if s["id"] != "IDX-P1"]
        self.assertIsNone(authority_for("instrument_range", past1, neither, self.catalogue))
        # a source with no declared scopes is the record for the scopes of the items its rows resolve to
        unscoped = copy.deepcopy(base)
        for s in unscoped["sources"]:
            if s["id"] == "IS-TT2207":
                s.pop("scopes")
        self.assertEqual(authority_for("instrument_range", past1, unscoped, self.catalogue), "instrument_spec_sheet")
        self.assertEqual(authority_for("instrument_range", cip, unscoped, self.catalogue), "instrument_index")
        # a site override (string or list) replaces the default order and still validates
        for override in ("instrument_index", ["instrument_index", "instrument_spec_sheet"]):
            site = copy.deepcopy(base)
            site.setdefault("settings", {})["authority"] = {"instrument_range": override}
            site["settings"]["authority_reasons"] = {"instrument_range": "Site keeps ranges in the index."}
            self.assertEqual(validate(site, self.schema, self.schema), [])
            self.assertEqual(authority_for("instrument_range", past1, site, self.catalogue), "instrument_index")
        bad = copy.deepcopy(base)
        bad.setdefault("settings", {})["authority"] = {"instrument_range": []}
        self.assertTrue(validate(bad, self.schema, self.schema), "empty authority list must be refused")

    # ---------------------------------------------------------------- wide-form datasheets
    def test_wide_datasheet_templates_convert_to_valid_long_rows(self):
        wide = self.catalogue["datasheet_wide_forms"]
        datasheet = self.registers["datasheet"]
        long_header = [f["name"] for f in datasheet["fields"]]
        forms = {f["id"]: f for f in wide["forms"]}
        for needed in ("pump", "heat_exchanger", "vessel_tank", "control_valve", "transmitter", "relief_valve"):
            self.assertIn(needed, forms)
        sheet_types = next(f for f in datasheet["fields"] if f["name"] == "sheet_type")["values"]
        kinds = next(f for f in datasheet["fields"] if f["name"] == "fact_kind")["values"]
        self.assertEqual(wide["identity_columns"][:3], ["tag", "plant", "unit"])
        self.assertEqual(wide["trailing_columns"], ["locator", "status", "note"])
        self.assertEqual(set(wide["identity_columns"] + wide["trailing_columns"]) - set(long_header), set())
        for fid, form in forms.items():
            self.assertIn(form["sheet_type"], sheet_types, fid)
            path = DIR / form["template"]
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"), f"{path.name}: BOM")
            rows = read_csv(path)
            props = [p["name"] + (f"[{p['uom']}]" if p.get("uom") else "") for p in form["properties"]]
            self.assertEqual(rows[0], wide["identity_columns"] + props + wide["trailing_columns"], fid)
            names = [p["name"] for p in form["properties"]]
            self.assertEqual(len(names), len(set(names)), f"{fid}: duplicate property")
            for p in form["properties"]:
                self.assertRegex(p["name"], r"^[a-z0-9_]+$", fid)
                self.assertIn(p["fact_kind"], kinds, f"{fid}.{p['name']}")
            self.assertTrue(1 <= len(rows) - 1 <= 4, f"{fid}: needs one to four example rows")
            filled = sum(1 for row in rows[1:] for col, v in zip(rows[0], row)
                         if v and col not in wide["identity_columns"] + wide["trailing_columns"])
            long_rows = wide_to_long(form, wide, rows)
            self.assertEqual(len(long_rows), filled, f"{fid}: one long row per filled property cell")
            self.assertTrue(long_rows, fid)
            for i, lr in enumerate(long_rows):
                self.assertEqual(list(lr), long_header, f"{fid}: long row columns")
                self.assertEqual(row_errors(datasheet, lr, f"{fid} long row {i}"), [])
            # deterministic: same input, same output
            self.assertEqual(wide_to_long(form, wide, rows), long_rows)
        # one worked case, end to end
        tt = wide_to_long(forms["transmitter"], wide, read_csv(DIR / forms["transmitter"]["template"]))
        low = next(r for r in tt if r["property"] == "range_low")
        self.assertEqual((low["tag"], low["value"], low["uom"], low["fact_kind"], low["sheet_type"], low["locator"]),
                         ("TT-2207", "0", "degC", "instrument_range", "instrument_spec_sheet",
                          "box 22; column range_low[degC]"))
        # an empty cell gives no row; an undefined extra column becomes a property with no fact kind
        pump_header, pump_row = read_csv(DIR / forms["pump"]["template"])[:2]
        header = pump_header + ["paint_colour"]
        body = ["" if col.startswith("speed") else v for col, v in zip(pump_header, pump_row)] + ["blue"]
        converted = wide_to_long(forms["pump"], wide, [header, body])
        self.assertNotIn("speed", {r["property"] for r in converted})
        paint = next(r for r in converted if r["property"] == "paint_colour")
        self.assertEqual((paint["value"], paint["fact_kind"], paint["uom"]), ("blue", "", ""))

    def test_no_stray_wide_templates(self):
        expected = {Path(f["template"]).name for f in self.catalogue["datasheet_wide_forms"]["forms"]}
        present = {p.name for p in (DIR / "templates" / "datasheet-wide").glob("*.csv")}
        self.assertEqual(present, expected)

    # ---------------------------------------------------------------- decided 2026-11-04
    def test_new_registers_capa_criticality_inspection(self):
        mapped = {row[1] for row in read_csv(MAPPING)[1:]}
        expect = {"capa": ("quality", "corrective_action"), "criticality_ranking": ("maintenance", "criticality"),
                  "inspection_record": ("maintenance", "inspection_status")}
        for rid, (dept, kind) in expect.items():
            r = self.registers[rid]
            self.assertEqual(r["department"], dept, rid)
            self.assertTrue(r["default_owner"], rid)
            self.assertEqual(r["authority_for"], [kind], rid)
            self.assertTrue(r["standards"], rid)
            self.assertIn(rid, mapped, f"{rid}: no standards-mapping row")
            self.assertIn(f"`{rid}`", DOC.read_text(encoding="utf-8"), f"{rid}: not defined in the spec")
            rows = read_csv(DIR / r["template"])
            header = rows[0]
            tags = {dict(zip(header, row)).get("tag") for row in rows[1:]}
            self.assertTrue(tags and tags <= PASTEURIZER_TAGS, f"{rid}: example tags {tags}")
        capa = {f["name"] for f in self.registers["capa"]["fields"]}
        self.assertTrue({"tag", "document"} <= capa, "a CAPA links by tag and by document")
        crit = read_csv(DIR / self.registers["criticality_ranking"]["template"])
        self.assertEqual({dict(zip(crit[0], r))["tag"] for r in crit[1:]}, PASTEURIZER_TAGS)
        crit_field = next(f for f in self.registers["maintenance_export"]["fields"] if f["name"] == "criticality")
        self.assertEqual(crit_field["fact_kind"], "criticality")

    def test_planned_registers_are_listed_not_defined(self):
        planned = self.catalogue["planned_registers"]
        ids = {p["id"] for p in planned}
        self.assertEqual(ids, {"pfd_hmb", "electrical_single_line", "training_record", "sds"})
        self.assertEqual(ids & set(self.registers), set())
        self.assertEqual(ids & set(self.schema["$defs"]["RecordsLayer"]["propertyNames"]["enum"]), set())
        doc = DOC.read_text(encoding="utf-8")
        for p in planned:
            self.assertIn(p["department"], self.catalogue["departments"])
            self.assertIn(p["name"], doc, p["id"])

    def test_permits_and_purchase_orders_are_read_only_copies_linked_by_tag(self):
        for rid in ("permit", "purchase_order"):
            r = self.registers[rid]
            self.assertIs(r.get("record_copy"), True, rid)
            self.assertEqual(r["authority_for"], [], rid)
            self.assertIn("tag", {f["name"] for f in r["fields"]}, rid)
            self.assertIn("external governed service", r["notes"], rid)
            self.assertIn("read-only copy", r["notes"], rid)
        self.assertEqual([rid for rid, r in self.registers.items() if r.get("record_copy")],
                         ["purchase_order", "permit"])

    def test_relation_names_are_frozen(self):
        rel = self.schema["$defs"]["RelationType"]
        self.assertEqual(set(rel["enum"]), FROZEN_RELATIONS, "relation names are frozen; a rename needs context-map-2")
        self.assertIn("context-map-2", rel["description"])
        self.assertEqual(self.schema["$defs"]["Relation"]["properties"]["type"], {"$ref": "#/$defs/RelationType"})
        doc_props = set(self.schema["$defs"]["Document"]["properties"])
        self.assertTrue(FROZEN_DOCUMENT_RELATIONS <= doc_props)
        doc = DOC.read_text(encoding="utf-8")
        table = set(re.findall(r"^\| `([a-z_]+)` \| [^|]+ \| [^|]+ \| stable", doc, re.M))
        self.assertEqual(table, FROZEN_RELATIONS | FROZEN_DOCUMENT_RELATIONS, "the spec's frozen relation table")

    def test_no_per_value_standard_refs(self):
        defs = self.schema["$defs"]
        for name in ("Fact", "Relation", "Scope", "RecordRow", "Appearance", "Mention"):
            self.assertNotIn("std", defs[name]["properties"], name)
        for name in ("isa95_level", "isa88_level"):
            self.assertNotIn(name, defs["Scope"]["properties"])
        self.assertNotIn('"std"', EXAMPLE.read_text(encoding="utf-8"))
        bad = copy.deepcopy(self.example)
        bad["plant"]["items"][0]["attributes"] = {"rated_flow": {"value": "12000", "std": {"standard": "CFIHOS",
                                                                                            "ref": "CFIHOS-1"}}}
        self.assertTrue(validate(bad, self.schema, self.schema), "a value may not carry its own standard ref")

    def test_templates_use_plant_words(self):
        for r in self.registers.values():
            for f in r["fields"]:
                if f["type"] == "scope":
                    self.assertIn(f["name"], ("plant", "unit"), r["id"])
                self.assertNotRegex(f["description"].lower(), r"\barea\b", f"{r['id']}.{f['name']}")
        for path in sorted((DIR / "templates").rglob("*.csv")):
            header = read_csv(path)[0]
            for word in ("area", "work_center", "process_cell", "site_area"):
                self.assertNotIn(word, header, path.name)
        rows = read_csv(MAPPING)
        isa = [r for r in rows[1:] if r[1] == "(scopes)" and r[3] in ("ISA-95", "ISA-88")]
        self.assertTrue(isa)
        self.assertTrue(all(r[8] == "equivalent" for r in isa), "ISA-95/88 are equivalents in the mapping table")

    def test_cfihos_codes_stay_to_confirm_except_the_one_checked(self):
        rows = read_csv(MAPPING)
        header = rows[0]
        for row in rows[1:]:
            rec = dict(zip(header, row))
            if rec["standard"] != "CFIHOS":
                continue
            if "CFIHOS-10000395" in rec["reference"]:
                self.assertEqual(rec["id_status"], "verified")
            else:
                self.assertEqual(rec["id_status"], "to_confirm", rec["reference"])
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("CFIHOS reference data is not redistributed", doc)
        self.assertIn("IOGP", doc)
        self.assertIn("POSC Caesar", doc)

    def test_open_questions_closed_with_a_dated_decision_log(self):
        doc = DOC.read_text(encoding="utf-8")
        self.assertNotIn("## Open questions", doc)
        self.assertIn("## Decided (2026-11-04)", doc)
        log = doc.split("## Decided (2026-11-04)", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(len(re.findall(r"^\d+\. \*\*", log, re.M)), 8, "eight decisions")

    # ---------------------------------------------------------------- standards mapping
    def test_standards_mapping_refers_to_real_registers_and_fields(self):
        rows = read_csv(MAPPING)
        header, body = rows[0], rows[1:]
        self.assertEqual(header, ["layer", "register", "field", "standard", "version", "reference", "reference_kind",
                                  "match", "choice", "id_status", "note", "url"])
        self.assertTrue(body)
        standards = set()
        for n, row in enumerate(body, 2):
            rec = dict(zip(header, row))
            self.assertEqual(len(row), len(header), f"mapping line {n}")
            self.assertIn(rec["layer"], ("plant", "records", "documents", "decisions"))
            self.assertIn(rec["id_status"], ("verified", "to_confirm", "n/a"))
            self.assertIn(rec["match"], ("exact", "close", "broader", "narrower", "none"))
            standards.add(rec["standard"])
            if rec["register"].startswith("("):
                continue
            self.assertIn(rec["register"], self.registers, f"mapping line {n}")
            if rec["field"].startswith("("):
                continue
            fields = {f["name"] for f in self.registers[rec["register"]]["fields"]}
            for name in rec["field"].split("|"):
                self.assertIn(name.split("=")[0], fields, f"mapping line {n}: {name}")
            if rec["url"]:
                self.assertTrue(rec["url"].startswith("https://"), f"mapping line {n}")
        for needed in ("ISA-95", "ISA-88", "DEXPI", "ISA-5.1", "CFIHOS", "ISO 14224", "VDI 2770", "AAS", "ISO 15926"):
            self.assertIn(needed, standards)
        # every register is mapped (to a standard or explicitly to 'none')
        mapped = {r[1] for r in body}
        self.assertEqual(sorted(set(self.registers) - mapped), [])

    # ---------------------------------------------------------------- example map
    def test_example_map_validates(self):
        self.assertEqual(validate(self.example, self.schema, self.schema), [])

    def test_example_map_cross_references_hold(self):
        m = self.example
        sources = {s["id"] for s in m["sources"]}
        scopes = {s["id"] for s in m["plant"]["scopes"]}
        items = {i["id"]: i for i in m["plant"]["items"]}
        docs = {d["id"] for d in m["documents"]}
        known = scopes | set(items) | docs
        for i in items.values():
            self.assertIn(i["scope"], scopes)
            self.assertEqual(i["id"], i["scope"] + "/" + i["tag"])
            self.assertIn(i["source"], sources)
        for rel in m["plant"]["relations"]:
            self.assertIn(rel["from"], known)
            self.assertIn(rel["to"], known)
            self.assertIn(rel["source"], sources)
        for rid, rows in m["records"].items():
            fields = {f["name"] for f in self.registers[rid]["fields"]}
            for row in rows:
                self.assertIn(row["source"], sources)
                self.assertTrue(set(row["values"]) <= fields, f"{rid}: {set(row['values']) - fields}")
                if "item" in row:
                    self.assertIn(row["item"], items)
        for c in m["decisions"]["conflicts"]:
            self.assertIn(c["subject"], known)
        for s in m["sources"]:
            self.assertIn(s["record_type"], set(self.registers) | set(self.catalogue["pseudo_record_types"]))

    def test_identity_only_map_is_valid_and_missing_identity_is_not(self):
        minimal = {"format": "context-map-1", "map": {"site": "S1"},
                   "plant": {"scopes": [{"id": "S1", "level": "site"}, {"id": "S1/P1", "level": "plant"}],
                             "items": [{"id": "S1/P1/P-101", "tag": "P-101", "scope": "S1/P1"}]}}
        self.assertEqual(validate(minimal, self.schema, self.schema), [])
        for mutate, why in (
                (lambda d: d.pop("plant"), "no plant layer"),
                (lambda d: d.update(format="context-map-2"), "wrong format"),
                (lambda d: d["plant"]["items"][0].pop("tag"), "item without tag"),
                (lambda d: d["plant"]["items"][0].pop("scope"), "item without scope"),
                (lambda d: d["plant"]["items"][0].update(tag="P-101 "), "trailing space in tag"),
                (lambda d: d["plant"]["items"][0].update(tag="P1/P-101"), "slash in tag"),
                (lambda d: d.update(records={"spreadsheet": []}), "unknown register"),
                (lambda d: d.update(records={"ccp": [{"values": {}}]}), "row without source"),
                (lambda d: d.update(decisions={"rulings": [{"id": "R1", "concerns": "S1/P1/P-101",
                                                             "ruling": "accept_value", "by": "x", "on": "2026-11-04"}]}),
                 "ruling without reason")):
            bad = copy.deepcopy(minimal)
            mutate(bad)
            self.assertTrue(validate(bad, self.schema, self.schema), why)

    def test_with_jsonschema_when_installed(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema not installed; the local validator covers the keywords used")
        jsonschema.Draft202012Validator.check_schema(self.schema)
        jsonschema.Draft202012Validator(self.schema).validate(self.example)

    # ---------------------------------------------------------------- the ontology pieces (1.1)
    def test_ontology_files_share_the_minor_version(self):
        versions = {p.name: load(p)["format_version"] for p in (REGISTERS, CLASSES, RELATIONS, RULES, EXAMPLE)}
        self.assertEqual(set(versions.values()), {"1.2.0-draft"}, versions)
        self.assertIn("1.2", self.schema["title"])
        self.assertIn("1.2.0-draft", DOC.read_text(encoding="utf-8"))

    def test_relation_semantics_cover_exactly_the_frozen_names(self):
        rel = load(RELATIONS)
        self.assertEqual({r["name"] for r in rel["relations"]}, FROZEN_RELATIONS | FROZEN_DOCUMENT_RELATIONS)
        classes = {c["id"] for c in load(CLASSES)["classes"]}
        for r in rel["relations"]:
            for key in ("domain", "range", "inverse", "transitive", "cardinality"):
                self.assertIn(key, r, r["name"])
            for c in r["domain"] + r["range"]:
                self.assertTrue(c in classes or c in rel["pseudo_classes"], (r["name"], c))

    def test_class_refs_are_dexpi_verified_and_cfihos_to_confirm(self):
        doc = load(CLASSES)
        ids = [c["id"] for c in doc["classes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in doc["classes"]:
            self.assertTrue(c["parent"] is None or c["parent"] in ids, c["id"])
            self.assertEqual(c["cfihos"]["id_status"], "to_confirm", c["id"])
            self.assertIn(c["certification"]["status"], ("draft", "certified"))
            if c["dexpi"]:
                self.assertEqual(len(c["dexpi"]["classes"]), len(c["dexpi"]["uris"]))
                for name, uri in zip(c["dexpi"]["classes"], c["dexpi"]["uris"]):
                    self.assertTrue(uri.endswith(f"/{name}.html"), uri)
        for rule in doc["letter_rules"]:
            self.assertIn(rule["class"], ids)
        for cid in doc["equipment_prefixes"].values():
            self.assertIn(cid, ids)

    def test_example_map_uses_classes_glossary_and_expectations(self):
        classes = {c["id"] for c in load(CLASSES)["classes"]}
        for it in self.example["plant"]["items"]:
            self.assertIn(it["class"], classes, it["id"])
        gl = self.registers["glossary"]
        terms = {}
        for row in self.example["records"]["glossary"]:
            vals = dict(row["values"])
            self.assertEqual(row_errors(gl, vals, f"glossary {row['id']}"), [])
            terms[vals["term"]] = vals
        self.assertEqual({t["certification"] for t in terms.values()}, {"certified", "draft"})
        glossary_mentions = [mt for d in self.example["documents"] for mt in d.get("mentions", [])
                             if mt.get("match") == "glossary"]
        self.assertTrue(glossary_mentions)
        for mt in glossary_mentions:
            self.assertEqual(terms[mt["term"]]["certification"], "certified", "only a certified term links")
        rules = {r["id"] for r in load(RULES)["rules"]}
        for res in self.example["expectations"]["results"]:
            self.assertIn(res["rule"], rules)
        for c in self.example["coverage"]["by_rule"]:
            self.assertIn(c["rule"], rules)
        site = copy.deepcopy(self.example)
        site["settings"]["authority"] = {"rating": "maintenance_export"}
        site["settings"]["authority_certification"] = {"rating": {"status": "draft"}}
        self.assertEqual(validate(site, self.schema, self.schema), [])
        site["settings"]["authority_certification"] = {"rating": {"status": "maybe"}}
        self.assertTrue(validate(site, self.schema, self.schema))
        bad = copy.deepcopy(self.example)
        bad["plant"]["items"][0]["class"] = "Pump"
        self.assertTrue(validate(bad, self.schema, self.schema), "class ids are lower-case ids from classes.json")

    def test_rules_template_ships_every_rule_as_draft(self):
        doc = load(RULES)
        self.assertEqual(doc["format"], "context-map-expectations-1")
        for r in doc["rules"]:
            self.assertEqual(r["certification"]["status"], "draft", r["id"])
            for key in ("id", "title", "applies_to", "owner", "severity", "checks"):
                self.assertIn(key, r, r["id"])

    def test_spec_documents_the_ontology_sections(self):
        doc = DOC.read_text(encoding="utf-8")
        for heading in ("## Classes", "## Relation semantics", "## Expectations", "## Glossary", "## Certification",
                        "## Answerability", "## JSON-LD view"):
            self.assertIn(heading, doc)

    # ---------------------------------------------------------------- public wording
    def test_public_files_name_no_private_product(self):
        paths = [SCHEMA, REGISTERS, MAPPING, EXAMPLE, DOC, CLASSES, RELATIONS, RULES,
                 *sorted((DIR / "templates").rglob("*.csv"))]
        for p in paths:
            self.assertNotIn("changepilot", p.read_text(encoding="utf-8").lower(), p.name)


if __name__ == "__main__":
    unittest.main()
