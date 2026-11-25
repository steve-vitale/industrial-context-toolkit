# Engineering-records readiness self-assessment

This page helps you see where one unit stands against the six conditions in [the end picture](END_PICTURE.md). It
answers one question: if your team's assistants were pointed at this unit's records today, what would they
find, and what would they get wrong?

Each condition has four levels. A unit sits at one level per condition. The level is the lowest one that holds
for the records examined.

## The levels

### 1. Visible

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Not reachable. Records live on paper, in personal folders or in one person's memory. | Where the equipment list, work orders, datasheets and drawings actually are |
| 2 | Reachable by export. Someone can produce a file on request. | A sample export of each record, and who produced it |
| 3 | Reachable by the team's assistant. The approved assistant can open them without a manual step. | A test question answered from the real records |
| 4 | Reachable with owners and refresh dates. Each record has a named owner and a date it was last refreshed. | The register of records, with owner and date columns |

### 2. Tied to equipment

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Facts are free text. Tags are missing or spelled several ways. | A sample of rows from each record, checked for tags |
| 2 | Most facts carry a tag, but the same item has different tags in different records. | Tags compared across the equipment list, work orders and drawings |
| 3 | Every fact in the sample carries one agreed tag. | The same sample, matched tag by tag |
| 4 | Every fact carries the tag and its source: file, row or drawing location. | A fact picked at random and traced to its source |

### 3. Owned

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Nobody is named. Disagreements stay open or get settled by whoever notices. | A recent disagreement and what happened to it |
| 2 | Owners exist by habit, without names written down. | Who people say owns each record |
| 3 | Each record has a named owner. | The owner list, checked against practice |
| 4 | Named owners, and disagreements go to them with the evidence attached. | A disagreement followed from detection to ruling |

### 4. Kept current

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Records change when someone remembers. | Dates of last change on a sample of records |
| 2 | Some records are updated at closeout, by habit. | A recent work order closeout and what it updated |
| 3 | Closeouts for work orders, drawing revisions and MOCs include a record check. | The closeout procedure, and a recent closed job |
| 4 | Closeout checks plus a refresh interval for each record, and someone notices when one is missed. | The interval list and the last refresh of each record |

### 5. Connected

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | The CMMS, historian and document store cannot be read together. | How a recent cross-system question was answered |
| 2 | Each can be exported. Someone joins the exports by hand. | The export routes and their formats |
| 3 | The team's approved assistant reads them by export or connector. | A test question that spans two systems |
| 4 | Connected, with identities matched between systems (a historian tag to an equipment tag) and the mapping owned. | The tag mapping and who maintains it |

### 6. Recorded

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Changes are in email and memory. | How a past change was reconstructed |
| 2 | Changes are in files: MOC forms, marked-up drawings, spreadsheets. | The files for one recent change |
| 3 | Changes and the reasons for them are kept in one place, but not tied to the equipment records. | The change log and how it links to records |
| 4 | Changes and reasons live in a governed system of record, tied to the equipment and the records they changed. | A change traced from request to closeout |

## What your records can support

The levels matter because each kind of assistant work needs a minimum set of them. An assistant used above what
the records support still answers. It answers confidently from the wrong revision, the wrong unit or a stale
export, and nobody can tell. Read the tier your unit supports today from the lowest condition it needs.

| Tier | What the assistant does | Example question or task | Minimum levels |
|---|---|---|---|
| **1. Find documents** | Searches and summarizes files the user can open, such as a work Copilot over SharePoint. | "Find the startup procedure for the pasteurizer." | Visible 3 |
| **2. Answer about equipment** | Answers a question about one tag from several records and shows where each fact came from. | "What size is FDV-2210, and which record says so?" | Visible 3, Tied to equipment 3 |
| **3. Investigate across systems** | Joins the CMMS, documents and historian for a unit, flags records that disagree and drafts the note to each owner. | "Which valves in this unit were replaced in the last year but still show the old size on the datasheet?" | Tied to equipment 4, Owned 3, Connected 3 |
| **4. Work inside a governed service** | Proposes record changes, keeps them current as work orders, revisions and MOCs close, and keeps each decision with its reason and approver. People approve; the assistant does the legwork. | "FDV-2210's work order closed. Propose the datasheet and CMMS updates and route them to their owners." | Owned 4, Kept current 4, Connected 4, Recorded 4 |

Most units start at tier 1 for some records and below it for others. Moving up a tier is usually one or two
conditions, not all six. The [worked sample](../examples/readiness-audit/SAMPLE_REPORT.md) shows a unit at tier 2 with a manual step
and the jobs that would take it to tier 3.

Tier 4 is not something this repository provides. It needs a governed system of record that people and agents
share. The toolkit prepares the records and the [context-map format](CONTEXT_MAP_FORMAT.md) such a service can
read; see the [foundation roadmap](ENGINEERING_FOUNDATION.md).

## How to use it

1. Pick one unit and a handful of records: the equipment list, recent work orders, datasheets and drawings.
2. For each condition, find the level whose description holds for the records you sampled, using the evidence
   column as a guide.
3. Read which tier the unit supports today, then list the conditions that hold it below the next tier. Each
   one points to a job: for example, level 2 on "Tied to equipment" calls for a
   [record reconciliation](MAINTENANCE_INTAKE.md).

A [worked sample](../examples/readiness-audit/SAMPLE_REPORT.md) for a fictional unit shows the result.

## Limits

The levels are plain-word descriptions. They are not a certified standard or a comparison with other plants.
They have been exercised on public and fictional inputs only. A level describes the records examined, not the
whole plant.
