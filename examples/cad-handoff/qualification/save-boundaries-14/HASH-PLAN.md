# Test process hash-order effects without changing preservation rules

Declared before fixed-seed native execution. Attempt-1 and the historical no-edit default returns have
53 strict row differences per case: 50 LTYPE and 3 STYLE records. Names/handles are associated differently;
generated textstyle0/textstyle1 font associations swap. The old conservative closed-pair checker only closes
63 of 278 records for one pair, so this is not yet an established whole-record equivalence explanation.

Qt 5.14.2's public qhash.cpp documents the testing-only QT_HASH_SEED=0 control. Hypothesis: process hash
iteration contributes to serialized generated resource assignment. Run two separate fresh processes, each
importing all six identical exposed sources and no-edit exporting default format, with only QT_HASH_SEED=0
added to the frozen controller environment. Retain every raw file, public inventory and fresh read. Compare
both runs with the original unchanged strict comparator and with the unseeded attempt-1 returns. No timestamp,
style or handle exclusion, sorted metric, resource deletion or save-header change is allowed.

Treat a zero fixed-seed repeat only as bounded reproducibility evidence. It cannot resolve source/full-save
preservation losses, guarantee byte equality or qualify another runtime. Keep all failures and any remaining
differences. This environment control is a diagnostic intervention, not advice to disable production hash
randomization or a claim to observe every internal proprietary exporter operation.
