"""Rebuild source-bound sidecars and verify retained candidates/baselines without a CAD UI or network."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cad_exchange as ce
import cad_handoff as ch
import verify_bytes


def check():
    freeze = ce.read_json(HERE / "EXCHANGE-6-FREEZE.json")
    for relative, sha in freeze["methods"].items():
        raw = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Method binding changed: " + relative)
    base = HERE / "exchange-6"
    inputs = ce.read_json(base / "INPUTS.json")
    saved = ce.read_json(base / "results/summary.json")
    if [c["id"] for c in inputs["cases"]] != [r["id"] for r in saved["cases"]] or len(inputs["cases"]) != 6:
        raise ValueError("Saved cohort coverage differs")
    total_edits = total_assets = 0
    for case, row in zip(inputs["cases"], saved["cases"]):
        source, key = base / case["source"], base / case["plan"]
        if ch.digest(source) != case["source_sha256"] or ch.digest(key) != case["plan_sha256"]:
            raise ValueError("Input/key pin changed")
        expected, record = ce.read_json(key), base / "results" / case["id"]
        response = ce.read_json(record / "response.json")
        with tempfile.TemporaryDirectory(prefix="ict-check-exchange-") as tmp:
            root = Path(tmp)
            data = ce.prepare(source, root / "exchange")
            if ce.plan_from(source, data, response) != expected:
                raise ValueError("Response differs from authored key")
            report = ce.apply(source, data, response, root / "draft")
            candidate = root / "draft/candidate.dxf"
            byte_check = verify_bytes.verify(source, candidate, expected)
            if candidate.read_bytes() != (record / "candidate.dxf").read_bytes():
                raise ValueError("Candidate does not reproduce")
            if report["unexpected"] or row["sidecar_strict_differences"] != 0 or byte_check != row["byte_check"]:
                raise ValueError("Preservation result differs")
            if ce.read_json(record / "byte-check.json") != byte_check:
                raise ValueError("Saved byte check differs")
            total_assets += len(data["assets"])
            total_edits += len(expected["changes"])
        def core(report):
            return {k: v for k, v in report.items() if k != "save_metadata_changed"}
        for filename, comparison in (("candidate.dxf", "comparison.json"), ("library-candidate.dxf", "library-comparison.json")):
            report = ch.compare(ch.snapshot(source), ch.snapshot(record / filename), expected)
            if core(report) != core(ce.read_json(record / comparison)):
                raise ValueError("Retained strict comparison differs")
            if filename.startswith("library") and len(report["unexpected"]) != row["library_strict_differences"]:
                raise ValueError("Library baseline count differs")
        try:
            verify_bytes.verify(source, record / "library-candidate.dxf", expected)
            library_bytes = "pass"
        except ValueError:
            library_bytes = "different bytes"
        if library_bytes != row["library_byte_check"] or ch.digest(record / "candidate.dxf") != row["candidate_sha256"]:
            raise ValueError("Retained candidate/baseline result differs")
    if (saved["cases_total"], saved["assets_total"], saved["edits_total"], saved["source_preservation_passes"]) != (6, total_assets, total_edits, 6):
        raise ValueError("Summary totals differ")
    print(f"PASS: 6 source-bound sidecar cases, {total_assets} assets/{total_edits} edits; exact candidates and retained baselines reproduce")
    print("No native CAD UI, visual equivalence or engineering acceptance inferred; browser receipt is separate")


if __name__ == "__main__":
    check()
