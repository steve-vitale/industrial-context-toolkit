"""Retain the common-basis development regressions and actual fresh-process command evidence.

This is not the frozen transfer, full-goal acceptance or ChangePilot receiving run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("test_context_basis", "test_context_intake", "test_context_components", "test_context_packet")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.absolute()
    if out.exists():
        parser.error("output exists; retain it and choose a new directory")
    out.mkdir(parents=True)
    paths = [ROOT / "scripts" / (name + ".py") for name in MODULES]
    paths += sorted((ROOT / "scripts").glob("context_*.py"))
    paths += [Path(__file__), ROOT / "examples/map-component-cycle/inputs/EXPECTED.json"]
    pins = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in paths}
    command = [sys.executable, "-B", "-S", "-m", "unittest", "-v", *MODULES]
    environment = dict(os.environ, CONTEXT_TEST_EVIDENCE=str(out / "commands-and-artifacts"))
    started = time.perf_counter()
    run = subprocess.run(command, cwd=ROOT / "scripts", env=environment, capture_output=True)
    elapsed = time.perf_counter() - started
    (out / "stdout.txt").write_bytes(run.stdout)
    (out / "stderr.txt").write_bytes(run.stderr)
    receipt = {"schema": "context-development-replay-1", "command": command, "cwd": "scripts",
               "exit_code": run.returncode, "elapsed_seconds": elapsed, "python": sys.version,
               "platform": platform.platform(), "method_sha256_lf": pins,
               "scope": "Development fictional-source software tests only; not transfer, human benefit, plant truth or product receiving",
               "goal_acceptance": "31 required cases remain incomplete pending full retained evidence"}
    (out / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run.stderr.decode("utf-8", errors="replace"))
    print(json.dumps({"exit_code": run.returncode, "evidence": str(out), "seconds": elapsed}))
    return run.returncode


if __name__ == "__main__":
    sys.exit(main())
