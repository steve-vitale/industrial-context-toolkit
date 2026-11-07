"""Run every predeclared procedural sidecar case beside the unchanged library-save baseline."""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cad_exchange as ce
import cad_handoff as ch
import verify_bytes


def run(out):
    out = Path(out)
    if out.exists():
        raise ValueError("Use a new results directory")
    inputs = ce.read_json(HERE / "exchange-6/INPUTS.json")
    rows = []
    with tempfile.TemporaryDirectory(prefix="ict-exchange-six-") as tmp:
        stage = Path(tmp) / "results"
        stage.mkdir()
        for case in inputs["cases"]:
            source = HERE / "exchange-6" / case["source"]
            key = HERE / "exchange-6" / case["plan"]
            if ch.digest(source) != case["source_sha256"] or ch.digest(key) != case["plan_sha256"]:
                raise ValueError("Predeclared source/key changed: " + case["id"])
            target = stage / case["id"]
            target.mkdir()
            expected = ce.read_json(key)
            data = ce.prepare(source, target / "exchange")
            response = ce.response_for(data, expected["changes"])
            ch.write_json(target / "response.json", response)
            code = ce.main(["apply", str(source), str(target / "exchange/exchange.json"),
                            str(target / "response.json"), "--out", str(target / "draft")])
            if code != 0:
                raise ValueError("Sidecar CLI failed: " + case["id"])
            draft = target / "draft"
            if ce.read_json(draft / "plan.json") != expected:
                raise ValueError("Plan differs from predeclared key")
            byte_result = verify_bytes.verify(source, draft / "candidate.dxf", expected)
            strict = ce.read_json(draft / "comparison.json")
            library = target / "library"
            library.mkdir()
            doc = ch.load(source)
            for handle, change in ch.validate_plan(ch.snapshot(source), expected).items():
                doc.entitydb[handle].dxf.text = change["after"]
            doc.saveas(library / "candidate.dxf")
            baseline = ch.compare(ch.snapshot(source), ch.snapshot(library / "candidate.dxf"), expected)
            ch.write_json(library / "comparison.json", baseline)
            try:
                verify_bytes.verify(source, target / "library/candidate.dxf", expected)
                baseline_raw = "pass"
            except ValueError:
                baseline_raw = "different bytes"
            row = {"id": case["id"], "source_sha256": ch.digest(source),
                   "candidate_sha256": ch.digest(draft / "candidate.dxf"),
                   "assets": len(data["assets"]), "edits": len(expected["changes"]),
                   "sidecar_strict_differences": len(strict["unexpected"]), "byte_check": byte_result,
                   "library_strict_differences": len(baseline["unexpected"]), "library_byte_check": baseline_raw}
            ch.write_json(target / "byte-check.json", byte_result)
            # Retain exact outputs and comparisons, without duplicating large source snapshots/catalog packets.
            for origin, destination in ((draft / "candidate.dxf", target / "candidate.dxf"),
                                        (draft / "comparison.json", target / "comparison.json"),
                                        (target / "library/candidate.dxf", target / "library-candidate.dxf"),
                                        (target / "library/comparison.json", target / "library-comparison.json")):
                shutil.copyfile(origin, destination)
            # Temporary packet directories are inside this function's private temporary directory only.
            shutil.rmtree(target / "exchange")
            shutil.rmtree(target / "draft")
            shutil.rmtree(target / "library")
            rows.append(row)
        summary = {"schema": "cad-exchange-six-results-1", "cases": rows,
                   "cases_total": len(rows), "assets_total": sum(r["assets"] for r in rows),
                   "edits_total": sum(r["edits"] for r in rows),
                   "source_preservation_passes": sum(r["sidecar_strict_differences"] == 0 and r["byte_check"]["status"] == "pass" for r in rows),
                   "scope": "Same-author procedural equipment-data exchange; not native UI, visual or engineering acceptance"}
        ch.write_json(stage / "summary.json", summary)
        shutil.copytree(stage, out)
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.out), indent=2))
