"""Explicit scoped projection/replay; whole included files are never row-redacted."""
import copy
import csv
import io
import json
import re
import tempfile
from pathlib import Path

import context_basis as cb
import context_components as cc
import context_intake as ci

SCHEMA = "engineering-context-scope-1"
ROUTE = "records_scoped_v1"
INCREMENTAL_SCHEMA = "engineering-context-incremental-history-1"
INCREMENTAL_KEYS = {"schema", "previous_scoped_receipt_sha256", "previous_original_receipt_sha256"}
MATERIALIZATION_SCHEMA = "engineering-scoped-component-materialization-1"
QUALIFICATION = ("Included source files are whole and may contain unrelated rows, columns or text; "
                 "no row redaction or authorization grant. Unrelated structured content and files are omitted.")
CORRECTION_QUALIFICATION = ("selected_field_source_replay_only; original correction and parent basis commitment "
                           "retained; original whole parent basis digest and authentic origin not verified")
HASH = re.compile(r"[0-9a-f]{64}\Z")
MANIFEST_KEYS = {"schema", "request", "source_packet_receipt_sha256", "source_basis_sha256",
    "source_input", "source_register_sha256", "source_contributions_sha256", "contribution_record_numbers",
    "selected_entities", "evidence_dependency_entities", "external_subject_references", "whole_files",
    "omitted_counts", "counts", "correction_witnesses", "correction_qualification", "qualification",
    "whole_file_permission_sha256", "permission_root_source_receipt_sha256"}


def exact(value, keys, message):
    cb.require(type(value) is dict and set(value) == set(keys), message)


def method_pins():
    import context_packet as cp
    return {**cp.pins(), "context_scope.py": cb.raw_sha(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))}


def request_for(opened, scope, item):
    cb.require((scope is None) != (item is None), "choose exactly one packet scope or item")
    chosen = cc.selected(cb.View(opened["basis"]), scope, item)
    external = set(opened.get("scope", {}).get("external_subject_references", []))
    cb.require(not external.intersection(chosen), "external_subject_reference is unexpanded; missing context must be supplied")
    return {"scope": scope, "item": chosen[0] if item is not None else None}


def selected_ids(basis, request):
    if request["item"] is not None:
        return [request["item"]] if any(e["id"] == request["item"] for e in basis["entities"]) else []
    return sorted(e["id"] for e in basis["entities"] if e["scope"] == request["scope"]
                  or e["scope"].startswith(request["scope"] + "/"))


def project(basis, request, identity_origins=()):
    """Copy occurrences unchanged; incoming external subjects retain identity only."""
    selected = set(selected_ids(basis, request))
    entities = cb.index(basis["entities"], "entity")
    dependencies = {r["subject"] for r in basis["relationships"]
        if r["object"] in selected and r["subject"] in entities
        and ((r["predicate"] == "associated_with" and entities[r["subject"]]["identity_role"] == "maintenance_record")
             or (r["predicate"] == "reported_installation_at" and entities[r["subject"]]["identity_role"] == "physical_item"))} - selected
    content = selected | dependencies
    edges = [copy.deepcopy(r) for r in basis["relationships"] if r["subject"] in content or r["object"] in content]
    external = {r["subject"] for r in edges} - content
    subjects = content | external
    targets = {r["object"] for r in edges} - subjects
    result = cb.empty(basis["namespace"])
    for e in basis["entities"]:
        if e["id"] in content:
            result["entities"].append(copy.deepcopy(e))
        elif e["id"] in external:
            result["entities"].append({k: copy.deepcopy(e[k]) for k in ("id", "tag", "scope", "identity_role")}
                                      | {"aliases": [], "projection_coverage": "external_subject_reference"})
    result["boundaries"] = [{"id": identifier, "coverage": "unexpanded_external_object_reference"}
                            for identifier in sorted(targets)]
    result["claims"] = [copy.deepcopy(r) for r in basis["claims"] if r["subject"] in content]
    result["relationships"] = edges
    result["corrections"] = [copy.deepcopy(r) for r in basis["corrections"] if r["subject"] in content]
    sources = cb.index(basis["sources"], "source")
    needed = {r["source"] for r in [*result["claims"], *edges]}
    needed.update(root for a in result["corrections"] for root in a["roots"] if root in sources)
    fact_sources = set(needed)
    prerequisites = []
    for subject in sorted(content):
        candidates = [r for r in identity_origins if r["subject"] == subject
                      and r["identity_role"] == entities[subject]["identity_role"] and r["source"] in sources]
        supplied_constructor = entities[subject]["identity_role"] == "functional_position" and any(
            r["subject"] == subject and r["role"] == "supplied_interpretation" for r in [*result["claims"], *edges])
        if candidates and not supplied_constructor and not any(r["source"] in fact_sources for r in candidates):
            origin = min(candidates, key=lambda r: (r["source"], r["locator"]))
            needed.add(origin["source"])
            prerequisites.append({"kind": "scoped_identity_origin", **copy.deepcopy(origin),
                "qualification": "Source-declared identity constructor row only; not an engineering fact, independent alias support, authenticated origin or verified current installation."})
    for identifier in list(needed):
        needed.update(r["id"] for r in cb.lineage_records(sources, identifier))
    result["sources"] = [copy.deepcopy(r) for r in basis["sources"] if r["id"] in needed]
    for collection in ("preparation", "omissions"):
        result[collection] = [copy.deepcopy(r) for r in basis[collection]
            if r.get("kind") != "scoped_identity_origin" and (r.get("source") in needed or (collection == "preparation" and r.get("kind") == "source_bound_contributions"))
            and (r.get("subject") is None or r["subject"] in content)]
    result["preparation"].extend(prerequisites)
    cb.validate(result)
    return result, sorted(selected), sorted(dependencies), sorted(external)


def csv_bytes(fields, rows):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return text.getvalue().encode("utf-8")


def input_parts(opened, basis):
    """Retain declaration extracts, not an absent original source-register file."""
    import context_packet as cp
    originals = cp.source_bytes(opened["root"]) if (opened["root"] / "originals").is_dir() else {}
    source_ids = {r["id"] for r in basis["sources"]}
    if opened.get("scope"):
        prior = opened["scope"]
        source_input = copy.deepcopy(prior["source_input"])
        source_input["declarations"] = [r for r in source_input["declarations"] if r["DocumentID"] in source_ids]
        register_sha = prior["source_register_sha256"]
    else:
        register = originals.get("source-register.csv")
        if register is not None:
            fields, records, _ = ci.csv_rows(register, opened["config"]["encoding"])
            declarations = [row for row, *_ in records if row["DocumentID"] in source_ids]
        else:
            fields = ["File", "DocumentID", "Revision", "Status", "Owner", "Applicability"]
            declarations = [{"File": r["path"], "DocumentID": r["id"], "Revision": r["revision"],
                "Status": r["status"], "Owner": r["owner"], "Applicability": r["applicability"]} for r in basis["sources"]]
        source_input = {k: opened["config"][k] for k in ("site", "plant", "encoding", "date_format")}
        source_input.update(declaration_fields=fields, declarations=declarations)
        register_sha = cb.raw_sha(register) if register is not None else None
    files = {r["path"]: originals[r["path"]] for r in basis["sources"] if r["sha256"] is not None}
    contribution = opened["root"] / "contributions.csv"
    raw = contribution.read_bytes() if contribution.exists() else None
    numbers, retained = [], []
    if raw is not None:
        fields, records, _ = ci.csv_rows(raw)
        original_numbers = opened.get("scope", {}).get("contribution_record_numbers")
        wanted = {(r["subject"], r["predicate"], r["source"], r["locator"], r.get("object", ""))
                  for r in [*basis["claims"], *basis["relationships"]] if r["role"] == "supplied_interpretation"}
        for index, (row, number, *_rest) in enumerate(records):
            subject = row["Subject"] or basis["namespace"] + "/documents/" + ci.quote(row["Source"], safe="-._~")
            if (subject, row["Predicate"], row["Source"], row["Locator"], row.get("Target", "")) in wanted:
                retained.append(row); numbers.append(original_numbers[index] if original_numbers is not None else number)
        raw = csv_bytes(fields, retained) if retained else None
    contribution_sha = (opened.get("scope", {}).get("source_contributions_sha256") if opened.get("scope") else
                        cb.raw_sha(contribution.read_bytes()) if contribution.exists() else None)
    mappings = cb.read_json(opened["root"] / "mappings.json")
    mappings = {k: v for k, v in mappings.items() if k in source_ids}
    path = opened["config"].get("identity_crosswalk")
    if path is not None and any(r["path"] == path and mappings.get(r["id"], {}).get("mode") == "source_bound_identity_crosswalk"
                                for r in basis["sources"]):
        source_input["identity_crosswalk"] = path
    else:
        source_input.pop("identity_crosswalk", None)
    return source_input, register_sha, files, raw, numbers, contribution_sha, mappings


def retained_subjects(basis):
    return sorted(r["id"] for r in basis["entities"] if r.get("projection_coverage") != "external_subject_reference")


def validate_identity_input(source_input, basis, originals, mappings):
    """Bind the optional scoped crosswalk mode; never infer it from a CSV name."""
    import context_packet as cp
    mapped = {key for key, value in mappings.items() if type(value) is dict and value.get("mode") == "source_bound_identity_crosswalk"}
    if "identity_crosswalk" not in source_input:
        cb.require(not mapped, "scoped identity crosswalk opt-in path missing")
        return
    path = source_input["identity_crosswalk"]
    cb.require(type(path) is str and path and Path(path).suffix.lower() == ".csv", "scoped identity crosswalk needs an exact relative CSV path")
    try:
        cp.safe_name(path)
    except (cb.ContextError, ValueError) as error:
        raise cb.ContextError("scoped identity crosswalk path is unsafe") from error
    declarations = [r for r in basis["sources"] if r["path"] == path]
    cb.require(len(declarations) == 1 and declarations[0]["id"] in mapped and len(mapped) == 1 and path in originals,
               "scoped identity crosswalk path/mode/source binding differs")


def replay(source_input, originals, mappings, contribution, numbers, retained_subjects=None, identity_origins=None):
    with tempfile.TemporaryDirectory(prefix="context-scope-replay-") as folder:
        root = Path(folder)
        for name, raw in originals.items():
            target = ci.local(root, name); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        if not source_input["declarations"]:
            cb.require(not originals and contribution is None, "empty scoped replay has unexpected source content")
            return cb.empty(ci.quote(source_input["site"], safe="-._~") + "/" + ci.quote(source_input["plant"], safe="-._~")), {}
        cb.require("source-register.csv" not in originals, "source register cannot also be an engineering original in scoped replay")
        (root / "source-register.csv").write_bytes(csv_bytes(source_input["declaration_fields"], source_input["declarations"]).decode("utf-8").encode(source_input["encoding"]))
        basis, _, actual = ci.prepare(root, source_input["site"], source_input["plant"], previous_mapping=mappings,
                                     encoding=source_input["encoding"], date_format=source_input["date_format"],
                                     identity_crosswalk=source_input.get("identity_crosswalk"),
                                     identity_crosswalk_subjects=retained_subjects if "identity_crosswalk" in source_input else None,
                                     identity_origins=identity_origins)
        if contribution is not None:
            basis = ci.add_contributions(basis, originals, contribution, record_numbers=numbers)
        else:
            cb.require(numbers == [], "scoped contribution record numbers have no retained rows")
        return basis, actual


def counts(basis, selected, dependencies, external):
    return {"selected_entities": len(selected), "evidence_dependency_entities": len(dependencies),
            "external_subject_reference_count": len(external), "external_object_reference_count": len(basis["boundaries"]),
            **{key: len(basis[key]) for key in ("claims", "relationships", "sources", "corrections")}}


def all_opened(opened):
    import context_packet as cp
    result = [opened]
    while result[-1]["receipt"]["history_depth"]:
        result.append(cp.open_packet(result[-1]["root"] / "previous", result[-1]["receipt"]["previous_receipt_sha256"]))
    return result


def build_plans(opened, request):
    import context_packet as cp
    versions = all_opened(opened)
    references = {}
    for index, version in enumerate(versions):
        basis = version["basis"]
        for length in range(len(basis["corrections"]) + 1):
            references.setdefault(cb.digest({**basis, "corrections": basis["corrections"][:length]}), []).append(index)
        for witness in version.get("scope", {}).get("correction_witnesses", []):
            references.setdefault(witness["original_basis_sha256"], []).append(index + witness["revision"])
    plans = []
    for index, version in enumerate(versions):
        all_input, _, all_originals, all_raw, all_numbers, _, all_mappings = input_parts(version, version["basis"])
        origins = []
        replay(all_input, all_originals, all_mappings, all_raw, all_numbers, retained_subjects(version["basis"]), identity_origins=origins)
        desired, selected, dependencies, external = project(version["basis"], request, origins)
        source_input, register_sha, originals, raw, numbers, contribution_sha, mappings = input_parts(version, desired)
        retained_origins = []
        rebuilt, actual_mapping = replay(source_input, originals, mappings, raw, numbers, retained_subjects(desired), identity_origins=retained_origins)
        rebuilt["corrections"] = copy.deepcopy(desired["corrections"])
        expected, s, d, e = project(rebuilt, request, retained_origins)
        for key in ("entities", "sources", "claims", "relationships", "corrections", "boundaries"):
            cb.require(cb.canonical(expected[key]) == cb.canonical(desired[key]), "selected source replay changed " + key)
        cb.require(cb.canonical(actual_mapping) == cb.canonical(mappings), "scoped mappings do not reproduce")
        witnesses = []
        for annotation in expected["corrections"]:
            revision = next((n for n in sorted(set(references.get(annotation["basis_sha256"], []))) if n >= index), None)
            cb.require(revision is not None, "selected correction historical field basis unavailable")
            witnesses.append({"annotation_id": annotation["id"], "original_basis_sha256": annotation["basis_sha256"], "revision": revision - index})
        whole = [{"path": name, "sha256": cb.raw_sha(value), "bytes": len(value),
                  "contains_unfiltered_whole_file_content": True} for name, value in sorted(originals.items())]
        manifest = {"schema": SCHEMA, "request": copy.deepcopy(request),
            "source_packet_receipt_sha256": version["receipt_sha256"], "source_basis_sha256": cb.digest(version["basis"]),
            "source_input": source_input, "source_register_sha256": register_sha,
            "source_contributions_sha256": contribution_sha, "contribution_record_numbers": numbers,
            "selected_entities": s, "evidence_dependency_entities": d, "external_subject_references": e,
            "whole_files": whole, "omitted_counts": {k: len(version["basis"][k]) - len(expected[k])
                for k in ("entities", "claims", "relationships", "sources", "corrections")},
            "counts": counts(expected, s, d, e), "correction_witnesses": witnesses,
            "correction_qualification": CORRECTION_QUALIFICATION, "qualification": QUALIFICATION,
            "whole_file_permission_sha256": None, "permission_root_source_receipt_sha256": opened["receipt_sha256"]}
        plans.append({"basis": expected, "scope": manifest, "originals": originals, "contribution": raw, "mappings": mappings})
    return plans


def history_binding(scoped_receipt, original_receipt):
    return {"schema": INCREMENTAL_SCHEMA, "previous_scoped_receipt_sha256": scoped_receipt,
            "previous_original_receipt_sha256": original_receipt}


def validate_history_binding(value):
    exact(value, INCREMENTAL_KEYS, "unsupported incremental history binding")
    cb.require(value["schema"] == INCREMENTAL_SCHEMA
               and all(type(value[k]) is str and HASH.fullmatch(value[k])
                       for k in INCREMENTAL_KEYS - {"schema"}), "invalid incremental history commitment")


def plans_with_previous(opened, request, previous_scoped):
    """Verify the actual original ancestor, not only a self-consistent prior hash."""
    import context_packet as cp
    plans = build_plans(opened, request)
    if previous_scoped is None:
        return plans, None
    prior = cp.open_packet(previous_scoped)
    cb.require(prior.get("scope") is not None, "previous-scoped needs a scoped packet")
    cb.require(prior["basis"]["namespace"] == opened["basis"]["namespace"]
               and prior["scope"]["request"] == request, "previous scoped namespace or selection policy differs")
    ancestors = [i for i, plan in enumerate(plans) if i > 0
                 and plan["scope"]["source_packet_receipt_sha256"] == prior["scope"]["source_packet_receipt_sha256"]]
    cb.require(len(ancestors) == 1, "previous scoped original ancestor is absent or ambiguous")
    boundary = ancestors[0]
    previous_frames = all_opened(prior)
    cb.require(len(previous_frames) == len(plans) - boundary, "prior scoped projection history differs from original ancestor")
    excluded = {"whole_file_permission_sha256", "permission_root_source_receipt_sha256", "incremental_history"}
    for old, expected in zip(previous_frames, plans[boundary:]):
        actual_manifest = {k: v for k, v in old["scope"].items() if k not in excluded}
        expected_manifest = {k: v for k, v in expected["scope"].items() if k not in excluded}
        originals = {name[len("originals/"):]: (old["root"] / name).read_bytes()
                     for name in cp.inventory(old["root"]) if name.startswith("originals/")}
        old_contribution = (old["root"] / "contributions.csv").read_bytes() if (old["root"] / "contributions.csv").is_file() else None
        cb.require(cb.canonical(actual_manifest) == cb.canonical(expected_manifest)
                   and cb.canonical(old["basis"]) == cb.canonical(expected["basis"])
                   and originals == expected["originals"] and old_contribution == expected["contribution"]
                   and cb.canonical(cb.read_json(old["root"] / "mappings.json")) == cb.canonical(expected["mappings"]),
                   "prior scoped projection differs from original ancestor semantics or source commitments")
    return plans[:boundary], prior


def preview_from_scopes(scopes, anchor=None):
    value = {"schema": "engineering-context-scope-preview-1", "source_receipt_sha256": scopes[0]["source_packet_receipt_sha256"],
             "request": scopes[0]["request"], "selected_entities": scopes[0]["selected_entities"], "counts": scopes[0]["counts"],
             "whole_files": [{**row, "packet_prefix": "previous/" * index}
                             for index, scope in enumerate(scopes) for row in scope["whole_files"]],
             "qualification": QUALIFICATION}
    if anchor is not None:
        validate_history_binding(anchor)
        value["previous_scoped_anchor"] = copy.deepcopy(anchor)
    return value


def incremental_anchor(chain):
    """Derive one preserved boundary from the actual nested receipt chain."""
    current = chain[0]["scope"]
    group = (current["whole_file_permission_sha256"], current["permission_root_source_receipt_sha256"])
    boundary = next((i for i, entry in enumerate(chain)
                     if (entry["scope"]["whole_file_permission_sha256"],
                         entry["scope"]["permission_root_source_receipt_sha256"]) != group), None)
    cb.require(boundary is not None and boundary > 0, "incremental preserved permission boundary missing")
    cb.require(all("incremental_history" in entry["scope"] for entry in chain[:boundary]),
               "incremental segment frame marker missing")
    cb.require(all((entry["scope"]["whole_file_permission_sha256"],
                    entry["scope"]["permission_root_source_receipt_sha256"]) != group for entry in chain[boundary:]),
               "incremental repeated or ambiguous permission boundary")
    old = chain[boundary]
    return history_binding(old["receipt_sha256"], old["scope"]["source_packet_receipt_sha256"])


def preview(packet, destination, *, scope=None, item=None, previous_scoped=None):
    import context_packet as cp
    opened = cp.open_packet(packet); request = request_for(opened, scope, item)
    plans, prior = plans_with_previous(opened, request, previous_scoped)
    scopes = [p["scope"] for p in plans] + ([p["scope"] for p in prior["scope_chain"]] if prior else [])
    anchor = history_binding(prior["receipt_sha256"], prior["scope"]["source_packet_receipt_sha256"]) if prior else None
    value = preview_from_scopes(scopes, anchor)
    raw = cp.encode(value)
    destination = Path(destination).absolute()
    cb.require(not destination.resolve().is_relative_to(opened["root"].resolve())
               and (prior is None or not destination.resolve().is_relative_to(prior["root"].resolve())),
               "scope preview must be outside the retained source packet")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        output.write(raw)
    return {"preview": str(Path(destination).absolute()), "preview_sha256": cb.raw_sha(raw), **value}


def scoped_draft(basis, config, manifest, chain):
    clean = {**basis, "corrections": []}
    draft = cc.generate(clean, scope=config["scope"], item=config["item"])
    draft["basis_sha256"] = cb.digest(basis)
    by_id = {a["id"]: a for a in basis["corrections"]}
    cb.require(len(manifest["correction_witnesses"]) == len(by_id), "selected correction field witnesses missing")
    seen = set()
    for witness in manifest["correction_witnesses"]:
        exact(witness, {"annotation_id", "original_basis_sha256", "revision"}, "unsupported scoped correction witness")
        cb.require(type(witness["revision"]) is int and 0 <= witness["revision"] < len(chain), "selected correction field witness history unavailable")
        annotation = by_id.get(witness["annotation_id"])
        cb.require(annotation is not None and annotation["id"] not in seen and annotation["basis_sha256"] == witness["original_basis_sha256"], "selected correction witness commitment differs")
        seen.add(annotation["id"])
        reference = chain[witness["revision"]]["basis"]
        cc.check_field_annotation(annotation, reference)
        if annotation["subject"] in draft["selection"]["entities"]:
            rendered = cc.render_annotation(annotation, cb.View(basis))
            rendered["verification"] = CORRECTION_QUALIFICATION
            draft["annotations"].append(rendered)
    draft["review"] += " Scoped corrections: " + CORRECTION_QUALIFICATION
    draft["scope_coverage"] = coverage(manifest, basis)
    return draft


def coverage(manifest, basis=None):
    result = {**manifest["counts"], "state": "selected_context_projection",
            "external_subject_references": manifest["external_subject_references"],
            "external_reference_expansion": "unexpanded_missing_context_not_empty_known_entity",
            "whole_files": manifest["whole_files"], "qualification": QUALIFICATION,
            "correction_verification": CORRECTION_QUALIFICATION,
            "parent_basis": "commitment_retained_not_reconstructed_or_authenticated",
            "managed_receiving": "records_scoped_v1_not_qualified_for_ChangePilot"}
    if "identity_crosswalk" in manifest["source_input"]:
        result["identity_lookup"] = "projection-local retained active source lineage only; not global or namespace uniqueness, entity merging or authenticated identity"
    if "incremental_history" in manifest:
        result["incremental_history"] = copy.deepcopy(manifest["incremental_history"])
        result["history_receiving"] = ("Exact adjacent scoped predecessor binding; local retained history does not prove managed admissions. "
                                       "Intervening revisions may require sequential receiving before the current packet.")
    if basis is not None:
        origins = [r for r in basis["preparation"] if r.get("kind") == "scoped_identity_origin"]
        if origins:
            result["identity_origins"] = copy.deepcopy(origins)
    return result


def guard_selection(opened, *, item=None, scope=None):
    if not opened.get("scope"):
        return
    chosen = cc.selected(cb.View(opened["basis"]), scope, item)
    allowed = set(opened["scope"]["selected_entities"]) | set(opened["scope"]["evidence_dependency_entities"])
    cb.require(set(chosen) <= allowed,
               "external_subject_reference is unexpanded as a draft target; missing context must be supplied")
    return chosen


def materialized_selection(opened, *, scope=None, item=None):
    """Explicit retained targets; a versioned envelope keeps nonasset evidence distinct."""
    chosen = guard_selection(opened, scope=scope, item=item)
    if scope == opened["config"]["scope"] and item == opened["config"]["item"]:
        return opened["draft"]
    config = {**opened["config"], "scope": scope, "item": item}
    draft = scoped_draft(opened["basis"], config, opened["scope"], opened["scope_chain"])
    dependencies = set(opened["scope"]["evidence_dependency_entities"])
    view = cb.View(opened["basis"])
    supporting = [view.inspect(identifier) for identifier in chosen if identifier in dependencies]
    if not supporting:
        return draft
    # Maintenance/document records remain their actual identity roles. They do
    # not become eligible assets because an engineer explicitly selects them.
    for component in draft["components"].values():
        if not component["items"] and not component["gaps"]:
            component["gaps"].append({"field": "eligible_asset_identity", "state": "unsupported_identity_role",
                "reason": "The retained selected supporting records have no eligible asset identity for this component."})
    qualification = ("Retained supporting source context, not engineering acceptance. "
                     "Selected field witnesses verify retained field/source replay, not the omitted whole parent basis "
                     "or authentic origin. New scoped edits remain unsupported.")
    return {"schema": MATERIALIZATION_SCHEMA, "basis_sha256": draft["basis_sha256"], "namespace": draft["namespace"],
            "selection": copy.deepcopy(draft["selection"]), "component_draft": draft,
            "supporting_context": supporting,
            "readable_supporting_context": "Retained supporting context: " + qualification + "\n" +
                json.dumps(supporting, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
            "qualification": qualification}


def guard_traversal(opened, result, depth):
    """Do not treat an identity-only subject reached mid-path as expandable context."""
    if not opened.get("scope"):
        return
    external = set(opened["scope"]["external_subject_references"])
    edges = {}
    for row in result["edges"]:
        edges.setdefault(row["subject"], []).append(row["object"])
    included = set(result["nodes"])
    frontier, seen = {result["start"]}, set()
    for _ in range(depth):
        cb.require(not frontier.intersection(external),
                   "external_subject_reference is unexpanded; missing context must be supplied before further traversal")
        seen.update(frontier)
        frontier = {target for subject in frontier for target in edges.get(subject, [])
                    if target in included and target not in seen}


def package(packet, out, *, scope=None, item=None, permission=None, previous_scoped=None):
    import context_packet as cp
    out = Path(out).absolute()
    cb.require(not out.exists() and not out.is_symlink(), "output exists; retain it and choose a new directory")
    opened = cp.open_packet(packet); request = request_for(opened, scope, item)
    cb.require(not out.resolve().is_relative_to(opened["root"].resolve()), "scoped output must be outside the retained source packet")
    plans, prior = plans_with_previous(opened, request, previous_scoped)
    cb.require(prior is None or not out.resolve().is_relative_to(prior["root"].resolve()),
               "scoped output must be outside the retained prior scoped packet")
    scopes = [p["scope"] for p in plans] + ([p["scope"] for p in prior["scope_chain"]] if prior else [])
    anchor = history_binding(prior["receipt_sha256"], prior["scope"]["source_packet_receipt_sha256"]) if prior else None
    preview_raw = cp.encode(preview_from_scopes(scopes, anchor))
    cb.require(type(permission) is str and HASH.fullmatch(permission) and cb.raw_sha(preview_raw) == permission,
               "explicit exact whole-file preview permission required; included files may contain unrelated content")
    generated = None
    if prior is not None:
        generated = {"files": {name: (prior["root"] / name).read_bytes() for name in cp.inventory(prior["root"])},
                     "draft": prior["draft"], "depth": prior["receipt"]["history_depth"], "scope": prior["scope"]}
    for index in range(len(plans) - 1, -1, -1):
        plan = plans[index]; manifest = plan["scope"]; manifest["whole_file_permission_sha256"] = permission
        config = {"route": ROUTE, **{k: manifest["source_input"][k] for k in ("site", "plant", "encoding", "date_format")},
                  "scope": request["scope"] if manifest["selected_entities"] else None,
                  "item": request["item"] if manifest["selected_entities"] else None}
        if "identity_crosswalk" in manifest["source_input"]:
            config["identity_crosswalk"] = manifest["source_input"]["identity_crosswalk"]
        if prior is not None:
            manifest["incremental_history"] = history_binding(cb.raw_sha(generated["files"]["RECEIPT.json"]),
                                                              generated["scope"]["source_packet_receipt_sha256"])
        chain = plans[index:] + (prior["scope_chain"] if prior else [])
        draft = scoped_draft(plan["basis"], config, manifest, chain)
        files = {"basis.json": cp.encode(plan["basis"]), "scope.json": cp.encode(manifest),
                 "drafts.json": cp.encode(cc.specification(draft, method_pins())),
                 "mappings.json": cp.encode(plan["mappings"]), "intake.json": cp.encode(config), "annotations.json": cp.encode([]),
                 **{name: text.encode("utf-8") for name, text in cc.render(draft).items()}}
        if plan["contribution"] is not None: files["contributions.csv"] = plan["contribution"]
        files.update({"originals/" + cp.safe_name(name): raw for name, raw in plan["originals"].items()})
        if generated is not None:
            files.update({"previous/" + name: raw for name, raw in generated["files"].items()})
            files["changes.json"] = cp.encode(cc.changes(generated["draft"], draft))
        receipt = {"schema": cp.SCHEMA, "basis_sha256": cb.digest(plan["basis"]), "method_sha256_lf": method_pins(),
                   "files": {name: cb.raw_sha(raw) for name, raw in files.items()}, "history_depth": generated["depth"] + 1 if generated else 0,
                   "previous_receipt_sha256": cb.raw_sha(generated["files"]["RECEIPT.json"]) if generated else None,
                   "source_authority": "Owner/review declarations; no authenticated engineering release",
                   "access": QUALIFICATION, "product_receiving": "records_scoped_v1_not_qualified_for_ChangePilot"}
        files["RECEIPT.json"] = cp.encode(receipt)
        cb.require(sum(map(len, files.values())) <= cp.MAX_PACKET_BYTES, "packet exceeds declared total byte limit")
        generated = {"files": files, "draft": draft, "depth": receipt["history_depth"], "scope": manifest}
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".context-scope-", dir=out.parent) as folder:
        stage = Path(folder) / "packet"; stage.mkdir()
        for name, raw in generated["files"].items():
            target = stage.joinpath(*cp.PurePosixPath(cp.safe_name(name)).parts)
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        cp.open_packet(stage)
        cb.require(not out.exists() and not out.is_symlink(), "output appeared; refusing replacement")
        stage.rename(out)
    return {"packet": str(out), "receipt_sha256": cb.raw_sha(generated["files"]["RECEIPT.json"]),
            "scope_coverage": coverage(plans[0]["scope"], plans[0]["basis"])}


def open_scoped(root, files, receipt, receipt_raw):
    import context_packet as cp
    exact(receipt, {"schema", "basis_sha256", "method_sha256_lf", "files", "history_depth",
                    "previous_receipt_sha256", "source_authority", "access", "product_receiving"},
          "unsupported scoped packet receipt")
    cb.require(receipt["source_authority"] == "Owner/review declarations; no authenticated engineering release"
               and receipt["access"] == QUALIFICATION
               and receipt["product_receiving"] == "records_scoped_v1_not_qualified_for_ChangePilot",
               "unsupported scoped receipt qualification")
    pins = receipt["method_sha256_lf"]
    cb.require(type(pins) is dict and 0 < len(pins) <= 32
               and all(type(k) is str and re.fullmatch(r"[A-Za-z0-9_-]+\.py", k)
                       and type(v) is str and HASH.fullmatch(v) for k, v in pins.items()),
               "invalid scoped declared method pins")
    manifest = cb.read_json(root / "scope.json")
    exact(manifest, MANIFEST_KEYS | ({"incremental_history"} if "incremental_history" in manifest else set()),
          "unsupported scoped projection manifest")
    if "incremental_history" in manifest:
        validate_history_binding(manifest["incremental_history"])
    cb.require(manifest["schema"] == SCHEMA and manifest["qualification"] == QUALIFICATION
               and manifest["correction_qualification"] == CORRECTION_QUALIFICATION, "unsupported scoped projection qualification")
    exact(manifest["request"], {"scope", "item"}, "unsupported scoped selection request")
    cb.require((manifest["request"]["scope"] is None) != (manifest["request"]["item"] is None), "scoped selection request must be exclusive")
    for value in manifest["request"].values():
        cb.require(value is None or type(value) is str and bool(value), "scoped selection request needs text")
    for key in ("source_packet_receipt_sha256", "source_basis_sha256", "whole_file_permission_sha256", "permission_root_source_receipt_sha256"):
        cb.require(type(manifest[key]) is str and HASH.fullmatch(manifest[key]), "scoped commitment needs SHA-256")
    for key in ("source_register_sha256", "source_contributions_sha256"):
        cb.require(manifest[key] is None or type(manifest[key]) is str and HASH.fullmatch(manifest[key]), "scoped source commitment needs SHA-256 or null")
    source_input = manifest["source_input"]
    source_keys = {"site", "plant", "encoding", "date_format", "declaration_fields", "declarations"}
    exact(source_input, source_keys | ({"identity_crosswalk"} if "identity_crosswalk" in source_input else set()), "unsupported scoped source input")
    cb.require(type(source_input["declaration_fields"]) is list and len(source_input["declaration_fields"]) <= 1000
               and all(type(f) is str and f for f in source_input["declaration_fields"])
               and len(set(source_input["declaration_fields"])) == len(source_input["declaration_fields"]), "invalid scoped source declaration fields")
    cb.require(type(source_input["declarations"]) is list and len(source_input["declarations"]) <= 20000
               and all(type(r) is dict and set(r) == set(source_input["declaration_fields"])
                       and all(type(v) is str for v in r.values()) for r in source_input["declarations"]), "invalid scoped source declarations")
    for key in ("site", "plant", "encoding", "date_format"): cb.text(source_input[key], "scoped intake " + key)
    basis = cb.read_json(root / "basis.json")
    try:
        cb.validate(basis)
    except cb.ContextError as error:
        raise cb.ContextError("scoped basis replay differs: " + str(error)) from error
    declarations = source_input["declarations"]
    cb.require("DocumentID" in source_input["declaration_fields"]
               and sorted(r["DocumentID"] for r in declarations) == sorted(r["id"] for r in basis["sources"]),
               "scoped declaration closure differs from retained sources")
    represented = {name for name in files if name != "RECEIPT.json"}
    managed = {"basis.json", "scope.json", "drafts.json", "mappings.json", "intake.json", "annotations.json", "equipment-instruments.csv", "datasheets.md", "control-outline.md", "contributions.csv", "changes.json"}
    cb.require(all(name in managed or name.startswith(("originals/", "previous/")) for name in represented), "unaccounted scoped packet artifact")
    cb.require(type(manifest["whole_files"]) is list and len(manifest["whole_files"]) <= 20000, "invalid scoped whole-file disclosure")
    originals = {}
    for row in manifest["whole_files"]:
        exact(row, {"path", "sha256", "bytes", "contains_unfiltered_whole_file_content"}, "invalid scoped whole-file disclosure")
        name = cp.safe_name(row["path"])
        cb.require(name not in originals and row["contains_unfiltered_whole_file_content"] is True
                   and type(row["bytes"]) is int and row["bytes"] >= 0, "invalid scoped whole-file permission declaration")
        target = root / "originals" / name
        cb.require(target.is_file(), "source raw-byte binding mismatch: required scoped original missing")
        raw = target.read_bytes()
        cb.require(cb.raw_sha(raw) == row["sha256"] and len(raw) == row["bytes"], "source raw-byte binding mismatch: scoped original changed")
        originals[name] = raw
    cb.require({"originals/" + name for name in originals} == {n for n in represented if n.startswith("originals/")}, "undeclared scoped whole original")
    cb.require(set(originals) == {r["path"] for r in basis["sources"] if r["sha256"] is not None},
               "scoped original closure differs from retained sources")
    cb.require(type(manifest["contribution_record_numbers"]) is list and len(manifest["contribution_record_numbers"]) <= 100000,
               "invalid scoped contribution record numbers")
    raw = (root / "contributions.csv").read_bytes() if "contributions.csv" in files else None
    mappings = cb.read_json(root / "mappings.json")
    validate_identity_input(source_input, basis, originals, mappings)
    origins = []
    rebuilt, actual_mapping = replay(source_input, originals, mappings, raw, manifest["contribution_record_numbers"], retained_subjects(basis), identity_origins=origins)
    if raw is not None:
        _, retained, _ = ci.csv_rows(raw)
        retained_numbers = manifest["contribution_record_numbers"]
        included_numbers = {r["contribution_record"] for r in [*basis["claims"], *basis["relationships"]]
                            if r["role"] == "supplied_interpretation"}
        cb.require(set(retained_numbers) == included_numbers and len(retained) == len(included_numbers),
                   "scoped contribution closure differs from retained occurrences")
    rebuilt["corrections"] = copy.deepcopy(basis.get("corrections"))
    expected, selected, dependencies, external = project(rebuilt, manifest["request"], origins)
    cb.require(cb.canonical(expected) == cb.canonical(basis), "scoped basis replay differs from retained selected originals")
    cb.require(cb.digest(basis) == receipt.get("basis_sha256"), "scoped basis identity differs")
    cp.check_source_bindings(basis, originals)
    cb.require(cb.canonical(actual_mapping) == cb.canonical(mappings), "scoped mappings do not reproduce")
    cb.require((manifest["selected_entities"], manifest["evidence_dependency_entities"], manifest["external_subject_references"])
               == (selected, dependencies, external) and cb.canonical(manifest["counts"]) == cb.canonical(counts(basis, selected, dependencies, external)), "scoped coverage differs")
    exact(manifest["omitted_counts"], {"entities", "claims", "relationships", "sources", "corrections"}, "invalid scoped omission counts")
    cb.require(all(type(v) is int and v >= 0 for v in manifest["omitted_counts"].values()), "invalid scoped omission counts")
    config = cb.read_json(root / "intake.json")
    config_keys = {"route", "site", "plant", "encoding", "date_format", "scope", "item"}
    exact(config, config_keys | ({"identity_crosswalk"} if "identity_crosswalk" in config else set()), "unsupported scoped intake")
    expected_config = {"route": ROUTE, **{k: source_input[k] for k in ("site", "plant", "encoding", "date_format")},
                       "scope": manifest["request"]["scope"] if selected else None, "item": manifest["request"]["item"] if selected else None}
    if "identity_crosswalk" in source_input:
        expected_config["identity_crosswalk"] = source_input["identity_crosswalk"]
    cb.require(cb.canonical(config) == cb.canonical(expected_config), "scoped intake selection differs")
    cb.require(cb.read_json(root / "annotations.json") == [], "scoped annotations must use exact original correction witnesses")
    depth = receipt.get("history_depth")
    cb.require(type(depth) is int and 0 <= depth <= 8, "unsupported scoped history depth")
    prior = None
    if depth:
        prior = cp.open_packet(root / "previous", receipt.get("previous_receipt_sha256"))
        cb.require(prior.get("scope") is not None and prior["receipt"]["history_depth"] == depth - 1
                   and prior["scope"]["request"] == manifest["request"]
                   and prior["basis"]["namespace"] == basis["namespace"], "scoped history declaration differs")
        if "incremental_history" in manifest:
            cb.require(manifest["incremental_history"] == history_binding(prior["receipt_sha256"], prior["scope"]["source_packet_receipt_sha256"]),
                       "incremental adjacent predecessor binding differs")
        else:
            cb.require("incremental_history" not in prior["scope"], "incremental segment frame marker missing")
            cb.require(prior["scope"]["whole_file_permission_sha256"] == manifest["whole_file_permission_sha256"]
                       and prior["scope"]["permission_root_source_receipt_sha256"] == manifest["permission_root_source_receipt_sha256"],
                       "scoped whole-file permission history differs")
    else:
        cb.require("incremental_history" not in manifest, "incremental history needs a predecessor")
        cb.require(receipt.get("previous_receipt_sha256") is None and "changes.json" not in files
                   and not any(n.startswith("previous/") for n in files), "undeclared scoped history")
    chain = [{"basis": basis, "scope": manifest, "receipt_sha256": cb.raw_sha(receipt_raw)}] + (prior["scope_chain"] if prior else [])
    originals = [entry["scope"]["source_packet_receipt_sha256"] for entry in chain]
    cb.require(len(set(originals)) == len(originals), "scoped original history repeats or cycles")
    if "incremental_history" in manifest:
        anchor = incremental_anchor(chain)
    else:
        anchor = None
    draft = scoped_draft(basis, config, manifest, chain)
    stored = cb.read_json(root / "drafts.json")
    expected_draft = cc.specification(draft, receipt.get("method_sha256_lf")) if stored.get("schema") == cc.SPEC_SCHEMA else draft
    cb.require(cb.canonical(stored) == cb.canonical(expected_draft), "scoped component views differ")
    for name, text in cc.render(draft).items():
        cb.require((root / name).read_bytes() == text.encode("utf-8"), "scoped readable component differs: " + name)
    if prior:
        cb.require(cb.canonical(cb.read_json(root / "changes.json")) == cb.canonical(cc.changes(prior["draft"], draft)), "scoped revision impact differs")
    if manifest["permission_root_source_receipt_sha256"] == manifest["source_packet_receipt_sha256"]:
        cb.require(cb.raw_sha(cp.encode(preview_from_scopes([v["scope"] for v in chain], anchor))) == manifest["whole_file_permission_sha256"], "scoped whole-file preview permission differs")
    return {"root": root, "receipt": receipt, "receipt_sha256": cb.raw_sha(receipt_raw), "basis": basis,
            "draft": draft, "config": config, "history_bases": {}, "scope": manifest, "scope_chain": chain,
            "method_changed": receipt.get("method_sha256_lf") != method_pins()}
