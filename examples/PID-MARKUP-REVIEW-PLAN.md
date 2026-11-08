# Requested P&ID markup verification — development plan

Written before the tool and fictional fixture. This is a new reusable preparation/review route,
not a claim that arbitrary markups or returned drawings can already be interpreted automatically.

## Job

Compare the exact original drawing, exact markups sent to a consultant, and exact returned
revision against an explicit inventory of requested changes. A company-approved assistant or
engineer reads the documents and authors source-bound observations; code compares those
observations without inventing missing facts. No CAD UI, MCP, company account or live system
is needed for this local comparison. Existing CAD receiving review remains separate.

## Acceptance before implementation

- Pin and retain original/markup/returned source bytes, sheet/page/revision identities and
  prepared request/reading bytes. Every intent and observation has exact document hash,
  declared page/sheet and normalized region. Refuse stale bindings before publication.
- Do not equate a changed pixel, found tag, new revision letter or present symbol with a
  requested connection or function. Check explicit symbol presence, attribute/note values
  and typed directed connections separately, in a sheet-qualified namespace.
- Each interpreted markup decomposes into one or more explicit before/after checks.
  Unreadable/unsupported markups remain inventory rows. Require every inventory row to
  appear in results. Inventory completeness and source interpretation remain supplied work.
- Only known, unambiguous original values matching the request's before value plus known
  returned values matching its after value support a check. Report unchanged, different,
  ambiguous, missing/unreadable and baseline-mismatch outcomes separately. No silent
  absence inference from a missing extraction row. Exact typed comparison, no fuzzy tags
  or unrequested unit conversion; explicit absence needs its own source observation.
- Aggregate multi-part markups without hiding failed/open checks. Safety-priority rows
  remain in the review queue even when observed checks match. Never accept/release a drawing.
- Compare every other supplied fact, listing unexpected observed changes and coverage gaps.
  This is bounded by reading coverage; no full-sheet visual/CAD preservation or installed-state
  claim follows. Keep original locators beside requests and returned findings.
- Write a new offline packet with JSON, CSV, readable HTML/Markdown, exact sources and
  prepared inputs. Refuse output collisions; escape user text in HTML; preserve inputs.

## Fictional example and independent observable controls

Author a small water-transfer drawing, numbered redline requests and a deliberately imperfect
returned drawing. Freeze a separately written expected-outcome key before running the tool.
Include a correct size update; unchanged deletion; partial valve/connection addition; present
instrument with missing requested signal; unclear note; baseline mismatch; and an unrequested
changed value. No plant records, real consultant, model extraction accuracy or timed human
benefit is represented. Fixture observations are authored from the same fictional design,
not an independent test of visual reading. Directly inspect the actual source drawings/report.

Controls must refuse stale source/readings, duplicate/ambiguous source identities, wrong
sheet/page/hash/regions, output collision, typed mismatches and unsafe input paths. Conflicting
readings and missing negative coverage must stay unresolved instead of passing. Re-run with a
corrected later return to verify earlier findings do not carry over without a new bound reading.
Register meaningful regression tests, tool discovery, feature evidence and the attempt ledger.
Existing CAD scorer/patcher, qualification sources, old failures and acceptance criteria stay frozen.
