"""Several local P&ID sheets + existing extractions -> one unverified review bundle (stdlib only).

The drawing-set sibling of import_site_drawing.py. It validates each sheet exactly as the one-sheet intake does,
builds one model across the set (build_twin.py), and pairs off-page connectors across sheets. It never calls a
model, traces, scores, connects signals or approves operations. Input schema: site-drawing-set-1. See --help.

Cross-sheet pairing runs in two passes, each recorded on the pair as its method:
  1. build_twin.py's own rules, for references written like "PID 140-1".
  2. Literal matching on the drawing numbers supplied in the manifest, for references written any other way
     ("REF SHT P-204", "DWG 10-PI-003"):
       reciprocal_supplied_numbers        a connector on sheet A names B's number and one on B names A's number;
       one_way_number_plus_sheet_title     a connector on A names B's number, and a connector on B names no
                                           drawing but carries every word of A's supplied title.
Every pair stays unverified and is listed in the review queue with its method.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import build_twin
import generate
import import_site_drawing as one
import pi_mapping

SCHEMA = "site-drawing-set-1"
MAX_SHEETS = 200
LIMITATIONS = one.LIMITATIONS + [
    "Cross-sheet pairs are matched from connector text and the supplied drawing numbers and titles; a pair is a "
    "review candidate, not an established continuation.",
]
TITLE_STOP = {"PID", "P&ID", "DRAWING", "DWG", "SHEET", "SHT", "REF", "SEE", "FROM", "TO", "THE", "AND", "OF", "FOR"}
SHEET_KEYS = {"drawing_id", "revision", "page", "image", "extraction", "drawing_number", "system_code",
              "system_name", "title"}


def number_pattern(number):
    """A supplied drawing number as a literal, separator-tolerant pattern: P-204 matches 'P-204', 'P 204', 'P204'
    but never 'P-2045' or 'XP-204'."""
    runs = re.findall(r"[A-Z0-9]+", number.upper())
    one.require(bool(runs), f"drawing_number {number!r} has no letters or digits")
    return re.compile(r"(?<![A-Z0-9])" + r"[\s\-_./]*".join(map(re.escape, runs)) + r"(?![A-Z0-9])")


def title_words(text):
    return {w for w in re.findall(r"[A-Z][A-Z0-9&]{2,}", (text or "").upper()) if w not in TITLE_STOP}


def pair_by_supplied_numbers(model, numbers, titles):
    """Second pairing pass (module docstring). Mutates the model's connectors, pairs and streams in place."""
    patterns = {s: number_pattern(n) for s, n in numbers.items()}
    sheet_of = {c["id"]: c["provenance"][0]["sheet"] for c in model["offpage_connectors"]}

    def refs(c):
        text = (c.get("text") or "").upper()
        return sorted(s for s, p in patterns.items() if s != sheet_of[c["id"]] and p.search(text))

    open_ = [c for c in model["offpage_connectors"] if not c["pair"]]
    named = {c["id"]: refs(c) for c in open_}
    candidates = []
    for x in open_:
        if len(named[x["id"]]) != 1:
            continue
        a, b = sheet_of[x["id"]], named[x["id"]][0]
        for y in open_:
            if sheet_of[y["id"]] != b:
                continue
            if named[y["id"]] == [a]:
                method = "reciprocal_supplied_numbers"
            elif not named[y["id"]] and not y.get("refers_to_drawing") and len(title_words(titles.get(a))) >= 2 \
                    and title_words(titles.get(a)) <= title_words(y.get("text")):
                method = "one_way_number_plus_sheet_title"
            else:
                continue
            wx = build_twin.tag_tokens(patterns[b].sub(" ", (x.get("text") or "").upper()))
            wy = build_twin.tag_tokens(patterns[a].sub(" ", (y.get("text") or "").upper()))
            sim = len(wx & wy) / len(wx | wy) if wx | wy else 0.0
            candidates.append((method != "reciprocal_supplied_numbers", -sim, x["id"], y["id"], method, sim))
    candidates.sort()
    options = {}
    for _, _, xi, yi, _, _ in candidates:
        options[xi] = options.get(xi, 0) + 1
        options[yi] = options.get(yi, 0) + 1
    by_id = {c["id"]: c for c in model["offpage_connectors"]}
    added = 0
    for _, _, xi, yi, method, sim in candidates:
        x, y = by_id[xi], by_id[yi]
        if x["pair"] or y["pair"] or xi == yi:
            continue
        x["pair"], y["pair"] = yi, xi
        for c, other in ((x, y), (y, x)):
            c["pair_method"], c["pair_status"] = method, "paired"
            c["pair_description_similarity"] = round(sim, 2)
            if not c.get("refers_to_drawing") and named.get(c["id"]):
                c["refers_to_drawing"] = numbers[named[c["id"]][0]]
        pid = f"XP-{len(model['offpage_pairs']) + 1:03d}"
        model["offpage_pairs"].append({"id": pid, "a": xi, "b": yi, "sheet_a": sheet_of[xi], "sheet_b": sheet_of[yi],
                                       "text_a": x["text"], "text_b": y["text"], "method": method,
                                       "description_similarity": round(sim, 2),
                                       "alternatives": max(options[xi], options[yi]) - 1,
                                       "verification": {"status": "unverified"}})
        model["streams"].append({"id": pid, "name": f"off-page {x['text']} <-> {y['text']}", "kind": "cross_sheet",
                                 "from": xi, "to": yi, "sheet": None, "direction": "unknown", "confidence": None,
                                 "verification": {"status": "unverified"}})
        added += 1
    for c in open_:
        if c["pair"] or not named[c["id"]]:
            continue
        c["refers_to_drawing"] = c.get("refers_to_drawing") or numbers[named[c["id"]][0]]
        c["pair_status"] = ("unpaired: target sheet is in this set but no matching connector was found"
                            if len(named[c["id"]]) == 1 else "unpaired: names more than one sheet in this set")
    return added


def load_set(manifest_path, out):
    manifest_path = Path(manifest_path).resolve()
    raw_manifest = one.read_bounded(manifest_path, one.MAX_JSON_BYTES)
    manifest = one.strict_json(raw_manifest)
    one.require(isinstance(manifest, dict), "Manifest must be an object")
    one.require(manifest.get("schema_version") == SCHEMA, f"schema_version must be {SCHEMA}")
    set_id = one.text_field(manifest, "set_id")
    fmt = manifest.get("extraction_format")
    one.require(fmt in ("prediction", "run-record"), "extraction_format must be prediction or run-record")
    producer = manifest.get("producer")
    one.require(isinstance(producer, dict), "producer must describe the supplied extractions")
    producer = {k: one.text_field(producer, k, optional=k == "model") for k in ("method", "tool", "model")}
    sheets = manifest.get("sheets")
    one.require(isinstance(sheets, list) and 1 <= len(sheets) <= MAX_SHEETS, f"sheets must list 1 to {MAX_SHEETS} sheets")
    out = Path(out).absolute()
    one.require(not out.exists() and not out.is_symlink(), f"Output already exists: {out}")
    one.require(out.parent.is_dir(), "Output parent directory must already exist")
    resolved_out = out.resolve()
    loaded, seen_numbers, seen_ids = [], set(), set()
    for index, sheet in enumerate(sheets):
        one.require(isinstance(sheet, dict), f"sheets[{index}] must be an object")
        unknown = set(sheet) - SHEET_KEYS
        one.require(not unknown, f"sheets[{index}] has unsupported fields: {sorted(unknown)}")
        identity = {k: one.text_field(sheet, k) for k in ("drawing_id", "revision")}
        one.require((identity["drawing_id"], identity["revision"]) not in seen_ids,
                    f"sheets[{index}] repeats drawing {identity['drawing_id']} revision {identity['revision']}")
        seen_ids.add((identity["drawing_id"], identity["revision"]))
        page = sheet.get("page")
        one.require(type(page) is int and page > 0, f"sheets[{index}].page must be a positive integer")
        identity["page"] = page
        paths = {k: (manifest_path.parent / one.text_field(sheet, k)).resolve() for k in ("image", "extraction")}
        for source in (manifest_path, *paths.values()):
            one.require(source != resolved_out and not source.is_relative_to(resolved_out), "Output overlaps an input")
        image = one.read_bounded(paths["image"], one.MAX_IMAGE_BYTES)
        dimensions = one.png_dimensions(image)
        original = one.read_bounded(paths["extraction"], one.MAX_JSON_BYTES)
        record = one.strict_json(original)
        one.require(isinstance(record, dict), f"sheets[{index}] extraction JSON must be an object")
        if fmt == "run-record":
            one.require(not record.get("error") and not record.get("parse_error"),
                        f"sheets[{index}]: a failed extraction record cannot be imported")
            if record.get("image_sha256") is not None:
                one.require(record["image_sha256"] == one.digest(image), f"sheets[{index}]: run record image_sha256 does not match image")
            prediction = one.validate_prediction(record.get("prediction"))
        else:
            prediction = one.validate_prediction(record)
        register = {k: one.text_field(sheet, k, optional=True) for k in ("drawing_number", "system_code", "system_name")}
        title = one.text_field(sheet, "title", optional=True)
        if title and not register["system_name"]:
            register["system_name"] = title  # name the sheet's system after its title block, not "Sheet 0"
        if register["drawing_number"]:
            key = re.sub(r"[^A-Z0-9]", "", register["drawing_number"].upper())
            one.require(key not in seen_numbers, f"sheets[{index}] repeats drawing_number {register['drawing_number']}")
            seen_numbers.add(key)
            number_pattern(register["drawing_number"])
        n = str(index)
        sources = {k: {"original_filename": paths[k].name, "sha256": one.digest(content), "bytes": len(content),
                       "bundle_path": f"source/{n}.png" if k == "image" else f"source/extraction-original-{n}.json"}
                   for k, content in (("image", image), ("extraction", original))}
        loaded.append({"internal_sheet": n, "drawing": identity, "image": image, "original": original,
                       "prediction": prediction, "register": register, "title": title, "image_size_px": dimensions,
                       "record_producer": {k: record.get(k) for k in ("tool", "model")} if fmt == "run-record" else None,
                       "sources": sources})
    provenance = {"schema_version": SCHEMA, "set_id": set_id, "manifest_sha256": one.digest(raw_manifest),
                  "supplied_producer": producer, "extraction_format": fmt,
                  "original_manifest": "source/set-manifest-original.json", "limitations": LIMITATIONS,
                  "sheets": [{"internal_sheet": s["internal_sheet"], "drawing": s["drawing"], "title": s["title"],
                              "supplied_register": s["register"], "sources": s["sources"],
                              "image_size_px": s["image_size_px"], "supplied_record_producer": s["record_producer"],
                              "normalized_record": f"source/{s['internal_sheet']}.json"} for s in loaded],
                  "normalization": "Only supported symbols and connections are converted. Extra input fields remain in the preserved originals; tag whitespace and box precision follow build_twin.",
                  "pairing": "build_twin.py rules first, then literal matching on supplied drawing numbers and titles (scripts/import_drawing_set.py).",
                  "importer_sha256": one.digest(Path(__file__).read_bytes()),
                  "sheet_validator_sha256": one.digest(Path(one.__file__).read_bytes()),
                  "converter_sha256": one.digest(Path(build_twin.__file__).read_bytes()),
                  "generator_sha256": one.digest(Path(generate.__file__).read_bytes()),
                  "pi_mapping_sha256": one.digest(Path(pi_mapping.__file__).read_bytes())}
    return out, raw_manifest, producer, loaded, provenance


def import_set(manifest_path, out, check_only=False):
    out, raw_manifest, producer, loaded, provenance = load_set(manifest_path, out)
    drawings = [s["drawing"] for s in loaded]
    if check_only:
        return {"inputs_valid": True, "exports_written": False, "set_id": provenance["set_id"], "drawings": drawings,
                "limitations": LIMITATIONS}
    stage = Path(tempfile.mkdtemp(prefix=".site-set-intake-", dir=out.parent))
    try:
        source = stage / "source"
        source.mkdir()
        (source / "set-manifest-original.json").write_bytes(raw_manifest)
        for s in loaded:
            n = s["internal_sheet"]
            (source / f"{n}.png").write_bytes(s["image"])
            (source / f"extraction-original-{n}.json").write_bytes(s["original"])
            one.write_json(source / f"{n}.json", {"tool": producer["tool"], "model": producer["model"],
                           "prediction": s["prediction"], "image_sha256": one.digest(s["image"]),
                           "intake": {"set_id": provenance["set_id"], "drawing": s["drawing"]}})
        sheet_list = [s["internal_sheet"] for s in loaded]
        register = {s["internal_sheet"]: s["register"] for s in loaded}
        model = build_twin.build("supplied-extraction", source, sheet_list, source, register,
                                 "site-drawing-set", parent_rule="linked")
        numbers = {s["internal_sheet"]: s["register"]["drawing_number"] for s in loaded if s["register"]["drawing_number"]}
        titles = {s["internal_sheet"]: s["title"] for s in loaded if s["title"]}
        added = pair_by_supplied_numbers(model, numbers, titles)
        model["summary"] = build_twin.summary(model)
        model["meta"]["source_document"] = f"{provenance['set_id']}: " + "; ".join(
            f"{d['drawing_id']} rev {d['revision']} p{d['page']}" for d in drawings)
        model["meta"]["extraction_method"] = "Imported supplied extractions; no model or tracer executed by this intake"
        model["meta"]["intake"] = provenance
        model["meta"]["review_requirements"] = {"draft_review_exports_allowed": True, "operational_export_allowed": False,
                    "status_scope": "Descriptive intake readiness only; not an enforced deployment interlock", "blockers": LIMITATIONS[2:6]}
        evidence = {s["internal_sheet"]: {"source_manifest": "intake_manifest.json", "source_drawing": s["drawing"],
                                          "image_sha256": one.digest(s["image"]), "extraction_sha256": one.digest(s["original"])}
                    for s in loaded}
        for system in model["systems"]:
            system["source_run"] = f"source/{system['sheet']}.json"
            system.update(evidence[system["sheet"]])
        for collection in ("units", "instruments", "line_items", "offpage_connectors"):
            for item in model[collection]:
                for appearance in item["provenance"]:
                    appearance["source_run"] = f"source/{appearance['sheet']}.json"
                    appearance.update(evidence[appearance["sheet"]])
        for stream in model["streams"]:
            stream["source_evidence"] = evidence[stream["sheet"]] if stream.get("sheet") in evidence else \
                {"source_manifest": "intake_manifest.json", "cross_sheet": True}
        one.require(not model["dropped"]["symbols"] and not model["dropped"]["connections"], "Converter dropped input items")
        problems = generate.validate_twin(model)
        one.require(not problems, f"Converted model is invalid: {problems}")
        generate.export_twin(model, stage, images_dir=source)
        one.write_json(stage / "plant_model.json", model)
        one.write_json(stage / "intake_manifest.json", provenance)
        (stage / "READ_ME.txt").write_text("UNVERIFIED LOCAL REVIEW BUNDLE (DRAWING SET)\n\n" + "\n".join(LIMITATIONS)
                    + "\n\nSource paths are relative to this bundle. Keep source/ with the model and SVG files.\n", encoding="utf-8")
        one.require(not out.exists() and not out.is_symlink(), f"Output appeared while preparing bundle: {out}")
        os.rename(stage, out)
        return {"inputs_valid": True, "exports_written": True, "output": str(out), "summary": model["summary"],
                "pairs_from_supplied_numbers": added, "operational_export_allowed": False, "limitations": LIMITATIONS}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=(
        "Manifest fields: schema_version=site-drawing-set-1, set_id, extraction_format=prediction|run-record, "
        "producer={method,tool,model}, sheets=[{drawing_id, revision, page, image, extraction; optional "
        "drawing_number, title, system_code, system_name}]. Supply each sheet's drawing number and title from its "
        "title block so cross-sheet references can be matched. Paths are relative to the manifest. Output must be "
        "new, with an existing parent."))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--check-only", action="store_true", help="validate inputs without writing")
    args = parser.parse_args(argv)
    try:
        result = import_set(args.manifest, args.out, args.check_only)
    except (ValueError, OSError, TypeError, KeyError, OverflowError, RecursionError) as error:
        parser.exit(2, f"Drawing set intake failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
