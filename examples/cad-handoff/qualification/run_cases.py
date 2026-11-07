"""Run matched saved/library/value-span CAD cases; reserved cases require a frozen method receipt.

No model calls or native trial invocations here. The native receiving gates are separate.
"""
import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import cad_handoff as ch
import cad_value_patch as patcher
from verify_bytes import verify

METHODS = ["scripts/cad_value_patch.py", "scripts/cad_handoff.py",
           "examples/cad-handoff/qualification/verify_bytes.py",
           "examples/cad-handoff/qualification/run_cases.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def run_case(identity, source, planpath, out):
    plan = json.loads(planpath.read_text(encoding="utf-8"))
    before = ch.snapshot(source)
    result = {"case": identity, "source_sha256": ch.digest(source), "routes": {}}
    out.mkdir(parents=True)
    library = out / "library.dxf"
    for route, target in [("library-save", library), ("value-spans", out / "candidate/candidate.dxf")]:
        row = {}
        try:
            if route == "library-save":
                # Retain an unguarded save baseline, even when the guarded product would refuse it.
                doc = ch.load(source)
                for handle, change in ch.validate_plan(before, plan).items():
                    doc.entitydb[handle].dxf.text = change["after"]
                doc.saveas(library)
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
    ap.add_argument("--split", choices=["development", "exposed-regression", "reserved-authored", "public-adapted"], required=True)
    ap.add_argument("--manifest", type=Path, default=HERE / "fixtures/MANIFEST.json")
    ap.add_argument("--freeze", type=Path)
    ap.add_argument("--admission", type=Path, help="prior derived-manifest receipt for public adaptations")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error("Output exists; retain earlier results")
    if args.split in {"reserved-authored", "public-adapted"}:
        if args.freeze is None:
            ap.error("Reserved results require a prior committed freeze receipt")
        freeze = json.loads(args.freeze.read_text(encoding="utf-8"))
        if not set(METHODS).issubset(freeze["methods"]):
            ap.error("Freeze omits required preservation/comparison methods")
        for method, wanted in freeze["methods"].items():
            if wanted != sha(ROOT / method):
                ap.error("Method changed since freeze: "+method)
        relative = args.manifest.resolve().relative_to(ROOT).as_posix()
        if args.split == "reserved-authored" and freeze["manifests"].get(relative) != sha(args.manifest):
            ap.error("Authored manifest does not match the prior freeze")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.split == "public-adapted":
        if args.admission is None:
            ap.error("Public adaptations require a receipt frozen before candidate execution")
        admission = json.loads(args.admission.read_bytes())
        if admission.get("freeze_sha256_lf") != sha(args.freeze) or admission.get("manifest_sha256_lf") != sha(args.manifest):
            ap.error("Public adaptation receipt does not bind this freeze and manifest")
        adaptation = manifest["adaptation"]
        selected = adaptation["selection"]
        recipe = "examples/cad-handoff/qualification/adapt_public.py"
        if (freeze["manifests"].get(selected) != sha(ROOT / selected)
                or adaptation["selection_sha256_lf"] != sha(ROOT / selected)
                or adaptation["freeze_sha256_lf"] != sha(args.freeze)
                or adaptation["recipe_sha256_lf"] != freeze["methods"].get(recipe)):
            ap.error("Public selection or adaptation recipe differs from prior freeze")
        original = json.loads((ROOT / selected).read_bytes())
        if [(c["id"], c["source_sha256"]) for c in original["cases"]] != [
                (c["id"], c["original_sha256"]) for c in manifest["cases"]]:
            ap.error("Derived cohort omits, adds or changes selected originals")
    chosen = [c for c in manifest["cases"] if args.split == "exposed-regression" or c["split"] == args.split]
    if not chosen:
        ap.error("No selected cases; an empty cohort is not a pass")
    args.out.mkdir(parents=True)
    results = []
    for case in chosen:
        if case.get("admission_error"):
            result = {"case": case["id"], "routes": {}, "stage": "public adaptation",
                      "error": case["admission_error"]}
            caseout = args.out / case["id"]
            caseout.mkdir()
            ch.write_json(caseout / "result.json", result)
            results.append(result)
            print(case["id"], result["error"], flush=True)
            continue
        source, plan = args.manifest.parent / case["source"], args.manifest.parent / case["plan"]
        if ch.digest(source) != case["source_sha256"] or ch.digest(plan) != case["plan_sha256"]:
            ap.error("Frozen case changed: "+case["id"])
        try:
            result = run_case(case["id"], source, plan, args.out / case["id"])
        except (ch.InputError, ch.ezdxf.DXFError, OSError, ValueError) as error:
            result = {"case": case["id"], "source_sha256": ch.digest(source), "routes": {},
                      "error": type(error).__name__+": "+str(error), "traceback": traceback.format_exc()}
            caseout = args.out / case["id"]
            caseout.mkdir(exist_ok=True)
            ch.write_json(caseout / "result.json", result)
        results.append(result)
        print(case["id"], json.dumps(result["routes"]), flush=True)
    if args.split == "development" and args.manifest.resolve() == (HERE / "fixtures/MANIFEST.json").resolve():
        results.append(run_case("original-valve", ROOT / "examples/cad-handoff/source/valve.dxf",
                                ROOT / "examples/cad-handoff/source/edit-plan.json", args.out / "original-valve"))
    ch.write_json(args.out / "results.json", {"split": args.split, "results": results,
                  "method_sha256_lf": {method: sha(ROOT / method) for method in METHODS},
                  "scope": "authored software cases; no native GUI or plant acceptance"})
    return int(any(r.get("error") or r["routes"].get("value-spans", {}).get("error")
                   or r["routes"].get("value-spans", {}).get("strict_status") != "pass"
                   or r["routes"].get("value-spans", {}).get("byte_check", {}).get("status") != "pass"
                   for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
