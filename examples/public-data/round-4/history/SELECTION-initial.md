# Linked maintenance acquisition, declared before row download

Acquire one source family: NYC Parks' public AMPS system, using the publisher's table descriptions and
field definitions. This is municipal maintenance, not an industrial plant trial. No model or evaluation run.

- Select **all work orders whose `evt_date` is in [2024-01-01, 2024-01-08)**. Do not select for completion,
  parts usage, repair success, particular equipment, or favorable joins. Retain open/missing records.
- Fetch referenced assets (`evt_object` -> `obj_code`), transactions whose `tra_toentity = 'EVNT'` and
  `tra_tocode` refers to the selected work orders, transaction details (`trl_trans` -> `tra_code`), and labor
  (`boo_event` -> `evt_code`). These relationships come from the publisher metadata, not guessed text matches.
- Explicit field projections are in `acquire.py`. Labor has trade/hours/cost/correction and no worker identity.
  Do not fetch the separate comments collection. Original projected API response bytes remain local/ignored;
  publish pins, queries, schema metadata, counts, missing/ambiguous joins and limitations, not source rows.
- Sort keys and batches of 100 identifiers are deterministic. Work-order ceiling 5,000, related batch ceiling
  10,000, total HTTP body budget 20 MB, 60-second timeout. Query one extra row to detect overflow; retain and
  report it as a failed bounded acquisition, never a complete cohort. No outcome-dependent fallback dates.
- Keep all attempted queries and failures, raw metadata and response hashes. Live tables can change; later
  different bytes must fail the pins rather than silently refresh the cohort. A sequential linked fetch is
  not a transactionally consistent historical database snapshot.
- Check raw integrity, projected schemas, duplicate/missing primary keys and relationship coverage. Completion
  fields are administrative observations, not verified repair effectiveness; transaction quantities may be
  returns/corrections and must not automatically be called consumption. Do not sum costs/hours yet.
- No open-data license ID was present in the five inspected metadata documents. Retain publisher terms and
  attribution, keep records local, and do not infer public-domain rights or an open redistribution license.

The existing drawing/CAD splits, methods and scores remain unchanged. This acquisition cannot qualify CAD,
establish current installed truth or add an independent plant/engineering acceptance result.
