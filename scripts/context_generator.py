"""Bounded equipment-only projection to the existing process-model generator.

The canonical basis retains engineering evidence; the generated model is a partial
view. No topology, signals, installed state or authenticated review is inferred.
"""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import context_basis as cb
import context_packet as cp
import generate as consumer

SCHEMA = "engineering-generator-projection-1"
RECEIPT_SCHEMA = "engineering-generator-bundle-1"
METHODS = ("context_generator.py", "generate.py", "pi_mapping.py", "provenance.py", "output_paths.py")
QUALIFICATION = ("Equipment-only source-declared scaffold; no topology, instruments, signals, operating strategy, "
                 "installed truth or authenticated engineering acceptance. Original bytes remain in the input packet.")
README = """# Partial equipment scaffold from retained context

model.json projects only supported, unambiguous source-declared equipment class
and description from the selected context. projection.json reverses every safe
export ID to the exact scoped identity and retains the selected context evidence,
unknowns, disagreements, omissions and editorial proposals. All equipment remains
unverified. This derived view adds no independent corroboration.

The original packet remains the home of exact source bytes, history and three
component drafts. This output is not a self-contained original-source transfer.
Reopen that packet to inspect the original files and compare revisions.

generated/ was actually produced by the existing scripts/generate.py consumer.
Human SVG labels and export descriptions retain the source tag, scope and name;
the safe machine keys remain unchanged. Wrapped SVG label lengths and canvases
are bounded by the optional consumer presentation contract, not engineering facts.
The overview's automatic x/y positions are presentation, not engineering layout.
No process stream, instrument, final element or measurement binding is projected.
Ignition UDT types have an empty BasePath default and OPCServer default
"Ignition OPC UA Server"; instances have generated BasePath values in the form
"ns=1;s=context_<basis digest>.<safe equipment key>".
These nonempty defaults are consumer placeholders, not supplied site addresses
or working connections. There are no atomic measurement tags. PI rows are
equipment-only staging. Platform imports, CAD, plant truth and engineering acceptance are untested.

Reproduce with the same packet and pinned tools in a fresh output directory:
python -B -S scripts/context_workflow.py generate PACKET --out NEW-DIRECTORY
Check source, model, projection and actual consumer files:
python -B -S scripts/context_workflow.py verify-generated PACKET OUTPUT-DIRECTORY
A tool/source revision requires a fresh projection; do not overwrite this evidence.
"""


def pins():
    return {**cp.pins(), **{name: cb.raw_sha(Path(__file__).with_name(name).read_bytes().replace(b"\r\n", b"\n"))
                           for name in METHODS}}


def export_id(subject):
    """Safe deterministic presentation identifier; the projection map is reversible."""
    return "CTX_" + cb.raw_sha(subject.encode("utf-8"))


def usable_text(value):
    return (type(value) is str and value == value.strip() and bool(value)
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
            and not value.startswith(("=", "+", "-", "@")))


def required_text(view, subject, predicate):
    field = view.field(subject, predicate)
    if field["state"] != "sourced_unreviewed":
        return None, predicate + ": " + field["state"]
    rows = [r for r in field["alternatives"] if r["active_source"]]
    if any(r["role"] not in ("source_statement", "export_record", "supplied_interpretation") or r["review"]["status"] == "proposed"
           or r.get("unit") not in (None, "") for r in rows):
        return None, predicate + ": unsupported/proposed declaration or unit"
    values = [r["value"] for r in rows]
    if not all(usable_text(v) for v in values) or len({cb.canonical(v) for v in values}) != 1:
        return None, predicate + ": unsupported exact text"
    return values[0], None


def project(opened):
    """Project a verified packet's exact draft selection, never an implicit wider scope."""
    basis, draft = opened["basis"], opened["draft"]
    view = cb.View(basis)
    cb.require(draft["basis_sha256"] == cb.digest(basis), "draft/basis identity mismatch")
    selected = draft["selection"]["entities"]
    cb.require(type(selected) is list and selected == sorted(set(selected))
               and all(s in view.entities for s in selected), "invalid selected identities")
    units, omitted, identity_map, context = [], [], {}, {}
    for subject in selected:
        entity = view.entities[subject]
        context[subject] = view.inspect(subject)
        reasons = []
        if entity["identity_role"] != "functional_position":
            reasons.append("equipment-only functional-position projection; identity role " + entity["identity_role"])
        if entity["scope"] == basis["namespace"] or not entity["scope"].startswith(basis["namespace"] + "/"):
            reasons.append("explicit unit/area scope required; no owning unit guessed")
        cls, class_error = required_text(view, subject, "class")
        name, name_error = required_text(view, subject, "description")
        reasons += [error for error in (class_error, name_error) if error]
        if cls is not None and cls not in consumer.SYMBOLS:
            reasons.append("class unsupported by existing generate.SYMBOLS: " + cls)
        if reasons:
            omitted.append({"subject": subject, "reasons": reasons})
            continue
        identifier = export_id(subject)
        cb.require(identifier not in identity_map, "safe export identity collision")
        if not usable_text(entity["tag"]) or len(entity["tag"]) > 2048 or len(entity["scope"]) > 2048 or len(name) > 4096:
            omitted.append({"subject": subject, "reasons": ["source tag/scope/name exceeds bounded presentation contract or contains unsupported text"]})
            continue
        identity_map[identifier] = copy.deepcopy(entity)
        units.append({"id": identifier, "name": name, "type": cls,
                      "presentation": {"tag": entity["tag"], "scope": entity["scope"]},
                      "source": "projection.json#/context/" + subject.replace("~", "~0").replace("/", "~1") + " (source declarations; unverified)",
                      "verification": {"status": "unverified"}})
    model = {"meta": {"model_id": "context_" + cb.digest(basis)[:24],
                      "title": "Partial equipment scaffold from engineering context",
                      "source_document": "projection.json; input packet " + opened["receipt_sha256"],
                      "context_basis_sha256": cb.digest(basis), "projection_schema": SCHEMA,
                      "qualification": QUALIFICATION},
             "units": units, "streams": [], "instruments": [], "final_elements": []}
    projection = {"schema": SCHEMA, "basis_sha256": cb.digest(basis),
                  "input_packet_receipt_sha256": opened["receipt_sha256"],
                  "selection": copy.deepcopy(draft["selection"]), "identity_map": identity_map,
                  "context": context, "omissions": omitted,
                  "basis_omissions": copy.deepcopy(basis["omissions"]),
                  "editorial_proposals": copy.deepcopy(draft["annotations"]),
                  "model_sha256": cb.digest(model), "qualification": QUALIFICATION,
                  "presentation": "Existing consumer automatic positions and connection-template placeholders are presentation, not supplied engineering facts."}
    return model, projection


def run_consumer(model_path, destination):
    command = [sys.executable, "-B", "-S", str(Path(__file__).with_name("generate.py")),
               str(model_path), "--out", str(destination)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=300,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired as error:
        raise cb.ContextError("existing generator exceeded bounded 300-second execution") from error
    cb.require(result.returncode == 0, "existing generator refused projected model: " + result.stderr.decode("utf-8", "replace")[:2000])
    return result


def expected_files(opened, folder):
    model, projection = project(opened)
    cb.require(bool(model["units"]), "no supported unambiguous equipment; inspect source class/name/scope, no defaults invented")
    # The consumer owns display placement. The projected model itself has no x/y.
    cb.require(not consumer.validate(consumer._auto_layout(consumer._mark_finals(model))),
               "projected equipment failed existing process-model validator")
    model_path = folder / "model.json"
    model_path.write_bytes(cp.encode(model))
    (folder / "projection.json").write_bytes(cp.encode(projection))
    (folder / "README.md").write_text(README, encoding="utf-8", newline="\n")
    result = run_consumer(model_path, folder / "generated")
    # Execution output is informative and intentionally outside engineering data.
    (folder / "generator.stdout.txt").write_bytes(result.stdout.replace(str(folder).encode(), b"OUTPUT"))
    files = cp.inventory(folder)
    receipt = {"schema": RECEIPT_SCHEMA, "basis_sha256": cb.digest(opened["basis"]),
               "input_packet_receipt_sha256": opened["receipt_sha256"],
               "method_sha256_lf": pins(), "files": files, "qualification": QUALIFICATION}
    (folder / "RECEIPT.json").write_bytes(cp.encode(receipt))
    cp.inventory(folder)  # enforce existing total byte and symlink bounds including receipt
    return receipt


def verify(packet, output):
    opened = cp.open_packet(packet)
    output = Path(output).absolute()
    actual = cp.inventory(output)
    receipt = cb.read_json(output / "RECEIPT.json")
    cb.require(receipt.get("schema") == RECEIPT_SCHEMA, "unsupported generator bundle")
    cb.require(receipt.get("method_sha256_lf") == pins(), "generator method changed; retain old output and create a new projection")
    with tempfile.TemporaryDirectory(prefix=".generator-replay-") as temporary:
        expected = Path(temporary)
        expected_files(opened, expected)
        wanted = cp.inventory(expected)
        cb.require(actual == wanted, "generated bundle/source projection does not replay; changed, missing or extra artifact")
    return {"verified": True, "basis_sha256": cb.digest(opened["basis"]),
            "input_packet_receipt_sha256": opened["receipt_sha256"],
            "generated_files": len(actual), "qualification": QUALIFICATION}


def write(packet, output):
    opened = cp.open_packet(packet)
    output = Path(output).absolute()
    cb.require(not output.exists() and not output.is_symlink(), "output exists; choose a new directory")
    cb.require(not output.resolve().is_relative_to(opened["root"].resolve()), "generator output must be outside input packet")
    cb.require(not any(p.is_symlink() for p in output.parents), "symlink output ancestor refused")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".generator-stage-", dir=output.parent) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        receipt = expected_files(opened, stage)
        verify(packet, stage)
        cb.require(not output.exists() and not output.is_symlink(), "output appeared; refusing replacement")
        stage.rename(output)
    return {"output": str(output), "basis_sha256": receipt["basis_sha256"],
            "units": len(cb.read_json(output / "model.json")["units"]),
            "qualification": QUALIFICATION}
