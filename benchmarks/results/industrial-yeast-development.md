# Task results: industrial-yeast-development

Task: `batch-totals`. Industrial-yeast depth task (docs/DEPTH_GOAL.md, attempt A418): development batches B01-B05; held-out batches not yet run. Deterministic tool runs; the key is the sum of the same logged feeds, so this checks integration semantics, units, coverage and windows, not measurement accuracy.

Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.

## Deliberately wrong controls (built by the scorer from each key)

Matched / key items within 0.5 kg. Tool-run controls (wrong interpolation, wrong unit) are separate runs below. Recall in the F1 table is matched / key items; an incomplete or missing total is unanswered, never zero.

| Case | perfect | empty | shuffled | recipe_constant |
|---|---|---|---|---|
| yeast-development-batch | 5 / 5 | 0 / 5 | 2 / 5 | 3 / 5 |
| yeast-development-hourly | 84 / 84 | 0 / 84 | 0 / 84 | 0 / 84 |

| Model / version | Method / interface | Family / split / evidence | Cohort | Cases | Replicates | Metric | Mean F1 | Min–max | SD |
|---|---|---|---|---|---|---|---|---|---|
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py next, unit declared kg/s / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; hourly windows; development batches B01-B05 | d662a472f40b | 1 | 1 | hourly_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | batch_analysis.py V2 interval-ending hold (next), kg/h / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; hourly windows; development batches B01-B05 | d662a472f40b | 1 | 1 | hourly_feed_totals | 1.0000 | 1.0000–1.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py linear, blank hour-0 feed written as 0 / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; hourly windows; development batches B01-B05 | d662a472f40b | 1 | 1 | hourly_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py previous-value hold / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; hourly windows; development batches B01-B05 | d662a472f40b | 1 | 1 | hourly_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py linear (trapezoid) / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; hourly windows; development batches B01-B05 | d662a472f40b | 1 | 1 | hourly_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py linear (trapezoid) / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; whole-batch windows; development batches B01-B05 | 457a005e6364 | 1 | 1 | batch_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | batch_analysis.py V2 interval-ending hold (next), kg/h / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; whole-batch windows; development batches B01-B05 | 457a005e6364 | 1 | 1 | batch_feed_totals | 1.0000 | 1.0000–1.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py previous-value hold / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; whole-batch windows; development batches B01-B05 | 457a005e6364 | 1 | 1 | batch_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py next, unit declared kg/s / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; whole-batch windows; development batches B01-B05 | 457a005e6364 | 1 | 1 | batch_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |
| deterministic-tool / scripts/batch_analysis.py as committed with A418 | control: batch_analysis.py linear, blank hour-0 feed written as 0 / scripts/batch_analysis.py CLI via scripts/industrial_yeast_case.py | industrial-yeast / development / Publisher-logged running cumulative (total_fermentable_sugar_kg), withheld from the tool; whole-batch windows; development batches B01-B05 | 457a005e6364 | 1 | 1 | batch_feed_totals | 0.0000 | 0.0000–0.0000 | unavailable |

## Coverage and failures

- yeast-development-method (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-method (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-trapezoid (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-trapezoid (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-trapezoid_zero_start (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-trapezoid_zero_start (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-previous_hold (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-previous_hold (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-wrong_unit (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- yeast-development-wrong_unit (industrial-yeast / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.

## Limits

- Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.
- Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.
- Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.
- Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.
- Batch totals compare the tool report with a publisher-logged running cumulative that is the sum of the same logged feeds: the score checks integration semantics, units, coverage and window handling, not measurement accuracy, transcription or plant truth.
