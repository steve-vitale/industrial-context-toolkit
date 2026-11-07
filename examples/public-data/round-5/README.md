# Industrial batches, alarms and engineering exchange references

This pass acquired **35 original files, 196,525,541 bytes, in nine download groups**. The five passes now total
**218 files, 620,297,070 bytes, in 49 groups**, plus the four separately frozen DXF originals. Files, revisions,
shuffled folds and download groups are not independent plants. These are acquired, unscored inputs.

Originals remain in ignored `data/external/<group>/`. The repository retains the
[source registry](../../../data/public_sources_20261107_round5.json),
[SHA-256 pins](../../../data/corpus_pins.json), publisher metadata, [selection](SELECTION.json),
[acquisition receipt](acquisition.json), [admission](admission.json) and [verification](verification.json).
No downloaded code, macros, pickle data, model, solver or CAD application was executed. No archive was extracted.

## Fetch or inspect

Python 3.10+, from the repository root:

```sh
# Small, complete industrial batch deposit, including its dictionary/reference material.
python examples/public-data/round-5/reproduce.py --fetch --source industrial-yeast --max-mb 0.1 --out data/external/yeast-admission-1

# All nine groups, bounded by the committed original byte/hash pins.
python examples/public-data/round-5/reproduce.py --fetch --max-mb 210 --out data/external/public-round5-1

# Offline after acquisition; --out must always be new.
python examples/public-data/round-5/reproduce.py --out data/external/public-round5-2

# Cached replay with network refused, earlier-method/pin checks and altered-original controls.
python examples/public-data/round-5/verify.py --out data/external/public-round5-verification-1
```

Repeat `--source GROUP` to select groups. Standard-library fetching uses the unchanged common checksum engine.
PDF text inspection uses the existing optional pypdf/Poppler reader; missing readers and unsupported inputs are
reported. Parquet framing, JSON syntax and ZIP/AASX directories are checked without installing packages or
reading archive members. These checks do not certify schema conformance or engineering meaning.

ALPI's HTTPS chain failed in this Python environment. Windows curl with Schannel verified HTTPS and acquired
all three originals; no insecure option was used. If your Python trust store has the same problem, use a client
with working system trust to place the exact pinned bytes at `data/external/alpi-packaging/`, then run the
offline command. Changed upstream bytes are refused. NIST HEAD requests returned 403, but the declared ordinary
HTTPS GET downloads succeeded; the failed discovery and successful acquisitions are both retained.

## What was added and what to do with it

| Category / fetch group | Actual addition | Useful next task and boundary |
|---|---|---|
| Industrial batch logs — `industrial-yeast` | [Baker's-yeast deposit](https://figshare.com/articles/dataset/33201579), CC BY 4.0: all five files; 59 batch metadata rows, 1,090 time-series rows, 18 reference-profile rows | Prepare a declared batch/unit mapping for the batch-analysis workflow. The publisher identifies 10 full-process batches; the remaining batches are sparse. Hourly rows are repeated observations within batches, not 1,090 independent trials. Original operator PDF logs are withheld, so their transcription cannot be checked here. Keep evaluation profiles and summaries outside a future inference packet. |
| Industrial alarms — `alpi-packaging` | [ALPI / University of Padua](https://researchdata.cab.unipd.it/1031/), CC BY 4.0: raw/processed alarm archive, README and preprocessing source | Start with the publisher dictionary, then separately declare extraction of the raw CSV for an equipment/alarm/time mapping. Only the directory was inventoried here. Processed labels/splits remain distinct; pickle is never deserialized. Occurrence sequences do not establish actionable priorities, work-order closure or successful repairs. |
| Maintenance and tag descriptions — `synthetic-maint-sensor` | [Pinned synthetic dataset](https://huggingface.co/datasets/Jvachier/industrial-maintenance-synthetic/tree/d19fef76d9969f162d8633360187920137baeb2b), Apache-2.0: complete maintenance and sensor-tag Parquet files and README | Develop intake/mapping and deliberately dirty-data exercises after a separate schema/relationship check. Framing only was inspected; publisher row counts, joins and stated impurity rate were not verified. These are synthetic records; tag descriptions are not time-series observations. They do not close the real industrial maintenance-history gap. |
| Manufacturing quality — `uci-steel-faults` | [UCI Steel Plates Faults](https://archive.ics.uci.edu/dataset/198/steel+plates+faults), CC BY 4.0: original archive and publisher CSV; 1,941 rows, 27 descriptors and seven class columns | Prepare a source-bound quality classification exercise. These are numerical descriptors, not raw defect photographs. Archive/CSV representations are the same collection; neither provides asset histories, event clocks or site acceptance limits. |
| Energy/process measurements — `uci-ccpp` | [UCI Combined Cycle Power Plant](https://archive.ics.uci.edu/dataset/294/combined+cycle+power+plant), CC BY 4.0: original archive and CSV, 9,568 rows | Check units and build a declared power-output analysis. Data are shuffled and lack timestamps; row order cannot support historian drift or before/after savings. Publisher language calls PE energy while the units are MW, a power unit. Five shuffled workbook folds are repeated representations of one collection. |
| Equipment/context exchange — `idta-digital-nameplate` | [IDTA Digital Nameplate](https://github.com/admin-shell-io/submodel-templates/tree/5285185b1ef9425fe45068bcbda8faaf74f3eb89/published/Digital%20nameplate), CC BY 4.0: 3.0/3.0.3 JSON templates, two 3.0.3 AASX variants, READMEs and license | Compare a reviewed photo/asset record with a published field vocabulary; later declare a revision or adapter exercise. Templates/example values are not installed equipment or a transcription key for unrelated photos. JSON syntax and container inventory do not establish AAS schema conformance or a ready toolkit adapter. |
| Process models — `biosteam-sugarcane` | [BioSTEAM/Bioindustrial-Park](https://github.com/BioSTEAMDevelopmentGroup/Bioindustrial-Park/tree/c1e3393d347046aec23386cef368267200e20ac8/biorefineries/cane), MIT: sugar, ethanol, combined sugar/ethanol and cellulosic-ethanol system definitions, README/license | Review authored process structure before a separately declared toolkit-model adapter. Selected Python imports other modules and is retained as source evidence; this is neither a standalone model package nor a solver result. Related system definitions are one source family. |
| Equipment photograph — `commons-ksb-pump` | [KSB pump nameplate at Mine Göttelborn](https://commons.wikimedia.org/wiki/File:20260426_Grube_G%C3%B6ttelborn_08.jpg), Flocci Nivis, CC BY-SA 4.0: original 9.4 MB photo and license/author metadata | Use the [photo-to-record route](../../photo-to-record/README.md) with explicit crops, unknown fields and reviewed transcription. OCR was off; the retained unsupported result is not an empty plate. A displayed historic plate does not establish current installed identity. |
| CAD/STEP and technical drawings — `nist-pmi-cases` | [NIST/MBx-IF PMI test cases](https://www.mbx-if.org/home/cax/resources/): CTC-01/02 PDFs and three complete definition/STEP/native-CAD archives | Prepare a separate mechanical exchange/PMI task with the reference specifications. Archive directories include STEP, CATIA, Inventor, NX, SolidWorks and Creo-style files; their contents remain unopened. Public reference files are valuable, but no preservation, geometry or PMI result was measured here. These formats are outside the present ASCII DXF qualification and do not change its frozen cohorts. Retain NIST attribution and disclaimers; no endorsement. |

## What the verification establishes

All 35 originals match their raw-byte SHA-256 pins. Where publishers supplied MD5, SHA-1 or LFS SHA-256, the
initial download checked those too. All checked CSV rows have their expected column widths. Two standalone
NIST PDFs yielded unreviewed text; text extraction does not verify their graphical annotations.

The cached replay checks all nine groups with **zero network calls and zero fetched bytes**. Truncation and
same-size mutations are refused for one original in every group: 18 controls. All 51 preexisting pin groups
and the ten recorded fetching/extraction/CAD methods remain unchanged. A second fresh HTTPS fetch of the five
yeast files reproduces all pins. It does not re-fetch the other eight groups. Nothing is added to accuracy
tables, training splits, the workflow matrix, feature-review totals or the reader leaderboard.

## Coverage that remains open

The [previous passes](../README.md) already cover plant P&IDs/electrical drawings, scans, public maintenance
records, photos, condition monitoring, historian/energy data, batches, process models, DEXPI and DXF. This pass
deepens the covered categories without claiming a new source for each one.

The [IRIS-v2 scene/P&ID collection](https://zenodo.org/records/18671364) is a useful research lead, but its
CC BY-NC-ND 4.0 terms were recorded and no dataset files were acquired for the consulting examples. Two CSB
report pages were unavailable during discovery; no reports were obtained. These outcomes remain in
[the discovery record](discovery-outcomes.json), rather than being counted as acquired coverage.

Still missing: verified real industrial work-order/asset/parts histories with repair outcomes, reviewed
multi-revision P&ID truth, qualified native CAD edit/save/reopen, and customer-system acceptance. Synthetic
records, templates, mechanical test cases and unrelated public drawings cannot substitute for those.
Before evaluation, freeze the task/method/acceptance rules and separate annotations/reference outputs from
inference inputs. Record what was actually exposed; public availability does not establish an unseen holdout.
