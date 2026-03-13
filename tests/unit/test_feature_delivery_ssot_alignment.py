from pathlib import Path


def test_feature_delivery_feat_doc_matches_canonical_l2_contract():
    feat_doc = Path(
        "spec/requirements/features/FEAT-SRC-009-001__feature-delivery-l2-gongzuoliudingyi.md"
    )
    text = feat_doc.read_text(encoding="utf-8")

    assert "repo_frontend" in text
    assert "repo_backend" in text
    assert "Contract → Backend / Frontend 并行 → Integration → Evidence Pack" in text


def test_feature_delivery_tech_doc_matches_canonical_l2_contract():
    tech_doc = Path(
        "spec/tech/TECH-FEAT-SRC-009-001-001__feature-delivery-l2-gongzuoliudingyi-frozenjizhuji.md"
    )
    text = tech_doc.read_text(encoding="utf-8")

    assert "repo_frontend/repo_backend" in text
    assert "contract_design -> backend_dev / frontend_dev 并行 -> integration" in text


def test_feature_delivery_task_doc_matches_canonical_l2_contract():
    task_doc = Path(
        "spec/tasks/FEAT-SRC-009-001/"
        "TASK-FEAT-SRC-009-001-001__l2gongzuoliuguifanyujiegoudingyi.md"
    )
    text = task_doc.read_text(encoding="utf-8")

    assert "repo_frontend, repo_backend" in text
    assert "Contract→Backend/Frontend并行→Integration→Evidence Pack" in text
