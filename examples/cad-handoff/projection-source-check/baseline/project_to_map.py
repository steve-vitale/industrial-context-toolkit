"""Project a retained CAD attribute packet into a draft one-map sheet through an explicit identity mapping.

This tutorial adapter publishes drawing-reference attributes, not accepted installed-equipment records.
It does not infer piping, edit a released map or implement reverse/multi-master synchronization.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def project(packet, mapping, out):
    packet, out = Path(packet), Path(out)
    if out.exists():
        raise ValueError("Use a new projection directory to retain history")
    context = read(packet / "cad_context.json")
    if context.get("schema") != "cad-context-1" or context.get("relationships"):
        raise ValueError("Only the declared attribute-context profile is supported")
    original = (packet / "source.dxf").read_bytes()
    sha = hashlib.sha256(original).hexdigest()
    rows = mapping["assets"]
    index = {r["id"]: r for r in rows}
    if len(index) != len(rows) or set(index) != {n["id"] for n in context["nodes"]}:
        raise ValueError("Map every stable identity exactly once; missing/extra identities are not guessed")
    sheet = {"schema": "one-map-sheet-1", "equipment": [], "instruments": [], "lines": [], "signal_lines": [],
             "note": "Draft CAD-reference projection. No connectivity or installed-state claim; original DXF retained."}
    for node in context["nodes"]:
        rule = index[node["id"]]
        if node["source"]["sha256"] != sha or node["tag"] != rule["tag"]:
            raise ValueError("Source hash or supplied tag mapping changed; reconcile explicitly")
        if rule["section"] not in {"equipment", "instruments"}:
            raise ValueError("Unknown sheet section")
        attributes = {"cad_" + k.lower(): v for k, v in node["attributes"].items()}
        attributes.update(cad_source_sha256=sha, cad_insert_handle=node["source"]["insert_handle"])
        sheet[rule["section"]].append({"tag": rule["tag"], "attributes": attributes})
    site = {"schema": "one-map-site-1", "note": sheet["note"],
            "site": {"id": mapping["site"], "name": "Fictional CAD handoff reference"},
            "plants": [{"id": mapping["plant"], "name": "Fictional plant", "owner": "Engineering",
                        "units": [{"id": mapping["unit"], "name": "Fictional unit"}]}],
            "record_owners": {"pid": "Engineering", "maintenance_export": "Maintenance", "instrument_index": "I&C"},
            "drawing_register": "drawing_register.csv"}
    out.mkdir(parents=True)
    (out / "cad-source.dxf").write_bytes(original)
    write(out / "identity-mapping.json", mapping)
    write(out / "sheet.json", sheet)
    write(out / "site.json", site)
    write(out / "projection.json", {"schema": "cad-map-projection-1", "source_sha256": sha,
        "context_sha256": hashlib.sha256((packet / "cad_context.json").read_bytes()).hexdigest(),
        "mapping_sha256": hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest(),
        "status": "draft drawing reference; not installed-state authority", "relationships_inferred": 0})
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["sheet", "rev", "plant", "unit", "owner", "path", "status"])
    writer.writerow(["CAD-FDV", sha[:12], mapping["plant"], mapping["unit"], "Engineering", "sheet.json", "draft"])
    (out / "drawing_register.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("packet")
    ap.add_argument("mapping")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    project(args.packet, read(args.mapping), args.out)
    print(f"Draft CAD reference projection -> {args.out}")


if __name__ == "__main__":
    main()
