# Recorded batch phase analysis

supplied identities and revisions; not verified against installed assets

not selected; asset IDs are supplied labels only

Context: site_id=industrial baker's-yeast plant (publisher does not name it), asset_id=fed-batch fermenter, about 150 m3 geometric (publisher README), model_revision=not supplied, recipe_id=not supplied (strain 167, publisher README), recipe_revision=not supplied

A complete integral covers the supplied window under each signal's declared interpolation; it is not a verified plant total.

| Window / batch / phase | Signal | Unit | Accepted / all samples | Covered s / phase s | Coverage | Observed mean | Observed integral | Full-window integral | Integral unit |
|---|---|---|---|---|---|---|---|---|---|
| B01 / B01 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1319.26471 | 22427.5 | 22427.5 | kg |
| B02 / B02 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 17 / 17 | 57600 / 57600 | complete | 1397.34375 | 22357.5 | 22357.5 | kg |
| B03 / B03 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1319.61765 | 22433.5 | 22433.5 | kg |
| B04 / B04 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1325.67647 | 22536.5 | 22536.5 | kg |
| B05 / B05 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1331.91176 | 22642.5 | 22642.5 | kg |

Bad sample locations, source references, exact input hashes and method fingerprint are in the JSON.

## Supplied signal semantics

| Signal | Interpolation | Quality policy |
|---|---|---|
| sugar_feed_rate_kg_rs_h | linear | no external quality filter selected; quality not checked |

Both good endpoints are required even for previous-value hold; this is not an OPC historian aggregate implementation.

- Descriptive recorded-data calculation; no diagnosis, prediction or acceptance.
- Sample extrema can miss excursions between observations.
- Observed integrals over incomplete coverage are not full-phase totals.
- Supplied phase labels, units and mappings require engineering review.
- Accepted numeric samples and complete coverage do not verify source quality or original sensor continuity.
