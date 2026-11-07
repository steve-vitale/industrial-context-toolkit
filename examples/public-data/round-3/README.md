# More public records for the remaining data gaps

This pass acquired **29 original files, 103,450,866 bytes, in 10 download groups**. Across the three passes,
that is **130 files, 421,405,519 bytes, in 39 groups**, plus the four separately frozen DXF originals.
Groups, revisions, dates and language copies are not independent plants. These are acquired, unscored inputs.

Original bytes stay in ignored `data/external/<group>/`. The public repository retains the
[source registry](../../../data/public_sources_20261107_round3.json),
[SHA-256 pins](../../../data/corpus_pins.json), primary metadata, attribution, rights/limits and
[actual admission](admission.json). Nothing downloaded was executed. No package was installed.

## Fetch or check

From the repository root, Python 3.10+:

```sh
# Small example: three water networks and their original notices.
python examples/public-data/round-3/reproduce.py --fetch --source epanet-networks --max-mb 0.1 --out data/external/networks-admission-1

# All new originals, bounded by their committed byte/hash pins.
python examples/public-data/round-3/reproduce.py --fetch --max-mb 110 --out data/external/public-round3-1

# Offline: check already downloaded originals and inspect the same structures.
python examples/public-data/round-3/reproduce.py --out data/external/public-round3-2
```

`--out` must be new; repeat `--source GROUP` to select groups. The wrapper reuses the unchanged common
checksum engine and previous structural inspectors. PDF text inspection uses the existing optional text
extractor. Missing/changed files and parser errors are retained per file and return exit 1 after the cohort.
An unsupported reader is reported explicitly; a byte/hash match alone is not format or engineering acceptance.

## What was acquired

| Category | Source / fetch group | Useful next task and boundary |
|---|---|---|
| Maintenance-linked signals and alarms | [`tina-mining`](https://github.com/ari-dasci/OD-TINA/tree/927b1584ea4aeac2ac7daa084a82f899b114419b): four mining-machine days, README and CC BY-SA notice | Develop a declared maintenance/signal mapping using coded `m_id`, `m_subid` and `alarms`. Days were selected by date before reading rows, not by favorable outcomes. Variables are normalized/anonymized; there are no linked parts or work-order closure records. Four days are not a continuous full-history cohort. |
| Field alarm events | [`bms-alarms`](https://zenodo.org/records/22301575): all five deposit files, plus companion README/license | Preserve publisher train/test separation, metadata and rejected ambiguous cases. Data CC BY 4.0 differs from the companion software's BSD license. Periodicity annotations do not establish alarm rationalization, actionable priorities or repair effectiveness. No Parquet rows/schema/labels have been read here. |
| Parts and equipment specifications | [`mro-catalog`](https://data.mendeley.com/datasets/hr2ysn26ys/7): February and September English-named CSV snapshots | Prepare a source-bound catalog/revision comparison. Actual files contain 35,233 and 36,016 data rows, with 12 and 16 columns respectively. Headers remain Vietnamese and include empty columns. Keep the schema change; do not assume a ready equipment-register input or interpret the publisher's million-item title as the unique count in these files. Catalog identifiers do not establish installed assets, stock, BOM compatibility or completed repairs. |
| Wear/degradation experiments | [`nasa-milling`](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/): milling experiment archive | Create a declared wear-analysis case after reviewing contributor terms and the nested source documentation. Only the outer ZIP directory was inventoried; arrays and labels remain unopened. NASA hosting does not settle every contributor's data rights; local originals only. |
| Simulated condition monitoring | `nasa-cmapss`: turbofan degradation archive linked from the same NASA repository | Keep original nested splits and labels for a later frozen task. Simulation cycles are not dates or measured plant maintenance. Only the outer ZIP directory was read. This is a different source collection from milling, without implying independent plant field trials. |
| Process/context models | [`epanet-networks`](https://github.com/OpenWaterAnalytics/EPANET/tree/57d8bd8ad60e89b57f2a1ac591f05c8e13589866/example-networks): Net1/Net2/Net3, README and MIT notice | Source-described network topology, pump/control and water-quality questions. Passive section/row inventories were read; no solver or toolkit-schema adapter ran. Example-network identities are not installed plant truth. Related water-network datasets in the earlier catalog may share this modeling lineage. |
| Native CAD originals | [`freecad-originals`](https://github.com/FreeCAD/Examples/tree/40a806f3f3ef0e6a248fd5aed168a4d29213c421): attachment, fillet and overconstraint tutorial models plus README | Additional editable-model formats for a future separately declared workflow. Filenames/hashes only: no archive XML, geometry or thumbnail inspection. No repository-wide data license was found in the pinned tree; originals stay local. FreeCAD software licensing is not substituted. These files are outside the current ASCII DXF qualification profile. |
| Technical drawings, scans and pump references | [`usda-pumping`](https://directives.nrcs.usda.gov/sites/default/files2/1720457430/Chapter%208%20-%20Irrigation%20Pumping%20Plants.pdf): irrigation pumping chapter; [`phoenix-nameplate`](https://www.phoenixpumps.com/pdf/PPI_Pump_Nameplate_Guidelines.pdf): pump nameplate guidance | Page-scoped source questions and nameplate field review. Text was extracted from 208 and one page respectively; this is not a reviewed transcription of diagrams. Some USDA material is marked draft; no current-standard/site-procedure claim. Third-party/vendor figures are not republished and the PDFs stay local. |
| Equipment photograph | [`commons-fireboat`](https://commons.wikimedia.org/wiki/File:Nameplate_for_one_of_Fireboat_Firefighter_%27s_600V_DC_Marine_Motors.jpg): motor builder plate, Kaylee La Spisa, CC BY-SA 4.0 | Use the photo-to-record workflow with an explicit crop and reviewed transcription key. The current text extractor reports JPG unsupported with OCR off; zero segments is not an empty plate. No OCR or current installed-state determination was performed. |

## What the checks establish

All 29 raw byte/hash pins match. The [verification record](verification.json) retains a full cached replay
with the network fetch function replaced by a refusal, zero download budget and zero network calls. A separate
[fresh HTTPS fetch](fresh-fetch.json) reproduces all five EPANET file pins. Truncation and same-size mutation
controls are refused. All 40 previous pin groups and the existing evaluated fetching/extraction methods remain
unchanged. Saved metadata hashes normalize CRLF to LF; source hashes always cover raw original bytes.

Parquet checks verify framing/footer bounds only. NASA ZIPs each contain a nested ZIP, which remains unread.
The photo reader's unsupported result is retained. PDFs' extracted text is unreviewed. There is no new model
accuracy, workflow matrix cell, feature-review pass, human time saving or CAD qualification result.

The [discovery record](discovery-outcomes.json) retains the failed Mendeley version endpoint, explicit use of
the returned version 7, the BMS concept DOI's newer five-file version, and the excluded 5 GB capacitor archive.
The source files, including test/ambiguous labels, must be separated from future inference packets before
model evaluation. A file's public availability is not proof that it was unseen by a model.

## Coverage still missing

The [first](../README.md) and [second](../round-2/README.md) passes already supply batch/laboratory records,
plant P&IDs/electrical drawings, scanned documents, process flowsheets, historian/quality/energy histories,
maintenance text, photos, DEXPI and DXF. This pass deepens several thinner categories; it does not relabel
additional dates, revisions, tutorial models or annotations as independent plants.

The [later AMPS acquisition](../round-4/README.md) now supplies linked municipal asset/work-order/parts/labor
records and completion fields. **Linked industrial plant histories, verified parts consumption and repair
effectiveness** remain missing. A product catalog plus coded events from another source cannot fill those gaps.
Engineering-reviewed drawing revisions, native CAD acceptance and plant system/permission/ownership checks
also remain separate work. No source was added to the training, reader leaderboard or existing frozen CAD
qualification cohorts by this acquisition.
