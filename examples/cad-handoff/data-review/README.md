# Review equipment data while preserving the CAD drawing

Use this when your maintenance/engineering job is to correct **existing equipment attributes**, rather than
redraw geometry. An agent can prepare the exchange and apply your proposed values. A reviewer can use the
local form. No CAD application, account, commercial subscription or model API is required for these steps.

A native CAD session checks the **receiving drawing**, separately from this metadata entry. The
[Linux receiving experiment](../qualification/linux-native-7/README.md) opens the source-preserving valve
candidate with readable labels and editable fields. A full native editor save still produces strict differences,
so this form applies only declared value spans against the original. Layouts, fonts, geometry changes and target
editor acceptance need their own checks; they are not dependencies for preparing a data proposal here.

The source must meet the [DXF handoff profile](../README.md#use-your-own-dxf): explicit unique ICT_ID and TAG
attributes on each model-space asset INSERT. Only present TAG, MANUFACTURER, MODEL, SERIAL and SIZE fields can
change. Foreign fields remain visible and read-only; missing identities are a preparation task, not guessed.

## Try the fictional valve or substitute your source

From the repository root, Python 3.10+ with the pinned requirements installed:

```sh
python scripts/cad_exchange.py prepare examples/cad-handoff/source/valve.dxf --out out/my-cad-review
python -m http.server 8796 --bind 127.0.0.1 --directory out/my-cad-review
```

Open `http://127.0.0.1:8796/review.html` in your browser. The server serves that review folder locally; it does
not receive edits or contact a company system. Stop it with Ctrl+C after review. A generated form has its data
embedded and no external dependencies; direct `file:` opening was blocked by the test connector, so the
verified tutorial route is loopback HTTP. This committed folder is a ready-made example of the prepared output.

Change MODEL from SRC-2 to SRC-3, enter a reason referencing your evidence and choose **Download proposed
changes**. These particular records are fictional: the example does not establish that a replacement occurred.
Save the downloaded JSON somewhere appropriate, then have your agent run:

```sh
python scripts/cad_exchange.py apply examples/cad-handoff/source/valve.dxf out/my-cad-review/exchange.json PATH_TO_DOWNLOADED_RESPONSE.json --out out/my-cad-draft
python scripts/cad_exchange.py prepare out/my-cad-draft/candidate.dxf --out out/my-cad-review-revision
```

The draft retains the exact source, complete catalog, exact original returned JSON bytes, normalized response,
hash-bound plan, strict comparison, edited candidate and original/proposed context packets. Inspect the draft
and its reasons before any engineering release. A reason string or downloaded file is not authenticated approval.
Prepare and serve the revised folder to review a subsequent version. Reusing an old response on a changed source
refuses before output; there is no automatic rebase or conflict choice.

## Ask your agent to do it

> Prepare an equipment-data review for this DXF. Show me existing fields and missing evidence. Propose only
> supported attribute changes with exact before values and evidence reasons. Use a fresh destination, retain the
> original, apply the response with cad_exchange.py, and report the strict comparison and draft context changes.

The agent uses `exchange.json` and returns this structure, without needing the form:

```json
{
  "schema": "cad-data-response-1",
  "source_sha256": "exact source hash from exchange.json",
  "exchange_sha256": "cad_exchange.fingerprint(complete exchange.json)",
  "changes": [
    {"id": "explicit ICT_ID", "attribute": "MODEL", "before": "exact source value",
     "after": "proposed value", "reason": "supplied evidence, with its uncertainty"}
  ]
}
```

For Python callers, `cad_exchange.response_for(exchange, changes)` constructs the response binding. The full
catalog is regenerated from the current DXF on apply; changing an allowlist or catalog does not grant editing
rights. Empty, duplicate, extra/unknown/identity/foreign-field, stale, multiline and overlong changes refuse.
The retained proposed context can follow the existing [explicit map projection](../README.md#carry-the-explicit-exchange-into-the-context-map).
Installed records, relationships and site decisions are not silently overwritten.

## What this design qualifies

The drawing never goes through a full CAD save: only declared raw attribute value spans are patched. Independent
source-plus-plan reconstruction and the unchanged strict comparator verify preservation. This removes full-save
rewriting from this equipment-data job; it does not make a native full save equivalent or resolve its failures.

The [six-case evidence](../qualification/exchange-6/README.md) reports 10 edits on nine authored assets, with
zero unexpected differences and no unplanned byte changes. A real browser download/apply/reopen exercise is
retained separately. These are software checks, not independent plant data or a human adoption trial.

**A native CAD UI is needed when the claim is interactive drafting/editability in that editor.** It is not a
prerequisite to this source-preserving metadata operation. Native layout appearance, unknown proprietary
semantics, full-editor saves, DWG and released engineering documents still need their own receiving checks.
For geometry changes use the owning CAD workflow and audit its complete return; do not submit a full returned
DXF as this sidecar or treat untransferred geometry edits as accepted.
