# Task results: nestor-excavators-system-grouping

Task: `maintenance-system-grouping`. Depth increment 2, attempt A420. Split decided 2026-11-12 before any result: development assets A-C, held out D-E. Method, scorer and pass margin frozen before the one held-out run. What it shows: the tool derive option applies a user-declared vocabulary faithfully and groups by it, and a 10-rule vocabulary written from A-C (including their publisher codes) carries over to D-E under one publisher coding scheme. The vocabulary is a per-dataset profile artifact, not part of the product. It does not show what a user without a key would write (see the post-hoc key-free control run) and does not measure engineering correctness: the key was made by keyword rules over the same text. Originals are not redistributed: the suite opts in to optional_cache, so in a clean clone it is UNVERIFIED and its committed report stands as recorded.

Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.

## Per-record system classes beside the wrong controls

Per-record precision / recall / F1 for the scored answer and every control on the same keyed records. `reference` is the key itself (must be 1.0); `raw-asset-baseline` is the predeclared raw-asset-ID grouping, which has no system; `majority-system` gives every record one fixed class; `shuffled-within-asset` permutes the answer's own classes; `misaligned-key` scores the answer against another record's key. A run with a role (the post-hoc key-free control, added at review after the sealed run) shows its answer row only. Records the key gives no system are outside the frozen precision and counted in the last column; the two "no-key as FP" columns count every such record given a class as a false positive.

| Case / split | Run | Answer or control | Orders P | Orders R | Orders F1 | Orders P, no-key as FP | Orders F1, no-key as FP | Membership F1 | Groups F1 | No-system records given a class |
|---|---|---|---|---|---|---|---|---|---|---|
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | answer | 0.9749 | 0.9511 | 0.9629 | 0.8765 | 0.9123 | 0.8620 | 0.9796 | 130 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | reference | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | raw-asset-baseline | n/a | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | majority-system | 0.4123 | 0.4123 | 0.4123 | 0.2423 | 0.3052 | 0.2922 | 0.2143 | 832 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | shuffled-within-asset | 0.2919 | 0.1922 | 0.2318 | 0.1772 | 0.1844 | 0.1744 | 0.9796 | 506 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | misaligned-key | 0.2179 | 0.1088 | 0.1451 | 0.1002 | 0.1043 | 0.0987 | 0.9796 | 695 |
| nestor-excavators-a-c / development | a420-maintenance-history-vocabulary | margin over the best wrong control (orders F1) |  |  | 0.5506 |  |  |  |  |  |
| nestor-excavators-a-c / development | a420-posthoc-classname-control | answer (post-hoc key-free control) | 0.8700 | 0.3668 | 0.5160 | 0.7982 | 0.5026 | 0.4642 | 0.8372 | 45 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | answer | 0.9701 | 0.9164 | 0.9425 | 0.8591 | 0.8868 | 0.8350 | 0.9000 | 229 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | reference | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | raw-asset-baseline | n/a | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | majority-system | 0.3937 | 0.3937 | 0.3937 | 0.2247 | 0.2861 | 0.2733 | 0.1667 | 1412 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | shuffled-within-asset | 0.2611 | 0.1593 | 0.1979 | 0.1494 | 0.1542 | 0.1451 | 0.9000 | 857 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | misaligned-key | 0.2231 | 0.1039 | 0.1418 | 0.0974 | 0.1005 | 0.0947 | 0.9000 | 1128 |
| nestor-excavators-d-e / held-out | a420-maintenance-history-vocabulary | margin over the best wrong control (orders F1) |  |  | 0.5488 |  |  |  |  |  |
| nestor-excavators-d-e / held-out | a420-posthoc-classname-control | answer (post-hoc key-free control) | 0.8853 | 0.3495 | 0.5011 | 0.8039 | 0.4872 | 0.4475 | 0.7778 | 75 |

The group F1 does not separate the answer from the shuffled or misaligned controls: most systems recur on every asset under any labelling with the same class counts. Read the per-record and membership columns. The model/method summary (one deterministic run per cohort, no replicates) is in the JSON only, so that no table here shows the answer without its controls.


## Coverage and failures

- a420-maintenance-history-vocabulary (nestor-excavators / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- a420-maintenance-history-vocabulary (nestor-excavators / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- a420-posthoc-classname-control (nestor-excavators / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- a420-posthoc-classname-control (nestor-excavators / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.

## Limits

- Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.
- Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.
- Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.
- Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.
- System grouping scores per-record classes against a publisher's own system coding, itself made by keyword rules over the same short text: agreement with those rules, not engineering truth, failure diagnosis or repair effectiveness. Records the key gives no system are outside the precision denominator and counted separately.
