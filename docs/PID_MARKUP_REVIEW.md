# Did the returned P&ID incorporate your markups?

Start with **three retained records**: the original drawing, the exact annotated version/instructions
sent out, and the consultant's returned revision. Review each requested change against what the returned
drawing actually shows. Also look for changes nobody requested. This job needs no complete plant graph,
MCP service or CAD UI when the supplied drawing pages are readable without one.

The [fictional example](../examples/pid-markup-review/README.md) is runnable now. It deliberately includes
a valve left in place, a half-finished bypass, a missing signal and an unrequested fail-action change.
The reusable local tool compares prepared readings and keeps the evidence; **it does not itself read
arbitrary PDFs, handwriting or CAD drawings**. An engineer or an approved assistant supplies those readings.
Actual image-reading accuracy, completeness and human review effort remain unmeasured.

## Start with an approved assistant or manual review

If your approved assistant already accesses the documents in SharePoint, use that access. The toolkit adds
an explicit check list and retained evidence, not a new SharePoint connection. This prompt is usable without
installing Python:

```text
Review whether the consultant incorporated my P&ID markups. Retain the original,
the exact marked-up version/instructions sent out, and the returned revision.
Confirm sheet numbers, revisions and page correspondence from the actual documents.
Inventory every annotation, including illegible ones, before deciding whether changes match.
Split multi-part instructions into separate checks. For each, show the requested
before/after condition and original/returned evidence with page and region.
Trace the relevant process or signal connections; finding the tag is insufficient.
Report supported, partial, unchanged, different and unverifiable checks. Do not
infer absence from a failed search or incomplete extraction. Flag other observed
changes and any region or sheet that was not checked. Keep safety items for review.
Return a correction/clarification list. Do not approve or release the drawing.
Use docs/PID_MARKUP_REVIEW.md from industrial-context-toolkit for the optional
source-bound local packet format. Keep company records in the approved environment.
```

Read title blocks and transmittal scope, not just filenames or revision clouds. Account for reordered sheets,
rotated/scaled scans and cross-sheet references. Number annotations that have no IDs. Preserve unclear
instructions as questions instead of choosing an interpretation. Review a whole changed region and its
connection endpoints, including nearby labels, notes and continuations.

Freeze the requested-change list before scoring the return. First transcribe what the returned region shows;
then compare it with the request. This reduces leading the reading toward an expected value, but is not an
independent visual review. Overlay/pixel differences may help locate changes; they cannot by themselves
establish that a valve, connection or control function matches the requested intent.

## Prepare and run a local packet

Use Python 3.10+ standard library. Put permitted working copies and prepared JSON in one private input folder.
The [example inputs](../examples/pid-markup-review/inputs/manifest.json) show the complete contract:

- `manifest.json`, schema `pid-markup-review-1`: local source files with SHA-256, document ID and role
  (`original`, `markup`, `returned`). Each has declared page number, qualified sheet, revision and
  `identity: confirmed` or `uncertain`. Sheet identity is unique within a role; qualify names by plant/unit.
  Also pin the request and reading JSON files. Paths are relative, inside this folder, with forward slashes.
- `requests.json`, schema `pid-markup-requests-1`: inventory basis and every numbered markup. Each has
  sheet, exact request text, `normal`/`safety` priority, source evidence and interpretation
  (`prepared`, `unreadable`, `unsupported`). Prepared rows have explicit before/after checks; other rows
  retain a reason and an empty check list. Conflicting requested outcomes for the same fact refuse.
- `readings.json`, schema `pid-drawing-readings-1`: method/limitations and original/returned observations.
  Each is `known` with a value or `unknown` with a reason. Conflicting readings remain ambiguous.
  Source evidence names document ID, exact document SHA-256, page, `box_0_1000: [left,top,right,bottom]`
  measured from the page's top-left, and a readable description. These are supplied locators, not automatically
  verified quotations or PDF page-count checks. Explicit absence needs a reason describing the region checked.

Check keys are intentionally small and exact:

| Fact | Key besides `sheet` | Value |
|---|---|---|
| Symbol presence | `kind: symbol`, `subject: HV-102` | Boolean present/absent |
| Attribute | `kind: attribute`, `subject: FV-101`, `name: size` | Explicit typed value, e.g. `"DN80"` |
| Note text | `kind: note`, `subject: drain-note` | Supplied note text anchored across revisions |
| Directed connection | `kind: connection`, `subject: PT-101`, `relation: signal`, `to: PIC-101` | Boolean present/absent |

Names, relation types, direction and values must match exactly. There is no fuzzy tag match, unit conversion,
automatic symbol equivalence, path tracing or cross-sheet identity resolver. Represent multiple bypass segments
as separate checks; valve presence alone does not establish a complete route. Stable anchors and exact fact
meanings are supplied interpretation. Existing drawing readers/DEXPI tools may help prepare readings, but
this command does not directly import their formats or upgrade uncertain topology into a known connection.

```sh
python -S scripts/check_pid_markups.py --manifest PRIVATE_INPUT/manifest.json --out PRIVATE_NEW_PACKET
```

The output retains exact source bytes, original input manifest, exact requests/readings and a portable
`manifest.json`. It writes `REPORT.html`, `REPORT.md`, complete `result.json`, `review_queue.csv` and a hash
receipt including the tool's LF-normalized source hash. Open the HTML for both readings/locators on each check.
All markups, other observed changes and other coverage gaps enter the CSV. Safety markups stay first even if
supported; unrequested changes require assessment, not an automatically inferred risk classification.
Keep the entire folder when passing the review to another person. Its portable manifest supports re-running
the comparison after relocation. A hash receipt is an integrity record, not authenticated approval.

Exit 0 means a comparison packet was written, including open findings. Exit 2 refuses invalid/stale inputs
or an existing output. Neither is a drawing-release decision. Stale source hashes and observations bound to an
older returned document refuse even if someone updates the manifest alone.

## Interpret and close the findings

| Outcome | Meaning from the supplied readings |
|---|---|
| Supported | Every before value matches the original and every returned value matches the request. |
| Partly supported | Some checks match but others fail or remain open. The report retains each check. |
| Not supported | A checked value/connection stayed unchanged or differs from the request. |
| Original differs from request | The markup's assumed before condition conflicts with the original reading. Resolve the baseline/intent first. |
| Cannot verify / ambiguous | Evidence is missing, unreadable, conflicting, unsupported, or sheet/revision identity is uncertain. |

Only supplied facts are compared. Missing observation rows never prove removal; a missing sheet is not a clean
sheet. Unlisted annotations, drawing geometry, line styles, omitted detail and functional adequacy can escape
this comparison. Review inventory and reading coverage before relying on positive rows. All safety rows require
engineering review; interpreting markups correctly does not establish a safe design or installed condition.

Send the responsible reviewer a concise issue list: annotation ID, requested condition, returned evidence,
correction/clarification needed, owner and disposition. Keep engineering/drafting decisions in the company's
existing process. A later return needs its own exact source and fresh bound readings in a new output folder;
do not carry old supported labels forward. The example's corrected return still leaves the illegible instruction
and wrong-baseline request open. Native CAD editability and preservation remain a separate
[receiving review](../examples/cad-handoff/receiving-review/README.md).

Once an organization accepts the revision, its accepted model/records may feed the existing
[context/map revision route](RUNNING_THE_MAP.md). This tool does not update the map, MOC record or source system.
For a larger drawing backlog, [connect with me on LinkedIn and message me there](https://www.linkedin.com/in/steve-vitale/).
