# Task results: demo-suite

Task: `drawing-extraction`. Demonstration suite: fictional, scripted author and reviewer. Not evidence about any reader or any person's labelling.

Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.

| Model / version | Method / interface | Family / split / evidence | Cohort | Cases | Replicates | Metric | Mean F1 | Min–max | SD |
|---|---|---|---|---|---|---|---|---|---|
| synthetic-control / 1 | empty answer / authored fixture | pid2graph-open100 / validation / contributed demonstration case, model-drafted key, scripted sampled review, fictional roles; provenance in examples/contribute-a-pid/open100-0-demo/case.json | 5c3ef99fe754 | 1 | 1 | symbols_rough | 0.0000 | 0.0000–0.0000 | unavailable |
| synthetic-control / 1 | empty answer / authored fixture | pid2graph-open100 / validation / contributed demonstration case, model-drafted key, scripted sampled review, fictional roles; provenance in examples/contribute-a-pid/open100-0-demo/case.json | 5c3ef99fe754 | 1 | 1 | symbols_strict | 0.0000 | 0.0000–0.0000 | unavailable |
| synthetic-control / 1 | empty answer / authored fixture | pid2graph-open100 / validation / contributed demonstration case, model-drafted key, scripted sampled review, fictional roles; provenance in examples/contribute-a-pid/open100-0-demo/case.json | 5c3ef99fe754 | 1 | 1 | networks | 0.0000 | 0.0000–0.0000 | unavailable |

## Coverage and failures

- demo-suite-empty-control (pid2graph-open100 / validation): 1 cases in this family/cohort; suite total 1; suite-wide unattempted: none; failed attempted answers: none.

## Limits

- Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.
- Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.
- Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.
- Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.
- Description facts grade literal selected fields only: no prose names, source validity, dimensions, limits, layout quality or plant truth.
