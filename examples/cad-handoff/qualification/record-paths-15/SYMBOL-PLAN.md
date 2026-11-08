# Test the observed invalid-symbol candidate without rewriting the sources

Declared after the complete crossed cohort and before this native intervention.
The retained hydraulic native inventories differ in only two named identities:
Continuous/CONTINUOUS and 2_2-directional valve/2/2-directional valve. OpenDesign
import sanitizes the block's slash; dxflib import retains it. Both original
dxflib->OpenDesign hydraulic namespace variants fail Invalid Symbol Table name.

Use the exact two frozen hydraulic sources from attempt-4 in a new symbol-5
workdir. For each, import explicitly with dxflib and export R15 OpenDesign:

1. No operation, to reproduce the original failure.
2. Rename only block 2/2-directional valve to 2_2-directional valve with an
   ordinary native add-object operation, applyCurrentAttributes=false.
3. Rename only the unrelated valid ICT_QUAL_TEST_ANCHOR block to
   ICT_QUAL_TEST_CONTROL, leaving the slash name unchanged.

Freeze methods, inputs and six-job manifest before execution. Capture complete
public inventories before/after the operation, export and reopen, and fresh
imports only for successful exports. Require exactly the declared public block
name change; preserve IDs, other public properties and document variables.
Keep any strict profile refusals and the raw returned files. Original source
bytes and earlier errors never change. Successful export alone is not geometry,
attribute, source preservation, full CAD or engineering qualification.

Evidence for the specific causal hypothesis requires unchanged and unrelated
controls still to fail, with the target-only rename permitting both exports.
Otherwise retain the failed hypothesis; do not expand the intervention after
seeing results. The controller retains complete failure coverage and exits1
if any native job failed, as in the earlier declared diagnostic method.
