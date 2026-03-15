from lee.orchestrator.execution.runners.llm_runner import LLMRunner


def test_sync_business_output_uses_materialized_epic_id() -> None:
    business_output = {
        "epic_id": "EPIC-046",
        "title": "交付轴 workflow 化治理与发布闭环建设",
    }
    structured_payload = {
        "business_output": {
            "epic_id": "EPIC-046",
            "title": "交付轴 workflow 化治理与发布闭环建设",
        }
    }
    ssot_materialized = {
        "outputs": {
            "epic": {
                "id": "EPIC-SRC-046-001",
                "identity_kind": "ssot",
            }
        }
    }

    normalized_business, normalized_structured = LLMRunner._synchronize_business_identity_from_materialized_ssot(
        business_output=business_output,
        structured_payload=structured_payload,
        ssot_materialized=ssot_materialized,
    )

    assert normalized_business["epic_id"] == "EPIC-SRC-046-001"
    assert normalized_business["epic_ref"] == "EPIC-SRC-046-001"
    assert normalized_structured["business_output"]["epic_id"] == "EPIC-SRC-046-001"
    assert normalized_structured["business_output"]["epic_ref"] == "EPIC-SRC-046-001"
