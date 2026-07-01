# Legacy test archive: pre-v14.8.5.019

These tests were moved out of active pytest collection during the v14.8.5.020 test-suite reconciliation pass.

Reasoning:

- They assert historical runtime/schema versions such as v14.5.x, v14.6.x, v14.7.x, v14.8.2.x, v14.8.3.x, v14.8.4.x, v14.8.5.011, or v14.8.5.017.
- Several require local historical artifacts that are not part of the lean active runtime checkout: raw chat archives, legacy SQLite tables, generated audit reports, or dedup manifests.
- They remain available here as regression references, but they are no longer part of the active `pytest tests` contract for v14.8.5.019+.

Current active tests should assert behavior through dynamic schema helpers where possible, or through explicit current-release tests named with the current version.

Archived files:

- `test_chatgpt_cognitive_bridge.py`
- `test_conversation_archive_sql.py`
- `test_runtime_persistence.py`
- `test_v14521_review_fixes.py`
- `test_v14526_package_completeness.py`
- `test_v14528_awareness_logic.py`
- `test_v14529_conversation_runtime.py`
- `test_v14530_polish_understanding.py`
- `test_v14531_identity_continuity_understanding.py`
- `test_v14532_cognitive_packets.py`
- `test_v14533_download_safe_cognitive_packets.py`
- `test_v14534_emotional_granularity_continuity_cognition.py`
- `test_v14535_timestamp_contract.py`
- `test_v14536_birth_source_contract.py`
- `test_v14537_persistent_runtime_dialogue.py`
- `test_v14538_github_cognitive_runtime.py`
- `test_v14539_cleanup_dedup.py`
- `test_v1460_lexical_semantic_runtime.py`
- `test_v146101_stale_route_context_guard.py`
- `test_v14610_startup_contract.py`
- `test_v14610_version_consistency.py`
- `test_v146112_runtime_preview_source_state.py`
- `test_v146113_cognitive_turn_envelope.py`
- `test_v146114_bootstrap_recognition_hotfix.py`
- `test_v146114_final_visible_continuity_ledger.py`
- `test_v146114_runtime_preview_fallback_detection.py`
- `test_v146114_version_consistency_contract.py`
- `test_v146115_contextual_greeting_fallback_repair.py`
- `test_v1461_nlp_adapter_zip_profiles.py`
- `test_v14621_stale_nlp_route_hotfix.py`
- `test_v1462_runtime_start_fallback_truth_contract.py`
- `test_v1464_active_cache_visible_preview.py`
- `test_v1466_self_owned_startup_contract.py`
- `test_v14692_runtime_self_expression_topic_mismatch.py`
- `test_v14694_dynamic_runtime_provenance_template_origin_neuro_nlp.py`
- `test_v1470_model_independent_voice_runtime.py`
- `test_v1471_dialogue_grounding_hotfix.py`
- `test_v14825_final_response_preserves_handler_body.py`
- `test_v14825_route_memory_capability_hotfix.py`
- `test_v148260_self_memory_recall_presentation_quality.py`
- `test_v148261_non_memory_intent_memory_gating.py`
- `test_v148262_runtime_contract_version_normalizer.py`
- `test_v148266_current_turn_route_grounding_health_weather.py`
- `test_v1482_dialogue_followup_time_repair.py`
- `test_v1482_dialogue_intent_classifier_precision.py`
- `test_v1482_raw_memory_status.py`
- `test_v14831_fast_wake_route_trace.py`
- `test_v14832_unified_chat_session_core.py`
- `test_v14834_ordinary_dialogue_natural_presence.py`
- `test_v1484_ordinary_dialogue_stale_route_hotfix.py`
- `test_v1485_006_runtime_marker_schema_integrity.py`
- `test_v1485_008_ordinary_dialogue_naturalness.py`
- `test_v1485_009_sleep_closure_validator_contract.py`
- `test_v1485_010_sleep_closure_repair_loop.py`
- `test_v1485_011_self_architecture_audit_reflection_memory_gate.py`
- `test_v14_8_0_network_sjp_lexical_bridge.py`
- `test_v14_8_1_large_dialogue_memory_grounding.py`
