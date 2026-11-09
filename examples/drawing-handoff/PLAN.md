# Engineer and engineering-manager receiving rehearsal

Freeze before the new rehearsal. Use the existing, already exposed fictional
markup example and separate valve CAD example. They are two jobs, not a single
integrated plant drawing. No image interpretation or new model run is performed.

Run the real documented markup CLI and CAD review CLI into new folders. Preserve
commands, stdout/stderr, exit status, complete packets and hashes. Expected:

1. Markup comparison writes a packet (exit 0), retaining all seven requests,
   the missing safety valve removal, partial bypass, missing signal, unreadable
   instruction/note and wrong baseline. Retain the unrequested fail-action change
   and the uncovered material fact. Exit 0 does not clear these findings.
2. CAD review writes a packet but exits 1: all three planned attribute edits
   are observed while all 335 unexpected strict differences remain unresolved.
   Preserve the exact before/returned drawings and complete strict queue.
3. A brief based on those actual results identifies the next action and review
   role for each unresolved item, with references back to the complete packet.
   Roles are suggested responsibilities, not authenticated assignments. There is
   no automatic release, claimed time saving, site acceptance or shared case ID.
4. Re-running a portable markup packet reproduces its comparison facts; a second
   invocation into an occupied output refuses. Retain the first packet unchanged.

This is an agent-authored workflow rehearsal, not independent engineering review,
a human usability study or qualification of reading arbitrary P&IDs/CAD formats.
Native qualification and fresh reserved cases remain separate unfinished work.
