# A reusable receiving job, using the existing checkers

The current markup and CAD tools already accept a user's inputs. The combined
rehearsal brief is case-specific. Add a thin own-input command that accepts a job
manifest, invokes those unchanged tools and builds its brief entirely from their
results. Keep the two teaching drawings explicitly separate. This is workflow
orchestration, not another CAD renderer or a new drawing reader.

Before validating the new command, keep these observable requirements:

- Retain every supplied request outcome, safety review, other observed change,
  coverage gap and CAD attribute/identity finding. Link all strict differences.
- Show the actual before/returned values, including unknowns, for collateral
  changes and coverage gaps. Keep full source checks/locators in machine output.
- Derive actions from supplied outcomes, without fixed tags, request IDs or case
  names. Suggested roles remain unassigned; authorized decisions remain pending.
- Preserve the markup and CAD checkers and their original comparison results.
  Do not require a native CAD session to use the receiving command.
- Support markup-only standard-library use and optional DXF checks with the
  existing dependency. Do not silently call source-bound readings image reading.
- Preserve an exact original job, source-bearing sub-packets and a rewritten
  portable job. Re-running the portable job must reproduce the brief.
- Refuse stale inputs, duplicate drawing IDs and occupied/overlapping output
  paths without changing earlier packets or inputs. Preflight all selected checks
  before publishing the output folder.
- If a user supplies both representations under one drawing ID, retain that
  supplied association and explicitly leave CAD/readable-sheet correspondence
  unverified. Separate drawings must not be silently merged.

Validate first against the existing two teaching cases and direct checker outputs,
then a markup-only portable replay and deliberate bad-input/refusal controls.
This establishes orchestration behavior, not new reader accuracy, engineer timing,
paper delivery, native-save preservation or engineering acceptance. The existing
CAD qualification objective and its failures remain open.
