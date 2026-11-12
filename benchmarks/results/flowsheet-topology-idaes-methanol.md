# Task results: flowsheet-topology-idaes-methanol

Task: `flowsheet-topology`. A419. Development: the no-recycle flowsheet (v0 = workflow as on main 9ba93ccc; v1 = the frozen A419 contract). Held out: the recycle flowsheet, one sealed run of three replicates of v1 after the method was committed. Same-family model only (Claude); one publisher.

Only rows with the same cohort are directly comparable. See JSON for exact cases, failures, fingerprints and configurations.

## Key controls (connection and unit F1 for answers built from the key alone)

The reference is the key written as a native model and must score 1.000; reversed, shuffled and empty are deliberately wrong and must stay at or below the wrong-control bar of the scorer.

| Case | Control | Units F1 | Boundaries F1 | Connections F1 |
|---|---|---|---|---|
| methanol-no-recycle | reference | 1.000 (7/7 key, 7 given) | 1.000 (4/4 key, 4 given) | 1.000 (10/10 key, 10 given) |
| methanol-no-recycle | empty | 0.000 (0/7 key, 0 given) | 0.000 (0/4 key, 0 given) | 0.000 (0/10 key, 0 given) |
| methanol-no-recycle | reversed | 1.000 (7/7 key, 7 given) | 1.000 (4/4 key, 4 given) | 0.000 (0/10 key, 10 given) |
| methanol-no-recycle | shuffled | 1.000 (7/7 key, 7 given) | 1.000 (4/4 key, 4 given) | 0.300 (3/10 key, 10 given) |
| methanol-recycle | reference | 1.000 (9/9 key, 9 given) | 1.000 (4/4 key, 4 given) | 1.000 (13/13 key, 13 given) |
| methanol-recycle | empty | 0.000 (0/9 key, 0 given) | 0.000 (0/4 key, 0 given) | 0.000 (0/13 key, 0 given) |
| methanol-recycle | reversed | 1.000 (9/9 key, 9 given) | 1.000 (4/4 key, 4 given) | 0.077 (1/13 key, 13 given) |
| methanol-recycle | shuffled | 1.000 (9/9 key, 9 given) | 1.000 (4/4 key, 4 given) | 0.308 (4/13 key, 13 given) |

## Each answer beside its own wrong controls and the naive baseline

Reversed and shuffled corrupt the streams of the answer itself (wrong controls); mention-order chain links the units of the answer in the order the source first cites them (a naive method to beat, not a wrong answer).

| Run | Case | Status | Units F1 | Connections F1 | Reversed | Shuffled | Mention-order chain |
|---|---|---|---|---|---|---|---|
| dev-v0-r1 | methanol-no-recycle | failed | 0.000 (0/7 key, 0 given) | 0.000 (0/10 key, 0 given) | n/a | n/a | n/a |
| dev-v0-r2 | methanol-no-recycle | failed | 0.000 (0/7 key, 0 given) | 0.000 (0/10 key, 0 given) | n/a | n/a | n/a |
| dev-v0-r3 | methanol-no-recycle | failed | 0.000 (0/7 key, 0 given) | 0.000 (0/10 key, 0 given) | n/a | n/a | n/a |
| dev-v1-r1 | methanol-no-recycle | ok | 1.000 (7/7 key, 7 given) | 0.947 (9/10 key, 9 given) | 0.000 (0/10 key, 9 given) | 0.105 (1/10 key, 9 given) | 0.211 (2/10 key, 9 given) |
| dev-v1-r2 | methanol-no-recycle | ok | 1.000 (7/7 key, 7 given) | 0.462 (3/10 key, 3 given) | 0.000 (0/10 key, 3 given) | 0.154 (1/10 key, 3 given) | 0.105 (1/10 key, 9 given) |
| dev-v1-r3 | methanol-no-recycle | ok | 1.000 (7/7 key, 7 given) | 0.462 (3/10 key, 3 given) | 0.000 (0/10 key, 3 given) | 0.154 (1/10 key, 3 given) | 0.105 (1/10 key, 9 given) |
| heldout-v1-r1 | methanol-recycle | ok | 0.875 (7/9 key, 7 given) | 0.353 (3/13 key, 4 given) | 0.000 (0/13 key, 4 given) | 0.235 (2/13 key, 4 given) | 0.087 (1/13 key, 10 given) |
| heldout-v1-r2 | methanol-recycle | ok | 0.875 (7/9 key, 7 given) | 0.353 (3/13 key, 4 given) | 0.000 (0/13 key, 4 given) | 0.235 (2/13 key, 4 given) | 0.087 (1/13 key, 10 given) |
| heldout-v1-r3 | methanol-recycle | ok | 0.875 (7/9 key, 7 given) | 0.353 (3/13 key, 4 given) | 0.000 (0/13 key, 4 given) | 0.235 (2/13 key, 4 given) | 0.174 (2/13 key, 10 given) |

| Model / version | Method / interface | Family / split / evidence | Cohort | Cases | Replicates | Metric | Mean F1 | Min–max | SD |
|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / held-out / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES); the held-out input contains the development input verbatim (its first 69 lines) plus the recycle paragraphs, so held out means a held-out key and the recycle text | 2377423500cb | 1 | 3 | units | 0.8750 | 0.8750–0.8750 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / held-out / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES); the held-out input contains the development input verbatim (its first 69 lines) plus the recycle paragraphs, so held out means a held-out key and the recycle text | 2377423500cb | 1 | 3 | boundaries | 1.0000 | 1.0000–1.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / held-out / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES); the held-out input contains the development input verbatim (its first 69 lines) plus the recycle paragraphs, so held out means a held-out key and the recycle text | 2377423500cb | 1 | 3 | connections | 0.3529 | 0.3529–0.3529 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / held-out / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES); the held-out input contains the development input verbatim (its first 69 lines) plus the recycle paragraphs, so held out means a held-out key and the recycle text | 2377423500cb | 1 | 3 | internal | 0.0000 | 0.0000–0.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | units | 1.0000 | 1.0000–1.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | boundaries | 0.8571 | 0.8571–0.8571 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | connections | 0.6235 | 0.4615–0.9474 | 0.2805 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (A419 contract: source-named equipment kept, order-based connections recorded as assumptions, mixer outline stated) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | internal | 0.3333 | 0.0000–1.0000 | 0.5774 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (contract before A419) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | units | 0.0000 | 0.0000–0.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (contract before A419) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | boundaries | 0.0000 | 0.0000–0.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (contract before A419) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | connections | 0.0000 | 0.0000–0.0000 | 0.0000 |
| claude-opus-5-5 / served id from CLI modelUsage; build not provider-attested | description_workflow.py packet (contract before A419) answered with no tools, check diagnostics returned up to 4 rounds, then build / claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty temporary folder, --strict-mcp-config, --disable-slash-commands | idaes-methanol / development / Third-party flowsheet code keys third-party prose; same author and notebook, one publisher (IDAES) | 81bd1570b5c2 | 1 | 3 | internal | 0.0000 | 0.0000–0.0000 | 0.0000 |

## Coverage and failures

- dev-v0-r1 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: methanol-no-recycle:failed.
  methanol-no-recycle missing_arcs: ["CO_FEED", "H2_FEED", "gas", "prod", "s02", "s03", "s04", "s05", "s06", "s07"].
- dev-v0-r2 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: methanol-no-recycle:failed.
  methanol-no-recycle missing_arcs: ["CO_FEED", "H2_FEED", "gas", "prod", "s02", "s03", "s04", "s05", "s06", "s07"].
- dev-v0-r3 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: methanol-no-recycle:failed.
  methanol-no-recycle missing_arcs: ["CO_FEED", "H2_FEED", "gas", "prod", "s02", "s03", "s04", "s05", "s06", "s07"].
- dev-v1-r1 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: none.
  methanol-no-recycle missing_arcs: ["gas"].
- dev-v1-r2 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: none.
  methanol-no-recycle missing_arcs: ["gas", "s02", "s03", "s04", "s05", "s06", "s07"].
- dev-v1-r3 (idaes-methanol / development): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-recycle; failed attempted answers: none.
  methanol-no-recycle missing_arcs: ["gas", "s02", "s03", "s04", "s05", "s06", "s07"].
- heldout-v1-r1 (idaes-methanol / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-no-recycle; failed attempted answers: none.
  methanol-recycle missing_arcs: ["gas", "s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09"].
  methanol-recycle unexpected_streams: ["S4"].
- heldout-v1-r2 (idaes-methanol / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-no-recycle; failed attempted answers: none.
  methanol-recycle missing_arcs: ["gas", "s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09"].
  methanol-recycle unexpected_streams: ["S-VAP"].
- heldout-v1-r3 (idaes-methanol / held-out): 1 cases in this family/cohort; suite total 2; suite-wide unattempted: methanol-no-recycle; failed attempted answers: none.
  methanol-recycle missing_arcs: ["gas", "s01", "s02", "s03", "s04", "s05", "s06", "s07", "s08", "s09"].
  methanol-recycle unexpected_streams: ["S-VAP"].

## Limits

- Compare only the same cohort and scoring contract; model identity is contributor-declared, not provider-attested.
- Each replicate pools counts over its cases; summary reports mean/range/stdev over replicates, not a significance test or winner.
- Missing/failed attempted answers score empty; unattempted cases remain visible and create different comparison cohorts.
- Public keys and retrospective registration do not establish blindness. Synthetic controls and corrected/development results are separate.
- Flowsheet topology grades coarse unit roles and directed unit-to-unit connections after a role-preserving alignment: no names, ports, conditions, stream identities or engineering correctness; two units of one role can be swapped unseen. The key is the flowsheet code, a model, not plant truth.
