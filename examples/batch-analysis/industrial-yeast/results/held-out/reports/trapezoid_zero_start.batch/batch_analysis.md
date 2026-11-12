# Recorded batch phase analysis

supplied identities and revisions; not verified against installed assets

not selected; asset IDs are supplied labels only

Context: site_id=industrial baker's-yeast plant (publisher does not name it), asset_id=fed-batch fermenter, about 150 m3 geometric (publisher README), model_revision=not supplied, recipe_id=not supplied (strain 167, publisher README), recipe_revision=not supplied

A complete integral covers the supplied window under each signal's declared interpolation; it is not a verified plant total.

| Window / batch / phase | Signal | Unit | Accepted / all samples | Covered s / phase s | Coverage | Observed mean | Observed integral | Full-window integral | Integral unit |
|---|---|---|---|---|---|---|---|---|---|
| B06 / B06 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1324.08824 | 22509.5 | 22509.5 | kg |
| B07 / B07 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1314.02941 | 22338.5 | 22338.5 | kg |
| B08 / B08 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1321.02941 | 22457.5 | 22457.5 | kg |
| B09 / B09 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1316.47059 | 22380 | 22380 | kg |
| B10 / B10 / whole logged batch | sugar_feed_rate_kg_rs_h | kg/h | 18 / 18 | 61200 / 61200 | complete | 1317.64706 | 22400 | 22400 | kg |

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
