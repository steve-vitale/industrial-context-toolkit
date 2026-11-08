# Multi-asset revision and loss rehearsal

2026-11-08. Exposed development only. This extends step 7 of [PLAN.md](PLAN.md)
on both already published sources in `DEVELOPMENT-INPUTS.json`. It does not
select reserved drawings, change a comparator, or fill the native manual-edit,
paper/layout, final-method or independent engineering-review gates.

Freeze this plan before implementing the runner; freeze the runner, source/plan
bindings and existing methods before execution. Retain failed runs unchanged.
Use a new output folder for every run. No CAD application or model is launched.

## Revision story and expected observations

1. Build the original two-MODEL proposal with the existing value patcher.
2. From the same original, author a simulated concurrent return: asset 1 MODEL
   is `OTHER-CHOICE`, asset 2 MODEL is the requested value, and asset 2 SERIAL is
   `FIELD-OBSERVED`. This is a declared fictional branch produced by software,
   not a real field observation, consultant return or native manual edit.
3. Applying the old proposal to that return must refuse both its stale source
   hash and, after changing only the hash, its stale before values. Neither
   refusal may publish a packet or alter existing files.
4. Review the concurrent return against the original requests. The asset-1
   MODEL disagreement and asset-2 unrequested SERIAL must remain explicit. The
   supported asset-2 MODEL must not hide either item.
5. Author a separately bound second plan, explicitly selecting the originally
   requested asset-1 MODEL while retaining the fictional concurrent SERIAL.
   The candidate must pass the unchanged strict and independent byte checks
   relative to the concurrent source. Against the original plan, the unrequested
   SERIAL must remain an unexpected difference. Selection is a teaching action,
   not company acceptance or an automatic merge.
6. Project original and selected packets using supplied exact identity mappings;
   build both draft maps and their change record through actual CLI calls.
   Both assets, every foreign/literal field and exact original/selected DXF
   bytes must remain. Map attributes stay `cad_` drawing references. No
   installed-equipment authority or inferred connectivity is introduced.

## Matched preservation controls

For each source, the unaltered first candidate is the positive baseline. Plant
one raw record change at a time in a copy of that candidate, without a library
save: model LINE geometry, model LINE layer, STYLE height, foreign attribute
text, foreign XDATA string and block-definition geometry. Identify each exact
record/group in the retained control receipt. Require both a nonzero unchanged
strict result and refusal by independent source-plus-plan byte reconstruction.
Do not change keys, masks, tolerances or baseline after results.

Also require proposal refusal for an identity edit, duplicate planned target,
newline value and output-folder collision, retaining the complete failed CLI
record and exact pre-existing output inventory. A malformed single-line target
is a separate authored source: insert an extra group-3 payload in its ATTRIB,
bind its own hash, and require refusal without output. If the declared generator
or expected failure is wrong, retain that attempt before a prospective correction.

## Reproduction and useful result

Retain full existing-tool packets, actual CLI command/exit/stdout/stderr, all
strict reports and byte refusals. Publish a short engineer/manager brief listing
the two distinct findings, explicit selection, retained SERIAL, unresolved
authority and remaining CAD gates. Re-running in a new folder must reproduce
the source hashes, strict counts, field outcomes and refusal categories. This
checks software behavior on exposed fictional cases; it establishes no timing,
site benefit, native human-edit behavior or CAD qualification.
