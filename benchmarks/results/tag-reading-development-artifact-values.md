# Tag reading results: dexpi-tag-reading-exposed-development

Retrospective exposed historical/development registration using CURRENT frozen cache keys. Five sheets from one DEXPI publisher; saved 2026-10-13 model dates; no new trial, blindness or independent source families.

Task: `tag-reading` / `tag-text-v1`. Geometry and tag-list modes have separate denominators and cohorts.

## Geometry-keyed tag rates

Strict recall includes unfound labelled symbols; found accuracy is conditional on a matched symbol. Lenient rates use the companion text normalization.

### claude-opus-5-5[1m]

- **Provider / version:** Anthropic / provider build not recorded beyond the saved model identifier
- **Method / client:** historical 2x2 tiled model extraction + deterministic trace replacement / Claude Code CLI
- **Family / split / evidence:** dexpi-trainingtestcases / development / exposed historical model answers; CURRENT frozen derived cache keys, original producing key/converter identity unknown
- **Cohort:** c29f507b690ef52ba59746011168ec5112d9c35d32075c13a4c4f1847059e295; **group:** 9839b94b54ce04c580567531c01fec37c52802dc66c2c974333f33bf4b57ac05
- **Selected cases / repeats:** 3 / 5
- **Configuration:** {"overlap": 0.15, "reasoning_effort": "not recorded", "temperature": "not recorded", "tiles": "2x2", "trace": "replace"}

| Rate | Mean | Range | SD | Defined / total |
|---|---|---|---|---|
| strict_end_to_end_recall | 0.8485 | 0.8485–0.8485 | 0.0000 | 5 / 5 |
| strict_accuracy_on_found | 0.9032 | 0.9032–0.9032 | 0.0000 | 5 / 5 |
| lenient_end_to_end_recall | 0.8485 | 0.8485–0.8485 | 0.0000 | 5 / 5 |
| lenient_accuracy_on_found | 0.9032 | 0.9032–0.9032 | 0.0000 | 5 / 5 |

### gpt-6.1-sol

- **Provider / version:** OpenAI / provider build not recorded beyond the saved model identifier
- **Method / client:** historical 2x2 tiled model extraction + deterministic trace replacement / Codex CLI
- **Family / split / evidence:** dexpi-trainingtestcases / development / exposed historical model answers; CURRENT frozen derived cache keys, original producing key/converter identity unknown
- **Cohort:** c29f507b690ef52ba59746011168ec5112d9c35d32075c13a4c4f1847059e295; **group:** c756f21bd3c84717924ea30dbdbe555bbb5d7ee5937732a26ffaf81fd87ec48e
- **Selected cases / repeats:** 3 / 5
- **Configuration:** {"overlap": 0.15, "reasoning_effort": "not recorded", "temperature": "not recorded", "tiles": "2x2", "trace": "replace"}

| Rate | Mean | Range | SD | Defined / total |
|---|---|---|---|---|
| strict_end_to_end_recall | 0.8788 | 0.8788–0.8788 | 0.0000 | 5 / 5 |
| strict_accuracy_on_found | 0.8788 | 0.8788–0.8788 | 0.0000 | 5 / 5 |
| lenient_end_to_end_recall | 0.8788 | 0.8788–0.8788 | 0.0000 | 5 / 5 |
| lenient_accuracy_on_found | 0.8788 | 0.8788–0.8788 | 0.0000 | 5 / 5 |

## Partial-list identifier rates

Substring recall measures coverage of partial lists, without assigning identifiers to the correct item. Class agreement is a share of found identifiers, not precision.

### gpt-6.1-sol

- **Provider / version:** OpenAI / provider build not recorded beyond the saved model identifier
- **Method / client:** historical 2x2 tiled model extraction + deterministic trace replacement / Codex CLI
- **Family / split / evidence:** dexpi-trainingtestcases / development / exposed historical model answers; CURRENT frozen derived cache keys, original producing key/converter identity unknown
- **Cohort:** 170682030ada42cd0c34dd5ef0876dbc31796d8d1a3c82eec52d9ac6d8f42ad6; **group:** c0faadca272adcb40b06105356b555b3eb6aacaa83c630e8294db8a9deef2bdc
- **Selected cases / repeats:** 2 / 5
- **Configuration:** {"overlap": 0.15, "reasoning_effort": "not recorded", "temperature": "not recorded", "tiles": "2x2", "trace": "replace"}

| Rate | Mean | Range | SD | Defined / total |
|---|---|---|---|---|
| identifier_recall | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| found_identifier_class_agreement | 0.9862 | 0.9793–0.9931 | 0.0069 | 5 / 5 |
| identifier_recall / list equipment | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| found_identifier_class_agreement / list equipment | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| identifier_recall / list instrument | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| found_identifier_class_agreement / list instrument | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| identifier_recall / list valve | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| found_identifier_class_agreement / list valve | 0.9747 | 0.9620–0.9873 | 0.0127 | 5 / 5 |

### claude-opus-5-5[1m]

- **Provider / version:** Anthropic / provider build not recorded beyond the saved model identifier
- **Method / client:** historical 2x2 tiled model extraction + deterministic trace replacement / Claude Code CLI
- **Family / split / evidence:** dexpi-trainingtestcases / development / exposed historical model answers; CURRENT frozen derived cache keys, original producing key/converter identity unknown
- **Cohort:** 170682030ada42cd0c34dd5ef0876dbc31796d8d1a3c82eec52d9ac6d8f42ad6; **group:** c2ffc57dc6dfe4ac92b199f9bf22e6d4e41a6ae32093b0e0b982f8dfddac5d7e
- **Selected cases / repeats:** 2 / 5
- **Configuration:** {"overlap": 0.15, "reasoning_effort": "not recorded", "temperature": "not recorded", "tiles": "2x2", "trace": "replace"}

| Rate | Mean | Range | SD | Defined / total |
|---|---|---|---|---|
| identifier_recall | 0.9945 | 0.9793–1.0000 | 0.0090 | 5 / 5 |
| found_identifier_class_agreement | 0.9861 | 0.9859–0.9862 | 0.0001 | 5 / 5 |
| identifier_recall / list equipment | 0.9900 | 0.9500–1.0000 | 0.0224 | 5 / 5 |
| found_identifier_class_agreement / list equipment | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| identifier_recall / list instrument | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| found_identifier_class_agreement / list instrument | 1.0000 | 1.0000–1.0000 | 0.0000 | 5 / 5 |
| identifier_recall / list valve | 0.9924 | 0.9747–1.0000 | 0.0113 | 5 / 5 |
| found_identifier_class_agreement / list valve | 0.9745 | 0.9740–0.9747 | 0.0003 | 5 / 5 |

<details>
<summary>Per-run counts and coverage (20 run/cohort records)</summary>

## Per-run primitive counts and coverage

- tag-reading-claude-r5-dx-rep1-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}, "lenient": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-claude-r5-dx-rep1-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 143}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 77}}, "predicted_tags": 180}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-claude-r5-dx-rep2-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 28, "wrong": 2, "no_tag": 1, "missed": 2, "found": 31, "with_truth": 33}, "lenient": {"correct": 28, "wrong": 2, "no_tag": 1, "missed": 2, "found": 31, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-claude-r5-dx-rep2-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 143}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 77}}, "predicted_tags": 184}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-claude-r5-dx-rep3-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}, "lenient": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-claude-r5-dx-rep3-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 144, "found_with_list_class": 142}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 78, "found_with_list_class": 76}}, "predicted_tags": 183}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-claude-r5-dx-rep4-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 28, "wrong": 2, "no_tag": 1, "missed": 2, "found": 31, "with_truth": 33}, "lenient": {"correct": 28, "wrong": 2, "no_tag": 1, "missed": 2, "found": 31, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-claude-r5-dx-rep4-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 143}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 77}}, "predicted_tags": 183}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-claude-r5-dx-rep5-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}, "lenient": {"correct": 28, "wrong": 0, "no_tag": 3, "missed": 2, "found": 31, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-claude-r5-dx-rep5-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 142, "found_with_list_class": 140}, "by_list": {"equipment": {"listed": 20, "found": 19, "found_with_list_class": 19}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 77, "found_with_list_class": 75}}, "predicted_tags": 176}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-codex-r5-dx-rep1-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}, "lenient": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-codex-r5-dx-rep1-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 144}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 78}}, "predicted_tags": 177}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-codex-r5-dx-rep2-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}, "lenient": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-codex-r5-dx-rep2-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 142}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 76}}, "predicted_tags": 178}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-codex-r5-dx-rep3-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}, "lenient": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-codex-r5-dx-rep3-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 143}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 77}}, "predicted_tags": 174}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-codex-r5-dx-rep4-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}, "lenient": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-codex-r5-dx-rep4-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 142}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 76}}, "predicted_tags": 171}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.
- tag-reading-codex-r5-dx-rep5-trace / geometry / dexpi-trainingtestcases: 3 selected cases; counts {"strict": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}, "lenient": {"correct": 29, "wrong": 3, "no_tag": 1, "missed": 0, "found": 33, "with_truth": 33}}; suite-wide unattempted: none.
  - dexpi-c01: ok.
  - dexpi-c02: ok.
  - dexpi-c03: ok.
- tag-reading-codex-r5-dx-rep5-trace / taglist / dexpi-trainingtestcases: 2 selected cases; counts {"all": {"listed": 145, "found": 145, "found_with_list_class": 144}, "by_list": {"equipment": {"listed": 20, "found": 20, "found_with_list_class": 20}, "instrument": {"listed": 46, "found": 46, "found_with_list_class": 46}, "valve": {"listed": 79, "found": 79, "found_with_list_class": 78}}, "predicted_tags": 173}; suite-wide unattempted: none.
  - dexpi-c08a: ok.
  - dexpi-c08b: ok.

</details>

## Limits

- Geometry and partial-list modes have distinct denominators/cohorts and are never pooled.
- Geometry reports strict/lenient tag recall and conditional found accuracy, not tag precision or F1.
- Tag-list substring recall is partial coverage, not item assignment; class agreement is a derived found-identifier share.
- Only comparable cohorts may be compared. Source/key/model metadata is declared, not authenticated engineering truth.
- Missing/failed/invalid attempted answers retain full admitted truth denominators; unattempted cases remain visible.
- Replicates summarize defined pooled rates with explicit defined/total counts; no significance test or winner.
- Exposed historical/development registration and generated controls do not establish blindness or new source families.
