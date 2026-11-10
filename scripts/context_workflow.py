"""Prepare, query, draft, revise and reopen sourced engineering context from local records.

No account or network is required. Interpretation is supplied work; the result is
a draft basis and portable packet, not an authenticated release or product import.
"""
import argparse
import json
import sys

import context_basis as cb
import context_basis_compare as cbc
import context_components as cc
import context_packet as cp
import context_review as cr
import context_scope as cs


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities", help="Show supported inputs, queries, draft targets and limits")
    prepare = sub.add_parser("prepare", help="Retain permitted originals and prepare all three component drafts")
    prepare.add_argument("--records", required=True)
    prepare.add_argument("--site", required=True)
    prepare.add_argument("--plant", required=True)
    prepare.add_argument("--out", required=True)
    prepare.add_argument("--previous", help="Previous complete packet: retain mappings, edits and history")
    prepare.add_argument("--mapping", help="Reviewed column mappings, ordinarily reused from --previous")
    prepare.add_argument("--contributions", help="Supplied source-bound interpretation CSV")
    prepare.add_argument("--identity-crosswalk", help="Relative source CSV Position,Area,Alias for existing stable functional positions")
    prepare.add_argument("--encoding", default="utf-8-sig")
    prepare.add_argument("--date-format", choices=("ISO", "MDY", "DMY"), default="ISO")
    select = prepare.add_mutually_exclusive_group()
    select.add_argument("--scope")
    select.add_argument("--item")
    for name, help_text in (("scope-preview", "Preview the exact whole files needed for an explicit scoped packet"),
                            ("package-scope", "Project a selected packet after exact whole-file preview permission")):
        scoped = sub.add_parser(name, help=help_text)
        scoped.add_argument("packet")
        scoped.add_argument("--out", required=True)
        scoped.add_argument("--previous-scoped", help="Previously delivered scoped packet: retain its exact bytes and predecessor")
        selection = scoped.add_mutually_exclusive_group(required=True)
        selection.add_argument("--scope")
        selection.add_argument("--item")
        if name == "package-scope":
            scoped.add_argument("--permit-whole-files-preview", required=True)
    verify = sub.add_parser("verify", help="Replay originals, drafts, history and exact byte bindings")
    verify.add_argument("packet")
    verify.add_argument("--expected-receipt", help="Optional independently retained receipt SHA-256")
    query = sub.add_parser("query", help="Inspect selected facts, gaps and declared relations")
    query.add_argument("packet")
    query.add_argument("--item", required=True)
    mode = query.add_mutually_exclusive_group()
    mode.add_argument("--field")
    mode.add_argument("--relation", choices=sorted(cb.RELATIONS))
    query.add_argument("--depth", type=int, default=1)
    query.add_argument("--limit", type=int, default=100)
    compare = sub.add_parser("compare", help="Whole-basis differences plus generated-component impact between retained packets")
    compare.add_argument("before")
    compare.add_argument("after")
    edit = sub.add_parser("edit", help="Retain a proposed editorial correction without replacing source facts")
    edit.add_argument("packet")
    edit.add_argument("--item", required=True)
    edit.add_argument("--field", required=True)
    edit.add_argument("--value", required=True)
    edit.add_argument("--type", choices=("text", "boolean", "integer", "number", "null"), default="text")
    edit.add_argument("--rationale", required=True)
    edit.add_argument("--out", required=True)
    materialize = sub.add_parser("materialize", help="Export a full typed component draft for inspection, explicit edits and reimport")
    materialize.add_argument("packet")
    materialize.add_argument("--out", required=True)
    materialize_select = materialize.add_mutually_exclusive_group()
    materialize_select.add_argument("--scope")
    materialize_select.add_argument("--item")
    reimport = sub.add_parser("reimport", help="Read back own-format drafts with explicit editorial proposals")
    reimport.add_argument("packet")
    reimport.add_argument("--draft", required=True)
    reimport.add_argument("--out", required=True)
    bundle = sub.add_parser("bundle", help="Create a private full-source portable payload; not a product acceptance")
    bundle.add_argument("packet")
    bundle.add_argument("--out", required=True)
    bundle.add_argument("--max-bytes", type=int, default=25 * 1024 * 1024)
    unbundle = sub.add_parser("unbundle", help="Verify and reopen a private portable payload in a new directory")
    unbundle.add_argument("delivery")
    unbundle.add_argument("--out", required=True)
    unbundle.add_argument("--expected-sha256")
    review = sub.add_parser("review", help="Create an offline component review with downloadable text proposals")
    review.add_argument("packet")
    review.add_argument("--out", required=True)
    verify_review = sub.add_parser("verify-review", help="Check exact delivered HTML against its retained packet")
    verify_review.add_argument("packet")
    verify_review.add_argument("html")
    apply_review = sub.add_parser("apply-review", help="Retain a downloaded text proposal on its exact source basis")
    apply_review.add_argument("packet")
    apply_review.add_argument("--edit", required=True)
    apply_review.add_argument("--out", required=True)
    generate = sub.add_parser("generate", help="Project selected sourced equipment and run the existing generator; no inferred topology/signals")
    generate.add_argument("packet")
    generate.add_argument("--out", required=True)
    verify_generated = sub.add_parser("verify-generated", help="Reproject source and replay actual generator output bytes")
    verify_generated.add_argument("packet")
    verify_generated.add_argument("output")
    return p


def typed(value, kind):
    if kind == "text":
        return value
    if kind == "boolean":
        cb.require(value in ("true", "false"), "boolean edit needs true/false")
        return value == "true"
    if kind == "integer":
        import re
        cb.require(re.fullmatch(r"-?[0-9]{1,128}", value), "integer edit needs explicit bounded integer")
        return int(value)
    if kind == "number":
        return cb.lossless_float(value)
    cb.require(kind == "null" and value == "null", "null edit requires literal null")
    return None


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "capabilities":
            result = {**cb.capabilities(), "input_route": "ordinary CSV exports plus retained originals",
                      "preparation": "Document/graph interpretation needs source-bound contributions or qualified adapters",
                      "packet_history_revisions_max": 9, "packet_bytes_max": cp.MAX_PACKET_BYTES,
                      "offline_review": "review / apply-review: bounded text proposals; no authenticated approval",
                      "typed_draft_export": "materialize: full typed own-format draft; compact stored view specifications are not editable drafts",
                      "existing_generator_bridge": "generate / verify-generated: partial sourced equipment to existing process-model consumer; no inferred topology/signals",

                      "identity_crosswalk": "prepare --identity-crosswalk: source CSV Position,Area,Alias for existing stable functional positions; scoped source-evidenced lookup, no rekey/merge",
                      "product_receiving": "Not established by local packet verification"}
        elif args.command == "prepare":
            out = cp.prepare(args.records, args.out, args.site, args.plant, previous=args.previous,
                             mapping=args.mapping, contribution=args.contributions, scope=args.scope,
                             item=args.item, encoding=args.encoding, date_format=args.date_format,
                             identity_crosswalk=args.identity_crosswalk)
            opened = cp.open_packet(out)
            result = {"packet": str(out), "receipt_sha256": opened["receipt_sha256"],
                      "entities": len(opened["basis"]["entities"]), "omissions": opened["basis"]["omissions"],
                      "drafts": list(cc.TARGETS), "product_receiving": "not established"}
        elif args.command == "scope-preview":
            result = cs.preview(args.packet, args.out, scope=args.scope, item=args.item, previous_scoped=args.previous_scoped)
        elif args.command == "package-scope":
            result = cs.package(args.packet, args.out, scope=args.scope, item=args.item,
                                permission=args.permit_whole_files_preview, previous_scoped=args.previous_scoped)
        elif args.command == "verify":
            opened = cp.open_packet(args.packet, args.expected_receipt)
            result = {"verified": True, "receipt_sha256": opened["receipt_sha256"],
                      "basis_sha256": cb.digest(opened["basis"]), "method_changed": opened["method_changed"],
                      "history_depth": opened["receipt"]["history_depth"],
                      "qualification": "Source/draft replay and byte identity; not independent engineering truth or product acceptance"}
            if opened.get("scope"):
                result["scope_coverage"] = cs.coverage(opened["scope"], opened["basis"])
        elif args.command == "query":
            opened = cp.open_packet(args.packet)
            view = cb.View(opened["basis"])
            subject = view.resolve(args.item)
            cb.require(subject not in opened.get("scope", {}).get("external_subject_references", []),
                       "external_subject_reference is unexpanded; missing context must be supplied")
            result = (view.field(subject, args.field) if args.field else
                      view.traverse(subject, args.relation, depth=args.depth, limit=args.limit)
                      if args.relation else view.inspect(subject))
            resolution = view.alias_resolution(args.item)
            if resolution is not None:
                result["identity_resolution"] = resolution
            if opened.get("scope"):
                if args.relation:
                    cs.guard_traversal(opened, result, args.depth)
                result["scope_coverage"] = cs.coverage(opened["scope"], opened["basis"])
        elif args.command == "compare":
            before, after = cp.open_packet(args.before), cp.open_packet(args.after)
            result = cc.changes(before["draft"], after["draft"])
            result["basis_changes"] = cbc.changes(before["basis"], after["basis"])
        elif args.command in ("edit", "reimport"):
            annotation = (cc.new_annotation(cp.open_packet(args.packet)["basis"], args.item, args.field,
                                           typed(args.value, args.type), args.rationale)
                          if args.command == "edit" else None)
            out = cp.write_edited(args.packet, args.out, annotation=annotation,
                                  draft=args.draft if args.command == "reimport" else None)
            result = {"packet": str(out), "receipt_sha256": cp.open_packet(out)["receipt_sha256"],
                      "qualification": "Retained editorial proposals; source facts unchanged"}
        elif args.command == "materialize":
            result = cp.materialize(args.packet, args.out, scope=args.scope, item=args.item)
        elif args.command in ("generate", "verify-generated"):
            import context_generator as cg
            result = cg.write(args.packet, args.out) if args.command == "generate" else cg.verify(args.packet, args.output)
        elif args.command == "bundle":
            result = cp.bundle(args.packet, args.out, args.max_bytes)
        elif args.command == "review":
            result = cr.write(args.packet, args.out)
        elif args.command == "verify-review":
            result = cr.verify(args.packet, args.html)
        elif args.command == "apply-review":
            result = cr.apply(args.packet, args.edit, args.out)
        else:
            result = cp.unbundle(args.delivery, args.out, expected_sha256=args.expected_sha256)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (cb.ContextError, OSError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({"error": str(error), "outcome": "refused; no acceptance claimed"},
                         ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
