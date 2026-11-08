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
