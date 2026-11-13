# Recorded batch phases beside a digital twin

**Tool:** `scripts/batch_analysis.py` accepts your recorded CSV and explicitly authored phase plan. It computes
duration, observed extrema, time-weighted means and supported rate integrals. Optional `--graph` binds supplied
IDs to a selected graph snapshot. **Tutorial:** this folder's small authored fermenter and three recorded batches
are fictional teaching fixtures, not an operating plant or fermentation model.

Use it to answer a bounded question such as: *How much feed was recorded during this phase, and is the record
complete enough to compare with another batch?* Start with [process analytics](../../docs/PROCESS_ANALYTICS.md)
to choose the job and identify the evidence it needs. Kinetics is unnecessary for this calculation; yield
prediction or a new feed policy needs more evidence and a suitable model.

| Choose an episode | Role and useful outcome |
|---|---|
| First example below | Fictional V1 calculation: learn phase windows, units and missing-duration behavior. |
| [Quality and interpolation](semantics/README.md) | Fictional V2 controls: declare signal semantics and keep both assumption-sensitive results. |
| [Measured laboratory record](public-distillation/README.md) | Fixed-source calculation and independently checked key, with the source's processing and anomaly qualifications. |
| [Industrial production batches](industrial-yeast/README.md) | A registered, scored task on 10 public baker's-yeast batches: the tool's feed totals against the publisher's logged cumulative, with a sealed held-out split and wrong-answer controls. |
| [Retain the finding](context-handoff/README.md) | Existing context tools and pure snapshot reader: keep missing event/recipe/lab/model evidence, then reopen an answer when its report changes. |
| [Join batch, recipe, event, lab and outcome records](record-joins/README.md) | Reusable local manifest/CSV route: compare declared basis and availability, withhold incomplete metrics and check upstream calculations. Fictional source/revision tutorial; no causal or plant-acceptance claim. |
| [Keep an investigation reconstructable](investigation/README.md) | Follow a question through evidence, a contradicted explanation and source revisions. Use the [own-input guide](investigation/OWN-INPUT.md) to assemble a proposed colleague handoff; an engineer or manager still reviews the scientific meaning and owns the decision. |

## Try it offline

Python 3.10+, standard library only, no accounts, assistant, network connection or listener. From the repository
root, choose a new private output directory:

```sh
python -B scripts/batch_analysis.py --csv examples/batch-analysis/observations.csv --plan examples/batch-analysis/plan.json --graph examples/batch-analysis/graph.json --out ../engineering-work/batch-phases
python -B scripts/test_batch_analysis.py
```

Read `batch_analysis.md`, then its JSON companion for input/method hashes, source references, node statuses,
coverage and bad-sample record locations. Neither command fetches process data. The tests execute the CLI in
temporary folders and compare analytical oracles and the [committed results](expected/batch_analysis.md).

The graph was produced with the existing `graph_export.py` from [process_model.json](process_model.json).
To reproduce it without changing the example, use:

```sh
python -B scripts/graph_export.py examples/batch-analysis/process_model.json --out ../engineering-work/fermenter.graph.json
```

All graph records remain unverified. Source tracing here demonstrates a connection contract; it is not a
validated sensor mapping or dynamic twin. Graph membership does not verify signal ownership or process physics.

## What the example establishes

Each phase is one hour. At 3,600 seconds, batch A's feed rate is 2 kg/h; at 5,400 and 7,200 seconds it is 4 kg/h.
Linear interpolation gives **1.5 + 2 = 3.5 kg** in A's feed phase. B stays at 2 kg/h: **2 kg**. C has a bad midpoint:
neither adjacent interval is admitted, so its feed total is **unknown**, not zero or 2 kg. Other C signals remain
usable; coverage is evaluated separately per signal.

A's growth window includes a ramp from 0 to 2 kg/h between 1,800 and 3,600 seconds, giving **0.5 kg**. The shared
boundary belongs to both adjacent calculations but has no duration. If the actual process stepped rather than
ramped, these sparse observations do not establish that fact: use suitable records and a justified integration
method. Every window records 1,000 W for one hour: **1 kWh**. A's observed feed-phase DO minimum is **20% air
saturation**; that is neither a concentration nor proof of oxygen limitation.

These arithmetic differences do not establish a better recipe, lower yield or a reason for intervention. The
[investigation brief](first-question.md) carries the next evidence requests, including the conditional need for
kinetics. There is no model fit, anomaly threshold, causal test, control recommendation or site performance claim.

## Use your own records

1. Follow your approved [data path](../../docs/INTERNAL_CONNECTIVITY.md). Preserve the export and record any
   conversion, including timestamp origin, units, quality encoding and source revision. Do not put company
   process data in this public repository. The tool accepts one explicitly selected local CSV, whether obtained
   by export or an independently approved data integration; it does not provide the live connector.
2. Prepare the CSV contract below. Review the signal meanings, including engineering units versus raw counts,
   mass versus volumetric flow and percent-saturation versus concentration. V1 requires prior quality filtering;
   export bad-quality readings as blank or `Bad`. V2 can apply a supplied exact-token policy to a separate
   quality column. Neither profile decodes vendor bitfields or detects numeric sentinel values automatically.
3. Author the plan from permitted batch/event records. Supply site, asset, model revision, recipe/revision and
   actual phase windows; use separate plans for different sites, assets, recipes or scales. Set `max_gap_s` from
   what the investigation can tolerate. It is not chosen by the tool or proved adequate by this example.
4. Optionally export your reviewed supported model using `graph_export.py`. Select the graph with `--graph` and
   use exact equipment/instrument node IDs in the plan. Unknown, wrong-kind or rejected referenced records refuse.
   Unverified records remain explicitly unverified in the result. With no graph, IDs remain supplied labels only.
5. Run into a new folder. Review source timing, boundary observations, bad samples and every signal's coverage
   before using a total. Retain the plan, input originals, graph if used, tool revision, both reports and reviewer
   with the investigation. Cite the report through an existing [context answer](../../docs/CONTEXT_REGISTER.md)
   if useful; the [worked handoff](context-handoff/README.md) shows this existing manual route. There is no
   automatic report-to-context/MCP import or analysis execution through MCP.

Before reusing a saved result, run the [explicit basis check](basis-check/README.md) with the CSV, plan and
graph you intend to use. It compares the report's input/code pins and reproduces the full JSON when they match.
An unchanged report alone cannot show whether its upstream files changed. A changed basis calls for review,
a new calculation where appropriate, and a separate context refresh; the checker writes no files.

## Input contract

CSV is UTF-8, comma-separated, decimal point `.`. V1 contains exactly `batch_id`, `time_s` and the planned signal
columns, in any order; V2 additionally requires exactly its declared quality columns. Signal names are unique.
`time_s` is finite, nonnegative elapsed seconds from the declared
batch origin and must strictly increase within each batch. Batches may interleave and restart their own clocks;
the plan and CSV must contain the same batch IDs. Do not concatenate sites with reused batch IDs.

Bad/blank/non-numeric/non-finite signal cells are unavailable observations, never zero. V1 assumes prior quality
filtering. V2 either applies the supplied exact-token policy or explicitly declares `quality: null` for no
external quality filter; numeric admission alone then says nothing about source quality or prior filtering.
No resampling, automatic timestamp conversion or lab/event join occurs. Rows outside
selected windows are not analyzed. A planned window with no observations reports unknown values.

[plan.json](plan.json) is the exact `batch-analysis-1` contract: all its fields are required and additional fields
refuse. [V2](semantics/README.md) requires explicit interpolation and quality choices per signal. Numeric
configuration cannot be boolean or non-finite. Windows have unique IDs and `0 <= start_s < end_s`;
windows within one batch cannot overlap but may share endpoints. Repeated phase names require separate window
IDs. Signal definitions contain a unit, exact asset ID and supplied source reference. Context revisions and
source references are user assertions; their referenced documents are not fetched or authenticated.

Supported rate units: `kg/h`, `g/h`, `kg/s`, `L/h`, `L/s`, `kW`, `W`; outputs are respectively kg, g, kg, L, L, kWh,
kWh. Supported summary-only units: `degC`, `pH`, `%`, `rpm`, `bar`, `g/L`, `kg/L`, `kg`, `L`. There is no inferred
density, percent conversion, counter differencing or arbitrary unit algebra. Rates are signed: confirm the source
direction convention. A mean pH is only a descriptive numeric summary, not an acid/base material balance.

## Calculation and refusal rules

Select observations on the **closed** phase interval. Admit an interval only between two adjacent good samples
inside it, with elapsed time at most `max_gap_s`. V1 and V2's `linear` choice use the trapezoid area
`(left/2 + right/2) * elapsed_seconds`; V2's `previous` choice uses `left * elapsed_seconds`.
V2's `next` choice is an interval-ending hold for logs whose value covers the interval it closes (an hourly total
or an hourly average written at the end of the hour): it uses `right * elapsed_seconds`, and because the opening
value is not used, only the closing sample must be good; the opening row still supplies the interval's start time.
Choose it only when the source says so: on the [industrial-yeast batches](industrial-yeast/README.md) the
publisher's running cumulative is the sum of each hour's logged feed, which only `next` reproduces.
There is no interpolation across bad observations, long gaps or missing phase edges. Partial intervals spanning
a phase edge are not clipped or interpolated to the boundary.

`covered_s` sums admitted durations; `time_weighted_mean_observed` divides their areas by that duration.
`observed_integral` converts their area to the supported total unit. Both are null if there are no admitted
intervals. `full_window_integral` is populated only when actual observations include both exact boundaries and
every intervening interval was admitted. Zero covered time is not a zero total. Sample min/max use good
observations in the window and may miss excursions between them. They are not safety limits.

Source bytes are captured once and fingerprinted. Reports refuse existing destinations or aliases of any selected
input, including hardlinks. Output checks assume a stable local filesystem; two reports are not an atomic
publication and a write failure can leave a partial pair. Use a new version directory and inspect successful
completion. The tool loads the CSV into memory and scans batch rows per window, so keep exports bounded; this
is not an online or global-scale processing service.

The [acceptance protocol](ACCEPTANCE.md) defines the analytical and planted-failure cases. These exposed controls
test software, not field accuracy. New real-data contributions need cleared source and event/quality provenance,
a separately reviewed calculation key, retained failures and matched baseline comparisons under
[CONTRIBUTING.md](../../CONTRIBUTING.md). This is not a new task/model benchmark or workflow-matrix result.
