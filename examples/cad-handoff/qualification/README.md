# Source-preserving CAD value edits: qualification in progress

The [frozen protocol](PROTOCOL.md) defines the full acceptance gates. This route proposes edits to existing,
profiled ASCII-DXF asset attributes; it does not import a noisy native return or qualify native full-file saves.
The original native-save failures, including all 335/344 strict differences, remain in the earlier evidence.

## Try a declared edit

```sh
python scripts/cad_value_patch.py examples/cad-handoff/source/valve.dxf examples/cad-handoff/source/edit-plan.json --out out/cad-preserving-proposal
```

Supply your own DXF and `cad-edit-plan-1` using the [handoff contract](../README.md). Only existing model-space
INSERTs with unique ICT_ID/TAG and an existing editable attribute are supported. The plan binds exact source
SHA256 and before values, desired values and review reasons. Outputs retain the exact source, candidate,
original/candidate snapshots, strict comparison, byte-edit spans and proposed context separately. Nothing is
marked as installed, accepted or automatically synchronized to a company system.

The patcher identifies one raw ATTRIB group-1 value per declared handle and replaces only that value's bytes.
It preserves all other bytes, line endings and ordering. A separate offset-free checker reconstructs expected
bytes directly from the source/plan without reading the patcher's receipt. Both use the existing source asset
profile and ezdxf encoding: this is a second same-author software check, not independent engineering review.
The unchanged strict comparator is an additional gate. Rejected inputs produce no validated packet.

Scope: ASCII DXF with ordinary single-line ATTRIB serialization, code-page encoding before R2007 and UTF8 from
R2007, encoded replacement length at most 250 bytes. Binary DXF, ambiguous/multiline target records, control
characters, paragraph escapes, unroundtrippable literal Unicode escapes and unsupported encodings refuse.
Unrelated attributes/XDATA/custom dictionaries/comments are retained as bytes, not interpreted or certified.
Native rendering, editability, UI save/close/reopen and actual returned-file preservation remain required gates.

## Cases and exposure

[The fixture manifest](fixtures/MANIFEST.json) was committed before method implementation: two authored
development cases and six reserved authored cases. The existing valve and unit-test drawing are development
inputs too. Reserved files must not be used for tuning; a failure used for a fix becomes development and needs
a replacement case for a new qualification claim. These are authored procedural controls, not six independent
plants or proof of model-training blindness. Public originals have a separate [manifest](public-sources/MANIFEST.json).

`run_cases.py` runs matched library-save and value-span routes. Library-save candidates are retained even when
the guarded product would refuse them. It keeps strict comparison and byte preservation separate: a library
save can pass the logical comparison while changing unrelated raw comments or save metadata.

```sh
python examples/cad-handoff/qualification/run_cases.py --split development --out data/external/cad-qualification/dev-replay
# Reserved runs require the method freeze receipt, created and committed before opening their results.
```

Development checks exercise exact LF/CRLF byte expectations, multi-value edits, stale source/before values,
identity and duplicate edit refusal, binary and duplicate raw value refusal, concurrent source changes,
output collisions, later revisions, planted geometry/layer/foreign-attribute/XDATA loss and an extra comment
change that the strict snapshot alone ignores. Those controls do not replace the reserved and native gates.
