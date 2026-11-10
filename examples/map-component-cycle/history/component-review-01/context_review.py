"""Offline component review and basis-bound text proposals; no authenticated approval."""
import json
from pathlib import Path

import context_basis as cb
import context_components as cc
import context_packet as cp
import context_review_html

SCHEMA = "engineering-context-review-edit-1"
MAX_HTML_BYTES = 32 * 1024 * 1024
MAX_EDIT_BYTES = 128 * 1024
TARGET_LABELS = dict(zip(cc.TARGETS, ("Equipment and instrument list", "Item datasheet scaffold",
                                     "Loop and control narrative outline")))


def edit_fields(opened, subject):
    return sorted({name for component in opened["draft"]["components"].values()
                   for identifier, item in component["items"].items() if identifier == subject
                   for name in item["fields"]} | {"draft_review_note"})


def field_payload(field):
    """JSON numbers are display strings; a browser cannot round engineering values."""
    rows = field.get("alternatives", field.get("relationships", []))
    evidence = []
    for row in rows:
        original = row.get("value")
        kind = {str: "text", int: "integer", float: "decimal", bool: "boolean", list: "array",
                dict: "object", type(None): "null"}.get(type(original), "unsupported")
        value = (cb.canonical(row["value"]) if "value" in row else
                 row["subject"] + " — " + row["predicate"] + " → " + row["object"])
        source = row["source_record"]
        evidence.append({"value_text": value, "unit_text": cb.canonical(row.get("unit")),
                         "value_display": original if type(original) is str else value,
                         "unit_display": row.get("unit") if type(row.get("unit")) is str else
                         cb.canonical(row.get("unit")), "value_kind": kind if "value" in row else "relationship",
                         "active": row["active_source"], "source_id": row["source"],
                         "source_label": str(source.get("path") or source["id"]),
                         "revision_label": str(source["revision"]) if source["revision"] is not None else "unknown",
                         "owner_label": str(source["owner"]) if source["owner"] is not None else "unknown",
                         "applicability_label": str(source["applicability"]) if source["applicability"] is not None else "unknown",
                         "locator": row["locator"], "direction": row.get("direction"),
                         "review_text": cb.canonical(row["review"]),
                         "lineage_text": cb.canonical(row["source_lineage"]),
                         "source_text": cb.canonical(row["source_record"])})
    return {"state": field["state"], "evidence": evidence,
            "content_fingerprint": field["content_fingerprint"],
            "evidence_fingerprint": field["evidence_fingerprint"],
            "roots": field["distinct_declared_roots"]}


def payload(opened):
    view = cb.View(opened["basis"])
    chosen = opened["draft"]["selection"]["entities"]
    items = []
    for subject in chosen:
        targets = {name: {"label": TARGET_LABELS[name],
                          "field_order": list(component["items"][subject]["fields"]),
                          "fields": {key: field_payload(field) for key, field in
                                     component["items"][subject]["fields"].items()}}
                   for name, component in opened["draft"]["components"].items()
                   if subject in component["items"]}
        if not targets:
            continue
        fields = {name: field_payload(cc.annotation_field(view, subject, name))
                  for name in edit_fields(opened, subject)}
        notes = [{"field": wrapped["annotation"]["field"],
                  "value_text": cb.canonical(wrapped["annotation"]["value"]),
                  "rationale": wrapped["annotation"]["rationale"], "state": wrapped["state"]}
                 for wrapped in opened["draft"]["annotations"]
                 if wrapped["annotation"]["subject"] == subject]
        items.append({"id": subject, "tag": view.entities[subject]["tag"],
                      "role": view.entities[subject]["identity_role"], "targets": targets,
                      "edit_fields": fields, "notes": notes})
    return {"schema": SCHEMA, "basis_sha256": cb.digest(opened["basis"]),
            "receipt_sha256": opened["receipt_sha256"], "namespace": opened["basis"]["namespace"],
            "items": items, "omissions_text": cb.canonical(opened["basis"]["omissions"]),
            "boundaries_text": cb.canonical(opened["basis"]["boundaries"])}


def render(opened):
    result = context_review_html.render(payload(opened)).encode("utf-8")
    cb.require(len(result) <= MAX_HTML_BYTES, "review HTML exceeds 32 MiB limit; select a smaller draft scope")
    return result


def write(packet, destination):
    opened = cp.open_packet(packet)
    data = render(opened)
    # Exclusive creation also refuses broken symlinks and never replaces earlier review evidence.
    with Path(destination).open("xb") as output:
        output.write(data)
    return {"html": str(Path(destination).absolute()), "sha256": cb.raw_sha(data),
            "bytes": len(data), "basis_sha256": cb.digest(opened["basis"]),
            "qualification": "Offline draft review; source selection is not an access boundary"}


def verify(packet, html):
    path = Path(html)
    cb.require(path.stat().st_size <= MAX_HTML_BYTES, "review HTML exceeds declared limit")
    cb.require(path.read_bytes() == render(cp.open_packet(packet)), "review HTML differs from retained packet")
    return {"verified": True, "qualification": "Exact delivered view replay, not engineering acceptance"}


def apply(packet, request_path, destination):
    opened = cp.open_packet(packet)
    request = cb.read_json(request_path, MAX_EDIT_BYTES)
    keys = {"schema", "basis_sha256", "receipt_sha256", "subject", "field", "value", "rationale",
            "expected_content_fingerprint", "expected_evidence_fingerprint", "roots"}
    cb.require(type(request) is dict and set(request) == keys and request["schema"] == SCHEMA,
               "unsupported review proposal shape")
    cb.require(request["receipt_sha256"] == opened["receipt_sha256"] and
               request["basis_sha256"] == cb.digest(opened["basis"]),
               "review proposal packet changed; reopen the current review and explicitly rebase")
    subject, field = request["subject"], request["field"]
    cb.require(type(subject) is str and subject in opened["draft"]["selection"]["entities"],
               "review proposal subject outside selected draft")
    cb.require(any(subject in component["items"] for component in opened["draft"]["components"].values()),
               "review proposal subject has no delivered component")
    cb.require(type(field) is str and field in edit_fields(opened, subject),
               "review proposal field outside delivered component")
    cb.require(type(request["value"]) is str and len(request["value"]) <= 32768,
               "review supports bounded text proposals only")
    cb.require(type(request["rationale"]) is str and len(request["rationale"]) <= 32768,
               "review rationale exceeds limit")
    row = cc.new_annotation(opened["basis"], subject, field, request["value"], request["rationale"])
    cb.require(all(cb.canonical(request[key]) == cb.canonical(row[key]) for key in
                   ("expected_content_fingerprint", "expected_evidence_fingerprint", "roots")),
               "review proposal source dependencies differ")
    out = cp.write_edited(packet, destination, annotation=row)
    return {"packet": str(out), "receipt_sha256": cp.open_packet(out)["receipt_sha256"],
            "qualification": "Retained text proposal; original facts unchanged, no engineering approval"}
