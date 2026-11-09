# What the engineering foundations unlock

The goal is an organization that can explain its decisions, coordinate work and learn from results. Engineers
should inherit the evidence and reasoning behind a plant or project, make a useful reviewed contribution, and
leave it in a maintained company record. A chatbot, graph or internal endpoint is one part of that capability.

This repository is an on-ramp to that maintained foundation. A maintenance
investigation, drawing review or record cleanup should solve today's job while
leaving evidence and structure the organization can reuse. When continued
reliance needs managed maintenance, auditability and single-source-of-truth
controls, the foundation should carry into **ChangePilot or another suitable
company tool**. Tool selection can follow the work and the operating need.

Here **single source of truth (SSOT)** means explicit authoritative homes and
owners for records and accepted facts, with derived views traceable to the
applicable versions. The CMMS may own work-order status, document control the
released drawing, and a reviewed context record the sourced interpretation and
decision. Define how these fit together, who resolves disagreement, and which
accepted version people may rely on.

From the first job, retain a handoff basis:

- Scope, asset identities and reviewed source-system crosswalks.
- Original evidence or permitted references, revisions, locators and provenance.
- Findings, accepted interpretations, unresolved conflicts and review/decision history.
- Authoritative record locations, accountable owners and receiving responsibilities.
- Dependencies, revision triggers and the agreed refresh/review procedure, including manual steps.
- Portable outputs, destination mappings, known omissions and receiving readback checks.

Record what is actually supplied or unknown in that basis. A named local reviewer
does not establish authenticated approval. A snapshot does not establish an
operated refresh service. The existing [record lifecycle](CONTEXT_LIFECYCLE.md)
owns those distinctions. No implemented ChangePilot import or live synchronization
is claimed here; qualify the chosen receiving route. Assess improvements by the
useful job completed **and** the reusable, maintainable foundation it leaves.

[![Six engineering capability layers, their benefits, cross-cutting controls and managed-product handoff](../assets/engineering-foundation.svg)](../assets/engineering-foundation.png)

[Editable SVG](../assets/engineering-foundation.svg) · [Shareable PNG](../assets/engineering-foundation.png)

This is a **capability roadmap, not a mandatory installation sequence or a single-product feature stack**.
Start with approved records, one question and human review. That path can produce value before a graph,
retrieval index or MCP server exists. Ownership, access, provenance, uncertainty and validation apply from the
first pilot and continue through every layer. The layers describe intended capabilities, not measured benefits.

## What each layer unlocks

| Foundation or capability | What becomes possible | Evidence needed before relying on it |
|---|---|---|
| **1. Controlled sources and observations** | Find and reconstruct the basis of an engineering claim. | Retained originals or permitted source snapshots; document IDs/revisions/locators, owners and approved access. Operating observations also need time, quality, units and mode. |
| **2. Shared engineering meaning** | Connect records about the same equipment, process or requirement. | Reviewed identities and aliases, typed relationships, units, site scope and explicit unknowns. A matching tag alone is insufficient; a graph is one representation. |
| **3. Maintained context and decisions** | Preserve why something was believed or changed, who owns it, and what should reopen on revision. | Source-linked claims, decision/ownership history, declared dependencies, company acceptance and a maintained refresh/review route. |
| **4. Authorized access and evidence retrieval** | Give people and approved assistants the relevant, permitted context for a job. | Correct source/version selection, authorization before disclosure, useful evidence locations, explicit missing/conflicting records and tested access withdrawal. |
| **5. Engineer-reviewed workflows** | Reuse onboarding, investigations, calculations and draft-generation methods. | Declared inputs and versions, appropriate validation, review of the result and an authorized receiving process. A draft or completed script is not a company release. |
| **6. Execution evidence and outcome learning** | Compare intent with what was actually done, assess results and improve future decisions. | Authorized execution/configuration records, qualified observations and an effectiveness review. A recommendation or completed-task flag alone does not establish success or causation. |

The arrows back matter. An investigation can expose a source error; propose a correction through its owner.
Reviewed execution and observations become new evidence. Preserve the previous source and decision basis while
the responsible reviewers establish what now applies. Do not silently overwrite a drawing of record to match
a generated model or infer that a shared template was adopted at every site.

## The managed-product handoff line

**Hand over service operations when other people rely on this context staying current, permission-correct and
traceable, and the current company arrangement cannot sustainably provide that.**

For a bounded assignment, a named publisher, reviewer and backup can use these tools with existing company
records and approvals. As the result becomes a continuing dependency for other teams, the obligation changes:
someone must operate access, publication, revision handling, conflicts, recovery and support after the original
author moves on. Avoid quietly turning a collection of personal scripts into that business-critical service.

| Situation | Practical decision |
|---|---|
| One bounded investigation; existing company controls and owners are adequate | Keep the simple tool/manual/approved-Copilot route. Preserve the contribution and review history. |
| Other teams repeatedly depend on the context, and reliable changes/access/review require unsupported manual coordination | Evaluate a managed product or an appropriately supported existing company service before widening reliance. |
| Required access, approved history, revision identity or conflict handling cannot be maintained | Contain the affected path and restore an authorized company review route. Involve the service owner/product architects before relying on it again. |

The company keeps engineering judgment and approval authority. The product takes on a **defined service
responsibility**, demonstrated in a bounded receiving trial. Existing company platforms may already satisfy it;
a new purchase is not a requirement of this roadmap. The [scaling guide](SCALING_ENGINEERING_CONTEXT.md) provides
specific small-team, site and global failure signals and service-evaluation criteria.

The handoff should carry scope and identity mappings, source IDs/revisions/locators, permitted retained evidence,
reviewed facts and uncertainties, decisions and owners, dependencies, access requirements and the proposed
refresh/acceptance route. Have the receiving owner read these back, then exercise a source revision, conflicting
proposal, revoked access, interrupted delivery and complete export. These company trials have not been run here.

## One product does not need to own the whole engineering graph

A process/operations-focused product can maintain the **operations-relevant context and decisions** while
engineering and business systems retain their own responsibilities. For example, an equipment investigation
may depend on selected drawing facts, a vendor limit, a maintenance event and operating observations. Preserve
the permitted, version-bound basis for that decision and its provenance; a live URL alone can lose its meaning
when the target, revision or access changes. That does not require importing every CAD object or design calculation.
A complete P&ID-derived process graph may fit this scope. The boundary is engineering meaning and responsibility,
not an arbitrary node count: maintaining a process model does not require becoming the owner of every engineering system.

| Responsibility | Recommended ownership boundary |
|---|---|
| Released drawings, detailed engineering models, specifications and design calculations | Their engineering/document/PLM owners and systems remain authoritative. Retain reviewed references or declared projections for the operational job. |
| Process/operations interpretations, investigations, decisions and their evidence dependencies | A company-approved process/ops context service can maintain this declared scope, with review, uncertainty, history and source-change handling. |
| Work orders, change releases and execution status | The system assigned authority for each record keeps it. Link actual receiving/execution records rather than inventing a second approval or completion status. |
| Generation and analysis | Tools consume supported, selected inputs and return drafts, checks and receipts to the responsible review route. An adapter must preserve or report unsupported fields. |

Keep as-designed, as-installed and as-operated claims distinct where they differ. Return an engineering change
proposal to its owner rather than letting an operations interpretation rewrite the design master. Expand into
another engineering domain when recurring work justifies it and domain owners can validate the meaning,
permissions, receiving behavior and continuing support. A generic graph alone does not supply that expertise.

## Teach RAG now; defer the infrastructure until there is a job for it

**Retrieval-augmented generation (RAG)** retrieves relevant information and supplies it to a language model as
context for a generated response. A company implementation must select permitted content; users still need to
check whether the source actually supports the answer. Microsoft's
[RAG overview](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview) describes
retrieval, limited model context and access-control concerns. The concept helps a reader understand what an
approved Copilot or future context product is doing without requiring them to build a retrieval platform.

| Term | Job | What it does not establish |
|---|---|---|
| Search or structured lookup | Find relevant text or exact records. | That the record is current, authoritative or sufficient for the decision. |
| Knowledge graph | Represent identities, relationships and sourced claims. | A graph export alone is not an implemented GraphRAG pipeline. |
| RAG | Use retrieved information to help generate an answer or draft. | Source truth, access enforcement, engineering approval or automatic document maintenance. |
| MCP | Connect a client to declared tools/resources. | A retrieval index, company identity service, RAG implementation or permission to cross IT/OT boundaries. |

A simple learning exercise is: select permitted evidence, ask a bounded question, inspect its references,
separate source statements from inference, and return a draft or missing-evidence request to a reviewer.
Preserve the source revision and rationale in the company record. Microsoft's
[grounding guidance](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-prompt-engineering)
explains the role of source metadata, citations and missing/conflicting information; prompt instructions still
need validation and cannot enforce permissions.

Teach that distinction here. Leave embeddings, chunk sizes, index products and retrieval orchestration for an
approved implementation with a real workload. Keyword search, exact queries or selected documents may be enough.
Any future RAG deployment needs separate retrieval/answer evaluations, including source versions, citation
support, access refusal/revocation, insufficient evidence and reviewer effort. No RAG pipeline or RAG evaluation
result is supplied by this toolkit. Introducing the concept does not change that implementation boundary.

## What is available here, and what remains company integration

The toolkit provides local source/model intake, graph exports, question screens, review/history mechanisms and
generation/analysis tools through their [documented contracts](WORKFLOWS.md). The local context register requires
explicit refresh. The [MCP starter](../examples/internal-mcp/README.md) reads selected startup snapshots; its
metadata lookup is not a document-search or RAG backend and it has no company authentication. These mechanisms
teach selected parts of the roadmap, rather than completing every layer or operating a shared company service.

Company acceptance, authenticated publication, maintained connectors and a verified operational outcome loop
remain integration work. Controlled documents, work orders and operating data can stay in their existing systems.
Use approved exports, replicas or local-only work where required; the roadmap requires no new OT network path
or cloud processing. See [connectivity](INTERNAL_CONNECTIVITY.md) for the actual choices and boundaries.
