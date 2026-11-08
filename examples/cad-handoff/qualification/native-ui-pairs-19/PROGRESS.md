# Native UI procedure development — still running

2026-11-08. This is a provisional development checkpoint under [PLAN.md](PLAN.md), not a released evidence
packet, new validation result or qualification. The original protocol and strict comparator remain unchanged.
The six sources are exact exposed public adaptations from header16/layout17, with their earlier provenance
and exposure correction in [public-validation-11](../public-validation-11/README.md).

## Completed observations

- Startup-only preflight exited normally without opening/saving a drawing. Both native file dialogs and
  the By Handle dialog were observed; action-count and synchronous accessibility timeout failures remain.
- All six staged source-preserving candidates pass strict comparison and independent byte reconstruction.
  All six matched library saves pass semantic strict comparison but fail exact byte reconstruction.
- One libre-air-water no-edit native UI process completed open/select/field checks/Save As/close/reopen,
  editable-field checks and normal native exit. Its three common-frame canvas comparisons have zero changed
  pixels. The returned file nevertheless retains 300 strict differences, including AC1021 to AC1027 conversion.
- A separate edited process retained a keyboard-routing failure: Ctrl+A reached the drawing, selected all
  14 entities and left MANUFACTURER unchanged. It refused before save. A separately frozen recovery in that
  same process clicked the actual field, verified focus/text/commit and completed edit/save/close/reopen.
  Native/UI/readback show QUAL-AFTER with ICT_ID and TAG unchanged. Native exit is 0; original controller
  and container remain failed (1), so this is not a clean full-procedure pass.
- The recovered return also retains 300 source-to-return strict differences. No-edit versus recovered-edit
  comparison retains 57 unexpected entity differences; table handle assignments and saved view/layout values
  are visible. They are not waived. This recovery had the earlier wrong-window keystrokes and cannot stand in
  for the clean matched cohort.

The failures and corrections are in [DEVELOPMENT-NOTES.md](DEVELOPMENT-NOTES.md). Current observations are
retained locally under `C:/Users/Steve/.cp-scratch/cad-native-ui-pairs-19/`; portable publication, complete
offline receiving, loss controls and CI for this experiment are unfinished. Earlier sealed packets are intact.

## Fresh cohort in progress

Freeze `5f27559` precedes a new 18-process cohort: baseline, edited and fresh receiving process for each
of the six drawings. Four isolated processes may run concurrently. The batch locks method hashes before
later job launches, stops launching after a controller failure and never restarts an existing process.
Historical/recovered processes are not adopted into this cohort. Each receiver opens source, no-edit return,
edited return and exact-span candidate serially. [METHOD.md](METHOD.md) owns the checks and fixed pixel region.

Do not infer completed coverage from this plan or a live batch. Inspect the actual process handles and
finished receipts, then retain all attempted outcomes, recompute complete comparisons and assemble bounded
lossless packets. Fresh independent/reserved evaluation, foreign-attribute/other text coverage, original
revision/conflict gates and engineering/company acceptance remain open.
