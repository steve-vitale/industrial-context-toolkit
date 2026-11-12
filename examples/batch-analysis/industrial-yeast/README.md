# Recorded sugar feed on public industrial baker's-yeast batches

**A registered, scored task for the [batch tool](../../../scripts/batch_analysis.py)** on a real public source: ten
full-process production batches from an industrial baker's-yeast fed-batch fermenter (Zhao et al., figshare
[10.6084/m9.figshare.33201579](https://doi.org/10.6084/m9.figshare.33201579), CC BY 4.0), attempt A418 in
[data/attempts.json](../../../data/attempts.json).

**In one paragraph.** On ten real batches, the batch tool's `next` integral reproduces the publisher's logged running cumulative on 9 of 10 batches and 166 of 169 hours; the one mismatch (B09 hours 11-13) is an inconsistency inside the source. The key is the publisher's own sum of the same feed column, so this checks the interval convention, unit, window and coverage, and the source's internal consistency. It is not a measurement or outcome benchmark.

Under [DEPTH_GOAL.md](../../../docs/DEPTH_GOAL.md) this is an *integration-semantics check with all six mechanics in
place* (registered task, frozen scorer with controls, development and sealed held-out results, matrix cell, product
path, written failures). It does **not** give the process-data area depth: that still needs a source with an outcome
key (C-MAPSS or SECOM, deferred until a remaining-life estimate or a lot outcome screen exists).

## The question and the key

*How much sugar did each batch receive, by hour and in total, from its hourly feed log?* Operators logged, each
hour, the reducing-sugar feed rate (`sugar_feed_rate_kg_rs_h`, kg RS/h) and a running cumulative of fermentable
sugar (`total_fermentable_sugar_kg`). The publisher's README states that the cumulative's change equals the sum
of the hourly feed. The tool is given only the feed column; the cumulative is the key, kept in a separate file:

- **batch level**: one window per batch, from its first to its last logged hour; key = cumulative at the end minus
  cumulative at the start;
- **hourly level**: one window per logged hour; key = that hour's change in the cumulative. This level exists
  because whole-batch totals are nearly the same for every batch (the recipe aims at about 23,000 kg): a constant
  answer matches 3 of the 5 development totals, but none of the hours.

A match is within 0.5 kg (half the 1 kg resolution of the log). The rules, the controls and the decision rule are
frozen in [score_batch_totals.py](../../../scripts/score_batch_totals.py)'s docstring.

**What it checks, and what it does not.** The key is the publisher's own sum of the same logged feeds, so a match
shows that the tool integrates this kind of log with the right interval convention, unit, window and coverage
rule, and that the source's cumulative is consistent with its feed. It does not check the feed meter, the
transcription from the paper sheets (the originals are not public), the sugar actually delivered, or anything
about yield or the process.

## Method: an interval-ending hold

The log's value at hour *k* is the feed over the hour that ends at *k* (the cumulative adds it in full at *k*).
Before this case the tool offered a trapezoid (`linear`) and a previous-value hold (`previous`); neither reproduces
an hourly-total log, and both refuse a whole-batch total because the hour-0 feed is blank (feed had not started).
The tool now has `next`, an interval-ending hold: each closing sample's value covers the interval it ends, so only
that sample must be good and the opening row gives only its time (tests in
[test_batch_analysis.py](../../../scripts/test_batch_analysis.py), written failing first). The difference was stated
before the first run: with the blank hour-0 feed written as 0, the trapezoid covers the batch and falls short of
the logged sum by exactly half the last hour's feed (measured: 63.5 to 342.5 kg on the development batches).

## Run it offline

```sh
python scripts/fetch_corpus.py industrial-yeast          # once; checks every file against data/corpus_pins.json
python -B scripts/industrial_yeast_case.py --split development --out ../engineering-work/yeast-dev
python -B scripts/industrial_yeast_case.py --split development --check   # re-run and compare with results/
python -B scripts/industrial_yeast_case.py --split held-out --check      # the sealed split, re-run deterministically
python scripts/benchmark.py --suite benchmarks/industrial-yeast-batch-totals.json --out ../engineering-work/yeast-bench
```

The case runner verifies the two originals it reads against their pins, keeps only the split's batches (from the
dated plan in [data/corpus_depth.json](../../../data/corpus_depth.json)), writes the feed column into the tool's CSV
contract in a temporary folder (only its hash is kept), authors the V2 plans, runs `scripts/batch_analysis.py` as
its CLI for the method and four tool-run controls, builds the key from the withheld column, and scores. Each
results folder holds the plans, the key, every tool report (JSON and Markdown, unchanged tool output), `SCORE.md`,
`score.json` and `RECEIPT.json` (source pins, input hash, code hashes, commands). The originals are not
committed: fetch them by hash.

## Results

| Split | Level | Method (`next`) | Trapezoid | Trapezoid, hour 0 as 0 | Previous hold | Unit as kg/s | Perfect | Empty | Shuffled | Recipe constant |
|---|---|---|---|---|---|---|---|---|---|---|
| development B01-B05 | batch | **5 / 5** | 0 / 5 | 0 / 5 | 0 / 5 | 0 / 5 | 5 / 5 | 0 / 5 | 2 / 5 | 3 / 5 |
| development B01-B05 | hourly | **84 / 84** | 0 / 84 | 0 / 84 | 0 / 84 | 0 / 84 | 84 / 84 | 0 / 84 | 0 / 84 | 0 / 84 |
| held out B06-B10 | batch | **4 / 5** | 0 / 5 | 0 / 5 | 0 / 5 | 0 / 5 | 5 / 5 | 0 / 5 | 2 / 5 | 3 / 5 |
| held out B06-B10 | hourly | **82 / 85** | 0 / 85 | 0 / 85 | 1 / 85 | 0 / 85 | 85 / 85 | 0 / 85 | 1 / 85 | 0 / 85 |

**Kept**, by the decision rule fixed before the held-out run (batch at least 4/5, hourly at least 0.95, each above
every control except perfect), with no margin at the batch level: 4/5 is the floor. The method, the scorer and the
development result were committed first (dd040dad); the held-out batches were then run once. The only evidence of
that order is the commit order: one working session, the freeze commit at 13:37:26 and the held-out run at 13:37:37 (local
time, 2026-11-12), and dd040dad bundles the rules with the development result rather than committing the rules first. After the
held-out run, one wording-only change was made to the tool (the report's `method.assumption` text when `next` is
used, which had wrongly said both endpoints are required); every committed report was regenerated and every score
is byte-identical. The tool is deterministic, so there is no run spread; the corpus matrix (row 9) re-runs both
splits and requires the same bytes. Held-out exposure, as the plan recorded it: held-out key counts were surveyed
on 2026-11-12 (row and logged-cumulative counts over all batches and the completeness tier of every batch; key
values were read for B01 only); no method was run.

Full tables: [development](results/development/SCORE.md), [held out](results/held-out/SCORE.md). The registered
benchmark report is [industrial-yeast-batch-totals](../../../benchmarks/results/industrial-yeast-batch-totals.md);
the development-only report committed before the held-out run is kept as
[industrial-yeast-development](../../../benchmarks/results/industrial-yeast-development.md).

## Failures on this source, and limits

- **B09 (held out) does not match, and the cause is in the source.** Its logged cumulative rises 1,979, 1,907 and
  1,973 kg over hours 11-13 while the logged feeds are 1,981, 1,973 and 1,814 kg, so the batch total differs by
  91 kg (logged 22,700 kg; the feeds sum to 22,609 kg). The tool's totals equal the summed feeds there; the runner's
  source check flags the same three hours. It looks like a transcription slip in one of the two columns (the
  publisher's own README says the change equals the summed feed, and its QC record gives no residual error rate),
  but the paper originals are not public, so which column is wrong cannot be settled here. Not fixed: no tool
  change can correct a source, and nothing was tuned after the held-out run. A reviewer using totals from this
  source should read the source check first.
- **The tool could not read this log before the change.** Both existing interpolation rules refused every
  whole-batch total (blank hour-0 feed) and put the hourly values in the wrong interval (1 of 338 hourly windows matched across both rules and splits, by coincidence); this is fixed in the tool (`next`), not
  in an adapter.
- **Whole-batch totals barely separate a right answer from a recipe constant** (3 of 5 batches in each split log
  exactly 22,700 kg). The hourly level carries the evidence; never quote the batch level alone.
- **The key is not independent of the measurement.** It is the publisher's sum of the same logged feed values.
- **Choosing `next` is a reading of the source**, from its README and the logged cumulative; on a log of
  instantaneous rates it would be wrong. The tool cannot tell which convention a source uses.
- **Not used from the plan:** the published full-process statistics in `summary_stats.json` pool all ten batches
  (development and held-out) as row-level statistics, so they cannot be split, and row means are not the tool's
  time-weighted window means. Their values were not read (only the file's key names, to confirm the pooling) and they are not a key here.
- Ten batches from one plant and one strain; no claim beyond this publisher. The 49 sparse batches are not scored.
