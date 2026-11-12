# Task results: nestor-excavators-system-grouping

Task: `maintenance-system-grouping`. Depth increment 2, attempt A420. Split decided 2026-11-12 before any result: development assets A-C, held out D-E. Method, scorer and pass margin frozen before the one held-out run. Key computed by the publisher from the same text (keyword rules), so a high score is agreement with those rules. Originals are not redistributed: in a clean clone this suite is UNVERIFIED and its committed report stands as recorded.

Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.

## Per-record system classes beside the wrong controls

Per-record precision / recall / F1 for the scored answer and every control on the same keyed records. `reference` is the key itself (must be 1.0); `raw-asset-baseline` is the predeclared raw-asset-ID grouping, which has no system; `majority-system` gives every record one fixed class; `shuffled-within-asset` permutes the answer's own classes; `misaligned-key` scores the answer against another record's key. Records the key gives no system are outside precision and counted in the last column.

| Run | Case / split | Answer or control | Orders P | Orders R | Orders F1 | Membership F1 | Groups F1 | No-system records given a class |
|---|---|---|---|---|---|---|---|---|
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | answer | 0.9749 | 0.9511 | 0.9629 | 0.8620 | 0.9796 | 130 |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | reference | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | raw-asset-baseline | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | majority-system | 0.4123 | 0.4123 | 0.4123 | 0.2922 | 0.2143 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | shuffled-within-asset | 0.2919 | 0.1922 | 0.2318 | 0.1744 | 0.9796 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | misaligned-key | 0.2179 | 0.1088 | 0.1451 | 0.0987 | 0.9796 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-a-c / development | margin over the best wrong control (orders F1) |  |  | 0.5506 |  |  |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | answer | 0.9701 | 0.9164 | 0.9425 | 0.8350 | 0.9000 | 229 |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | reference | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | raw-asset-baseline | n/a | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | majority-system | 0.3937 | 0.3937 | 0.3937 | 0.2733 | 0.1667 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | shuffled-within-asset | 0.2611 | 0.1593 | 0.1979 | 0.1451 | 0.9000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | misaligned-key | 0.2231 | 0.1039 | 0.1418 | 0.0947 | 0.9000 |  |
| a420-maintenance-history-vocabulary | nestor-excavators-d-e / held-out | margin over the best wrong control (orders F1) |  |  | 0.5488 |  |  |  |

The group F1 does not separate the answer from the shuffled or misaligned controls: most systems recur on every asset under any labelling with the same class counts. Read the per-record and membership columns. The model/method summary (one deterministic run per cohort, no replicates) is in the JSON only, so that no table here shows the answer without its controls.


## Coverage and failures

- a420-maintenance-history-vocabulary (nestor-excavators / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.
- a420-maintenance-history-vocabulary (nestor-excavators / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: none; failed attempted answers: none.

## Limits

- Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.
- Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.
- Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.
- Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.
- System grouping scores per-record classes against a publisher's own system coding, itself made by keyword rules over the same short text: agreement with those rules, not engineering truth, failure diagnosis or repair effectiveness. Records the key gives no system are outside the precision denominator and counted separately.
