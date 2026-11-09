# Learn from engineering platforms before adding more features

Reviewed **2026-11-08**, prompted by [Semodia's Flow2MTP-in-Entellia walkthrough](https://www.linkedin.com/posts/entellia-engineeringintelligence-processengineering-ugcPost-7523640872480120832-YcG_/),
shared as [this short link](https://lnkd.in/p/gSABYEmr). The public post describes a condensed progression
from process description through drawings and automation information to module-package outputs. We read
the post and linked product material; no vendor software, generated package or complete video workflow was tested.

## The overlap is real

These are first-party product descriptions, not independent capability or accuracy measurements.
This small survey establishes overlapping offerings; it does not measure growth in competitor count,
market size, price, implementation effort or willingness to pay.

| Offering and primary source | Advertised overlap | Decision for this toolkit and a consulting assignment |
|---|---|---|
| [Entellia](https://semodia.com/en/entellia/) and [Flow2MTP](https://flow2mtp.com/) | Connected engineering models, process/automation handoffs, reusable module descriptions and brownfield workflows. | Ask whether the client's job fits an existing engineering workflow. A generic graph, brownfield label or reusable template is not an exclusive advantage. |
| [Cognite contextualization](https://www.cognite.com/en/contextualization) | Linking drawings, equipment records, observations and other industrial information. | A maintenance context graph overlaps an established platform category. Compare the actual source preparation, identity corrections, receiving work and continuing ownership needed for the client's job. |
| [Siemens Eigen Engineering Agent](https://www.siemens.com/en-gb/products/tia-portal/eigen-engineering-agent/) | An assistant connected to a TIA Portal engineering project. | Assistant access to engineering context is already a product direction. An existing licensed environment may be the right destination for the work. No toolkit integration with this product is established. |
| [Flowstead](https://github.com/HazemMancy/Flowstead) on DWSIM | Open-source numerical simulation with a browser interface. | An adjacent calculation tool that could complement source preparation and review. [One limited browser observation and the numerical handoff lessons](PROCESS_ANALYTICS.md#lessons-from-flowstead-accessible-calculations-with-a-retained-basis) are retained; no toolkit simulator adapter is implemented. |

[Semodia's Flow2MTP subscription SLA](https://semodia.com/en/service-level-agreement-flow2mtp-en/)
separately scopes project engineering, migration, integration and consulting, and calls for professional
review of generated engineering material. Its [PAVIS partnership](https://flow2mtp.com/) also offers
engineering services. Thus neither human review nor consulting is an uncontested market gap.
The SLA distinguishes standard subscription scope; it does not mean those services are unavailable.

### Flowstead: distinguish the calculation from the unfinished plant job

The additional short link [gXuMHZsU](https://lnkd.in/p/gXuMHZsU) resolves to
[Hazem ElMancy's 2026-11-06 browser launch post](https://www.linkedin.com/posts/hazemmancy_processengineering-chemicalengineering-processsimulation-share-7524462037176074240-LHoB/),
already assessed in the [calculation review](PROCESS_ANALYTICS.md#lessons-from-flowstead-accessible-calculations-with-a-retained-basis).
It advertises a free, account-free browser tool, editable DWSIM files and browser-path benchmarks.
Those are the author's claims; our [single desktop observation](../examples/external-simulator-review/flowstead/README.md)
does not establish mobile usability, file interoperability, privacy or the entire benchmark suite.

The commercial implication is a hypothesis to test: a client with a suitable free or already licensed
calculator may still need help establishing the installed equipment, reconciling source revisions,
selecting defensible inputs and getting a reviewed result back into its working records. Ask which of
those steps is actually unfinished and funded. Do not quote a simulator build or sell access to a free
tool when the client's problem is source preparation or receiving verification. Specialist numerical
review is a separate scope requiring the relevant competence and validation basis.

Use the same lesson for maintenance and drawing jobs: deliver one inspectable finding before proposing
a platform, and leave the recipient an editable, source-bound package. The
[first-result trial](DELIVERY_ROADMAP.md#measure-the-whole-first-result) defines the remaining access,
portability and effort checks; no new browser intake or simulator integration is implied.

## Moshe Baum: keep generated components useful for the engineer who edits them

Inspected **2026-11-09 UTC**: [Moshe Baum's Claude-to-CAD account](https://www.linkedin.com/posts/moshebaum_ive-been-experimenting-with-claude-to-cad-share-7525400010524590081-dP56/),
shared as [gtXsdiEP](https://lnkd.in/p/gtXsdiEP). He reports repeated correction,
slow browser interaction and difficulty taking over generated CAD. These are
one practitioner's observations, not measured toolkit/vendor comparisons or
proof of universal limits on AI reasoning or creativity. No model or CAD session
from the post was reproduced here.

There is an important technical distinction. [Onshape's FeatureScript introduction](https://cad.onshape.com/FsDoc/intro.html)
explains that native feature operations also have FeatureScript representations.
Thus script use alone does not distinguish an opaque result from an editable
parametric model. Qualify the actual feature/parameter structure and receiving
behavior. The [official API documentation](https://onshape-public.github.io/docs/)
provides a structured integration route; its existence does not demonstrate
speed, correctness or an implemented toolkit connector.

The discussion links to [Aaddrick Williams's scene-testing account](https://aaddrick.com/blog/testing-blender-scenes-built-by-llm-agents).
Its useful methodological lesson is to check the evaluated artifact, challenge
the check with planted defects, and bind results to the delivered file/spec.
Its own reported checker errors and unfinished final-file checks matter too.
No Blender thresholds, physics results or code are adopted for plant engineering.

Apply these lessons to the [shared map and component-view design](ENGINEERING_FOUNDATION.md#human-editable-components-and-retained-corrections):

| Design requirement for this toolkit | Observable acceptance for a future component adapter |
|---|---|
| Deliver an editable basis at the granularity the engineer needs | Change one declared field, relationship or parameter using the chosen receiving route; retain unrelated content and reproduce the changed draft. Qualify parametric behavior separately when claimed. |
| Prefer bounded, inspectable operations | Map one selected engineering change into the existing generator or a qualified structured tool route; retain commands, versions and failures. Use UI checks where they test behavior not established by the structured route. |
| Carry applicable corrections between sessions | A fresh process receives the same scoped correction/rule record and reproduces the retained failing case. The record includes provenance, applicability and the counterexample; it is supplied context, not a model-training claim. |
| Check delivered results independently of their descriptions | Read actual output fields/relationships and, where relevant, evaluated geometry or native edits. Wrong units, endpoints, stale files and lost records must fail fixed checks. A render and a successful script exit are insufficient. |
| Establish benefit on the whole task | Compare preparation, retries, review, manual correction and receiving against the same job done through the existing route. Software wall time alone cannot establish engineer time saved. |

Start with a bounded draft from known context and requirements. Do not replace
the missing map-to-generator projection with another general mechanical-CAD
research campaign. Existing [CAD qualification failures](CAD_QUALIFICATION.md)
remain failures; no Onshape/FeatureScript adapter or new native-editability
qualification is established by this source review. Human benefit remains an
open measurement in the [delivery roadmap](DELIVERY_ROADMAP.md).

## Ideas worth applying now

1. **Show one unit accumulating useful information.** Follow stable asset IDs from an original record to
   an interpreted drawing/model, an explicit review decision, the recipient's handoff and its next revision.
   Show the input and output of each step, preparation and corrections included. The toolkit's
   [engineering-change example](../examples/engineering-change/README.md) already connects several of these
   steps. Its source and interpretation are fictional; it is not a full process-to-automation application.
2. **Describe behavior as well as connections.** A route through a graph does not establish what a unit
   should do. For an agreed automation handoff, record the requested function, boundary, modes, signals,
   operating constraints and unresolved questions from their own sources. Use the
   [manual handoff worksheet](../examples/consulting-start/AUTOMATION_HANDOFF.md); it adds no generated logic.
3. **Keep requirements, supplier statements and receiving evidence separate.** What an owner requests,
   what a supplier says is implemented and what a receiving check demonstrates are different records.
   Reconcile them by requirement ID, retaining partial and unverifiable returns. The existing
   [markup review](PID_MARKUP_REVIEW.md) already uses this request/return discipline for drawings.
4. **Reuse a pattern only after checking applicability.** A prior pump or skid package is a candidate
   starting point. Record its version, service, exclusions, changed assumptions and reviewer for the new
   application. Similar symbols or asset names cannot establish compatible operation or safeguards.
5. **Choose the receiver before an export.** Ask for the actual tool/version, required information and
   an accepted sample. Define the import/readback and next-revision check before promising a file format.
   [CAD qualification](../examples/cad-handoff/README.md), DEXPI exchange and MTP integration each need
   their own acceptance evidence. Success on one does not qualify another.

### MTP is a specific integration choice

Flow2MTP distinguishes an owner's requested module behavior (rMTP) from a supplier's module description
(MTP). That distinction is useful for an ordinary requirements/handoff review too; using the worksheet
does not create either package or establish standards conformance.

Check the actual receiving version. [PI's official MTP page](https://www.profibus.com/technologies/mtp)
lists MTP Specification 2.0, and its [release announcement](https://www.profibus.com/newsroom/press-news/profibus-profinet-international-publishes-mtp-specification-20)
is dated January 2026. Flow2MTP's inspected page still describes a 2025 release as current.
Use the standards publisher and the target implementation to settle versions, rather than copying a
marketing page into an exchange contract. We inspected public descriptions, not the normative specification.
No MTP/rMTP generator, validator, PLC deployment or qualified standards adapter is supplied here.

## Plant as Code: preserve common identities without inventing a common format

On 2026-11-09 UTC, the earlier short link
[gQ4Gb26t](https://lnkd.in/p/gQ4Gb26t) was resolved to
[Davy Demeyer's Plant as Code post](https://www.linkedin.com/posts/demeyerdavy_first-plant-with-the-new-plant-as-code-pac-ugcPost-7524024318847254528-XpQw/).
It describes combining engineering formats, an autonomous two-train example,
rework and paid proofs of concept, while saying a proposed combined-format
repository is being prepared. We inspected the public post, not its files,
simulations or customer engagements. Reported scale and commercial claims remain
the author's statements, not evidence of toolkit capability or market demand.

Apply the useful lessons here: retain exact scoped identities across selected
records, make unsupported content visible, validate before accumulating dependent
outputs, and exercise the recipient's next revision. The
[foundation handoff](FOUNDATION_HANDOFF.md) tests that bounded software route with
existing contracts. The existing DEXPI route remains separately scoped. No PaC,
IFCX, CFIHOS or BatchML adapter, whole-plant generation or specification equivalence
is implemented. A future adapter needs a released version, permitted source
examples and a real receiving contract before adoption. Reusing a file-format
name or producing a large package is insufficient.

## Trace the lessons through existing evidence

The existing attempt ledger and feature registry remain authoritative. This is
source navigation, not another capability catalog:

- [Johannes Van Opstal's structured P&ID experiment](PID_RULES_RESEARCH.md), shared
  as `ggsbnBw7`: A352 and the registered port/markup checkers implement selected
  prepared-record consistency checks. General design rules and complete reader
  correctness remain unimplemented/unqualified; JSON alone is no guarantee.
- [Maetee Lorprajuksiri's cross-sheet example](PID_GRAPH_QUESTIONS.md), `gmVa2TTE`:
  A354 implements qualified paths, disputed associations and revision comparisons.
  Complete line/valve registers and operating consequence inference remain outside
  that route.
- [Semodia's connected-engineering walkthrough](#the-overlap-is-real), `gSABYEmr`:
  A356 supplies the primary-source comparison and manual automation handoff.
  MTP generation and platform superiority are not implemented or measured.
- [Flowstead's browser launch](#flowstead-distinguish-the-calculation-from-the-unfinished-plant-job),
  `gXuMHZsU`: A357 retains one limited browser calculation and a manual review
  worksheet. Simulator integration, mobile suitability and whole-suite accuracy
  are unqualified.
- The PaC source above is now explicitly retained under A397. The portable
  foundation implementation/evidence is A396. The earlier attribution gap does
  not establish that all lessons were already incorporated.
- [Moshe Baum's generation/editing account](#moshe-baum-keep-generated-components-useful-for-the-engineer-who-edits-them),
  `gtXsdiEP`: A399 adds component-design acceptance requirements and primary
  FeatureScript/API clarification. It implements no new generator, memory system
  or CAD connector and does not close the existing native qualification failures.

N052 (human review timing), N062 (real organizational usefulness) and N063
(authorized company receiving and next change) stay open in `docs/TRIED.md`.
Managed notifications remain a product/integration decision in the
[delivery roadmap](DELIVERY_ROADMAP.md), with no new alert service here. Do not
treat documented advice, an exposed software example, independent review and a
company-accepted result as interchangeable.

## A consulting offer to test against the alternatives

Lead with the client's stalled job: **reconcile the selected records or check a consultant's return,
then hand back an actionable correction package in the client's existing workflow.** The
[bounded paid review](WORK_WITH_ME.md) already supplies the scope, price-preparation and receiving forms.
An automation requirements review is an optional scoped extension, not a prerequisite for that first job.

Before quoting, identify the existing tool, internal team or service provider that could do the work.
Ask what remains undone, why, and who would fund an outside contribution. Buying an established product,
using an existing license or partnering with a specialist may solve the job better than additional toolkit code.
This is a positioning hypothesis; no competitive win, customer demand or cost advantage is established.

Deepen the first paid workflow before expanding the format list: source-to-finding reconstruction,
engineering interpretation coverage, correction receiving/readback, the next revision and total human effort.
Use the [vendor-evaluation kit](../examples/vendor-evaluation/README.md) where its documented drawing task
applies. Score the same permitted inputs, coverage and deliberately wrong controls; measure preparation,
review and receiving work too. A drawing-reader score cannot compare whole platforms or prove MTP quality.

Add a standards adapter or maintained product capability when an actual receiving job requires it and has
a testable acceptance case. The open-source toolkit remains useful for self-service preparation and review
when the recipient ultimately chooses another vendor's platform.
