# First development export refused its own readback

The first Riverbend build succeeded (63 nodes, 114 edges, 14 conflicts). The first
explorer export exited 2 with `map explorer: explorer HTML differs from retained records`.
The outer PowerShell command returned 1. No final packet was published.

Cause: the embedded HTML data used insertion order while saved JSON used sorted
keys. Parsing the saved records changed key order, so rendering them did not
reproduce the first HTML bytes. Sorting the embedded JSON fixes deterministic
readback without changing map data, question semantics, sources or the key.

The first browser check also stopped: its exact V-204 button locator matched both
the relationship and the question-answer navigation links. Both links correctly
name the same node. Selecting the first exact match corrects the test selector;
the HTML and engineering records were unchanged by that test correction.
