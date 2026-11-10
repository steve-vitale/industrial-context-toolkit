"""Build one map: the plant half and the document half of a site in one twin-graph-2 graph, with every disagreement
kept as a conflict record routed to the owner of the record, and review queues split by owner, plant and unit.

    python scripts/one_map.py build examples/one-map/inputs/site.json --out out/one-map      # first or incremental run
    python scripts/one_map.py draft-lists examples/one-map/inputs/site.json --out out/drafts # start from drawings
    python scripts/one_map.py check out/one-map/graph.json                                  # validate a one-map graph
    python scripts/one_map.py loops-from-graph examples/graph-export/sheet0_graph.json --out out/sheet0-loops.md
    python scripts/one_map.py split-queue my-bundle/review_queue.csv --by belongs_to --out out/queues
    python scripts/one_map.py ask --map out/one-map/graph.json --question-kind measured-by --item HT-100
    python scripts/one_map.py jsonld --map out/one-map/graph.json --out out/one-map/map.jsonld
    python scripts/one_map.py changes old/graph.json new/graph.json --out out/changes  # what a new build changed
    python scripts/one_map.py affected --map out/one-map/graph.json --tags FDV-2210 --out out/moc  # MOC open
    python scripts/one_map.py affected --tags FDV-2210 --closeout open/graph.json close/graph.json --out out/moc
    python scripts/one_map.py sheet-from-prediction predictions/r2-tiles-trace/codex/0.json --sheet 140 --rev A \
        --plant P1 --unit MSS --out sheet.json   # a drawing reader's prediction -> a sheet read for build

Two starts, one map. (A) From lists: a maintenance equipment export, an instrument index and a control-system loop
list (loop_audit.py's input contract) form the skeleton; drawings listed in a drawing register locate each tag
(sheet, zone), confirm signal lines and supply piping. (B) From drawings only: draft-lists writes draft lists in
the same formats (status unverified, tiered for review with the safety floor); once reviewed they are ordinary lists
and (A) applies on every later revision. A site can mix both, scope by scope.

Identity is site-qualified (SITE/PLANT/UNIT/TAG); legacy tags are never renumbered and earlier tags stay as aliases.
A shared utility system has exactly one owning scope and is referenced from plants across boundary nodes. Loops
come from the list; drawing loop-number grouping only flags loops the list lacks. Documents (a context-sources-1
manifest, fingerprinted by context_register.load_sources) cover scopes, mention tags (exact matching only: an
ambiguous or near-miss tag is never asserted) and are based on other documents' revisions; a basis change reopens
dependents. Conflicts are graph nodes with what each source says and a record owner; only a person's decision
(--decisions) changes their status. Deterministic, offline, stdlib only; no model calls. See docs/ONE_MAP.md.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_export as gx  # noqa: E402
import loop_audit  # noqa: E402
import context_register as cr  # noqa: E402
import extract_text  # noqa: E402
import ontology as onto_mod  # noqa: E402

SCHEMA = "twin-graph-2"
SITE_SCHEMA = "one-map-site-1"
SHEET_SCHEMA = "one-map-sheet-1"
STATE_SCHEMA = "one-map-state-1"
DOC_STATUSES = ("draft", "released")
CONFLICT_STATUSES = ("open", "disputed", "resolved")
CONFLICT_TYPES = {
    "asset_presence": "an asset is in one source and not in the other",
    "value_disagreement": "two sources give different values for the same attribute",
    "mention_not_in_register": "a document mentions a tag the maintenance export does not hold",
    "ambiguous_reference": "a document names a tag that exists in more than one scope it could mean",
    "superseded_basis": "a document is based on a revision that has been superseded",
    "loop_pairing": "the loop list and the drawings pair a controller differently",
    "loop_reference": "the loop list names a tag the drawings of its unit do not show",
    "boundary": "two sides of a plant or utility boundary disagree",
    "unlisted_loop": "the drawings show a possible loop the loop list does not hold",
}
TIER_ORDER = {"red": 0, "amber": 1, "green": 2}
QUEUE_COLS = ("rank", "tier", "owner", "plant", "unit", "item", "kind", "why", "safety", "spot_check")
TAG_TEXT = re.compile(r"(?<![A-Za-z0-9/_.-])((?:[A-Z0-9]+/){1,3})?([A-Z]{1,5})([- ]?)(\d{2,5})([A-Z]{0,2})"
                      r"(?![A-Za-z0-9_-])")
CONTROLLER = re.compile(r"^[A-Z]D?I?C$")           # FIC, TIC, PC, PDIC; not FCV (ends in V)
MEASUREMENT = re.compile(r"^[A-Z]D?[TE]$|^[A-Z]IT$")  # FT, TE, PT, PDT, RE, FIT
FINAL = re.compile(r"^[A-Z]C?V$|^XV$|^[A-Z]Y$")      # FV, TCV, PV, LCV, XV; a transducer FY drives one
# Mentions written in another case or another style (P101, p-101, PSV 204) of exactly one map tag; letters only.
TAG_TEXT_ANY_CASE = re.compile(r"(?<![A-Za-z0-9/_.-])([A-Za-z]{1,5})([- ]?)(\d{2,5})([A-Za-z]{0,2})(?![A-Za-z0-9_-])")
CONFIRM = "possible mention, confirm"
OCR_CONFIRM = "possible mention (OCR), confirm"  # OCR text never links (it turns tags into other tags)
EQUIPMENT_KINDS = ("equipment", "final_element", "relief_device")
# Columns a generated draft list adds for its reviewer; the import path reads them as review notes, not claims.
DRAFT_COLS = {"review_tier", "how_found", "confidence", "located_on", "reviewed_by", "reviewed_on"}
SCOPE_KINDS = ("system", "unit", "plant", "site", "scope")
# Which record is authoritative for each kind of fact (site file `authority` overrides any entry). The P&ID is the
# authority for connectivity, tags and the control scheme; values printed on it are reference only.
DEFAULT_AUTHORITY = {"connectivity": "pid", "tags": "pid", "control_scheme": "pid", "rating": "datasheet",
                     "size": "datasheet", "material": "datasheet", "instrument_range": "instrument_index",
                     "instrument_model": "instrument_index", "installed": "maintenance_export"}
RECORD_TYPES = ("pid", "datasheet", "maintenance_export", "instrument_index", "loop_list")
PID_NOTE = "P&ID value note"
DOC_TEXT_NOTE = "document text note"
# extract_text.py add-ons a site file may switch on for its documents (`document_text`); all off by default
DOC_TEXT_OPTIONS = ("ocr", "ocr_lang", "ocr_dpi", "convert_legacy", "pdf_layout", "excel_display")
LOW_PRIORITY_KINDS = (PID_NOTE, DOC_TEXT_NOTE)  # amber, after every other amber row
RECORD_NAMES = {"maintenance_export": "maintenance equipment export", "instrument_index": "instrument index",
                "loop_list": "loop list", "datasheet": "datasheet", "pid": "P&ID"}


def default_fact_kind(name):
    """The fact kind of an attribute name when the site file's `fact_kinds` does not name it; None = no authority."""
    n = name.lower()
    if n.startswith(("rated_", "design_", "max_", "min_")) or n in ("rating", "duty", "capacity", "set_pressure"):
        return "rating"
    if n in ("size", "line_size", "nominal_size") or n.endswith("_size"):
        return "size"
    if "material" in n:
        return "material"
    if "range" in n:
        return "instrument_range"
    if n in ("model", "manufacturer", "make", "vendor"):
        return "instrument_model"
    if n.startswith("installed") or n in ("serial", "serial_number", "asset_number"):
        return "installed"
    return None


# Optional per-item fields a converted reader prediction carries (sheet-from-prediction); copied onto the appearance.
READER_FIELDS = ("reader_symbol", "reader_class", "reader_confidence", "printed_tag", "tag_status")


class InputError(ValueError):
    pass


# ---------------------------------------------------------------- small helpers

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def short(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:10]


def part(value, where):
    """One identity segment: text without '/', no surrounding whitespace (never trimmed silently)."""
    if not isinstance(value, str) or not value or value != value.strip() or "/" in value:
        raise InputError(f"{where} must be nonempty text without '/' or surrounding spaces (got {value!r})")
    return value


def qid(*parts):
    return "/".join(parts)


def norm(tag):
    return re.sub(r"[\s\-_]", "", tag or "").upper()


def loop_key(tag):
    """(letters, loop number, suffix) from 'FV-2203A' -> ('FV', '2203', 'A'); None when it is not a loop tag."""
    m = re.fullmatch(r"([A-Z]{1,5})[\s-]*(\d{2,6})([A-Z]{0,2})", (tag or "").strip().upper())
    return (m.group(1), m.group(2), m.group(3)) if m else None


def role_of(letters):
    if letters is None:
        return None
    if CONTROLLER.match(letters):
        return "controller"
    if MEASUREMENT.match(letters):
        return "measurement"
    if FINAL.match(letters):
        return "final"
    return None


def safety_of(tag):
    """confidence.safety_function on the tag's letters: the same rule the twin's safety floor uses."""
    import confidence
    lk = loop_key(tag)
    found = confidence.safety_function(lk[0] if lk else None, None, tag, set())
    return found[0] if found else ""


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "unassigned"


def inside(root, rel, where):
    """A path from an input file, kept inside that file's folder (reuses the register's rule)."""
    if not isinstance(rel, str) or not rel.strip():
        raise InputError(f"{where}: a path is required")
    local = (root / rel).resolve()
    if Path(rel).is_absolute() or re.match(r"^[A-Za-z]:", rel) or not local.is_relative_to(root):
        raise InputError(f"{where}: path {rel!r} must stay inside {root.name}/")
    return local


def read_json(path, what):
    try:
        return cr.read_json(path, what)
    except cr.InputError as exc:
        raise InputError(str(exc)) from None


def read_csv(path, what, required):
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"{what} {path}: can't read as UTF-8 ({exc})") from None
    text = "".join(ln for ln in text.splitlines(keepends=True) if not ln.lstrip().startswith("#"))
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in required if c not in header]
    if missing:
        raise InputError(f"{what} {path}: missing column(s) {', '.join(missing)}")
    if any(None in r for r in rows):
        raise InputError(f"{what} {path}: a row has more fields than the header")
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in rows]


def claim(name, value, source, status="unverified"):
    return {"name": name, "value": value, "status": status, "source": source}


def mk_node(id_, kind, tag, name, source, *, aliases=(), attributes=(), status="unverified", **extra):
    return {"id": id_, "kind": kind, "tag": tag, "name": name, "aliases": list(aliases), "status": status,
            "attributes": list(attributes), "source": source, **extra}


def mk_edge(type_, a, b, source, *, status="unverified", attributes=(), **extra):
    return {"id": f"{type_}:{a}->{b}", "type": type_, "from": a, "to": b, "status": status, "direction": None,
            "source": source, "attributes": list(attributes), **extra}


# ---------------------------------------------------------------- inputs

def load_site(path):
    path = Path(path).resolve()
    site = read_json(path, "site file")
    if not isinstance(site, dict) or site.get("schema") != SITE_SCHEMA:
        raise InputError(f"{path.name}: needs schema {SITE_SCHEMA}")
    root = path.parent
    sid = part((site.get("site") or {}).get("id"), "site.id")
    plants = {}
    for p in site.get("plants") or []:
        pid = part(p.get("id"), "plant id")
        if pid in plants:
            raise InputError(f"plant {pid} listed twice")
        units = {}
        for u in p.get("units") or []:
            uid = part(u.get("id"), f"plant {pid} unit id")
            if uid in units:
                raise InputError(f"unit {pid}/{uid} listed twice")
            units[uid] = u
        plants[pid] = {"name": p.get("name"), "units": units, "owner": p.get("owner")}
    scopes = {}
    for s in site.get("scopes") or []:
        scid = part(s.get("id"), "scope id")
        if scid in plants or scid in scopes:
            raise InputError(f"scope {scid} reuses a plant or scope id")
        if not s.get("owner"):
            raise InputError(f"scope {scid} needs an owner")
        scopes[scid] = s
    shared = {}
    for s in site.get("shared_systems") or []:
        sys_id = part(s.get("id"), "shared system id")
        owner = s.get("owner_scope")
        valid = {qid(sid, x) for x in list(plants) + list(scopes)}
        if owner not in valid:
            raise InputError(f"shared system {sys_id}: owner_scope {owner!r} must be exactly one plant or scope "
                             f"({', '.join(sorted(valid))})")
        if sys_id in shared:
            raise InputError(f"shared system {sys_id} listed twice (a shared system has exactly one owner)")
        shared[sys_id] = s
    owners = site.get("record_owners") or {}
    routing = site.get("routing") or {}
    unknown = sorted(set(routing) - set(CONFLICT_TYPES))
    if unknown:
        raise InputError(f"routing names unknown conflict type(s): {', '.join(unknown)}")
    for t, rec in routing.items():
        if rec not in owners and rec not in ("document", "shared_system_owner"):
            raise InputError(f"routing {t} -> {rec!r}: not a record type in record_owners")
    for kind, rec in (site.get("authority") or {}).items():
        if rec not in RECORD_TYPES:
            raise InputError(f"authority {kind} -> {rec!r}: not a record type ({', '.join(RECORD_TYPES)})")
    # an override acts only when it has no certification entry (1.0 behaviour) or a certified one; a draft override
    # leaves the default in place and becomes a review row for the overridden record's owner
    certs = site.get("authority_certification") or {}
    overrides, draft_overrides = {}, []
    for kind, rec in (site.get("authority") or {}).items():
        c = certs.get(kind)
        if c is not None and not onto_mod.certified(c):
            draft_overrides.append((kind, rec, c))
        else:
            overrides[kind] = rec
    authority = dict(DEFAULT_AUTHORITY, **overrides)
    fact_kinds = site.get("fact_kinds") or {}
    for name, kind in fact_kinds.items():
        if kind not in authority:
            raise InputError(f"fact_kinds {name} -> {kind!r}: not a fact kind in the authority map")
    as_of = site.get("as_of")
    if as_of is not None and not onto_mod.DATE.match(str(as_of)):
        raise InputError("as_of must be a date YYYY-MM-DD")
    try:
        onto = onto_mod.Ontology.load(letter_overrides=site.get("letter_overrides"),
                                      equipment_prefixes=site.get("equipment_prefixes"))
    except onto_mod.OntologyError as exc:
        raise InputError(str(exc)) from None
    doc_text = site.get("document_text") or {}
    bad = sorted(set(doc_text) - set(DOC_TEXT_OPTIONS)) if isinstance(doc_text, dict) else ["(not an object)"]
    if bad:
        raise InputError(f"document_text: unknown option(s) {', '.join(bad)} (allowed: {', '.join(DOC_TEXT_OPTIONS)})")
    return {"path": path, "root": root, "raw": site, "site": sid, "site_name": site["site"].get("name"),
            "plants": plants, "scopes": scopes, "shared": shared, "owners": owners, "routing": routing,
            "authority": authority, "fact_kinds": fact_kinds, "sample_every": int(site.get("spot_check_every", 10)),
            "draft_overrides": draft_overrides, "as_of": as_of, "onto": onto, "document_text": doc_text}


def load_register(cfg):
    """The sheet index. A site file without `drawing_register` has no drawings yet (a lists-only start): no sheets."""
    rel = cfg["raw"].get("drawing_register")
    if rel is None:
        return []
    path = inside(cfg["root"], rel, "drawing_register")
    rows = read_csv(path, "drawing register", ("sheet", "rev", "plant", "unit", "owner", "path"))
    out, seen = [], set()
    for n, r in enumerate(rows, 2):
        where = f"drawing register line {n}"
        sheet = part(r["sheet"], f"{where} sheet")
        plant = part(r["plant"], f"{where} plant")
        if plant not in cfg["plants"] and plant not in cfg["scopes"]:
            raise InputError(f"{where}: plant/scope {plant!r} is not in the site file")
        unit = r["unit"]
        if plant in cfg["plants"]:
            part(unit, f"{where} unit")
            if unit not in cfg["plants"][plant]["units"]:
                raise InputError(f"{where}: unit {plant}/{unit} is not in the site file")
        elif unit:
            raise InputError(f"{where}: a scope sheet ({plant}) has no unit")
        doc = f"PID-{plant}-{sheet}"
        if doc in seen:
            raise InputError(f"{where}: sheet {plant}/{sheet} listed twice")
        seen.add(doc)
        if not r["rev"] or not r["owner"]:
            raise InputError(f"{where}: rev and owner are required")
        out.append({"doc": doc, "sheet": sheet, "rev": r["rev"], "plant": plant, "unit": unit, "owner": r["owner"],
                    "path": inside(cfg["root"], r["path"], where), "rel": r["path"],
                    "status": r.get("status") or "released"})
    return out


# ---------------------------------------------------------------- primary records: the skeleton comes from lists

def kind_for(tag, declared=None):
    if declared:
        if declared not in gx.NODE_KINDS:
            raise InputError(f"{tag}: kind {declared!r} is not a graph node kind")
        return declared
    lk = loop_key(tag)
    role = role_of(lk[0]) if lk else None
    if safety_of(tag) == "relief device":
        return "relief_device"
    return {"final": "final_element", "controller": "controller", "measurement": "instrument"}.get(role, "instrument")


def within(scope, scopes):
    return any(scope == s or scope.startswith(s + "/") for s in scopes)


def list_specs(cfg):
    """(record, default kind, spec) for every primary list; a record may be one list or several scoped lists."""
    out = []
    for record, default_kind in (("maintenance_export", "equipment"), ("instrument_index", None)):
        specs = cfg["raw"].get(record) or []
        for spec in ([specs] if isinstance(specs, dict) else specs):
            for sc in spec.get("scopes") or []:
                if sc != cfg["site"] and not sc.startswith(cfg["site"] + "/"):
                    raise InputError(f"{record} {spec.get('id')}: scope {sc!r} is not in site {cfg['site']}")
            out.append((record, default_kind, spec))
    return out


def covering(lists, record, scope):
    """The list of this record type whose declared scopes cover scope, or None (path B: no list yet)."""
    return next((x for x in lists.get(record, []) if within(scope, x["scopes"])), None)


def row_scope(cfg, record, lid, n, r, spec_scopes):
    """(tag, scope id) of one record row, refusing a plant, unit or scope the site file or the record does not hold."""
    tag = part(r["tag"], f"{record} row {n} tag")
    plant = part(r["plant"], f"{record} row {n} plant")
    if plant not in cfg["plants"] and plant not in cfg["scopes"]:
        raise InputError(f"{record} row {n}: plant/scope {plant!r} is not in the site file")
    if r["unit"] and (plant not in cfg["plants"] or r["unit"] not in cfg["plants"][plant]["units"]):
        raise InputError(f"{record} row {n}: unit {plant}/{r['unit']} is not in the site file")
    scope = qid(cfg["site"], plant, r["unit"]) if r["unit"] else qid(cfg["site"], plant)
    if not within(scope, spec_scopes):
        raise InputError(f"{record} {lid} row {n}: {scope} is outside the list's declared scopes "
                         f"({', '.join(spec_scopes)})")
    return tag, scope


def load_datasheets(m, lists):
    """Equipment datasheets and instrument spec sheets (CSV tag,plant,unit + value columns): the authority for
    ratings, sizes and materials (site file `authority`). A datasheet adds values to an item an equipment or
    instrument record or a P&ID already holds; it never creates one. A row for an item nobody else holds is a review
    item for the datasheet's owner."""
    cfg = m.cfg
    specs = cfg["raw"].get("datasheets") or []
    for spec in ([specs] if isinstance(specs, dict) else specs):
        path = inside(cfg["root"], spec.get("path"), "datasheets.path")
        rows = read_csv(path, "datasheet", ("tag", "plant", "unit"))
        lid = part(spec.get("id"), "datasheets.id")
        m.record_of[lid] = "datasheet"
        base = {"kind": "document", "document": lid, "revision": spec.get("revision"),
                "sha256": sha_bytes(path.read_bytes()), "path": spec.get("path")}
        owner = cfg["owners"].get("datasheet") or "needs owner"
        spec_scopes = spec.get("scopes") or [cfg["site"]]
        seen = {}
        for n, r in enumerate(rows, 2):
            tag, scope = row_scope(cfg, "datasheet", lid, n, r, spec_scopes)
            nid = qid(scope, tag)
            if nid in seen:
                raise InputError(f"datasheet {lid} row {n}: {nid} already on row {seen[nid]}")
            seen[nid] = n
            if nid not in m.nodes:
                m.review.append({"item": nid, "kind": "datasheet without an item", "owner": owner,
                                 "why": f"datasheet {lid} row {n} describes {tag}, which no equipment or instrument "
                                        f"record and no P&ID of {scope} holds"})
                continue
            src = dict(base, locator=f"row {n}")
            status = r.get("status") if r.get("status") in gx.STATUSES else "unverified"
            for k, v in sorted(r.items()):
                if k not in ("tag", "plant", "unit", "status", "description") and v:
                    c = claim(k, v, src, status)
                    m.held[nid].setdefault(lid, {})[k] = c
                    m.add_value(nid, c, "datasheet")
        lists.setdefault("datasheet", []).append({"id": lid, "source": base, "owner": owner, "rows": seen,
                                                  "scopes": spec_scopes})


def load_lists(m):
    """Maintenance equipment export and instrument index: one node per row, site/plant/unit(/system) qualified.
    These are the skeleton; drawings only locate and connect what they hold. A row repeated in one list refuses."""
    cfg, sid = m.cfg, m.cfg["site"]
    lists = {}
    for record, default_kind, spec in list_specs(cfg):
        path = inside(cfg["root"], spec.get("path"), f"{record}.path")
        rows = read_csv(path, record, ("tag", "plant", "unit"))
        lid = part(spec.get("id"), f"{record}.id")
        m.record_of[lid] = record
        base = {"kind": "document", "document": lid, "revision": spec.get("revision"),
                "sha256": sha_bytes(path.read_bytes()), "path": spec.get("path")}
        owner = cfg["owners"].get(record) or "needs owner"
        spec_scopes = spec.get("scopes") or [sid]
        seen = {}
        for n, r in enumerate(rows, 2):
            tag, scope = row_scope(cfg, record, lid, n, r, spec_scopes)
            nid = qid(scope, tag)
            if nid in seen:
                raise InputError(f"{record} row {n}: {nid} already listed on row {seen[nid]}")
            seen[nid] = n
            src = dict(base, locator=f"row {n}")
            status = r.get("status") if r.get("status") in gx.STATUSES else "unverified"
            skip = {"tag", "plant", "unit", "kind", "status", "system", "former_tag", "description",
                    "class"} | DRAFT_COLS
            attrs = [claim(k, v, src, status) for k, v in sorted(r.items()) if k not in skip and v]
            m.held[nid][lid] = {c["name"]: c for c in attrs}
            aliases = [r["former_tag"]] if r.get("former_tag") else []
            if r.get("class"):
                m.explicit_class.setdefault(nid, []).append((r["class"], lid))
            existing = m.nodes.get(nid)
            if existing is None:
                kind = kind_for(tag, r.get("kind"))
                if kind == "instrument" and default_kind and not r.get("kind"):
                    kind = default_kind  # a maintenance row with no instrument letters is equipment
                n_ = mk_node(nid, kind, tag, r.get("description") or None,
                             src, aliases=aliases, attributes=attrs, status=status, scope=scope, owner=owner,
                             listed_in=[lid], appearances=[])
                if safety_of(tag):
                    n_["safety"] = safety_of(tag)
                m.nodes[nid] = n_
            else:  # the same tag in both records: one item, two records
                existing["listed_in"].append(lid)
                for c in attrs:
                    m.add_value(nid, c, record)
            parent = scope
            if r.get("system"):
                system = r["system"]
                if system in cfg["shared"]:
                    parent = qid(cfg["shared"][system]["owner_scope"], system)
                else:
                    parent = qid(scope, part(system, f"{record} row {n} system"))
                    if parent not in m.nodes:
                        m.node(mk_node(parent, "system", system, None, src))
                        m.edge(mk_edge("contains", scope, parent, src))
            m.edge(mk_edge("contains", parent, nid, src))
        lists.setdefault(record, []).append({"id": lid, "source": base, "owner": owner, "rows": seen,
                                             "scopes": spec_scopes})
    # the same tag listed in two units: legitimate under qualified ids, but a bare tag is then ambiguous
    by_tag = defaultdict(list)
    for nid, n in m.nodes.items():
        if n.get("listed_in"):
            by_tag[n["tag"]].append(nid)
    for tag, ids in sorted(by_tag.items()):
        if len(ids) > 1:
            m.review.append({"item": ids[0], "kind": "tag in two scopes", "owner": m.nodes[ids[0]]["owner"],
                             "why": f"tag {tag} is listed as {', '.join(sorted(ids))}; a bare '{tag}' in a document "
                                    "or loop list is ambiguous unless its scope says which"})
    return lists


# ---------------------------------------------------------------- one sheet -> a fragment (what the drawing shows)

def sheet_fragment(cfg, row):
    """Parse one sheet model: the tags it shows (with zone/box), piping lines, signal lines and off-page connectors.
    Nothing here decides identity; place_fragments locates each tag against the lists."""
    data = row["path"].read_bytes()
    model = json.loads(data.decode("utf-8-sig"))
    if not isinstance(model, dict) or model.get("schema") != SHEET_SCHEMA:
        raise InputError(f"{row['rel']}: needs schema {SHEET_SCHEMA}")
    sid = cfg["site"]
    scope = qid(sid, row["plant"], row["unit"]) if row["unit"] else qid(sid, row["plant"])
    items, review = [], []
    seen = set()
    for section in ("equipment", "instruments"):
        for it in model.get(section) or []:
            tag = part(it.get("tag"), f"{row['rel']} {section} tag")
            if tag in seen:
                review.append({"item": qid(scope, tag), "kind": "duplicate tag", "owner": row["owner"],
                               "why": f"tag {tag} appears twice on sheet {row['sheet']}; confirm both are real"})
                continue
            seen.add(tag)
            at = f"sheet {row['sheet']}" + (f" zone {it['zone']}" if it.get("zone") else "")
            if it.get("tag_status") == "placeholder":  # carried, never dropped: a person supplies the real tag
                review.append({"item": qid(scope, tag), "kind": "placeholder tag", "owner": row["owner"],
                               "why": f"{tag} on {at} is a placeholder as printed ({it.get('printed_tag') or tag}); "
                                      "a person supplies the real tag"})
            items.append({"tag": tag, "section": section, "zone": it.get("zone"), "box_0_1000": it.get("box_0_1000"),
                          "on": it.get("on"), "on_line": it.get("on_line"), "name": it.get("name"),
                          "former_tag": it.get("former_tag"),
                          "attributes": {k: v for k, v in sorted((it.get("attributes") or {}).items()) if gx.plain(v)},
                          **{k: it[k] for k in READER_FIELDS if it.get(k) is not None}})
    runs = {ln.get("id"): ln for ln in model.get("lines") or []}
    names = {op.get("id"): f"{op.get('id')} ({op['name']})" if op.get("name") else op.get("id")
             for op in model.get("offpage") or []}
    run = lambda c: f"run {runs[c]['from']} to {runs[c]['to']}" if c in runs else c  # noqa: E731
    for it in model.get("instruments") or []:  # placement unclear (sheet-from-prediction): a person decides
        cands = it.get("placement_candidates") or []
        if len(cands) < 2:
            continue
        at = f"sheet {row['sheet']}" + (f" zone {it['zone']}" if it.get("zone") else "")
        common = sorted(names.get(x, x) for x in set.intersection(
            *({runs[c]["from"], runs[c]["to"]} if c in runs else {c} for c in cands)))
        shown = ", ".join(run(c) for c in cands[:4]) + (", ..." if len(cands) > 4 else "")
        review.append({"item": qid(scope, part(it.get("tag"), f"{row['rel']} instruments tag")),
                       "kind": "placement unclear", "owner": row["owner"],
                       "why": f"{it['tag']} on {at} reaches {len(cands)} candidates within {PLACE_HOPS} hops of the "
                              f"reader's connections ({shown}); a person says what it is on"
                              + (f" (every candidate run ends at {', '.join(common)})" if common else "")})
    inline = []
    for u in model.get("untagged") or []:  # read by a drawing reader without a usable tag (sheet-from-prediction)
        sym = part(u.get("symbol"), f"{row['rel']} untagged symbol")
        at = f"sheet {row['sheet']}" + (f" zone {u['zone']}" if u.get("zone") else "")
        if u.get("class") in ("tank", "pump", "instrumentation"):
            review.append({"item": qid(scope, f"@{row['sheet']}", f"untagged-{sym}"), "kind": "untagged symbol",
                           "owner": row["owner"],
                           "why": f"a {u['class']} symbol ({sym}) on {at} has no readable tag"
                                  + (f" (printed text {u['printed_text']!r})" if u.get("printed_text") else "")
                                  + "; it is not on the map until a person supplies its tag"})
        else:
            inline.append(sym)
    if inline:
        review.append({"item": qid(scope, f"@{row['sheet']}", "untagged-inline"), "kind": "untagged in-line symbols",
                       "owner": row["owner"],
                       "why": f"{len(inline)} untagged valve/fitting symbol(s) read on sheet {row['sheet']} are kept "
                              "in the sheet read (`untagged`, with zone and box), not placed on the map as items"})
    offpage = []
    for op in model.get("offpage") or []:
        offpage.append({"id": part(op.get("id"), f"{row['rel']} offpage id"), "name": op.get("name"),
                        "to": op.get("to") or {}, "system": op.get("system"), "zone": op.get("zone"),
                        "attrs": {k: v for k, v in sorted((op.get("attributes") or {}).items()) if gx.plain(v)}})
    return {"doc": row["doc"], "sha256": sha_bytes(data), "rev": row["rev"], "scope": scope, "sheet": row["sheet"],
            "plant": row["plant"], "owner": row["owner"], "items": items, "offpage": offpage,
            "signals": [list(x) for x in model.get("signal_lines") or []],
            "lines": [dict(x) for x in model.get("lines") or []],
            "systems": [dict(x) for x in model.get("systems") or []], "review": review}


# ---------------------------------------------------------------- a drawing reader's prediction -> a sheet read

READER_TAG = re.compile(r"([A-Z]{1,6})[\s-]+([0-9][0-9A-Z]*|X{2,}|\?+|TBD|TBA)")  # stacked bubble "TCV 1401"
PLAIN_TAG = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)*")
PIPING = ("tank", "pump", "valve", "general")  # tagged symbols of these classes end piping lines
PASS_THROUGH = ("valve", "general")             # untagged in-line symbols a piping line runs through
MAX_RUN_ENDS = 12  # a network of in-line symbols touching more run ends than this writes no runs (12 ends = 66 runs)
PLACE_HOPS = 2     # an instrument bubble is placed from what it reaches within this many hops


def reader_tag(text):
    """(tag, printed, placeholder) for a reader's tag text. A stacked bubble ('TCV\\n1401') is joined as 'TCV-1401';
    text that is not tag-shaped (a name, a nozzle 'N1', an operator letter 'H') or has fewer than two digits and no
    placeholder gives tag None. The printed text is kept as read (whitespace collapsed)."""
    import build_twin as bt
    printed = bt.clean(text)
    if printed is None:
        return None, None, False
    up = printed.upper()
    placeholder = bool(bt.PLACEHOLDER.search(up))
    m = READER_TAG.fullmatch(up)
    tag = f"{m.group(1)}-{m.group(2)}" if m else up if PLAIN_TAG.fullmatch(up) else None
    if tag is None or (sum(ch.isdigit() for ch in tag) < 2 and not placeholder):
        return None, printed, False
    return tag, printed, placeholder


def sheet_from_prediction(pred_path, *, sheet, revision, plant, unit="", rows=None, cols=None, frame=None,
                          origin="bottom-right"):
    """One reader prediction (the documented format, bare or in its stored predictions/ form) -> a one-map-sheet-1
    read, plus a list of what could not be converted. Validated with the intake's own validator first. Tags are
    zoned with scripts/sheet_zone.py; untagged symbols are carried, not dropped; nothing is inferred beyond the
    reader's own symbols and connections."""
    import build_twin as bt
    import import_site_drawing as intake
    import sheet_zone as sz
    for value, what in ((sheet, "sheet"), (revision, "revision"), (plant, "plant")):
        part(value, what)
    if unit:
        part(unit, "unit")
    raw = Path(pred_path).read_bytes()
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"{pred_path}: not JSON ({exc})") from None
    stored = isinstance(doc, dict) and "prediction" in doc and "symbols" not in doc
    pred = doc.get("prediction") if stored else doc
    if pred is None:
        raise InputError(f"{pred_path}: the stored run failed (prediction null); there is no reading to convert")
    try:
        valid = intake.validate_prediction(pred)
    except ValueError as exc:
        raise InputError(f"{pred_path}: not in the documented prediction format: {exc}") from None
    grid = {"rows": sz.DEFAULT_ROWS if rows is None else rows, "cols": sz.DEFAULT_COLS if cols is None else cols,
            "frame": tuple(frame or sz.WHOLE_SHEET),
            "origin": origin}
    try:
        sz.zone_at(0, 0, **grid)
    except ValueError as exc:
        raise InputError(str(exc)) from None
    zone = lambda box: sz.zone_of_box(box, **grid)  # noqa: E731
    box_of = lambda box: [round(v, 1) for v in box]  # noqa: E731
    equipment, instruments, offpage, untagged, not_converted = [], [], [], [], []
    anchor = {}  # symbol id -> the line endpoint name in the sheet read (a tag, or an off-page connector id)
    by_id = {s["id"]: s for s in valid["symbols"]}
    tagged = {}
    adj = defaultdict(set)
    for c in valid["connections"]:
        adj[c["from"]].add(c["to"])
        adj[c["to"]].add(c["from"])
    for s in valid["symbols"]:
        tag, printed, placeholder = reader_tag(s["tag"])
        base = {"zone": zone(s["box"]), "box_0_1000": box_of(s["box"]), "reader_symbol": s["id"],
                "reader_class": s["class"]}
        if s["confidence"] is not None:
            base["reader_confidence"] = s["confidence"]
        if s["class"] == "inlet/outlet":
            op = {"id": s["id"], "name": printed, "zone": base["zone"]}
            ref = bt.DWG_REF.search((printed or "").upper())
            if ref:
                op["attributes"] = {"drawing_reference": f"{ref.group(1) + ' ' if ref.group(1) else ''}PID "
                                                         f"{ref.group(2)}-{ref.group(3)}"}
            offpage.append(op)
            anchor[s["id"]] = s["id"]
            continue
        if tag is None:
            untagged.append({"symbol": s["id"], "class": s["class"], "zone": base["zone"],
                             "box_0_1000": base["box_0_1000"], "printed_text": printed,
                             "reader_confidence": s["confidence"]})
            continue
        item = dict({"tag": tag}, **base, printed_tag=printed,
                    tag_status="placeholder" if placeholder else "as_extracted")
        equip = s["class"] in ("tank", "pump") or (s["class"] == "general"
                                                   and bt.EQUIP_TAG.fullmatch(tag))
        (equipment if equip else instruments).append(item)
        tagged[s["id"]] = tag
        if s["class"] in PIPING:
            anchor[s["id"]] = tag
    # Piping runs (rules in docs/ONE_MAP.md, "Connectivity from a reader prediction"). Untagged valves and fittings
    # (class valve/general, no usable tag) are in-line items a run passes through, however many connections they
    # have; tagged equipment, tagged valves/fittings and off-page connectors end a run; instrument bubbles never carry
    # a run (a bubble's link is its leader or signal line, not pipe). Each connected group of untagged in-line items
    # is a network; a network touching N run ends yields one run per pair of ends (a tee joining three ends gives
    # three runs), written along one shortest path, unless N > MAX_RUN_ENDS (then no run goes through it; listed).
    conn_id = {frozenset((c["from"], c["to"])): f"c{i}" for i, c in enumerate(valid["connections"])}
    inline = {sid for sid, s in by_id.items() if s["class"] in PASS_THROUGH and sid not in tagged}
    nets, net_of = [], {}
    for sid in sorted(inline):
        if sid in net_of:
            continue
        members, todo = {sid}, [sid]
        while todo:
            cur = todo.pop()
            for nb in adj[cur]:
                if nb in inline and nb not in members:
                    members.add(nb)
                    todo.append(nb)
        for x in members:
            net_of[x] = len(nets)
        ends = sorted({n for x in members for n in adj[x] if n in anchor})
        nets.append({"members": members, "ends": ends, "expanded": len(ends) <= MAX_RUN_ENDS})
    walk = {x for x in inline if nets[net_of[x]]["expanded"]}
    dist, lines, self_loops = {}, {}, 0
    for start in sorted(anchor):  # breadth first: fewest symbols, ties broken by symbol id, so the output is stable
        prev, d, todo = {start: None}, {start: 0}, [start]
        while todo:
            nxt = []
            for cur in todo:
                for nb in sorted(adj[cur]):
                    if nb in prev or (nb not in anchor and nb not in walk):
                        continue
                    prev[nb], d[nb] = cur, d[cur] + 1
                    if nb in walk:
                        nxt.append(nb)
            todo = nxt
        dist[start] = d
        for end in sorted(n for n in d if n in anchor and n > start):
            if anchor[start] == anchor[end]:
                self_loops += 1
                continue
            path, p = [end], prev[end]
            while p is not None:
                path.append(p)
                p = prev[p]
            path.reverse()
            via = path[1:-1]
            nv = sum(1 for v in via if by_id[v]["class"] == "valve")
            no = len(via) - nv
            parts = ([f"{nv} valve{'s' if nv != 1 else ''}"] if nv else []) + (
                [f"{no} other in-line symbol{'s' if no != 1 else ''}"] if no else [])
            attrs = {"via_symbols": " ".join(via), "through": " and ".join(parts) or "direct",
                     "prediction_connections": " ".join(conn_id[frozenset(x)] for x in zip(path, path[1:])),
                     "how_found": "reader connections" + (" collapsed through untagged in-line symbols along one "
                                                          "shortest path" if via else "")}
            net = nets[net_of[via[0]]] if via else None
            if net and len(net["ends"]) > 2:
                attrs["branched_network"] = (f"{len(net['ends'])} run ends meet through {len(net['members'])} "
                                             "untagged in-line symbols; other paths may exist")
            lines[(start, end)] = {"id": f"L-{start}-{end}", "from": anchor[start], "to": anchor[end],
                                   "direction": "unknown", "attributes": attrs}
    on_line = {v for ln in lines.values() for v in ln["attributes"]["via_symbols"].split()}
    for u in untagged:
        u["on_a_line"] = u["symbol"] in on_line
    runs_at = defaultdict(set)
    for (a, b), ln in lines.items():
        runs_at[a].add(ln["id"])
        runs_at[b].add(ln["id"])

    def runs_through(x):  # every run with a shortest path through in-line symbol x
        return {ln["id"] for (a, b), ln in lines.items()
                if x in dist[a] and x in dist[b] and dist[a][x] + dist[b][x] == dist[a][b]}

    # Placement: walk out from a tagged instrument bubble through untagged in-line symbols, one hop at a time, up to
    # PLACE_HOPS. At the first hop that reaches anything the candidates are the tagged equipment reached, the runs
    # through each in-line symbol reached and the runs ending at each tagged valve or connector reached. Exactly one
    # candidate places it (`on` a vessel or pump, `on_line` a run); two or more are "placement unclear" for review.
    equip_ids = {t["reader_symbol"] for t in equipment}
    placed = on_runs = 0
    unclear = []
    for item in instruments:
        sid = item["reader_symbol"]
        if by_id[sid]["class"] != "instrumentation":
            continue
        seen, frontier, found = {sid}, [sid], set()
        for _ in range(PLACE_HOPS):
            nxt = []
            for cur in frontier:
                for nb in sorted(adj[cur]):
                    if nb in seen:
                        continue
                    seen.add(nb)
                    if nb in equip_ids:
                        found.add(("equipment", tagged[nb]))
                    elif nb in anchor:
                        found |= {("run", r) for r in runs_at[nb]}
                    elif nb in inline:
                        found |= {("run", r) for r in runs_through(nb)}
                        nxt.append(nb)
            if found:
                break
            frontier = nxt
        if len(found) == 1:
            what, target = next(iter(found))
            item["on" if what == "equipment" else "on_line"] = target
            placed += 1
            on_runs += what == "run"
        elif found:
            item["placement_candidates"] = sorted(t for _, t in found)
            unclear.append(item["tag"])
    counts = Counter(t["tag"] for t in equipment + instruments)
    dup = sorted(t for t, n in counts.items() if n > 1)
    branched = [{"run_ends": [anchor[e] for e in n["ends"]], "untagged_in_line_symbols": len(n["members"]),
                 "runs_written": n["expanded"]} for n in nets if len(n["ends"]) > 2]
    capped = [n for n in nets if not n["expanded"]]
    if self_loops:
        not_converted.append(f"{self_loops} connection path(s) joining two symbols with the same tag (no line drawn)")
    if capped:
        not_converted.append(f"{len(capped)} network(s) of untagged in-line symbols touch more than {MAX_RUN_ENDS} "
                             "run ends; no runs are written through them (conversion.branched_networks, "
                             "runs_written false)")
    lone = sorted(sid for sid in by_id if not adj[sid])
    if lone:
        not_converted.append(f"{len(lone)} symbol(s) with no connection: {', '.join(lone)}")
    instr = [i for i in instruments if by_id[i["reader_symbol"]]["class"] == "instrumentation"]
    not_converted += [
        "signal lines: the documented prediction format has no line type, so no signal lines are written and no "
        "loop is proposed from connectivity (loops come from the loop list or a format that carries line types, "
        "e.g. DEXPI; loop-number grouping still runs)",
        f"placement: {placed} of {len(instr)} tagged instrument bubble(s) placed ({on_runs} on a run); "
        f"{len(unclear)} reach more than one candidate within {PLACE_HOPS} hops (placement unclear, for review); "
        f"{len(instr) - placed - len(unclear)} reach no tagged item or run within {PLACE_HOPS} hops",
        f"untagged: {len(untagged)} symbol(s) without a usable tag are carried under `untagged` "
        f"({sum(1 for u in untagged if u['on_a_line'])} of them on a written run), not placed on the map",
        "off-page connectors: the reading has no target connector, so `to` is empty; the map pairs a connector with "
        "one on another registered sheet when their printed references name each other's sheets"]
    meta = {k: doc.get(k) for k in ("label", "tool", "model", "drawing", "prompt_sha256", "image_sha256")
            if stored and doc.get(k) is not None}
    read = {
        "schema": SHEET_SCHEMA,
        "note": "Converted from a drawing reader's prediction by one_map.py sheet-from-prediction. Every item is the "
                "reader's draft (unverified); zones are computed from the reader's boxes.",
        "source": dict({"kind": "reader_prediction", "path": Path(pred_path).as_posix(), "sha256": sha_bytes(raw),
                        "stored_form": stored, "sheet": sheet, "revision": revision, "plant": plant, "unit": unit},
                       **meta),
        "zone_grid": sz.grid_record(grid["rows"], grid["cols"], grid["frame"], origin),
        "equipment": equipment, "instruments": instruments,
        "lines": [lines[k] for k in sorted(lines)], "signal_lines": [], "offpage": offpage, "untagged": untagged,
        "conversion": {"symbols_in": len(valid["symbols"]), "connections_in": len(valid["connections"]),
                       "equipment": len(equipment), "instruments": len(instruments), "offpage": len(offpage),
                       "untagged": len(untagged), "lines": len(lines), "signal_lines": 0,
                       "placeholder_tags": sorted(t["tag"] for t in equipment + instruments
                                                  if t["tag_status"] == "placeholder"),
                       "duplicate_tags": dup, "instruments_placed": placed, "instruments_placed_on_runs": on_runs,
                       "placement_unclear": unclear, "branched_networks": branched,
                       "not_converted": not_converted}}
    return read

class Map:
    def __init__(self, cfg):
        self.cfg = cfg
        self.nodes, self.edges, self.conflicts, self.review = {}, {}, {}, []
        self.loops = []
        self.pid_values = []  # (item, claim) printed on a P&ID: reference values
        self.record_of = {}  # record id (an equipment/instrument record or datasheet id) -> record type
        self.explicit_class = {}  # node id -> [(class named by a record row, record id)]
        self.records = {}  # register id -> rows of the generic `records` registers (ccp, calibration_record, ...)
        self.glossary = []
        self.sources = []  # {"id", "register", "scopes"}: which record is the record for which scopes (coverage)
        self.expectations = None
        self.link_counts = None
        self.held = defaultdict(dict)  # node id -> {record id: {attribute: claim}}: each record's own values

    def record_type(self, source):
        return "pid" if source.get("kind") == "drawing" else self.record_of.get(source.get("document"), "unknown")

    def add_value(self, nid, c, record):
        """One attribute value from one record, compared under the site's authority map. A P&ID value is reference:
        a difference becomes a low-priority note to the P&ID owner, never a value conflict, and a record's value
        replaces it. Between records, the authoritative one (for the attribute's fact kind) is source A and the
        conflict goes to the owner of the other record; with no authority among them, to the newer record's owner."""
        node = self.nodes[nid]
        have = next((x for x in node["attributes"] if x["name"] == c["name"]), None)
        if have is None:
            node["attributes"].append(c)
            return
        if have["value"] == c["value"]:
            return
        have_rec, name = self.record_type(have["source"]), c["name"]
        if "pid" in (record, have_rec):
            pid_c, other = (c, have) if record == "pid" else (have, c)
            if record != "pid":
                node["attributes"][node["attributes"].index(have)] = c
            other_rec = self.record_type(other["source"])
            said = (f"sheet {other['source'].get('sheet')}" if other_rec == "pid" else
                    f"the {RECORD_NAMES.get(other_rec, other_rec)} {other['source'].get('document')}")
            self.review.append({"item": nid, "kind": PID_NOTE, "owner": self.cfg["owners"].get("pid") or "needs owner",
                                "why": f"{node['tag']} {name}: {pid_c['value']} printed on sheet "
                                       f"{pid_c['source'].get('sheet')}, {other['value']} in {said}. P&ID values are "
                                       "reference only; correct the P&ID at its next revision if it is wrong"})
            return
        kind = self.cfg["fact_kinds"].get(name) or default_fact_kind(name)
        auth = self.cfg["authority"].get(kind) if kind else None
        if auth in (record, have_rec) and record != have_rec:
            (a, a_rec), (b, b_rec) = (((have, have_rec), (c, record)) if have_rec == auth
                                      else ((c, record), (have, have_rec)))
            if a is c:
                node["attributes"][node["attributes"].index(have)] = c
            self.conflict("value_disagreement", nid, name, a["source"], a["value"], b["source"], b["value"],
                          record=b_rec, what=f"{node['tag']} {name}: {a['value']} in the {RECORD_NAMES.get(a_rec, a_rec)} "
                                             f"{a['source'].get('document')} (authoritative for {kind}), "
                                             f"{b['value']} in the {RECORD_NAMES.get(b_rec, b_rec)} "
                                             f"{b['source'].get('document')}")
        else:
            self.conflict("value_disagreement", nid, name, have["source"], have["value"], c["source"], c["value"],
                          record=record)

    def node(self, n):
        if n["id"] not in self.nodes:
            self.nodes[n["id"]] = n
        return self.nodes[n["id"]]

    def edge(self, e):
        if e["id"] not in self.edges:
            self.edges[e["id"]] = e

    def owner_for(self, ctype, record=None, document_owner=None, system_owner=None):
        rec = self.cfg["routing"].get(ctype) or record
        if rec == "document" or (rec is None and document_owner):
            return document_owner or "needs owner"
        if rec == "shared_system_owner" or (rec is None and system_owner):
            return system_owner or "needs owner"
        return self.cfg["owners"].get(rec) or "needs owner"

    def conflict(self, ctype, subject, attribute, src_a, says_a, src_b, says_b, *, record=None, what=None,
                 document_owner=None, system_owner=None, parties=()):
        key = {"type": ctype, "subject": subject, "attribute": attribute,
               "a": [src_a.get("document"), says_a], "b": [src_b.get("document"), says_b]}
        cid = f"C-{short(key)}"
        if cid in self.conflicts:
            return cid
        owner = self.owner_for(ctype, record, document_owner, system_owner)
        self.conflicts[cid] = {
            "id": cid, "type": ctype, "what": what or f"{CONFLICT_TYPES[ctype]}: {subject} {attribute}", "subject": subject,
            "attribute": attribute, "source_a": {"source": src_a, "says": says_a},
            "source_b": {"source": src_b, "says": says_b}, "record_owner": owner,
            "parties": sorted({p for p in parties if p} | {owner}), "status": "open", "detected": True,
            "history": []}
        return cid


def scope_of(node_id, cfg):
    """(plant, unit) of a qualified id, '' where it has none."""
    parts = node_id.split("/")
    plant = parts[1] if len(parts) > 1 and parts[1] not in ("DOC", "CONFLICT") else ""
    unit = parts[2] if len(parts) > 2 and plant in cfg["plants"] and parts[2] in cfg["plants"][plant]["units"] else ""
    return plant, unit


def hierarchy(m):
    cfg, sid = m.cfg, m.cfg["site"]
    site_src = {"kind": "document", "document": cfg["path"].name, "note": "site file"}
    m.node(mk_node(sid, "site", sid, cfg["site_name"], site_src, status="confirmed"))
    for pid, p in sorted(cfg["plants"].items()):
        m.node(mk_node(qid(sid, pid), "plant", pid, p["name"], site_src, status="confirmed"))
        m.edge(mk_edge("contains", sid, qid(sid, pid), site_src, status="confirmed"))
        for uid, u in sorted(p["units"].items()):
            m.node(mk_node(qid(sid, pid, uid), "unit", uid, u.get("name"), site_src, status="confirmed"))
            m.edge(mk_edge("contains", qid(sid, pid), qid(sid, pid, uid), site_src, status="confirmed"))
    for scid, s in sorted(cfg["scopes"].items()):
        m.node(mk_node(qid(sid, scid), "scope", scid, s.get("name"), site_src, owner=s["owner"], status="confirmed"))
        m.edge(mk_edge("contains", sid, qid(sid, scid), site_src, status="confirmed"))
    for sys_id, s in sorted(cfg["shared"].items()):
        nid = qid(s["owner_scope"], sys_id)
        m.node(mk_node(nid, "system", sys_id, s.get("name"), site_src, shared=True, owner_scope=s["owner_scope"],
                       status="confirmed"))
        m.edge(mk_edge("contains", s["owner_scope"], nid, site_src, status="confirmed"))


def scope_owner(cfg, scope_id):
    parts = scope_id.split("/")
    if len(parts) >= 2 and parts[1] in cfg["scopes"]:
        return cfg["scopes"][parts[1]]["owner"]
    if len(parts) >= 2 and parts[1] in cfg["plants"]:
        return cfg["plants"][parts[1]].get("owner")
    return None


def list_for(kind):
    """Which primary list should hold an item of this kind: equipment, valves and relief devices are maintained
    assets (maintenance export); transmitters and controllers are instruments (instrument index)."""
    return "maintenance_export" if kind in EQUIPMENT_KINDS else "instrument_index"


def place_fragments(m, register, fragments, lists):
    """Drawings locate listed tags (sheet, zone) and supply piping/signal topology. Mismatches become conflicts."""
    cfg, sid = m.cfg, m.cfg["site"]
    listed_by_tag = defaultdict(list)
    for nid, n in m.nodes.items():
        if n.get("listed_in"):
            listed_by_tag[n["tag"]].append(nid)
    covered_scopes = set()
    for row in register:
        f = fragments[row["doc"]]
        covered_scopes.add(f["scope"])
        doc_id = qid(sid, "DOC", row["doc"])
        src = {"kind": "drawing", "document": doc_id, "sheet": row["sheet"], "revision": row["rev"], "path": row["rel"]}
        m.node(mk_node(doc_id, "document", row["doc"], f"P&ID {row['sheet']}",
                       {"kind": "document", "document": doc_id, "revision": row["rev"], "path": row["rel"]},
                       status="confirmed", **{"class": cfg["onto"].doc_class("pid")},
                       document={"id": row["doc"], "revision": row["rev"], "status": row["status"],
                                 "owner": row["owner"], "department": row["owner"], "doc_type": "pid",
                                 "sha256": f["sha256"], "path": row["rel"]}))
        m.edge(mk_edge("covers", doc_id, f["scope"], {"kind": "document", "document": doc_id}, status="confirmed"))
        for r in f["review"]:
            m.review.append(dict(r))
        for it in f["items"]:
            nid = qid(f["scope"], it["tag"])
            at = dict(src, zone=it["zone"]) if it.get("zone") else dict(src)
            if it.get("box_0_1000"):
                at["box_0_1000"] = it["box_0_1000"]
            at.update({k: it[k] for k in READER_FIELDS if k in it and k != "tag_status"})
            node = m.nodes.get(nid)
            if node is None:  # not in any list: a drawing-only item (first appearance decides what to raise)
                kind = "equipment" if it["section"] == "equipment" else kind_for(it["tag"])
                record = list_for(kind)
                spec = covering(lists, record, f["scope"])
                elsewhere = [x for x in listed_by_tag.get(it["tag"], []) if x != nid]
                node = mk_node(nid, kind, it["tag"], it.get("name"), at,
                               aliases=[it["former_tag"]] if it.get("former_tag") else [], scope=f["scope"],
                               owner=row["owner"], listed_in=[], appearances=[])
                if safety_of(it["tag"]):
                    node["safety"] = safety_of(it["tag"])
                if it.get("tag_status") == "placeholder":
                    node["tag_status"] = "placeholder"
                m.nodes[nid] = node
                m.edge(mk_edge("contains", f["scope"], nid, at))
                if spec is None:  # path B: no list covers this scope yet; the drawing read is the draft
                    m.review.append({"item": nid, "kind": f"on the P&ID, not in the {RECORD_NAMES[record]}",
                                     "owner": cfg["owners"].get(record) or row["owner"],
                                     "why": f"{it['tag']} read from sheet {row['sheet']}"
                                            + (f" zone {it['zone']}" if it.get("zone") else "")
                                            + f"; no {RECORD_NAMES[record]} covers {f['scope']} yet: review the "
                                              f"draft {RECORD_NAMES[record]} from `one_map.py draft-lists`"})
                else:
                    m.conflict("asset_presence", nid, "listed", at, f"drawn on {row['sheet']} rev {row['rev']}",
                               spec["source"], "no row for this tag in this unit" + (
                                   f" (listed as {', '.join(elsewhere)}; not matched across scopes)" if elsewhere
                                   else ""), record=record, parties=(row["owner"],),
                               what=f"{it['tag']} is drawn on sheet {row['sheet']} but not in the "
                                    f"{record.replace('_', ' ')} for {f['scope']}")
            shown = dict(at, printed=dict(it["attributes"])) if it["attributes"] else at  # values printed there
            if shown not in node["appearances"]:
                node["appearances"].append(shown)
            if it.get("former_tag") and it["former_tag"] not in node["aliases"]:
                node["aliases"].append(it["former_tag"])
            for k, v in it["attributes"].items():  # reference values, compared once every record is in
                m.pid_values.append((nid, claim(k, v, at)))
        local = {it["tag"]: qid(f["scope"], it["tag"]) for it in f["items"]}
        for it in f["items"]:
            if it.get("on"):
                target = local.get(it["on"]) or qid(f["scope"], it["on"])
                if target not in m.nodes:
                    raise InputError(f"{row['rel']}: {it['tag']} is drawn on {it['on']}, which is not on the sheet")
                t = {"relief_device": "protects", "final_element": "acts_on",
                     "instrument": "measures"}.get(m.nodes[local[it["tag"]]]["kind"])
                if t:
                    m.edge(mk_edge(t, local[it["tag"]], target, src))
        for a, b in f["signals"]:
            if a not in local or b not in local:
                raise InputError(f"{row['rel']}: signal line {a}-{b} names a tag not on the sheet")
            m.edge(mk_edge("signal_line", local[a], local[b], src, how_found="drawn signal line"))
        ops = {op["id"]: qid(f["scope"], f"@{row['sheet']}", op["id"]) for op in f["offpage"]}
        for op in f["offpage"]:
            m.node(mk_node(ops[op["id"]], "offpage_connector", op["id"], op.get("name"), src,
                           attributes=[claim(k, v, src) for k, v in op["attrs"].items()], scope=f["scope"],
                           owner=row["owner"]))
        on_run = defaultdict(list)  # a run an instrument is placed on (sheet-from-prediction): kept on both sides
        for it in f["items"]:
            if it.get("on_line"):
                on_run[it["on_line"]].append(it["tag"])
        known = {ln.get("id") for ln in f["lines"]}
        for lid, tags in sorted(on_run.items()):
            if lid not in known:
                raise InputError(f"{row['rel']}: {', '.join(tags)} placed on run {lid}, which is not on the sheet")
            for tag in tags:
                for at in m.nodes[local[tag]]["appearances"]:
                    if at.get("document") == doc_id:
                        at["on_line"] = qid(f["scope"], f"@{row['sheet']}", lid)
        for ln in f["lines"]:
            lid = part(ln.get("id"), f"{row['rel']} line id")
            ends = [ops.get(x) or local.get(x) for x in (ln.get("from"), ln.get("to"))]
            if None in ends:
                raise InputError(f"{row['rel']}: line {lid} ends at a tag or connector not on the sheet")
            attrs = dict(ln.get("attributes") or {})
            if on_run.get(lid):
                attrs["instruments_on"] = " ".join(sorted(set(on_run[lid])))
            e = mk_edge("connects", ends[0], ends[1], src, layer="stream",
                        attributes=[claim(k, v, src) for k, v in sorted(attrs.items())])
            # a reader's run is a connection, not a flow direction: its ends are ordered by symbol id
            e["id"], e["direction"] = qid(f["scope"], f"@{row['sheet']}", lid), ln.get("direction") or "known"
            m.edge(e)
        for s in f["systems"]:
            sys_id = part(s.get("id"), f"{row['rel']} system id")
            if sys_id in cfg["shared"]:
                owner = cfg["shared"][sys_id]["owner_scope"]
                if not (f["scope"] == owner or f["scope"].startswith(owner + "/")):
                    m.conflict("boundary", qid(owner, sys_id), "owner_scope", src, f["scope"],
                               {"kind": "document", "document": cfg["path"].name}, owner,
                               what=f"sheet {row['sheet']} claims to own shared system {sys_id}, which the site "
                                    f"file gives to {owner}; it stays with one owner",
                               system_owner=scope_owner(cfg, owner), parties=(row["owner"],))
                continue
            nid = qid(f["scope"], sys_id)
            m.node(mk_node(nid, "system", sys_id, s.get("name"), src))
            m.edge(mk_edge("contains", f["scope"], nid, src))
    # listed but not on any drawing of a covered unit: the drawings' owner checks (an uncovered unit is reported)
    uncovered = defaultdict(int)
    for nid, n in sorted(m.nodes.items()):
        if n.get("listed_in") and not n["appearances"]:
            if n["scope"] in covered_scopes:
                m.conflict("asset_presence", nid, "drawn", n["source"], f"listed in {', '.join(n['listed_in'])}",
                           {"kind": "drawing_register", "document": "drawing register"},
                           "not on any registered sheet of " + n["scope"], record="pid", parties=(n["owner"],),
                           what=f"{n['tag']} is listed for {n['scope']} but no registered sheet of that unit shows it")
            else:
                uncovered[n["scope"]] += 1
    return dict(sorted(uncovered.items()))


def pair_offpage(m, fragments):
    """Pair off-page connectors across sheets and plants; a connector to a shared system crosses a boundary node."""
    cfg, sid = m.cfg, m.cfg["site"]
    by_ref = {}
    for f in fragments.values():
        for op in f["offpage"]:
            by_ref[(f["plant"], f["sheet"], op["id"])] = dict(op, node=qid(f["scope"], f"@{f['sheet']}", op["id"]),
                                                             owner=f["owner"], plant=f["plant"], sheet=f["sheet"])
    for key in sorted(by_ref):
        op = by_ref[key]
        src = m.nodes[op["node"]]["source"]
        sys_owner = None
        if op.get("system"):
            sysd = cfg["shared"].get(op["system"])
            if sysd is None:
                m.review.append({"item": op["node"], "kind": "boundary", "owner": op["owner"],
                                 "why": f"names system {op['system']}, which the site file does not list as shared"})
            else:
                sys_owner = scope_owner(cfg, sysd["owner_scope"])
                target = qid(sysd["owner_scope"], op["system"])
                if op["plant"] != sysd["owner_scope"].split("/")[1]:
                    bnd = qid(sid, op["plant"], f"BND-{op['system']}")
                    if bnd not in m.nodes:
                        bsrc = {"kind": "document", "document": cfg["path"].name, "note": "shared system reference"}
                        m.node(mk_node(bnd, "boundary", None, f"{op['plant']} boundary to {op['system']}", bsrc,
                                       status="confirmed"))
                        m.edge(mk_edge("contains", qid(sid, op["plant"]), bnd, bsrc, status="confirmed"))
                        m.edge(mk_edge("references", bnd, target, bsrc, status="confirmed"))
                    m.edge(mk_edge("references", op["node"], bnd, src))
                else:
                    m.edge(mk_edge("references", op["node"], target, src))
        to = op["to"]
        if not to:
            continue  # paired by printed reference below, or a review row
        ref = (to.get("plant"), to.get("sheet"), to.get("connector"))
        other = by_ref.get(ref)
        if other is None:
            m.conflict("boundary", op["node"], "pairs_with", src, "/".join(map(str, ref)),
                       {"kind": "drawing_register", "document": "drawing register"},
                       "no such connector in the register",
                       what="an off-page connector points to a sheet/connector the register does not hold",
                       system_owner=sys_owner or op["owner"], parties=(op["owner"],))
            continue
        back = other["to"] or {}
        if (back.get("plant"), back.get("sheet"), back.get("connector")) != key:
            m.conflict("boundary", op["node"], "pairs_with", src, other["node"], m.nodes[other["node"]]["source"],
                       "/".join(map(str, (back.get("plant"), back.get("sheet"), back.get("connector")))),
                       what="two off-page connectors do not point back at each other",
                       system_owner=sys_owner or op["owner"], parties=(op["owner"], other["owner"]))
            continue
        if key > ref:
            continue  # each pair once, from its lower end
        e = mk_edge("connects", op["node"], other["node"], src, layer="offpage_pair")
        e["direction"] = "unknown"
        m.edge(e)
        for name in sorted(set(op["attrs"]) & set(other["attrs"])):
            if op["attrs"][name] != other["attrs"][name]:
                m.conflict("boundary", op["node"], name, src, op["attrs"][name],
                           m.nodes[other["node"]]["source"], other["attrs"][name],
                           what=f"the two ends of an off-page pair ({op['plant']} {op['sheet']} and {other['plant']} "
                                f"{other['sheet']}) disagree on {name}",
                           system_owner=sys_owner or op["owner"], parties=(op["owner"], other["owner"]))
    pair_by_reference(m, by_ref)


def printed_ref(op):
    """(drawing, sheet) printed on an off-page connector ('ES PID 180-1' -> ('180', '1')), and its name without it."""
    import build_twin as bt
    text = " ".join(str(x) for x in (op["attrs"].get("drawing_reference"), op.get("name")) if x).upper()
    hit = bt.DWG_REF.search(text)
    rest = " ".join(bt.DWG_REF.sub(" ", (op.get("name") or "").upper()).split())
    return ((hit.group(2).lstrip("0") or "0", hit.group(3).lstrip("0") or "0") if hit else None), rest


def pair_by_reference(m, by_ref):
    """Connectors with no `to` (a reader prediction never has one) pair across registered sheets of the site by
    scripts/offpage_pairing.py, the one cross-sheet rule, with each registered sheet id as the number its connectors
    print ('ES PID 180-1' names sheet '180-1', '180-01' or, registered without sheet numbers, '180'). A pair becomes
    an offpage_pair edge whose how_found is the rule's method. Nothing is guessed: equally likely candidates, or a
    connector whose candidates paired elsewhere, become "off-page pairing unclear" review rows naming them; the rest
    are "off-page connector unpaired" rows (no reference, the named sheet is not registered, or nothing there points
    back)."""
    import offpage_pairing
    loose = {k: op for k, op in by_ref.items() if not op["to"]}
    sheet_key = {k: f"{k[0]}/{k[1]}" for k in by_ref}
    sheets = {sheet_key[k]: {"number": k[1]} for k in by_ref}
    node_key = {op["node"]: k for k, op in loose.items()}
    texts = {k: " ".join(str(x) for x in (op["attrs"].get("drawing_reference"), op.get("name")) if x)
             for k, op in loose.items()}
    result = offpage_pairing.pair([{"id": op["node"], "sheet": sheet_key[k], "text": texts[k]}
                                   for k, op in sorted(loose.items())], sheets)

    def label(op):
        return f"off-page connector {op['id']}" + (f" ({op['name']})" if op.get("name") else "") + \
            f" on sheet {op['sheet']}"

    by_pair = {}
    for p in result["pairs"]:
        a, b = sorted((node_key[p["a"]], node_key[p["b"]]))
        src = m.nodes[loose[a]["node"]]["source"]
        e = mk_edge("connects", loose[a]["node"], loose[b]["node"], src, layer="offpage_pair",
                    attributes=[claim("how_found", p["method"], src),
                                claim("chosen_by", p["evidence"]["chosen_by"], src)])
        e["direction"] = "unknown"
        m.edge(e)
        by_pair[a] = by_pair[b] = p
    for key in sorted(loose):
        op = loose[key]
        if key in by_pair:
            continue
        status, named = result["status"][op["node"]], [s.split("/", 1)[1] for s in result["names"][op["node"]]]
        cands = result["candidates"].get(op["node"]) or []
        ref, _ = printed_ref(op)
        if status.startswith("unpaired: tied"):
            kind, why = "off-page pairing unclear", (
                f"{label(op)} has equally likely partners ({', '.join(cands[:4])}{', ...' if len(cands) > 4 else ''})"
                "; a person says which pairs with which")
        elif cands:
            kind, why = "off-page pairing unclear", (
                f"{label(op)} points to {', '.join(cands[:4])}{', ...' if len(cands) > 4 else ''}, which paired "
                "elsewhere or wait on a tie; a person says where it continues")
        elif len(named) > 1:
            kind, why = "off-page pairing unclear", (
                f"{label(op)} names more than one registered sheet ({', '.join(named)}); a person says which it "
                "continues on")
        elif named:
            kind, why = "off-page connector unpaired", (
                f"{label(op)} names P&ID {'-'.join(ref) if ref else named[0]}, registered as sheet {named[0]}, but no "
                f"connector there points back to sheet {op['sheet']}")
        elif ref is None:
            kind, why = "off-page connector unpaired", f"{label(op)}: no sheet reference was read from it; a person " \
                                                       "supplies the sheet it continues on"
        else:
            kind, why = "off-page connector unpaired", (
                f"{label(op)} names P&ID {'-'.join(ref)}, which is not in the sheet index; it pairs once that sheet "
                "is registered and read")
        m.review.append({"item": op["node"], "kind": kind, "owner": op["owner"], "why": why})


# ---------------------------------------------------------------- loops: the loop list leads, drawings locate

def loop_candidates(members, signals):
    """Loop-number groups and drawn signal pairings inside ONE unit scope (callers never pass two units).
    members: {node_id: tag}; signals: set of frozenset pairs -> ({controller: {"in": set, "out": set, how}}, report).
    These are candidates for comparison with a loop list, never asserted loops."""
    groups = defaultdict(list)
    roles = {}
    for nid, tag in sorted(members.items()):
        lk = loop_key(tag)
        roles[nid] = role_of(lk[0]) if lk else None
        if lk and roles[nid]:
            groups[lk[1]].append(nid)
    cands, report = {}, []
    for number, ids in sorted(groups.items()):
        ctl = [i for i in ids if roles[i] == "controller"]
        note = ("more than one controller shares this loop number; not paired" if len(ctl) > 1 else
                "no controller with this loop number; not paired" if not ctl else "")
        report.append({"loop": number, "members": [members[i] for i in ids], "note": note})
        if len(ctl) == 1:
            c = cands.setdefault(ctl[0], {"in": {}, "out": {}})
            for i in ids:
                if roles[i] == "measurement":
                    c["in"].setdefault(i, set()).add("loop_number")
                elif roles[i] == "final":
                    c["out"].setdefault(i, set()).add("loop_number")
    for pair in sorted(signals, key=sorted):
        a, b = sorted(pair)
        for x, y in ((a, b), (b, a)):
            if roles.get(x) == "measurement" and roles.get(y) == "controller":
                cands.setdefault(y, {"in": {}, "out": {}})["in"].setdefault(x, set()).add("signal_line")
            if roles.get(x) == "controller" and roles.get(y) == "final":
                cands.setdefault(x, {"in": {}, "out": {}})["out"].setdefault(y, set()).add("signal_line")
    return dict(sorted(cands.items())), report


def loops(m, lists):
    """Each listed loop becomes edges sourced to the loop list (its status), then is located on the drawings:
    located and consistent / partly located / not found. Drawing-only loop candidates are flagged, not asserted."""
    cfg = m.cfg
    owner = cfg["owners"].get("loop_list") or "needs owner"
    pid_owner = cfg["owners"].get("pid") or "needs owner"
    signals = defaultdict(set)
    for e in m.edges.values():
        if e["type"] == "signal_line":
            signals[m.nodes[e["from"]]["scope"]].add(frozenset((e["from"], e["to"])))
    listed_ctl = defaultdict(set)
    results = []
    in_scope = defaultdict(dict)  # one pass over the map: O(items), however many loop lists
    for n in m.nodes.values():
        if n.get("scope") and n.get("tag") and n["kind"] != "offpage_connector":
            in_scope[n["scope"]][norm(n["tag"])] = n["id"]
    for spec in cfg["raw"].get("loop_lists") or []:
        path = inside(cfg["root"], spec.get("path"), "loop_lists[].path")
        scope = spec.get("scope")
        if scope not in m.nodes or m.nodes[scope]["kind"] != "unit":
            raise InputError(f"loop list {spec.get('id')}: scope {scope!r} is not a unit in the site file")
        try:
            rows, _ = loop_audit.read_loops(path)
        except loop_audit.InputError as exc:
            raise InputError(str(exc)) from None
        # optional status column: the loop list's own status for each loop (read_loops validates the rest)
        status_col = {norm(r.get("controller")): r.get("status", "") for r in read_csv(path, "loop list", ())}
        lid = part(spec.get("id"), "loop list id")
        m.record_of[lid] = "loop_list"
        raw = path.read_bytes()
        by_norm = in_scope[scope]
        ctl_norms = {norm(r["controller"]) for r in rows}
        drawn_cands, _ = loop_candidates({k: m.nodes[k]["tag"] for k in by_norm.values()
                                          if m.nodes[k]["kind"] in ("instrument", "controller", "final_element")
                                          and m.nodes[k].get("appearances")}, signals[scope])
        for lp in rows:
            src = {"kind": "document", "document": lid, "revision": spec.get("revision"), "sha256": sha_bytes(raw),
                   "locator": f"{spec.get('path')} line {lp['line']}"}
            st = status_col.get(norm(lp["controller"]))
            st = st if st in gx.STATUSES else "unverified"
            ids = {k: by_norm.get(norm(lp[k])) for k in ("controller", "measurement", "output")}
            located = {k: bool(v and m.nodes[v].get("appearances")) for k, v in ids.items()}
            if ids["controller"]:
                listed_ctl[scope].add(ids["controller"])
            sig = signals[scope]
            sig_in = bool(ids["controller"] and ids["measurement"] and (
                ids["measurement"] == ids["controller"] or frozenset((ids["measurement"], ids["controller"])) in sig))
            sig_out = bool(ids["controller"] and ids["output"] and
                           frozenset((ids["controller"], ids["output"])) in sig)
            edges = []
            if ids["controller"] and ids["measurement"] and ids["measurement"] != ids["controller"]:
                edges.append(("controls", ids["measurement"], ids["controller"], sig_in))
            if ids["controller"] and ids["output"]:
                t = "sets_point_of" if norm(lp["output"]) in ctl_norms else "controls"
                edges.append((t, ids["controller"], ids["output"], sig_out))
            for t, a, b, drawn in edges:
                e = mk_edge(t, a, b, src, status=st, how_found=["loop_list"] + (["drawing:signal_line"] if drawn else []),
                            attributes=[claim("loop_list", lid, src, st),
                                        claim("signal_drawn", drawn, src if not drawn else
                                              m.nodes[a]["appearances"][0] if m.nodes[a]["appearances"] else src)])
                m.edge(e)
            n_located = sum(located.values())
            outcome = ("located and consistent" if n_located == 3 and sig_in and sig_out else
                       "not found on any sheet" if n_located == 0 else "partly located")
            missing = [f"{lp[k]} ({k}) " + ("not in the lists or drawings of this unit" if not ids[k]
                                             else "not on any registered sheet") for k in ("controller", "measurement",
                                                                                          "output") if not located[k]]
            if n_located and not sig_in:
                missing.append(f"no drawn signal line {lp['measurement']} -> {lp['controller']}")
            if n_located and not sig_out:
                missing.append(f"no drawn signal line {lp['controller']} -> {lp['output']}")
            sheets = sorted({a["sheet"] for v in ids.values() if v for a in m.nodes[v].get("appearances", [])})
            zones = sorted({f"{a['sheet']}:{a['zone']}" for v in ids.values() if v
                            for a in m.nodes[v].get("appearances", []) if a.get("zone")})
            # a tag nobody holds is the loop list's to explain; a held tag missing from the drawings is doc control's
            route = owner if any(not ids[k] for k in ids) else pid_owner
            res = {"scope": scope, "loop_list": lid, "line": lp["line"], "controller": lp["controller"],
                   "measurement": lp["measurement"], "output": lp["output"], "outcome": outcome,
                   "sheets": sheets, "zones": zones, "missing": missing, "route": route,
                   "item": ids["controller"] or qid(scope, lp["controller"])}
            results.append(res)
            # drawing pairs the controller differently from the list
            if ids["controller"]:
                c = drawn_cands.get(ids["controller"], {"in": {}, "out": {}})
                for role, got in (("measurement", c["in"]), ("output", c["out"])):
                    for other, how in sorted(got.items()):
                        if norm(m.nodes[other]["tag"]) != norm(lp[role]) and "signal_line" in how:
                            m.conflict("loop_pairing", ids["controller"], role, m.nodes[other]["appearances"][0],
                                       m.nodes[other]["tag"], src, lp[role], record="loop_list",
                                       what=f"a drawn signal line pairs {m.nodes[other]['tag']} with {lp['controller']}; "
                                            f"the loop list says {lp[role]}", parties=(pid_owner,))
    # drawing-only loop candidates (secondary): flagged to the loop list owner, never asserted
    by_scope = defaultdict(dict)
    for n in m.nodes.values():
        if n.get("scope") and n["kind"] in ("instrument", "controller", "final_element") and n.get("appearances"):
            by_scope[n["scope"]][n["id"]] = n["tag"]
    groups = {}
    lists_by_scope = {spec.get("scope"): spec.get("id") for spec in cfg["raw"].get("loop_lists") or []}
    for scope in sorted(by_scope):
        cands, report = loop_candidates(by_scope[scope], signals[scope])
        groups[scope] = report
        for ctl, c in cands.items():
            if ctl in listed_ctl[scope] or not (c["in"] or c["out"]):
                continue
            how = sorted(set().union(*c["in"].values(), *c["out"].values()))
            members = sorted(m.nodes[x]["tag"] for x in list(c["in"]) + list(c["out"]))
            ll = lists_by_scope.get(scope)
            if not ll:  # path B: no loop list for this unit yet; the candidate goes into the draft loop list
                m.review.append({"item": ctl, "kind": "drawn loop, no loop list yet", "owner": owner,
                                 "why": f"possible loop {m.nodes[ctl]['tag']} with {', '.join(members)} "
                                        f"({' + '.join(how)}); no loop list covers {scope} yet: review the draft "
                                        "loop list from `one_map.py draft-lists`"})
                continue
            m.conflict("unlisted_loop", ctl, "loop", m.nodes[ctl]["appearances"][0],
                       f"{m.nodes[ctl]['tag']} with {', '.join(members)} ({' + '.join(how)})",
                       {"kind": "document", "document": ll or "no loop list for " + scope},
                       "not listed" if ll else "no loop list supplied for this unit", record="loop_list",
                       what=f"the drawings show a possible loop around {m.nodes[ctl]['tag']} ({' + '.join(how)}) "
                            "that the loop list does not hold; not asserted", parties=(pid_owner,))
    m.loops = results
    return groups


# ---------------------------------------------------------------- documents: covers, mentions, based_on

def tag_index(m):
    exact, by_norm = defaultdict(set), defaultdict(set)
    for n in m.nodes.values():
        if not n.get("scope") or not n.get("tag") or n["kind"] in ("document", "conflict", "offpage_connector"):
            continue
        for t, how in [(n["tag"], "tag")] + [(a, "alias (former tag)") for a in n["aliases"]]:
            exact[t].add((n["id"], how))
            by_norm[norm(t)].add(n["id"])
    by_base = defaultdict(set)
    for key, ids in by_norm.items():
        base = re.sub(r"(?<=\d)[A-Z]{1,2}$", "", key)
        if base != key:
            by_base[base] |= ids
    return exact, by_norm, by_base


def match_mentions(text, exact, by_norm, by_base, covers, nodes):
    """Every tag-like token in text -> (asserted mentions, not-asserted findings). Deterministic; O(tokens).

    An exact tag (or former tag) links as before. A token that equals exactly one map tag or former tag once
    separators, spaces and case are ignored (P101, p-101, PSV 204, TT2205) links with matched="format-insensitive".
    Anything else that resembles a map tag (the same normalized tag in more than one scope, a suffix the map does not
    have, lower-case letters followed by a space) is a finding marked `confirm`, never a link."""
    asserted, findings = [], []

    def covered(ids):
        return [i for i in ids if any(i == c or i.startswith(c + "/") for c in covers)]

    def near_covers(i):  # inside the site/plant/unit of a covers scope (an equipment cover counts as its unit)
        return any(i == p or i.startswith(p + "/") for p in ("/".join(c.split("/")[:3]) for c in covers))

    def loose(where, token, sep):
        key = norm(token)
        base = re.sub(r"(?<=\d)[A-Z]{1,2}$", "", key)
        lower = token != token.upper()
        ids = sorted(by_norm.get(key, ()))
        if len(ids) == 1 and covers and not near_covers(ids[0]):
            findings.append(dict(where, kind="same tag in another format, outside the units the document covers",
                                 candidates=ids, confirm=True))
        elif len(ids) == 1 and not (lower and sep == " "):
            n = nodes.get(ids[0]) or {}
            via = "; via alias (former tag)" if n.get("tag") and norm(n["tag"]) != key else ""
            asserted.append(dict(where, node=ids[0], confidence="format-insensitive, unique on the map" + via,
                                 matched="format-insensitive"))
        elif ids:
            kind = ("same tag in another format, in more than one scope" if len(ids) > 1 else
                    "lower-case letters and a space; could be ordinary words")
            findings.append(dict(where, kind=kind, candidates=ids, covered=covered(ids), confirm=True))
        elif key in by_base:
            findings.append(dict(where, kind="near miss (the map has only suffixed tags)",
                                 candidates=sorted(by_base[key]), confirm=True))
        elif base != key and base in by_norm:
            findings.append(dict(where, kind="near miss (suffix not on the map)", candidates=sorted(by_norm[base]),
                                 confirm=True))
        elif not lower:
            findings.append(dict(where, kind="tag-like text not on the map", candidates=[]))

    for ln, line in enumerate(text.splitlines(), 1):
        spans = []
        for mt in TAG_TEXT.finditer(line):
            spans.append(mt.span())
            prefix, letters, sep, digits, suffix = mt.groups()
            token = f"{letters}{sep}{digits}{suffix}"
            where = {"line": ln, "column": mt.start() + 1, "matched_text": mt.group(0)}
            if prefix:
                target = prefix + token
                if target in nodes:
                    asserted.append(dict(where, node=target, confidence="site-qualified exact"))
                else:
                    findings.append(dict(where, kind="qualified tag not on the map", candidates=[]))
                continue
            hits = sorted(exact.get(token, ()))
            if hits:
                ids = sorted({h[0] for h in hits})
                how = {h[0]: h[1] for h in hits}
                if len(ids) > 1:
                    inside_cover = covered(ids)
                    if len(inside_cover) != 1:
                        findings.append(dict(where, kind="ambiguous", candidates=ids))
                        continue
                    ids, conf = inside_cover, "exact in covered scope"
                else:
                    conf = "exact, unique on the map"
                if how[ids[0]] != "tag":
                    conf += f"; via {how[ids[0]]}"
                asserted.append(dict(where, node=ids[0], confidence=conf))
                continue
            loose(where, token, sep)
        for mt in TAG_TEXT_ANY_CASE.finditer(line):
            letters, sep, digits, suffix = mt.groups()
            token = f"{letters}{sep}{digits}{suffix}"
            if token == token.upper() or any(s < mt.end() and mt.start() < e for s, e in spans):
                continue  # upper-case tokens were handled above
            loose({"line": ln, "column": mt.start() + 1, "matched_text": mt.group(0)}, token, sep)
    asserted.sort(key=lambda x: (x["line"], x["column"]))
    findings.sort(key=lambda x: (x["line"], x["column"]))
    return asserted, findings


def ocr_of(res, locator):
    """Why a piece of a document's text came from OCR ('' when it did not).

    extract_text records OCR per piece: `result.ocr` maps each OCR'd piece's locator ("page 2", or "embedded
    'spec.pdf' (in table 3) page 2") to its mean word confidence, and `result.ocr_engine` is set whenever any piece
    came from OCR. A PDF with some scanned pages keeps engine 'pypdf' and status 'partial' or 'ok (ocr)', so the
    locator decides: in `result.ocr` (or beginning with a locator in it) -> OCR; not in it -> a text layer. With `ocr_engine` set and an empty `ocr`
    map (nothing to compare the locator against) the whole file counts as OCR. Without `ocr_engine` the older
    signals still apply: engine starting 'tesseract', status 'ok (ocr)', or an `ocr_pages` list of page numbers or
    locators. A result with none of these is not OCR."""
    engine = str(getattr(res, "engine", "") or "")
    status = str(getattr(res, "status", "") or "")
    per_piece = getattr(res, "ocr", None)
    per_piece = per_piece if isinstance(per_piece, dict) else {}
    ocr_engine = str(getattr(res, "ocr_engine", "") or "")
    loc = str(locator or "")
    # the segment's locator is an OCR'd piece's locator, or (a finer piece of it) begins with one ("page 2, ...")
    key = loc if loc in per_piece else next((k for k in sorted(per_piece, key=len, reverse=True)
                                             if loc.startswith(f"{k},") or loc.startswith(f"{k} ")), None)
    if key is not None:
        conf = per_piece[key]
        return (ocr_engine or "OCR") + (f", mean word confidence {conf}" if conf is not None else "")
    if ocr_engine:
        return "" if per_piece else f"{ocr_engine}; which pieces is not recorded, so the whole file counts as OCR"
    if engine.lower().startswith("tesseract") or status.lower() == "ok (ocr)":
        return engine if engine.lower().startswith("tesseract") else status
    pages = getattr(res, "ocr_pages", None) or ()
    if pages:
        m_ = re.match(r"page (\d+)", locator or "")
        wanted = {str(p) for p in pages}
        if (locator in wanted) or (m_ and (m_.group(1) in wanted or f"page {m_.group(1)}" in wanted)):
            return f"OCR page ({engine or 'ocr'})"
    return ""


def segment_locator(locator, text, line, column):
    """'page 3, line 4, column 2'; a one-line piece (a text-file line, a cell, a paragraph) needs no inner line."""
    return f"{locator}, column {column}" if "\n" not in text else f"{locator}, line {line}, column {column}"


def document_text_note(m, doc_node, d, res):
    """A document whose text was not (fully) read is a low-priority note to its owner, never a crash."""
    if res.status == extract_text.OK and len(res.segments):
        return
    if res.status == extract_text.OK:
        why = f"no text found in {d['path']}"
    else:
        why = f"{d['path']}: text {res.status}"
    if res.warnings:
        why += " (" + "; ".join(res.warnings) + ")"
    why += ("; nothing in it is on the map" if res.status == extract_text.OK or not len(res.segments) else
            "; mentions in what was not read are not on the map")
    m.review.append({"item": doc_node, "kind": DOC_TEXT_NOTE, "owner": d["owner"], "why": why})


def documents(m, cfg, lists):
    spec = cfg["raw"].get("documents")
    if not spec:
        return {}
    path = inside(cfg["root"], spec, "documents")
    try:
        sources, _, _ = cr.load_sources(path, {})
    except cr.InputError as exc:
        raise InputError(str(exc)) from None
    manifest = read_json(path, "document manifest")
    sid = cfg["site"]
    docs = {}
    revisions = {n["document"]["id"]: n["document"]["revision"] for n in m.nodes.values() if n["kind"] == "document"}
    for d in manifest["documents"]:
        did = d["id"]
        if did in revisions:
            raise InputError(f"document {did}: id already used by a drawing in the register")
        if d.get("status") not in DOC_STATUSES:
            raise InputError(f"document {did}: status must be draft or released")
        if not d.get("owner"):
            raise InputError(f"document {did}: owner is required")
        revisions[did] = d["revision"]
        docs[did] = d
    exact, by_norm, by_base = tag_index(m)
    term_pat, by_phrase = onto_mod.term_matcher(m.glossary)
    items_by_class = defaultdict(list)
    for n in m.nodes.values():
        if n.get("class") and n.get("scope") and n["kind"] not in ("document", "conflict"):
            items_by_class[n["class"]].append(n["id"])
    for did in sorted(docs):
        d, s = docs[did], sources[did]
        doc_node = qid(sid, "DOC", did)
        local = (path.parent / d["path"]).resolve()
        dsrc = {"kind": "document", "document": doc_node, "revision": s["revision"], "sha256": s["sha256"],
                "path": d["path"]}
        doc_cls = cfg["onto"].doc_class(d.get("doc_type"))
        m.node(mk_node(doc_node, "document", did, d.get("title"), dsrc, status="confirmed",
                       **({"class": doc_cls} if doc_cls else {}), document={"id": did, "revision": s["revision"], "status": d["status"], "owner": d["owner"],
                                 "department": d.get("department") or d["owner"], "doc_type": d.get("doc_type"),
                                 "sha256": s["sha256"], "path": d["path"]}))
        covers = []
        for c in d.get("covers") or []:
            if c not in m.nodes:
                raise InputError(f"document {did}: covers {c!r}, which is not a node on the map (use an exact "
                                 "site-qualified id; tags are never guessed)")
            covers.append(c)
            m.edge(mk_edge("covers", doc_node, c, dsrc, status="confirmed"))
        for b in d.get("based_on") or []:
            target = b.get("id")
            if target not in revisions:
                raise InputError(f"document {did}: based_on {target!r} is not a document in the register/manifest")
            tnode = qid(sid, "DOC", target)
            m.edge(mk_edge("based_on", doc_node, tnode, dsrc, status="confirmed",
                           attributes=[claim("revision", b.get("revision"), dsrc, status="confirmed")]))
            if b.get("revision") != revisions[target]:
                m.conflict("superseded_basis", doc_node, f"based_on {target}", dsrc, f"rev {b.get('revision')}",
                           m.nodes[tnode]["source"], f"current rev {revisions[target]}", record="document",
                           what=f"{did} rev {s['revision']} is based on {target} rev {b.get('revision')}; the "
                                f"current revision is {revisions[target]}",
                           document_owner=d["owner"], parties=(m.nodes[tnode]["document"]["owner"],))
        try:
            res = extract_text.extract(local, **cfg["document_text"])
        except ValueError as exc:
            raise InputError(f"document_text: {exc}") from None
        m.nodes[doc_node]["document"]["text"] = {"status": res.status, "format": res.format,
                                                  "segments": len(res.segments),
                                                  "extractor": f"{extract_text.EXTRACTOR} {extract_text.VERSION}"}
        document_text_note(m, doc_node, d, res)
        asserted, findings = [], []
        term_rows = {}  # (term, why) -> [locators]: one review row per document and term, never one per hit
        ocr_rows = {}  # matched text -> [(locator, what the map has)]: OCR text never links (ocr_of)
        for locator, text in res.segments:
            got, missed = match_mentions(text, exact, by_norm, by_base, covers, m.nodes)
            for x in got + missed:
                x["locator"] = segment_locator(locator, text, x["line"], x["column"])
            hits = onto_mod.find_terms(text, term_pat, by_phrase)
            ocr = ocr_of(res, locator)
            if ocr:
                for x in got + missed + hits:
                    loc = x.get("locator") or segment_locator(locator, text, x["line"], x["column"])
                    has = ([x["node"]] if x.get("node") else x.get("candidates") or
                           ([f"glossary term '{x['terms'][0]['term']}'"] if x.get("terms") else []))
                    ocr_rows.setdefault(x["matched_text"], []).append((loc, has, ocr))
                continue
            asserted += got
            findings += missed
            for hit in hits:
                hit["locator"] = segment_locator(locator, text, hit["line"], hit["column"])
                target, term, why = onto_mod.resolve_term_hit(hit, covers, items_by_class, cfg["onto"])
                if target:
                    asserted.append({"line": hit["line"], "column": hit["column"], "locator": hit["locator"],
                                     "matched_text": hit["matched_text"], "node": target, "matched": "glossary",
                                     "term": term["term"],
                                     "confidence": f"glossary term '{term['term']}' "
                                                   f"({onto_mod.cert_text(term['certification'])}), one item in "
                                                   "the covered scope"})
                elif why:
                    term_rows.setdefault((term["term"] if term else hit["matched_text"], why), []).append(hit)
        for text_, places in sorted(ocr_rows.items()):
            has = sorted({h for _, hs, _ in places for h in hs})
            m.review.append({"item": doc_node, "kind": OCR_CONFIRM, "owner": d["owner"],
                             "why": f"'{text_}' at {places[0][0]}" + (f" and {len(places) - 1} more place(s)"
                                                                     if len(places) > 1 else "")
                                    + f" in {did} was read by OCR ({places[0][2]}); OCR can turn one tag into "
                                      "another (FDV-0756 read as EDV-0756), so nothing read by OCR links"
                                    + (f" (the map has {', '.join(has)})" if has else "") + "; not asserted"})
        for (tname, why), hits in sorted(term_rows.items()):
            owner = next((t["owner"] for t in m.glossary if t["term"] == tname and t["owner"]), None) or d["owner"]
            m.review.append({"item": doc_node, "kind": CONFIRM, "owner": owner,
                             "why": f"{why}: '{hits[0]['matched_text']}' at {hits[0]['locator']}"
                                    + (f" and {len(hits) - 1} more place(s)" if len(hits) > 1 else "")
                                    + f" in {did}; not asserted"})
        # one edge per (document, item); its locator is the first exact mention, else the first mention
        first = {}
        for a in asserted:
            if a["node"] not in first or ("matched" in first[a["node"]] and "matched" not in a):
                first[a["node"]] = a
        for a in sorted(asserted, key=lambda x: x is not first[x["node"]]):
            lsrc = dict(dsrc, locator=a["locator"])
            eid = f"mentions:{doc_node}->{a['node']}"
            if eid in m.edges:
                m.edges[eid].setdefault("more_locators", []).append(lsrc["locator"])
            else:
                attrs = [claim("file", d["path"], lsrc), claim("locator", lsrc["locator"], lsrc),
                         claim("matched_text", a["matched_text"], lsrc), claim("confidence", a["confidence"], lsrc)]
                if "matched" in a:
                    attrs.append(claim("matched", a["matched"], lsrc))
                if "term" in a:
                    attrs.append(claim("glossary_term", a["term"], lsrc))
                m.edge(mk_edge("mentions", doc_node, a["node"], lsrc, attributes=attrs))
            tgt = m.nodes[a["node"]]
            rec = list_for(tgt["kind"])
            if "listed_in" in tgt and not tgt["listed_in"] and covering(lists, rec, tgt["scope"]):
                m.conflict("mention_not_in_register", a["node"], "listed", lsrc,
                           f"{did} mentions {a['matched_text']}", {"kind": "document", "document": rec},
                           "no row for this tag", record=rec, parties=(d["owner"],),
                           what=f"{did} mentions {a['matched_text']} ({lsrc['locator']}); the "
                                f"{rec.replace('_', ' ')} has no row for it")
        for f in findings:
            lsrc = dict(dsrc, locator=f["locator"])
            if f["kind"] == "ambiguous":
                m.conflict("ambiguous_reference", doc_node, f"mention {f['matched_text']}", lsrc,
                           f["matched_text"], {"kind": "map", "document": "one map"},
                           "exists as " + ", ".join(f["candidates"]), record="document",
                           what=f"{did} names {f['matched_text']} ({lsrc['locator']}); the map has it in more than "
                                "one scope and the document's covers do not choose; not asserted",
                           document_owner=d["owner"])
            else:
                hint = (f"; the document's covers point to {f['covered'][0]}"
                        if len(f.get("covered") or ()) == 1 else "")
                m.review.append({"item": doc_node, "kind": CONFIRM if f.get("confirm") else "mention",
                                 "owner": d["owner"],
                                 "why": f"{f['kind']}: '{f['matched_text']}' at {lsrc['locator']}"
                                        + (f" (map has {', '.join(f['candidates'])})" if f["candidates"] else "")
                                        + hint + "; not asserted"})
    return {did: {"revision": sources[did]["revision"], "sha256": sources[did]["sha256"]} for did in docs}


# ---------------------------------------------------------------- ontology: classes, records, links, expectations

ITEM_KINDS = ("equipment", "instrument", "controller", "final_element", "manual_valve", "relief_device", "line")
# The field that names the item a row is about, where it is not `tag` (registers.json tag_ref fields).
TAG_FIELD = {"ccp": "monitored_tag", "isolation_point": "isolates_tag", "interlock_list": "cause_tag"}
_REGISTERS = None


def registers():
    global _REGISTERS
    if _REGISTERS is None:
        doc = json.loads((onto_mod.DIR / "registers.json").read_text(encoding="utf-8"))
        _REGISTERS = {r["id"]: r for r in doc["registers"]}
    return _REGISTERS


def classify(m):
    """A class for every item where it is deterministic (classes.json): a record's `class` column, else the tag
    letters (or the site's equipment prefixes), refined by a datasheet value. Two records naming different classes,
    or an unknown class, is a review row for the record's owner; nothing is guessed."""
    onto = m.cfg["onto"]
    for nid in sorted(m.nodes):
        n = m.nodes[nid]
        if n["kind"] not in ITEM_KINDS or not n.get("tag"):
            continue
        named = m.explicit_class.get(nid, [])
        explicit = named[0][0] if named else None
        if len({c for c, _ in named}) > 1:
            m.review.append({"item": nid, "kind": "class disagreement", "owner": n.get("owner") or "needs owner",
                             "why": f"{n['tag']}: records name different classes "
                                    f"({', '.join(f'{c} in {lid}' for c, lid in named)}); the first is used"})
        attrs = {a["name"]: a["value"] for a in n["attributes"]}
        cid, how = onto.infer(n["tag"], n["kind"], attrs, explicit=explicit)
        if explicit and cid is None:
            m.review.append({"item": nid, "kind": "class not recognized", "owner": n.get("owner") or "needs owner",
                             "why": f"{n['tag']}: {how} ({named[0][1]}); add it to classes.json or fix the record"})
            cid, how = onto.infer(n["tag"], n["kind"], attrs)
        if cid:
            n["class"], n["class_how"] = cid, how


def resolver(m):
    """resolve(tag or qualified id, scope) -> a node id: the id itself, SCOPE/TAG, or the one item with that tag
    inside the scope (a plant-level row). None when it is absent or not unique."""
    by_tag = defaultdict(list)
    for n in m.nodes.values():
        if n.get("tag") and n.get("scope") and n["kind"] not in ("document", "conflict", "offpage_connector"):
            by_tag[n["tag"]].append(n["id"])

    def resolve(text, scope):
        if not text:
            return None
        if "/" in text:
            return text if text in m.nodes else None
        if qid(scope, text) in m.nodes:
            return qid(scope, text)
        hits = [x for x in by_tag.get(text, ()) if x.startswith(scope + "/")]
        return hits[0] if len(hits) == 1 else None
    return resolve


def load_records(m):
    """The site file's `records`: any register of schemas/context-map/registers.json (HACCP plan CCPs, calibration
    records, relief device register, criticality ranking, PM plan, glossary, ...) as CSV in its template's columns.
    Rows resolve to items by their tag field; they carry their source and row locator. They feed expectations, the
    glossary and answers; they never create items."""
    cfg, regs = m.cfg, registers()
    resolve = resolver(m)
    for spec in cfg["raw"].get("records") or []:
        reg_id = spec.get("register")
        if reg_id not in regs:
            raise InputError(f"records {spec.get('id')}: register {reg_id!r} is not in registers.json")
        reg = regs[reg_id]
        lid = part(spec.get("id"), "records.id")
        path = inside(cfg["root"], spec.get("path"), f"records {lid} path")
        required = [f["name"] for f in reg["fields"] if f["required"] is True]
        rows = read_csv(path, f"{reg['name']} {lid}", required)
        scopes = spec.get("scopes") or [cfg["site"]]
        for sc in scopes:
            if sc != cfg["site"] and not sc.startswith(cfg["site"] + "/"):
                raise InputError(f"records {lid}: scope {sc!r} is not in site {cfg['site']}")
        m.record_of[lid] = reg_id
        owner = spec.get("owner") or cfg["owners"].get(reg_id) or reg["default_owner"]
        base = {"kind": "document", "document": lid, "revision": spec.get("revision"),
                "sha256": sha_bytes(path.read_bytes()), "path": spec.get("path")}
        tag_field = TAG_FIELD.get(reg_id) or ("tag" if any(f["name"] == "tag" for f in reg["fields"]) else None)
        tag_required = tag_field == "tag" and next(f for f in reg["fields"] if f["name"] == "tag")["type"] == "tag"
        key = next((k for k in reg["key"] if k not in ("plant", "unit", "tag")), None)
        out = m.records.setdefault(reg_id, [])
        for n, r in enumerate(rows, 2):
            plant = part(r.get("plant"), f"{lid} row {n} plant") if "plant" in r else None
            if plant is not None:
                if plant not in cfg["plants"] and plant not in cfg["scopes"]:
                    raise InputError(f"{lid} row {n}: plant/scope {plant!r} is not in the site file")
                if r.get("unit") and (plant not in cfg["plants"] or r["unit"] not in cfg["plants"][plant]["units"]):
                    raise InputError(f"{lid} row {n}: unit {plant}/{r['unit']} is not in the site file")
                scope = qid(cfg["site"], plant, r["unit"]) if r.get("unit") else qid(cfg["site"], plant)
            else:
                scope = cfg["site"]
            if not any(onto_mod.within(scope, s) or onto_mod.within(s, scope) for s in scopes):
                raise InputError(f"{lid} row {n}: {scope} is outside the record's declared scopes ({', '.join(scopes)})")
            tag = r.get(tag_field) if tag_field else None
            item = resolve(tag, scope) if tag else None
            row = {"register": reg_id, "id": r.get(key) if key else None, "item": item, "scope": scope,
                   "values": {k: v for k, v in r.items() if v},
                   "source": dict(base, locator=f"row {n}" + (f"; {r['locator']}" if r.get("locator") else "")),
                   "status": r.get("status") or "unverified"}
            out.append(row)
            if reg_id == "ccp" and item and not m.nodes[item].get("safety"):
                # a CCP's monitoring instrument is food-safety relevant: the review queue's safety floor holds it
                m.nodes[item]["safety"] = f"CCP monitoring instrument ({r.get('ccp_id')})"
            if tag and item is None and tag_required:
                m.review.append({"item": qid(scope, tag), "kind": "record row, item not on the map", "owner": owner,
                                 "why": f"{reg['name']} {lid} row {n} is about {tag}, which no equipment or "
                                        f"instrument record and no P&ID of {scope} holds"})
        m.sources.append({"id": lid, "register": reg_id, "scopes": list(scopes), "owner": owner})
    if "glossary" in m.records:
        m.glossary = onto_mod.load_glossary(m.records["glossary"], cfg["onto"], resolve)
        for t in m.glossary:
            if t["problem"]:
                m.review.append({"item": t["scope"], "kind": "glossary term problem", "owner": t["owner"] or
                                 cfg["owners"].get("glossary") or "Doc control",
                                 "why": f"glossary term '{t['term']}': {t['problem']}; it links nothing until fixed"})


LIKE_FOR_LIKE = "replacement may not be like-for-like"
WO_NOTE = "work order closeout note"
INSTALLED_FIELDS = ("manufacturer", "model", "serial_number", "size")  # work_order installed_<name> columns


def same_value(a, b):
    """Installed values are compared ignoring case and repeated spaces ('DN 65' and 'dn 65' agree; 'DN65' does not)."""
    return " ".join(str(a).split()).casefold() == " ".join(str(b).split()).casefold()


def work_order_closeout(m, lists):
    """Closed work orders that record what was installed (`installed_manufacturer`, `installed_model`,
    `installed_serial_number`, `installed_size` in the work_order register), compared with the records. An installed
    value that differs from the item's maintenance equipment export or instrument index row is a value_disagreement
    for that record's owner (the work order is the newer word from the field). One that differs from a datasheet
    value is a "replacement may not be like-for-like" review row for the datasheet's owner: a possible management
    of change trigger, never decided here. Manufacturer, model or serial number that no maintenance equipment export
    or instrument index row holds is a closeout note (the record should hold what is installed). A work order with
    no closed_on, or with no installed_ values, is not a closeout and is not compared. A work order history holds
    every earlier replacement too, so for each item and value only the latest closeout (by closed_on, then work
    order number) is compared; an earlier one that a later one superseded raises nothing."""
    owners = {s["id"]: s.get("owner") for s in m.sources}
    for rec in ("maintenance_export", "instrument_index", "datasheet"):
        owners.update({x["id"]: x["owner"] for x in lists.get(rec, [])})
    latest = {}  # (item or tag, value name) -> (closed_on, work order) of the newest closeout that records it
    for row in m.records.get("work_order") or []:
        v = row["values"]
        if v.get("closed_on"):
            for k in INSTALLED_FIELDS:
                if v.get(f"installed_{k}"):
                    key = (row["item"] or qid(row["scope"], v.get("tag", "")), k)
                    latest[key] = max(latest.get(key, ("", "")), (v["closed_on"], v.get("work_order") or ""))
    for row in m.records.get("work_order") or []:
        v = row["values"]
        here = row["item"] or qid(row["scope"], v.get("tag", ""))
        installed = {k: v[f"installed_{k}"] for k in INSTALLED_FIELDS if v.get(f"installed_{k}")
                     and latest.get((here, k)) == (v.get("closed_on"), v.get("work_order") or "")}
        if not installed or not v.get("closed_on"):
            continue
        wo, src = v.get("work_order"), row["source"]
        wo_owner = owners.get(src["document"]) or "needs owner"
        nid = row["item"]
        if nid is None:
            m.review.append({"item": qid(row["scope"], v.get("tag", "")), "kind": WO_NOTE, "owner": wo_owner,
                             "why": f"work order {wo} ({src['document']} {src['locator']}) records what was installed "
                                    f"on {v.get('tag')}, which no record or P&ID of {row['scope']} holds"})
            continue
        tag, held = m.nodes[nid]["tag"], m.held.get(nid, {})
        for name, value in installed.items():
            said = f"work order {wo} (closed {v['closed_on']}) records {name} {value} installed"
            in_records = False
            for lid in sorted(held):
                rec, have = m.record_of.get(lid), held[lid].get(name)
                if rec not in ("maintenance_export", "instrument_index", "datasheet") or have is None:
                    continue
                in_records = in_records or rec != "datasheet"
                if same_value(have["value"], value):
                    continue
                if rec == "datasheet":
                    m.review.append({"item": nid, "kind": LIKE_FOR_LIKE, "owner": owners.get(lid) or "needs owner",
                                     "why": f"{tag}: {said}; datasheet {lid} ({have['source'].get('locator')}) says "
                                            f"{have['value']}. A replacement that differs from its datasheet may need "
                                            "a management of change review; this is a flag, not a decision"})
                else:
                    m.conflict("value_disagreement", nid, name, src, value, have["source"], have["value"],
                               record=rec, parties=(wo_owner,),
                               what=f"{tag} {name}: {said}; the {RECORD_NAMES[rec]} {lid} "
                                    f"({have['source'].get('locator')}) says {have['value']}")
            if not in_records and name != "size":
                m.review.append({"item": nid, "kind": WO_NOTE, "owner": m.nodes[nid].get("owner") or wo_owner,
                                 "why": f"{tag}: {said}; no maintenance equipment export or instrument index row "
                                        f"for it holds {name}, so nothing was compared"})


def coverage_sources(m, register, lists):
    """Which record is the record for which scopes: P&ID sheets cover their unit; lists, datasheets, loop lists and
    `records` their declared scopes; a document manifest the whole site."""
    cfg = m.cfg
    out = [{"id": r["doc"], "register": "pid",
            "scopes": [qid(cfg["site"], r["plant"], r["unit"]) if r["unit"] else qid(cfg["site"], r["plant"])],
            "owner": r["owner"]}
           for r in register]
    for rec in ("maintenance_export", "instrument_index", "datasheet"):
        out += [{"id": x["id"], "register": rec, "scopes": list(x["scopes"]), "owner": x["owner"]}
                for x in lists.get(rec, [])]
    out += [{"id": s.get("id"), "register": "loop_list", "scopes": [s.get("scope")],
             "owner": cfg["owners"].get("loop_list") or "needs owner"}
            for s in cfg["raw"].get("loop_lists") or []]
    if cfg["raw"].get("documents"):
        out.append({"id": cfg["raw"]["documents"], "register": "documents", "scopes": [cfg["site"]]})
    return out + m.sources


def check_relations(m):
    """Every link against relations.json domain and range: a link that does not fit what it connects is a review row
    for the owner of the record that asserted it. It is kept on the map, never dropped."""
    onto = m.cfg["onto"]
    edges = [m.edges[k] for k in sorted(m.edges)]
    findings, counts = onto_mod.check_links(m.nodes, edges, onto)
    for f in findings:
        e = m.edges.get(f["edge"]) if f["edge"] else None
        src = (e or {}).get("source") or {}
        rec = m.record_type(src)
        doc = m.nodes.get(src.get("document") or "")
        owner = ((doc or {}).get("document") or {}).get("owner") if doc and rec == "unknown" else None
        owner = owner or m.cfg["owners"].get(rec) or "needs owner"
        t = lambda x: (m.nodes.get(x) or {}).get("tag") or x  # noqa: E731
        cls = lambda x: (m.nodes.get(x) or {}).get("class") or (m.nodes.get(x) or {}).get("kind")  # noqa: E731
        said = (f" ({e['type']} from {src.get('document') or src.get('kind')}"
                + (f" sheet {src['sheet']}" if src.get("sheet") else "") + ")") if e else ""
        m.review.append({"item": f["from"], "kind": onto_mod.LINK_ROW, "owner": owner,
                         "why": f"{t(f['from'])} ({cls(f['from'])}) {f['relation']} {t(f['to'])} ({cls(f['to'])})"
                                f"{said}: {f['why']}; the link is kept for a person to check"})
    m.link_counts = counts


class ExpectationView:
    """What the expectation rules read, built from the assembled map."""

    def __init__(self, m, sources):
        onto = m.cfg["onto"]
        self.as_of = m.cfg["as_of"]
        self.items = {nid: {"class": n.get("class"), "kind": n["kind"], "scope": n["scope"], "tag": n["tag"]}
                      for nid, n in m.nodes.items()
                      if n.get("scope") and n.get("tag") and n["kind"] not in ("document", "conflict",
                                                                               "offpage_connector")}
        self.records = m.records
        self.edges = [{"rel": onto.relation_for_edge(e["type"], (m.nodes.get(e["from"]) or {}).get("class")),
                       "from": e["from"], "to": e["to"]} for e in m.edges.values()]
        self.documents = {}
        for n in m.nodes.values():
            if n["kind"] == "document":
                self.documents[n["id"]] = {"class": n.get("class"), "covers": set(), "mentions": set()}
        for e in m.edges.values():
            if e["type"] in ("covers", "mentions") and e["from"] in self.documents:
                self.documents[e["from"]][e["type"]].add(e["to"])
        self.conflicts = list(m.conflicts.values())
        self.sources = sources
        self._resolve = resolver(m)
        by_norm = defaultdict(dict)
        for nid, it in self.items.items():
            by_norm[it["scope"]][norm(it["tag"])] = nid
        self.loops = []
        for lp in m.loops:
            ids = {k: by_norm[lp["scope"]].get(norm(lp[k])) if lp[k] else None
                   for k in ("controller", "measurement", "output")}
            self.loops.append(dict(lp, ids=ids, item=ids["controller"] or lp["item"]))

    def present(self, register, scope):
        return any(s["register"] == register and any(onto_mod.within(scope, x) for x in s["scopes"])
                   for s in self.sources)

    def resolve(self, text, scope):
        return self._resolve(text, scope)


def expectations(m, sources):
    """The site's expectation rules (its own copy of templates/expectations.json): results, review rows routed to
    each rule's owner, per-rule coverage."""
    cfg = m.cfg
    rel = cfg["raw"].get("expectations")
    if not rel:
        return
    path = inside(cfg["root"], rel, "expectations")
    try:
        doc = onto_mod.load_rules(read_json(path, "expectations"), cfg["onto"])
        results, rows, cov = onto_mod.evaluate(doc, ExpectationView(m, sources), cfg["onto"])
    except onto_mod.OntologyError as exc:
        raise InputError(f"{rel}: {exc}") from None
    for r in rows:
        m.review.append({k: r[k] for k in ("item", "kind", "owner", "why")})
    m.expectations = {"rules_source": rel, "rules_version": doc.get("format_version"),
                      "as_of": doc.get("as_of") or cfg["as_of"], "results": results, "by_rule": cov}


def draft_override_rows(m):
    for kind, rec, c in m.cfg["draft_overrides"]:
        m.review.append({"item": m.cfg["site"], "kind": "draft authority override",
                         "owner": m.cfg["owners"].get(rec) or "needs owner",
                         "why": f"the site file overrides the authority for {kind} to {rec}, but the override is "
                                f"{onto_mod.cert_text(c)}; the default ({DEFAULT_AUTHORITY.get(kind, 'none')}) "
                                "stays in force until it is certified"})


# ---------------------------------------------------------------- conflicts as graph nodes, human decisions

RULING_STATUS = {"accept_source": "resolved", "accept_value": "resolved", "no_conflict": "resolved",
                 "authority_override": "resolved", "defer": "disputed"}
RULING_AUTHORITIES = ("field", "record", "person")
RULED = "record differs from a ruling"


def read_decisions(path, site):
    """One decisions file -> [(conflict id, history entry, line)]. Two forms: one map's decisions.csv
    (conflict_id,status,by,on,note) and the context map's `ruling` template (ruling_id,concerns,attribute,ruling,
    chosen_source,chosen_value,reason,by,on,authority,evidence). A field verification (walkdown) ruling is a ruling
    row with authority `field` and, under `evidence`, the photo, nameplate reading or locator that shows it."""
    try:
        first = Path(path).read_text(encoding="utf-8-sig").lstrip().split("\n", 1)[0]
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"decisions {path}: can't read as UTF-8 ({exc})") from None
    if "ruling_id" not in [h.strip() for h in first.split(",")]:
        out = []
        for n, r in enumerate(read_csv(path, "decisions", ("conflict_id", "status", "by", "on", "note")), 2):
            if r["status"] not in CONFLICT_STATUSES or not r["by"] or not r["on"]:
                raise InputError(f"decisions line {n}: status open/disputed/resolved with by and on is required")
            out.append((r["conflict_id"], {k: r[k] for k in ("status", "by", "on", "note")}, n))
        return out
    out = []
    rows = read_csv(path, "rulings", ("ruling_id", "concerns", "ruling", "reason", "by", "on"))
    for n, r in enumerate(rows, 2):
        where = f"{Path(path).name} line {n}"
        if r["ruling"] not in RULING_STATUS:
            raise InputError(f"{where}: ruling must be one of {', '.join(RULING_STATUS)}")
        if not (r["ruling_id"] and r["reason"] and r["by"] and onto_mod.DATE.match(r["on"] or "")):
            raise InputError(f"{where}: ruling_id, reason, by and on (YYYY-MM-DD) are required")
        authority = r.get("authority") or "person"
        if authority not in RULING_AUTHORITIES:
            raise InputError(f"{where}: authority must be one of {', '.join(RULING_AUTHORITIES)}")
        if authority == "field" and not r.get("evidence"):
            raise InputError(f"{where}: a field verification ruling needs evidence (photo file, nameplate reading "
                             "or locator)")
        concerns = r["concerns"]
        if concerns.startswith(f"{site}/CONFLICT/"):
            cid = concerns.rsplit("/", 1)[-1]
        elif "/" in concerns:  # an item: the one detected conflict on that item and attribute (apply_decisions)
            if not r.get("attribute"):
                raise InputError(f"{where}: a ruling that concerns an item ({concerns}) names the attribute")
            cid = ("item", concerns, r["attribute"])
        else:
            cid = concerns
        rec = {"status": RULING_STATUS[r["ruling"]], "by": r["by"], "on": r["on"], "note": r["reason"],
               "ruling_id": r["ruling_id"], "ruling": r["ruling"], "authority": authority}
        for k in ("attribute", "chosen_source", "chosen_value", "evidence"):
            if r.get(k):
                rec[k] = r[k]
        out.append((cid, rec, n))
    return out


def apply_decisions(conflicts, previous, decisions_paths, site=""):
    """Carry earlier human statuses forward; apply new decisions and rulings (each file in order, each row once).
    Nothing is auto-resolved."""
    for cid, old in (previous or {}).items():
        if cid in conflicts:
            conflicts[cid]["status"], conflicts[cid]["history"] = old["status"], old["history"]
        else:
            kept = copy.deepcopy(old)
            kept["detected"] = False
            conflicts[cid] = kept
    if isinstance(decisions_paths, (str, Path)):
        decisions_paths = [decisions_paths]
    for path in decisions_paths or ():
        for cid, rec, n in read_decisions(path, site):
            if isinstance(cid, tuple):
                _, item, attr = cid
                hits = sorted(k for k, c in conflicts.items()
                              if c["subject"] == item and c["attribute"] == attr and c.get("detected", True))
                if len(hits) != 1:
                    raise InputError(f"{Path(path).name} line {n}: {item} {attr} has "
                                     f"{'no' if not hits else len(hits)} detected conflict(s)"
                                     + (f" ({', '.join(hits)}); name one conflict id" if hits else ""))
                cid = hits[0]
            if cid not in conflicts:
                raise InputError(f"{Path(path).name} line {n}: unknown conflict {cid}")
            if rec not in conflicts[cid]["history"]:
                conflicts[cid]["history"].append(rec)
                conflicts[cid]["status"] = rec["status"]
    return conflicts


def ruling_rows(m):
    """A resolved conflict whose last ruling chose a value while a record still says another: a review row asking
    that record's owner to update it. The ruling settles the dispute; the record stays its owner's to change."""
    for cid, c in sorted(m.conflicts.items()):
        last = c["history"][-1] if c["history"] else {}
        chosen = last.get("chosen_value") or next(
            (c[x]["says"] for x in ("source_a", "source_b")
             if last.get("chosen_source") and c[x]["source"].get("document") == last["chosen_source"]), None)
        if c["status"] != "resolved" or not c["detected"] or chosen is None:
            continue
        for side in ("source_a", "source_b"):
            src, says = c[side]["source"], c[side]["says"]
            rec = m.record_of.get(src.get("document"))
            if same_value(says, chosen) or rec in (None, "work_order"):
                continue
            subj = (m.nodes.get(c["subject"]) or {}).get("tag") or c["subject"]
            m.review.append({"item": c["subject"], "kind": RULED, "owner": m.cfg["owners"].get(rec) or "needs owner",
                             "why": f"{subj} {c['attribute']}: {last['by']} ruled {chosen} on "
                                    f"{last['on']} ({last.get('authority', 'person')}"
                                    + (f": {last['evidence']}" if last.get("evidence") else "")
                                    + f"; {last.get('ruling_id') or 'decision'} on {cid}); the "
                                      f"{RECORD_NAMES.get(rec, rec.replace('_', ' '))} {src.get('document')} "
                                      f"({src.get('locator') or 'no locator'}) still says {says}: update it"})


def conflict_nodes(m):
    for cid, c in sorted(m.conflicts.items()):
        nid = qid(m.cfg["site"], "CONFLICT", cid)
        n = mk_node(nid, "conflict", cid, c["what"], c["source_a"]["source"], conflict=c)
        m.nodes[nid] = n
        if c["subject"] in m.nodes:
            m.edges[f"concerns:{nid}"] = mk_edge("concerns", nid, c["subject"], c["source_a"]["source"])
        else:
            n["subject_not_on_map"] = c["subject"]


# ---------------------------------------------------------------- review queues: people review disagreements

def spot_check(item, every):
    return "sample" if every and int(hashlib.sha256(item.encode("utf-8")).hexdigest()[:8], 16) % every == 0 else ""


def queue_rows(m):
    """Red: open/disputed conflicts. Amber: review items, partly located / not found loops and safety-relevant
    matches (the floor). Green: list items located on a drawing with nothing disagreeing, and loops located and
    consistent; a deterministic sample of them is flagged for spot-check instead of full review."""
    cfg = m.cfg
    rows = []
    for cid, c in sorted(m.conflicts.items()):
        if c["status"] == "resolved":
            continue
        plant, unit = scope_of(c["subject"], cfg)
        subj = m.nodes.get(c["subject"]) or {}
        rows.append({"tier": "red", "owner": c["record_owner"], "plant": plant, "unit": unit,
                     "item": qid(cfg["site"], "CONFLICT", cid), "kind": "conflict: " + c["type"],
                     "why": f"{c['what']} ({c['status']}{'' if c['detected'] else ', no longer detected'})",
                     "safety": safety_of(subj["tag"]) if subj.get("tag") else ""})
    for r in m.review:
        plant, unit = scope_of(r["item"], cfg)
        rows.append({"tier": "amber", "owner": r["owner"], "plant": plant, "unit": unit, "item": r["item"],
                     "kind": r["kind"], "why": r["why"], "safety": (m.nodes.get(r["item"]) or {}).get("safety", "")})
    conflicted = {c["subject"] for c in m.conflicts.values() if c["status"] != "resolved"}
    for lp in m.loops:
        plant, unit = scope_of(lp["item"], cfg)
        safety = safety_of(lp["output"])
        ok = lp["outcome"] == "located and consistent" and lp["item"] not in conflicted
        rows.append({"tier": "green" if ok and not safety else "amber", "owner": lp["route"] if not ok else
                     cfg["owners"].get("loop_list") or "needs owner", "plant": plant, "unit": unit,
                     "item": f"loop {lp['controller']} ({lp['loop_list']} line {lp['line']})", "kind": "listed loop",
                     "why": (f"safety-relevant ({safety}): always checked; " if safety else "") + lp["outcome"]
                     + (f" on {', '.join(lp['zones'] or lp['sheets'])}" if lp["sheets"] else "")
                     + (": " + "; ".join(lp["missing"]) if lp["missing"] else ""), "safety": safety})
    for nid, n in sorted(m.nodes.items()):
        if not n.get("listed_in") or not n.get("appearances") or nid in conflicted:
            continue
        plant, unit = scope_of(nid, cfg)
        safety = n.get("safety", "")
        where = ", ".join(f"{a['sheet']}" + (f":{a['zone']}" if a.get("zone") else "") for a in n["appearances"])
        rows.append({"tier": "amber" if safety else "green", "owner": n.get("owner") or "needs owner",
                     "plant": plant, "unit": unit, "item": nid, "kind": n["kind"],
                     "why": (f"safety-relevant ({safety}): always checked; " if safety else "")
                     + f"listed in {', '.join(n['listed_in'])}; located on {where}", "safety": safety})
    rows.sort(key=lambda r: (TIER_ORDER[r["tier"]], 0 if r["safety"] else 1, r["kind"] in LOW_PRIORITY_KINDS, r["kind"],
                             r["item"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["spot_check"] = spot_check(r["item"], cfg["sample_every"]) if r["tier"] == "green" else ""
    return rows


def floor_problems(rows, safety_col="safety", tier_col="tier", why_cols=()):
    """The safety floor survives the split: no safety-relevant row is green."""
    bad = []
    for r in rows:
        marked = r.get(safety_col) or any("safety-relevant" in (r.get(c) or "") for c in why_cols)
        if marked and r.get(tier_col) == "green":
            bad.append(r.get("item") or r.get("item_id"))
    return bad


def split(rows, key):
    """Order-preserving split: each part keeps the global risk order (and its safety floor)."""
    out = defaultdict(list)
    for r in rows:
        out[r.get(key) or "unassigned"].append(r)
    slugs = defaultdict(set)
    for k in out:
        slugs[slug(k)].add(k)
    clash = {s: sorted(ks) for s, ks in slugs.items() if len(ks) > 1}
    if clash:
        raise InputError(f"split values collide as file names: {clash}")
    return dict(sorted(out.items()))


def csv_text(cols, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])
    return buf.getvalue()


# ---------------------------------------------------------------- checks and reports

ONE_MAP_KINDS = ("site", "unit", "scope", "document", "conflict")
ONE_MAP_EDGES = ("covers", "mentions", "based_on", "references", "signal_line", "concerns")


def problems(g):
    """twin-graph-2 = every twin-graph-1 rule (graph_export.problems, unchanged) plus the one-map rules. The one-map
    kinds and edge types are mapped onto twin-graph-1 vocabulary with no special rules for that check only, so
    graph_export.py itself (whose bytes other reports pin) stays untouched and keeps refusing twin-graph-2."""
    if g.get("schema") != SCHEMA:
        return gx.problems(g)
    base = dict(g, schema=gx.SCHEMA,
                nodes=[dict(n, kind="plant") if n.get("kind") in ONE_MAP_KINDS else n for n in g.get("nodes", [])],
                edges=[dict(e, type="acts_on") if e.get("type") in ONE_MAP_EDGES else e for e in g.get("edges", [])])
    out = gx.problems(base)
    nodes = {n["id"]: n for n in g.get("nodes", [])}
    site = [n for n in nodes.values() if n["kind"] == "site"]
    if len(site) != 1:
        out.append(f"a one-map graph has exactly one site node (found {len(site)})")
    parents = defaultdict(list)
    for e in g.get("edges", []):
        if e["type"] == "contains":
            parents[e["to"]].append(e["from"])
        if e["type"] == "mentions":
            miss = {"file", "locator", "matched_text", "confidence"} - {c["name"] for c in e.get("attributes", [])}
            if miss:
                out.append(f"edge {e['id']}: a mention needs {', '.join(sorted(miss))}")
        if e["type"] == "based_on" and not any(c["name"] == "revision" for c in e.get("attributes", [])):
            out.append(f"edge {e['id']}: based_on needs the revision it is based on")
        if e["type"] in ("covers", "mentions", "based_on") and nodes.get(e["from"], {}).get("kind") != "document":
            out.append(f"edge {e['id']}: {e['type']} must start at a document")
    for nid, n in nodes.items():
        if site and n["kind"] != "site" and not nid.startswith(site[0]["id"] + "/"):
            out.append(f"node {nid}: id is not qualified by the site ({site[0]['id']}/...)")
        if n["kind"] == "system" and len(parents[nid]) != 1:
            out.append(f"node {nid}: a system has exactly one owning scope (found {len(parents[nid])})")
        if n["kind"] == "document":
            d = n.get("document") or {}
            if d.get("status") not in DOC_STATUSES or not d.get("owner") or not d.get("revision"):
                out.append(f"node {nid}: a document needs revision, owner and status draft|released")
        if n["kind"] == "conflict":
            c = n.get("conflict") or {}
            if (c.get("status") not in CONFLICT_STATUSES or not c.get("record_owner")
                    or c.get("type") not in CONFLICT_TYPES):
                out.append(f"node {nid}: a conflict needs a known type, a record owner and status open|disputed|resolved")
            for side in ("source_a", "source_b"):
                if not isinstance((c.get(side) or {}).get("source"), dict):
                    out.append(f"node {nid}: {side} needs its source")
    return out


def report_md(g, run, groups, reopened, loops_, uncovered):
    nodes, edges = g["nodes"], g["edges"]
    kinds, types = defaultdict(int), defaultdict(int)
    for n in nodes:
        kinds[n["kind"]] += 1
    for e in edges:
        types[e["type"]] += 1
    conf = [n["conflict"] for n in nodes if n["kind"] == "conflict"]
    by_owner = defaultdict(lambda: defaultdict(int))
    for c in conf:
        by_owner[c["record_owner"]][c["type"]] += 1
    listed = [n for n in nodes if n.get("listed_in")]
    lines = ["# One map: run report", "",
             f"Generated by `scripts/one_map.py build` from `{g['source_model']}` ({g['title']}). Schema `{SCHEMA}`. "
             "The P&IDs are lined up against the equipment and instrument records, datasheets hold the values, and "
             "people work the review queue. No item is verified by this run.", "",
             f"Sheets rebuilt: {len(run['rebuilt'])} ({', '.join(run['rebuilt']) or 'none'}); reused unchanged: "
             f"{len(run['reused'])}; removed from the register: {len(run['removed'])}.", "",
             f"Items in an equipment or instrument record: {len(listed)}; located on a P&ID: "
             f"{sum(1 for n in listed if n['appearances'])}; "
             "on a P&ID but in no equipment or instrument record: "
             f"{sum(1 for n in nodes if n.get('listed_in') == [])}.", ""]
    if uncovered:
        lines += ["Units with listed items but no registered sheet yet (not reported as missing): "
                  + ", ".join(f"{k} ({v})" for k, v in uncovered.items()) + ".", ""]
    lines += ["## Nodes and edges", "", "| Node kind | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(kinds.items())]
    lines += ["", "| Edge type | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(types.items())]
    classes = defaultdict(int)
    for n in nodes:
        if n["kind"] in ITEM_KINDS and n.get("tag"):
            classes[n.get("class") or "(unset: not deterministic from the records or tag letters)"] += 1
    lines += ["", "## Item classes (classes.json)", "", "| Class | Items |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(classes.items())]
    lc = (g.get("coverage") or {}).get("relations_checked") or {}
    if lc:
        lines += ["", f"Links checked against relations.json: {lc['checked']} of {lc['links']} "
                      f"({lc['unchecked_no_class']} with an end of no class, not checked); "
                      f"{lc['do_not_fit']} do not fit what they connect (review rows, kept on the map)."]
    exp = g.get("expectations")
    if exp:
        lines += ["", "## Expectations (completeness rules)", "",
                  f"Rules from `{exp['rules_source']}`, as of {exp['as_of'] or 'no date (date checks not evaluated)'}. "
                  "A check whose register is absent for the subject's scope is not evaluated; a draft rule raises one "
                  "summary row per scope; a rule not rolled out to a scope raises nothing there.", "",
                  "| Rule | Certification | Subjects | Complete | Missing | Not evaluable | Not rolled out | Rows raised |",
                  "|---|---|---|---|---|---|---|---|"]
        for c in exp["by_rule"]:
            lines.append(f"| {c['rule']} | {c['certification']} | {c['subjects']} | {c['complete']} | {c['missing']} | "
                         f"{c['not_evaluable']} | {c['not_rolled_out']} | {c['rows_raised']} |")
    if g.get("glossary"):
        lines += ["", "## Glossary", "", "| Term | Scope | Maps to | Certification |", "|---|---|---|---|"]
        for tm in g["glossary"]:
            lines.append(f"| {tm['term']} | {tm['scope']} | {tm['maps_to_item'] or tm['maps_to_class'] or '-'} | "
                         f"{onto_mod.cert_text(tm['certification'])} |")
        links = sum(1 for e in edges if e["type"] == "mentions"
                    and any(c["name"] == "matched" and c["value"] == "glossary" for c in e.get("attributes", [])))
        lines += ["", f"Document mentions linked through a certified glossary term: {links}."]
    lines += ["", "## Conflicts by record owner", "", "| Owner | Type | Count |", "|---|---|---|"]
    for o in sorted(by_owner):
        for t in sorted(by_owner[o]):
            lines.append(f"| {o} | {t} | {by_owner[o][t]} |")
    lines += ["", "## Listed loops located on the drawings", "",
              "| Loop list | Controller | Measurement | Output | Outcome | Where | Routed to | Missing |",
              "|---|---|---|---|---|---|---|---|"]
    for lp in loops_:
        lines.append(f"| {lp['loop_list']} line {lp['line']} | {lp['controller']} | {lp['measurement']} | "
                     f"{lp['output']} | {lp['outcome']} | {', '.join(lp['zones'] or lp['sheets']) or '-'} | "
                     f"{lp['route'] if lp['outcome'] != 'located and consistent' else 'spot-check'} | "
                     f"{'; '.join(lp['missing']) or '-'} |")
    lines += ["", "## Loop-number groups on the drawings (secondary; compared with the list, never asserted)", ""]
    for scope, rep in sorted(groups.items()):
        for gr in rep:
            lines.append(f"- {scope} loop {gr['loop']}: {', '.join(gr['members'])}"
                         + (f" ({gr['note']})" if gr["note"] else ""))
    lines += ["", "## Reopened by a basis change", ""]
    lines += [f"- {r}" for r in reopened] or ["- none on this run"]
    return "\n".join(lines) + "\n"


def conflicts_md(conf):
    lines = ["# Conflicts, routed to the owner of the record", "",
             "Each conflict keeps what both sources say. None is resolved by software; a person records a decision "
             "(`--decisions`).", ""]
    by_owner = defaultdict(list)
    for c in conf:
        by_owner[c["record_owner"]].append(c)

    def cell(s):
        src = s["source"]
        where = src.get("document") or src.get("kind")
        loc = src.get("locator") or (f"sheet {src['sheet']}" + (f" zone {src['zone']}" if src.get("zone") else "")
                                     if src.get("sheet") else "")
        return f"{s['says']} ({where}{', ' + loc if loc else ''})".replace("|", "/")
    for o in sorted(by_owner):
        lines += [f"## {o}", "", "| Id | Type | Status | About | Source A says | Source B says |",
                  "|---|---|---|---|---|---|"]
        for c in sorted(by_owner[o], key=lambda c: (c["type"], c["id"])):
            lines.append(f"| {c['id']} | {c['type']} | {c['status']}{'' if c['detected'] else ' (not detected now)'} "
                         f"| {c['subject']} {c['attribute']} | {cell(c['source_a'])} | {cell(c['source_b'])} |")
        lines.append("")
    decided = sorted((c for c in conf if c["history"]), key=lambda c: c["id"])
    if decided:
        lines += ["## Decision history", "",
                  "Every decision and ruling recorded with `--decisions`, oldest first. A field verification ruling "
                  "(authority `field`) names its evidence.", ""]
        for c in decided:
            lines.append(f"- **{c['id']}** ({c['subject']} {c['attribute']}), now {c['status']}:")
            for h in c["history"]:
                extra = [f"{k} {h[k]}" for k in ("ruling_id", "ruling", "authority", "chosen_value", "evidence")
                         if h.get(k)]
                lines.append(f"  - {h['on']} {h['by']}: {h['status']}" + (f" ({'; '.join(extra)})" if extra else "")
                             + (f". {h['note']}" if h.get("note") else ""))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- build (incremental)

def assemble(cfg, register, fragments):
    """The one assembly both starts share: path A (lists first) and path B (drawings only) differ only in which
    lists exist; the map, conflicts and queues come from the same steps."""
    m = Map(cfg)
    hierarchy(m)
    lists = load_lists(m)
    uncovered = place_fragments(m, register, fragments, lists)
    load_datasheets(m, lists)
    for nid, c in m.pid_values:  # a P&ID value differing from the records is a note, never a value conflict
        m.add_value(nid, c, "pid")
    classify(m)
    load_records(m)
    work_order_closeout(m, lists)
    pair_offpage(m, fragments)
    groups = loops(m, lists)
    docs = documents(m, cfg, lists)
    sources = coverage_sources(m, register, lists)
    m.sources = sources
    check_relations(m)
    expectations(m, sources)
    draft_override_rows(m)
    return m, lists, uncovered, groups, docs


# ---------------------------------------------------------------- path B: draft lists generated from drawings

LIST_COLS = ("tag", "plant", "unit", "system", "kind", "description", "status", "review_tier", "how_found",
             "located_on")
LOOP_COLS = ("controller", "measurement", "output", "description", "status", "review_tier", "how_found",
             "confidence", "located_on")


def where(n):
    return " ".join(f"{a['sheet']}" + (f":{a['zone']}" if a.get("zone") else "") for a in n.get("appearances", []))


def draft_lists(site_path, out_dir, scopes=None):
    """Start from drawings: write draft equipment list, instrument index and loop list per scope in the same formats
    the import path reads (loop lists keep loop_audit.py's contract). Only scopes no list covers are drafted unless
    --scope names them. Every row is status unverified, tiered for review with the safety floor (never green)."""
    cfg = load_site(site_path)
    register = load_register(cfg)
    fragments = {r["doc"]: sheet_fragment(cfg, r) for r in register}
    m, lists, _, _, _ = assemble(cfg, register, fragments)
    sheet_scopes = sorted({f["scope"] for f in fragments.values()})
    dup = {r["item"] for r in m.review if r["kind"] == "duplicate tag"}
    loop_scopes = {spec.get("scope") for spec in cfg["raw"].get("loop_lists") or []}
    def head(record):
        return (f"# DRAFT {RECORD_NAMES[record]} generated from P&ID sheets by one_map.py draft-lists. Status stays "
                f"unverified until a person reviews each row;\n# once reviewed it is an ordinary "
                f"{RECORD_NAMES[record]}: set status and add it to the site file.\n")
    files, counts = {}, {}
    for scope in sheet_scopes:
        if scopes and scope not in scopes:
            continue
        plant, unit = scope_of(scope, cfg) if scope.count("/") > 1 else (scope.split("/")[1], "")
        folder = slug(f"{plant}-{unit}" if unit else plant)
        for record, name in (("maintenance_export", "equipment.csv"), ("instrument_index", "instrument_index.csv")):
            if not scopes and covering(lists, record, scope):
                continue
            rows = []
            for nid, n in sorted(m.nodes.items()):
                if n.get("scope") != scope or n.get("listed_in") != [] or list_for(n["kind"]) != record:
                    continue
                placeholder = n.get("tag_status") == "placeholder"
                tier = "amber" if n.get("safety") or nid in dup or placeholder else "green"
                rows.append({"tag": n["tag"], "plant": plant, "unit": unit, "system": "", "kind": n["kind"],
                             "description": n.get("name") or "", "status": "unverified", "review_tier": tier,
                             "how_found": "P&ID" + (", safety-relevant (" + n["safety"] + "): always checked"
                                                       if n.get("safety") else "")
                                          + (", placeholder tag: a person supplies the real tag" if placeholder
                                             else "") + (", duplicate tag on a sheet" if nid in dup else ""),
                             "located_on": where(n)})
            if rows:
                rows.sort(key=lambda r: (TIER_ORDER[r["review_tier"]], r["tag"]))
                files[f"{folder}/{name}"] = head(record) + csv_text(LIST_COLS, rows)
                counts[f"{folder}/{name}"] = len(rows)
        if not unit or (not scopes and scope in loop_scopes):
            continue
        members = {nid: n["tag"] for nid, n in m.nodes.items() if n.get("scope") == scope and n.get("appearances")
                   and n["kind"] in ("instrument", "controller", "final_element")}
        sig = {frozenset((e["from"], e["to"])) for e in m.edges.values() if e["type"] == "signal_line"
               and e["from"] in members and e["to"] in members}
        cands, _ = loop_candidates(members, sig)
        rows, notes = [], []
        for ctl, c in cands.items():
            tag = m.nodes[ctl]["tag"]
            if len(c["in"]) != 1 or len(c["out"]) != 1:
                notes.append(f"# not written as a loop, needs review: {tag} measurement candidates "
                             f"[{', '.join(sorted(m.nodes[x]['tag'] for x in c['in']))}], output candidates "
                             f"[{', '.join(sorted(m.nodes[x]['tag'] for x in c['out']))}]\n")
                continue
            (mi, h_in), (out, h_out) = next(iter(c["in"].items())), next(iter(c["out"].items()))
            both = h_in == h_out == {"loop_number", "signal_line"}
            safety = safety_of(m.nodes[out]["tag"])
            how = "+".join(sorted(h_in | h_out))
            rows.append({"controller": tag, "measurement": m.nodes[mi]["tag"], "output": m.nodes[out]["tag"],
                         "description": "", "status": "unverified",
                         "review_tier": "green" if both and not safety else "amber", "how_found": how,
                         "confidence": ("loop number and drawn signal lines agree" if both else
                                        f"measurement: {'+'.join(sorted(h_in))}; output: {'+'.join(sorted(h_out))}"),
                         "located_on": where(m.nodes[ctl])})
        if rows or notes:
            rows.sort(key=lambda r: (TIER_ORDER[r["review_tier"]], r["controller"]))
            files[f"{folder}/loops.csv"] = head("loop_list") + "".join(notes) + csv_text(LOOP_COLS, rows)
            counts[f"{folder}/loops.csv"] = len(rows)
    out_dir = Path(out_dir)
    for rel, text in files.items():
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return counts


def build(site_path, out_dir, *, full=False, decisions=None, register_path=None):
    cfg = load_site(site_path)
    out_dir = Path(out_dir)
    state_path = out_dir / "state.json"
    prev = read_json(state_path, "state") if state_path.exists() and not full else {}
    if prev and prev.get("schema") != STATE_SCHEMA:
        raise InputError(f"{state_path}: not a {STATE_SCHEMA} file")
    code = sha_bytes(Path(__file__).read_bytes().replace(bytes([13, 10]), bytes([10])))
    cached = (prev.get("sheets") or {}) if prev.get("code") == code else {}  # new parsing code: re-read every sheet
    register = load_register(cfg)
    fragments, run = {}, {"rebuilt": [], "reused": [], "removed": []}
    for row in register:
        old = cached.get(row["doc"])
        sha = sha_bytes(row["path"].read_bytes())
        if (old and old["rev"] == row["rev"] and old["sha256"] == sha and old.get("plant") == row["plant"]
                and old.get("unit") == row["unit"] and old.get("owner") == row["owner"]):
            fragments[row["doc"]] = old["fragment"]
            run["reused"].append(row["doc"])
        else:
            fragments[row["doc"]] = sheet_fragment(cfg, row)
            run["rebuilt"].append(row["doc"])
    run["removed"] = sorted(set(prev.get("sheets") or {}) - set(fragments))
    m, lists, uncovered, groups, docs = assemble(cfg, register, fragments)
    # reopen: a document whose own revision/bytes changed reopens everything based on it, transitively
    reopened = []
    old_docs = prev.get("documents") or {}
    current = dict(docs, **{r["doc"]: {"revision": r["rev"], "sha256": fragments[r["doc"]]["sha256"]}
                            for r in register})
    changed = sorted(d for d in current if d in old_docs and old_docs[d] != current[d])
    dependents = defaultdict(set)
    for e in m.edges.values():
        if e["type"] == "based_on":
            dependents[e["to"].rsplit("/", 1)[1]].add(e["from"].rsplit("/", 1)[1])
    seen, todo = set(), list(changed)
    while todo:
        d = todo.pop(0)
        for dep in sorted(dependents[d]):
            if dep not in seen:
                seen.add(dep)
                todo.append(dep)
                why = (f"rev {old_docs[d]['revision']} -> {current[d]['revision']}" if d in old_docs
                       else "it changed upstream")
                reopened.append(f"document {dep}: its basis {d} changed ({why})")
    if register_path:
        reg = read_json(register_path, "context register")
        try:
            cr.validate_register(reg)
        except cr.InputError as exc:
            raise InputError(str(exc)) from None
        hit = set(changed) | seen
        by_id = {r["id"]: r for r in reg["decisions"]}
        for q, cur in sorted((reg.get("current") or {}).items()):
            for a in cur.get("answers", []):
                rec = by_id.get(a["decision_id"])
                if rec and rec["evidence"]["source"]["id"] in hit:
                    reopened.append(f"answer {q}/{a['answer_id']}: cites {rec['evidence']['source']['id']}, whose "
                                    "content or basis changed; reopen it with context_register.py apply")
    reopened = sorted(set(reopened))
    m.conflicts = apply_decisions(m.conflicts, prev.get("conflicts"), decisions, cfg["site"])
    ruling_rows(m)
    conflict_nodes(m)
    nodes = [m.nodes[k] for k in sorted(m.nodes)]
    edges = [m.edges[k] for k in sorted(m.edges)]
    g = {"schema": SCHEMA, "model_kind": "one_map", "title": cfg["site_name"], "site": cfg["site"],
         "source_model": cfg["path"].name, "nodes": nodes, "edges": edges, "questions": [], "events": [],
         "not_exported": [], "loops": m.loops,
         "coverage": {"sources": m.sources, "relations_checked": m.link_counts},
         **({"records": m.records} if m.records else {}),
         **({"glossary": m.glossary} if m.glossary else {}),
         **({"expectations": m.expectations} if m.expectations else {}),
         "counts": {"nodes": len(nodes), "edges": len(edges),
                    "claims": sum(len(n["attributes"]) for n in nodes) + sum(len(e.get("attributes", [])) for e in edges),
                    "conflicts": len(m.conflicts), "questions": 0, "events": 0}}
    bad = problems(g)
    if bad:
        raise InputError("the assembled map fails its own check: " + "; ".join(bad[:10]))
    rows = queue_rows(m)
    floor = floor_problems(rows)
    if floor:
        raise InputError(f"safety floor broken for {floor}")
    files = {"graph.json": json.dumps(g, indent=1, ensure_ascii=False) + "\n",
             "conflicts.md": conflicts_md(list(m.conflicts.values())),
             "report.md": report_md(g, run, groups, reopened, m.loops, uncovered),
             "queues/review_queue.csv": csv_text(QUEUE_COLS, rows)}
    unit_rows = [dict(r, unit_scope=f"{r['plant']}-{r['unit']}" if r["unit"] else (r["plant"] or "site")) for r in rows]
    for folder, rs_, key in (("by-owner", rows, "owner"), ("by-plant", [dict(r, plant=r["plant"] or "site")
                                                                         for r in rows], "plant"),
                             ("by-unit", unit_rows, "unit_scope")):
        for k, rs in split(rs_, key).items():
            files[f"queues/{folder}/{slug(k)}.csv"] = csv_text(QUEUE_COLS, rs)
    state = {"schema": STATE_SCHEMA, "code": code,
             "sheets": {r["doc"]: {"rev": r["rev"], "sha256": fragments[r["doc"]]["sha256"], "plant": r["plant"],
                                   "unit": r["unit"], "owner": r["owner"], "fragment": fragments[r["doc"]]}
                        for r in register},
             "documents": current, "conflicts": m.conflicts}
    files["state.json"] = json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "queues").exists():
        for p in (out_dir / "queues").rglob("*.csv"):
            if p.relative_to(out_dir).as_posix() not in files:
                p.unlink()
    for rel, text in files.items():
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    return g, run, rows, reopened


# ---------------------------------------------------------------- loop candidates on an existing twin-graph-1 graph

def loops_from_graph(graph_path):
    g = read_json(graph_path, "graph")
    kind = {n["id"]: n for n in g.get("nodes", [])}
    parent = {}
    for e in g.get("edges", []):
        if e["type"] == "contains":
            parent[e["to"]] = e["from"]
    def scope(nid):  # climb item parents (an instrument contained by its valve) to the sheet's system/unit/plant
        seen = set()
        while nid in parent and nid not in seen and kind.get(nid, {}).get("kind") not in SCOPE_KINDS:
            seen.add(nid)
            nid = parent[nid]
        return nid if kind.get(nid, {}).get("kind") in SCOPE_KINDS else "unplaced"
    by_scope = defaultdict(dict)
    for n in g.get("nodes", []):
        if n["kind"] in ("instrument", "controller", "final_element") and n.get("tag"):
            by_scope[scope(n["id"])][n["id"]] = n["tag"]
    adj = defaultdict(set)
    for e in g.get("edges", []):
        if e["type"] in ("instrument_connection", "signal_line"):
            adj[e["from"]].add(e["to"])
            adj[e["to"]].add(e["from"])
    signals = defaultdict(set)
    for scope, members in by_scope.items():
        for a in members:
            seen, todo = {a}, [a]
            while todo:  # through junctions only, never through another item
                x = todo.pop()
                for y in adj[x]:
                    if y in seen:
                        continue
                    seen.add(y)
                    if y in members and y != a:
                        signals[scope].add(frozenset((a, y)))
                    elif kind.get(y, {}).get("kind") == "junction":
                        todo.append(y)
    lines = [f"# Loop candidates from `{Path(graph_path).name}`", "",
             "Generated by `scripts/one_map.py loops-from-graph`. Instruments are grouped by loop number only inside "
             "their containing scope; letters decide the role (controller, measurement, final element). A candidate "
             "needs a controller. Nothing here is a verified loop. Tags are read as printed; a duplicate printed "
             "tag is listed twice.", ""]
    total = 0
    for scope in sorted(by_scope):
        cands, report = loop_candidates(by_scope[scope], signals[scope])
        roles = defaultdict(int)
        for t in by_scope[scope].values():
            lk = loop_key(t)
            roles[(role_of(lk[0]) if lk else None) or "unclassified"] += 1
        lines += [f"## Scope {scope}", "",
                  f"{len(by_scope[scope])} instrument-like items: "
                  + ", ".join(f"{k} {v}" for k, v in sorted(roles.items()))
                  + f"; {sum(len(s) for s in [signals[scope]])} instrument-to-instrument signal paths.", "",
                  "| Loop number | Members | Result |", "|---|---|---|"]
        for gr in report:
            lines.append(f"| {gr['loop']} | {', '.join(gr['members'])} | {gr['note'] or 'paired'} |")
        flat = [(x, ctl, sorted(h)) for ctl, c in cands.items() for x, h in c["in"].items()]
        flat += [(ctl, x, sorted(h)) for ctl, c in cands.items() for x, h in c["out"].items()]
        total += len(flat)
        lines += ["", f"Candidate pairings (to compare with a loop list, never asserted): {len(flat)}."]
        lines += [f"- {kind[a]['tag']} -> {kind[b]['tag']} ({', '.join(h)})" for a, b, h in flat]
        lines.append("")
    return "\n".join(lines), total


def split_existing(csv_path, by, out_dir):
    text = Path(csv_path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    cols, rows = reader.fieldnames, list(reader)
    if by not in cols:
        raise InputError(f"{csv_path}: no column {by!r} (columns: {', '.join(cols)})")
    bad = floor_problems(rows, safety_col="__none__", why_cols=("why", "why_check_this"))
    if bad:
        raise InputError(f"safety floor broken in the input queue for {bad[:5]}")
    parts = split(rows, by)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for k, rs in parts.items():
        (Path(out_dir) / f"{slug(k)}.csv").write_text(csv_text(cols, rs), encoding="utf-8", newline="\n")
    return {k: len(v) for k, v in parts.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build or refresh the one map from a site file (incremental by sheet)")
    b.add_argument("site")
    b.add_argument("--out", required=True)
    b.add_argument("--full", action="store_true", help="ignore the previous state and rebuild every sheet")
    b.add_argument("--decisions", action="append",
                   help="CSV of human conflict decisions (conflict_id,status,by,on,note) or rulings in the ruling "
                        "template (a field verification ruling has authority field and evidence); repeatable")
    b.add_argument("--register", help="a context_register.py context.json whose answers may reopen")
    c = sub.add_parser("check", help="validate a one-map (twin-graph-2) graph")
    c.add_argument("graph")
    lg = sub.add_parser("loops-from-graph", help="loop candidates on an existing graph export")
    lg.add_argument("graph")
    lg.add_argument("--out")
    d = sub.add_parser("draft-lists", help="start from drawings: write draft equipment/instrument/loop lists")
    d.add_argument("site")
    d.add_argument("--out", required=True)
    d.add_argument("--scope", action="append", help="draft this scope even if a list covers it (repeatable)")
    sp = sub.add_parser("sheet-from-prediction",
                        help="convert a drawing reader's prediction file into a one-map-sheet-1 sheet read")
    sp.add_argument("prediction", help="predictions/<label>/<tool>/<sheet>.json, or a bare prediction file")
    sp.add_argument("--sheet", required=True, help="sheet id as in the drawing register")
    sp.add_argument("--rev", required=True, help="sheet revision as in the drawing register")
    sp.add_argument("--plant", required=True, help="plant or site scope id from the site file")
    sp.add_argument("--unit", default="", help="unit id (omit for a site-scope sheet)")
    sp.add_argument("--zones", default="8x12", help="zone grid ROWSxCOLS (default 8x12; see scripts/sheet_zone.py)")
    sp.add_argument("--zone-frame", help="x0,y0,x1,y1 of the drawing frame in 0-1000 units (default whole sheet)")
    sp.add_argument("--zone-origin", default="bottom-right", choices=("bottom-right", "top-left"),
                    help="where zone A-1 is: bottom-right (ASME style, default) or top-left (ISO style)")
    sp.add_argument("--out", required=True, help="the sheet read to write (JSON)")
    q = sub.add_parser("ask", help="answer one question about an item from a built graph, with provenance (read-only)")
    q.add_argument("--map", required=True, help="graph.json written by build")
    q.add_argument("--question-kind", required=True, choices=sorted(onto_mod.QUESTION_KINDS))
    q.add_argument("--item", required=True, help="qualified id, a tag unique on the map, or a certified glossary term")
    q.add_argument("--json", action="store_true", help="print the answer as JSON")
    jl = sub.add_parser("jsonld", help="write an optional JSON-LD view of a built graph")
    jl.add_argument("--map", required=True)
    jl.add_argument("--out", required=True)
    import map_changes as mc  # changes/affected reports (read-only); imported here, it imports nothing from here
    ch = sub.add_parser("changes", help="what changed between two builds (P&ID revision release, MOC or "
                                        "turnaround before/after pack); read-only")
    ch.add_argument("old", help="graph.json of the earlier build")
    ch.add_argument("new", help="graph.json of the later build")
    af = sub.add_parser("affected", help="records and documents holding or naming some tags, by owner (MOC open); "
                                         "--closeout: which of them changed by MOC close; read-only")
    af.add_argument("--map", help="graph.json written by build (not needed with --closeout)")
    af.add_argument("--closeout", nargs=2, metavar=("OPEN", "CLOSE"),
                    help="graph.json at MOC open and at MOC close: affected records changed or still unchanged")
    for x in (ch, af):
        x.add_argument("--tags", action="extend", nargs="+", default=[],
                       help="tags or qualified ids (a tag must name one item)")
        x.add_argument("--scope", action="extend", nargs="+", default=[], help="qualified scope ids, e.g. S1/P1/PAST1")
        x.add_argument("--critical", default=",".join(mc.DEFAULT_CRITICAL),
                       help="criticality_ranking values that raise the criticality review flag "
                            f"(default {','.join(mc.DEFAULT_CRITICAL)})")
        x.add_argument("--out", help="folder for the .md and .json reports (default: print the Markdown)")
    s = sub.add_parser("split-queue", help="split an existing review_queue.csv by a column, keeping its order")
    s.add_argument("queue")
    s.add_argument("--by", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "build":
            g, run, rows, reopened = build(a.site, a.out, full=a.full, decisions=a.decisions, register_path=a.register)
            print(json.dumps(g["counts"]) + f" rebuilt {len(run['rebuilt'])} reused {len(run['reused'])} sheet(s); "
                  f"{len(rows)} queue rows; {len(reopened)} reopened -> {a.out}")
        elif a.cmd == "check":
            g = read_json(a.graph, "graph")
            bad = problems(g)
            for x in bad:
                print("FAIL:", x)
            print(f"{a.graph}: {len(bad)} problem(s)")
            return 1 if bad else 0
        elif a.cmd == "draft-lists":
            print(json.dumps(draft_lists(a.site, a.out, a.scope)) + f" -> {a.out}")
        elif a.cmd == "sheet-from-prediction":
            import sheet_zone as sz
            try:
                rows_, cols_ = sz.parse_grid(a.zones)
                frame = sz.parse_frame(a.zone_frame) if a.zone_frame else None
            except ValueError as exc:
                raise InputError(str(exc)) from None
            read = sheet_from_prediction(a.prediction, sheet=a.sheet, revision=a.rev, plant=a.plant, unit=a.unit,
                                         rows=rows_, cols=cols_, frame=frame, origin=a.zone_origin)
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(read, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                   newline="\n")
            c = read["conversion"]
            print(f"{c['symbols_in']} symbols, {c['connections_in']} connections -> {c['equipment']} equipment, "
                  f"{c['instruments']} instruments, {c['offpage']} off-page, {c['untagged']} untagged, "
                  f"{c['lines']} lines, {c['signal_lines']} signal lines -> {a.out}")
            for x in c["not_converted"]:
                print("not converted:", x)
        elif a.cmd == "ask":
            ans = onto_mod.ask(read_json(a.map, "graph"), a.question_kind, a.item)
            sys.stdout.write(json.dumps(ans, indent=1, ensure_ascii=False) + "\n" if a.json
                             else onto_mod.ask_text(ans))
        elif a.cmd == "jsonld":
            doc = onto_mod.to_jsonld(read_json(a.map, "graph"), onto_mod.Ontology.load())
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                                   newline="\n")
            print(f"{len(doc['@graph'])} JSON-LD nodes -> {a.out}")
        elif a.cmd in ("changes", "affected"):
            crit = tuple(x.strip() for x in a.critical.split(",") if x.strip())
            try:
                if a.cmd == "changes":
                    rep = mc.changes(read_json(a.old, "graph"), read_json(a.new, "graph"), a.tags, a.scope, crit,
                                     labels=(a.old, a.new))
                    stem, md = "changes", mc.changes_md(rep)
                elif a.closeout:
                    rep = mc.closeout(read_json(a.closeout[0], "graph"), read_json(a.closeout[1], "graph"), a.tags,
                                      a.scope, crit, labels=tuple(a.closeout))
                    stem, md = "closeout", mc.closeout_md(rep)
                else:
                    if not a.map:
                        raise InputError("affected needs --map (or --closeout OPEN CLOSE)")
                    rep = mc.affected(read_json(a.map, "graph"), a.tags, a.scope, crit, label=a.map)
                    stem, md = "affected", mc.affected_md(rep)
            except mc.ReportError as exc:
                raise InputError(str(exc)) from None
            if a.out:
                paths = mc.write(a.out, stem, rep, md)
                print(json.dumps(rep["counts"]) + " -> " + ", ".join(p.as_posix() for p in paths))
            else:
                sys.stdout.write(md)
        elif a.cmd == "loops-from-graph":
            text, total = loops_from_graph(a.graph)
            if a.out:
                Path(a.out).write_text(text, encoding="utf-8", newline="\n")
            print(f"{total} candidate edge(s)" + (f" -> {a.out}" if a.out else ""))
        else:
            counts = split_existing(a.queue, a.by, a.out)
            print(json.dumps(counts))
    except (InputError, onto_mod.OntologyError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
