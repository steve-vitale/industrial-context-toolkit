# Engineering-records readiness self-assessment

This page helps you see where one unit stands against the six conditions in [the end picture](END_PICTURE.md). It
answers one question: if your team's assistants were pointed at this unit's records today, what would they
find, and what would they get wrong?

Each condition has four levels. Rate each record family in the unit separately: maintenance records are often
far ahead of process safety records. Within a family, the level is the lowest one that holds for the records
examined.

## Record families

A unit's engineering context is spread across many more records than the equipment list, work orders and
drawings. Rate each family separately. The families are a starting checklist; add any your site keeps.

| Family | Typical records | Usual owner | Usual home |
|---|---|---|---|
| **Drawings** | P&IDs, PFDs, loop diagrams, isometrics, electrical one-lines, plot plans, as-builts | Engineering, doc control | Doc control's system, CAD folders |
| **Equipment and instrument data** | Equipment datasheets and specs, instrument index, I/O list, cause and effect matrix, alarm database, motor list, nameplate photos | Engineering, I&C | Engineering folders, spreadsheets, I&C database |
| **Maintenance** | Asset register, work orders, PM job plans, spare parts and bills of materials, calibration records, inspection and thickness readings, condition monitoring | Maintenance, reliability, quality | CMMS, calibration system, reliability software |
| **Operations** | SOPs, operating limits, alarm response, isolation and lockout lists, shift logs, operator rounds | Operations | Doc control's system, binders, logbooks |
| **Process safety and quality** | HAZOP and LOPA worksheets, safety requirements specs, relief studies and relief device register, MOC packages, pre-startup safety reviews, incident investigations, HACCP plans, environmental registers | Process safety, quality, environmental | MOC tool, quality system, reports, folders |
| **Control and process data** | Historian tags and trends, control narratives, DCS or PLC configuration, HMI screens | Controls, I&C | Historian, control system |
| **Vendor and project records** | Vendor manuals, pump curves, purchase specs, calculations, turnover and commissioning packages, punch lists | Engineering, projects, maintenance | Vendor PDFs, project folders, vendor portals |
| **Decisions and conversations** | Meeting notes and transcripts, emails, chat threads, decision logs, field markups | Whoever made the decision | Inboxes, team sites, notebooks |

The last family is the one most plants skip and most questions need: why something is the way it is.

## The levels

### 1. Visible

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Not reachable. Records live on paper, in personal folders or in one person's memory. | Where each record in the family actually is |
| 2 | Reachable by export. Someone can produce a file on request. | A sample export of each record, and who produced it |
| 3 | Reachable by the team's assistant. The approved assistant can open them without a manual step. | A test question answered from the real records |
| 4 | Reachable through a register of records the assistant can read, so it knows what exists and what it can't see. | The register, checked against what is actually there |

### 2. Tied to equipment

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Facts are free text. Tags are missing or spelled several ways. | A sample of records from the family, checked for tags |
| 2 | Most facts carry a tag, but the same item has different tags in different records. | Tags compared across the records in the family and the P&ID |
| 3 | Every fact in the sample carries one agreed identity: an equipment tag, or for unit-wide records such as procedures and calculations, the system or unit. | The same sample, matched identity by identity |
| 4 | Every fact carries the tag and its source: file, row or drawing location. | A fact picked at random and traced to its source |

### 3. Owned

| Level | In plain words | Evidence looked at |
|---|---|---|
| 1 | Nobody is named. Disagreements stay open or get settled by whoever notices. | A recent disagreement and what happened to it |
| 2 | Owners are departments or habit, not named people. | Who people say owns each record |
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
| 1 | The family's systems (CMMS, historian, doc control, MOC tool, quality system) cannot be read together. | How a recent cross-system question was answered |
| 2 | Each can be exported. Someone joins the exports by hand. | The export routes and their formats |
| 3 | The team's approved assistant reads them by export or connector. | A test question that spans two families |
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
export, and nobody can tell.

**A tier belongs to a question, not to a plant.** The tier available for a question is the lowest tier of the
record families that question needs. A unit can support tier 3 on maintenance questions and tier 1 on anything
that touches its relief devices.

| Tier | What the assistant does | Example question or task | Minimum levels, in every family the question uses |
|---|---|---|---|
| **0. Work from handed files** | Reads an export someone hands it for each question. The answer is only as current as that export. | "Here's this week's CMMS export: which critical valves have no PM plan?" | Visible 2 |
| **1. Find documents** | Searches and summarizes files the user can open, such as a work Copilot over SharePoint. It finds documents; it doesn't reconcile them. | "Find the startup procedure for the pasteurizer." | Visible 3 |
| **2. Answer about equipment** | Answers about one tag from several records in reach and names the document each fact came from. | "What size is FDV-2210, and which record says so?" | Visible 3, Tied to equipment 3 |
| **3. Investigate across families** | Joins records from different families and systems for a unit, such as work orders with datasheets, trends and the MOC log. It flags records that disagree and drafts the note to each owner. | "Which valves replaced this year still show the old size on the datasheet, and was an MOC raised for any of them?" | Visible 3, Tied to equipment 4, Owned 3, Kept current 3, Connected 3 |
| **4. Work inside a governed service** | Proposes record changes as work orders, revisions and MOCs close, routes them to the owners, and keeps each decision with its reason and approver. People approve; the assistant does the legwork. | "FDV-2210's work order closed. Propose the datasheet and CMMS updates and route them to their owners." | All six conditions at 4 |

**Safety-critical families need more before any tier above 1.** For relief devices, safety instrumented
functions, HAZOP actions, MOC packages and food safety control points, the records also need their released
status visible (draft, released, or a dated copy) and a named person, not a department, who owns them. These
are two separate checks. Until both hold, the family stays at tier 1 or below. Even then, an answer is a sourced draft for
the responsible engineer, never the decision.

**Levels describe the records, not the assistant.** Before relying on a tier, ask three real questions at that
tier and check each answer against its source. Every answer is only as current as the last refresh of the
records it used, so it should give that date.

Most units are at different tiers for different families. Moving one family up a tier is usually one or two
conditions, not all six. The [worked sample](../examples/readiness-audit/SAMPLE_REPORT.md) rates a fictional
unit family by family.

Tier 4 is not something this repository provides. It needs a governed system of record that people and agents
share. The toolkit prepares the records and the [context-map format](CONTEXT_MAP_FORMAT.md) such a service can
read; see the [foundation roadmap](ENGINEERING_FOUNDATION.md).

## How to use it

Before rating anything, map where the unit's records live with the
[offline worksheet](../examples/readiness-audit/worksheet.html): which assistant you may use, which systems hold each
kind of record, and what that assistant can reach today. Nothing is sent anywhere.

1. Pick one unit and the record families your questions need. Sample a handful of records from each.
2. For each family and condition, find the level whose description holds for the records you sampled, using the evidence
   column as a guide.
3. Pick the three or four questions your team most wants an assistant to answer. Read the tier each one gets
   today, then list the conditions that hold it below the next tier. Each one points to a job: for example, level 2 on "Tied to equipment" calls for a
   [record reconciliation](MAINTENANCE_INTAKE.md).

A [worked sample](../examples/readiness-audit/SAMPLE_REPORT.md) for a fictional unit shows the result.

## Limits

The levels are plain-word descriptions. They are not a certified standard or a comparison with other plants.
They have been exercised on public and fictional inputs only. A level describes the records examined, not the
whole plant.
