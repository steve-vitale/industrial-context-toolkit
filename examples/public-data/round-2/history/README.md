# Retained first admission

`admission-first.json` is the actual first 46-file result, before the successful system-TLS Salina download.
`registry-first.json` and `inspector-first.py` preserve its exact registry and normalized method fingerprints.
The Python snapshot is historical source at its original `examples/public-data/round-2/reproduce.py` path;
its relative imports/root calculation are not intended to run from this history directory.

The first run exposed the earlier LANL CSV's non-UTF-8 bytes and unexpected Nestor row widths. The current
inspector keeps the UTF-8 failure and adds an explicit partial/warning status for those row widths; it does
not repair or discard records. Salina was subsequently acquired with verified Windows system TLS. The first
discovery failure is also retained in `../discovery-outcomes-first.json`. None of these are held-out task scores.
