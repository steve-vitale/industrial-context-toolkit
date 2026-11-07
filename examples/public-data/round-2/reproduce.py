"""Reproduce round-2 acquisition: opt-in pinned fetch and offline structural admission.

No model runs, downloaded code execution or archive extraction. CAD contents remain unopened.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import platform
import struct
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PARENT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data/public_sources_20261107_round2.json"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(PARENT))
import fetch_corpus  # noqa: E402

spec = importlib.util.spec_from_file_location("public_admission_v1", PARENT / "reproduce.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def inspect(path, sid):
    if path.suffix.lower() == ".dxf":
        return {"parser": "intentionally not run", "status": "content uninspected",
                "reason": "Preserve acquisition/evaluation separation; filenames and hashes only."}
    if path.suffix.lower() == ".parquet":
        # Check framing and footer bounds without installing a reader or interpreting metadata.
        with path.open("rb") as stream:
            start = stream.read(4)
            stream.seek(-8, 2)
            footer = stream.read(8)
        size = path.stat().st_size
        if start != b"PAR1" or footer[4:] != b"PAR1":
            raise ValueError("Invalid Parquet framing")
        footer_size = struct.unpack("<I", footer[:4])[0]
        if footer_size > size - 12:
            raise ValueError("Parquet footer outside file bounds")
        return {"parser": "Parquet framing only", "footer_bytes": footer_size,
                "rows_and_schema": "not inspected; optional Parquet reader not installed"}
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            # Inventory only: no archive member is read or extracted, including publisher labels.
            return {"parser": "stdlib zip directory only", "extracted": False,
                    "members": [{"name": m.filename, "bytes": m.file_size,
                                 "compressed_bytes": m.compress_size, "crc32": f"{m.CRC:08x}"}
                                for m in members],
                    "uncompressed_bytes": sum(m.file_size for m in members)}
    if path.suffix.lower() == ".csv" and sid == "nestor-excavators":
        # Same raw escape convention as the retained official Nestor loader; not a CMMS adapter.
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = csv.reader(stream, escapechar="\\")
            header = next(rows)
            widths, count = {}, 0
            for row in rows:
                count += 1
                widths[len(row)] = widths.get(len(row), 0) + 1
        return {"parser": "stdlib csv, official loader escapechar", "columns": header,
                "data_rows": count, "row_widths": widths, "meaning": "not scored",
                "status": "partial" if any(width != len(header) for width in widths) else "ok",
                "warnings": ["Rows with unexpected widths retained in original; not a ready CMMS intake."]
                            if any(width != len(header) for width in widths) else []}
    return base.inspect(path, "off")


def run(argv=None):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sources = registry["sources"]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", action="append", choices=sorted(sources))
    ap.add_argument("--fetch", action="store_true", help="opt in to pinned downloads")
    ap.add_argument("--max-mb", type=float, default=225, help="total missing byte budget, decimal MB")
    ap.add_argument("--out", type=Path, required=True, help="new report directory")
    args = ap.parse_args(argv)
    selected = list(dict.fromkeys(args.source or sources))
    if args.out.exists():
        ap.error("--out exists; choose a new evidence directory")
    pins = fetch_corpus.load_pins()
    problems = fetch_corpus.validate_file_pins(pins, sources)
    if problems:
        ap.error("; ".join(problems))
    needed = sum(pin["bytes"] for sid in selected for name, pin in pins[sid].items()
                 if not (fetch_corpus.EXTERNAL / sid / name).is_file()
                 or base.digest(fetch_corpus.EXTERNAL / sid / name) != pin["sha256"])
    if args.fetch and (not 0 <= args.max_mb < float("inf") or needed > args.max_mb * 1e6):
        ap.error(f"{needed} missing/replaced bytes exceed --max-mb {args.max_mb}")
    args.out.mkdir(parents=True)
    report = {"schema": "public-source-admission-2", "created": datetime.now(timezone.utc).isoformat(),
              "role": "acquired-unscored; structural admission only", "python": platform.python_version(),
              "fingerprint_convention": "method/registry CRLF normalized to LF; originals raw bytes",
              "method_sha256": fingerprint(Path(__file__)),
              "base_inspector_sha256": fingerprint(PARENT / "reproduce.py"),
              "extractor_sha256": fingerprint(ROOT / "scripts/extract_text.py"),
              "fetch_engine_sha256": fingerprint(ROOT / "scripts/fetch_corpus.py"),
              "registry_sha256": fingerprint(REGISTRY),
              "fetch_receipts": [], "sources": {}, "errors": []}
    fetch_corpus.FILE_SOURCES.update(sources)
    fetch_corpus.USER_AGENT = "industrial-context-toolkit public-source acquisition https://github.com/steve-vitale/industrial-context-toolkit"
    if args.fetch:
        for sid in selected:
            try:
                report["fetch_receipts"].append(fetch_corpus.fetch_pinned(
                    sid, args.max_mb, fetch_corpus.EXTERNAL / sid))
            except Exception as error:
                report["errors"].append({"source": sid, "stage": "fetch", "error": str(error)})
    for sid in selected:
        files = []
        for name, pin in pins[sid].items():
            path = fetch_corpus.EXTERNAL / sid / name
            item = {"path": name, "bytes": pin["bytes"], "sha256": pin["sha256"]}
            try:
                fetch_corpus.check_bytes(name, path.read_bytes(), pin["bytes"], pin["sha256"])
                item["integrity"] = "match"
                item["inspection"] = inspect(path, sid)
                if item["inspection"].get("status") == "error":
                    raise ValueError("Document parser error: " + str(item["inspection"].get("warnings")))
            except Exception as error:
                item["error"] = str(error)
                report["errors"].append({"source": sid, "path": name, "stage": "inspection", "error": str(error)})
            files.append(item)
        report["sources"][sid] = {"categories": sources[sid]["categories"], "files": files}
        print(sid, len(files), "files checked", flush=True)
    (args.out / "admission.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(run())
