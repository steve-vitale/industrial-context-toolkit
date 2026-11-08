# Execute the current workflow entry points

This is a fixed public/fictional fixture runner for the
[workflow reproduction guide](../../../docs/REPRODUCE_A_WORKFLOW.md), not a general
importer or an independent agent session. It calls the actual existing tools and
example runners for maintenance revisions, markup returns, exact ports,
cross-sheet paths, drawing bundles, knowledge revisions and batch calculations.
It then executes five existing regression suites, including wrong-input,
missing-source and next-revision controls.

From the repository root, with Python 3.10+ standard library and a new destination:

```sh
python -S examples/agent-first-use/workflow-check/reproduce.py --out ../ict-repro-check
```

Inspect `PLAN.json`, `COMMANDS.json`, `RESULT.json` and each command's stdout/stderr.
The output includes the actual workflow reports and retained revision packets.
`all_pass` requires every command to exit zero and the additional declared checks
to agree with the pre-existing markup key, maintenance/knowledge revision checks,
and complete committed batch result. Port/path runners check their own frozen
keys and intentionally wrong baselines. Read those results, not only the boolean.
An existing output directory refuses before work and is never replaced.

These results test command discovery, software contracts and the supplied cases.
They do not measure new image reading, manager usefulness, end-to-end human time,
native CAD/platform acceptance or commercial demand. See the guide for supplied
preparation and for using your own records; keep those in an approved location.
