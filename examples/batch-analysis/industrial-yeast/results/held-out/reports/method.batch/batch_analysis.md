# Recorded batch phase analysis

supplied identities and revisions; not verified against installed assets

not selected; asset IDs are supplied labels only

Context: site_id=industrial baker's-yeast plant (publisher does not name it), asset_id=fed-batch fermenter, about 150 m3 geometric (publisher README), model_revision=not supplied, recipe_id=not supplied (strain 167, publisher README), recipe_revision=not supplied

A complete integral covers the supplied window under each signal's declared interpolation; it is not a verified plant total.

| Window / batch / phase | Signal | Unit | Accepted / all samples | Covered s / phase s | Coverage | Observed mean | Observed integral | Full-window integral | Integral unit |
|---|---|---|---|---|---|---|---|---|---|
| B06 / B06 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 18 | 61200 / 61200 | complete | 1335.29412 | 22700 | 22700 | kg |
| B07 / B07 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 18 | 61200 / 61200 | complete | 1338.29412 | 22751 | 22751 | kg |
| B08 / B08 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 18 | 61200 / 61200 | complete | 1335.23529 | 22699 | 22699 | kg |
| B09 / B09 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 18 | 61200 / 61200 | complete | 1329.94118 | 22609 | 22609 | kg |
| B10 / B10 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 18 | 61200 / 61200 | complete | 1335.29412 | 22700 | 22700 | kg |

Bad sample locations, source references, exact input hashes and method fingerprint are in the JSON.

## Supplied signal semantics

| Signal | Interpolation | Quality policy |
|---|---|---|
| sugar_feed_rate_kg_rs_h | next | no external quality filter selected; quality not checked |

Linear and previous-value hold require both good endpoints. Interval-ending hold (next) uses the closing sample's value for the interval it ends and needs only that sample good; the opening row supplies its time. This is not an OPC historian aggregate implementation.

- Descriptive recorded-data calculation; no diagnosis, prediction or acceptance.
- Sample extrema can miss excursions between observations.
- Observed integrals over incomplete coverage are not full-phase totals.
- Supplied phase labels, units and mappings require engineering review.
- Accepted numeric samples and complete coverage do not verify source quality or original sensor continuity.
- An interval-ending hold is right only for a log whose value covers the interval it closes (an hourly total or average); confirm the source's convention.
