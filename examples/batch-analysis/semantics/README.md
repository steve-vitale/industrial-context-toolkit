# State the signal semantics before calculating a total

**Tutorial using the same batch tool.** Supply quality rules and interpolation explicitly with
`batch-analysis-2`. The original `batch-analysis-1` profile remains available for prefiltered observations
and linear interpolation. No extra package, model, server or plant connection is needed.

Use this when an export includes a separate quality column or the source meaning calls for holding the previous
value rather than drawing a straight line between readings. Establish that meaning from the historian/export
configuration and process records. This example does not decide it for your signals.

## Try both assumptions on one source

Python 3.10+, standard library only, from the repository root; choose new output directories:

```sh
python -B scripts/batch_analysis.py --csv examples/batch-analysis/semantics/observations.csv --plan examples/batch-analysis/semantics/previous.plan.json --graph examples/batch-analysis/graph.json --out ../engineering-work/previous-phase
python -B scripts/batch_analysis.py --csv examples/batch-analysis/semantics/observations.csv --plan examples/batch-analysis/semantics/linear.plan.json --graph examples/batch-analysis/graph.json --out ../engineering-work/linear-phase
```

Read the [previous-value result](expected/previous/batch_analysis.md) and [linear result](expected/linear/batch_analysis.md).
Both are actual tool outputs on the same fictional CSV. Their JSON companions retain input/method/graph hashes,
exact rejected quality tokens and physical CSV record-ending lines. The plans differ only in the feed signal's
interpolation choice; power uses linear interpolation in both.

| Batch | Previous-value feed total | Linear feed total | Why |
|---|---|---|---|
| A | 4 kg | 5 kg | At 0, 1800, 3600 s the rate is 2, 6, 6 kg/h. Rectangles give 1+3; trapezoids give 2+3. |
| B | Unknown | Unknown | Numeric midpoint 99 has token `FAULT`; only `GOOD` is allowed. Neither neighboring interval is admitted. |

Every window still integrates the independently usable power signal to approximately 1 kWh. Keep both feed
outcomes as sensitivity evidence until the applicable source semantics are established; neither total is
automatically correct. This is calculation evidence, not a comparison of two recipes.

## The explicit V2 choices

Use the existing top-level plan fields and `schema: "batch-analysis-2"`. Each signal has exactly these fields:

```json
{
  "unit": "kg/h",
  "asset_id": "FT-101",
  "source_ref": "your qualified signal and export configuration revision",
  "interpolation": "previous",
  "quality": {"column": "FT-101_status", "good_values": ["GOOD"]}
}
```

`interpolation` is `linear`, `previous` or `next` (an interval-ending hold: the closing sample's value covers the interval it ends; see the [main guide](../README.md#calculation-and-refusal-rules)); there is no automatic selection. `quality` is the declared exact-token
policy, or explicit `null` when no external quality filter is selected. Null is reported as **quality not checked**;
it makes no assertion of prior filtering or verified good quality. V2 refuses omitted choices. V1 continues
to refuse these additional fields rather than silently accepting a different contract.

The CSV contains identity/time, planned signals and exactly the declared quality columns. Multiple signals may
explicitly share one quality column. Accepted tokens are nonempty unique strings compared literally: `0`, `00`
and `0.0` differ, as do `GOOD`, `good` and `GOOD `. The tool does not decode OPC/vendor status bitfields, trim
tokens, infer meaning from numeric codes or authenticate quality. Include only codes the responsible data owner
has qualified. Blank, unknown and all other unlisted tokens exclude that sample.

A good token cannot rescue blank, nonnumeric or non-finite values. Rejected samples retain raw value, quality
column/token and every applicable reason in JSON. A rejected value remains a barrier between adjacent
observations; it is never dropped to create a new spanning interval.

The legacy JSON field `good_samples` counts numerically valid samples admitted by the selected policy; V2's
readable table calls them **Accepted** samples. With null quality, it is a
numeric-validity count only. Complete coverage describes the supplied series under that policy; a publisher or
historian may already have filled gaps before export. Keep upstream processing and unavailable quality evidence
explicit in the source reference and investigation.

## Bound the calculation

Linear interpolation uses `(left/2 + right/2) * duration`. Previous-value hold uses `left * duration` from the
left sample to the right one. Both choices conservatively require **both endpoints good**. Neither holds past
a bad endpoint, extrapolates outside observations, bridges an excessive gap or synthesizes phase-boundary
observations. This is a bounded local calculation, not an OPC historian aggregate implementation.

The [OPC Foundation's aggregate definitions](https://reference.opcfoundation.org/specs/OPC-10000-13/3)
distinguish interpolation and quality handling; a site's configured aggregate may follow different rules.
[SciPy's interpolation guide](https://docs.scipy.org/doc/scipy/tutorial/interpolate/1D.html) describes
previous-value interpolation. No SciPy dependency is introduced here.

The [acceptance protocol](ACCEPTANCE.md) predates the extension. The
[retained A306 JSON](../history/a306/batch_analysis.json) and [Markdown](../history/a306/batch_analysis.md)
preserve the initial V1 report. Regression checks compare all its fields and values, allowing only the tool
fingerprint to change; its readable report stays byte-identical. This does not establish new-site accuracy.
Use your permitted records through the [own-input steps](../README.md#use-your-own-records) and keep the
source/export meaning with the finding.
