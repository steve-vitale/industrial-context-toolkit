# Restore empty protocol directories before replay

The first concurrent archive replay fails `Private mailbox directory inventory
differs`. The original native attempts and their live receipts pass. The
file-only archive contains every inventoried file but omits empty directories.
The original `recheck.py` already restores each declared `native_io.FOLDERS`
directory at both mailbox roots. Apply that same rule in the separate derived
replayer and semantic-control materializer before their successor executions.

Keep `native_revisions.py`, its preparation/launch freezes, native files,
archives and first external identities unchanged. Its original `check` branch
remains a retained failed experiment; the public replay command is now
`recheck_native_revisions.py`. Preserve the first replay observation and complete
failed control logs. Do not fabricate files, invocation records or failed/normal
outcomes. Re-created empty directories carry no evidence bytes.

Acceptance remains the same: both original complete packets receive unchanged,
their externally pinned receipts match, and source/plan repinning, changed
derived identity, omitted SERIAL commit, lost foreign-field editability and
hidden controller failure refuse after local file inventories are recomputed.
No native restart, changed comparator, larger bounds or CAD result promotion.
