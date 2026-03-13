from pathlib import Path


def test_bugfix_batch_approval_process_defines_gate_and_record_fields():
    doc_path = Path("spec-global/departments/dev/docs/bugfix-batch-approval-process.md")
    assert doc_path.exists(), "Bugfix batch approval process doc not found"

    text = doc_path.read_text(encoding="utf-8")
    assert "## Approval Flow" in text
    assert "dev-process-owner" in text
    assert "dev-architecture-owner" in text
    assert "`batch_approval_record`" in text
    assert "审批拒绝后，运行时必须回退为单 bug 拆分执行。" in text
