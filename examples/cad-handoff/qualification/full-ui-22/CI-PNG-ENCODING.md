# CI compared PNG encodings instead of pixels

The [actual failed job](https://github.com/steve-vitale/industrial-context-toolkit/actions/runs/42537786428/job/128905842551)
at commit `427a14b` reproduced the complete second-receiver reports but failed on
regenerated difference-image file bytes. The exact excerpt is retained in
[CI-427-FAILURE-EXCERPT.txt](CI-427-FAILURE-EXCERPT.txt).

Recompute all thirty difference images on Linux from the original bound native
canvas pairs. Both the installed Pillow 10.2 and CI's exact Pillow 12.2 produce
different PNG encodings on all thirty files, with **zero decoded pixel, mode or
size differences**. [The diagnosis](png-encoding-diagnosis-1/OBSERVED.json) retains
the actual original container exits and complete per-image hashes/results.
These are Python-only image checks; they do not rerun CAD or change native images.

The replayer now requires exact file inventory, exact decoded PNG pixels/mode/size
and exact bytes for non-PNG outputs. All original evidence/image byte pins remain
required. Two focused test methods prove that alternate compression can pass,
while a single changed pixel or a missing image fails. The complete corrected
second-receiver replayer passes locally. New exact-head CI is a separate check.
There is no tolerance, camera, mask, raw-byte or strict CAD comparison waiver.
