"""Generate three engineering component views from the same selected context.

Unknowns, competing claims and original roots remain represented. Editorial
annotations are proposals; they do not overwrite source facts or add corroboration.
"""
import copy
import csv
import io

import context_basis as cb

SCHEMA = "engineering-component-drafts-1"
LIST_FIELDS = ("class", "description", "manufacturer", "model", "serial_number",
               "rated_flow", "variable", "engineering_unit")
SHEET_FIELDS = (*LIST_FIELDS, "design_temperature", "range_low", "range_high",
                "fail_position", "operating_limits", "trip_settings")
TARGETS = ("equipment_instrument_list", "item_datasheet_scaffold", "loop_control_narrative_outline")


def selected(view, scope=None, item=None):
    cb.require(not (scope and item), "select a scope or an item")
    if item is not None:
        return [view.resolve(item)]
    if scope is None:
        return sorted(view.entities)
    values = sorted(identifier for identifier, entity in view.entities.items()
                    if entity["scope"] == scope or entity["scope"].startswith(scope + "/"))
    cb.require(values, "selected scope has no represented entities")
    return values


def relation_field(view, subject, predicate):
    all_rows = [e for e in view.edges[subject]
                if e["subject"] == subject and e["predicate"] == predicate]
    evidence = [view.evidence(e) for e in sorted(all_rows, key=lambda e: e["id"])]
    active = [e for e in all_rows if view.active(e)]
    content = [{k: e[k] for k in ("id", "subject", "predicate", "object", "direction", "review")}
               for e in sorted(active, key=lambda e: e["id"])]
    return {"subject": subject, "predicate": predicate,
            "state": "sourced_unreviewed" if active else "inactive_evidence" if all_rows else "unknown",
            "relationships": evidence, "dependency": [subject, "relation:" + predicate],
            "content_fingerprint": cb.digest(content), "evidence_fingerprint": cb.digest(evidence),
            "distinct_declared_roots": sorted({root for row in active for root in row["roots"]})}


def annotation_field(view, subject, field):
    return relation_field(view, subject, field) if field in cb.RELATIONS else view.field(subject, field)


def checked_annotations(basis, annotations, history_bases):
    """Verify immutable edit lineage against its actual retained pre-edit basis."""
    known = dict(history_bases or {})
    known[cb.digest(basis)] = basis
    # Same-snapshot edits can be checked without external history. Revised inputs
    # need the actual prior basis; hashes alone do not reconstruct its facts.
    for n in range(len(basis["corrections"])):
        before = {**basis, "corrections": basis["corrections"][:n]}
        known[cb.digest(before)] = before
    retained = {}
    for annotation in [*basis["corrections"], *annotations]:
        cb.require(type(annotation) is dict and type(annotation.get("id")) is str,
                   "editorial annotation needs id")
        identifier = annotation["id"]
        cb.require(identifier not in retained or cb.canonical(retained[identifier]) == cb.canonical(annotation),
                   "conflicting versions of an editorial annotation")
        sha = annotation.get("basis_sha256")
        cb.require(sha in known, "editorial correction basis unavailable; retain its verified history")
        reference = known[sha]
        cb.require(cb.digest(reference) == sha, "editorial correction historical basis identity mismatch")
        expected = new_annotation(reference, annotation.get("subject"), annotation.get("field"),
                                  annotation.get("value"), annotation.get("rationale"))
        cb.require(cb.canonical(annotation) == cb.canonical(expected),
                   "editorial correction lineage/fingerprint differs from retained basis")
        retained[identifier] = copy.deepcopy(annotation)
    return retained


def generate(basis, *, scope=None, item=None, annotations=(), history_bases=None):
    view = cb.View(basis)
    chosen = selected(view, scope, item)
    assets = [i for i in chosen if view.entities[i]["identity_role"] in ("functional_position", "physical_item")]
    components = {target: {"status": "draft_for_engineering_review", "items": {}, "gaps": []}
                  for target in TARGETS}
    for subject in assets:
        for target, names in ((TARGETS[0], LIST_FIELDS), (TARGETS[1], SHEET_FIELDS)):
            fields = {name: view.field(subject, name) for name in names}
            components[target]["items"][subject] = {"identity": copy.deepcopy(view.entities[subject]),
                                                    "fields": fields}
            for name, field in fields.items():
                if field["state"] in ("unknown", "inactive_evidence", "disputed"):
                    components[target]["gaps"].append({"subject": subject, "field": name, "state": field["state"]})
        classes = [r["value"] for r in view.field(subject, "class")["alternatives"] if r["active_source"]]
        if "controller" in classes:
            fields = {"reads": relation_field(view, subject, "reads"),
                      "commands": relation_field(view, subject, "commands"),
                      **{name: view.field(subject, name) for name in
                         ("setpoint", "sequence", "fail_position", "trip_settings", "operating_limits")}}
            components[TARGETS[2]]["items"][subject] = {"identity": copy.deepcopy(view.entities[subject]),
                                                       "fields": fields,
                                                       "qualification": "Recorded input/command links scaffold an outline; no unstated strategy or operating action inferred."}
            for name, field in fields.items():
                if field["state"] in ("unknown", "inactive_evidence", "disputed"):
                    components[TARGETS[2]]["gaps"].append({"subject": subject, "field": name, "state": field["state"]})
    if not components[TARGETS[2]]["items"]:
        components[TARGETS[2]]["gaps"].append({"field": "controller_identity_and_behavior",
                                             "state": "unknown", "reason": "No sourced controller class in selected context; outline only."})
    retained = checked_annotations(basis, annotations, history_bases)
    rendered = []
    for annotation in retained.values():
        subject, field = annotation.get("subject"), annotation.get("field")
        cb.require(type(subject) is str and type(field) is str and bool(field),
                   "editorial annotation needs subject/field")
        cb.require("value" in annotation and type(annotation.get("rationale")) is str
                   and annotation["rationale"].strip(), "editorial annotation needs value and rationale")
        expected = annotation.get("expected_content_fingerprint")
        # A selected derived view must not expose annotations for other items.
        # Full private corrections remain in the basis, including absent subjects.
        if subject not in chosen and (scope is not None or item is not None):
            continue
        if subject not in view.entities:
            rendered.append({"annotation": annotation, "state": "subject_unavailable",
                             "current_content_fingerprint": None,
                             "authority": "Retained proposal; subject absent in current inputs, not evidence of physical removal"})
            continue
        field_basis = annotation_field(view, subject, field)
        current = field_basis["content_fingerprint"]
        rendered.append({"annotation": annotation,
                         "state": "needs_rebase" if expected != current or annotation["expected_evidence_fingerprint"]
                         != field_basis["evidence_fingerprint"] else "proposed_editorial",
                         "current_content_fingerprint": current,
                         "current_evidence_fingerprint": field_basis["evidence_fingerprint"],
                         "authority": "Proposed edit, not a new independent observation or authenticated approval"})
    return {"schema": SCHEMA, "basis_sha256": cb.digest(basis), "namespace": basis["namespace"],
            "selection": {"scope": scope, "item": item, "entities": chosen},
            "components": components, "annotations": rendered,
            "basis_role": "Derived views with retained source roots; not independent corroboration",
            "review": "Engineering interpretation and receiving acceptance remain required."}


def new_annotation(basis, subject, field, value, rationale):
    view = cb.View(basis)
    subject = view.resolve(subject)
    cb.text(rationale, "edit rationale")
    cb.json_value(value)
    cb.text(field, "edit field")
    field_basis = annotation_field(view, subject, field)
    row = {"subject": subject, "field": field, "value": copy.deepcopy(value),
           "field_kind": "relationship" if field in cb.RELATIONS else "claim",
           "rationale": rationale, "expected_content_fingerprint": field_basis["content_fingerprint"],
           "expected_evidence_fingerprint": field_basis["evidence_fingerprint"],
           "basis_sha256": cb.digest(basis), "kind": "editorial_proposal",
           "roots": field_basis["distinct_declared_roots"]}
    row["id"] = "edit-" + cb.digest(row)[:24]
    return row


def reimport(basis, draft, *, history_bases=None):
    """Admit exact own-format derivations and explicit edits without adding source claims."""
    cb.require(type(draft) is dict and draft.get("schema") == SCHEMA,
               "unsupported component draft")
    cb.require(draft.get("basis_sha256") == cb.digest(basis), "draft basis changed; regenerate and explicitly rebase edits")
    selection = draft.get("selection", {})
    expected = generate(basis, scope=selection.get("scope"), item=selection.get("item"), history_bases=history_bases)
    cb.require(cb.canonical(draft.get("components")) == cb.canonical(expected["components"])
               and cb.canonical(selection) == cb.canonical(expected["selection"])
               and draft.get("namespace") == basis["namespace"],
               "derived facts changed; submit explicit editorial annotations, not replacement source evidence")
    result = copy.deepcopy(basis)
    existing = {r["id"]: r for r in result["corrections"]}
    for wrapped in draft.get("annotations", []):
        row = wrapped.get("annotation")
        cb.require(type(row) is dict and row.get("kind") == "editorial_proposal",
                   "derived contribution must be an explicit editorial proposal")
        if row.get("id") in existing:
            cb.require(cb.canonical(existing[row["id"]]) == cb.canonical(row), "edit id has different content")
            continue
        checked = new_annotation(basis, row.get("subject"), row.get("field"), row.get("value"),
                                 row.get("rationale"))
        cb.require(cb.canonical(row) == cb.canonical(checked), "editorial annotation basis/lineage mismatch")
        result["corrections"].append(copy.deepcopy(row))
        existing[row["id"]] = row
    cb.validate(result)
    cb.require(cb.canonical(result["claims"]) == cb.canonical(basis["claims"])
               and cb.canonical(result["sources"]) == cb.canonical(basis["sources"]),
               "derived reimport must not manufacture source claims")
    return result


def all_fields(draft):
    result = {}
    for target, component in draft["components"].items():
        for subject, item in component["items"].items():
            for field, value in item["fields"].items():
                result[(target, subject, field)] = value
    return result


def changes(previous, current):
    cb.require(previous.get("schema") == SCHEMA and current.get("schema") == SCHEMA
               and previous["namespace"] == current["namespace"], "draft comparison needs same supported namespace")
    before, after = all_fields(previous), all_fields(current)
    rows = []
    for key in sorted(before.keys() | after.keys()):
        a, b = before.get(key), after.get(key)
        if a is None or b is None:
            state = "added" if a is None else "removed"
        elif a["content_fingerprint"] != b["content_fingerprint"]:
            state = "content_changed"
        elif a["evidence_fingerprint"] != b["evidence_fingerprint"]:
            state = "basis_changed"
        else:
            continue
        rows.append({"component": key[0], "subject": key[1], "field": key[2], "change": state,
                     "before": copy.deepcopy(a), "after": copy.deepcopy(b),
                     "review": "Revisit affected review basis; no automatic approval transfer."})
    return {"schema": "engineering-component-impact-1", "changes": rows,
            "selection_policy_changed": any(previous.get("selection", {}).get(k) != current.get("selection", {}).get(k)
                                            for k in ("scope", "item")),
            "annotations": copy.deepcopy(current.get("annotations", [])),
            "scope": "Explicit field/relation dependencies only; unsupported legacy consumers keep conservative refresh."}


def readable(field):
    if "relationships" in field:
        rows = field["relationships"]
        return "; ".join(f"{r['object']} [direction={r['direction']}; {r['source']} "
                         f"rev {r['source_record']['revision']}; {r['locator']}; "
                         + ("supplied" if r["active_source"] else "INACTIVE") + "]" for r in rows) or "UNKNOWN"
    rows = field.get("alternatives", [])
    if not rows:
        return "UNKNOWN"
    return "; ".join(cb.canonical(r["value"]) + (" " + r["unit"] if r.get("unit") else "")
                     + f" [{r['source']} rev {r['source_record']['revision']}; {r['locator']}; "
                     + ("supplied" if r["active_source"] else "INACTIVE") + "]" for r in rows)


def csv_cell(value):
    # Typed original remains in drafts.json; this protects the spreadsheet display.
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def render(draft):
    """Return readable artifacts; the complete typed/source basis stays in drafts.json."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["qualified_id", "tag", "identity_role", *LIST_FIELDS])
    for subject, item in draft["components"][TARGETS[0]]["items"].items():
        writer.writerow([csv_cell(v) for v in [subject, item["identity"]["tag"],
                         item["identity"]["identity_role"],
                         *[readable(item["fields"][field]) for field in LIST_FIELDS]]])
    result = {"equipment-instruments.csv": stream.getvalue()}
    for target, filename, title in ((TARGETS[1], "datasheets.md", "Datasheet scaffolds"),
                                     (TARGETS[2], "control-outline.md", "Loop/control narrative outlines")):
        lines = ["# " + title, "", "Draft for engineering review. UNKNOWN and INACTIVE remain explicit.", ""]
        for subject, item in draft["components"][target]["items"].items():
            lines += ["## " + subject.replace("\n", " "), ""]
            for name, field in item["fields"].items():
                lines.append("- " + name + " (" + field["state"] + "): " + readable(field).replace("\n", " "))
            lines.append("")
        if not draft["components"][target]["items"]:
            lines += ["No supported items for this target; inspect the explicit gaps in drafts.json.", ""]
        lines += ["Editorial proposals (not independent evidence):", ""]
        for row in draft["annotations"]:
            edit = row["annotation"]
            lines.append("- " + cb.canonical(edit["subject"]) + " / " + cb.canonical(edit["field"])
                         + ": " + cb.canonical(edit["value"]) + " — " + row["state"])
        result[filename] = "\n".join(lines) + "\n"
    return result

