"""Revision differences across a whole represented engineering context basis.

This is separate from generated-component dependencies. A changed declaration is
not an accepted plant change, and an unchanged declaration is not verification.
"""
import copy

import context_basis as cb
import context_components as cc

SCHEMA = "engineering-context-basis-impact-1"
ANCHOR_FIELDS = ("subject", "predicate", "source", "locator", "role")


def field(view, subject, predicate, relationship=False):
    """Keep the existing query evidence/fingerprints, including inactive rows."""
    if subject in view.entities:
        return (cc.relation_field(view, subject, predicate) if relationship
                else view.field(subject, predicate))
    return {"subject": subject, "predicate": predicate, "state": "subject_unavailable",
            "relationships" if relationship else "alternatives": [],
            "dependency": [subject, "relation:" + predicate if relationship else predicate],
            "content_fingerprint": None, "evidence_fingerprint": None,
            "distinct_declared_roots": []}


def literal(row, relationship):
    # Compare retained typed literals, without quantity conversion or collapsing
    # false/0, integer/float, signed zero, null/empty or nested typed values.
    return cb.canonical([row["object"], row["direction"]] if relationship
                        else [row["value"], row.get("unit")])


def occurrence_matching(before, after):
    """Match only unique declared source occurrences, without their mutable target.

    A source location can name several relations. Keep those ambiguous groups
    visible rather than pairing them by array position or choosing a target.
    """
    def grouped(rows):
        result = {}
        for row in rows:
            key = cb.canonical([row[k] for k in ANCHOR_FIELDS])
            result.setdefault(key, []).append(row)
        return result
    a, b = grouped(before), grouped(after)
    paired, ambiguous = [], []
    for key in sorted(a.keys() | b.keys()):
        old, new = a.get(key, []), b.get(key, [])
        if len(old) == len(new) == 1:
            paired.append((old[0], new[0]))
        elif len(old) > 1 or len(new) > 1:
            row = (old or new)[0]
            ambiguous.append({"anchor": {k: row[k] for k in ANCHOR_FIELDS},
                              "before_occurrence_ids": sorted(r["id"] for r in old),
                              "after_occurrence_ids": sorted(r["id"] for r in new)})
    return paired, {"unambiguous_common_anchors": len(paired), "ambiguous_anchors": ambiguous,
                    "policy": "Match unique subject/predicate/source/locator/role declarations, excluding mutable target. "
                              "Multiple relations at one anchor are not paired; their individual content attribution "
                              "remains unresolved even when the change is classified basis_changed."}


def field_change(before, after, relationship):
    name = "relationships" if relationship else "alternatives"
    a, b = before[name], after[name]
    if not a or not b:
        return "added" if not a and b else "removed" if a else None
    if before["evidence_fingerprint"] == after["evidence_fingerprint"]:
        return None
    old_literals = {r["id"]: literal(r, relationship) for r in a}
    new_literals = {r["id"]: literal(r, relationship) for r in b}
    if (set(old_literals.values()) != set(new_literals.values())
            or any(old_literals[k] != new_literals[k] for k in old_literals.keys() & new_literals.keys())):
        return "content_changed"
    if relationship and any(literal(old, True) != literal(new, True)
                            for old, new in occurrence_matching(a, b)[0]):
        return "content_changed"
    # Distinguish availability changes even when a second source still supplies
    # the same value. A changed locator/source with the same active literal is
    # evidence change; occurrence ids alone do not establish changed content.
    old_active = {r["id"]: r["active_source"] for r in a}
    new_active = {r["id"]: r["active_source"] for r in b}
    if (before["state"] != after["state"]
            or any(old_active[k] != new_active[k] for k in old_active.keys() & new_active.keys())
            or {literal(r, relationship) for r in a if r["active_source"]}
            != {literal(r, relationship) for r in b if r["active_source"]}):
        return "availability_changed"
    return "basis_changed"


def fields(before, after, relationship=False):
    collection = "relationships" if relationship else "claims"
    keys = sorted({(row["subject"], row["predicate"])
                   for view in (before, after) for row in view.basis[collection]})
    result = []
    for subject, predicate in keys:
        a = field(before, subject, predicate, relationship)
        b = field(after, subject, predicate, relationship)
        change = field_change(a, b, relationship)
        if change:
            row = {"subject": subject, "predicate": predicate,
                   "change": change, "before": a, "after": b}
            if relationship:
                row["occurrence_matching"] = occurrence_matching(a["relationships"], b["relationships"])[1]
            result.append(row)
    return result


def records(before, after, **label):
    """Exact identity/metadata records; absent records remain distinct from null."""
    result = []
    for identifier in sorted(before.keys() | after.keys()):
        a, b = before.get(identifier), after.get(identifier)
        if cb.canonical(a) != cb.canonical(b):
            result.append({**label, "id": identifier,
                           "change": "added" if a is None else "removed" if b is None else "record_changed",
                           "before": copy.deepcopy(a), "after": copy.deepcopy(b)})
    return result


def sources(view):
    return {key: {"record": copy.deepcopy(value),
                  "declared_lineage": copy.deepcopy(cb.lineage_records(view.sources, key)),
                  "active_declared_lineage": all(r["status"] in cb.ACTIVE_SOURCES
                                                  for r in cb.lineage_records(view.sources, key))}
            for key, value in view.sources.items()}


def changes(previous, current):
    before, after = cb.View(previous), cb.View(current)
    cb.require(previous["namespace"] == current["namespace"],
               "basis comparison needs same supported namespace")
    source_changes = records(sources(before), sources(after))
    for row in source_changes:
        if (row["change"] == "record_changed"
                and cb.canonical(row["before"]["record"]) == cb.canonical(row["after"]["record"])):
            row["change"] = "lineage_changed"
    identities = records(before.entities, after.entities, kind="entity")
    identities += records(cb.index(previous["boundaries"], "boundary"),
                          cb.index(current["boundaries"], "boundary"), kind="boundary")
    excluded = {"schema", "version", "namespace", "entities", "boundaries", "sources", "claims", "relationships"}
    metadata = []
    for key in sorted((previous.keys() | current.keys()) - excluded):
        if (key in previous) != (key in current) or cb.canonical(previous.get(key)) != cb.canonical(current.get(key)):
            metadata.append({"field": key, "before_present": key in previous, "after_present": key in current,
                             "before": copy.deepcopy(previous.get(key)), "after": copy.deepcopy(current.get(key))})
    return {"schema": SCHEMA, "namespace": previous["namespace"],
            "before_basis_sha256": cb.digest(previous), "after_basis_sha256": cb.digest(current),
            "claims": fields(before, after), "relationships": fields(before, after, True),
            "identities": identities, "sources": source_changes, "metadata": metadata,
            "qualification": "All represented fields and declared records, including inactive evidence. "
                             "Typed literals are compared without unit normalization; absent fields remain unknown. "
                             "Source roots and reviews are declarations, not independent observations or engineering acceptance. "
                             "No downstream output coverage is inferred; component impact is reported separately."}
