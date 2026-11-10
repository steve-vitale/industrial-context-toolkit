"""Reproduce retained development faults in temporary standalone fixture workspaces.

Expected failures are checked for their specific assertions, with no import errors.
This runner never overwrites the current implementation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ("context-core-development-01", ("test_context_basis", "test_context_intake", "test_context_components"), 8),
    ("context-packet-order-01", ("test_context_packet.PacketWorkflowTests.test_prepare_replays_original_column_order_in_new_process",), 1),
    ("correction-physical-lineage-01", ("test_context_components", "test_context_intake"), 8),
    ("helper-annotation-retention-01", ("test_context_packet.PacketWorkflowTests.test_valid_api_annotations_survive_ordinary_edit_and_reimport",), 1),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.absolute()
    if out.exists():
        parser.error("output exists; retain it and choose a new directory")
    out.mkdir(parents=True)
    results = []
    for name, modules, failures in CASES:
        source = ROOT / "examples/map-component-cycle/history" / name
        with tempfile.TemporaryDirectory(prefix="context-history-") as folder:
            workspace = Path(folder)
            scripts = workspace / "scripts"
            scripts.mkdir()
            for path in source.glob("*.py"):
                shutil.copyfile(path, scripts / path.name)
            fixtures = workspace / "examples/map-component-cycle/inputs"
            fixtures.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "examples/map-component-cycle/inputs", fixtures)
            command = [sys.executable, "-B", "-S", "-m", "unittest", "-v", *modules]
            run = subprocess.run(command, cwd=scripts, capture_output=True, timeout=60)
            stderr = run.stderr.decode("utf-8", errors="replace")
            matched = run.returncode == 1 and "errors=" not in stderr and f"failures={failures}" in stderr
            if name != "context-packet-order-01":
                matched = matched and len([s for s in stderr.splitlines() if s.startswith("FAIL:")]) == failures
            else:
                matched = matched and "basis does not reproduce from retained originals/mappings/contributions" in stderr
            (out / (name + "-stdout.txt")).write_bytes(run.stdout)
            (out / (name + "-stderr.txt")).write_bytes(run.stderr)
            results.append({"history": name, "command": command, "exit_code": run.returncode,
                            "expected_assertion_failures": failures, "matched": bool(matched),
                            "sha256_raw": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in source.glob("*.py")}})
    receipt = {"checks": results, "scope": "Historical method reproduces intended failures in standalone temporary fixture workspace; not current candidate failure"}
    (out / "checks.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    matched = all(r["matched"] for r in results)
    print(json.dumps({"historical_cases": len(results), "matched": matched}))
    return 0 if matched else 1


if __name__ == "__main__":
    sys.exit(main())
