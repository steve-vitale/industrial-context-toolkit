"""Explicit offline test modes; never downloads, installs, or contacts a gateway.

Default/--full: all registered tests, using installed dependencies and cached TE data.
Includes a temporary OPC UA replay test service/client on 127.0.0.1 with an ephemeral port.
--source-only: stdlib and committed-fixture checks only; excludes that replay service
(NOT a full-suite pass).
--check-prerequisites: read-only preflight for the selected mode; does not run tests.
Exit codes: 0 selected checks pass, 1 test failure, 2 missing/invalid prerequisites.
"""
import argparse
import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TESTS = (
    "scripts/test_context_basis.py",
    "scripts/test_context_basis_compare.py",
    "scripts/test_context_intake.py",
    "scripts/test_context_identity.py",
    "scripts/test_context_components.py",
    "scripts/test_context_packet.py",
    "scripts/test_context_compact.py",
    "scripts/test_context_generator.py",
    "scripts/test_context_scope.py",
    "scripts/test_context_scope_identity.py",
    "scripts/test_context_scope_incremental.py",
    "scripts/test_context_review.py",
    "scripts/test_foundation_handoff.py",
    "scripts/test_maintenance_history.py",
    "scripts/test_score_maintenance_systems.py",
    "scripts/test_fetch_public_group.py",
    "scripts/test_pid_path_review.py",
    "scripts/test_pid_connections.py",
    "scripts/test_pid_markups.py",
    "scripts/test_maintenance_intake.py",
    "scripts/test_batch_analysis.py",
    "scripts/test_check_analysis_basis.py",
    "scripts/test_join_batch_records.py",
    "scripts/test_investigation_example.py",
    "scripts/test_benchmark.py",
    "scripts/test_source_support.py",
    "scripts/test_artifact_value_review.py",
    "scripts/test_display_contract.py",
    "scripts/test_process_mimic.py",
    "scripts/test_tiling.py",
    "scripts/test_apply_review.py",
    "scripts/test_review_identity.py",
    "scripts/test_scorer_controls.py",
    "scripts/test_pid2graph_synthetic_adapter.py",
    "scripts/test_dexpi_adapter.py",
    "scripts/test_dexpi_to_twin.py",
    "scripts/test_dexpi_reader.py",
    "scripts/test_source_evidence.py",
    "scripts/test_source_capture_mode.py",
    "scripts/test_source_handoff.py",
    "scripts/test_score_tags.py",
    "scripts/test_replicate_stats.py",
    "scripts/test_review_kit.py",
    "scripts/test_generate_validation.py",
    "scripts/test_export_review_boundaries.py",
    "scripts/test_site_drawing_intake.py",
    "scripts/test_site_extraction_workflow.py",
    "scripts/test_pi_mapping.py",
    "scripts/test_check_pi_export.py",
    "scripts/test_gateway_acceptance_preflight.py",
    "scripts/test_review_effort.py",
    "scripts/test_map_points.py",
    "scripts/test_run_tests.py",
    "scripts/test_pipeline.py",
    "scripts/test_bayer_rt.py",
    "scripts/test_check_claims.py",
    "scripts/test_rescore.py",
    "scripts/test_own_drawing_example.py",
    "scripts/test_loop_audit.py",
    "scripts/test_one_map.py",
    "scripts/test_map_explorer.py",
    "scripts/test_ontology.py",
    "scripts/test_plant_workflows.py",
    "scripts/test_context_map_format.py",
    "scripts/test_context_map.py",
    "scripts/test_sheet_from_prediction.py",
    "scripts/test_offpage_pairing.py",
    "scripts/test_pdf_tag_check.py",
    "scripts/test_ocr_tag_hints_score.py",
    "scripts/test_flow_direction_score.py",
    "scripts/test_loop_assembly.py",
    "scripts/test_extract_text.py",
    "scripts/test_evaluate_vendor.py",
    "scripts/test_drawing_case.py",
    "scripts/test_reader_template.py",
    "scripts/test_reader_external_kg.py",
    "scripts/test_reader_leaderboard.py",
    "scripts/test_script_index.py",
    "scripts/test_attempts_ledger.py",
    "scripts/test_vendor_neutral.py",
    "scripts/test_graph_export.py",
    "scripts/test_graph_provenance.py",
    "scripts/test_snapshot_packet.py",
    "scripts/test_knowledge_snapshot.py",
    "scripts/test_knowledge_capture.py",
    "scripts/test_feature_catalog.py",
    "scripts/test_corpus_matrix.py",
    "scripts/test_corpus_depth.py",
    "scripts/test_question_engine.py",
    "scripts/test_estimate_impact.py",
    "scripts/test_statements.py",
    "scripts/test_bound_statement_example.py",
    "scripts/test_context_register.py",
    "scripts/test_context_examples.py",
    "scripts/test_pump_revision.py",
    "scripts/test_team_context.py",
    "scripts/test_checkout_contracts.py",
    "scripts/test_deliverable_report.py",
    "scripts/test_fetch_corpus.py",
)
# These tests need cached data or third-party imports, even though none needs a gateway.
FULL_ONLY_TESTS = (
    "scripts/test_delivery_examples.py",
    "scripts/test_cad_handoff.py",
    "scripts/test_cad_projection.py",
    "scripts/test_receive_drawings.py",
    "scripts/test_drawing_resubmission.py",
    "scripts/test_cad_linux_evidence.py",
    "scripts/test_cad_exchange.py",
    "scripts/test_generate_any_model.py",
    "scripts/test_description_workflow.py",
    "scripts/test_engineering_change.py",
    "scripts/test_csv_tools.py",
    "scripts/test_te_channels.py",
    "scripts/test_along_line.py",
    "scripts/test_trace_connections_v2.py",
    "scripts/test_recheck_flagged.py",
    "scripts/test_scan_cleanup.py",
    "scripts/test_line_layers.py",
    "scripts/test_drawing_set_intake.py",
    "scripts/test_gateway_diff.py",
    "scripts/test_current_gateway_artifacts.py",
    "scripts/test_fault_detection_eval.py",
    "scripts/test_te_topology.py",
    "scripts/test_te_control_loops.py",
    "scripts/test_te_pid_roundtrip.py",
    "scripts/test_open100_structural.py",
    "scripts/test_loto_wording.py",
    "scripts/test_build_3d_scene.py",
    "scripts/test_verify_3d_render.py",
)
TESTS = SOURCE_TESTS + FULL_ONLY_TESTS
DEPENDENCIES = {"numpy": "numpy", "cv2": "opencv-python-headless",
                "asyncua": "asyncua", "cryptography": "cryptography", "PIL": "Pillow", "ezdxf": "ezdxf"}
TWIN = "out/twin/r2-tiles-trace/codex"
DRAWINGS = "data/external/pid2graph/PID2Graph/Complete/PID2Graph OPEN100"
SOURCE_FILES = (
    'examples/batch-analysis/investigation/README.md',
    'examples/batch-analysis/investigation/OWN-INPUT.md',
    'examples/batch-analysis/investigation/seed.knowledge.json',
    'examples/batch-analysis/investigation/INVESTIGATION-NOTES.md',
    'examples/batch-analysis/investigation/EXPECTATIONS.json',
    'examples/batch-analysis/investigation/SOURCE-LOCATORS.json',
    'examples/batch-analysis/investigation/REVIEW-TEMPLATE.md',
    'examples/batch-analysis/investigation/capture-template.json',
    'examples/batch-analysis/investigation/PROVENANCE.json',
    'examples/batch-analysis/investigation/reproduce.py',
    'examples/batch-analysis/investigation/worked/final/knowledge.json',
    'examples/batch-analysis/investigation/worked/final/handoff.md',
    "scripts/batch_analysis.py",
    "docs/PROCESS_ANALYTICS.md",
    "examples/batch-analysis/ACCEPTANCE.md",
    "examples/batch-analysis/README.md",
    "examples/batch-analysis/first-question.md",
    "examples/batch-analysis/observations.csv",
    "examples/batch-analysis/plan.json",
    "examples/batch-analysis/process_model.json",
    "examples/batch-analysis/graph.json",
    "examples/batch-analysis/expected/batch_analysis.json",
    "examples/batch-analysis/expected/batch_analysis.md",
    "examples/batch-analysis/history/a306/batch_analysis.json",
    "examples/batch-analysis/history/a306/batch_analysis.md",
    "examples/batch-analysis/semantics/ACCEPTANCE.md",
    "examples/batch-analysis/semantics/README.md",
    "examples/batch-analysis/semantics/observations.csv",
    "examples/batch-analysis/semantics/previous.plan.json",
    "examples/batch-analysis/semantics/linear.plan.json",
    "examples/batch-analysis/semantics/expected/previous/batch_analysis.json",
    "examples/batch-analysis/semantics/expected/previous/batch_analysis.md",
    "examples/batch-analysis/semantics/expected/linear/batch_analysis.json",
    "examples/batch-analysis/semantics/expected/linear/batch_analysis.md",
    "examples/batch-analysis/context-handoff/ACCEPTANCE.json",
    "examples/batch-analysis/context-handoff/README.md",
    "examples/batch-analysis/context-handoff/answer.recipe.json",
    "examples/batch-analysis/context-handoff/basis.json",
    "examples/batch-analysis/context-handoff/expected/partial/context.json",
    "examples/batch-analysis/context-handoff/expected/partial/enriched_graph.json",
    "examples/batch-analysis/context-handoff/expected/refreshed/context.json",
    "examples/batch-analysis/context-handoff/expected/refreshed/enriched_graph.json",
    "examples/batch-analysis/context-handoff/fictional-partial.csv",
    "examples/batch-analysis/context-handoff/questions.json",
    "examples/batch-analysis/context-handoff/readiness-review-template.csv",
    "examples/batch-analysis/context-handoff/readiness.json",
    "examples/batch-analysis/context-handoff/reproduce.py",
    "examples/batch-analysis/context-handoff/sources.linear.json",
    "examples/batch-analysis/context-handoff/sources.previous.json",
    "examples/batch-analysis/context-handoff/tool-basis.json",
    "examples/batch-analysis/public-distillation/ACCEPTANCE.md",
    "examples/batch-analysis/public-distillation/KEY.json",
    "examples/batch-analysis/public-distillation/PROVENANCE.json",
    "examples/batch-analysis/public-distillation/README.md",
    "examples/batch-analysis/public-distillation/expected/batch_analysis.json",
    "examples/batch-analysis/public-distillation/expected/batch_analysis.md",
    "examples/batch-analysis/public-distillation/reproduce.py",
    "examples/batch-analysis/public-distillation/source/anomaly-metadata.yaml",
    "examples/batch-analysis/public-distillation/source/operation-log.csv",
    "examples/batch-analysis/public-distillation/source/operation.csv",
    "examples/batch-analysis/public-distillation/source/plant-description.yaml",
    "examples/batch-analysis/public-distillation/source/settings.csv",
    "scripts/artifact_value_review.py",
    "benchmarks/source-support/artifact-values/EXPOSURE.json",
    "benchmarks/source-support/artifact-values/PROTOCOL.md",
    "benchmarks/source-support/artifact-values/README.md",
    "benchmarks/source-support/artifact-values/SOURCE-KEY-REVIEW.json",
    "benchmarks/source-support/artifact-values/SOURCE-ROLES.json",
    "benchmarks/source-support/artifact-values/admission-controls.json",
    "benchmarks/source-support/artifact-values/cases/false-shutdown/input-artifact.json",
    "benchmarks/source-support/artifact-values/cases/false-shutdown/input-v1-projection.json",
    "benchmarks/source-support/artifact-values/cases/false-shutdown/inventory.json",
    "benchmarks/source-support/artifact-values/cases/false-shutdown/model.json",
    "benchmarks/source-support/artifact-values/cases/false-shutdown/provided-values.csv",
    "benchmarks/source-support/artifact-values/cases/reference/input-artifact.json",
    "benchmarks/source-support/artifact-values/cases/reference/input-v1-projection.json",
    "benchmarks/source-support/artifact-values/cases/reference/inventory.json",
    "benchmarks/source-support/artifact-values/cases/reference/model.json",
    "benchmarks/source-support/artifact-values/cases/reference/provided-values.csv",
    "benchmarks/source-support/artifact-values/controls/A01-reference-valid/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A02-false-valid/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A03-stale-reference-inventory/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A03-stale-reference-inventory/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A03-stale-reference-inventory/key.json",
    "benchmarks/source-support/artifact-values/controls/A04-omitted-critical-entry/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A04-omitted-critical-entry/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A04-omitted-critical-entry/key.json",
    "benchmarks/source-support/artifact-values/controls/A05-duplicate-inventory-pointer/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A05-duplicate-inventory-pointer/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A05-duplicate-inventory-pointer/key.json",
    "benchmarks/source-support/artifact-values/controls/A06-extra-inventory-pointer/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A06-extra-inventory-pointer/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A06-extra-inventory-pointer/key.json",
    "benchmarks/source-support/artifact-values/controls/A07-boolean-numeric-typed-mismatch/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A07-boolean-numeric-typed-mismatch/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A07-boolean-numeric-typed-mismatch/key.json",
    "benchmarks/source-support/artifact-values/controls/A08-integer-float-typed-mismatch/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A08-integer-float-typed-mismatch/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A08-integer-float-typed-mismatch/key.json",
    "benchmarks/source-support/artifact-values/controls/A09-stale-source-bytes/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A09-stale-source-bytes/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A09-stale-source-bytes/key.json",
    "benchmarks/source-support/artifact-values/controls/A09-stale-source-bytes/source.txt",
    "benchmarks/source-support/artifact-values/controls/A10-wrong-source-quote/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A10-wrong-source-quote/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A10-wrong-source-quote/key.json",
    "benchmarks/source-support/artifact-values/controls/A11-wrong-locator-same-source/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A11-wrong-locator-same-source/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A11-wrong-locator-same-source/key.json",
    "benchmarks/source-support/artifact-values/controls/A12-critical-role-downgrade/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A12-critical-role-downgrade/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A12-critical-role-downgrade/key.json",
    "benchmarks/source-support/artifact-values/controls/A13-omit-critical-group-and-key/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A13-omit-critical-group-and-key/key.json",
    "benchmarks/source-support/artifact-values/controls/A13-omit-critical-group-and-key/v1_projection.json",
    "benchmarks/source-support/artifact-values/controls/A14-wrong-group-record-membership/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A14-wrong-group-record-membership/key.json",
    "benchmarks/source-support/artifact-values/controls/A15-CSV-missing-critical-row/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A15-CSV-missing-critical-row/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A15-CSV-missing-critical-row/key.json",
    "benchmarks/source-support/artifact-values/controls/A15-CSV-missing-critical-row/provided_values.csv",
    "benchmarks/source-support/artifact-values/controls/A16-CSV-duplicate-row/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A16-CSV-duplicate-row/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A16-CSV-duplicate-row/key.json",
    "benchmarks/source-support/artifact-values/controls/A16-CSV-duplicate-row/provided_values.csv",
    "benchmarks/source-support/artifact-values/controls/A17-CSV-foreign-record-identity/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A17-CSV-foreign-record-identity/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A17-CSV-foreign-record-identity/key.json",
    "benchmarks/source-support/artifact-values/controls/A17-CSV-foreign-record-identity/provided_values.csv",
    "benchmarks/source-support/artifact-values/controls/A18-missing-key-label/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A18-missing-key-label/key.json",
    "benchmarks/source-support/artifact-values/controls/A19-omitted-complementary-meta/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A19-omitted-complementary-meta/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A19-omitted-complementary-meta/key.json",
    "benchmarks/source-support/artifact-values/controls/A20-new-model-field-uninventoried/artifact.json",
    "benchmarks/source-support/artifact-values/controls/A20-new-model-field-uninventoried/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A20-new-model-field-uninventoried/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A20-new-model-field-uninventoried/key.json",
    "benchmarks/source-support/artifact-values/controls/A21-model-duplicate-JSON-key/artifact.json",
    "benchmarks/source-support/artifact-values/controls/A21-model-duplicate-JSON-key/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A21-model-duplicate-JSON-key/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A21-model-duplicate-JSON-key/key.json",
    "benchmarks/source-support/artifact-values/controls/A22-CSV-boolean-numeric-value/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A22-CSV-boolean-numeric-value/inventory.json",
    "benchmarks/source-support/artifact-values/controls/A22-CSV-boolean-numeric-value/key.json",
    "benchmarks/source-support/artifact-values/controls/A22-CSV-boolean-numeric-value/provided_values.csv",
    "benchmarks/source-support/artifact-values/controls/A23-changed-claim-prefix/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A23-changed-claim-prefix/v1_projection.json",
    "benchmarks/source-support/artifact-values/controls/A24-changed-claim-time/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A24-changed-claim-time/v1_projection.json",
    "benchmarks/source-support/artifact-values/controls/A25-changed-evidence-paraphrase/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A25-changed-evidence-paraphrase/v1_projection.json",
    "benchmarks/source-support/artifact-values/controls/A26-changed-evidence-source-context/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A26-changed-evidence-source-context/v1_projection.json",
    "benchmarks/source-support/artifact-values/controls/A27-mismatched-value-with-coherent-key-pin/input-artifact.json",
    "benchmarks/source-support/artifact-values/controls/A27-mismatched-value-with-coherent-key-pin/key.json",
    "benchmarks/source-support/artifact-values/controls/A27-mismatched-value-with-coherent-key-pin/v1_projection.json",
    "benchmarks/source-support/artifact-values/keys/false-shutdown-missing-critical.key-v1.json",
    "benchmarks/source-support/artifact-values/keys/false-shutdown.artifact-key.json",
    "benchmarks/source-support/artifact-values/keys/false-shutdown.key-v1.json",
    "benchmarks/source-support/artifact-values/keys/reference.artifact-key.json",
    "benchmarks/source-support/artifact-values/keys/reference.key-v1.json",
    "benchmarks/source-support/artifact-values/label-controls.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-all-contradicted.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-all-insufficient-evidence.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-all-supported.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-correct-label-poor-reason.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-empty.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-keyed-review.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-literal-unreviewed.json",
    "benchmarks/source-support/artifact-values/predictions/false-shutdown-missing-critical.json",
    "benchmarks/source-support/artifact-values/predictions/reference-all-contradicted.json",
    "benchmarks/source-support/artifact-values/predictions/reference-all-insufficient-evidence.json",
    "benchmarks/source-support/artifact-values/predictions/reference-all-supported.json",
    "benchmarks/source-support/artifact-values/predictions/reference-empty.json",
    "benchmarks/source-support/artifact-values/predictions/reference-keyed-review.json",
    "benchmarks/source-support/artifact-values/predictions/reference-missing-critical.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-correct-label-poor-reason.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-literal-unreviewed.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-all-contradicted.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-all-insufficient-evidence.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-all-supported.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-empty.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-keyed-review.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-false-shutdown-missing-critical.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-all-contradicted.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-all-insufficient-evidence.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-all-supported.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-empty.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-keyed-review.json",
    "benchmarks/source-support/artifact-values/runs/artifact-control-reference-missing-critical.json",
    "benchmarks/source-support/artifact-values/source.txt",
    "benchmarks/source-support/artifact-values/source_inventory.json",
    "benchmarks/source-support/artifact-values/suite.json",
    "scripts/knowledge_snapshot.py",
    "examples/engineering-onboarding/controls/ORDER-COMPANION-LOCAL-BEFORE-UNIQUENESS.json",
    "examples/engineering-onboarding/controls/ORDER-RECORD-BEFORE-LATE-LOCAL.json",
    "examples/engineering-onboarding/controls/ORDER-SAME-STAGE-RECORD-STEP-TIE.json",
    "examples/engineering-onboarding/controls/ORDER-STEP-BEFORE-LATE-LOCAL.json",
    "examples/engineering-onboarding/controls/capture-tamper.json",
    "examples/engineering-onboarding/controls/dependency-cycle.negative.json",
    "examples/engineering-onboarding/controls/duplicate-id.negative.json",
    "examples/engineering-onboarding/controls/excerpt-capture-tamper.json",
    "examples/engineering-onboarding/controls/memory-verified-contradiction.json",
    "examples/engineering-onboarding/controls/navigation-self-positive.json",
    "examples/engineering-onboarding/controls/owner-wrong-kind.json",
    "examples/engineering-onboarding/controls/record-vs-source-revision.json",
    "examples/engineering-onboarding/controls/required-companion-mismatch.negative.json",
    "examples/engineering-onboarding/controls/selected-document-mismatch.json",
    "examples/engineering-onboarding/controls/step-input-dangling.json",
    "examples/engineering-onboarding/controls/unknown-original-fake-hash.json",
    "examples/engineering-onboarding/controls/unknown-owner.negative.json",
    "examples/engineering-onboarding/controls/unsupported-relabel-structurally-valid.json",
    "examples/engineering-onboarding/controls/untrusted-source.positive-data-control.json",
    "examples/engineering-onboarding/controls/withdrawn-rejected-readable.json",
    "examples/engineering-onboarding/expected/A-READBACK.json",
    "examples/engineering-onboarding/expected/B-READBACK.json",
    "examples/engineering-onboarding/expected/C-READBACK.json",
    "examples/engineering-onboarding/knowledge-A.json",
    "examples/engineering-onboarding/knowledge-B.json",
    "examples/engineering-onboarding/knowledge-C.json",
    "scripts/drawing_case.py", "extraction/prompt.md", "examples/own-drawing/extraction_sheet0.json",
    *(f"examples/contribute-a-pid/{name}" for name in
      ("reproduce.py", "demo-suite.json", "runs/demo-suite-empty-control.json", "controls/open100-0-demo-empty.json",
       "results/demo-suite-1-cases.json", "results/demo-suite-1-cases.md", "open100-0-demo/case.json",
       "open100-0-demo/packet.json", "open100-0-demo/key.graphml", "open100-0-demo/key.draft.graphml",
       "open100-0-demo/review/sample-56456cda5c05.csv", "open100-0-demo/review/sample-24c2e079ea99.csv")),
    "scripts/source_evidence.py", "scripts/source_handoff.py", ".gitattributes", "NOTICE.md",
    *(f"examples/source-handoff/fixture/{name}" for name in
      ("I01V01-VER.EX01.xml", "embedded.model.json", "PROVENANCE.json", "EXPECTED.json")),
    *(f"examples/opportunity-screen/pump-motor-basis/{name}" for name in
      ("model.json", "questions.json", "screen.md", "README.md")),
    *(f"examples/opportunity-screen/source-investigation/{name}" for name in
      ("catalog.json", "questions.json", "screen.md", "README.md")),
    "examples/review-and-mapping/native-identity/model.json",
    "examples/review-and-mapping/native-identity/README.md",
    "examples/review-and-mapping/native-identity/review.csv",
    "examples/review-and-mapping/native-identity/expected/model.json",
    "examples/review-and-mapping/native-identity/expected/change_record.json",
    "examples/review-and-mapping/native-identity/expected/change_record.md",
    "data/te_process_model.json", "data/te_display_layout.json", "data/te_unit_purposes.json",
    "data/fixtures/water_utility_twin.json", "data/fixtures/water_utility_display.json",
    "data/dataset_adapters/pid2graph_synthetic.json", "data/dataset_adapters/dexpi_examples.json",
    "data/te_pid_layout.json", "data/te_pid/key.json", "data/te_pid/rev-a/key.json", "data/te_pid/rev-c/key.json",
    "data/te_control_loops.json", "examples/loop-audit/te_loops.csv", "data/script_index.json",
    "examples/one-map/inputs/site.json", "examples/graph-export/sheet0_graph.json",
    "examples/one-map/inputs/site-office.json", "examples/one-map/inputs/documents-office.json",
    "examples/one-map/make_office_docs.py", "examples/one-map/expected/office/report.md",
    "data/bayer_rt/process_model.json", "data/bayer_rt/fig11_calibration.json", "data/bayer_rt/fig11_digitized.csv",
    "out/bayer_rt/fig11_check.md", "scripts/digitize_bayer_fig11.py",
    "data/bayer_rt/fig10_inventory.json", "data/bayer_rt/pid/key.json", "out/bayer_rt/fig10_compare.md",
    *(f"examples/document-text/{name}" for name in
      ("make_samples.py", "measure_addons.py", "expected/manifest.json", "expected/CAPA-0042.html.txt",
       "expected/HACCP-plan-2019.doc.txt", "expected/PHA-node-review.pptx.txt", "expected/PM-plan-area-2.xlsx.txt",
       "expected/SOP-104-feed-pump-isolation.docx.txt", "expected/work-order-export.csv.txt")),
    "scripts/compare_bayer_fig10.py",
    "data/bayer_rt/replay_rules.json", "data/bayer_rt/replay.csv", "out/bayer_rt/replay_states.md",
    "scripts/bayer_replay.py",
    "data/bayer_rt/walkthrough_steps.json", "out/bayer_rt/fig11_check.json", "out/bayer_rt/walkthrough.md",
    "scripts/bayer_walkthrough.py",
    "data/te_tour_cards.json", "data/hazard_citations_prototype.json", "assets/fonts/AtkinsonHyperlegible-Regular.ttf",
    "drafts/3d-tour/label_boxes.json", "drafts/3d-tour/before/label_boxes.json",
    *(f"examples/plug-in-a-reader/{name}" for name in
      ("reader_output_sheet0.json", "prediction_sheet0.json", "manifest.json")),
    "examples/own-drawing/extraction_sheet0.json", "docs/PLUG_IN_A_READER.md", "benchmarks/LEADERBOARD.md",
    "benchmarks/registry.json", "examples/vendor-evaluation/report.json",
    *(f"data/te_pid/{s}.{e}" for s in ("101", "102", "103") for e in ("png", "graphml")),
    "out/ignition/gateway/twin_provider.json", "out/ignition/gateway/build_meta.json",
    "out/svg/overview.svg", f"{TWIN}/plant_model.json",
    "data/pi_builder_reference.json", "out/pi/pi_builder_af.csv", "out/pi/custom_uoms.csv",
    f"{TWIN}/pi/pi_builder_af.csv",
) + tuple(f"{TWIN}/svg/sheet_{i}.svg" for i in range(12)) + tuple(
    f"{DRAWINGS}/{i}.{extension}" for i in range(12) for extension in ("graphml", "png"))

# Committed files the full-mode tests read beyond SOURCE_FILES.
FULL_FILES = (*(f"examples/from-description/{case}/result/{name}" for case in ("assisted", "mgpi")
                for name in ("interpretation_review.csv", "source_coverage.csv")),
              "out/ignition/gateway/PIDTwin.zip", "data/te_control_loops.json", f"{TWIN}/ignition/tags.json",
              "out/open100_structural/flow_direction.json", "out/open100_structural/plant_structure.json",
              "out/open100_structural/mimic/views.json", "data/open100_direction_confidence.json",
              "data/open100_equipment_schedule.json", "docs/deliverables_matrix.json",
              "data/bayer_rt/pid_layout.json", "data/bayer_rt/pid/RT1.png", "data/bayer_rt/pid/RT1.graphml")


def prerequisites(root, source_only):
    """Check local files and module discovery only; never import third-party code."""
    issues = []
    scripts = SOURCE_TESTS if source_only else TESTS
    paths = SOURCE_FILES + scripts
    if not source_only:
        paths += FULL_FILES
    for relative in paths:
        path = root / relative
        if not path.is_file():
            issues.append(("source", f"missing committed file: {relative}"))
        else:
            try:
                with path.open("rb") as stream:
                    if not stream.read(1):
                        issues.append(("source", f"empty committed file: {relative}"))
            except OSError as error:
                issues.append(("source", f"unreadable committed file: {relative}: {error}"))
    if source_only:
        return issues
    for module, package in DEPENDENCIES.items():
        if importlib.util.find_spec(module) is None:
            issues.append(("dependency", f"missing Python module {module} (package {package})"))
    # This local stdlib module only defines download functions. Do NOT call main().
    # The full suite includes the 21-fault evaluation, so it needs the whole published set (fetch_te_data.py --all);
    # a missing file is a prerequisite failure, never a quietly skipped regeneration.
    import fetch_te_data
    for name, expected in {**fetch_te_data.FILES, **getattr(fetch_te_data, "EVALUATION_FILES", {})}.items():
        path = root / "data/external/te-braatz" / name
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            issues.append(("cache", f"missing/unreadable cached TE data: {path.relative_to(root)}: {error.strerror}"))
        else:
            if actual != expected:
                issues.append(("cache", f"checksum mismatch: {path.relative_to(root)}"))
    # The revised TE code (second source for the topology check). Stdlib module; importing it downloads nothing.
    from verify_te_topology import REVISED_SHA256
    path = root / "data/external/te-ricker/temexd_mod.zip"
    try:
        if hashlib.sha256(path.read_bytes()).hexdigest() != REVISED_SHA256:
            issues.append(("source-cache", f"checksum mismatch: {path.relative_to(root)}"))
    except OSError as error:
        issues.append(("source-cache", f"missing/unreadable revised TE code: {path.relative_to(root)}: {error.strerror}"))
    return issues


def report_remediation(issues):
    print("Separate setup/remediation steps (NOT executed by this runner):")
    kinds = {kind for kind, _ in issues}
    if "source" in kinds:
        print("  Restore the listed committed files from a complete checkout; do not overwrite local work blindly.")
    if "dependency" in kinds:
        print("  python -m pip install -r requirements.txt  # may access the network; use your chosen environment")
    if "cache" in kinds:
        print("  python scripts/fetch_te_data.py --all  # network download if cache is absent/invalid; verifies hashes")
    if "source-cache" in kinds:
        print("  python scripts/verify_te_topology.py  # downloads the revised TE code if absent; report only")
    print("  python scripts/run_tests.py --source-only  # narrower checks; NOT a full-suite pass")


def coverage_notices(stdout, stderr):
    """Read unittest summaries and explicit notices, not arbitrary prose containing the word 'skip'.

    Platform notices add reasons for unittest skips; they are reported separately, never added to its case count.
    Other SKIP lines describe extra checks/groups, whose granularity may differ from unittest cases. These are
    child-program reports, not independent proof that a test program attempted every intended check.
    """
    cases, platform, other = 0, [], []
    for line in (stdout + "\n" + stderr).splitlines():
        summary = re.fullmatch(r"(?:OK|FAILED)(?: \(([^)]*)\))?", line.strip())
        if summary and summary[1]:
            skipped = re.search(r"(?:^|,\s*)skipped=(\d+)(?:,|$)", summary[1])
            if skipped:
                cases += int(skipped[1])
        if line.startswith("SKIP [platform] "):
            platform.append(line[len("SKIP [platform] "):])
        elif line.startswith("SKIP "):
            other.append(line[5:])
    return cases, platform, other


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--full", action="store_true", help="full cached-data suite (default)")
    modes.add_argument("--source-only", action="store_true", help="stdlib and committed fixtures only; excludes the full-only scripts")
    parser.add_argument("--check-prerequisites", action="store_true", help="preflight only; no tests or setup actions")
    args = parser.parse_args(argv)
    label = "SOURCE-ONLY" if args.source_only else "FULL CACHED-DATA"
    print(f"Mode: {label}. No downloads, installs, or plant/gateway connections. Full tests include a temporary OPC UA replay service/client on 127.0.0.1 with an ephemeral port; source-only excludes it.")
    if args.source_only:
        print("Scope exclusions (not run): " + ", ".join(FULL_ONLY_TESTS))
    issues = prerequisites(ROOT, args.source_only)
    if issues:
        for _, reason in issues:
            print("BLOCKED  " + reason)
        print(f"{label}: prerequisite check failed; no test scripts ran. No suite pass.")
        report_remediation(issues)
        return 2
    if args.check_prerequisites:
        print(f"{label}: prerequisites present; tests NOT RUN. Module discovery does not verify binary compatibility.")
        return 0
    selected = SOURCE_TESTS if args.source_only else TESTS
    failed = 0
    unittest_skips, platform_skips, other_skips = 0, [], []
    for script in selected:
        # -S makes the source-only promise testable even on a machine with packages installed.
        command = [sys.executable] + (["-S"] if args.source_only else []) + [script]
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        except OSError as error:
            failed += 1
            print(f"FAIL  {script}: could not run: {error}")
            continue
        failed += result.returncode != 0
        status = "PASS" if result.returncode == 0 else "FAIL"
        last = (result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or [""])[-1]
        print(f"{status}  {script}: {last}".rstrip())
        cases, platform, other = coverage_notices(result.stdout, result.stderr)
        unittest_skips += cases
        if cases:
            print(f"      SKIP (unittest) {cases} case(s); run this unittest script with -v for identities/reasons")
        for reasons, retained, category in ((platform, platform_skips, "platform"),
                                             (other, other_skips, "additional check")):
            for reason in reasons:
                retained.append((script, reason))
                print(f"      SKIP ({category}) {reason}")
        if result.returncode:
            print(result.stdout[-2000:], result.stderr[-2000:])
    print(f"{label}: {len(selected) - failed}/{len(selected)} scripts passed; {failed} failed; "
          f"{unittest_skips} unittest case(s) skipped; {len(platform_skips)} platform notice(s); "
          f"{len(other_skips)} additional skipped-check notice(s).")
    if platform_skips:
        print("Platform notices explain unittest skips where reported; do not add them to the unittest case count.")
    if args.source_only:
        print("SOURCE-ONLY result is NOT a full-suite pass; cached-data and dependency checks were excluded.")
    elif not failed and (unittest_skips or platform_skips or other_skips):
        print("FULL CACHED-DATA scripts passed, but some checks did not run (see skipped cases/notices above): "
              "not a complete pass here. This is offline evidence, not gateway/runtime acceptance.")
    elif not failed:
        print("FULL CACHED-DATA suite passed. This is offline evidence, not gateway/runtime acceptance.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
