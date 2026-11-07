# Additional originals across the toolkit's data categories

This acquisition adds **47 original files, 203,089,339 bytes, in 15 download groups**. Together with the
[first acquisition](../README.md), that is 101 files (318 MB) in 29 groups, plus the four separately frozen
CAD originals. Groups count downloads, not independent plants. These inputs are acquired and structurally
inspected where stated; they have no new model accuracy, maintenance effectiveness or CAD qualification score.

Original bytes live in ignored `data/external/<group>/`. The public repository contains their URLs, SHA-256
pins, source-family/exposure records, attribution, rights/limits and actual admission results. None of the
downloaded notebooks, Python, Modelica, macros or embedded content is executed. No new package was installed.

## Fetch or check

From the repository root, with Python 3.10+:

```sh
# A small subset, with a total missing-download cap.
python examples/public-data/round-2/reproduce.py --fetch --source nestor-excavators --max-mb 2 --out data/external/nestor-admission-1

# All 47 originals; archives are inventoried, never extracted.
python examples/public-data/round-2/reproduce.py --fetch --max-mb 225 --out data/external/public-round2-1

# Offline: verify cached bytes and inspect the same admitted structures.
python examples/public-data/round-2/reproduce.py --out data/external/public-round2-2
```

`--out` must be new. Repeat `--source GROUP` to select groups. Standard-library fetching reuses the unchanged
common checksum engine. PDF text inspection uses the existing optional text extractor (pypdf or Poppler);
missing dependencies are reported. No OCR is attempted here. A parser error produces exit 1 while preserving
the other files' results. The first LANL CSV currently triggers that error; selecting only another group
avoids that known parser case. An intact download does not imply that its contents are import-ready.

Salina's HTTPS chain failed in this Python environment. Windows curl 8.13.0 with Schannel verified the server
and downloaded the original successfully, with no insecure TLS option. The [discovery record](discovery-outcomes.json)
retains both outcomes. If the pinned Python fetch encounters the same error, use a client with a working
system trust store to place the exact original at `data/external/salina-design-basis/original.pdf`, then run
the offline check. A changed file still fails its byte/hash pin; verification is not disabled.

## What was added and how it can help

| Category | New source groups | Useful next task and limits |
|---|---|---|
| Work orders and maintenance context | `nestor-excavators`: [official historical Nestor copies](https://github.com/usnistgov/nestor/tree/1d9cd96f129fb6562f5fdb86ae0a39fb50085048/nestor/datasets), raw/cleaned CSVs plus loader and notices | Prepare explicitly mapped dated maintenance text/cost records using the maintenance intake guide. These are deprecated historical copies recovered from the parent of NIST's removal commit after the current host failed DNS. Dataset reuse terms remain unresolved; NIST software rights do not license the third-party data. Keep originals local. Unexpected CSV row widths remain visible; do not silently drop or repair them. No linked parts/effectiveness register is supplied. |
| Condition monitoring and failure classification | `uci-aps`: [Scania APS failures](https://archive.ics.uci.edu/dataset/421/aps+failure+at+scania+trucks); `uci-naval`: [naval propulsion](https://archive.ics.uci.edu/dataset/316/condition+based+maintenance+of+naval+propulsion+plants) | Preserve publisher train/test splits and labels. APS negatives are other failures, not healthy trucks; feature meanings are anonymized. The data's GPL notice conflicts with UCI's CC BY footer: local originals only. Naval rows are a simulated degradation grid, not dated failure episodes. Neither is a verified repair history. |
| Manufacturing quality | `uci-secom`: [semiconductor measurements and pass/fail labels](https://archive.ics.uci.edu/dataset/179/secom) | Exercise missingness and source-bound quality questions. Anonymized sensor meanings/units and test labels need an explicit adapter and task key; do not infer a causal failure mechanism from a classification label. The original archive remains unopened beyond its directory inventory. |
| Energy and historian records | `uci-gas-turbine`: [five chronological years of turbine measurements](https://archive.ics.uci.edu/dataset/551/gas+turbine+co+and+nox+emission+data+set); `historian-rca`: [hold-tank benchmark](https://github.com/ScottDuncanAI/HistorianRCA/tree/8d12a821395ce5f72e464dc78cc2c10d05cbb9ed) | Gas-turbine dates are omitted; do not invent timestamps. It is the same plant as UCI's Combined Cycle dataset. Keep publisher year splits and check units. HistorianRCA adds a simulated process description, tag register, diagram and two Parquet sampling versions of one unit; its answer key is withheld. Parquet framing is checked, rows/schema are not read because a reader is not installed. |
| Batch and laboratory measurements | `lanl-biomanufacturing`: [PCC6803 cultivation data](https://github.com/lanl/Biomanufacturing-PCC6803-Dataset/tree/08cf022aa6537ee4f50dc55683b4b6ee3d3a4529) | Source-linked experimental comparison after mapping experiments/units. Original and merged literature datasets overlap; they are not independent campaigns or factory batch historians. One CSV reads as UTF-8, the earlier one does not. Keep that failed admission and original bytes rather than guessing an encoding or changing the source. |
| Process models, controls and context graphs | `modelica-fluid`: [pump, tanks, controlled tanks, boiler, exchanger and batch-plant examples](https://github.com/modelica/ModelicaStandardLibrary/tree/1625240ba3034459ad1bdbe245d157b2e58cb183/Modelica/Fluid/Examples); `historian-rca` description/tags/diagram | Compare source-described equipment, connections and controls before a reviewed toolkit-schema adapter. Modelica examples require the full library and solver; this subset is source text, not a self-contained running simulator. No downloaded model is executed or treated as installed plant truth. |
| Equipment photos and markings | `commons-instruments`: [air-supply gauge](https://commons.wikimedia.org/wiki/File:Pressure_gauge_of_air_supply_pipe.jpg), [brake-pipe gauge](https://commons.wikimedia.org/wiki/File:Pressure_gauge_of_brake_pipe.jpg), [regulator/gauge](https://commons.wikimedia.org/wiki/File:Regulator_valve_%26_pressure_gauge.JPG) | Use the photo-to-record workflow with source/crop evidence and unknown fields. Per-file CC0/public-domain declarations and credits are retained. A photograph does not establish calibrated pressure, current installed identity or an operating instruction. OCR/reading accuracy was not tested here. |
| P&IDs, electrical drawings, scans and engineering documents | `pahala-drawings`, `virden-drawings`, `haile-water-treatment`, `salina-design-basis`, `ruttan-water-treatment`: five facility drawing/design/submission sets | Start a page-scoped drawing or document question with an explicit source/revision, then separately key interpretation. Pahala describes project concept rather than design requirements. The other records include scans and mixed text layers. Government hosting does not establish federal authorship or redistribution rights for consultant drawings. All original PDFs stay local; no drawings are republished. |
| Native CAD exchange | `cad-extra-originals`: [six pinned ezdxf examples](https://github.com/mozman/ezdxf/tree/c498560bb491c357deda538360ed0c8fdb11f5a7/examples_dxf), plus license | Nested dimensions/blocks, multi-insert attributes, text/viewports, columns and hatch issues, selected by filenames. Contents are intentionally uninspected in this acquisition. Same upstream family as the earlier hatch case; no new plant or native-acceptance claim. Declare the next CAD split/method before using them for qualification. |

The five original facility PDFs are [Pahala](https://www.epa.gov/system/files/documents/2021-08/pahala-wwtp-design-build-drawings-2021-07-23.pdf),
[Virden](https://www.gov.mb.ca/sd/eal/registries/5697virden/2019-04-26_5697_00_phase_2_p_and_i_drwngs.pdf),
[Haile](https://des.sc.gov/sites/des/files/media/document/BOW_HGM_ContactWWTreatmentUpgrade.pdf),
[Salina](https://www.salina-ks.gov/media/utilities/Document%20Library/Salina_WWTP_Improvement_Project_BDR_Report_Final_051121%20%281%29.pdf)
and [Ruttan](https://gov.mb.ca/sd/eal/registries/294.30/20250618_letter.pdf). Discovery started from
[Scott Duncan's public source index](https://github.com/ScottDuncanAI/public-chemical-manufacturing-datasets);
the original government-hosted bytes, rather than that index's descriptions, are the admitted sources.

## Actual admission and gaps

The [saved admission](admission.json) records per-file integrity and actual parser outcomes. Earlier evidence
is retained in [history](history/README.md). Integrity checks, archive inventories and framing checks are not
semantic or engineering review. The byte-verified cached replay ran with network access replaced by a function
that raises if called. A separate empty-directory HTTPS download checked the naval archive pin.

The raw excavator CSV has 5,326 parsed rows, including one unexpected-width row; the cleaned copy has 5,308,
including two unexpected-width rows. The earlier LANL CSV fails UTF-8 parsing; the merged copy has 255 rows.
Pahala has a text layer; all 14 Virden pages need OCR; Haile, Salina and Ruttan have partial text with affected pages
listed in the report. No unreadable page has been treated as absent engineering content.

[IRIS](https://zenodo.org/records/18671364) is a promising linked P&ID/CAD/photo/point-cloud source, but its
CC BY-NC-ND 4.0 terms do not fit the intended commercial/derivative corpus. Only publisher metadata and the
file inventory are retained; no IRIS data was downloaded. KALBRO's metadata advertised data but its API file
list was empty, so no data was obtained there.

Existing sources continue to cover DEXPI/vendor exports, additional flowsheets, alarm/event/operator logs,
water-network and compressor histories, energy/O&M references, nameplates and batch workbooks. See the
[first acquisition](../README.md) and [earlier catalog](../../../docs/CORPUS_FETCH.md). More data here does
not add evaluated matrix cells or independent-source counts. Still needed are linked parts/closure/outcome
records, engineering-reviewed drawing revision truth, a usable task key/adapter for each new format, and
site access/acceptance for live workflows. Public records cannot supply those plant-specific authorities.
