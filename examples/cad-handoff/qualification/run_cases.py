"""Run matched saved/library/value-span CAD cases; reserved cases require a frozen method receipt.

No model calls or native trial invocations here. The native receiving gates are separate.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import cad_handoff as ch
import cad_value_patch as patcher
from verify_bytes import verify

METHODS = ["scripts/cad_value_patch.py", "scripts/cad_handoff.py",
           "examples/cad-handoff/qualification/verify_bytes.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run_case(identity, source, planpath, out):
    plan = json.loads(planpath.read_text(encoding="utf-8"))
    before = ch.snapshot(source)
    result = {"case": identity, "source_sha256": ch.digest(source), "routes": {}}
    out.mkdir(parents=True)
    # Matched baseline, including any unexpected serialization changes the guarded product would refuse.
    doc = ch.load(source)
    for handle, change in ch.validate_plan(before, plan).items():
        doc.entitydb[handle].dxf.text = change["after"]
    library = out / "library.dxf"
    doc.saveas(library)
    for route, target in [("library-save", library), ("value-spans", out / "candidate/candidate.dxf")]:
        row = {}
        try:
            if route == "value-spans":
                patcher.apply(source, plan, target.parent)
            comparison = ch.compare(before, ch.snapshot(target), plan)
            row.update(strict_status=comparison["status"], strict_differences=len(comparison["unexpected"]))
            ch.write_json(out / (route+".comparison.json"), comparison)
            try:
                row["byte_check"] = verify(source, target, plan)
            except ValueError as error:
                row["byte_check"] = {"status": "fail", "error": str(error)}
        except (ch.InputError, ch.ezdxf.DXFError, OSError, ValueError) as error:
            row["error"] = str(error)
        result["routes"][route] = row
    ch.write_json(out / "result.json", result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", choices=["development", "reserved-authored"], required=True)
    ap.add_argument("--freeze", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error("Output exists; retain earlier results")
    if args.split != "development":
        if args.freeze is None:
            ap.error("Reserved results require a prior committed freeze receipt")
        freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
        for method in METHODS:
            if freeze["methods"][method] != sha(ROOT / method):
                ap.error("Method changed since freeze: "+method)
    manifest = json.loads((HERE / "fixtures/MANIFEST.json").read_text(encoding="utf-8"))
    args.out.mkdir(parents=True)
    results = []
    for case in manifest["cases"]:
        if case["split"] != args.split:
            continue
        source, plan = HERE / "fixtures" / case["source"], HERE / "fixtures" / case["plan"]
        if ch.digest(source) != case["source_sha256"] or ch.digest(plan) != case["plan_sha256"]:
            ap.error("Frozen case changed: "+case["id"])
        result = run_case(case["id"], source, plan, args.out / case["id"])
        results.append(result)
        print(case["id"], json.dumps(result["routes"]), flush=True)
    if args.split == "development":
        results.append(run_case("original-valve", ROOT / "examples/cad-handoff/source/valve.dxf",
                                ROOT / "examples/cad-handoff/source/edit-plan.json", args.out / "original-valve"))
    ch.write_json(args.out / "results.json", {"split": args.split, "results": results,
                  "method_sha256_lf": {method: sha(ROOT / method) for method in METHODS},
                  "scope": "authored software cases; no native GUI or plant acceptance"})


if __name__ == "__main__":
    main()
