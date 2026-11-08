# Questions across P&ID sheets: review status must travel with the answer

Reviewed 2026-11-08 after [Maetee Lorprajuksiri's public example](https://www.linkedin.com/posts/maetee-lorprajuksiri-22378a46_processengineering-pid-dexpi-activity-7524669143963525121-jNHS),
shared as [this short link](https://lnkd.in/p/gmVa2TTE). The author describes connecting three sheets,
holding uncertain matches and a size disagreement for review, retaining status in derived registers,
and exporting DEXPI. These are the author's reported outcomes; no input/key/output packet or independent
score was supplied in the post. Its counts and claimed extraction quality are not toolkit results.

## Useful work for a maintenance or engineering manager

Start with a specific question: which drawings and records need checking before this pump replacement?
Give the agent the relevant supplied sheets, equipment export and instrument records. The existing
[one-map route](ONE_MAP.md) connects these sources and produces a review queue. Its `draft-lists` command
can prepare draft equipment, instrument and loop records. Those are useful starting points now.

A subsequent path-question feature should return a visible path, source sheet/revision/locator for each
step, review status and every stopping boundary. Separate a confirmed continuation from an unresolved
candidate. For example, a connector pair with disagreeing sizes should remain visible in the review map
while an accepted-only path query stops there and asks the owner to resolve it. A deliberately exploratory
query may display the candidate, with its disagreement carried into the answer and downstream exports.
An empty accepted path means no supported path was established within the supplied coverage; it does not
prove physical disconnection or adequate maintenance isolation.

These traversal/query behaviors are **proposed**, not implemented commands. Current `one_map.py`
`pair_offpage` retains reciprocal connector pairs as `connects` / `offpage_pair`, marks direction unknown,
and separately records shared-attribute disagreements. This is valid evidence retention. A future consumer
must reconcile edge status and applicable open conflicts before treating a pair as traversable. Renaming
every current edge to HOLD would lose the distinction between an observed pairing and a disputed attribute.

## Three distinctions the answer must preserve

| Evidence | Supported use | Additional evidence needed |
|---|---|---|
| Shared line network or logical stream | Candidate relationship and records to inspect | Physical pipe adjacency, actual direction and selected route |
| Reviewed physical path | Trace the supplied topology within stated coverage | Operating lineup, check-valve orientation, control mode and current installed state |
| Path plus a process description | Frame a conditional investigation | Applicable balances, dynamics, safeguards, failure mode, approved operating basis and engineering judgment |

`graph_export.py` already distinguishes network co-membership, logical streams, physical `piped_to`
segments, instrument connections and actuator/nozzle relations. A generic graph walk must not turn them
all into process flow. A topology trace alone cannot establish a failure consequence or issue an isolation
instruction. A graph retains sourced assertions; it does not become the engineering authority by being
structured. Company records, accepted decisions and ownership still govern the work.

Register outputs should retain row-level source and review state plus any dependency on a disputed link.
An asset's own tag may be supported even while its inferred service or downstream association remains open.
Do not blanket-confirm a whole row because one field matched, or reject every local fact because a remote
continuation is uncertain. Current draft records remain unverified; richer cross-sheet register propagation
and complete line/valve list generation require their own supported contracts and receiving checks.

## Next bounded development exercise

Before implementing path queries, freeze a three-sheet case and answer key with a legitimate continuation,
a line-size disagreement, an ambiguous signal connection, reversed direction and a missing sheet. Include
an accepted local route that does not depend on the disputed boundary. Test an accepted-only query and an
explicit exploratory query against a naive unrestricted walk. Then revise one source: dependent answers
must reopen, unaffected facts must remain, and exported registers must retain their qualifications.

Use attributed public sheets where available; otherwise label the authored case fictional and exposed.
Separate a fixed-key software exercise from reader accuracy, engineering review and human time saved.
This exercise is not yet run. It must not change old benchmark keys or convert a successful data parse into
DEXPI exchange qualification. Reuse the public-model review in [PID_RULES_RESEARCH.md](PID_RULES_RESEARCH.md)
before considering a new DEXPI adapter; returned-file semantic checks remain a separate gate.
