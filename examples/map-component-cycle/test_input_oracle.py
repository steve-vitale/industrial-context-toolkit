"""Challenge the input oracle with actual modified files and intact positive controls."""
import contextlib
import argparse
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("fixture_oracle", HERE / "check_inputs.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def run():
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    records = []
    for label, mutation, expected in (
        ("intact", None, None),
        ("raw-source-tamper", "source", "raw bytes inputs/development/rev1/datasheet.csv"),
        ("tamper-rehashed", "rehashed", "rev1 actual datasheet value/status"),
        ("typed-oracle-change", "typed", "false/zero/null/empty controls remain distinct types"),
        ("independent-record-change", "independent", "rev2 independent records unchanged"),
    ):
        with tempfile.TemporaryDirectory(prefix="input-oracle-", dir=out) as folder:
            target = Path(folder).resolve()
            if not target.is_relative_to(out.resolve()):
                raise ValueError("Temporary case escaped its intended workspace")
            shutil.copytree(HERE / "inputs", target / "inputs")
            shutil.copyfile(HERE / "INPUT-FREEZE.json", target / "INPUT-FREEZE.json")
            changed = None
            if mutation in ("source", "rehashed"):
                changed = target / "inputs/development/rev1/datasheet.csv"
                changed.write_bytes(changed.read_bytes().replace(b",45,", b",999,"))
            elif mutation == "typed":
                changed = target / "inputs/EXPECTED.json"
                key = json.loads(changed.read_bytes())
                key["typed_controls"][0] = 0
                write(changed, key)
            elif mutation == "independent":
                changed = target / "inputs/development/rev2/instruments.csv"
                changed.write_bytes(changed.read_bytes().replace(b",0,60", b",0,61"))
            if changed is not None and mutation != "source":
                pin = target / "INPUT-FREEZE.json"
                freeze = json.loads(pin.read_bytes())
                freeze["input_raw_sha256"][changed.relative_to(target).as_posix()] = hashlib.sha256(changed.read_bytes()).hexdigest()
                write(pin, freeze)
            oracle.HERE, oracle.ROOT = target, ROOT
            failure = None
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    oracle.check_inputs()
            except ValueError as error:
                failure = str(error)
            if expected is None:
                passed = failure is None
            else:
                passed = failure == "Input/key mismatch: " + expected
            records.append({"control": label, "expected": expected, "actual": failure, "passed": passed})
    if not all(r["passed"] for r in records):
        raise AssertionError(json.dumps(records, indent=2))
    return {"checks": len(records), "passed": len(records), "records": records,
            "oracle_sha256_lf": hashlib.sha256((HERE / "check_inputs.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "input_freeze_sha256_lf": hashlib.sha256((HERE / "INPUT-FREEZE.json").read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "scope": "fixture oracle controls, not candidate or product acceptance"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.out is not None and args.out.exists():
        parser.error("Result destination exists; preserve it")
    result = run()
    if args.out is not None:
        write(args.out, result)
    print(json.dumps(result, indent=2))
