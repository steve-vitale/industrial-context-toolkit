"""Bounded engineering projection basis: typed claims, source lineage and explicit relationships.

This is an interchange/projection basis over supported inputs, not context-map-1
storage, a source authority, an authentication service or an engineering approval.
"""
import copy
import hashlib
import json
import math
import re
from collections import defaultdict, deque
from fractions import Fraction
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

SCHEMA = "engineering-context-basis-1"
VERSION = 1
MAX_BYTES = 128 * 1024 * 1024
ACTIVE_SOURCES = {"supplied", "derived"}
SOURCE_STATES = ACTIVE_SOURCES | {"withdrawn", "superseded", "unavailable", "missing"}
REVIEW_STATES = {"unreviewed", "proposed", "confirmed", "corrected", "rejected"}
RELATIONS = {
    "piped_to": "Explicit consecutive process items; not network co-membership.",
    "network_member": "On the same recorded network; no adjacency or flow inference.",
    "signal_to": "Recorded signal association; not physical flow or established strategy.",
    "reads": "Explicitly described input to a controller.",
    "commands": "Explicitly described controller/final-element command association.",
    "measures": "Explicitly described measurement target.",
    "contains": "Declared hierarchy.",
    "associated_with": "Declared association; no physical/control implication.",
    "reported_installation_at": "Record links an item observation to a position; not installed truth.",
}
# Exact rational factors to common units. No temperature offsets, gauge/absolute
# pressure conversion, inferred dimensions, locale parsing or missing-unit guesses.
QUANTITIES = {
    "m3/h": ("volume_flow", Fraction(1, 3600)),
    "L/s": ("volume_flow", Fraction(1, 1000)),
    "L/min": ("volume_flow", Fraction(1, 60000)),
    "m3/s": ("volume_flow", Fraction(1)),
    "m": ("length", Fraction(1)),
    "mm": ("length", Fraction(1, 1000)),
    "in": ("length", Fraction(127, 5000)),
}
DECIMAL = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


class ContextError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContextError(message)


def canonical(value):
    """Keep JSON false/0, integer/float, signed zero and lexical text distinct."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ContextError("value is not finite JSON") from error


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def raw_sha(value):
    return hashlib.sha256(value).hexdigest()


def lossless_float(token):
    """Admit a finite float only when its JSON decimal roundtrip retains the value.

    Original source bytes remain authoritative for lexical notation. Unsupported
    precision/underflow is refused rather than converted into another number.
    """
    require(type(token) is str and len(token) <= 128 and DECIMAL.fullmatch(token),
            "number needs explicit bounded decimal notation")
    value = float(token)
    require(math.isfinite(value) and Decimal(token) == Decimal(str(value)),
            "lossy numeric conversion; retain exact source text or use a qualified decimal adapter")
    return value


def text(value, where):
    require(type(value) is str and bool(value.strip()), where + " needs nonempty text")
    return value


def json_value(value):
    """Reject non-JSON Python values without silently coercing their types."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        require(math.isfinite(value), "non-finite JSON number")
        return
    if type(value) is list:
        for item in value:
            json_value(item)
        return
    if type(value) is dict:
        require(all(type(key) is str for key in value), "JSON object keys need text")
        for item in value.values():
            json_value(item)
        return
    raise ContextError("value is not a builtin JSON type")


def read_json(path, limit=MAX_BYTES):
    path = Path(path)
    require(path.stat().st_size <= limit, "JSON input exceeds declared byte limit")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise ContextError("non-finite JSON constant: " + value)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=lossless_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ContextError("invalid UTF-8 JSON") from error


def qualified(site, plant, unit, tag):
    parts = [text(v, "identity component") for v in (site, plant, unit, tag)]
    require(all(v == v.strip() for v in parts), "identity needs clarification: outer whitespace")
    return "/".join(quote(v, safe="-._~") for v in parts)


def empty(namespace):
    return {"schema": SCHEMA, "version": VERSION, "namespace": text(namespace, "namespace"),
            "entities": [], "sources": [], "claims": [], "relationships": [],
            "boundaries": [], "corrections": [], "preparation": [], "omissions": []}


def index(rows, name):
    require(type(rows) is list, name + " must be a list")
    result = {}
    for row in rows:
        require(type(row) is dict, name + " entry must be an object")
        identifier = text(row.get("id"), name + " id")
        require(identifier not in result, "duplicate " + name + " id: " + identifier)
        result[identifier] = row
    return result


def root_sources(sources, source_id, seen=()):
    require(source_id in sources, "unknown source: " + source_id)
    require(source_id not in seen, "source lineage cycle")
    source = sources[source_id]
    roots = source.get("roots")
    require(type(roots) is list and roots and all(type(v) is str for v in roots)
            and len(set(roots)) == len(roots), "source roots must be unique nonempty ids")
    if roots == [source_id]:
        require(source["status"] != "derived", "derived source cannot declare itself independent")
        return [source_id]
    require(source_id not in roots, "source lineage cycle")
    return sorted({root for parent in roots
                   for root in root_sources(sources, parent, (*seen, source_id))})


def lineage_records(sources, source_id):
    """All declared derivation records, including intermediate sources."""
    root_sources(sources, source_id)  # Validate references and cycles first.
    pending, found = [source_id], set()
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        pending.extend(parent for parent in sources[current]["roots"] if parent != current)
    return [sources[key] for key in sorted(found)]


def record_id(kind, row):
    identity = [row[k] for k in ("subject", "predicate", "source", "locator", "role")]
    if kind == "relation":
        identity.append(row["object"])
    return kind + "-" + digest(identity)[:24]


def validate(basis):
    require(type(basis) is dict and basis.get("schema") == SCHEMA
            and type(basis.get("version")) is int and basis["version"] == VERSION,
            "unsupported engineering projection basis")
    json_value(basis)
    text(basis.get("namespace"), "namespace")
    entities, sources = index(basis.get("entities"), "entity"), index(basis.get("sources"), "source")
    boundaries = index(basis.get("boundaries"), "boundary")
    require(not (set(entities) & set(boundaries)), "entity is also an external boundary")
    for entity in entities.values():
        for key in ("tag", "scope", "identity_role"):
            text(entity.get(key), "entity " + key)
        require(entity["id"].startswith(entity["scope"] + "/"), "entity outside its declared scope")
        require(entity["scope"] == basis["namespace"]
                or entity["scope"].startswith(basis["namespace"] + "/"),
                "entity outside basis namespace")
        require(type(entity.get("aliases", [])) is list
                and all(type(a) is str and a for a in entity.get("aliases", [])),
                "entity aliases must be text")
    for source in sources.values():
        require(source.get("status") in SOURCE_STATES, "unknown source status")
        for key in ("revision", "owner", "applicability"):
            text(source.get(key), "source " + key)
        value = source.get("sha256")
        require(value is None or (type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)),
                "source sha256 is not a raw SHA-256")
        if source["status"] in ACTIVE_SOURCES:
            require(value is not None, "active source needs declared byte identity")
        root_sources(sources, source["id"])
    for collection, kind in (("claims", "claim"), ("relationships", "relation")):
        for row in index(basis.get(collection), kind).values():
            require(row.get("subject") in entities, kind + " has unknown subject")
            for key in ("predicate", "source", "locator", "role"):
                text(row.get(key), kind + " " + key)
            require(row["source"] in sources, kind + " has unknown source")
            require(row.get("roots") == root_sources(sources, row["source"]),
                    kind + " lineage disagrees with source roots")
            require(row.get("review", {}).get("status") in REVIEW_STATES,
                    kind + " needs explicit review state")
            require(row["id"] == record_id(kind, row), kind + " identity disagrees with source occurrence")
            if kind == "claim":
                require("value" in row, "claim must retain its typed value")
                require(row.get("unit") is None or type(row["unit"]) is str, "claim unit must be text or null")
            else:
                require(row.get("object") in entities or row.get("object") in boundaries,
                        "relation has unknown object")
                require(row["predicate"] in RELATIONS, "unsupported relation semantics")
                require(row.get("direction") in ("known", "unknown"), "relation direction must be explicit")
    for correction in index(basis.get("corrections"), "correction").values():
        require(correction.get("kind") == "editorial_proposal", "unsupported correction kind")
        for key in ("subject", "field", "rationale"):
            text(correction.get(key), "correction " + key)
        require(correction["subject"].startswith(basis["namespace"] + "/"),
                "correction subject outside namespace")
        require("value" in correction, "correction must retain its value")
        require(correction.get("field_kind") in ("claim", "relationship"), "correction needs field kind")
        for key in ("expected_content_fingerprint", "expected_evidence_fingerprint", "basis_sha256"):
            require(type(correction.get(key)) is str and re.fullmatch(r"[0-9a-f]{64}", correction[key]),
                    "correction needs " + key)
        roots = correction.get("roots")
        require(type(roots) is list and all(type(r) is str and r for r in roots)
                and roots == sorted(set(roots)), "correction roots must be sorted unique source ids")
        require(correction["id"] == "edit-" + digest({k: v for k, v in correction.items() if k != "id"})[:24],
                "correction identity differs from immutable proposal")
    require(type(basis.get("preparation")) is list and type(basis.get("omissions")) is list,
            "basis preparation/omissions must be retained")
    return basis


class Builder:
    def __init__(self, namespace, basis=None):
        self.basis = copy.deepcopy(basis) if basis is not None else empty(namespace)
        require(self.basis["namespace"] == namespace, "basis namespace mismatch")
        self.entities = index(self.basis["entities"], "entity")
        self.sources = index(self.basis["sources"], "source")
        self.claims = index(self.basis["claims"], "claim")
        self.relations = index(self.basis["relationships"], "relation")

    def source(self, identifier, revision, sha256, *, owner="unknown", status="supplied",
               applicability="unknown", roots=None, **metadata):
        row = dict(metadata, id=identifier, revision=revision, sha256=sha256, owner=owner,
                   status=status, applicability=applicability, roots=roots or [identifier])
        if identifier in self.sources:
            require(canonical(self.sources[identifier]) == canonical(row),
                    "conflicting source declaration: " + identifier)
        else:
            self.basis["sources"].append(row)
            self.sources[identifier] = row
        return row

    def entity(self, identifier, tag, scope, *, identity_role="functional_position", aliases=()):
        row = {"id": identifier, "tag": tag, "scope": scope,
               "identity_role": identity_role, "aliases": list(aliases)}
        if identifier in self.entities:
            require(canonical(self.entities[identifier]) == canonical(row),
                    "conflicting scoped entity declaration: " + identifier)
        else:
            self.basis["entities"].append(row)
            self.entities[identifier] = row
        return row

    def occurrence(self, subject, predicate, source, locator, *, value=None, unit=None,
                   target=None, role="source_statement", review=None, **metadata):
        json_value(value)
        kind = "relation" if target is not None else "claim"
        row = dict(metadata, subject=subject, predicate=predicate, source=source,
                   locator=locator, role=role, roots=root_sources(self.sources, source),
                   review=review or {"status": "unreviewed"})
        if target is None:
            row.update(value=copy.deepcopy(value), unit=unit)
        else:
            row.update(object=target, direction=row.pop("direction", "unknown"))
        row["id"] = record_id(kind, row)
        destination, rows = ((self.claims, self.basis["claims"]) if kind == "claim"
                             else (self.relations, self.basis["relationships"]))
        if row["id"] in destination:
            require(canonical(destination[row["id"]]) == canonical(row),
                    "source occurrence has conflicting values: " + row["id"])
        else:
            rows.append(row)
            destination[row["id"]] = row
        return row

    def finish(self):
        return validate(self.basis)


def semantic_value(claim):
    value, unit = claim["value"], claim.get("unit")
    if unit in QUANTITIES and type(value) in (str, int, float):
        token = str(value)
        exponent = token.lower().split("e")[-1] if "e" in token.lower() else "0"
        if len(token) <= 128 and DECIMAL.fullmatch(token) and abs(int(exponent)) <= 308:
            dimension, scale = QUANTITIES[unit]
            number = Fraction(token) * scale
            return canonical(["quantity", dimension, number.numerator, number.denominator])
    return canonical(["typed", type(value).__name__, value, unit])


class View:
    def __init__(self, basis):
        validate(basis)
        self.basis = basis
        self.entities = index(basis["entities"], "entity")
        self.sources = index(basis["sources"], "source")
        self.by_subject = defaultdict(list)
        self.by_property = defaultdict(list)
        self.edges = defaultdict(list)
        self.lookup = defaultdict(set)
        for entity in self.entities.values():
            for term in [entity["tag"], *entity.get("aliases", [])]:
                self.lookup[term].add(entity["id"])
        for claim in basis["claims"]:
            self.by_subject[claim["subject"]].append(claim)
            self.by_property[(claim["subject"], claim["predicate"])].append(claim)
        for edge in basis["relationships"]:
            self.edges[edge["subject"]].append(edge)
            if edge["object"] != edge["subject"]:
                self.edges[edge["object"]].append(edge)

    def resolve(self, item):
        if item in self.entities:
            return item
        choices = sorted(self.lookup.get(item, set()))
        require(bool(choices), "item not found: " + item)
        require(len(choices) == 1, "ambiguous item; choose qualified id: " + ", ".join(choices))
        return choices[0]

    def active(self, row):
        return (all(source["status"] in ACTIVE_SOURCES
                    for source in lineage_records(self.sources, row["source"]))
                and row["review"]["status"] != "rejected")

    def evidence(self, row):
        return {**copy.deepcopy(row), "source_record": copy.deepcopy(self.sources[row["source"]]),
                "source_lineage": copy.deepcopy(lineage_records(self.sources, row["source"])),
                "active_source": self.active(row),
                "authority": "source/reviewer declarations only; no authenticated engineering acceptance"}

    def field(self, subject, predicate):
        require(subject in self.entities, "field has unknown subject")
        rows = self.by_property[(subject, predicate)]
        current = [row for row in rows if self.active(row)]
        alternatives = {semantic_value(row) for row in current}
        state = ("disputed" if len(alternatives) > 1 else "sourced_unreviewed" if current
                 else "inactive_evidence" if rows else "unknown")
        content = [{"id": row["id"], "value": row["value"], "unit": row.get("unit"),
                    "role": row["role"], "active": self.active(row), "review": row["review"]}
                   for row in sorted(rows, key=lambda r: r["id"])]
        evidence = [self.evidence(row) for row in sorted(rows, key=lambda r: r["id"])]
        return {"subject": subject, "predicate": predicate, "state": state,
                "alternatives": evidence, "dependency": [subject, predicate],
                "content_fingerprint": digest(content), "evidence_fingerprint": digest(evidence),
                "distinct_declared_roots": sorted({r for row in current for r in row["roots"]}),
                "independence": "lineage roots are declarations, not proof of independent observations"}

    def inspect(self, item):
        subject = self.resolve(item)
        fields = {p: self.field(subject, p) for p in sorted({r["predicate"] for r in self.by_subject[subject]})}
        return {"entity": copy.deepcopy(self.entities[subject]), "fields": fields,
                "relationships": [self.evidence(e) for e in self.edges[subject]],
                "corrections": [copy.deepcopy(r) for r in self.basis["corrections"]
                                if r.get("subject") == subject],
                "unknowns": "Only represented facts are returned; absent facts remain unknown."}

    def traverse(self, item, predicate, *, depth=1, limit=100):
        start = self.resolve(item)
        require(predicate in RELATIONS, "choose an explicit supported relationship")
        require(type(depth) is int and 0 <= depth <= 8, "traversal depth must be 0..8")
        require(type(limit) is int and 1 <= limit <= 10000, "traversal limit must be 1..10000")
        queue, visited, edges = deque([(start, 0)]), {start}, {}
        truncated = False
        while queue:
            subject, level = queue.popleft()
            if level == depth:
                continue
            for edge in self.edges[subject]:
                if edge["subject"] != subject or edge["predicate"] != predicate or not self.active(edge):
                    continue
                if len(edges) >= limit and edge["id"] not in edges:
                    truncated = True
                    continue
                edges[edge["id"]] = self.evidence(edge)
                target = edge["object"]
                if target not in visited:
                    if len(visited) == limit:
                        truncated = True
                        continue
                    visited.add(target)
                    if target in self.entities:
                        queue.append((target, level + 1))
        return {"start": start, "predicate": predicate, "meaning": RELATIONS[predicate],
                "nodes": sorted(visited), "edges": list(edges.values()), "truncated": truncated,
                "qualification": "Traversal follows only declared outgoing active-source relations; no engineering consequence inferred."}


def capabilities():
    return {"schema": SCHEMA, "version": VERSION, "max_json_bytes": MAX_BYTES,
            "relations": RELATIONS, "queries": ["lookup", "inspect", "field", "traverse"],
            "draft_targets": ["equipment_instrument_list", "item_datasheet_scaffold",
                              "loop_control_narrative_outline"],
            "authority": "Draft source-linked context; company systems retain source and approval authority."}

