"""Inspect, compare and propose attribute edits in a bounded, source-retaining DXF handoff.

Uses ezdxf; no DWG conversion, intelligent-P&ID database, inferred connectivity or automatic synchronization.
Every model-space INSERT in the supported profile has a unique ICT_ID and TAG attribute. Other entities and
attributes are retained and checked. See examples/cad-handoff/README.md for the exact comparison boundary.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf.lldxf.tagwriter import TagCollector

SCHEMA = "cad-handoff-1"
EDITABLE = {"TAG", "MANUFACTURER", "MODEL", "SERIAL", "SIZE"}
# Drawing extents, handles and save metadata may change on serialization. They are reported separately, not
# claimed as preserved engineering content. Everything else in the header is compared.
SAVE_HEADERS = {"$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE", "$TDINDWG", "$TDUSRTIMER",
                "$FINGERPRINTGUID", "$VERSIONGUID", "$HANDSEED", "$LASTSAVEDBY", "$EXTMIN", "$EXTMAX"}


class InputError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return [plain(v) for v in value]


def load(path):
    path = Path(path)
    if path.suffix.lower() != ".dxf":
        raise InputError("Only DXF is supported; native DWG/project databases need a qualified adapter")
    doc = ezdxf.readfile(path)
    proxies = [e.dxftype() for e in doc.entitydb.values()
               if e.is_alive and e.dxftype() in {"ACAD_PROXY_ENTITY", "ACAD_PROXY_OBJECT"}]
    if proxies:
        raise InputError("Proxy objects present: retain the original and use the owning CAD application")
    return doc


def assets(doc):
    rows, seen = [], set()
    for entity in doc.modelspace().query("INSERT"):
        attrs, handles = {}, {}
        for a in entity.attribs:
            key = a.dxf.tag
            if key in attrs:
                raise InputError(f"Duplicate attribute {key} on INSERT {entity.dxf.handle}")
            attrs[key], handles[key] = a.dxf.text, a.dxf.handle
        identity = attrs.get("ICT_ID", "").strip()
        if not identity or not attrs.get("TAG", "").strip():
            raise InputError(f"INSERT {entity.dxf.handle} needs ICT_ID and TAG; unprofiled blocks are not guessed")
        if identity in seen:
            raise InputError(f"Duplicate stable identity: {identity}")
        seen.add(identity)
        rows.append({"id": identity, "handle": entity.dxf.handle, "block": entity.dxf.name,
                     "attributes": attrs, "attribute_handles": handles})
    if not rows:
        raise InputError("No profiled asset INSERTs found; a flattened picture is not an asset handoff")
    return sorted(rows, key=lambda r: r["id"])


def snapshot(path):
    original_hash = digest(path)
    doc = load(path)
    entities = {}
    metadata = doc.rootdict.get("EZDXF_META")
    save_entities = {v.dxf.handle for k, v in metadata.items()
                     if k in {"CREATED_BY_EZDXF", "WRITTEN_BY_EZDXF"}} if metadata is not None else set()
    save_values = {}
    for e in doc.entitydb.values():
        if e.is_alive:
            collector = TagCollector(dxfversion=doc.dxfversion)
            e.export_dxf(collector)
            tags = [[t.code, plain(t.value)] for t in collector.tags]
            # INSERT/POLYLINE exporters append their child entities. Each child has its own entitydb row;
            # compare it there, so an allowed ATTRIB edit does not also look like a parent geometry edit.
            end = next((i for i, t in enumerate(tags) if i and t[0] == 0), len(tags))
            tags = tags[:end]
            if e.dxf.handle in save_entities:
                save_values[e.dxf.handle] = [t[1] for t in tags if t[0] == 1]
                for t in tags:
                    if t[0] == 1:
                        t[1] = "<ezdxf save metadata>"
            entities[e.dxf.handle] = {"type": e.dxftype(), "tags": tags}
    header = {k: plain(doc.header[k]) for k in doc.header.varnames()}
    if digest(path) != original_hash:
        raise InputError("Source changed during inspection; retry from a retained version")
    return {"schema": SCHEMA, "sha256": original_hash, "ezdxf": ezdxf.__version__,
            "dxfversion": doc.dxfversion, "assets": assets(doc), "entities": entities,
            "header": {k: v for k, v in header.items() if k not in SAVE_HEADERS},
            "save_metadata": dict({k: v for k, v in header.items() if k in SAVE_HEADERS},
                                  ezdxf_dictionary_values=save_values)}


def validate_plan(before, plan):
    if not isinstance(plan, dict) or plan.get("schema") != "cad-edit-plan-1" or plan.get("source_sha256") != before["sha256"]:
        raise InputError("Plan must name cad-edit-plan-1 and the exact current source SHA-256")
    if not isinstance(plan.get("changes"), list) or not plan["changes"]:
        raise InputError("Plan needs at least one explicit change")
    index = {a["id"]: a for a in before["assets"]}
    expected, changed = {}, set()
    for change in plan["changes"]:
        if not isinstance(change, dict):
            raise InputError("Each planned change must be an object")
        identity, attr = change.get("id"), change.get("attribute")
        if not isinstance(identity, str) or not isinstance(attr, str) or identity not in index or attr not in EDITABLE:
            raise InputError("Unknown asset or noneditable attribute (ICT_ID cannot be changed)")
        key = (identity, attr)
        if key in changed:
            raise InputError("Duplicate edit in plan")
        changed.add(key)
        asset = index[identity]
        if attr not in asset["attributes"] or asset["attributes"][attr] != change.get("before"):
            raise InputError("Before-value mismatch: source or proposed edit is stale")
        if not isinstance(change.get("after"), str) or not change["after"].strip():
            raise InputError("After-value must be nonempty text; units are not inferred")
        if change["before"] == change["after"] or not isinstance(change.get("reason"), str) or not change["reason"].strip():
            raise InputError("Change needs a different after-value and a review/evidence reason")
        expected[asset["attribute_handles"][attr]] = change
    return expected


def compare(before, after, plan=None):
    edits = validate_plan(before, plan) if plan is not None else {}
    differences = []
    if before["dxfversion"] != after["dxfversion"]:
        differences.append({"kind": "dxf_version", "before": before["dxfversion"], "after": after["dxfversion"]})
    if before["header"] != after["header"]:
        differences.append({"kind": "header", "before": before["header"], "after": after["header"]})
    for handle in sorted(set(before["entities"]) | set(after["entities"])):
        left, right = before["entities"].get(handle), after["entities"].get(handle)
        expected = json.loads(json.dumps(left)) if left is not None else None
        if handle in edits and expected is not None:
            tags = [t for t in expected["tags"] if t[0] == 1]
            if len(tags) != 1 or tags[0][1] != edits[handle]["before"]:
                raise InputError("Attribute serialization does not match the declared comparison profile")
            tags[0][1] = edits[handle]["after"]
        if expected != right:
            differences.append({"kind": "entity", "handle": handle, "before": expected, "after": right})
    return {"schema": "cad-comparison-1", "before_sha256": before["sha256"], "after_sha256": after["sha256"],
            "status": "pass" if not differences else "differences", "expected_edits": list(edits.values()),
            "unexpected": differences, "save_metadata_changed": before["save_metadata"] != after["save_metadata"],
            "boundary": "All ezdxf-exported entity tags including block definitions, attributes, layers and objects; "
                        "all headers except listed save metadata and the two named EZDXF_META writer values. "
                        "Same handles required. This is not a byte-identical "
                        "DXF or proprietary project database/visual/engineering acceptance."}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def field_changes(before, after):
    """Retain missing versus present values; a null is not an absent field."""
    return {k: {"before": {"present": k in before, "value": before.get(k)},
                "after": {"present": k in after, "value": after.get(k)}}
            for k in sorted(set(before) | set(after)) if (k in before, before.get(k)) != (k in after, after.get(k))}


def review_records(doc):
    # These are explicit decoded fields, not a normalized geometry/equivalence test.
    def fields(entity):
        return {k: plain(v) for k, v in entity.dxfattribs().items() if k not in {"handle", "owner"}}
    drawing, tables, blocks, layouts = {}, {}, {}, {}
    for block in doc.blocks:
        blocks[block.name] = fields(block.block)
        for e in block:
            drawing[e.dxf.handle] = {"type": e.dxftype(), "scope": block.name, "fields": fields(e)}
    for layout in doc.layouts:
        layouts[layout.name] = {"block": layout.block_record_name,
                                "entities": dict(sorted(Counter(e.dxftype() for e in layout).items()))}
    for table in (doc.layers, doc.styles, doc.linetypes, doc.dimstyles, doc.appids):
        for e in table:
            tables[e.dxftype() + ":" + e.dxf.name] = fields(e)
    return drawing, tables, blocks, layouts


def review_data(before, after, strict, before_doc, after_doc, plan):
    edits = {(c["id"], c["attribute"]): c for c in plan["changes"]} if plan else {}
    assets_before = {a["id"]: a for a in before["assets"]}
    assets_after = {a["id"]: a for a in after["assets"]}
    attributes, asset_changes = [], []
    for identity in sorted(set(assets_before) | set(assets_after)):
        left, right = assets_before.get(identity), assets_after.get(identity)
        if left is None or right is None:
            asset_changes.append({"id": identity, "status": "added identity" if left is None else "missing identity",
                                  "before": left, "after": right})
        elif (left["handle"], left["block"]) != (right["handle"], right["block"]):
            asset_changes.append({"id": identity, "status": "handle or block changed",
                                  "before": {k: left[k] for k in ("handle", "block")},
                                  "after": {k: right[k] for k in ("handle", "block")}})
        la, ra = (left or {}).get("attributes", {}), (right or {}).get("attributes", {})
        for attr in sorted(set(la) | set(ra)):
            edit = edits.get((identity, attr))
            same = (attr in la, la.get(attr)) == (attr in ra, ra.get(attr))
            status = ("planned edit observed" if edit and attr in ra and ra[attr] == edit["after"] else
                      "planned edit missing or different" if edit else "unchanged" if same else "unexpected")
            attributes.append({"id": identity, "attribute": attr, "before_present": attr in la,
                               "before": la.get(attr), "after_present": attr in ra, "after": ra.get(attr),
                               "planned_after": edit["after"] if edit else None, "status": status})
    partitions = Counter()
    entity_changes = []
    for index, difference in enumerate(strict["unexpected"]):
        if difference["kind"] != "entity":
            continue
        left, right = difference["before"], difference["after"]
        category = ("added handle" if left is None else "removed handle" if right is None else
                    "handle reused for different type" if left["type"] != right["type"] else "same type changed")
        partitions[category] += 1
        def groups(entity):
            result = {}
            for code, value in (entity or {}).get("tags", []):
                result.setdefault(str(code), []).append(value)
            return result
        entity_changes.append({"handle": difference["handle"], "category": category,
                               "before_type": left["type"] if left else None,
                               "after_type": right["type"] if right else None,
                               "changed_groups": sorted(field_changes(groups(left), groups(right)), key=int),
                               "strict_difference_index": index})
    ld, lt, lb, ll = review_records(before_doc)
    rd, rt, rb, rl = review_records(after_doc)
    drawing_changes = []
    for handle in sorted(set(ld) | set(rd)):
        left, right = ld.get(handle), rd.get(handle)
        if left == right:
            continue
        category = ("added handle" if left is None else "removed handle" if right is None else
                    "handle reused for different type" if left["type"] != right["type"] else "same type changed")
        fields = field_changes((left or {}).get("fields", {}), (right or {}).get("fields", {}))
        if left and right and left["scope"] != right["scope"]:
            fields["record_scope"] = {"before": {"present": True, "value": left["scope"]},
                                      "after": {"present": True, "value": right["scope"]}}
        if left and right and left["type"] != right["type"]:
            fields["entity_type"] = {"before": {"present": True, "value": left["type"]},
                                     "after": {"present": True, "value": right["type"]}}
        drawing_changes.append({"handle": handle, "category": category,
                                "before_type": left["type"] if left else None,
                                "after_type": right["type"] if right else None,
                                "before_scope": left["scope"] if left else None,
                                "after_scope": right["scope"] if right else None,
                                "fields": fields})
    return {"schema": "cad-receiving-review-1", "before_sha256": before["sha256"], "after_sha256": after["sha256"],
            "strict_status": strict["status"], "strict_difference_count": len(strict["unexpected"]),
            "save_metadata_changed": strict["save_metadata_changed"],
            "version": {"before": before["dxfversion"], "after": after["dxfversion"]},
            "header_changes": field_changes(before["header"], after["header"]),
            "asset_changes": asset_changes, "asset_attributes": attributes,
            "entity_partitions": dict(sorted(partitions.items())), "entity_changes": entity_changes,
            "drawing_changes": drawing_changes, "named_table_changes": field_changes(lt, rt),
            "block_changes": field_changes(lb, rb), "layout_changes": field_changes(ll, rl),
            "acceptance": "not performed",
            "boundary": "Diagnostic only; the original strict comparison and its exit status remain authoritative for this software gate. "
                        "Handles are not matched by geometry. Added/removed handles may be remapping, not added/removed physical objects. "
                        "Drawing fields are explicit ezdxf attributes of direct block/layout records, not geometry or visual equivalence. "
                        "Child ATTRIB/complex payloads, XDATA and other objects remain in the strict queue. Named table fields do not "
                        "cover complete linetype patterns or style behavior. No difference is automatically waived, accepted or called harmless."}


def render_review(out, report):
    def cell(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    def observed(present, value):
        return cell(value) if present else "(absent)"
    lines = ["# CAD receiving review", "", f"Strict comparison: **{report['strict_status']}**; {report['strict_difference_count']} differences outside allowed edits.", "",
             "Acceptance has not been performed. This packet explains differences; it does not approve a returned drawing.", "",
             f"Before SHA-256: {report['before_sha256']}", f"After SHA-256: {report['after_sha256']}", "",
             f"DXF version: {report['version']['before']} to {report['version']['after']}.",
             f"Declared save metadata changed: {report['save_metadata_changed']}. These named exclusions are retained in the strict comparison.", ""]
    parts = ["<h1>CAD receiving review</h1>"] + [f"<p>{html.escape(x.replace('**', ''))}</p>" for x in lines[2:] if x]
    def table(title, headers, rows, folded=False):
        rows = [[cell(c) for c in row] for row in rows]
        lines.extend([f"## {title}", ""])
        if folded:
            lines.extend([f"{len(rows)} records; see review.json and strict-comparison.json for every exact change.", ""])
        else:
            lines.extend(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)])
            lines.extend("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in row) + " |" for row in rows)
            lines.append("")
        body = "<table><thead><tr>" + "".join("<th>" + html.escape(c) + "</th>" for c in headers) + "</tr></thead><tbody>"
        body += "".join("<tr>" + "".join("<td data-label='" + html.escape(label, quote=True) + "'>" + html.escape(c) + "</td>"
                                        for label, c in zip(headers, row)) + "</tr>" for row in rows)
        body += "</tbody></table>" if rows else "<tr><td colspan='" + str(len(headers)) + "'>No changes in this section</td></tr></tbody></table>"
        parts.append(("<details><summary>" + html.escape(title) + f" ({len(rows)} records)</summary>" + body + "</details>") if folded else "<h2>" + html.escape(title) + "</h2>" + body)
    table("Asset attribute values", ["Position / field", "Before", "Returned", "Observation"],
          [(a["id"] + " / " + a["attribute"], observed(a["before_present"], a["before"]),
            observed(a["after_present"], a["after"]), a["status"]) for a in report["asset_attributes"]])
    table("Identity and block changes", ["Position", "Observation", "Before", "Returned"],
          [(a["id"], a["status"], a["before"], a["after"]) for a in report["asset_changes"]])
    for title, key in (("Layouts", "layout_changes"), ("Block definitions", "block_changes"),
                       ("Named layers, styles and tables", "named_table_changes"), ("Header values", "header_changes")):
        table(title, ["Record", "Before", "Returned"],
              [(k, observed(v["before"]["present"], v["before"]["value"]),
                observed(v["after"]["present"], v["after"]["value"])) for k, v in report[key].items()], folded=key in {"named_table_changes", "header_changes"})
    table("Drawing records to inspect", ["Handle / type", "Scope before / returned", "Observation", "Fields"],
          [(a["handle"] + " / " + str(a["before_type"]) + " to " + str(a["after_type"]),
            str(a["before_scope"]) + " / " + str(a["after_scope"]), a["category"],
            ", ".join(a["fields"]) if a["category"] == "same type changed" else f"Entire record; {len(a['fields'])} explicit fields")
           for a in report["drawing_changes"]])
    table("All drawing record field values", ["Handle / type", "Scope before / returned", "Field", "Before", "Returned"],
          [(a["handle"] + " / " + str(a["before_type"]) + " to " + str(a["after_type"]),
            str(a["before_scope"]) + " / " + str(a["after_scope"]), k,
            observed(v["before"]["present"], v["before"]["value"]), observed(v["after"]["present"], v["after"]["value"]))
           for a in report["drawing_changes"] for k, v in a["fields"].items()], folded=True)
    table("Strict entity queue summary", ["Observation at handle", "Count"], list(report["entity_partitions"].items()))
    table("Every strict entity difference remains open", ["Handle", "Observation", "Type before / returned", "Changed group codes", "Strict index"],
          [(a["handle"], a["category"], str(a["before_type"]) + " / " + str(a["after_type"]),
            ", ".join(sorted(a["changed_groups"], key=int)), a["strict_difference_index"]) for a in report["entity_changes"]], folded=True)
    lines += ["## Boundaries and next step", "", report["boundary"], "",
              "Qualify the intended receiver/settings, inspect appearance and editable data, investigate every remaining difference, then retain an owner-reviewed receiving checklist. No context update is promoted by this report.", "",
              "Files: review.json, strict-comparison.json, originals/before.dxf, originals/after.dxf and receipt.json.", ""]
    parts += ["<h2>Boundaries and next step</h2><p>" + html.escape(report["boundary"]) + "</p><p>" + html.escape(lines[-4]) + "</p>",
              "<p><a href='review.json'>Exact review data</a> · <a href='strict-comparison.json'>Full strict comparison</a> · <a href='originals/before.dxf'>Original drawing</a> · <a href='originals/after.dxf'>Returned drawing</a> · <a href='receipt.json'>File receipt</a></p>"]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    (out / "REPORT.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>CAD receiving review</title><style>body{font:17px/1.5 system-ui;max-width:70rem;margin:2rem auto;padding:0 1rem;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:.9rem;margin:1rem 0}td,th{border:1px solid #bbb;padding:.5rem;text-align:left;vertical-align:top}th{background:#eee}details{margin:1.5rem 0}summary{cursor:pointer;font-weight:bold}a{color:#064e8a}@media(max-width:600px){table,thead,tbody,tr,th,td{display:block;width:auto}thead{display:none}tr{margin-bottom:1rem}td{border-bottom:0}td::before{content:attr(data-label) ': ';font-weight:bold}td:last-child{border-bottom:1px solid #bbb}}</style><main>" + "".join(parts) + "</main></html>", encoding="utf-8", newline="\n")


def review(source, returned, plan, out):
    source, returned, out = Path(source).resolve(), Path(returned).resolve(), Path(out).resolve()
    if out.exists() or any(out == p or out in p.parents for p in (source, returned)):
        raise InputError("Use an unused review folder outside input files; retain earlier evidence")
    before, after = snapshot(source), snapshot(returned)
    strict = compare(before, after, plan)
    report = review_data(before, after, strict, load(source), load(returned), plan)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cad-review-", dir=out.parent) as tmp:
        stage = Path(tmp) / "packet"
        (stage / "originals").mkdir(parents=True)
        for name, path, expected in (("before", source, before["sha256"]), ("after", returned, after["sha256"])):
            saved = stage / "originals" / (name + ".dxf")
            saved.write_bytes(path.read_bytes())
            if digest(saved) != expected or digest(path) != expected:
                raise InputError("Drawing changed during review; retry from retained versions")
        if plan is not None:
            write_json(stage / "originals/plan.json", plan)
        write_json(stage / "strict-comparison.json", strict)
        write_json(stage / "review.json", report)
        render_review(stage, report)
        write_json(stage / "receipt.json", {"schema": "cad-review-receipt-1", "ezdxf": ezdxf.__version__, "python": sys.version,
                   "method_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                   "files": {p.relative_to(stage).as_posix(): digest(p) for p in sorted(stage.rglob("*")) if p.is_file()},
                   "acceptance": "not performed", "scope": "Retained files and declared decoded comparison; hashes are not authenticated signatures"})
        if out.exists():
            raise InputError("Review destination appeared during run; refusing to replace it")
        stage.rename(out)
    return report


def write_packet(source, snap, out):
    out = Path(out)
    if out.exists():
        raise InputError("Output folder already exists; use a new destination to retain history")
    out.mkdir(parents=True)
    (out / "source.dxf").write_bytes(Path(source).read_bytes())
    write_json(out / "snapshot.json", snap)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["ict_id", "tag", "manufacturer", "model", "serial_number", "size", "status"])
    writer.writeheader()
    nodes = []
    for a in snap["assets"]:
        at = a["attributes"]
        writer.writerow(dict(ict_id=a["id"], tag=at["TAG"], manufacturer=at.get("MANUFACTURER", ""),
                             model=at.get("MODEL", ""), serial_number=at.get("SERIAL", ""),
                             size=at.get("SIZE", ""), status="unverified"))
        nodes.append({"id": a["id"], "tag": at["TAG"], "attributes": at,
                      "source": {"sha256": snap["sha256"], "insert_handle": a["handle"]}, "status": "unverified"})
    (out / "asset_candidates.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="")
    write_json(out / "cad_context.json", {"schema": "cad-context-1", "nodes": nodes, "relationships": [],
                                       "note": "Attribute context snapshot only; pipe connectivity is not inferred. "
                                               "Map reviewed IDs to one-map site/plant/unit identities explicitly."})
    (out / "README.txt").write_text("Draft DXF attribute context. source.dxf retains the exact supplied bytes.\n"
                                   "No receiving-CAD, installed-asset or engineering acceptance is implied.\n",
                                   encoding="utf-8", newline="\n")


def apply(source, plan, out):
    before = snapshot(source)
    edits = validate_plan(before, plan)
    if Path(out).exists():
        raise InputError("Output folder already exists")
    doc = load(source)
    if digest(source) != before["sha256"]:
        raise InputError("Source changed after inspection; proposal is stale")
    for handle, change in edits.items():
        doc.entitydb[handle].dxf.text = change["after"]
    # Stage, reload and compare before any accepted packet is emitted.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "candidate.dxf"
        doc.saveas(candidate)
        after = snapshot(candidate)
        report = compare(before, after, plan)
        if report["unexpected"]:
            raise InputError("Candidate changes more than the declared attributes; no packet written")
        if digest(source) != before["sha256"]:
            raise InputError("Source changed during editing; proposal is stale")
        write_packet(source, before, out)
        (Path(out) / "candidate.dxf").write_bytes(candidate.read_bytes())
    write_json(Path(out) / "candidate.snapshot.json", after)
    write_json(Path(out) / "plan.json", plan)
    write_json(Path(out) / "comparison.json", report)
    # Publish the proposed new context separately; the original snapshot is immutable.
    write_packet(Path(out) / "candidate.dxf", after, Path(out) / "candidate-context")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("drawing")
    inspect.add_argument("--out", required=True)
    edit = sub.add_parser("apply")
    edit.add_argument("drawing")
    edit.add_argument("plan")
    edit.add_argument("--out", required=True)
    diff = sub.add_parser("compare")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--plan")
    diff.add_argument("--out", required=True)
    rev = sub.add_parser("review", help="Explain a returned DXF in a readable packet; strict differences still fail")
    rev.add_argument("before")
    rev.add_argument("after")
    rev.add_argument("--plan")
    rev.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        if args.command == "inspect":
            value = snapshot(args.drawing)
            write_packet(args.drawing, value, args.out)
            print(f"{len(value['assets'])} draft assets -> {args.out}")
        elif args.command == "apply":
            value = apply(args.drawing, json.loads(Path(args.plan).read_text(encoding="utf-8-sig")), args.out)
            print(f"{len(value['expected_edits'])} proposed edits; no unexpected entity/header changes")
        elif args.command == "review":
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8-sig")) if args.plan else None
            value = review(args.before, args.after, plan, args.out)
            print(f"Review: {Path(args.out) / 'REPORT.html'}; strict {value['strict_status']}: {value['strict_difference_count']} differences; no acceptance")
            return int(value["strict_status"] != "pass")
        else:
            if Path(args.out).exists() or Path(args.out).resolve() in {Path(args.before).resolve(), Path(args.after).resolve()}:
                raise InputError("Comparison destination exists or would overwrite a source")
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8-sig")) if args.plan else None
            value = compare(snapshot(args.before), snapshot(args.after), plan)
            write_json(args.out, value)
            print(f"{value['status']}: {len(value['unexpected'])} unexpected differences")
            return int(bool(value["unexpected"]))
        return 0
    except (InputError, OSError, ValueError, ezdxf.DXFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
