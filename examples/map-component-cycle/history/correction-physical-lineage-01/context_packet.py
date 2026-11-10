"""Portable record-route packets with source replay, derived-view readback and exact originals."""
import base64
import copy
import json
import tempfile
from pathlib import Path, PurePosixPath

import context_basis as cb
import context_components as cc
import context_intake as ci

SCHEMA = "engineering-context-packet-1"
DELIVERY_SCHEMA = "engineering-context-delivery-1"
MAX_PACKET_BYTES = 512 * 1024 * 1024
METHODS = ("context_basis.py", "context_components.py", "context_intake.py", "context_packet.py",
           "context_workflow.py")


def encode(value):
    cb.json_value(value)
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def pins():
    return {name: cb.raw_sha(Path(__file__).with_name(name).read_bytes().replace(b"\r\n", b"\n"))
            for name in METHODS}


def safe_name(name):
    cb.require(type(name) is str and name and "\\" not in name and ":" not in name,
               "unsafe packet path")
    path = PurePosixPath(name)
    cb.require(path.as_posix() == name and not path.is_absolute()
               and not any(p in ("", ".", "..") for p in path.parts), "unsafe packet path")
    return name


def inventory(root):
    root = Path(root).absolute()
    cb.require(root.is_dir() and not root.is_symlink(), "packet needs an ordinary directory")
    files = {}
    folded = set()
    size = 0
    for path in sorted(root.rglob("*")):
        cb.require(not path.is_symlink(), "packet symlinks refused")
        if path.is_file():
            name = safe_name(path.relative_to(root).as_posix())
            cb.require(name.casefold() not in folded, "case-colliding packet paths")
            folded.add(name.casefold())
            size += path.stat().st_size
            cb.require(size <= MAX_PACKET_BYTES, "packet exceeds declared total byte limit")
            files[name] = cb.raw_sha(path.read_bytes())
    return files


def source_bytes(root):
    originals = Path(root) / "originals"
    cb.require(originals.is_dir(), "packet originals unavailable")
    return {name: (originals / name).read_bytes() for name in inventory(originals)}


def check_source_bindings(basis, originals):
    for source in basis["sources"]:
        name = source.get("path")
        if source.get("sha256") is not None:
            cb.require(name in originals and cb.raw_sha(originals[name]) == source["sha256"],
                       "source raw-byte binding mismatch: " + source["id"])


def source_replay(root, config, corrections):
    mapping = cb.read_json(root / "mappings.json")
    basis, originals, actual_mapping = ci.prepare(root / "originals", config["site"], config["plant"],
            previous_mapping=mapping, encoding=config["encoding"], date_format=config["date_format"])
    contribution = root / "contributions.csv"
    if contribution.exists():
        basis = ci.add_contributions(basis, originals, contribution.read_bytes())
    basis["corrections"] = copy.deepcopy(corrections)
    cb.validate(basis)
    return basis, actual_mapping


def open_packet(root, expected_receipt=None):
    root = Path(root).absolute()
    files = inventory(root)
    cb.require("RECEIPT.json" in files, "packet receipt missing")
    receipt_raw = (root / "RECEIPT.json").read_bytes()
    if expected_receipt is not None:
        cb.require(cb.raw_sha(receipt_raw) == expected_receipt, "unexpected packet receipt")
    receipt = cb.read_json(root / "RECEIPT.json")
    cb.require(receipt.get("schema") == SCHEMA, "unsupported packet receipt")
    represented = dict(files)
    represented.pop("RECEIPT.json")
    cb.require(represented == receipt.get("files"), "packet file inventory differs")
    managed = {"basis.json", "drafts.json", "mappings.json", "intake.json", "annotations.json",
               "equipment-instruments.csv", "datasheets.md", "control-outline.md", "contributions.csv",
               "changes.json"}
    cb.require(all(name in managed or name.startswith(("originals/", "previous/"))
                   for name in represented), "unaccounted packet artifact")
    basis, draft = cb.read_json(root / "basis.json"), cb.read_json(root / "drafts.json")
    config = cb.read_json(root / "intake.json")
    cb.require(type(config) is dict and config.get("route") == "records",
               "unsupported packet input route")
    cb.require(cb.digest(basis) == receipt.get("basis_sha256"), "packet basis identity differs")
    cb.validate(basis)
    check_source_bindings(basis, source_bytes(root))
    rebuilt, mapping = source_replay(root, config, basis["corrections"])
    cb.require(cb.canonical(rebuilt) == cb.canonical(basis), "basis does not reproduce from retained originals/mappings/contributions")
    cb.require(cb.canonical(mapping) == cb.canonical(cb.read_json(root / "mappings.json")),
               "mapping interpretation does not reproduce")
    expected = cc.generate(basis, scope=config.get("scope"), item=config.get("item"),
                           annotations=cb.read_json(root / "annotations.json"))
    cb.require(cb.canonical(expected) == cb.canonical(draft), "component views do not reproduce from retained basis")
    for name, text in cc.render(expected).items():
        cb.require((root / name).read_bytes() == text.encode("utf-8"), "readable component differs: " + name)
    depth = receipt.get("history_depth")
    cb.require(type(depth) is int and 0 <= depth <= 8, "unsupported packet history depth")
    if depth:
        previous = root / "previous/RECEIPT.json"
        cb.require(previous.is_file() and cb.raw_sha(previous.read_bytes()) == receipt.get("previous_receipt_sha256"),
                   "previous packet identity differs")
        # Each previous packet is verified too, using its own retained originals.
        prior = open_packet(root / "previous", receipt["previous_receipt_sha256"])
        cb.require(prior["receipt"]["history_depth"] == depth - 1, "history depth disagrees")
        cb.require(prior["basis"]["namespace"] == basis["namespace"], "previous namespace differs")
        cb.require(cb.canonical(cb.read_json(root / "changes.json"))
                   == cb.canonical(cc.changes(prior["draft"], draft)),
                   "revision impact does not reproduce from retained drafts")
    else:
        cb.require(receipt.get("previous_receipt_sha256") is None, "unexpected previous basis")
        cb.require("changes.json" not in files and not any(name.startswith("previous/") for name in files),
                   "unexpected history without declared previous basis")
    return {"root": root, "receipt": receipt, "receipt_sha256": cb.raw_sha(receipt_raw),
            "basis": basis, "draft": draft, "config": config,
            "method_changed": receipt.get("method_sha256_lf") != pins()}


def emit(out, basis, originals, mappings, config, *, contribution=None, annotations=(), previous=None):
    out = Path(out).absolute()
    cb.require(not out.exists(), "output exists; retain it and choose a new directory")
    cb.validate(basis)
    check_source_bindings(basis, originals)
    draft = cc.generate(basis, scope=config.get("scope"), item=config.get("item"), annotations=annotations)
    files = {"basis.json": encode(basis), "drafts.json": encode(draft),
             "mappings.json": encode(mappings), "intake.json": encode(config),
             "annotations.json": encode(list(annotations)),
             **{name: text.encode("utf-8") for name, text in cc.render(draft).items()}}
    if contribution is not None:
        files["contributions.csv"] = contribution
    for name, raw in originals.items():
        files["originals/" + safe_name(name)] = raw
    depth, prior_sha = 0, None
    if previous is not None:
        cb.require(previous["basis"]["namespace"] == basis["namespace"], "previous namespace differs")
        depth = previous["receipt"]["history_depth"] + 1
        cb.require(depth <= 8, "packet history limit reached; use a separately qualified receiving/history route")
        prior_sha = previous["receipt_sha256"]
        for name in inventory(previous["root"]):
            files["previous/" + name] = (previous["root"] / name).read_bytes()
        files["changes.json"] = encode(cc.changes(previous["draft"], draft))
    cb.require(sum(len(raw) for raw in files.values()) <= MAX_PACKET_BYTES, "packet exceeds declared total byte limit")
    names = [safe_name(name) for name in files]
    cb.require(len({name.casefold() for name in names}) == len(names), "case-colliding packet outputs")
    receipt = {"schema": SCHEMA, "basis_sha256": cb.digest(basis), "method_sha256_lf": pins(),
               "files": {name: cb.raw_sha(raw) for name, raw in files.items()},
               "history_depth": depth, "previous_receipt_sha256": prior_sha,
               "source_authority": "Owner/review declarations; no authenticated engineering release",
               "access": "Whole supplied source files are private local originals; selecting items is not source-file access filtering",
               "product_receiving": "not established by this local packet"}
    files["RECEIPT.json"] = encode(receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".context-", dir=out.parent) as temporary:
        stage = Path(temporary).resolve() / "packet"
        cb.require(stage.parent.is_relative_to(out.parent.resolve()), "staging escaped output parent")
        stage.mkdir()
        for name, raw in files.items():
            destination = stage.joinpath(*PurePosixPath(name).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        open_packet(stage)
        cb.require(not out.exists(), "output appeared during preparation; refusing replacement")
        stage.rename(out)
    return out


def prepare(records, out, site, plant, *, previous=None, mapping=None, contribution=None,
            scope=None, item=None, encoding="utf-8-sig", date_format="ISO"):
    cb.require(not Path(out).exists(), "output exists; choose a new directory")
    old = open_packet(previous) if previous is not None else None
    saved = cb.read_json(mapping) if mapping is not None else (
        cb.read_json(old["root"] / "mappings.json") if old is not None else None)
    basis, originals, mappings = ci.prepare(records, site, plant, previous_mapping=saved,
                                            encoding=encoding, date_format=date_format)
    raw = Path(contribution).read_bytes() if contribution is not None else None
    if raw is not None:
        basis = ci.add_contributions(basis, originals, raw)
    annotations = []
    if old is not None:
        basis["corrections"] = copy.deepcopy(old["basis"]["corrections"])
        retained = {a["id"]: a for a in basis["corrections"]}
        for wrapped in old["draft"]["annotations"]:
            annotation = wrapped["annotation"]
            cb.require(annotation["id"] not in retained
                       or cb.canonical(retained[annotation["id"]]) == cb.canonical(annotation),
                       "conflicting retained editorial annotation")
            if annotation["id"] not in retained:
                basis["corrections"].append(copy.deepcopy(annotation))
                retained[annotation["id"]] = annotation
    config = {"route": "records", "site": site, "plant": plant, "encoding": encoding,
              "date_format": date_format, "scope": scope, "item": item}
    return emit(out, basis, originals, mappings, config, contribution=raw, annotations=annotations, previous=old)


def write_edited(packet, out, *, annotation=None, draft=None):
    old = open_packet(packet)
    basis = copy.deepcopy(old["basis"])
    if draft is not None:
        basis = cc.reimport(basis, cb.read_json(draft))
    if annotation is not None:
        checked = cc.new_annotation(old["basis"], annotation.get("subject"), annotation.get("field"),
                                    annotation.get("value"), annotation.get("rationale"))
        cb.require(cb.canonical(checked) == cb.canonical(annotation), "editorial annotation basis mismatch")
        existing = {a["id"]: a for a in basis["corrections"]}
        cb.require(annotation["id"] not in existing or cb.canonical(existing[annotation["id"]])
                   == cb.canonical(annotation), "conflicting editorial annotation")
        if annotation["id"] not in existing:
            basis["corrections"].append(copy.deepcopy(annotation))
    contribution = old["root"] / "contributions.csv"
    return emit(out, basis, source_bytes(old["root"]), cb.read_json(old["root"] / "mappings.json"),
                old["config"], contribution=contribution.read_bytes() if contribution.exists() else None,
                previous=old)


def bundle(packet, destination, limit=25 * 1024 * 1024):
    opened = open_packet(packet)
    destination = Path(destination).absolute()
    cb.require(not destination.exists(), "delivery destination exists; retain it")
    require_files = inventory(opened["root"])
    delivery = {"schema": DELIVERY_SCHEMA, "packet_receipt_sha256": opened["receipt_sha256"],
                "source_access": "Full retained originals; owner/private processing only until explicit permitted sharing",
                "files": [{"path": name, "sha256": digest, "encoding": "base64",
                           "data": base64.b64encode((opened["root"] / name).read_bytes()).decode("ascii")}
                          for name, digest in require_files.items()],
                "receiving": "This is a portable payload, not proof that a managed service has accepted it."}
    raw = encode(delivery)
    cb.require(type(limit) is int and limit > 0 and len(raw) <= limit, "delivery exceeds declared receiving byte limit; choose a permitted smaller scope/qualified route")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".context-delivery-", dir=destination.parent) as folder:
        temp = Path(folder)
        cb.require(temp.resolve().is_relative_to(destination.parent.resolve()), "delivery staging escaped parent")
        file = temp / "delivery.json"
        file.write_bytes(raw)
        cb.require(not destination.exists(), "delivery destination appeared; refusing replacement")
        file.rename(destination)
    return {"bytes": len(raw), "sha256": cb.raw_sha(raw), "packet_receipt_sha256": opened["receipt_sha256"]}


def unbundle(delivery, out, *, expected_sha256=None):
    """Reopen a complete private portable delivery without its original workspace."""
    delivery, out = Path(delivery).absolute(), Path(out).absolute()
    cb.require(not out.exists(), "output exists; retain it and choose a new directory")
    cb.require(delivery.stat().st_size <= cb.MAX_BYTES, "delivery exceeds declared JSON byte limit")
    if expected_sha256 is not None:
        cb.require(cb.raw_sha(delivery.read_bytes()) == expected_sha256, "unexpected delivery identity")
    doc = cb.read_json(delivery)
    cb.require(type(doc) is dict and doc.get("schema") == DELIVERY_SCHEMA, "unsupported portable delivery")
    cb.require(type(doc.get("files")) is list and doc["files"], "portable delivery needs files")
    files, folded, total = {}, set(), 0
    for row in doc["files"]:
        cb.require(type(row) is dict and row.get("encoding") == "base64", "unsupported delivery file encoding")
        name = safe_name(row.get("path"))
        cb.require(name.casefold() not in folded, "duplicate or case-colliding delivery path")
        folded.add(name.casefold())
        try:
            raw = base64.b64decode(row.get("data"), validate=True)
        except (ValueError, TypeError) as error:
            raise cb.ContextError("invalid delivery base64") from error
        cb.require(cb.raw_sha(raw) == row.get("sha256"), "delivery raw-byte binding mismatch")
        total += len(raw)
        cb.require(total <= MAX_PACKET_BYTES, "delivery exceeds declared decoded byte limit")
        files[name] = raw
    cb.require("RECEIPT.json" in files and cb.raw_sha(files["RECEIPT.json"])
               == doc.get("packet_receipt_sha256"), "delivery receipt identity differs")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".context-reopen-", dir=out.parent) as temporary:
        stage = Path(temporary).resolve() / "packet"
        cb.require(stage.parent.is_relative_to(out.parent.resolve()), "reopen staging escaped parent")
        stage.mkdir()
        for name, raw in files.items():
            destination = stage.joinpath(*PurePosixPath(name).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        opened = open_packet(stage, doc["packet_receipt_sha256"])
        cb.require(not out.exists(), "output appeared during reopening; refusing replacement")
        stage.rename(out)
    return {"packet": str(out), "receipt_sha256": opened["receipt_sha256"],
            "product_receiving": "not established by local reopening"}

