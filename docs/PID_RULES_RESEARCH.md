# Public methods for structured P&ID checks

Reviewed 2026-11-08 in response to [Johannes Van Opstal's experiment](https://www.linkedin.com/posts/johannes-van-opstal-7900446_processengineering-pid-artificialintelligence-share-7525131450166284288-9bFo/).
He describes explicit engineering records and deterministic checks alongside AI-assisted generation.
The public post supplies no reproducible benchmark or implementation. JSON constrains representation;
it does not establish that an interpretation, control strategy or drawing is correct.

## Reuse established models before extending local contracts

[DEXPI](https://dexpi.org/) defines process-industry exchange models.
[pyDEXPI](https://github.com/process-intelligence-research/pyDEXPI) supplies typed models, graph tooling,
import/export and validation interfaces. Its current documentation describes DEXPI 2.0.1 support and
format-fidelity tests. These are upstream capabilities, not capabilities verified by this toolkit.
The inspected upstream commit is `309f1433a718d42c503e8730664d93bb3531eba9`;
[source fingerprints](../examples/pid-port-review/PUBLIC-SOURCES.json) retain retrieval/version boundaries.
The [upstream project page](https://www.pi-research.org/research/software/pydexpi/) is another primary reference.

The toolkit already has a bounded [DEXPI XML route](WORKFLOWS.md), sourced model/graph exports and
generator signal checks. The new [port checker](PID_CONNECTIONS.md) is an optional local prepared-record
contract. It does not import pyDEXPI JSON or round-trip DEXPI. No pyDEXPI package or code was copied into
this feature; its repository currently declares AGPL-3.0 and additional license notices. Evaluate an explicit
version and applicable terms before integrating upstream code.

Before adding an adapter, pin the upstream version and source hash; map exact item/connection-point IDs,
direction, signal medium and source locators; retain unsupported roles and omitted fields; then compare
the original and returned graph on independently keyed public examples. Successful parsing is insufficient.
Never silently turn an absent field or a vendor-specific class into a known generic port.

## Engineering rule graphs: what is actually public

[Schulze Balhorn et al., arXiv:2502.18493v2](https://arxiv.org/html/2502.18493v2) describes 33 rules but
publishes five examples in Table 1. Its illustrative case is not a representative industrial drawing;
the reported perfect detection applies to that case and selected rules. Full graph-to-DEXPI return is
described as future work. We have not independently reproduced its results.

| Published example | Decision before using it locally |
|---|---|
| Large globe control valves | Treat the size/cost heuristic as a design-review suggestion, not a prohibition. |
| Vessel level indication | Establish vessel service, existing measurement and applicable safeguards first. |
| Pump suction strainer | Review fluid, suction losses, pump requirements and local design basis. |
| Pump discharge check valve | Review backflow scenario and the specific pump/system arrangement. |
| Pump isolation and drains | Review maintenance isolation, fluid hazards and the approved isolation method. |

These are review prompts, not executable rules in the toolkit or universal engineering requirements.
No full 33-rule library is claimed. Rule interactions and execution order also require validation.

## Admission criteria for a future site rule

Record a rule ID/version, primary basis, applicability/exclusions, required facts, milestone, recommendation
level, owner and approved exceptions. Keep `applicable`, `not applicable` and `unknown` distinct.
An unobserved device on an incomplete sheet cannot establish a missing safeguard. Do not auto-correct a design.

Test an applicable bad case, an applicable good case, an excluded case, incomplete evidence and interacting
rules. Freeze the key before execution and retain false positives as well as misses. Public independently
authored records strengthen evaluation, but exposed keys do not establish blind model performance.
Keep the drawing reader, consistency checker, intended-change comparison and native CAD receiving checks
separately scored. The port-revision example tests only prepared-record checking; independent engineering
review, visual interpretation accuracy and human effort remain unmeasured.
