"""Read, write and check context-map-1 files: the hub the toolkit's other graph formats load into and project from.

    python scripts/context_map.py from-one-map out/drawing-to-map/graph.json --out map.json   # twin-graph-2 -> map
    python scripts/context_map.py from-twin-graph-1 examples/graph-export/sheet0_graph.json --out map.json
    python scripts/context_map.py to-twin-graph-1 map.json --out graph.json                  # map -> twin-graph-1 view
    python scripts/context_map.py validate map.json                                          # schema + cross-references

Edges translate through the tables in schemas/context-map/relations.json only (twin_graph_2_edges, its by-layer
override, twin_graph_1_edges and its by-layer table); an edge whose table entry is null is kept out of the map and
counted with the table's reason, never read as something it is not (network co-membership is network_member, never
piped_to). Every value keeps its source, locator and status; a status the format does not have reads as
unverified. What context-map-1 has no slot for is kept beside the map under extensions (a conversion report, and
for twin-graph-1 input everything to_twin_graph_1 needs to give the same graph back). Stdlib only.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "schemas" / "context-map"
SCHEMA_PATH = DIR / "context-map-1.schema.json"
RELATIONS_PATH = DIR / "relations.json"
FORMAT = "context-map-1"
VERSION = "1.2.0-draft"
REPORT = "x-toolkit-conversion"      # what was mapped, what was kept out and why
VIEW = "x-toolkit-twin-graph-1"      # twin-graph-1 fields with no slot in the map, for an exact way back
STATUSES = ("unverified", "confirmed", "corrected", "rejected", "stale")
SOURCE_KEYS = ("kind", "document", "revision", "path", "sha256")  # a source's identity; the rest is a locator
SCOPE_LEVELS = {"site": "site", "plant": "plant", "unit": "unit", "system": "system", "scope": "site_scope"}
ITEM_KINDS = ("equipment", "instrument", "controller", "final_element", "manual_valve", "relief_device", "line",
              "offpage_connector", "boundary", "junction", "other", "line_network")
# twin-graph-1 node kinds: plant and system are scopes; line_item (an untagged in-line valve or fitting) is an item of
# kind other; interlocks and limits are register rows (interlock_list, operating_limit), not PLANT items.
TG1_ITEM_KINDS = {"equipment": "equipment", "instrument": "instrument", "final_element": "final_element",
                  "controller": "controller", "line_item": "other", "offpage_connector": "offpage_connector",
                  "boundary": "boundary", "manual_valve": "manual_valve", "relief_device": "relief_device",
                  "junction": "junction", "line_network": "line_network"}
TG1_NOT_ITEMS = {"interlock": "an interlock belongs in the interlock_list register, not the PLANT layer",
                 "limit": "an operating limit belongs in the operating_limit register, not the PLANT layer"}
TG1_KIND_OF = {v: k for k, v in TG1_ITEM_KINDS.items()}
CONFLICT_TYPES = ("asset_presence", "value_disagreement", "mention_not_in_register", "ambiguous_reference",
                  "superseded_basis", "loop_pairing", "loop_reference", "unlisted_loop", "boundary", "authority_gap")
LOOP_OUTCOMES = ("located_and_consistent", "partly_located", "not_found_on_any_sheet", "not_checked")
SEGMENT = re.compile(r"^[^/\s](?:[^/]*[^/\s])?$")
REGISTER_IDS = frozenset(r["id"] for r in json.loads((DIR / "registers.json").read_text(encoding="utf-8"))["registers"])


class MapError(ValueError):
    pass


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema():
    return load_json(SCHEMA_PATH)


def relations_doc():
    return load_json(RELATIONS_PATH)


# ---------------------------------------------------------------- validation

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _type_ok(value, t):
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[t])


def validate(instance, schema, root, path="$"):
    """Errors for the JSON Schema keywords context-map-1 uses. Unknown keywords are refused, not ignored."""
    known = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "const", "enum", "required",
             "properties", "additionalProperties", "propertyNames", "items", "minItems", "maxItems", "minLength",
             "pattern", "oneOf", "minimum", "maximum"}
    unknown = set(schema) - known
    if unknown:
        raise AssertionError(f"validator does not implement {sorted(unknown)} (at {path})")
    errors = []
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/$defs/"), ref
        errors += validate(instance, root["$defs"][ref.split("/")[-1]], root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            return errors + [f"{path}: expected {types}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above {schema['maximum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing {key}")
        props = schema.get("properties", {})
        for key, value in instance.items():
            if "propertyNames" in schema:
                errors += validate(key, schema["propertyNames"], root, f"{path}.<{key}>")
            if key in props:
                errors += validate(value, props[key], root, f"{path}.{key}")
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}: unexpected {key}")
                elif isinstance(extra, dict):
                    errors += validate(value, extra, root, f"{path}.{key}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, value in enumerate(instance):
                errors += validate(value, schema["items"], root, f"{path}[{i}]")
    if "oneOf" in schema:
        passing = [s for s in schema["oneOf"] if not validate(instance, s, root, path)]
        if len(passing) != 1:
            errors.append(f"{path}: matches {len(passing)} of oneOf, needs exactly 1")
    return errors


def check(m, sch=None):
    """Schema errors plus the cross-references the schema cannot express: every source named is declared, every
    scope, item, relation end, document link and loop member is on the map, and ids are unique."""
    sch = sch or schema()
    errors = validate(m, sch, sch)
    if errors or not isinstance(m, dict):
        return errors
    plant = m["plant"]
    sources = [s["id"] for s in m.get("sources", [])]
    scopes = [s["id"] for s in plant["scopes"]]
    items = [i["id"] for i in plant["items"]]
    docs = [d["id"] for d in m.get("documents", [])]
    for what, ids in (("source", sources), ("scope", scopes), ("item", items), ("document", docs)):
        errors += [f"{what} id {i!r} appears more than once" for i in sorted({i for i in ids if ids.count(i) > 1})]
    known_src, scope_set = set(sources), set(scopes)
    on_map = scope_set | set(items) | set(docs)

    def src(where, sid):
        if sid is not None and sid not in known_src:
            errors.append(f"{where}: source {sid!r} is not in sources")

    for s in plant["scopes"]:
        if s.get("parent") is not None and s["parent"] not in scope_set:
            errors.append(f"scope {s['id']}: parent {s['parent']!r} is not a scope")
    for i in plant["items"]:
        if i["scope"] not in scope_set:
            errors.append(f"item {i['id']}: scope {i['scope']!r} is not a scope")
        if i.get("parent") is not None and i["parent"] not in on_map:
            errors.append(f"item {i['id']}: parent {i['parent']!r} is not on the map")
        src(f"item {i['id']}", i.get("source"))
        for a in i.get("appearances", []):
            src(f"item {i['id']} appearance", a["source"])
        for name, v in (i.get("attributes") or {}).items():
            if isinstance(v, dict):
                src(f"item {i['id']} attribute {name}", v.get("source"))
    for n, r in enumerate(plant.get("relations", [])):
        where = f"relation {r.get('id', n)}"
        for end in ("from", "to"):
            if r[end] not in on_map:
                errors.append(f"{where}: {end} {r[end]!r} is not on the map")
        src(where, r["source"])
        for name, v in (r.get("attributes") or {}).items():
            if isinstance(v, dict):
                src(f"{where} attribute {name}", v.get("source"))
    for d in m.get("documents", []):
        src(f"document {d['id']}", d.get("source"))
        for c in d.get("covers", []):
            if c not in on_map:
                errors.append(f"document {d['id']}: covers {c!r}, which is not on the map")
        for mt in d.get("mentions", []):
            if mt["target"] not in on_map:
                errors.append(f"document {d['id']}: mentions {mt['target']!r}, which is not on the map")
        for b in d.get("based_on", []):
            if b["id"] not in on_map:
                errors.append(f"document {d['id']}: based on {b['id']!r}, which is not on the map")
    for rid, rows in (m.get("records") or {}).items():
        for n, row in enumerate(rows):
            src(f"records.{rid}[{n}]", row["source"])
            if row.get("item") is not None and row["item"] not in on_map:
                errors.append(f"records.{rid}[{n}]: item {row['item']!r} is not on the map")
    for lp in plant.get("loops", []):
        if lp["scope"] not in scope_set:
            errors.append(f"loop {lp['id']}: scope {lp['scope']!r} is not a scope")
        for x in [lp.get("controller")] + lp.get("measurements", []) + lp.get("outputs", []):
            if x is not None and x not in on_map:
                errors.append(f"loop {lp['id']}: {x!r} is not on the map")
        src(f"loop {lp['id']}", lp.get("source"))
    for c in (m.get("decisions") or {}).get("conflicts", []):
        for s in c["sides"]:
            src(f"conflict {c['id']}", s["source"])
    return errors


# ---------------------------------------------------------------- edge translation (relations.json only)

def edge_relation(edge, from_kind, fmt, rel=None):
    """The context-map relation a twin-graph edge reads as, or None (kept out). fmt is twin-graph-1 or twin-graph-2."""
    rel = rel or relations_doc()
    key = "twin_graph_1" if fmt == "twin-graph-1" else "twin_graph_2"
    by_layer = rel.get(f"{key}_edges_by_layer", {})
    t = edge.get("type")
    if t in by_layer:
        r = by_layer[t].get(edge.get("layer"))
    else:
        r = rel[f"{key}_edges"].get(t)
    if r == "controls" and from_kind == "instrument":  # a measurement's `controls` is its signal to the controller
        r = rel["controls_from_measurement_reads_as"]
    return r


def not_mapped_reason(edge, fmt, rel):
    if fmt == "twin-graph-1":
        reasons = rel["twin_graph_1_not_mapped"]
        layered = f"{edge.get('type')}/{edge.get('layer')}"
        return reasons.get(layered) or reasons.get(edge.get("type")) or f"no relations.json entry for {layered}"
    return f"relations.json maps twin-graph-2 {edge.get('type')} to no relation"


# ---------------------------------------------------------------- sources, values and statuses

class Sources:
    """Distinct source dicts -> context-map sources, ids kept stable in first-seen order."""

    def __init__(self, record_type_of):
        self.record_type_of = record_type_of
        self.by_key, self.list, self.keys = {}, [], {}

    def add(self, src):
        """(source id, locator or None) for one twin-graph source dict."""
        if not isinstance(src, dict):
            raise MapError(f"source is not an object: {src!r}")
        ident = {k: src[k] for k in SOURCE_KEYS if k in src and (k != "document" or isinstance(src[k], str))}
        rest = {k: v for k, v in src.items() if k not in ident}
        key = json.dumps(ident, sort_keys=True)
        if key not in self.by_key:
            base = " ".join(str(ident.get("document") or ident.get("path") or ident.get("kind") or "").split())
            base = base or "source"
            sid, n = base, 1
            while sid in self.keys:
                n += 1
                sid = f"{base} #{n}"
            entry = {"id": sid, "record_type": self.record_type_of(ident)}
            if ident.get("document") is not None:
                entry["title"] = ident["document"]
            for k in ("revision", "path", "sha256"):
                if isinstance(ident.get(k), str) and (k != "sha256" or re.fullmatch(r"[0-9a-f]{64}", ident[k])):
                    entry[k] = ident[k]
            self.by_key[key] = sid
            self.keys[sid] = ident
            self.list.append(entry)
        if not rest:
            loc = None
        elif list(rest) == ["locator"] and isinstance(rest["locator"], str):
            loc = rest["locator"]
        else:
            loc = rest
        return self.by_key[key], loc


def status(value, report, where):
    if value in STATUSES:
        return value
    if value is not None:
        report["statuses_read_as_unverified"][str(value)] = report["statuses_read_as_unverified"].get(str(value), 0) + 1
    return "unverified"


def plain(v):
    return v is None or isinstance(v, (str, int, float, bool)) or (
        isinstance(v, list) and all(x is None or isinstance(x, (str, int, float, bool)) for x in v))


def fact(claim, sources, report, where):
    """A twin-graph claim as a Fact, or None when its value is not a plain value or list of them."""
    if not plain(claim.get("value")):
        bump(report["fields_not_mapped"], "claims whose value is not a plain value or list (kept in the view for "
             "twin-graph-1 input)")
        return None
    sid, loc = sources.add(claim["source"])
    f = {"value": claim.get("value"), "source": sid, "status": status(claim.get("status"), report, where)}
    if loc is not None:
        f["locator"] = loc
    return f


def segment(text):
    """One identity segment from a twin-graph-1 id (which may hold '/'), and whether it had to change."""
    s = " ".join(str(text).split()).replace("/", "%2F")
    return (s, s != text) if SEGMENT.match(s) else (None, True)


def new_report(fmt):
    return {"from": fmt, "converter": "scripts/context_map.py", "document_links": 0, "nodes_kept_out": {},
            "edges_kept_out": {},
            "statuses_read_as_unverified": {}, "fields_not_mapped": {}}


def bump(table, key, n=1):
    table[key] = table.get(key, 0) + n


# ---------------------------------------------------------------- twin-graph-2 (one map) -> context map

def from_one_map(graph):
    """A one_map.py twin-graph-2 graph as a context-map-1 map: scopes, items with class, appearances and sourced
    attributes, PLANT relations, documents with covers/mentions/based_on, register rows, loops and conflicts."""
    if graph.get("schema") != "twin-graph-2":
        raise MapError(f"needs a twin-graph-2 graph, got {graph.get('schema')!r}")
    rel = relations_doc()
    report = new_report("twin-graph-2")
    nodes = {n["id"]: n for n in graph["nodes"]}
    registers = {}
    for s in (graph.get("coverage") or {}).get("sources", []):
        registers[s["id"]] = s
    doc_tail = {}
    for n in graph["nodes"]:
        if n["kind"] == "document":
            doc_tail[n["id"]] = (n.get("document") or {}).get("id") or n.get("tag")
    for rows in (graph.get("records") or {}).values():
        for row in rows:
            d = (row.get("source") or {}).get("document")
            if isinstance(d, str) and d not in registers:
                registers[d] = {"register": row["register"]}

    def record_type_of(ident):
        d = ident.get("document")
        for key in (d, doc_tail.get(d)):
            if key in registers:
                return registers[key]["register"]
        if ident.get("kind") in ("drawing", "authored_schedule"):
            return "pid"
        for key in (ident.get("kind"), d):
            if key in REGISTER_IDS:
                return key
        if d in doc_tail:
            return "document_register"
        return "unspecified"

    sources = Sources(record_type_of)
    scopes, items, documents, conflicts = [], [], [], []
    parent = {}
    for e in graph["edges"]:
        if e["type"] == "contains":
            parent.setdefault(e["to"], e["from"])
    for n in graph["nodes"]:
        k = n["kind"]
        if k in SCOPE_LEVELS:
            sc = {"id": n["id"], "level": SCOPE_LEVELS[k]}
            if isinstance(n.get("name"), str):
                sc["name"] = n["name"]
            p = parent.get(n["id"])
            if p is not None and nodes.get(p, {}).get("kind") in SCOPE_LEVELS:
                sc["parent"] = p
            if n.get("owner"):
                sc["owner"] = n["owner"]
            if n.get("shared") is not None:
                sc["shared"] = bool(n["shared"])
            scopes.append(sc)
        elif k == "document":
            documents.append(_document(n, sources, report))
        elif k == "conflict":
            c = _conflict(n, sources, report)
            if c:
                conflicts.append(c)
        elif k in ITEM_KINDS:
            items.append(_item_tg2(n, nodes, parent, sources, report))
        else:
            bump(report["nodes_kept_out"], f"{k}: no context-map item kind")
    _implied_scopes(scopes, items, report)
    on_map = {s["id"] for s in scopes} | {i["id"] for i in items} | {d["id"] for d in documents}
    by_doc = {d["id"]: d for d in documents}
    relations = []
    for e in graph["edges"]:
        t = e["type"]
        if t in ("covers", "mentions", "based_on"):
            _document_link(e, by_doc, on_map, report)
            continue
        r = edge_relation(e, nodes.get(e["from"], {}).get("kind"), "twin-graph-2", rel)
        if r is None:
            why = ("a conflict's subject; kept as decisions.conflicts[].subject" if t == "concerns"
                   else not_mapped_reason(e, "twin-graph-2", rel))
            bump(report["edges_kept_out"], f"{t}{'/' + e['layer'] if e.get('layer') else ''}: {why}")
            continue
        if e["from"] not in on_map or e["to"] not in on_map:
            bump(report["edges_kept_out"], f"{t}: an end is not on the map")
            continue
        relations.append(_relation(e, r, e["from"], e["to"], sources, report))
    m = {"format": FORMAT, "format_version": VERSION,
         "map": {"site": graph["site"], "generator": "scripts/context_map.py from-one-map"}}
    if graph.get("title"):
        m["map"]["name"] = graph["title"]
    plant = {"scopes": scopes, "items": items, "relations": relations}
    loops = [lp for lp in (_loop(x, on_map, sources, report) for x in graph.get("loops", [])) if lp]
    if loops:
        plant["loops"] = loops
    records = {}
    for rid, rows in (graph.get("records") or {}).items():
        out = []
        for row in rows:
            sid, loc = sources.add(row["source"])
            r = {"source": sid, "status": status(row.get("status"), report, rid), "values": dict(row["values"])}
            if row.get("id"):
                r["id"] = row["id"]
            if row.get("item") in on_map:
                r["item"] = row["item"]
            if loc is not None:
                r["locator"] = loc
            out.append(r)
        records[rid] = out
    m["sources"] = sources.list
    for s in m["sources"]:
        cov = next((registers[k] for k in (s.get("title"), doc_tail.get(s.get("title"))) if k in registers), {})
        if cov.get("scopes") and "id" in cov:
            s["scopes"] = list(cov["scopes"])
        if cov.get("owner"):
            s["owner"] = cov["owner"]
    m["plant"] = plant
    if records:
        m["records"] = records
    if documents:
        m["documents"] = documents
    if conflicts:
        m["decisions"] = {"conflicts": conflicts}
    if graph.get("expectations"):
        ex = copy.deepcopy(graph["expectations"])
        by_rule = ex.pop("by_rule", None)
        m["expectations"] = ex
        if by_rule:
            m["coverage"] = {"by_rule": by_rule}
    for key in sorted(set(graph) - {"schema", "model_kind", "title", "site", "nodes", "edges", "loops", "records",
                                    "expectations"}):
        report["fields_not_mapped"][key] = "a twin-graph-2 section with no context-map-1 slot; regenerated, not stored"
    m["extensions"] = {REPORT: report}
    return m


def _scope_of(nid, nodes, parent):
    seen = set()
    while nid in parent and nid not in seen:
        seen.add(nid)
        nid = parent[nid]
        if nodes.get(nid, {}).get("kind") in SCOPE_LEVELS:
            return nid
    return None


def _implied_scopes(scopes, items, report):
    """An authored graph may name an item SITE/PLANT/UNIT/TAG without a node for each scope: add the scopes its
    qualified id implies (site, plant, unit, then system), counted in the report."""
    have = {s["id"] for s in scopes}
    levels = ("site", "plant", "unit")
    for it in items:
        if it["scope"] is None:
            it["scope"] = it["id"].rsplit("/", 1)[0] if "/" in it["id"] else None
        if it["scope"] is None:
            continue
        parts = it["scope"].split("/")
        for depth in range(1, len(parts) + 1):
            sid = "/".join(parts[:depth])
            if sid in have:
                continue
            sc = {"id": sid, "level": levels[depth - 1] if depth <= 3 else "system"}
            if depth > 1:
                sc["parent"] = "/".join(parts[:depth - 1])
            scopes.append(sc)
            have.add(sid)
            bump(report["fields_not_mapped"], "scopes implied by qualified item ids (no scope node in the graph)")


def _item_tg2(n, nodes, parent, sources, report):
    scope = n.get("scope") or _scope_of(n["id"], nodes, parent)
    tag = n.get("tag")
    if not (isinstance(tag, str) and SEGMENT.match(tag)):
        tag = n["id"].rsplit("/", 1)[-1]  # a boundary or connector with no printed tag: its id's last segment
        bump(report["fields_not_mapped"], "items with no tag (the id's last segment is used as the tag)")
    it = {"id": n["id"], "tag": tag, "scope": scope, "kind": n["kind"],
          "status": status(n.get("status"), report, n["id"])}
    if n.get("class"):
        it["class"] = n["class"]
        if n.get("class_how"):
            it["class_how"] = n["class_how"]
    if isinstance(n.get("name"), str):
        it["name"] = n["name"]
    p = parent.get(n["id"])
    if p is not None and p != scope and nodes.get(p, {}).get("kind") not in SCOPE_LEVELS:
        it["parent"] = p
    if n.get("aliases"):
        it["aliases"] = [{"alias": a, "kind": "other"} for a in n["aliases"]]
    if n.get("safety"):
        it["safety_relevant"] = True
    if isinstance(n.get("source"), dict):
        it["source"], loc = sources.add(n["source"])
        if loc is not None:
            bump(report["fields_not_mapped"], "item source locators (an item has no locator; its record row and "
                 "appearances keep theirs)")
    if n.get("listed_in"):
        it["listed_in"] = list(n["listed_in"])
    apps = []
    for a in n.get("appearances", []):
        sid, loc = sources.add({k: v for k, v in a.items() if k in SOURCE_KEYS})
        ap = {"source": sid, **{k: v for k, v in a.items() if k not in SOURCE_KEYS}}
        if "revision" in a:
            ap["revision"] = a["revision"]
        apps.append(ap)
    if apps:
        it["appearances"] = apps
    attrs = {}
    for c in n.get("attributes", []):
        f = fact(c, sources, report, n["id"])
        if f is not None:
            attrs[c["name"]] = f
    if attrs:
        it["attributes"] = attrs
    return it


def _relation(e, r, a, b, sources, report):
    out = {"id": e["id"], "type": r, "from": a, "to": b}
    if isinstance(e.get("source"), dict):
        out["source"], loc = sources.add(e["source"])
    else:
        out["source"], loc = sources.add({"kind": "unsourced", "document": "unsourced"})
    if loc is not None:
        out["locator"] = loc
    out["status"] = status(e.get("status"), report, e["id"])
    if r == "network_member":
        pass  # co-membership has no direction, whatever order the source wrote the ends in
    elif e.get("direction") in ("known", "forward"):
        out["directed"] = True
    elif e.get("direction") == "unknown":
        out["directed"] = False
    attrs = {}
    for c in e.get("attributes", []):
        f = fact(c, sources, report, e["id"])
        if f is not None:
            attrs[c["name"]] = f
    if attrs:
        out["attributes"] = attrs
    return out


def _document(n, sources, report):
    meta = n.get("document") or {}
    d = {"id": n["id"], "revision": str(meta.get("revision") or (n.get("source") or {}).get("revision") or "")}
    if isinstance(n.get("name"), str):
        d["title"] = n["name"]
    for k in ("doc_type", "owner", "path"):
        if isinstance(meta.get(k), str):
            d[k] = meta[k]
    if meta.get("status") in ("draft", "released", "superseded", "withdrawn"):
        d["status"] = meta["status"]
    if isinstance(meta.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", meta["sha256"]):
        d["sha256"] = meta["sha256"]
    text = (meta.get("text") or {}).get("status")
    if text in ("ok", "partial", "needs OCR", "none"):
        d["text_extracted"] = {"ok": "yes", "partial": "partial"}.get(text, "no")
    if isinstance(n.get("source"), dict):
        d["source"] = sources.add(n["source"])[0]
    return d


def _document_link(e, by_doc, on_map, report):
    d = by_doc.get(e["from"])
    if d is None or e["to"] not in on_map:
        bump(report["edges_kept_out"], f"{e['type']}: an end is not on the map")
        return
    attrs = {c["name"]: c.get("value") for c in e.get("attributes", [])}
    report["document_links"] += 1
    if e["type"] == "covers":
        if e["to"] not in d.setdefault("covers", []):
            d["covers"].append(e["to"])
    elif e["type"] == "based_on":
        d.setdefault("based_on", []).append({"id": e["to"], "revision": str(attrs.get("revision") or "")})
    else:
        src = e.get("source") or {}
        mt = {"target": e["to"], "locator": attrs.get("locator") or src.get("locator") or "",
              "matched_text": str(attrs.get("matched_text") or e["to"].rsplit("/", 1)[-1])}
        if attrs.get("matched") in ("exact", "alias", "qualified_id", "glossary"):
            mt["match"] = attrs["matched"]
        if attrs.get("glossary_term"):
            mt["term"] = str(attrs["glossary_term"])
        d.setdefault("mentions", []).append(mt)


def _conflict(n, sources, report):
    c = n.get("conflict") or {}
    if c.get("type") not in CONFLICT_TYPES or c.get("status") not in ("open", "disputed", "resolved"):
        bump(report["nodes_kept_out"],
             f"conflict: type {c.get('type')!r} or status {c.get('status')!r} not in the format")
        return None
    sides = []
    for key in ("source_a", "source_b"):
        s = c.get(key)
        if not s:
            continue
        sid, loc = sources.add(s["source"])
        side = {"source": sid, "says": s.get("says") if plain(s.get("says")) and not isinstance(s.get("says"), list)
                else json.dumps(s.get("says"))}
        if loc is not None:
            side["locator"] = loc
        sides.append(side)
    out = {"id": n["id"], "type": c["type"], "subject": c["subject"], "sides": sides, "status": c["status"]}
    for k in ("attribute", "record_owner"):
        if isinstance(c.get(k), str):
            out[k] = c[k]
    if c.get("parties"):
        out["other_parties"] = [p for p in c["parties"] if p != c.get("record_owner")]
    if isinstance(c.get("detected"), bool):
        out["detected"] = c["detected"]
    return out


def _loop(x, on_map, sources, report):
    scope, ctrl = x.get("scope"), x.get("controller")
    if scope not in on_map or not ctrl:
        bump(report["fields_not_mapped"], "loops: no scope or controller")
        return None
    q = lambda tag: f"{scope}/{tag}"  # noqa: E731
    lp = {"id": f"{scope}/@loop/{ctrl}", "scope": scope}
    if q(ctrl) in on_map:
        lp["controller"] = q(ctrl)
    ms = [q(t) for t in [x.get("measurement")] if t and q(t) in on_map]
    outs = [q(t) for t in [x.get("output")] if t and q(t) in on_map]
    if ms:
        lp["measurements"] = ms
    if outs:
        lp["outputs"] = outs
    outcome = str(x.get("outcome") or "").replace(" ", "_")
    lp["outcome"] = outcome if outcome in LOOP_OUTCOMES else "not_checked"
    sid = next((s["id"] for s in sources.list if s.get("title") == x.get("loop_list")), None)
    if sid:
        lp["source"] = sid
        if x.get("line") is not None:
            lp["locator"] = f"line {x['line']}"
    return lp


# ---------------------------------------------------------------- twin-graph-1 <-> context map

def from_twin_graph_1(graph, site="SITE"):
    """A graph_export.py twin-graph-1 graph as a context-map-1 map. Plant and system nodes become scopes under one
    site scope (twin-graph-1 has no site; `site` names it). Everything with no slot in the map is kept verbatim under
    extensions, so to_twin_graph_1 gives the same graph back."""
    if graph.get("schema") != "twin-graph-1":
        raise MapError(f"needs a twin-graph-1 graph, got {graph.get('schema')!r}")
    if not SEGMENT.match(site):
        raise MapError(f"site {site!r} is not one identity segment")
    rel = relations_doc()
    report = new_report("twin-graph-1")
    view = {"graph": {k: v for k, v in graph.items() if k not in ("nodes", "edges")}, "site": site,
            "order": [], "nodes": {}, "edges": {}, "kept_nodes": {}, "kept_edges": {}, "sources": {}, "ids": {}}
    nodes = {n["id"]: n for n in graph["nodes"]}
    parent = {}
    for e in graph["edges"]:
        if e.get("type") == "contains":
            parent.setdefault(e["to"], e["from"])
    sources = Sources(lambda ident: "pid")  # an extracted or authored P&ID model (CONTEXT_MAP_FORMAT.md fit-in table)
    scope_id, item_id = {}, {}

    def scope_for(nid, seen=()):
        if nid in scope_id:
            return scope_id[nid]
        n = nodes[nid]
        p = parent.get(nid)
        up = scope_for(p, seen + (nid,)) if p in nodes and nodes[p]["kind"] in ("plant", "system") \
            and p not in seen else site
        seg, changed = segment(nid)
        if seg is None:
            return None
        sid = f"{up}/{seg}"
        if changed:
            view["ids"][sid] = nid
        scope_id[nid] = sid
        return sid

    def container_scope(nid):
        seen = set()
        p = parent.get(nid)
        while p in nodes and p not in seen:
            seen.add(p)
            if nodes[p]["kind"] in ("plant", "system"):
                return scope_for(p)
            p = parent.get(p)
        return site

    scopes = [{"id": site, "level": "site"}]
    items = []
    for n in graph["nodes"]:
        k = n.get("kind")
        if k in ("plant", "system"):
            sid = scope_for(n["id"])
            if sid is None:
                view["kept_nodes"][n["id"]] = n
                view["order"].append(["kept_node", n["id"]])
                bump(report["nodes_kept_out"], f"{k}: id is not a usable identity segment")
                continue
            sc = {"id": sid, "level": k, "parent": sid.rsplit("/", 1)[0]}
            if isinstance(n.get("name"), str):
                sc["name"] = n["name"]
            scopes.append(sc)
            view["order"].append(["scope", sid])
            view["nodes"][sid] = _node_rest(n, sc, sources, report, scope=True)
            continue
        if k not in TG1_ITEM_KINDS:
            view["kept_nodes"][n["id"]] = n
            view["order"].append(["kept_node", n["id"]])
            bump(report["nodes_kept_out"], f"{k}: {TG1_NOT_ITEMS.get(k, 'no context-map item kind')}")
            continue
        seg, changed = segment(n["id"])
        tag = n.get("tag") if isinstance(n.get("tag"), str) and SEGMENT.match(n.get("tag") or "") else seg
        if seg is None or tag is None:
            view["kept_nodes"][n["id"]] = n
            view["order"].append(["kept_node", n["id"]])
            bump(report["nodes_kept_out"], f"{k}: id is not a usable identity segment")
            continue
        scope = container_scope(n["id"])
        iid = f"{scope}/{seg}"
        if changed:
            view["ids"][iid] = n["id"]
        item_id[n["id"]] = iid
        it = {"id": iid, "tag": tag, "scope": scope, "kind": TG1_ITEM_KINDS[k]}
        items.append(it)
        view["order"].append(["item", iid])
        view["nodes"][iid] = _node_rest(n, it, sources, report)
    by_id = {i["id"]: i for i in items}
    for n in graph["nodes"]:  # parents once every item has its id
        p = parent.get(n["id"])
        if n["id"] in item_id and p in item_id:
            by_id[item_id[n["id"]]]["parent"] = item_id[p]
    ids = {**scope_id, **item_id}
    relations = []
    for e in graph["edges"]:
        t = e.get("type")
        a, b = ids.get(e.get("from")), ids.get(e.get("to"))
        r = edge_relation(e, nodes.get(e.get("from"), {}).get("kind"), "twin-graph-1", rel)
        if r is None or a is None or b is None:
            why = (not_mapped_reason(e, "twin-graph-1", rel) if r is None else "an end is outside the map")
            key = f"kept:{len(view['kept_edges'])}"
            view["kept_edges"][key] = e
            view["order"].append(["kept_edge", key])
            bump(report["edges_kept_out"], f"{t}{'/' + e['layer'] if e.get('layer') else ''}: {why}")
            continue
        out = _relation(e, r, a, b, sources, report)
        relations.append(out)
        view["order"].append(["relation", e["id"]])
        rest = {k: v for k, v in e.items() if k not in ("id", "type", "from", "to", "status", "source", "attributes")}
        absent = [k for k in ("source", "attributes", "direction") if k not in e]
        if absent:
            rest["_absent"] = absent
        if e.get("status") not in STATUSES:
            rest["_status"] = e.get("status")
        if r != t:
            rest["_type"] = t
        _keep_list_claims(e, out, rest)
        view["edges"][e["id"]] = rest
    view["sources"] = dict(sources.keys)
    m = {"format": FORMAT, "format_version": VERSION,
         "map": {"site": site, "generator": "scripts/context_map.py from-twin-graph-1"}}
    if isinstance(graph.get("title"), str):
        m["map"]["name"] = graph["title"]
    m["sources"] = sources.list
    m["plant"] = {"scopes": scopes, "items": items, "relations": relations}
    m["extensions"] = {REPORT: report, VIEW: view}
    return m


def _keep_list_claims(x, out, rest):
    """Claim values the map cannot hold (not plain) stay in the view."""
    bad = [c["name"] for c in x.get("attributes", []) if not plain(c.get("value"))]
    if bad:
        rest["_claims"] = [c for c in x["attributes"] if c["name"] in bad]
        for name in bad:
            out["attributes"].pop(name, None)
        if not out["attributes"]:
            out.pop("attributes")
    if x.get("attributes") is not None:
        rest["_attr_order"] = [c["name"] for c in x["attributes"]]
    if any(c.get("status") not in STATUSES for c in x.get("attributes", [])):
        rest["_claim_status"] = {c["name"]: c.get("status") for c in x["attributes"] if c.get("status") not in STATUSES}


def _node_rest(n, target, sources, report, scope=False):
    """Fill the item from a twin-graph-1 node; return the node's fields the map has no slot for."""
    rest = {k: v for k, v in n.items() if k not in ("id", "kind", "tag", "name", "status", "source", "attributes",
                                                   "aliases", "provenance")}
    absent = [k for k in ("tag", "name", "status", "source", "attributes", "aliases") if k not in n]
    if absent:
        rest["_absent"] = absent
    if n.get("tag") != target.get("tag"):
        rest["tag"] = n.get("tag")
    if not isinstance(n.get("name"), str):
        rest["name"] = n.get("name")
    elif not scope:
        target["name"] = n["name"]
    if n.get("status") not in STATUSES:
        rest["_status"] = n.get("status")
    if scope:
        for k in ("tag", "status", "source", "attributes", "aliases", "provenance"):
            if k in n:
                rest[k] = n[k]
        return rest
    target["status"] = status(n.get("status"), report, n["id"])
    src_loc = None
    if isinstance(n.get("source"), dict):
        target["source"], src_loc = sources.add(n["source"])
        if src_loc is not None:
            rest["_source_locator"] = src_loc
    elif "source" in n:
        rest["source"] = n["source"]
    if "aliases" in n:
        target["aliases"] = [{"alias": a, "kind": "other"} for a in n["aliases"]]
    if "provenance" in n:
        if all(isinstance(p, dict) and "source" not in p for p in n["provenance"]) and target.get("source"):
            target["appearances"] = [{"source": target["source"], **p} for p in n["provenance"]]
        else:
            rest["provenance"] = n["provenance"]
    attrs = {}
    for c in n.get("attributes", []):
        if plain(c.get("value")):
            attrs[c["name"]] = fact(c, sources, report, n["id"])
    target["attributes"] = attrs
    _keep_list_claims(n, target, rest)
    if not target.get("attributes"):
        target.pop("attributes", None)
    return rest


def _source_dict(sid, loc, m_sources, view_sources):
    if sid in view_sources:
        src = dict(view_sources[sid])
    else:
        s = m_sources.get(sid, {"id": sid})
        src = {"kind": "drawing" if s.get("record_type") == "pid" else "document", "document": s.get("title", sid)}
        for k in ("revision", "path", "sha256"):
            if k in s:
                src[k] = s[k]
    if isinstance(loc, str):
        src["locator"] = loc
    elif isinstance(loc, dict):
        src.update(loc)
    return src


def _claims(owner, rest, m_sources, view_sources):
    out = {}
    for name, v in (owner.get("attributes") or {}).items():
        if isinstance(v, dict):
            c = {"name": name, "value": v.get("value"), "status": v.get("status", "unverified"),
                 "source": _source_dict(v["source"], v.get("locator"), m_sources, view_sources)}
        else:
            c = {"name": name, "value": v, "status": owner.get("status", "unverified"),
                 "source": _source_dict(owner.get("source"), None, m_sources, view_sources)}
        out[name] = c
    for c in rest.get("_claims", []):
        out[c["name"]] = c
    for name, st in rest.get("_claim_status", {}).items():
        if name in out:
            out[name]["status"] = st
    order = rest.get("_attr_order") or list(out)
    return [out[n] for n in order if n in out]


def to_twin_graph_1(m):
    """A context-map-1 map as a twin-graph-1 graph (the portable graph view). A map read from twin-graph-1 gives the
    same graph back. Otherwise: plant scopes become plant nodes, units and systems system nodes; relations read back
    through relations.json's twin_graph_1_edges; what twin-graph-1 cannot say is listed in not_exported."""
    rel = relations_doc()
    view = (m.get("extensions") or {}).get(VIEW)
    m_sources = {s["id"]: s for s in m.get("sources", [])}
    view_sources = (view or {}).get("sources", {})
    back = {}
    for t, r in rel["twin_graph_1_edges"].items():
        if r is not None:
            back.setdefault(r, t)
    plant = m["plant"]
    items = {i["id"]: i for i in plant["items"]}
    scopes = {s["id"]: s for s in plant["scopes"]}
    ids = (view or {}).get("ids", {})

    def orig(mid):
        if mid in ids:
            return ids[mid]
        if view:
            return mid.rsplit("/", 1)[-1]
        return mid

    nodes, edges, not_exported = {}, {}, {}
    for sid, s in scopes.items():
        rest = (view or {}).get("nodes", {}).get(sid)
        if view and rest is None:
            continue  # the synthesized site scope
        kind = {"plant": "plant", "unit": "system", "system": "system"}.get(s["level"])
        if kind is None:
            bump(not_exported, f"{s['level']} scope (twin-graph-1 has no {s['level']} node)")
            continue
        n = {"id": orig(sid), "kind": kind, "tag": orig(sid), "name": s.get("name"), "aliases": [],
             "status": "confirmed", "attributes": []}
        if rest is not None:
            n = {"id": orig(sid), "kind": kind}
            if "tag" not in rest.get("_absent", []):
                n["tag"] = orig(sid)
            n["name"] = s.get("name")
            n.update({k: v for k, v in rest.items() if not k.startswith("_")})
        nodes[sid] = n
    for iid, it in items.items():
        rest = (view or {}).get("nodes", {}).get(iid, {})
        kind = TG1_KIND_OF.get(it.get("kind"), "line_item" if it.get("kind") in (None, "other") else None)
        if kind is None:
            bump(not_exported, f"item of kind {it.get('kind')} (no twin-graph-1 node kind)")
            continue
        n = {"id": orig(iid), "kind": kind, "tag": it["tag"], "name": it.get("name") if isinstance(it.get("name"), str)
             else None, "aliases": [a["alias"] for a in it.get("aliases", [])], "status": rest.get("_status") or
             it.get("status", "unverified")}
        if it.get("source") is not None:
            n["source"] = _source_dict(it["source"], rest.get("_source_locator"), m_sources, view_sources)
        if it.get("appearances") is not None and view is not None:
            n["provenance"] = [{k: v for k, v in a.items() if k != "source"} for a in it["appearances"]]
        n["attributes"] = _claims(it, rest, m_sources, view_sources)
        for k, v in rest.items():
            if not k.startswith("_"):
                n[k] = v
        for k in rest.get("_absent", []):
            n.pop(k, None)
        if view is None:
            if it.get("class"):
                n["attributes"].append({"name": "class", "value": it["class"], "status": "unverified",
                                        "source": n.get("source") or {"kind": "model", "document": "context map"}})
            n.setdefault("source", {"kind": "model", "document": m["map"].get("name") or m["map"]["site"]})
        nodes[iid] = n
    for r in plant.get("relations", []):
        rid = r.get("id") or f"{r['type']}:{r['from']}->{r['to']}"
        rest = (view or {}).get("edges", {}).get(rid, {})
        a, b = r["from"], r["to"]
        if a not in nodes or b not in nodes:
            bump(not_exported, f"{r['type']} relation with an end that is not a twin-graph-1 node")
            continue
        t, layer = rest.get("_type"), None
        if t is None:
            if r["type"] == "network_member":
                t = "on_network" if items.get(b, {}).get("kind") == "line_network" else "connects"
                layer = "network_pair" if t == "connects" else None
            elif r["type"] == "references":
                both = all(items.get(x, {}).get("kind") == "offpage_connector" for x in (a, b))
                t, layer = ("connects", "offpage_pair") if both else (None, None)
            elif r["type"] == "signal_to":
                t = "controls" if items.get(a, {}).get("kind") == "instrument" else None
            else:
                t = back.get(r["type"])
        if t is None:
            bump(not_exported, f"{r['type']} relation (twin-graph-1 has no edge type for it)")
            continue
        e = {"id": rid, "type": t, "from": nodes[a]["id"], "to": nodes[b]["id"],
             "status": rest.get("_status") or r.get("status", "unverified")}
        if view is None:
            e["direction"] = None if "directed" not in r else ("known" if r["directed"] else "unknown")
        e["source"] = _source_dict(r["source"], r.get("locator"), m_sources, view_sources)
        if layer:
            e["layer"] = layer
        claims = _claims(r, rest, m_sources, view_sources)
        if claims or "attributes" not in rest.get("_absent", []):
            e["attributes"] = claims
        for k, v in rest.items():
            if not k.startswith("_"):
                e[k] = v
        for k in rest.get("_absent", []):
            e.pop(k, None)
        edges[rid] = e
    if view is not None:
        out_nodes, out_edges = [], []
        for kind, key in view["order"]:
            if kind in ("scope", "item"):
                if key in nodes:
                    out_nodes.append(nodes[key])
            elif kind == "kept_node":
                out_nodes.append(view["kept_nodes"][key])
            elif kind == "relation":
                if key in edges:
                    out_edges.append(edges[key])
            else:
                out_edges.append(view["kept_edges"][key])
        return _ordered(view["graph"], out_nodes, out_edges)
    node_list, edge_list = list(nodes.values()), list(edges.values())
    claims = sum(len(n["attributes"]) for n in node_list) + sum(len(e.get("attributes", [])) for e in edge_list)
    return {"schema": "twin-graph-1", "source_model": f"context map {m['map']['site']}", "model_kind": "context_map",
            "title": m["map"].get("name"), "nodes": node_list, "edges": edge_list, "questions": [], "events": [],
            "not_exported": [{"section": k, "items": v, "why": "context-map-1 content twin-graph-1 cannot carry"}
                             for k, v in sorted(not_exported.items())],
            "counts": {"nodes": len(node_list), "edges": len(edge_list), "claims": claims, "questions": 0,
                       "events": 0}}


def _ordered(graph_head, nodes, edges):
    """Rebuild the original key order: schema/source_model/model_kind/title, then nodes and edges, then the rest."""
    out = {}
    for k, v in graph_head.items():
        out[k] = v
        if k == "title" or (k == "model_kind" and "title" not in graph_head):
            out["nodes"], out["edges"] = nodes, edges
    out.setdefault("nodes", nodes)
    out.setdefault("edges", edges)
    return out


# ---------------------------------------------------------------- CLI

def write(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("from-one-map", "a twin-graph-2 graph.json (one_map.py build) -> context map"),
                           ("from-twin-graph-1", "a twin-graph-1 graph (graph_export.py) -> context map"),
                           ("to-twin-graph-1", "a context map -> twin-graph-1 graph")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("input")
        p.add_argument("--out", required=True)
        if name == "from-twin-graph-1":
            p.add_argument("--site", default="SITE", help="site id for the map (twin-graph-1 has none)")
    p = sub.add_parser("validate", help="check a context map against the schema and its own cross-references")
    p.add_argument("map")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            errors = check(load_json(a.map))
            for e in errors:
                print(e)
            print(f"{a.map}: {'valid' if not errors else f'{len(errors)} problem(s)'}")
            return 0 if not errors else 1
        src = load_json(a.input)
        if a.cmd == "from-one-map":
            out = from_one_map(src)
        elif a.cmd == "from-twin-graph-1":
            out = from_twin_graph_1(src, site=a.site)
        else:
            out = to_twin_graph_1(src)
        if a.cmd != "to-twin-graph-1":
            errors = check(out)
            if errors:
                for e in errors[:20]:
                    print(e, file=sys.stderr)
                print(f"refused: the converted map has {len(errors)} problem(s); nothing written", file=sys.stderr)
                return 1
        write(out, a.out)
        rep = (out.get("extensions") or {}).get(REPORT)
        if rep:
            kept = sum(rep["edges_kept_out"].values()) + sum(rep["nodes_kept_out"].values())
            print(f"{a.out}: {len(out['plant']['items'])} items, {len(out['plant']['relations'])} relations; "
                  f"{kept} nodes/edges kept out (see extensions.{REPORT})")
        else:
            print(f"{a.out}: {len(out['nodes'])} nodes, {len(out['edges'])} edges")
        return 0
    except (MapError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
