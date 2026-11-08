# Keep receiver failures and correct the aggregate count

The first receiver stopped at a dangling dictionary link in an actual return.
Its exact script and reproduced raw stdout/stderr are retained. The successor
reports the unresolved handle/path explicitly instead of crashing or excluding
it. No file is repaired and no missing object becomes a preservation pass.

The first completed diagnostic correctly captured 48 job observations, 46 fresh
imports, 12 strict differences, 34 profile refusals and two native failures,
but its `exports` aggregate was 5: a source-record dictionary shadowed the
successful-job list. Rename those local variables and regenerate only as
diagnosis-count-corrected.json. The first diagnosis.json remains. The receiver
checks that the sole difference between them is that aggregate 5 -> 46, and
the regression pins 48 attempted/46 completed/46 fresh, separately from failed
jobs and the 26 earlier successful exports. No native execution is repeated.
