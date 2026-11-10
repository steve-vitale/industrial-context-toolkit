"""Replay supplied document/drawing interpretations as portable engineering context.

Standard library only. No model calls, account, product import, drawing reader or
native CAD session. Existing original fixtures and preimplementation keys stay
separate from generated answers. This is an exposed development replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
INPUT = Path(__file__).resolve().parent / "inputs/entry-jobs"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.absolute()
    if out.exists():
        parser.error("Output exists; retain it and choose a new directory")
    out.mkdir(parents=True)
    commands = []
    manifest = load(INPUT / "INPUTS.json")
    for name, expected in manifest["files"].items():
        if sha((INPUT / name).read_bytes()) != expected:
            raise ValueError("Prepared input/key bytes changed: " + name)
    document = load(INPUT / "DOCUMENT-ORACLE.json")
    drawing = load(INPUT / "DRAWING-ORACLE.json")

    def run(label, *arguments):
        command = [sys.executable, "-B", "-S", "scripts/context_workflow.py",
                   *(str(value) for value in arguments)]
        start = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        (out / (label + ".stdout.json")).write_bytes(result.stdout)
        (out / (label + ".stderr.txt")).write_bytes(result.stderr)
        commands.append({"label": label, "command": command,
                         "exit_code": result.returncode,
                         "seconds": time.perf_counter() - start})
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n",
                                           encoding="utf-8")
        if result.returncode != 0:
            raise ValueError("Command failed; inspect retained output: " + label)
        return json.loads(result.stdout)

    def stage(name, sources, register):
        folder = out / name
        folder.mkdir()
        for filename, (origin, expected) in sources.items():
            raw = (ROOT / origin).read_bytes()
            if sha(raw) != expected:
                raise ValueError("Original source bytes changed: " + origin)
            (folder / filename).write_bytes(raw)
        shutil.copyfile(INPUT / register, folder / "source-register.csv")
        return folder

    def field(label, packet, item, predicate, expected):
        answer = run(label, "query", packet, "--item", item, "--field", predicate)
        values = [row["value"] for row in answer["alternatives"]]
        if len(values) != 1 or type(values[0]) is not type(expected) or values[0] != expected:
            raise ValueError("Original literal/type mismatch: " + label)
        if not all(row["source_lineage"] and row["locator"] for row in answer["alternatives"]):
            raise ValueError("Source lineage missing: " + label)
        return answer

    def roundtrip(label, packet, records):
        delivery = out / (label + ".context.json")
        bundled = run(label + "-bundle", "bundle", packet, "--out", delivery)
        # Withhold the preparation folder before a separate process reopens.
        records.rename(out / (records.name + "-withheld"))
        reopened = out / (label + "-reopened")
        run(label + "-unbundle", "unbundle", delivery, "--out", reopened,
            "--expected-sha256", bundled["sha256"])
        run(label + "-verify", "verify", reopened)
        inventory = lambda folder: {p.relative_to(folder).as_posix(): p.read_bytes()
                                    for p in folder.rglob("*") if p.is_file()}
        if inventory(packet) != inventory(reopened):
            raise ValueError("Portable packet files changed: " + label)
        return reopened

    records = stage("document-records", {
        name: ("examples/engineering-onboarding/sources/" + name, expected)
        for name, expected in document["source_sha256"].items()
    }, "document-source-register.csv")
    packet = out / "document-packet"
    run("document-prepare", "prepare", "--records", records, "--site", "DOC",
        "--plant", "P1", "--contributions", INPUT / "document-interpretation.csv",
        "--out", packet)
    for predicate, expected in document["B_values"].items():
        field("document-" + predicate, packet, document["B_subject"], predicate, expected)
    field("document-peer", packet, "DOC/P1/documents/PEER", "reason_verified", False)
    reopened = roundtrip("document", packet, records)
    field("document-reopened-value", reopened, document["B_subject"], "reported_result", "2.5")

    previous = None
    for revision in drawing["revisions"]:
        number = revision["revision"]
        records = stage("drawing-records-" + number, {
            name: (metadata["origin"], metadata["sha256"])
            for name, metadata in revision["source_pins"].items()
        }, "drawing-source-register-r" + number + ".csv")
        packet = out / ("drawing-packet-" + number)
        arguments = ["prepare", "--records", records, "--site", "DRAW", "--plant", "P1",
                     "--contributions", INPUT / ("drawing-interpretation-r" + number + ".csv"),
                     "--out", packet]
        if previous is not None:
            arguments += ["--previous", previous]
        run("drawing-prepare-" + number, *arguments)
        expected = drawing["fixed_findings"]["initial_model" if number == "1" else "next_model"]
        field("drawing-model-" + number, packet, drawing["subject"], "returned_model", expected)
        field("drawing-serial-" + number, packet, "DRAW/P1/validation-braces/asset-2",
              "returned_serial", drawing["fixed_findings"]["unrequested_serial"])
        if previous is not None:
            changed = run("drawing-compare", "compare", previous, packet)
            # Full comparison output is retained for inspection; component-only
            # changes cannot by themselves establish this custom-field finding.
            claims = changed.get("basis_changes", {}).get("claims", [])
            model_changes = [row for row in claims if row.get("subject") == drawing["subject"]
                             and row.get("predicate") == "returned_model"]
            if len(model_changes) != 1 or model_changes[0].get("change") != "content_changed":
                raise ValueError("Exact returned-model content change missing")
            for side, value in [("before", "OTHER-CHOICE"), ("after", "Assembly {D}")]:
                if [row["value"] for row in model_changes[0][side]["alternatives"]] != [value]:
                    raise ValueError("Returned-model comparison lost original values")
        previous = packet
        records.rename(out / (records.name + "-withheld"))
    # Both original drawing preparation folders are already withheld.
    delivery = out / "drawing.context.json"
    bundled = run("drawing-bundle", "bundle", packet, "--out", delivery)
    reopened = out / "drawing-reopened"
    run("drawing-unbundle", "unbundle", delivery, "--out", reopened,
        "--expected-sha256", bundled["sha256"])
    run("drawing-verify", "verify", reopened)
    inventory = lambda folder: {p.relative_to(folder).as_posix(): p.read_bytes()
                                for p in folder.rglob("*") if p.is_file()}
    if inventory(packet) != inventory(reopened):
        raise ValueError("Drawing history/original packet files changed")
    field("drawing-reopened-value", reopened, drawing["subject"], "returned_model", "Assembly {D}")
    field("drawing-history-value", reopened / "previous", drawing["subject"], "returned_model", "OTHER-CHOICE")
    receipt = {"schema": "entry-context-replay-1", "passed": True,
               "commands": len(commands), "supplied_interpretation_rows": {"document": 7, "drawing_per_revision": 4},
               "source_register_rows": {"document": 4, "drawing_per_revision": 3},
               "customer_json_edits": 0, "account_required": False,
               "qualification": "Exposed supplied-interpretation development replay; no new reading, native CAD or product receiving acceptance; human effort unmeasured"}
    (out / "RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "out": str(out), "commands": len(commands)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
