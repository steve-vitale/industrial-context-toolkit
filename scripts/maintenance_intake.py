"""Prepare explicitly mapped equipment/work-order CSVs and a sourced, offline manager review packet."""
import argparse
import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import tempfile
from pathlib import Path

import one_map
import map_changes

SCHEMA = "maintenance-intake-1"
FIELDS = {
    "equipment": {"tag", "unit", "description", "class", "manufacturer", "model", "serial_number", "size"},
    "work_orders": {"work_order", "tag", "unit", "closed_on", "description", "installed_manufacturer", "installed_model", "installed_serial_number", "installed_size"},
}
REQUIRED = {"equipment": {"tag", "unit"}, "work_orders": {"work_order", "tag", "unit", "closed_on"}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def date(value, where, pattern="%Y-%m-%d"):
    try:
        parsed = dt.datetime.strptime(value, pattern).date()
        if parsed.strftime(pattern) != value:
            raise ValueError("noncanonical date")
        return parsed.isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"{where}: date {value!r} must use declared {pattern}; no locale guessed") from None


def profile_check(p):
    if not isinstance(p, dict) or p.get("schema") != SCHEMA:
        raise ValueError(f"profile needs schema {SCHEMA}")
    for key in ("site", "plant"):
        if not isinstance(p.get(key), str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", p[key]):
            raise ValueError(f"profile {key}: supply one explicit namespace component")
    units = p.get("units")
    if not isinstance(units, list) or not units or any(
            not isinstance(u, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", u) for u in units) or len(set(units)) != len(units):
        raise ValueError("profile units: supply unique, explicit namespace components")
    date(p.get("as_of"), "profile as_of")
    for kind in FIELDS:
        s = p.get(kind, {})
        if not isinstance(s, dict):
            raise ValueError(f"{kind}: supply an export specification object")
        for key in ("id", "revision", "owner", "coverage"):
            if not isinstance(s.get(key), str) or not s[key].strip():
                raise ValueError(f"{kind}.{key}: explicitly describe source, revision, owner and export coverage")
        if "/" in s["id"] or "\\" in s["id"]:
            raise ValueError(f"{kind}.id: use a document ID without path separators")
        mapping = s.get("columns", {})
        if not isinstance(mapping, dict) or not mapping or any(not isinstance(k, str) or not k or not isinstance(v, str) for k, v in mapping.items()):
            raise ValueError(f"{kind}.columns: supply source header to canonical field mapping")
        if len(set(mapping.values())) != len(mapping) or not REQUIRED[kind] <= set(mapping.values()) or set(mapping.values()) - FIELDS[kind]:
            raise ValueError(f"{kind}.columns: duplicate/unsupported targets or missing {sorted(REQUIRED[kind])}")
        ignored = s.get("ignored_columns", [])
        if not isinstance(ignored, list) or any(not isinstance(x, str) for x in ignored) or len(set(ignored)) != len(ignored) or set(ignored) & set(mapping):
            raise ValueError(f"{kind}.ignored_columns: list disjoint source headers explicitly")
        if s.get("delimiter", ",") not in (",", ";", "\t", "|"):
            raise ValueError(f"{kind}.delimiter: supported values are comma, semicolon, tab or pipe")
        if s.get("encoding", "utf-8-sig") not in ("utf-8", "utf-8-sig", "cp1252"):
            raise ValueError(f"{kind}.encoding: explicitly select utf-8, utf-8-sig or cp1252")
        if s.get("date_format", "%Y-%m-%d") not in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            raise ValueError(f"{kind}.date_format: unsupported pattern")
    if p["equipment"]["id"] == p["work_orders"]["id"]:
        raise ValueError("source document IDs must be distinct")


def read_rows(raw, kind, p):
    spec = p[kind]
    try:
        stream = io.StringIO(raw.decode(spec.get("encoding", "utf-8-sig")), newline="")
    except UnicodeError as error:
        raise ValueError(f"{kind}: encoding mismatch: {error}") from None
    reader = csv.reader(stream, delimiter=spec.get("delimiter", ","), strict=True)
    headers = next(reader, [])
    if not headers or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
        raise ValueError(f"{kind}: blank/duplicate/missing CSV headers")
    if set(headers) != set(spec["columns"]) | set(spec.get("ignored_columns", [])):
        raise ValueError(f"{kind}: headers differ from mapping plus explicitly ignored columns: {headers}")
    result, origins, seen = [], [], set()
    for ordinal, cells in enumerate(reader, 2):
        end_line = reader.line_num
        if len(cells) != len(headers):
            raise ValueError(f"{kind} record {ordinal}: expected {len(headers)} fields, got {len(cells)}")
        row = dict(zip(headers, cells))
        r = {target: row[source].strip() for source, target in spec["columns"].items()}
        if not r["tag"] or "/" in r["tag"] or "\\" in r["tag"] or r["unit"] not in p["units"]:
            raise ValueError(f"{kind} record {ordinal}: missing/invalid tag or unknown unit; no identity guessed")
        identity = (r["unit"], r["tag"]) if kind == "equipment" else (r["unit"], r["tag"], r["work_order"])
        if identity in seen or (kind == "work_orders" and not r["work_order"]):
            raise ValueError(f"{kind} record {ordinal}: duplicate/blank record identity {identity}; reconcile rows first")
        seen.add(identity)
        if kind == "work_orders" and r["closed_on"]:
            r["closed_on"] = date(r["closed_on"], f"{kind} record {ordinal}", spec.get("date_format", "%Y-%m-%d"))
            if r["closed_on"] > p["as_of"]:
                raise ValueError(f"{kind} record {ordinal}: closure after as_of; do not treat future installation as present")
        r["plant"] = p["plant"]
        r["locator"] = f"original {kind}.csv CSV record {ordinal} (ends at physical line {end_line})"
        result.append(r)
        origins.append({"prepared": kind + ".csv", "prepared_record": ordinal, "original": f"originals/{kind}.csv",
                        "original_record": ordinal, "original_end_line": end_line, "source_id": spec["id"],
                        "revision": spec["revision"], "item": "/".join((p["site"], p["plant"], r["unit"], r["tag"]))})
    if not result:
        raise ValueError(f"{kind}: empty export; cannot claim a comparable record scope")
    return result, origins


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*")) if p.is_file() and p != root / "receipt.json"}


def verify_packet(root):
    root = Path(root).resolve()
    r = load(root / "receipt.json")
    if not isinstance(r, dict) or r.get("schema") != "maintenance-packet-1" or r.get("files") != inventory(root):
        raise ValueError("previous packet inventory differs; retain it and investigate before comparing")
    return r


def binding(p):
    # Format/header mappings may change between exports. Scope and source authority may not silently change.
    return {"site": p["site"], "plant": p["plant"], "units": sorted(p["units"]),
            "sources": {k: {x: p[k][x] for x in ("id", "owner", "coverage")} for k in FIELDS}}


def findings(graph):
    return [n["conflict"] for n in graph["nodes"] if n["kind"] == "conflict"]


def method_pins():
    """Inventory the loaded local implementation, as in the original packet receipt."""
    scripts = Path(__file__).resolve().parent
    modules = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, "__file__", None)
               and Path(m.__file__).resolve().parent == scripts and Path(m.__file__).suffix == ".py"}
    modules.add(Path(__file__).resolve())
    return {m.name: hashlib.sha256(m.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for m in sorted(modules)}


def interpretation(spec):
    return {"columns": spec["columns"], "ignored_columns": sorted(spec.get("ignored_columns", [])),
            "delimiter": spec.get("delimiter", ","), "encoding": spec.get("encoding", "utf-8-sig"),
            "date_format": spec.get("date_format", "%Y-%m-%d")}


def row_index(rows, origins, kind):
    mapped = {o["prepared_record"]: o for o in origins if o["prepared"] == kind + ".csv"}
    result = {}
    for n, row in enumerate(rows, 2):
        identity = [row["plant"], row["unit"], row["tag"]]
        if kind == "work_orders":
            identity.append(row["work_order"])
        key = tuple(identity)
        if key in result:
            raise ValueError(f"{kind}: previous/current normalized rows have duplicate identity {identity}")
        result[key] = {"identity": identity, "values": {k: v for k, v in row.items() if k != "locator"},
                       "origin": mapped.get(n)}
    return result


def comparison_basis(p, rows, origins, raw, pins, previous=None, previous_receipt=None):
    basis = {"schema": "maintenance-comparison-basis-1", "status": "initial", "changed_methods": [],
             "interpretation_changes": [], "python_change": None, "as_of_change": None,
             "unknown_prior_basis": [], "sources": [],
             "previous_receipt_sha256": sha(previous / "receipt.json") if previous else None,
             "meaning": "Recorded basis and export changes, not acceptance, physical change or proof of complete source coverage. Review disappeared findings against this basis."}
    if not previous:
        return basis
    oldp = load(previous / "originals/profile.json")
    oldpins = previous_receipt.get("methods_sha256_lf")
    if not isinstance(oldpins, dict) or not oldpins or any(not isinstance(k, str) or not isinstance(v, str)
                                                        or not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in oldpins.items()):
        basis["unknown_prior_basis"].append("Previous method pins are missing or invalid; method continuity is unknown")
    else:
        basis["changed_methods"] = sorted(k for k in set(oldpins) | set(pins) if oldpins.get(k) != pins.get(k))
    old_python = previous_receipt.get("python")
    if not isinstance(old_python, str) or not old_python:
        basis["unknown_prior_basis"].append("Previous Python version is missing; runtime continuity is unknown")
    elif old_python != sys.version:
        basis["python_change"] = {"before": old_python, "after": sys.version}
    if oldp["as_of"] != p["as_of"]:
        basis["as_of_change"] = {"before": oldp["as_of"], "after": p["as_of"]}
    oldorigins = load(previous / "prepared/row-origins.json")
    for kind in FIELDS:
        oldmeaning, meaning = interpretation(oldp[kind]), interpretation(p[kind])
        if oldmeaning != meaning:
            basis["interpretation_changes"].append({"source": kind, "before": oldmeaning, "after": meaning})
        with (previous / f"prepared/{kind}.csv").open(encoding="utf-8", newline="") as f:
            oldrows = list(csv.DictReader(f))
        before, after = row_index(oldrows, oldorigins, kind), row_index(rows[kind], origins, kind)
        prior_keys, keys = set(before), set(after)
        basis["sources"].append({"source": kind, "id": p[kind]["id"],
            "before_revision": oldp[kind]["revision"], "after_revision": p[kind]["revision"],
            "bytes_changed": sha(previous / f"originals/{kind}.csv") != hashlib.sha256(raw[kind]).hexdigest(),
            "before_rows": len(before), "after_rows": len(after),
            "added_records": [after[k] for k in sorted(keys - prior_keys)],
            "removed_records": [before[k] for k in sorted(prior_keys - keys)],
            "changed_records": [{"identity": list(k), "before": before[k]["values"], "after": after[k]["values"],
                                 "before_origin": before[k]["origin"], "after_origin": after[k]["origin"]}
                                for k in sorted(keys & prior_keys) if before[k]["values"] != after[k]["values"]]})
    changed = (basis["changed_methods"] or basis["interpretation_changes"] or basis["unknown_prior_basis"]
               or basis["python_change"] or basis["as_of_change"]
               or any(s["bytes_changed"] or s["before_revision"] != s["after_revision"] for s in basis["sources"]))
    basis["status"] = "needs_review" if changed else "unchanged_recorded_basis"
    return basis


def render(out, p, rows, graph, origins, prior, basis):
    fs = findings(graph)
    origin_index = {(o["source_id"], o["prepared_record"]): o for o in origins}
    sourced = []
    for f in fs:
        f = dict(f)
        f["original_evidence"] = []
        for side in ("source_a", "source_b"):
            src = f[side]["source"]
            match = re.search(r"\brow (\d+)", src.get("locator", ""))
            o = origin_index.get((src.get("document"), int(match[1]))) if match else None
            f["original_evidence"].append({"side": side, "says": f[side]["says"], "source": src, "origin": o})
        sourced.append(f)
    old = findings(load(prior / "map/graph.json")) if prior else []
    old_ids, ids = {f["id"] for f in old}, {f["id"] for f in fs}
    history = {"new": sorted(ids - old_ids), "still_detected": sorted(ids & old_ids),
               "no_longer_detected": [f for f in old if f["id"] not in ids],
               "meaning": "No longer detected is an observation, not an accepted correction or closure. Previous packet remains unchanged."}
    dump(out / "findings.json", {"schema": "maintenance-findings-1", "findings": sourced, "history": history,
                                "comparison_basis": "comparison-basis.json"})
    with (out / "map/queues/review_queue.csv").open(encoding="utf-8", newline="") as stream:
        queue = list(csv.DictReader(stream))
    actions = [{"item": f["subject"], "finding": f["id"], "record_owner_role": f["record_owner"],
                "action": "Confirm installed state against permitted evidence; propose source corrections and read back accepted records",
                "assigned_person": "", "due_date": "", "acceptance_evidence": "", "status": "needs review"} for f in fs]
    if actions:
        write_csv(out / "proposed-actions.csv", actions)
    else:
        (out / "proposed-actions.csv").write_text("item,finding,record_owner_role,action,assigned_person,due_date,acceptance_evidence,status\n", encoding="utf-8")
    esc = html.escape
    sections = []
    lines = ["# Maintenance record review", "", f"Scope: {p['site']}/{p['plant']}; units {', '.join(p['units'])}; as of {p['as_of']}.", "",
             f"{len(fs)} detected disagreements; {len(queue)} total review queue entries. Equipment rows: {len(rows['equipment'])}; work-order rows: {len(rows['work_orders'])}.", "",
             "Draft comparison of the supplied exports. Absence of a finding does not establish complete coverage, installed state or accepted corrections.", ""]
    sections.append("<h1>Maintenance record review</h1>" + "".join(f"<p>{esc(x)}</p>" for x in lines[2:] if x))
    if prior:
        title = "Comparison basis needs review" if basis["status"] == "needs_review" else "Recorded comparison basis unchanged"
        notes = [basis["meaning"]]
        if basis["changed_methods"]:
            notes.append("Changed method files: " + ", ".join(basis["changed_methods"]) + ". A changed result can reflect changed software; inspect before treating it as a source correction.")
        notes.extend(basis["unknown_prior_basis"])
        if basis["python_change"]:
            notes.append("Python runtime changed; versions are retained in comparison-basis.json.")
        if basis["as_of_change"]:
            notes.append(f"Comparison cutoff changed from {basis['as_of_change']['before']} to {basis['as_of_change']['after']}.")
        for c in basis["interpretation_changes"]:
            notes.append(f"{c['source']}: declared column/date/encoding interpretation changed. Identical bytes can produce different prepared values; review both mappings in comparison-basis.json.")
        for s in basis["sources"]:
            notes.append(f"{s['source']} ({s['id']}): revision {s['before_revision']} to {s['after_revision']}; {s['before_rows']} to {s['after_rows']} rows; {len(s['added_records'])} added, {len(s['removed_records'])} removed, {len(s['changed_records'])} changed normalized records.")
            for removed in s["removed_records"]:
                o = removed["origin"]
                at = f"prior original CSV record {o['original_record']}" if o else "prior original locator unavailable"
                notes.append(f"Missing from the supplied export: {'/'.join(removed['identity'])}, {at}. Omission is not physical removal or an accepted correction.")
        lines += [f"## {title}", ""] + ["- " + n for n in notes] + ["", "See comparison-basis.json for exact before/after values, source rows and mappings.", ""]
        sections.append(f"<section><h2>{title}</h2><ul>" + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul><p><a href='comparison-basis.json'>Exact comparison basis and source-row changes</a></p></section>")
    for f in sourced:
        lines += [f"## {f['subject']} — {f['attribute']} ({f['id']})", "", f"Review role: {f['record_owner']}. Status: {f['status']}.", ""]
        parts = [f"<h2>{esc(f['subject'])} — {esc(f['attribute'])}</h2><p>Review role: {esc(str(f['record_owner']))}; {esc(f['status'])}</p>"]
        for ev in f["original_evidence"]:
            o = ev["origin"]
            label = f"{ev['source'].get('document')} rev {ev['source'].get('revision')} {ev['source'].get('locator')}"
            lines += [f"- {ev['says']} — {label}"]
            ref = f"<a href='{o['original']}'>original CSV record {o['original_record']}</a>" if o else "Original link unavailable; inspect source locator"
            parts.append(f"<p><strong>{esc(str(ev['says']))}</strong> — {esc(label)}; {ref}</p>")
        sections.append("<article>" + "".join(parts) + "</article>")
        lines += [""]
    notes = ["Review queue includes scope ambiguities and other checks: map/queues/review_queue.csv.",
             "No field inspection, engineering approval, MOC determination, PM validation or company-system write/readback has occurred.",
             "Open work orders (blank closed_on) supply history only, not evidence of installation. Latest dated closed order per attribute is the comparison basis; owners must confirm its meaning.",
             "Only mapped fields are interpreted; ignored columns remain in originals. Text is trimmed in prepared CSVs; exact original bytes and CSV-record/physical-line locators remain.",
             "Proposed actions need a named person, due date and accepted source readback. No action has been assigned or completed by this tool."]
    if prior:
        notes += [f"Compared with verified previous packet: {len(history['new'])} new, {len(history['still_detected'])} still detected, {len(history['no_longer_detected'])} no longer detected. See changes.md and findings.json; disappearance is not acceptance."]
    for kind in FIELDS:
        notes.append(f"{kind}: {p[kind]['id']} rev {p[kind]['revision']}; owner {p[kind]['owner']}; declared coverage: {p[kind]['coverage']}")
        missing = sorted(set(p['units']) - {r['unit'] for r in rows[kind]})
        if missing:
            notes.append(f"Coverage gap: {kind} has no rows for declared units {', '.join(missing)}. No conclusions there.")
        blanks = [x for x in ("manufacturer", "model", "serial_number", "size") if any(not r.get(("installed_" if kind == "work_orders" else "") + x) for r in rows[kind])]
        notes.append(f"{kind} attributes absent in some/all rows (not compared where unavailable): {', '.join(blanks) or 'none'}.")
    lines += ["## Review boundaries and next steps", ""] + ["- " + n for n in notes] + ["", "Open REPORT.html offline; proposed-actions.csv is a draft review form. Retain this whole folder and receipt.json for the next revision.", ""]
    sections.append("<h2>Review boundaries and next steps</h2><ul>" + "".join(f"<li>{esc(n)}</li>" for n in notes) + "</ul><p><a href='proposed-actions.csv'>Proposed actions</a> · <a href='map/queues/review_queue.csv'>Full review queue</a> · <a href='findings.json'>Findings and history</a> · <a href='prepared/row-origins.json'>Row origins</a></p>")
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    (out / "REPORT.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Maintenance record review</title><style>body{font:17px/1.5 system-ui;max-width:58rem;margin:2rem auto;padding:0 1rem;overflow-wrap:anywhere}article{border:1px solid #aaa;padding:1rem;margin:1rem 0}a{color:#064e8a}@media print{article{break-inside:avoid}}</style><main>" + "".join(sections) + "</main></html>", encoding="utf-8", newline="\n")


def run(profile, equipment, work_orders, out, previous=None):
    paths = {"profile": Path(profile).resolve(), "equipment": Path(equipment).resolve(), "work_orders": Path(work_orders).resolve()}
    out = Path(out).resolve()
    if out.exists() or any(out == x or out in x.parents for x in paths.values()):
        raise ValueError("use an unused output directory outside input files; existing evidence is retained")
    raw = {k: path.read_bytes() for k, path in paths.items()}
    p = json.loads(raw["profile"].decode("utf-8-sig"))
    profile_check(p)
    rows, origins = {}, []
    for kind in FIELDS:
        rows[kind], oo = read_rows(raw[kind], kind, p)
        origins.extend(oo)
    # Refuse ambiguous same-day competing installation values. The underlying map otherwise sorts by order ID.
    installed = {}
    for r in rows["work_orders"]:
        for attr in ("installed_manufacturer", "installed_model", "installed_serial_number", "installed_size"):
            if r["closed_on"] and r.get(attr):
                key = (r["unit"], r["tag"], r["closed_on"], attr)
                if key in installed and installed[key] != r[attr]:
                    raise ValueError(f"work_orders: conflicting same-day installations {key}; confirm event sequence")
                installed[key] = r[attr]
    previous = Path(previous).resolve() if previous else None
    previous_receipt = verify_packet(previous) if previous else None
    if previous:
        if previous == out or previous in out.parents or out in previous.parents:
            raise ValueError("previous and new packets must be separate sibling destinations")
        oldp = load(previous / "originals/profile.json")
        if binding(oldp) != binding(p) or p["as_of"] < oldp["as_of"]:
            raise ValueError("previous packet scope/source authority/coverage differs or date moves backwards; explicitly reconcile before comparison")
        for kind in FIELDS:
            if oldp[kind]["revision"] == p[kind]["revision"] and sha(previous / f"originals/{kind}.csv") != hashlib.sha256(raw[kind]).hexdigest():
                raise ValueError(f"{kind}: changed bytes under unchanged revision; supply a new source revision")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".maintenance-", dir=out.parent) as tmp:
        stage = Path(tmp) / "packet"
        (stage / "originals").mkdir(parents=True)
        prepared = stage / "prepared"
        prepared.mkdir()
        for k, b in raw.items():
            (stage / "originals" / ("profile.json" if k == "profile" else k + ".csv")).write_bytes(b)
        for k, rr in rows.items():
            write_csv(prepared / (k + ".csv"), rr)
        dump(prepared / "row-origins.json", origins)
        (prepared / "drawings.csv").write_text("sheet,rev,plant,unit,owner,path\n", encoding="utf-8")
        scope = p["site"] + "/" + p["plant"]
        def spec(k):
            return {"id": p[k]["id"], "revision": p[k]["revision"], "path": k + ".csv", "scopes": [scope]}
        site = {"schema": "one-map-site-1", "site": {"id": p["site"]}, "plants": [{"id": p["plant"], "units": [{"id": u} for u in p["units"]]}],
                "as_of": p["as_of"], "drawing_register": "drawings.csv", "record_owners": {"maintenance_export": p["equipment"]["owner"], "work_order": p["work_orders"]["owner"]},
                "maintenance_export": spec("equipment"), "records": [dict(spec("work_orders"), register="work_order")]}
        dump(prepared / "site.json", site)
        one_map.build(prepared / "site.json", stage / "map")
        graph = load(stage / "map/graph.json")
        pins = method_pins()
        basis = comparison_basis(p, rows, origins, raw, pins, previous, previous_receipt)
        dump(stage / "comparison-basis.json", basis)
        if previous:
            rep = map_changes.changes(load(previous / "map/graph.json"), graph)
            map_changes.write(stage, "changes", rep, map_changes.changes_md(rep))
        render(stage, p, rows, graph, origins, previous, basis)
        receipt = {"schema": "maintenance-packet-1", "scope": binding(p), "as_of": p["as_of"],
                   "python": sys.version, "methods_sha256_lf": pins,
                   "method_scope": "Loaded local Python modules; Python version recorded; not a complete environment lock or tamper-proof signature",
                   "previous_receipt_sha256": sha(previous / "receipt.json") if previous else None,
                   "previous_files": previous_receipt["files"] if previous else None, "files": inventory(stage),
                   "company_acceptance": "not performed", "human_effort": "not measured"}
        dump(stage / "receipt.json", receipt)
        # Same-volume rename publishes only a completed packet; never replace an existing destination.
        if out.exists():
            raise ValueError("output appeared during run; refusing to replace it")
        stage.rename(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--equipment", required=True)
    parser.add_argument("--work-orders", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--previous")
    a = parser.parse_args()
    try:
        result = run(a.profile, a.equipment, a.work_orders, a.out, a.previous)
        print(f"Draft review packet: {result / 'REPORT.html'}; source acceptance remains with record owners")
    except (OSError, ValueError, csv.Error, one_map.InputError) as e:
        parser.exit(2, f"ERROR: {e}\n")


if __name__ == "__main__":
    main()
