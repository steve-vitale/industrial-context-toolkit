"""Replay two retained native returns through the reusable review CLI; expected strict failures stay failures."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import cad_handoff as cad


def replay(out):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Use an unused destination")
    out.mkdir(parents=True)
    source = ROOT / "examples/cad-handoff/source/valve.dxf"
    plan = source.with_name("edit-plan.json")
    native = ROOT / "examples/cad-handoff/native"
    inputs = [source, plan, native / "qcad/returned.dxf", native / "qcad-r15/returned.dxf"]
    pins = {str(p): cad.digest(p) for p in inputs}
    runs, checks = [], {}
    for label, returned, expected, headers in (("default-setting", inputs[2], 335, 54), ("r15-setting", inputs[3], 344, 3)):
        packet = out / label
        args = [sys.executable, "scripts/cad_handoff.py", "review", str(source), str(returned), "--plan", str(plan), "--out", str(packet)]
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=60)
        runs.append({"args": args, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != 1:
            raise ValueError("Expected complete review with strict difference exit 1: " + result.stdout + result.stderr)
        report = json.loads((packet / "review.json").read_text(encoding="utf-8"))
        receipt = json.loads((packet / "receipt.json").read_text(encoding="utf-8"))
        checks[label] = {
            "strict_failure_retained": report["strict_status"] == "differences" and report["strict_difference_count"] == expected,
            "every_entity_difference_partitioned": sum(report["entity_partitions"].values()) == len(report["entity_changes"]) == expected - (2 if label == "default-setting" else 1),
            "header_fields_explained": len(report["header_changes"]) == headers,
            "three_planned_edits_observed": sum(a["status"] == "planned edit observed" for a in report["asset_attributes"]) == 3,
            "no_acceptance": report["acceptance"] == receipt["acceptance"] == "not performed",
            "packet_hashes_verify": all(cad.digest(packet / name) == wanted for name, wanted in receipt["files"].items()),
            "original_drawing_bytes_retained": (packet / "originals/before.dxf").read_bytes() == source.read_bytes() and (packet / "originals/after.dxf").read_bytes() == returned.read_bytes(),
        }
    checks["inputs_unchanged"] = pins == {str(p): cad.digest(p) for p in inputs}
    cad.write_json(out / "replay.json", {"scope": "two exposed fictional native-return controls; not an engineering receiver benchmark", "checks": checks, "runs": runs})
    if not checks["inputs_unchanged"] or not all(all(v.values()) for k, v in checks.items() if k != "inputs_unchanged"):
        raise ValueError(str(checks))
    print("PASS: both expected strict failure exits; 15 exposed packet conditions; original inputs unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    a = parser.parse_args()
    try:
        replay(a.out)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        parser.exit(2, f"ERROR: {e}\n")
