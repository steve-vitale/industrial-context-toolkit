# Preserve the missing-output-directory failure

Attempt-2 is terminal exit1. Native import reaches export, which reports
Can't open file; the copied workdir lacks the empty returns directory. The
copy-by-frozen-files helper did not recreate empty directories. No exported
file or fresh-phase observation counts as successful. Retain all records.

Prepare attempt-3 from the exact attempt-2 frozen inputs in a new workdir,
creating every output's parent as declared in export.json. Freeze that directory
list as well as file hashes. Add a controller preflight that refuses a missing
parent, an existing output or an output outside /work before launching CAD.
Use the same explicit filters; extend the probe only to return the observations
already gathered if an export throws, without relaxing controller error/coverage
checks. Freeze the two successor methods before execution. No input source,
candidate, plan, route, exporter option, settings or native image is changed.
