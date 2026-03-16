from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.normalization import OutputExtractor


def test_extract_for_validation_prefers_generated_text_over_wrapper(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    output = {
        "raw_output": '{"status":"success","generated_text":"ignored"}',
        "generated_text": "business_output:\n  epic_ref: EPIC-003\n  feat_specs: []\n",
    }

    business_output, structured_payload = OutputExtractor.extract_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[],
        extract_primary_file_output=lambda *_: None,
        extract_best_written_file_payload=lambda *_: None,
        normalize_business_payload=lambda **kwargs: (
            kwargs["business_output"],
            kwargs["structured_payload"],
        ),
    )

    assert business_output["epic_ref"] == "EPIC-003"
    assert structured_payload["business_output"]["epic_ref"] == "EPIC-003"


def test_extract_ssot_contract_payload_reads_named_section():
    generated_text = """
评审输出

ssot_output_contract
```yaml
contract_version: "1.0"
outputs:
  - key: feat_spec
    ssot_type: feat
```
"""

    payload = OutputExtractor.extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
        extract_structured_segment_payload=lambda text, name: {
            "contract_version": "1.0",
            "outputs": [{"key": "feat_spec", "ssot_type": "feat"}],
        },
        extract_structured_payload_from_code_blocks=lambda *_: None,
        coerce_ssot_contract_dict=lambda payload: payload if isinstance(payload, dict) else None,
    )

    assert payload == {
        "contract_version": "1.0",
        "outputs": [{"key": "feat_spec", "ssot_type": "feat"}],
    }


def test_extract_best_written_file_payload_prefers_prd_bundle(tmp_path):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    generic_file = tmp_path / "business_output.yaml"
    generic_file.write_text("kind: business_output\nsummary: placeholder\n", encoding="utf-8")
    feat_file = tmp_path / "feat_spec.yaml"
    feat_file.write_text("epic_ref: EPIC-001\nfeat_specs: []\n", encoding="utf-8")

    payload = OutputExtractor.extract_best_written_file_payload(
        step=step,
        written_files=[str(generic_file), str(feat_file)],
        build_prd_writer_bundle_from_written_files=lambda files: {"epic_ref": "EPIC-001", "feat_specs": []},
        build_pm_planner_bundle_from_written_files=lambda files: None,
        score_written_output_candidate=lambda *_: 0,
    )

    assert payload == {"epic_ref": "EPIC-001", "feat_specs": []}
