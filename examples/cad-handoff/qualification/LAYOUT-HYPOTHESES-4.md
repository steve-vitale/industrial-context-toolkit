# Exposed layout compatibility diagnosis — not qualification

Before creating/running working copies, declare all six variants on the exposed validation-cp1251 source:
exact original, ordinary library save, add main viewport with its current-handle change, add main viewport
but restore the original current handle, set current handle to the existing display viewport only, and activate
the existing layout only. No original/validation source is overwritten or replaced. Keep every variant/result.

The source's Qualification sheet has one display viewport and no main viewport. Native read-only import reports
an empty block. Retained default/R15 files contain a paper/main viewport with different dimensions and view
settings, rather than the original display viewport. That is an actual preservation failure, not just a PNG issue.

Primary ezdxf documentation is cautious and internally inconsistent: layout internals describe a main viewport
as required for a well-defined layout; the API says CAD applications do not require one and does not create it by
default. Do not infer that the source is universally invalid or that one diagnostic fix proves a general importer
bug. Matched working-copy controls isolate candidate explanations: library serialization, missing main viewport,
current viewport handle and active/inactive storage. All changes here are deliberate diagnostic source revisions,
not byte-preserving candidates or a silent preparation step offered to users.

Generate and hash all working copies/manifest before native import. Use the same frozen native read-only layout
probe on each. If a variant exposes the display viewport, render the original and all variants with the same
layout name/window/settings, retaining trial marks and input hashes. Report complete cohort outcomes, including
failure. No preservation-method, strict-comparison exclusion, original score, fresh validation or GUI acceptance
claim changes. A useful diagnosis must be carried into an explicitly scoped future method/fresh cohort before
qualification is claimed.

Sources: https://ezdxf.readthedocs.io/en/stable/dxfinternals/layout_management.html and
https://ezdxf.readthedocs.io/en/stable/layouts/layouts.html (`reset_main_viewport`, `add_new_main_viewport`).
