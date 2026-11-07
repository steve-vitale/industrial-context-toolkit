# A separate qualification: equipment-data exchange without a CAD resave

2026-11-07, before implementation/results. Steve challenged making a native UI session a prerequisite and
asked for new designs. The original protocol is retained: its native UI/visual/full-save gates remain unproved.
This new contract qualifies a different, useful operation, not a retroactive pass on that protocol.

## Designs considered

1. **Immutable DXF plus a source-bound equipment-data sidecar (selected).** Review/edit existing attributes in
   a local browser or with an agent; return structured proposals; reconstruct a draft DXF using the frozen
   value-span writer. No CAD resave occurs. Geometry/layout/unknown bytes cannot be changed by the sidecar.
2. **Native CAD return as proposals only (deferred).** Retain the complete native return and audit; extracting
   attributes would need a separate import contract that does not silently discard intentional geometry edits.
3. **Newly authored drawing from a neutral model (existing separate route).** Useful when no drawing exists,
   but a newly generated DXF is not preservation of an existing drawing or its proprietary project semantics.

## Acceptance defined before the new method

- `prepare` retains exact supplied DXF bytes, emits a complete source-derived attribute catalog and a standalone
  HTML form. Only present TAG/MANUFACTURER/MODEL/SERIAL/SIZE fields are editable. ICT_ID and foreign attributes
  stay visible/read-only. No geometry, identity creation, source interpretation or installed authority is inferred.
- The response binds the exact source SHA and canonical complete catalog SHA. Every changed value has its
  exact before value and nonempty supplied reason. The catalog is independently regenerated from the current
  source during apply; untrusted catalog/response modifications cannot widen the permitted fields.
- A returned JSON is a proposal, not approval. Refuse empty/no-op/duplicate/unknown/identity/foreign-field edits,
  malformed/extra fields, stale source/catalog, wrong before values, multiline/overlong values, duplicate IDs,
  existing destinations, and attempts to treat a full returned DXF as this response. No automatic rebase.
- Apply uses the unchanged frozen `cad_value_patch.py`, then a separate raw-line reconstruction and unchanged
  strict comparator. Only declared value bytes change; exact source, catalog, returned response, plan, draft
  candidate and sourced context are retained. No full native save is merged or reclassified as preserved.
- A second revision requires prepare again. Two competing sidecars bind their original version; replaying one
  on the other's candidate refuses before writes. A new explicit proposal may use the revised source.
- Actual browser exercise: open the generated form, edit a value/reason, download JSON, apply that exact download,
  close/reopen a freshly prepared form on the candidate and observe stored values. Exercise invalid/empty form,
  read-only identity/foreign fields, mobile width and hostile display strings. This proves this form's operation,
  not native CAD usability, layout rendering, engineering correctness or authenticated approval.
- Record six fresh authored cases, source/key hashes and generation recipe before implementation. Freeze the
  method before their complete run. Include R12/modern DXF, CRLF/LF, cp1251/UTF-8, transforms, multiple assets,
  paper layouts, retained XDATA/foreign payload and HTML-special text. These are same-author procedural software
  validation, not independent plants, blind model tests or a new public source family.
- Run the same cases through the existing library-save baseline and new exchange; retain all failures and
  raw/strict results separately. Planted geometry/layer/foreign/XDATA changes must fail the independent byte
  checker. Earlier 21/42 candidate/native results and frozen methods remain untouched.
- Offline CI checks the saved sample, controls, source/plan reconstruction and focused regressions without CAD,
  browser download, commercial trial or network. The recorded browser run is distinct from offline CI coverage.

## Claim boundary

If these gates pass, report **source-preserving equipment-data exchange on the declared DXF profile**. It is
useful for maintenance/engineering records and agent-driven preparation without a native CAD UI. Never shorten
that to general CAD qualification, native editor acceptance, visual equivalence, DWG/proprietary database
support or approved site synchronization. A receiving team's native visual/editability check remains necessary
when that is the promised deliverable; it is not required to test this narrower metadata operation.
