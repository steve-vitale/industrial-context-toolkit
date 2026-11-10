"""Prepare a bounded common basis from explicit CSV columns and source-bound agent contributions.

Headers map to declared fields; document interpretation is supplied, unreviewed
work. Whole originals and unmapped columns remain in the caller's packet.
"""
import csv
import datetime
import io
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

import context_basis as cb

ALIASES = {
    "tag": ("tag", "equipment", "asset number", "equipment number", "equipment tag", "asset id"),
    "unit": ("area", "unit", "functional location", "unit code"),
    "class": ("class", "type", "asset kind", "equipment class"),
    "description": ("description", "asset description", "equipment description"),
    "manufacturer": ("manufacturer", "vendor", "make"),
    "model": ("model", "vendor model"),
    "serial_number": ("serial", "serial number", "vendor serial"),
    "physical_id": ("physical asset id", "installed item id"),
    "rated_flow": ("rated flow",),
    "flow_unit": ("flow unit",),
    "design_temperature": ("design temperature",),
    "temperature_unit": ("temperature unit",),
    "variable": ("variable", "measured variable"),
    "engineering_unit": ("engineering unit", "uom"),
    "range_low": ("range low",),
    "range_high": ("range high",),
    "work_order": ("order", "work order", "work order number"),
    "closed_on": ("closed", "closed on", "completion date"),
    "installed_serial_number": ("installed serial",),
    "installed_model": ("installed model",),
}
UNIT_FIELDS = {"rated_flow": "flow_unit", "design_temperature": "temperature_unit",
               "range_low": "engineering_unit", "range_high": "engineering_unit"}
DATE_FORMATS = {"ISO": "%Y-%m-%d", "MDY": "%m/%d/%Y", "DMY": "%d/%m/%Y"}
FIELD_MAX = 1024 * 1024


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


KNOWN = {header_key(alias): field for field, aliases in ALIASES.items() for alias in aliases}


def local(root, relative):
    path = PurePosixPath(relative)
    cb.require(type(relative) is str and relative and path.as_posix() == relative and "\\" not in relative
               and not path.is_absolute() and not any(p in ("", ".", "..") for p in path.parts)
               and ":" not in relative, "source path must stay within supplied records")
    target = root.joinpath(*path.parts)
    cb.require(target.resolve().is_relative_to(root.resolve()), "source path escapes records")
    for parent in (target, *target.parents):
        if parent == root.parent:
            break
        cb.require(not parent.is_symlink(), "symlink source path refused")
    return target


def csv_rows(raw, encoding="utf-8-sig", delimiter=None):
    cb.require(len(raw) <= cb.MAX_BYTES, "source exceeds declared byte limit")
    try:
        decoded = raw.decode(encoding)
    except UnicodeError as error:
        raise cb.ContextError("source encoding needs clarification; no replacement decoding") from error
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(decoded[:16384], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.DictReader(io.StringIO(decoded, newline=""), delimiter=delimiter)
    fields = reader.fieldnames
    cb.require(fields and all(type(f) is str and f.strip() for f in fields)
               and len(set(fields)) == len(fields), "CSV headers need unique nonempty names")
    result, previous = [], reader.line_num
    old_limit = csv.field_size_limit()
    csv.field_size_limit(FIELD_MAX)
    try:
        for number, row in enumerate(reader, 2):
            cb.require(None not in row and all(v is not None for v in row.values()),
                       "CSV row width disagrees with its headers")
            cb.require(all(len(v) <= FIELD_MAX for v in row.values()), "CSV field exceeds declared limit")
            result.append((row, number, previous + 1, reader.line_num))
            previous = reader.line_num
    except csv.Error as error:
        raise cb.ContextError("invalid or oversized CSV record") from error
    finally:
        csv.field_size_limit(old_limit)
    return fields, result, delimiter


def mapped_headers(fields, saved=None):
    mapping = {}
    for name in fields:
        field = KNOWN.get(header_key(name))
        if field is not None:
            cb.require(field not in mapping.values(), "ambiguous header mapping; clarify: " + field)
            mapping[name] = field
    if saved is not None:
        cb.require(set(saved.get("headers", [])) == set(fields),
                   "source headers changed; review mapping before reuse")
        cb.require(type(saved.get("mapping")) is dict
                   and set(saved["mapping"]) <= set(fields)
                   and len(set(saved["mapping"].values())) == len(saved["mapping"]),
                   "saved source mapping is malformed")
        cb.require(all(v in ALIASES for v in saved["mapping"].values()), "saved mapping has unsupported target")
        mapping = saved["mapping"]
    return mapping


def source_inventory(folder, encoding):
    register = folder / "source-register.csv"
    raw_files, declarations = {}, []
    if register.exists():
        cb.require(register.is_file() and not register.is_symlink(), "unsafe source register")
        register_raw = register.read_bytes()
        _, records, _ = csv_rows(register_raw, encoding)
        for row, _, _, _ in records:
            cb.require(all(row.get(k) for k in ("File", "DocumentID", "Revision", "Status", "Owner", "Applicability")),
                       "source register needs File/DocumentID/Revision/Status/Owner/Applicability")
            declarations.append(dict(row))
        raw_files["source-register.csv"] = register_raw
    else:
        for path in sorted(folder.iterdir()):
            if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in (".csv", ".txt", ".md", ".json", ".pdf", ".png", ".jpg", ".jpeg", ".svg"):
                declarations.append({"File": path.name, "DocumentID": path.name, "Revision": "unknown",
                                     "Status": "supplied", "Owner": "unknown", "Applicability": "unknown"})
    cb.require(declarations, "no admitted source files; supply permitted records")
    seen, ids = set(), set()
    for declaration in declarations:
        name, identifier = declaration["File"], declaration["DocumentID"]
        cb.require(name.casefold() not in seen and identifier not in ids, "duplicate source path or document id")
        seen.add(name.casefold())
        ids.add(identifier)
        path = local(folder, name)
        if path.exists():
            cb.require(path.is_file() and path.stat().st_size <= cb.MAX_BYTES, "unsafe or oversized source")
            raw_files[name] = path.read_bytes()
        elif declaration["Status"] in cb.ACTIVE_SOURCES:
            declaration["Status"] = "missing"
            declaration["availability_reason"] = "Declared active file was not supplied; no blank source fabricated."
    return declarations, raw_files


def consume_csv(builder, source, raw, site, plant, *, saved=None, encoding="utf-8-sig",
                date_format="ISO"):
    fields, records, delimiter = csv_rows(raw, encoding)
    mapping = mapped_headers(fields, saved)
    result = {"headers": fields, "mapping": mapping, "delimiter": delimiter,
              "unmapped_columns": [f for f in fields if f not in mapping],
              "date_format": date_format, "encoding": encoding}
    if not {"tag", "unit"} <= set(mapping.values()):
        builder.basis["omissions"].append({"source": source, "reason": "CSV has no unambiguous tag/unit mapping; original retained.",
                                          "headers": fields})
        return result
    builder.basis["preparation"].append({"source": source, "kind": "declared_header_mapping",
                                         "mapping": mapping, "unmapped_columns": result["unmapped_columns"]})
    cb.require(date_format in DATE_FORMATS, "select ISO, MDY or DMY date format")
    latest = {}
    for original, number, _, _ in records:
        mapped = {mapping[key]: value for key, value in original.items() if key in mapping}
        if "work_order" in mapping.values():
            cb.require(mapped.get("work_order"), "work-order identity needs clarification")
        closed = mapped.get("closed_on", "")
        if mapped.get("work_order") and closed:
            try:
                date = datetime.datetime.strptime(closed, DATE_FORMATS[date_format]).date()
                cb.require(date.strftime(DATE_FORMATS[date_format]) == closed, "noncanonical closeout date")
            except ValueError as error:
                raise cb.ContextError("work-order date needs explicit ISO/MDY/DMY clarification") from error
            key = (mapped.get("unit"), mapped.get("tag"))
            latest[key] = max(latest.get(key, date), date)
    for original, number, start, end in records:
        row = {mapping[key]: value for key, value in original.items() if key in mapping}
        cb.require(row["tag"] and row["unit"], "row needs tag/unit clarification; no identity guessed")
        subject = cb.qualified(site, plant, row["unit"], row["tag"])
        builder.entity(subject, row["tag"], subject.rsplit("/", 1)[0])
        order = row.get("work_order")
        closed = row.get("closed_on", "")
        parsed = None
        if closed:
            try:
                parsed = datetime.datetime.strptime(closed, DATE_FORMATS[date_format]).date()
                cb.require(parsed.strftime(DATE_FORMATS[date_format]) == closed, "noncanonical closeout date")
            except ValueError as error:
                raise cb.ContextError("work-order date needs explicit ISO/MDY/DMY clarification") from error
        role = ("closed_order_record" if closed else "open_order_proposal") if order else "export_record"
        record_subject = subject
        if order:
            record_subject = subject.rsplit("/", 1)[0] + "/record:" + quote(order, safe="-._~")
            builder.entity(record_subject, order, subject.rsplit("/", 1)[0], identity_role="maintenance_record")
            builder.occurrence(record_subject, "associated_with", source, f"CSV record {number}",
                               target=subject, role="maintenance_record_about_position", direction="known")
        # JSON mapping serialization may reorder object keys. Source-column order
        # is the stable occurrence order for replay, not mapping insertion order.
        for original_header in fields:
            if original_header not in mapping:
                continue
            field = mapping[original_header]
            value = original[original_header]
            if field in ("tag", "unit", "physical_id") or value == "":
                continue
            if field == "closed_on":
                value = parsed.isoformat() if closed else value
            predicate = field
            if order and field.startswith("installed_"):
                predicate = field.removeprefix("installed_") if closed else "proposed_" + field.removeprefix("installed_")
            locator = f"CSV record {number}; physical lines {start}-{end}; column {original_header}"
            builder.occurrence(record_subject, predicate, source, locator, value=value,
                               unit=row.get(UNIT_FIELDS.get(field, ""), None) or None, role=role,
                               original_header=original_header, record_id=order)
            if (order and closed and field.startswith("installed_")
                    and parsed == latest[(row["unit"], row["tag"])]):
                builder.occurrence(subject, predicate, source, locator, value=value, role="latest_closed_order_record",
                                   recorded_closed_on=parsed.isoformat(), record_id=order,
                                   qualification="Latest dated supplied closeout, not verified current installation")
        if row.get("physical_id"):
            item = subject.rsplit("/", 1)[0] + "/item:" + quote(row["physical_id"], safe="-._~")
            header = next(name for name in fields if mapping.get(name) == "physical_id")
            locator = f"CSV record {number}; physical lines {start}-{end}; column {header}"
            if order and not closed:
                builder.occurrence(record_subject, "proposed_physical_item_id", source, locator,
                                   value=row["physical_id"], role="open_order_proposal", original_header=header,
                                   review={"status": "proposed"})
                builder.basis["omissions"].append({"subject": record_subject, "source": source,
                    "proposed_physical_item_id": row["physical_id"],
                    "reason": "Open order proposes a physical item; no installation relationship established."})
            else:
                builder.entity(item, row["physical_id"], subject.rsplit("/", 1)[0], identity_role="physical_item")
                builder.occurrence(item, "reported_installation_at", source, locator,
                                   target=subject, role=role, direction="known", original_header=header,
                                   qualification="Supplied installation account; not independently verified current installation")
        elif row.get("serial_number") or row.get("installed_serial_number"):
            builder.basis["omissions"].append({"subject": subject, "source": source,
                    "reason": "Serial values alone do not establish a durable physical-item identity or current installation."})
    return result


def prepare(folder, site, plant, *, previous_mapping=None, encoding="utf-8-sig", date_format="ISO"):
    folder = Path(folder).absolute()
    cb.require(folder.is_dir() and not folder.is_symlink(), "records need an ordinary local directory")
    folder = folder.resolve()
    cb.require(all(type(p) is str and p and p == p.strip() for p in (site, plant)),
               "site/plant namespace needs explicit nonempty components without outer whitespace")
    namespace = "/".join(quote(cb.text(p, "scope"), safe="-._~") for p in (site, plant))
    builder = cb.Builder(namespace)
    declarations, originals = source_inventory(folder, encoding)
    mappings = {}
    for declaration in declarations:
        filename, identifier = declaration["File"], declaration["DocumentID"]
        raw = originals.get(filename)
        status = declaration["Status"]
        builder.source(identifier, declaration["Revision"], cb.raw_sha(raw) if raw is not None else None,
                       owner=declaration["Owner"], status=status,
                       applicability=declaration["Applicability"], path=filename,
                       availability_reason=declaration.get("availability_reason"))
    for declaration in declarations:
        filename, identifier = declaration["File"], declaration["DocumentID"]
        if filename not in originals:
            builder.basis["omissions"].append({"source": identifier, "reason": "Source bytes unavailable; retain status and ask owner."})
            continue
        suffix = Path(filename).suffix.lower()
        if suffix == ".csv":
            saved = None if previous_mapping is None else previous_mapping.get(identifier)
            mappings[identifier] = consume_csv(builder, identifier, originals[filename], site, plant,
                    saved=saved, encoding=encoding, date_format=date_format)
        else:
            # No document-reading claim: an approved assistant/engineer supplies
            # explicit source-bound contributions through add_contributions().
            if suffix == ".json":
                try:
                    doc = json.loads(originals[filename].decode(encoding))
                except (ValueError, UnicodeError):
                    doc = None
                if isinstance(doc, dict) and doc.get("schema") in ("engineering-component-drafts-1", cb.SCHEMA):
                    raise cb.ContextError("Derived context/draft requires its lineage-preserving import route; not a new independent source")
            builder.basis["omissions"].append({"source": identifier,
                "reason": "Original retained; document/model interpretation needs explicit source-bound contributions or an existing adapter."})
    return builder.finish(), originals, mappings


def add_contributions(basis, originals, raw_csv):
    """Consume supplied interpretation; check literal quotation, not engineering truth."""
    builder = cb.Builder(basis["namespace"], basis)
    fields, records, _ = csv_rows(raw_csv)
    required = {"Subject", "Predicate", "Source", "Locator", "Quote"}
    cb.require(required <= set(fields), "contribution CSV needs Subject/Predicate/Source/Locator/Quote")
    for row, number, _, _ in records:
        identifier, source_id = row["Subject"], row["Source"]
        cb.require(source_id in builder.sources, "contribution names unknown source")
        role = "functional_position"
        if not identifier:
            identifier = basis["namespace"] + "/documents/" + quote(source_id, safe="-._~")
            role = "document_record"
        cb.require(identifier.startswith(basis["namespace"] + "/") and "/" in identifier, "contribution subject outside declared namespace")
        if identifier not in builder.entities:
            scope, tag = identifier.rsplit("/", 1)
            builder.entity(identifier, unquote(tag), scope, identity_role=role)
        source = builder.sources[source_id]
        path = source.get("path")
        cb.require(path in originals, "contribution source bytes unavailable")
        cb.require(cb.raw_sha(originals[path]) == source["sha256"],
                   "source raw-byte binding mismatch: " + source_id)
        quote_text = cb.text(row["Quote"], "contribution quote")
        match = re.fullmatch(r"line ([1-9][0-9]*)", row["Locator"])
        cb.require(match is not None, "text contribution needs an explicit line N locator")
        try:
            lines = originals[path].decode("utf-8-sig").splitlines()
        except UnicodeError as error:
            raise cb.ContextError("text contribution needs UTF-8 source or its qualified adapter") from error
        line = int(match[1])
        cb.require(line <= len(lines) and quote_text in lines[line - 1],
                   "contribution quote does not match the cited original line")
        target = row.get("Target")
        metadata = {"quote": quote_text, "contribution_record": number,
                    "rationale": row.get("Rationale", ""),
                    "qualification": "Supplied unreviewed interpretation; matching quotation is not proof of engineering meaning."}
        if target:
            cb.require(target in builder.entities, "contribution target needs an explicit existing identity")
            builder.occurrence(identifier, row["Predicate"], source_id, row["Locator"],
                               target=target, role="supplied_interpretation", direction="known", **metadata)
        else:
            value = row.get("Value", "")
            kind = row.get("Type", "text") or "text"
            if kind == "boolean":
                cb.require(value in ("true", "false"), "boolean contribution needs true/false")
                value = value == "true"
            elif kind == "integer":
                cb.require(re.fullmatch(r"-?[0-9]{1,128}", value), "integer contribution needs an explicit integer")
                value = int(value)
            elif kind == "number":
                value = cb.lossless_float(value)
            elif kind == "null":
                cb.require(value in ("", "null"), "null contribution must not discard a nonempty value")
                value = None
            else:
                cb.require(kind == "text", "unsupported contribution type")
            builder.occurrence(identifier, row["Predicate"], source_id, row["Locator"],
                               value=value, unit=row.get("Unit") or None,
                               role="supplied_interpretation", **metadata)
    builder.basis["preparation"].append({"kind": "source_bound_contributions",
                                        "sha256": cb.raw_sha(raw_csv), "records": len(records),
                                        "interpretation_review": "not performed"})
    return builder.finish()

