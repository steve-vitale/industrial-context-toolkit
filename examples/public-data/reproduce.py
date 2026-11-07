"""Fetch optionally, verify every pinned byte, and inspect the newly acquired public inputs.

This is source admission, not scoring or training. No downloaded notebook/script is executed,
no archive is extracted, and no task truth is generated. Reserved CAD inputs are not opened.
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import extract_text  # noqa: E402
import fetch_corpus  # noqa: E402
import fetch_sources  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(path):
    # Software/metadata fingerprints are portable across Git checkout line endings;
    # acquired originals above always keep their raw-byte hashes.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def inspect(path, ocr):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            widths = {}
            rows = 0
            for row in reader:
                rows += 1
                widths[len(row)] = widths.get(len(row), 0) + 1
        return {"parser": "stdlib csv", "data_rows": rows, "columns": header, "row_widths": widths}
    if suffix in {".json", ".ipynb"}:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        result = {"parser": "stdlib json", "root_type": type(data).__name__, "root_items": len(data)}
        if suffix == ".ipynb":
            result.update(cells=len(data["cells"]), executed=False)
        return result
    if suffix == ".norm":
        records, active, pairs = 0, False, 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                active = True
                pairs += 1
            elif active:
                records += 1
                active = False
        return {"parser": "record separators", "records": records + int(active), "token_lines": pairs,
                "labels_present": True}
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            return {"parser": "stdlib zip directory only", "members": len(members),
                    "uncompressed_bytes": sum(m.file_size for m in members), "extracted": False,
                    "member_extensions": sorted({Path(m.filename).suffix for m in members if not m.is_dir()})}
    if suffix in {".pdf", ".xlsx", ".jpg", ".png"}:
        # OCR opt-in is for the three photographs. A newly acquired 300-page PDF may
        # need a separately bounded page-selection/OCR job, not an unbounded batch here.
        result = extract_text.extract(path, ocr=ocr if suffix in {".jpg", ".png"} else "off", embedded=False)
        return {"parser": "scripts/extract_text.py", "status": result.status, "engine": result.engine,
                "engine_version": result.engine_version, "segments": len(result.segments),
                "characters": sum(len(t) for _, t in result.segments), "warnings": result.warnings,
                "interpretation_accuracy": "not assessed"}
    return {"parser": "not run", "status": "retained as source bytes; no execution"}


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sources = fetch_sources.register()
    ap.add_argument("--source", action="append", choices=sorted(sources),
        help="repeat to select groups; default all 14")
    ap.add_argument("--fetch", action="store_true", help="opt in to pinned public downloads; default offline")
    ap.add_argument("--max-mb", type=float, default=125, help="total missing download budget, decimal MB")
    ap.add_argument("--ocr", choices=["off", "auto"], default="off")
    ap.add_argument("--out", type=Path, required=True, help="new directory; existing evidence is never replaced")
    args = ap.parse_args(argv)
    registry = json.loads(fetch_sources.REGISTRY.read_text(encoding="utf-8"))
    pins = fetch_corpus.load_pins()
    selected = args.source or list(registry["sources"])
    selected = list(dict.fromkeys(selected))
    if args.out.exists():
        ap.error("--out already exists; choose a new directory")
    problems = fetch_corpus.validate_file_pins(pins)
    if problems:
        ap.error("; ".join(problems))
    needed = sum(pin["bytes"] for sid in selected for name, pin in pins[sid].items()
                 if not (fetch_corpus.EXTERNAL / sid / name).is_file()
                 or digest(fetch_corpus.EXTERNAL / sid / name) != pin["sha256"])
    if args.fetch and (args.max_mb < 0 or needed > args.max_mb * 1e6):
        ap.error(f"missing/replaced bytes {needed} exceed total --max-mb {args.max_mb}")
    args.out.mkdir(parents=True)
    receipts = []
    if args.fetch:
        for sid in selected:
            receipts.append(fetch_corpus.fetch_pinned(sid, args.max_mb, fetch_corpus.EXTERNAL / sid))
    report = {"schema": "public-source-admission-1", "created": datetime.now(timezone.utc).isoformat(),
              "role": "acquired-unscored; structural/parser admission only", "python": platform.python_version(),
              "ocr": args.ocr, "fingerprint_convention": "code/registry CRLF normalized to LF; source files raw",
              "method_sha256": text_digest(Path(__file__)),
              "extractor_sha256": text_digest(ROOT / "scripts/extract_text.py"),
              "registry_sha256": text_digest(fetch_sources.REGISTRY),
              "fetch_engine_sha256": text_digest(ROOT / "scripts/fetch_corpus.py"),
              "fetch_catalog_sha256": text_digest(Path(__file__).with_name("fetch_sources.py")),
              "fetch_receipts": receipts, "sources": {}, "errors": []}
    for sid in selected:
        files = []
        for name, pin in pins[sid].items():
            path = fetch_corpus.EXTERNAL / sid / name
            item = {"path": name, "bytes": pin["bytes"], "sha256": pin["sha256"]}
            try:
                fetch_corpus.check_bytes(name, path.read_bytes(), pin["bytes"], pin["sha256"])
                item["integrity"] = "match"
                item["inspection"] = inspect(path, args.ocr)
                if item["inspection"].get("status") == "error":
                    raise ValueError("document parser error: " + str(item["inspection"]["warnings"]))
            except (OSError, ValueError, KeyError, zipfile.BadZipFile, fetch_corpus.PinError) as error:
                item["error"] = str(error)
                report["errors"].append({"source": sid, "path": name, "error": str(error)})
            files.append(item)
        report["sources"][sid] = {"categories": registry["sources"][sid]["categories"], "files": files}
        print(sid, len(files), "files inspected", flush=True)
    (args.out / "admission.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(run())
