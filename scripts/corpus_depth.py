"""The corpus depth register: every acquired public-source group and its disposition under docs/DEPTH_GOAL.md.

  python scripts/corpus_depth.py            # print the counts and the UNPLANNED groups
  python scripts/corpus_depth.py --write    # write docs/CORPUS_DEPTH.md
  python scripts/corpus_depth.py --check    # exit 1 if a rule is broken or docs/CORPUS_DEPTH.md is stale
  python scripts/corpus_depth.py --strict   # --check, and also exit 1 while any group is UNPLANNED (the goal's gate)
  python scripts/corpus_depth.py --reverify [--external DIR]
                                            # opt-in: recompute each key's cited counts from the pinned local bytes

It reads the existing registries and adds one disposition file beside them:

- the acquisition registries `data/public_sources_*.json` (one entry per download group), read only. Their bytes are
  pinned at acquisition, so they are never edited here;
- `data/corpus_depth.json`, keyed by group id: key availability VERIFIED from the group's own acquired files (the
  file, the field or column, a count and a one-line example, with the date it was read), an optional dated plan or
  retirement, and the sha256 of each registry it was read from. A registry that changes fails --check until its
  dispositions are re-read and the pin updated;
- `data/corpus_pins.json` for the files a verification may cite: a pinned file of the group (or `archive!member` of a
  pinned archive; the member is checked against the archive's listing by --reverify, since the pins hold no member
  list), or the group's own tracked metadata snapshot or a file its disposition cites;
- `docs/DEPTH_GOAL.md` for each group's area (its "Areas and the sources already acquired" table);
- `data/corpus.json` and `out/generalization/matrix.json` for what a group actually feeds: a corpus input whose
  `fetch` command or `local_path` names the group, and that input's matrix cells (the matrix must not be stale);
- `benchmarks/registry.json` for any registered suite whose case input files (followed through `*.input.json`) sit
  under the group's `data/external/` folder;
- `data/features.json` and the matrix rows' tool files (`scripts/corpus_matrix.py`) for the features a row exercises.

The status is derived, never typed: **feeds** needs a scored matrix cell (pass or fail) on an input that is neither
self-generated nor agent-keyed, or a registered benchmark; **planned** needs a plan with a date, the named key, the
task, an existing feature, a development/held-out split decided no later than the plan, an exposure statement, a key
verified as a key for a toolkit task with its independence from the tool's input, and tracked evidence files whose
quoted anchor is present and which mention the group; **deferred: needs feature** needs a verified key that no
existing feature consumes, the missing capability (a new id and one line) and the group's area; **retired** needs a
reason of a kind that can never qualify (no usable key, no area, duplicate, rights, blocked) with the same kind of
evidence; anything else is **UNPLANNED**. Stdlib only, no network. --check never opens the acquired files (they are
fetch-by-hash); --reverify reads them, after checking their pinned sha256, where a reader is available.
"""
import argparse
import csv
import functools
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import corpus_matrix  # noqa: E402  (row names, tool files and the staleness check; importing runs nothing)

REGISTRY_GLOB = "data/public_sources_*.json"
SIDECAR = "data/corpus_depth.json"
GOAL = "docs/DEPTH_GOAL.md"
CORPUS = "data/corpus.json"
MATRIX = "out/generalization/matrix.json"
PINS = "data/corpus_pins.json"
FEATURES = "data/features.json"
BENCHMARKS = "benchmarks/registry.json"
TARGET = ROOT / "docs" / "CORPUS_DEPTH.md"
PREFIX = "../"  # repository-relative paths; CORPUS_DEPTH.md sits in docs/

FEEDS, PLANNED, DEFERRED, RETIRED, UNPLANNED = ("feeds a scored task", "dated plan with named key",
                                                "deferred: needs feature", "retired", "UNPLANNED")
STATUS_ORDER = (FEEDS, PLANNED, DEFERRED, RETIRED, UNPLANNED)
SCORED = ("pass", "fail")
HAND_SET = ("status", "feeds", "scored", "evaluated")  # derived only; no registry record or disposition may assert them
# Key availability, verified from the group's own files, in the order the next-to-wire ranking prefers. Only the
# first is a key a toolkit task can be scored against; the second separates labels or structure that exist and can
# be checked but that no toolkit feature produces or consumes.
KEY = "verified key"
NOT_A_TASK_KEY = "verified, not a key for any toolkit task"
KEY_STATUSES = (KEY, NOT_A_TASK_KEY, "verified: labels not acquired", "verified: no key in source",
                "verified: withheld by publisher")
KEY_BLOCKED = KEY_STATUSES[2:]
VERIFIED_FIELDS = ("date", "file", "field", "count", "example")
EXAMPLE_MAX = 200  # a one-line example: a derived fact, never a copied passage
# A retirement is only for a group that can never qualify. A verified key with no consuming feature is DEFERRED.
RETIRE_KINDS = ("no usable key", "no area", "duplicate", "rights", "blocked")
# How a plan's key relates to what the tool is given: a separate file or a field withheld from the tool's input; the
# same layer the tool reads (a match checks reading, not understanding); or our own calculation over the input.
INDEPENDENCE = ("independent", "same-layer-as-input", "computed-from-input")
CAPABILITY_ID = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)+")

# Which existing matrix rows and features a group's acquisition categories could exercise once an adapter and a key
# exist. A candidate fit by category, not a verified applicability: it ranks what to wire next, nothing more.
# Every category used by a registry must appear here (an empty fit is an explicit "no existing feature").
CATEGORY_FIT = {
    "pid": ([1, 2, 3, 8], ["drawing-to-bundle", "drawing-set-to-bundle", "pid-port-review", "pid-path-review"]),
    "drawings": ([1, 3], ["drawing-to-bundle", "drawing-set-to-bundle"]),
    "electrical": ([], []),
    "scanned-documents": ([], ["document-text"]),
    "documents": ([], ["document-text", "one-map"]),
    "technical-documents": ([], ["document-text"]),
    "document-text": ([], ["document-text"]),
    "equipment-reference": ([], ["document-text"]),
    "context": ([], ["context-register"]),
    "historian": ([6], ["historian-csv"]),
    "process-measurements": ([6], ["historian-csv"]),
    "condition-monitoring": ([6], ["historian-csv"]),
    "historian-mapping": ([], ["review-and-mapping"]),
    "alarm-events": ([], []),
    "energy": ([], ["opportunity-screen", "impact-estimate"]),
    "opportunity-screen": ([], ["opportunity-screen"]),
    "maintenance": ([], ["maintenance-intake", "maintenance-history"]),
    "maintenance-context": ([], ["maintenance-history"]),
    "work-orders": ([], ["maintenance-intake", "maintenance-history"]),
    "parts-transactions": ([], ["maintenance-history"]),
    "labor": ([], ["maintenance-history"]),
    "parts": ([], []),
    "equipment-records": ([], ["photo-to-record", "one-map"]),
    "photo": ([], ["photo-to-record"]),
    "batch": ([], ["batch-analysis"]),
    "laboratory": ([], ["batch-analysis"]),
    "quality": ([], []),
    "manufacturing": ([], []),
    "process-model": ([5], ["description-to-model", "graph-export", "platform-exports"]),
    "flowsheets": ([5], ["description-to-model"]),
    "exchange-model": ([], ["dexpi-xml-to-model"]),
    "controls": ([4], ["loop-audit"]),
    "cad": ([], ["cad-handoff"]),
}

UNRESOLVED_TERMS = re.compile(r"unresolved|not established|conflicts|no open|copyright", re.I)
RECORD_TERMS = re.compile(r"public regulatory|public u\.s\.|public doe|federal|not separately cleared|"
                          r"individual review|local originals only", re.I)


def read_json(rel, root=ROOT):
    return json.loads((root / rel).read_bytes())


def text_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@functools.lru_cache(maxsize=None)
def tracked(root=ROOT):
    """Tracked repository paths; evidence must be committed, not merely present on this disk."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
        return frozenset(p for p in out.decode("utf-8").split("\0") if p)
    except (OSError, subprocess.CalledProcessError):
        return None  # no git: fall back to existence on disk


def is_tracked(rel, root=ROOT):
    paths = tracked(root)
    return (root / rel).is_file() if paths is None else rel in paths


def licence_status(text):
    """Licence/terms status from the acquisition record's own licence string."""
    if UNRESOLVED_TERMS.search(text):
        return "terms unresolved"
    if RECORD_TERMS.search(text):
        return "public record, rights retained, local only"
    return "open licence stated"


def load_groups(root=ROOT):
    """Every acquisition group: id -> (registry path, record). Duplicates across registries are problems."""
    groups, problems = {}, []
    for path in sorted(root.glob(REGISTRY_GLOB)):
        rel = path.relative_to(root).as_posix()
        for sid, record in json.loads(path.read_bytes())["sources"].items():
            if sid in groups:
                problems.append(f"{sid}: in both {groups[sid][0]} and {rel}")
            groups[sid] = (rel, record)
    return groups, problems


def load_sidecar(root=ROOT):
    return read_json(SIDECAR, root)


def registry_pin_problems(sidecar, root=ROOT):
    out = []
    pins = sidecar.get("registries", {})
    found = {p.relative_to(root).as_posix() for p in root.glob(REGISTRY_GLOB)}
    for rel in sorted(found - set(pins)):
        out.append(f"{rel}: not pinned in {SIDECAR} (read its records into dispositions, then pin its sha256)")
    for rel, digest in sorted(pins.items()):
        if rel not in found:
            out.append(f"{SIDECAR}: pins {rel}, which does not exist")
        elif text_hash(root / rel) != digest:
            out.append(f"{rel}: changed since {SIDECAR} pinned it; re-read its dispositions and update the pin "
                       "(acquisition registries are acquisition-time records and should not change)")
    return out


def goal_areas(groups, root=ROOT):
    """docs/DEPTH_GOAL.md area table -> ({group: area}, {area: candidate key}, problems)."""
    text = (root / GOAL).read_text(encoding="utf-8")
    areas, keys, problems = {}, {}, []
    rows = re.findall(r"^\| (?!Area |---)([^|]+?) \| ([^|]+?) \| ([^|]+?) \|$", text, re.M)
    if not rows:
        return areas, keys, [f"{GOAL}: no area table found"]
    by_registry = {}
    for sid, (rel, _) in groups.items():
        by_registry.setdefault(rel, []).append(sid)
    for area, cell, key in rows:
        keys[area] = key
        named = [t for t in re.findall(r"[a-z0-9][a-z0-9-]*[a-z0-9]", cell) if t in groups]
        m = re.search(r"the (\w+) pass-5 groups", cell)
        if m:
            fifth = by_registry.get("data/public_sources_20261107_round5.json", [])
            words = {"nine": 9, "ten": 10, "eight": 8}
            if words.get(m.group(1)) != len(fifth):
                problems.append(f"{GOAL}: '{m.group(0)}' but the pass-5 registry has {len(fifth)} groups")
            named += fifth
        for sid in named:
            if sid in areas:
                problems.append(f"{sid}: in two areas of {GOAL} ({areas[sid]}, {area})")
            areas[sid] = area
    for sid in sorted(set(groups) - set(areas)):
        problems.append(f"{sid}: acquired but in no area of {GOAL}")
    return areas, keys, problems


def linked_inputs(sid, corpus):
    """Corpus inputs that come from this group: its fetch command names it (wherever the input's local_path then
    lies, e.g. an agent-keyed folder built from the download), or a local_path segment is the group's folder."""
    out = []
    for inp in corpus["inputs"]:
        fetch = inp.get("fetch") or ""
        segments = (inp.get("local_path") or "").replace("\\", "/").split("/")
        named = re.search(r"(fetch_corpus\.py|fetch_sources\.py|--source)\s+" + re.escape(sid) + r"(\s|$|;|&)", fetch)
        if named or sid in segments:
            out.append(inp["id"])
    return out


def suite_paths(rel, root=ROOT, seen=None):
    """Every file path a registered suite's cases name, following referenced *.input.json files."""
    seen = set() if seen is None else seen
    if rel in seen or not (root / rel).is_file():
        return set()
    seen.add(rel)
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "path" and isinstance(v, str):
                    found.add(v.replace("\\", "/"))
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    doc = json.loads((root / rel).read_bytes())
    walk(doc.get("cases", doc) if isinstance(doc, dict) else doc)
    for p in sorted(found):
        if p.endswith(".input.json"):
            found |= suite_paths(p, root, seen)
    return found


def benchmark_suites(sid, root=ROOT):
    """Registered benchmark suites with a case file under this group's data/external folder."""
    base = f"data/external/{sid}"
    return [r["suite"] for r in read_json(BENCHMARKS, root)["reports"]
            if any(p == base or p.startswith(base + "/") for p in suite_paths(r["suite"], root))]


def row_features(features):
    """Matrix row -> features whose tools include one of the row's tool files."""
    return {row: sorted(f["id"] for f in features["features"] if set(f["tools"]) & set(tools))
            for row, tools in corpus_matrix.ROW_TOOL_FILES.items()}


def fit(categories):
    rows, feats = set(), set()
    for c in categories:
        r, f = CATEGORY_FIT.get(c, ([], []))
        rows.update(r)
        feats.update(f)
    return sorted(rows), sorted(feats)


def dated(value):
    try:
        return date.fromisoformat(value) <= date.today()
    except (TypeError, ValueError):
        return False


def squash(text):
    return " ".join(text.split())


def evidence_problems(sid, what, refs, root, registries, mention=None):
    """Each ref is `path#anchor`: the path must be tracked; a registry anchor must be this group's id; any other
    anchor must appear verbatim in the file. With mention, each file must also name the group (its id or a name)."""
    out = []
    if not refs:
        return [f"{sid}: {what} cites no evidence file"]
    for ref in refs:
        path, _, anchor = ref.partition("#")
        if not is_tracked(path, root):
            out.append(f"{sid}: {what} evidence {path} is not a tracked file")
            continue
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        if path in registries:
            if anchor != sid or sid not in json.loads(text)["sources"]:
                out.append(f"{sid}: {what} evidence {ref} must point at this group's own record ({path}#{sid})")
            continue
        if not anchor:
            out.append(f"{sid}: {what} evidence {path} needs a #quoted anchor from the file")
        elif squash(anchor) not in squash(text):
            out.append(f"{sid}: {what} evidence anchor {anchor!r} is not in {path}")
        if mention is not None and not any(term in text for term in mention):
            out.append(f"{sid}: {what} evidence {path} never names the group ({', '.join(mention)})")
    return out


def pinned_files(sid, root=ROOT):
    files = read_json(PINS, root).get(sid) or {}
    return {rel for rel, meta in files.items() if isinstance(meta, dict) and "sha256" in meta}


def verified_problems(sid, key, root=ROOT, own_tracked=()):
    """A key's `verified` record: every field present, a past ISO date, a one-line example, and a file that is a
    pinned file of this group (or a member of a pinned archive), or one of the group's own tracked files: its
    acquisition-time metadata snapshot or a file its disposition cites (own_tracked)."""
    v = key.get("verified")
    if not isinstance(v, dict):
        return [f"{sid}: key status needs a 'verified' record ({', '.join(VERIFIED_FIELDS)}) read from the source's "
                "own files"]
    out = [f"{sid}: verified record has no {f}" for f in VERIFIED_FIELDS if not str(v.get(f, "")).strip()]
    if v.get("date") and not dated(v["date"]):
        out.append(f"{sid}: verified date {v['date']!r} is not a past ISO date")
    example = str(v.get("example", ""))
    if len(example) > EXAMPLE_MAX or "\n" in example:
        out.append(f"{sid}: verified example must be one line of at most {EXAMPLE_MAX} characters")
    f = str(v.get("file", ""))
    if f and f.split("!", 1)[0] not in pinned_files(sid, root) and not (f in own_tracked and is_tracked(f, root)):
        out.append(f"{sid}: verified file {f!r} is neither a pinned file of this group in {PINS} nor the group's own "
                   "tracked snapshot or cited evidence")
    for i, c in enumerate(v.get("checks") or []):
        if not isinstance(c, dict) or c.get("reader") not in READERS or not isinstance(c.get("expect"), int) \
                or not str(c.get("path", "")).split("!", 1)[0] in pinned_files(sid, root):
            out.append(f"{sid}: verified check {i} needs a known reader ({', '.join(sorted(READERS))}), a pinned path "
                       "and an integer expect")
    return out


def split_problems(sid, plan):
    """A plan's development / held-out split, recorded before any result: held-out names at least one item, the two
    lists share none, and the split was decided no later than the plan."""
    sp = plan.get("split")
    if not isinstance(sp, dict):
        return [f"{sid}: plan needs a split (development, held_out, decided) recorded before any result"]
    dev, held = sp.get("development"), sp.get("held_out")
    out = []
    if not isinstance(dev, list) or not isinstance(held, list) or not held:
        out.append(f"{sid}: plan split needs a development list and a non-empty held_out list")
    elif set(dev) & set(held):
        out.append(f"{sid}: plan split puts {sorted(set(dev) & set(held))} in both development and held_out")
    if not dated(sp.get("decided")) or (dated(plan.get("date")) and sp["decided"] > plan["date"]):
        out.append(f"{sid}: plan split needs a past ISO 'decided' date no later than the plan date")
    return out


# ---------------------------------------------------------------------------------------------------------------------
# --reverify: recompute each key's cited counts from the pinned local bytes. Opt-in; never part of --check, because the
# acquired files are fetch-by-hash and absent from a fresh clone. Each reader takes the bytes of one file (an
# `archive!member[!member...]` path is opened inside the pinned archive) and the check's parameters.

def _text(data):
    return data.decode("utf-8-sig", errors="replace")


def _csv_rows(data, c):
    csv.field_size_limit(1 << 30)
    lines = _text(data).splitlines(keepends=True)[c.get("header_line", 0):]
    rows = list(csv.reader(io.StringIO("".join(lines))))
    return rows[0], [r for r in rows[1:] if r]


def _col(header, name):
    return header.index(name)


def _dxf_entities(data, c):
    lines = _text(data).splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    section, n = None, 0
    for i, (code, value) in enumerate(pairs):
        if code == "0" and value == "SECTION" and i + 1 < len(pairs):
            section = pairs[i + 1][1]
        elif section == "ENTITIES" and code == "0" and value == c["entity"]:
            n += 1
    return n


def _inp_section(data, c):
    n, current = 0, None
    for line in _text(data).splitlines():
        t = line.strip()
        if t.startswith("["):
            current = t
        elif current == c["section"] and t and not t.startswith(";"):
            n += 1
    return n


def _varint(b, i):
    shift = result = 0
    while True:
        byte = b[i]
        i += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return result, i


def _skip(b, i, t):
    """Skip one Thrift compact-protocol value of type t starting at b[i]."""
    if t in (1, 2):
        return i
    if t == 3:
        return i + 1
    if t in (4, 5, 6):
        return _varint(b, i)[1]
    if t == 7:
        return i + 8
    if t == 8:
        n, i = _varint(b, i)
        return i + n
    if t in (9, 10):
        head = b[i]
        i += 1
        n, et = head >> 4, head & 0x0F
        if n == 15:
            n, i = _varint(b, i)
        for _ in range(n):
            i = i + 1 if et in (1, 2) else _skip(b, i, et)
        return i
    if t == 11:
        n, i = _varint(b, i)
        if n:
            kv = b[i]
            i += 1
            for _ in range(n):
                i = _skip(b, i, kv >> 4)
                i = _skip(b, i, kv & 0x0F)
        return i
    if t == 12:
        while True:
            head = b[i]
            i += 1
            if head == 0:
                return i
            if not head >> 4:
                i = _varint(b, i)[1]
            i = _skip(b, i, head & 0x0F)
    raise ValueError(f"unknown thrift type {t}")


def _parquet_rows(data, c):
    """FileMetaData.num_rows (field 3) from the parquet footer, decoded with the Thrift compact protocol."""
    if data[-4:] != b"PAR1":
        raise ValueError("not a parquet file")
    n = int.from_bytes(data[-8:-4], "little")
    b, i, fid = data[-8 - n:-8], 0, 0
    while True:
        head = b[i]
        i += 1
        if head == 0:
            raise ValueError("num_rows not found")
        delta, t = head >> 4, head & 0x0F
        if delta:
            fid += delta
        else:
            z, i = _varint(b, i)
            fid = (z >> 1) ^ -(z & 1)
        if fid == 3 and t == 6:
            z, i = _varint(b, i)
            return (z >> 1) ^ -(z & 1)
        i = _skip(b, i, t)


def _fitz():
    import fitz  # PyMuPDF, optional (pdf_tag_check.py needs it too)
    return fitz


def _pdf(data):
    return _fitz().open(stream=data, filetype="pdf")


READERS = {
    "csv-rows": lambda d, c: len(_csv_rows(d, c)[1]),
    "csv-count": lambda d, c: (lambda h, r: sum(x[_col(h, c["column"])] == c["value"] for x in r))(*_csv_rows(d, c)),
    "csv-nonempty": lambda d, c: (lambda h, r: sum(bool(x[_col(h, c["column"])].strip()) for x in r))(*_csv_rows(d, c)),
    "lines": lambda d, c: sum(bool(x.strip()) for x in _text(d).splitlines()),
    "blocks": lambda d, c: len([x for x in re.split(r"\n\s*\n", _text(d).replace("\r\n", "\n")) if x.strip()]),
    "regex": lambda d, c: len(re.findall(c["pattern"], _text(d), re.M)),
    "json-len": lambda d, c: len(json.loads(_text(d))),
    "zip-members": lambda d, c: sum(not n.endswith("/") and n.lower().endswith(c.get("suffix", "").lower())
                                    for n in zipfile.ZipFile(io.BytesIO(d)).namelist()),
    "xlsx-sheets": lambda d, c: len(re.findall(r"<(?:\w+:)?sheet\b", _text(zipfile.ZipFile(io.BytesIO(d))
                                                                            .read("xl/workbook.xml")))),
    "dxf-entities": _dxf_entities,
    "inp-section": _inp_section,
    "parquet-rows": _parquet_rows,
    "pdf-pages": lambda d, c: _pdf(d).page_count,
    "pdf-text-chars": lambda d, c: sum(len(_pdf(d)[n - 1].get_text()) for n in c.get("pages") or
                                       range(1, _pdf(d).page_count + 1)),
    "pdf-pages-matching": lambda d, c: sum(bool(re.search(c["pattern"], pg.get_text())) for pg in _pdf(d)),
    "pdf-unique-matches": lambda d, c: len(set(re.findall(c["pattern"], _pdf(d)[c["page"] - 1].get_text()))),
}
OPTIONAL_READERS = {"pdf-pages", "pdf-text-chars", "pdf-pages-matching", "pdf-unique-matches"}


def pinned_bytes(sid, path, external, root=ROOT):
    """The bytes a check names, after the outer file's pinned sha256 is confirmed; nested archive members are opened
    by name, and a member missing from the archive's listing is an error."""
    parts = path.split("!")
    meta = (read_json(PINS, root).get(sid) or {}).get(parts[0]) or {}
    f = Path(external) / sid / parts[0]
    if not f.is_file():
        raise FileNotFoundError(f"{f} is not on this disk")
    data = f.read_bytes()
    if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
        raise ValueError(f"{f} does not match its pinned sha256")
    for member in parts[1:]:
        z = zipfile.ZipFile(io.BytesIO(data))
        if member not in z.namelist():
            raise KeyError(f"member {member!r} is not in the listing of {parts[0]}")
        data = z.read(member)
    return data


def reverify(rows, external, root=ROOT):
    """(lines, mismatches): every check's recomputed count against its expect, and each verified `archive!member`
    against the archive listing. Missing files and optional readers that are not installed are reported, not
    counted as mismatches."""
    lines, bad = [], []
    for r in rows:
        v = r["key"].get("verified") or {}
        targets = [dict(c) for c in v.get("checks") or []]
        if "!" in str(v.get("file", "")):
            targets.append({"reader": "member", "path": v["file"]})
        if not targets:
            lines.append(f"{r['id']}: no recomputable check recorded")
            continue
        for c in targets:
            label = f"{r['id']}: {c['reader']} {c['path']}" + (f" {c.get('page') or c.get('pattern') or c.get('column') or c.get('section') or c.get('entity') or ''}".rstrip())
            try:
                data = pinned_bytes(r["id"], c["path"], external, root)
                if c["reader"] == "member":
                    lines.append(f"ok   {label}: member present in the pinned archive")
                    continue
                got = READERS[c["reader"]](data, c)
            except ImportError:
                lines.append(f"skip {label}: optional reader not installed")
                continue
            except FileNotFoundError as e:
                lines.append(f"skip {label}: {e}")
                continue
            except Exception as e:  # noqa: BLE001 (a broken check is a mismatch, reported with its reason)
                bad.append(f"FAIL {label}: {type(e).__name__}: {e}")
                continue
            if got == c["expect"]:
                lines.append(f"ok   {label}: {got}")
            else:
                bad.append(f"FAIL {label}: recorded {c['expect']}, recomputed {got}")
    return lines, bad


def summary(cells):
    """Cells per row as status counts; input identifiers are left out of the page."""
    if not cells:
        return "none"
    by_row = {}
    for c in cells:
        by_row.setdefault(c["row"], Counter())[c["status"]] += 1
    return "; ".join(f"{row_label(r)}: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
                     for r, counts in sorted(by_row.items()))


def build(root=ROOT):
    """All rows, the earlier pinned sources, and every rule problem."""
    groups, problems = load_groups(root)
    sidecar = load_sidecar(root)
    registries = set(sidecar.get("registries", {}))
    problems += registry_pin_problems(sidecar, root)
    dispositions = sidecar.get("groups", {})
    problems += [f"{sid}: in {SIDECAR} but in no acquisition registry" for sid in sorted(set(dispositions) - set(groups))]
    areas, area_keys, area_problems = goal_areas(groups, root)
    problems += area_problems
    corpus, matrix = read_json(CORPUS, root), read_json(MATRIX, root)
    stale = corpus_matrix.stale_cells(matrix, corpus)
    if stale:
        problems.append(f"{MATRIX}: {len(stale)} cells are stale against {CORPUS} or their tools (run "
                        "python scripts/corpus_matrix.py --check): " + "; ".join(stale[:5]))
    inputs_by_id = corpus_matrix.inputs_by_id(corpus)
    features = read_json(FEATURES, root)
    feature_ids = {f["id"] for f in features["features"]}
    by_row = row_features(features)
    cells = {}
    for c in matrix["cells"]:
        cells.setdefault(c["input"], []).append(c)
    for cat, (rows, feats) in CATEGORY_FIT.items():
        problems += [f"CATEGORY_FIT {cat}: unknown matrix row {r}" for r in rows if r not in corpus_matrix.ROWS]
        problems += [f"CATEGORY_FIT {cat}: unknown feature {f}" for f in feats if f not in feature_ids]

    def counts_as_scored(c):
        inp = inputs_by_id.get(c["input"], {})
        return (c["status"] in SCORED and not corpus_matrix.self_generated(c) and not corpus_matrix.self_generated(inp)
                and not corpus_matrix.agent_keyed(c) and not corpus_matrix.agent_keyed(inp))

    def feeding(sid):
        inputs = linked_inputs(sid, corpus)
        found = [c for i in inputs for c in sorted(cells.get(i, []), key=lambda c: c["row"])]
        return inputs, found, benchmark_suites(sid, root)

    out = []
    for sid, (rel, rec) in groups.items():
        depth = dispositions.get(sid)
        if depth is None:
            problems.append(f"{sid}: no entry in {SIDECAR} (verify its key from its own files first)")
            depth = {}
        for word in HAND_SET:
            if word in rec:
                problems.append(f"{sid}: registry field {word!r} is derived here, never asserted by a record")
            if word in depth or word in (depth.get("plan") or {}):
                problems.append(f"{sid}: {word} is derived from the matrix and benchmarks, never set by hand")
        for cat in rec.get("categories", []):
            if cat not in CATEGORY_FIT:
                problems.append(f"{sid}: category {cat!r} has no CATEGORY_FIT entry in scripts/corpus_depth.py")
        key = depth.get("key")
        if not key:
            problems.append(f"{sid}: no key availability in {SIDECAR}")
            key = {"status": "unknown", "what": "", "evidence": []}
        elif key.get("status") not in KEY_STATUSES:
            problems.append(f"{sid}: key status {key.get('status')!r} not one of {', '.join(KEY_STATUSES)}")
        else:
            refs = key.get("evidence") or []
            if f"{rel}#{sid}" not in refs:
                problems.append(f"{sid}: key availability must cite its acquisition record {rel}#{sid}")
            problems += evidence_problems(sid, "key", refs, root, registries)
            own = {rec.get("metadata_snapshot")} | {e.partition("#")[0] for d in ("plan", "deferred", "retired")
                                                     for e in (depth.get(d) or {}).get("evidence") or []}
            problems += verified_problems(sid, key, root, own - {None})
        plan, deferred, retired = depth.get("plan"), depth.get("deferred"), depth.get("retired")
        if sum(bool(x) for x in (plan, deferred, retired)) > 1:
            problems.append(f"{sid}: more than one of a plan, a deferral and a retirement")
        names = None
        for what, entry in (("plan", plan), ("deferred", deferred), ("retired", retired)):
            if not entry:
                continue
            names = [sid] + list(entry.get("names") or [])
            for n in entry.get("names") or []:
                if n not in rec.get("name", "") and n not in rec.get("source_family", ""):
                    problems.append(f"{sid}: {what} name {n!r} is not in the acquisition record's name or family")
            problems += evidence_problems(sid, what, entry.get("evidence") or [], root, registries, mention=names)
        plan_ok = bool(plan) and dated(plan.get("date")) and bool(plan.get("key")) and bool(plan.get("task"))
        if plan and not plan_ok:
            problems.append(f"{sid}: plan needs a past ISO date, the key and the task")
        if plan:
            plan_problems = split_problems(sid, plan)
            if plan.get("feature") not in feature_ids:
                plan_problems.append(f"{sid}: plan feature {plan.get('feature')!r} is not a feature in {FEATURES}")
            if key.get("status") != KEY:
                plan_problems.append(f"{sid}: plan needs key status {KEY!r}, not {key.get('status')!r}")
            if key.get("independence") not in INDEPENDENCE:
                plan_problems.append(f"{sid}: plan needs key independence, one of {', '.join(INDEPENDENCE)}")
            if not str(plan.get("exposure", "")).strip():
                plan_problems.append(f"{sid}: plan needs an exposure statement: what of the held-out key was read, "
                                     "when, and that no method ran (or that nothing was read)")
            problems += plan_problems
            plan_ok = plan_ok and not plan_problems
        deferred_ok = False
        if deferred:
            feat = deferred.get("feature") or {}
            dp = []
            if not dated(deferred.get("date")):
                dp.append(f"{sid}: deferred needs a past ISO date")
            if key.get("status") != NOT_A_TASK_KEY:
                dp.append(f"{sid}: deferred needs key status {NOT_A_TASK_KEY!r} (a verified key no feature consumes), "
                          f"not {key.get('status')!r}")
            if not CAPABILITY_ID.fullmatch(str(feat.get("id", ""))) or feat.get("id") in feature_ids:
                dp.append(f"{sid}: deferred feature id {feat.get('id')!r} must be a new hyphenated capability id, not "
                          f"an existing feature in {FEATURES}")
            if not str(feat.get("description", "")).strip() or "\n" in str(feat.get("description", "")):
                dp.append(f"{sid}: deferred feature needs a one-line description")
            if deferred.get("area") != areas.get(sid):
                dp.append(f"{sid}: deferred area {deferred.get('area')!r} is not the group's area {areas.get(sid)!r}")
            problems += dp
            deferred_ok = not dp
        if retired and not retired.get("reason"):
            problems.append(f"{sid}: retired needs a reason")
        if retired and retired.get("kind") not in RETIRE_KINDS:
            problems.append(f"{sid}: retirement kind {retired.get('kind')!r} not one of {', '.join(RETIRE_KINDS)}"
                            + (" (a verified key no feature consumes is deferred, not retired)"
                               if retired.get("kind") == "no toolkit task" else ""))
        if retired and key.get("status") == KEY:
            problems.append(f"{sid}: retired with a {KEY!r} that fits a toolkit task: plan it instead")
        if retired and retired.get("kind") == "no usable key" and key.get("status") not in KEY_BLOCKED:
            problems.append(f"{sid}: retired as 'no usable key' but its key status is {key.get('status')!r}; a "
                            "verified key no feature consumes is deferred, not retired")
        inputs, found, suites = feeding(sid)
        scored = [c for c in found if counts_as_scored(c)]
        if retired and (scored or suites):
            problems.append(f"{sid}: retired but still feeds {len(scored)} scored cells / {len(suites)} suites")
        if deferred and (scored or suites):
            problems.append(f"{sid}: deferred but feeds {len(scored)} scored cells / {len(suites)} suites: plan it")
        if rec.get("evidence_role", "acquired-unscored") != "acquired-unscored" and not (scored or suites):
            problems.append(f"{sid}: evidence_role {rec['evidence_role']!r} claims evaluation that no scored matrix "
                            "cell or registered benchmark backs")
        status = (RETIRED if retired else FEEDS if (scored or suites) else PLANNED if plan_ok
                  else DEFERRED if deferred_ok else UNPLANNED)
        cats = rec.get("categories", [])
        fit_rows, fit_feats = fit(cats)
        out.append({
            "id": sid, "registry": rel, "family": rec.get("source_family", sid),
            "area": areas.get(sid, "?"), "area_key": area_keys.get(areas.get(sid), ""),
            "licence": licence_status(rec.get("license", "")), "origin": rec.get("origin", ""), "categories": cats,
            "key": key, "plan": plan, "deferred": deferred, "retired": retired, "note": depth.get("note", ""), "inputs": inputs,
            "cells": found, "scored": scored, "suites": suites,
            "features": sorted({f for c in scored for f in by_row.get(c["row"], [])}),
            "fit_rows": fit_rows, "fit_features": fit_feats, "status": status})
    earlier = []
    for sid in read_json(PINS, root):
        if sid == "about" or sid in groups:
            continue
        inputs, found, suites = feeding(sid)
        scored = [c for c in found if counts_as_scored(c)]
        earlier.append({"id": sid, "inputs": inputs, "cells": found, "scored": scored, "suites": suites,
                        "features": sorted({f for c in scored for f in by_row.get(c["row"], [])})})
    return out, earlier, problems


def ranked(rows):
    """UNPLANNED groups by the existing features they could exercise, then key availability, then open licence.

    A group whose own record says it has no key, or whose publisher withholds it, cannot feed a scored task however
    many features it fits, so it ranks after every group that may have one."""
    pool = [r for r in rows if r["status"] == UNPLANNED]
    return sorted(pool, key=lambda r: (r["key"]["status"] in KEY_BLOCKED, -len(r["fit_features"]), -len(r["fit_rows"]),
                                       KEY_STATUSES.index(r["key"]["status"]) if r["key"]["status"] in KEY_STATUSES
                                       else len(KEY_STATUSES), r["licence"] != "open licence stated", r["id"]))


def esc(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def link(ref, prefix=PREFIX):
    base = ref.split("#", 1)[0]
    return f"[{Path(base).name}]({prefix}{base})"


def row_label(n):
    return f"row {n} {corpus_matrix.ROWS[n]['short']}"


def fit_text(r):
    rows = ", ".join(row_label(n) for n in r["fit_rows"]) or "no matrix row"
    return f"{rows}; features {', '.join(r['fit_features']) or 'none'}"


def status_text(r):
    text = f"**{r['status']}**" if r["status"] == UNPLANNED else r["status"]
    if r["status"] == PLANNED and r["plan"].get("open"):
        text += f" ({r['plan']['open']})"
    return text


def disposition_text(r, prefix=PREFIX):
    if r["status"] == PLANNED:
        p = r["plan"]
        ev = ", ".join(link(e, prefix) for e in p["evidence"])
        sp = p["split"]
        split = (f"split decided {sp['decided']}: development {'; '.join(sp['development']) or 'none'}; "
                 f"held out {'; '.join(sp['held_out'])}")
        text = (f"{p['date']}: key {p['key']}; task {p['task']} (feature {p['feature']}); {split}; exposure: "
                f"{p['exposure']} ({ev})")
        return text + (f". {p['note']}" if p.get("note") else "")
    if r["status"] == RETIRED:
        return (f"{r['retired'].get('kind')}: {r['retired']['reason']} ("
                + ", ".join(link(e, prefix) for e in r["retired"]["evidence"]) + ")")
    if r["status"] == DEFERRED:
        d = r["deferred"]
        return (f"{d['date']}: needs {d['feature']['id']} ({d['feature']['description']}). {d.get('note', '')}".rstrip()
                + " (" + ", ".join(link(e, prefix) for e in d["evidence"]) + ")")
    if r["status"] == FEEDS:
        return "scored through " + (summary(r["scored"]) if r["scored"] else ", ".join(r["suites"]))
    return r["note"] or "no plan, key or retirement recorded"


def key_text(r):
    k = r["key"]
    v = k.get("verified") or {}
    text = f"{k['status']}: {k['what']}"
    if k.get("independence"):
        text += f" (independence: {k['independence']})"
    if v:
        text += f" [read {v.get('date')}: {v.get('file')}, {v.get('field')}; {v.get('count')}; e.g. {v.get('example')}]"
    return text


def page(rows, earlier, prefix=PREFIX):
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUS_ORDER}
    disposed = len(rows) - counts[UNPLANNED]
    unplanned = [r for r in rows if r["status"] == UNPLANNED]
    done = ("Increment 1 is done" if not unplanned else "Increment 1 is not done")
    lines = [
        "# Corpus depth: every acquired source group and its disposition", "",
        f"*Generated by `scripts/corpus_depth.py` from the acquisition registries (`{REGISTRY_GLOB}`, read only and "
        f"hash-pinned), the dispositions in [corpus_depth.json]({prefix}{SIDECAR}), [{Path(GOAL).name}]"
        f"({prefix}{GOAL}) (areas), [corpus.json]({prefix}{CORPUS}) and [matrix.json]({prefix}{MATRIX}) (what each "
        f"group feeds), [registry.json]({prefix}{BENCHMARKS}) and [features.json]({prefix}{FEATURES}). Edit those, "
        "then run `python scripts/corpus_depth.py --write`; `--check` runs in the test suite.*", "",
        f"The standing goal ([DEPTH_GOAL.md]({prefix}{GOAL})): before any further acquisition, every acquired "
        "source either feeds a scored task through the product path, or has a dated plan naming its key, or is "
        "retired with its reason. The status below is derived, not typed: **feeds** needs a scored matrix cell "
        "(pass or fail, not self-generated or agent-keyed) or a registered benchmark; **planned** needs a dated plan "
        "with a verified key, its task, an existing feature, a development/held-out split recorded before any "
        "result, and quoted evidence; **retired** needs a reason of a named kind with evidence. Everything else is "
        "**UNPLANNED**.", "",
        f"**{len(rows)} groups: {counts[FEEDS]} feed a scored task, {counts[PLANNED]} have a dated plan with a "
        f"named key, {counts[RETIRED]} retired, {counts[UNPLANNED]} UNPLANNED. {done}: "
        f"{disposed} of {len(rows)} groups have a disposition.**", "",
        "Key availability is verified from each group's own acquired files: the file, the field or column, a count "
        "and a one-line example, with the date read. *verified key* means a key exists, can be checked and fits a "
        "toolkit task; *verified, not a key for any toolkit task* means labels or structure exist and can be "
        "checked, but no toolkit feature produces or consumes them.", "",
        "| Key availability (verified) | Groups |", "|---|---|"]
    lines += [f"| {s} | {sum(r['key']['status'] == s for r in rows)} |" for s in KEY_STATUSES]
    lines += ["", "| Area | " + " | ".join(STATUS_ORDER) + " |", "|---|" + "---|" * len(STATUS_ORDER)]
    for area in sorted({r["area"] for r in rows}):
        n = [sum(r["area"] == area and r["status"] == s for r in rows) for s in STATUS_ORDER]
        lines.append(f"| {esc(area)} | " + " | ".join(str(x) for x in n) + " |")
    lines += ["", "| Retirement kind | Groups |", "|---|---|"]
    lines += [f"| {k} | {sum(bool(r['retired']) and r['retired'].get('kind') == k for r in rows)} |"
              for k in RETIRE_KINDS]
    lines += [
        "", f"## UNPLANNED: {len(unplanned)} of {len(rows)}", "",
        "No new acquisition pass while this list is not empty (`python scripts/corpus_depth.py --strict` fails "
        "until it is).", "",
        ", ".join(f"`{r['id']}`" for r in sorted(unplanned, key=lambda r: (r["area"], r["id"]))) or "None.", "",
        "## Next to wire: the ten highest-value UNPLANNED groups", "",
        "Ranked by how many existing features the group's acquisition categories could exercise, then by the "
        "matrix rows, then by key availability, then open licence. A group whose verified key is missing, not "
        "acquired or withheld ranks after all the others: it cannot feed a scored task until someone authors a "
        "key. The fit is by category: a candidate, not a verified applicability.", ""]
    top = ranked(rows)[:10]
    if top:
        lines += ["| # | Group | Area | Could exercise (matrix row / features) | Key availability | Licence |",
                  "|---|---|---|---|---|---|"]
        for n, r in enumerate(top, 1):
            lines.append(f"| {n} | `{r['id']}` | {esc(r['area'])} | {esc(fit_text(r))} | "
                         f"{esc(r['key']['status'])}: {esc(r['key']['what'])} | {esc(r['licence'])} |")
    else:
        lines.append("None: every group has a disposition. The planned groups below are what to wire next.")
    planned = sorted((r for r in rows if r["status"] == PLANNED), key=lambda r: (r["area"], r["id"]))
    lines += ["", f"### Planned groups and their verified keys: {len(planned)}", "",
              "Each plan names an existing feature, the key and the split; the split was recorded before any result "
              "and must not change once a held-out item is scored. A plan is not depth (DEPTH_GOAL.md).", "",
              "| Group | Area | Feature | Key independence | Key (verified) | Development | Held out | Exposure |",
              "|---|---|---|---|---|---|---|---|"]
    for r in planned:
        sp = r["plan"]["split"]
        lines.append(f"| `{r['id']}` | {esc(r['area'])} | {esc(r['plan']['feature'])} | "
                     f"{esc(r['key'].get('independence'))} | {esc(key_text(r))} | "
                     f"{esc('; '.join(sp['development']) or 'none')} | {esc('; '.join(sp['held_out']))} | "
                     f"{esc(r['plan']['exposure'])} |")
    deferred = sorted((r for r in rows if r["status"] == DEFERRED), key=lambda r: (r["area"], r["id"]))
    lines += ["", f"### Deferred: a verified key waits for a feature: {len(deferred)}", "",
              "These count as disposed for increment 1 but are not retirements: each has a checkable key, and no "
              "toolkit feature yet produces or consumes it. Each names the capability it waits for. Building one "
              "turns its group into a plan.", "",
              "| Group | Area | Needs (new capability) | Key (verified) |", "|---|---|---|---|"]
    for r in deferred:
        f = r["deferred"]["feature"]
        lines.append(f"| `{r['id']}` | {esc(r['area'])} | {esc(f['id'])}: {esc(f['description'])} | "
                     f"{esc(key_text(r))} |")
    lines += ["", "## The register", "",
              "One row per acquisition group. *Feeds now* counts the matrix cells of the group's corpus inputs by "
              "row and status; *features* are those whose tools the scored rows run. *What it is* is the "
              "acquisition record's origin and categories. *Key availability* gives the verified status and what "
              "was read: file, field or column, count and a one-line example.", "",
              "| Group | Family | Area | Licence / terms | What it is | Feeds now (matrix cells; features) | "
              "Key availability | Status | Disposition |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["area"], STATUS_ORDER.index(r["status"]), r["id"])):
        feeds = summary(r["cells"]) + (f"; suites {', '.join(r['suites'])}" if r["suites"] else "")
        if r["features"]:
            feeds += f"; features {', '.join(r['features'])}"
        lines.append(
            f"| `{r['id']}` | {esc(r['family'])} | {esc(r['area'])} | {esc(r['licence'])} | "
            f"{esc(r['origin'])}; {esc(', '.join(r['categories']))} | {esc(feeds)} | {esc(key_text(r))} | "
            f"{status_text(r)} | {esc(disposition_text(r, prefix))} |")
    lines += ["", "## Earlier pinned sources (outside the 49-group goal)", "",
              f"Sources pinned in [corpus_pins.json]({prefix}{PINS}) before the 2026-11-07 passes, by their dataset "
              "identifiers. They are listed so the feeding rule above is seen to find real matrix cells; they carry "
              "no disposition here. *Scored* counts the cells that would make a group feed (pass or fail, not "
              "agent-keyed or self-generated).", "",
              "| Source | Corpus inputs | Matrix cells | Scored | Features |", "|---|---|---|---|---|"]
    for e in earlier:
        lines.append(f"| `{e['id']}` | {len(e['inputs'])} | {esc(summary(e['cells']))} | {len(e['scored'])} | "
                     f"{esc(', '.join(e['features']) or 'none')} |")
    lines += ["", "## Limits", "",
              "- Areas come from the DEPTH_GOAL table. Key availability was read from each group's own acquired "
              "files on the date shown; those files are fetch-by-hash and are not in the repository, so --check "
              "verifies the record's shape and that it cites a pinned file, not the count itself. `--reverify` "
              "recomputes the recorded checks from the pinned local bytes (PDF checks need PyMuPDF; PDF character "
              "counts are PyMuPDF get_text lengths, not layout-padded text). Counts without a recorded check are "
              "dated readings only.",
              "- Pahala is the exception: its key record comes from the development record (data/attempts.json "
              "A404) so that no held-out sheet is opened.",
              "- A dated plan is not depth: depth is the six checks in DEPTH_GOAL.md. Development runs on a planned "
              "group (the plan's note) are not a sealed held-out result.",
              "- A retirement is a disposition, not a verdict on the source: a later feature can reopen a retired "
              "group with a new plan.",
              "- The next-to-wire fit is a category match. It does not say an adapter exists or that the result "
              "would hold.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="write docs/CORPUS_DEPTH.md")
    ap.add_argument("--check", action="store_true", help="exit 1 on a broken rule or a stale docs/CORPUS_DEPTH.md")
    ap.add_argument("--strict", action="store_true", help="--check, and exit 1 while any group is UNPLANNED")
    ap.add_argument("--reverify", action="store_true",
                    help="recompute each key's recorded checks from the pinned local bytes; exit 1 on a mismatch")
    ap.add_argument("--external", default=str(ROOT / "data" / "external"),
                    help="folder holding <group>/<pinned file> (default data/external)")
    a = ap.parse_args(argv)
    if a.write and (a.check or a.strict):
        ap.error("--write cannot be combined with --check or --strict")
    rows, earlier, bad = build()
    text = page(rows, earlier)
    if a.reverify:
        lines, mismatches = reverify(rows, a.external)
        print("\n".join(lines + mismatches))
        print(f"reverify: {sum(x.startswith('ok') for x in lines)} ok, {sum(x.startswith('skip') for x in lines)} "
              f"skipped, {len(mismatches)} mismatched, "
              f"{sum(x.endswith('no recomputable check recorded') for x in lines)} groups without a check")
        if mismatches or not (a.check or a.strict):
            return 1 if mismatches else 0
    if a.check or a.strict:
        current = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n") if TARGET.exists() else None
        if current != text:
            bad.append("docs/CORPUS_DEPTH.md is stale or missing: run python scripts/corpus_depth.py --write")
        if a.strict:
            bad += [f"{r['id']}: UNPLANNED" for r in rows if r["status"] == UNPLANNED]
        print("\n".join(bad) if bad else "corpus depth: rules hold and docs/CORPUS_DEPTH.md is current")
        return 1 if bad else 0
    if bad:
        print("\n".join(bad))
        return 1
    if a.write:
        TARGET.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {TARGET.relative_to(ROOT).as_posix()}")
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUS_ORDER}
    print(", ".join(f"{s}: {n}" for s, n in counts.items()))
    print("UNPLANNED:", " ".join(r["id"] for r in rows if r["status"] == UNPLANNED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
