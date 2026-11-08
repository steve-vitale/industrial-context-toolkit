# Review one route across three sheets

This fictional case shows what to hand a maintenance or engineering manager when a pump's downstream
route crosses drawings with an unresolved continuation. The tool runs on prepared records; no model reads
an image here. Start with the [remote review report](worked/remote-reviewed/REPORT.md), then inspect the
[exploratory route](worked/remote-exploratory/REPORT.md) and its [qualified register](worked/remote-exploratory/REGISTER.csv).
Download/open the corresponding `REPORT.html` in either folder for the browser view.

The three authored sheet schedules and separate acceptance key were frozen at `4f58d2a` before the tool.
The same assistant authored and saw sources, graph assumptions, key and implementation; graph labels such
as confirmed are fictional supplied assumptions, not authenticated engineering decisions. This tests
software behavior on exposed development records, not blind extraction, field truth or review-time savings.

The first prototype treated matched off-page pairs as process connections without explicit network meaning.
Its [code/result and explanation](attempt-1/NOTE.md) remain. The source schedules distinguished media,
but the prepared graphs omitted that meaning. A new input cohort, frozen at `24eed65`, adds source-bound
`network_kind` claims. The original graphs/key are unchanged and the successor still qualifies the original
missing meaning. This preparation correction is not a model accuracy gain or an untouched holdout result.

From the repository root, with Python 3.10+ and the standard library:

```sh
python -S examples/pid-path-review/reproduce.py --out your-new-review-example
```

It verifies frozen source/graph bytes, runs five questions under both policies, compares each with the
deliberately unrestricted undirected baseline, and performs corrected/unrelated revision runs. That baseline
claims reachability for every question, including the reversed edge. It supplies no evidence/review controls.

| Question | Reviewed-only | Exploratory |
|---|---|---|
| Local pump to local valve | Supported | Supported |
| Pump to vessel across disputed 3 in / 4 in continuation | Not established | Qualified, with both sources and owner |
| Uncertain signal continuation | Not established | Qualified with unresolved status/direction |
| Follow a known edge backward | Not established | Not established |
| Reach a connector whose next sheet is missing | Supported up to that connector; missing continuation retained | Same boundary retained |

The [actual replay](worked/replay.json) matches all ten fixed policy outcomes. After the third sheet is
corrected, the prior remote answer reopens and the new route is supported by the supplied assumptions.
The local answer's dependencies remain unchanged even though two wider register rows change. An unrelated
record addition reopens neither answer. Exact earlier packets remain nested and re-score on receipt.

Eighteen regression methods additionally exercise new edges/conflicts, typed/duplicate/unknown input,
scope-qualified identity, source/claim status, omitted media, rejected records, direction, bounded scope,
tampered/rehashed answers and HTML, existing/nested destinations and escaped HTML/JSON CSV cells.
Browser inspection of the actual generated HTML confirmed the visible source conflict and separate item/
association columns. This is display QA, not a human recipient or mobile usability trial.

For your own job, substitute a graph from the [supported model/map routes](../../docs/WORKFLOWS.md), exact
IDs and supplied source/review meaning. Follow the [tool contract](../../docs/PID_GRAPH_QUESTIONS.md).
Original document verification, graph preparation, source authority and engineering acceptance remain your
review work. The consumer does not produce full line/valve registers, operating consequences or CAD files.
The [consulting scope](../consulting-start/README.md) shows how to agree a bounded paid assignment while
keeping the public example useful for self-service.
