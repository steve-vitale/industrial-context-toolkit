# More public inputs for maintenance and engineering work

The [second acquisition](round-2/README.md) adds **47 more files (203 MB)**: historical excavator work orders,
five facility drawing/document sets, industrial failure/quality data, process models, instrument photos and
additional CAD originals. Both acquisitions total 101 files in 29 download groups; groups are not independent
plants. Each acquisition retains its own provenance, failures, rights and inspection limits.

The 2026-11-07 acquisition adds **54 files, 114,865,314 bytes, across 14 source groups**. They are downloaded
locally, with original filenames/bytes, attribution, license information, published checksums where supplied,
and a SHA-256 pin for every file. Four separate CAD originals are committed in the
[reserved CAD collection](../cad-handoff/qualification/public-sources/MANIFEST.json).
Groups are download units, **not independent plants**. This is an acquired, unscored corpus, not an accuracy result.

## Get the same inputs

From the repository root:

```sh
# One group; standard library only, original bytes in ignored data/external/<group>/.
python examples/public-data/fetch_sources.py maintie --max-mb 10
python examples/public-data/fetch_sources.py uci-steel-energy --max-mb 5

# All 14 groups; 125 MB total missing-download cap, then integrity/format inspection.
python examples/public-data/reproduce.py --fetch --max-mb 125 --out data/external/public-admission-1

# Offline inspection of the local copies; optionally OCR raster photographs/flowsheets.
python examples/public-data/reproduce.py --ocr auto --out data/external/public-admission-2
```

`--out` must be a new directory. Repeat `--source GROUP` to select groups. Fetches accept only the committed
URLs/pins, refuse changed upstream bytes, and reuse matching local files without network access. No notebook,
script, macro, external workbook link or archive member is executed. Archives are inventoried, not extracted.
The opt-in catalog uses the unchanged `fetch_corpus.py` pin-checking engine. Historical corpus results keep
their original code fingerprints; the new groups are registered only in this separate command's process.
PDF text extraction needs pypdf or Poppler; optional raster-image OCR needs Tesseract. Missing dependencies and
partial PDF text are reported explicitly. The standard-library fetch and hash checks still work without them.

The saved [admission report](admission.json) records actual file integrity, parser versions, rows/records,
archive directories, document segments and limitations. It does not contain a transcription answer key,
engineering review, model predictions or claimed task scores. A new local report may differ in parser versions.
Source and metadata pins are in [the acquisition registry](../../data/public_sources_20261107.json) and
[the common pin table](../../data/corpus_pins.json).
The [original pre-wrapper admission](admission-original.json) is retained with its execution-content provenance.

The OCR baseline is deliberately retained: the generator nameplate produced **no text**, and the traction motor
produced only **six characters**. The other motor produced 153 characters, without a verified field key. These
are useful failure/coverage cases, not successful equipment extraction. Three batch workbooks produced text;
an embedded Word object in the Candida workbook was reported and left unread with embedded extraction off.
All four DOE PDFs produced partial text with the affected page numbers recorded. Blank pages and unreadable
content need page inspection; do not infer missing engineering content solely from that parser warning.

## Choose data for a job

| Category | Added public inputs / group to fetch | Useful next job and boundary |
|---|---|---|
| Maintenance language and context | [`maintie`](https://github.com/nlp-tlp/maintie): 1,076 fine-grained and 7,000 coarse-annotated short texts; [`maintnorm`](https://github.com/nlp-tlp/MaintNorm): normalization/masking corpus with publisher company and combined splits | Test grounded extraction and terminology normalization. These are sanitized texts, not a complete dated CMMS/equipment-register export. Do not turn text classification into completed-repair or installed-state evidence. |
| Condition monitoring | [`uci-ai4i`](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset): 10,000 synthetic rows | Failure-label/units handling and intake refusal cases. No real event clock; Product ID is not an installed asset register. Retain the synthetic label. |
| Energy and historian records | [`uci-steel-energy`](https://archive.ics.uci.edu/dataset/851/steel+industry+energy+consumption): 35,040 rows from a steel producer | Prepare an explicitly mapped energy/time-series input. `Usage_kWh` is interval energy, not instantaneous kW. Publisher CO2 name/units conflict; carbon calculations remain unresolved. No measured savings intervention or tariff supplied. |
| Equipment photos | `commons-equipment`: [Malmbergs motor](https://commons.wikimedia.org/wiki/File:Motor_nameplate_Malmbergs.jpg), [Italian generator](https://commons.wikimedia.org/wiki/File:Nameplate_of_Italian_Generator.jpg), [traction motor](https://commons.wikimedia.org/wiki/File:ZXAM2502A-4_traction_motor_nameplate_on_19_0077_(20210721133155).jpg) | Use the [photo-to-record route](../photo-to-record/README.md) with explicit evidence/crops and unreadable fields left unresolved. Actual OCR was run; transcription accuracy and current installed identity were not established. Per-file CC0 / CC BY-SA 4.0 and credits are in the pins. |
| Experimental batches | [`wine-competition`](https://zenodo.org/records/18757697), [`candida-bioreactor`](https://zenodo.org/records/19854128), [`sequencing-batch-reactor`](https://zenodo.org/records/18247081), [`pomace-fermentation`](https://zenodo.org/records/22152061) | Four additional laboratory deposits, with original workbooks/archive and available descriptions. Workbook text can be read now; named experiments, units, time axes, phases and calculation plans need explicit adapters before `batch_analysis.py`. They are not four accepted factory batch systems. |
| Batch measurement quality | [`distillation-modalities`](https://zenodo.org/records/22250958): actuator, sensor-uncertainty, GC-composition and ambient records, simulation configuration, modality availability and plant metadata | Deepen the [existing distillation case](../batch-analysis/public-distillation/README.md) with uncertainty/interpolation and alignment checks. These are more modalities of the same plant, not independent validation. Large audio/image/NMR/simulation archives remain excluded. |
| Process models, flowsheets and graphs | [`idaes-processes`](https://github.com/IDAES/examples/tree/eb64e38ac429b7e3ae4f8db071f8d8cad2eef675/idaes_examples/notebooks/docs/flowsheets): methanol synthesis/recycle and temperature swing adsorption | New process coverage within the existing IDAES family. Retain notebooks and Python as source evidence only. A reviewed model-schema adapter is needed before graph, loop, drawing or platform export; downloaded simulations are not executed. |
| Technical documents and instructional drawings | `doe-engineering-drawings`, `doe-mechanical`, `doe-operations-maintenance`: [engineering prints](https://www.energy.gov/ehss/articles/doe-hdbk-10161-93), [mechanical handbook](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1018-93_VOL1.pdf) (both volumes), [O&M guide](https://www.energy.gov/cmei/femp/articles/operations-and-maintenance-best-practices-guide-achieving-operational-efficiency) | Sourced document questions and drawing practice. The fundamentals handbooks are archived/cancelled references, not active standards or site procedures. Text extraction is partial on pages without text; reference diagrams need a separately sourced/keyed drawing case. Original PDFs remain local; no third-party figures are republished. |
| CAD exchange | [Four reserved originals](../cad-handoff/qualification/public-sources/MANIFEST.json): air/water, mechanical and power drawings from LibreCAD, plus an ezdxf hatch example | Test preservation across unfamiliar geometry. Two upstream projects, not four independent plants. Do not open/score these during method development; follow the [frozen protocol](../cad-handoff/qualification/PROTOCOL.md). No native editor acceptance is claimed. |

## Categories already covered, and remaining gaps

The official DEXPI collection still points to `a23d61e2e089eb2ca464cd552f9ae580a2785963` as of this acquisition.
All 634 files are already available through `python scripts/fetch_corpus.py dexpi-ttc-all`; refetching them is
not new coverage. Existing OPEN100, PID2Graph, public drawings, PRONTO logs/alarms, HAI, hydraulic, MetroPT and
BattLeDIM data remain in [the earlier catalog](../../docs/CORPUS_FETCH.md). New material here is not silently
added to the eight-workflow matrix, reader leaderboard or feature-review totals.

The Nestor excavator loader points to `prognosticsdl.systemhealthlab.com`; that host failed DNS during acquisition.
No work-order records were obtained there. NIST software licensing was not substituted for the missing dataset's
terms. The failed OSTI mechanical-handbook download was replaced by a successful DOE-hosted original; both
attempts are recorded in [discovery outcomes](discovery-outcomes.json).

Still missing: public, linked equipment registers plus dated work orders/parts/closure/effectiveness records;
engineering-reviewed multi-revision CAD/P&ID truth; tested native GUI edit/save/reopen; and customer environment
acceptance. Public records cannot supply a plant's SharePoint permissions, CMMS authority, historian/PLC endpoints,
current installed identities or approvals. Those remain supplied inputs for the tools, not invented fixtures.

## Keep acquisition separate from evaluation

Publisher annotations and original train/validation/test files are retained. MaintIE, MaintNorm and IDAES
materials are related within their respective upstream families; overlap is not ruled out. More files and
modalities must not inflate the independent-source count.

Before a new method run, declare the source families and task, freeze the candidate/adapter and acceptance rules,
and prepare a text/image-only inference packet that excludes annotations, labels and reference outputs. Record
actual exposure. Once a case informs a fix it is development evidence; retain the failure and use a replacement
case for a subsequent transfer claim. CAD's reserved split has its own stronger separation protocol.

All new downloads are local ignored source storage. Publisher metadata snapshots are retained for provenance;
each group carries its license, attribution, limitations, excluded files and original-source URLs. No source
author endorsement, timed review saving, model accuracy or production acceptance is implied by a successful fetch.
