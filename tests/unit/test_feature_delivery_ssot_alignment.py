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


def test_feature_delivery_epic_scope_matches_canonical_l2_contract():
    epic_doc = Path(
        "spec/requirements/epics/EPIC-SRC-009__dev-department-ssot-alignment-delivery-governance.md"
    )
    text = epic_doc.read_text(encoding="utf-8")

    assert "repo_frontend" in text
    assert "repo_backend" in text


def test_feature_delivery_followup_tasks_match_canonical_l2_contract():
    task_impl_doc = Path(
        "spec/tasks/FEAT-SRC-009-001/"
        "TASK-FEAT-SRC-009-001-002__l2gongzuoliumobanshixian.md"
    )
    task_governance_doc = Path(
        "spec/tasks/FEAT-SRC-009-001/"
        "TASK-FEAT-SRC-009-001-004__yanzhengceshiyuwendangzhili.md"
    )
    impl_text = task_impl_doc.read_text(encoding="utf-8")
    governance_text = task_governance_doc.read_text(encoding="utf-8")

    assert "Backend/Frontend并行" in impl_text
    assert "repo_frontend, repo_backend" in impl_text
    assert "Contract→Backend/Frontend并行→Integration→Evidence Pack" in governance_text
    assert "repo_frontend, repo_backend" in governance_text


def test_bugfix_tech_doc_matches_exception_approval_contract():
    tech_doc = Path(
        "spec/tech/TECH-FEAT-SRC-009-002-001__bugfix-delivery-l2-gongzuoliudingyi-frozenjizhujia.md"
    )
    text = tech_doc.read_text(encoding="utf-8")

    assert "batch_approval_record" in text
    assert "五同失败后的审批例外" in text or "审批例外路径" in text


def test_bugfix_followup_tasks_match_exception_approval_contract():
    template_task = Path(
        "spec/tasks/FEAT-SRC-009-002/"
        "TASK-FEAT-SRC-009-002-002__bugfix-l2-gongzuoliumobanshixian.md"
    )
    policy_task = Path(
        "spec/tasks/FEAT-SRC-009-002/"
        "TASK-FEAT-SRC-009-002-004__bugfix-lidukongzhicelveyuzhuangtaijishixian.md"
    )
    governance_task = Path(
        "spec/tasks/FEAT-SRC-009-002/"
        "TASK-FEAT-SRC-009-002-005__yanzhengceshiyuwendangzhili.md"
    )
    template_text = template_task.read_text(encoding="utf-8")
    policy_text = policy_task.read_text(encoding="utf-8")
    governance_text = governance_task.read_text(encoding="utf-8")

    assert "batch_approval_record" in template_text
    assert "审批例外" in template_text
    assert "batch_approval_record" in policy_text
    assert "审批例外路径" in policy_text
    assert "审批例外 batch 模式" in governance_text


def test_shared_input_lineage_documents_feature_repo_extensions():
    feat_117 = Path(
        "spec/requirements/features/FEAT-117__shared-input-specification-implementation.md"
    )
    feat_128 = Path(
        "spec/requirements/features/FEAT-128__shared-input-specification-implementation.md"
    )
    task_140 = Path(
        "spec/tasks/FEAT-140/TASK-FEAT-140-001__gongxiangshuruguifanyuzhiliguizeshixian.md"
    )
    feat_117_text = feat_117.read_text(encoding="utf-8")
    feat_128_text = feat_128.read_text(encoding="utf-8")
    task_140_text = task_140.read_text(encoding="utf-8")

    assert "repo_frontend, repo_backend" in feat_117_text
    assert "repo_frontend, repo_backend" in feat_128_text
    assert "repo_frontend, repo_backend" in task_140_text


def test_legacy_feature_delivery_feat_matches_canonical_repo_extensions():
    feat_130 = Path("spec/requirements/features/FEAT-130__feature-delivery-l2-gongzuoliudingyi.md")
    text = feat_130.read_text(encoding="utf-8")

    assert "repo_frontend" in text
    assert "repo_backend" in text
    assert "Contract → Backend / Frontend 并行 → Integration → Evidence Pack" in text


def test_early_feature_delivery_feat_matches_canonical_parallel_contract():
    feat_108 = Path("spec/requirements/features/FEAT-108__feature-delivery-l2-workflow-definition.md")
    text = feat_108.read_text(encoding="utf-8")

    assert "repo_frontend" in text
    assert "repo_backend" in text
    assert "Contract Design → Backend Development / Frontend Development 并行 → Integration → Evidence Pack" in text


def test_alternate_feature_delivery_feat_matches_canonical_parallel_contract():
    feat_119 = Path("spec/requirements/features/FEAT-119__feature-delivery-l2-workflow-definition.md")
    text = feat_119.read_text(encoding="utf-8")

    assert "governing_adrs" in text
    assert "repo_frontend" in text
    assert "repo_backend" in text
    assert "Contract Design → Backend / Frontend 并行 → Integration → Evidence Pack" in text


def test_contract_design_feat_matches_canonical_freeze_handoff():
    feat_111 = Path("spec/requirements/features/FEAT-111__contract-design-l3-stage-definition.md")
    text = feat_111.read_text(encoding="utf-8")

    assert "contract_freeze_ref" in text
    assert "Contract freeze completed" in text
    assert "唯一结构真相源" in text


def test_integration_feat_matches_canonical_input_boundary():
    feat_114 = Path("spec/requirements/features/FEAT-114__integration-l3-stage-definition.md")
    text = feat_114.read_text(encoding="utf-8")

    assert "tech_spec_ref" in text
    assert "contract_freeze_ref" in text
    assert "env_ref/base_url/runtime_config_ref" in text
    assert "contract/mock 模式或 environment-backed 模式" in text


def test_evidence_pack_feat_matches_canonical_handoff_contract():
    feat_126 = Path("spec/requirements/features/FEAT-126__evidence-pack-stage-definition-closing-mechanism.md")
    text = feat_126.read_text(encoding="utf-8")

    assert "integration_outputs" in text
    assert "verification_results" in text
    assert "verification_summary_ref" in text
    assert "delivery_candidate_ref" in text
    assert "audit_declaration_ref" in text
    assert "smoke_gate_inputs" in text


def test_early_bugfix_feat_matches_canonical_bugfix_contract():
    feat_109 = Path("spec/requirements/features/FEAT-109__bugfix-delivery-l2-workflow-definition.md")
    text = feat_109.read_text(encoding="utf-8")

    assert "bug_ssot_id" in text
    assert "batch_approval_record" in text
    assert "Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence" in text


def test_bugfix_main_lineage_matches_canonical_stage_model():
    feat_src = Path("spec/requirements/features/FEAT-SRC-009-002__bugfix-delivery-l2-gongzuoliudingyi.md")
    tech = Path("spec/tech/TECH-FEAT-SRC-009-002-001__bugfix-delivery-l2-gongzuoliudingyi-frozenjizhujia.md")
    task = Path(
        "spec/tasks/FEAT-SRC-009-002/"
        "TASK-FEAT-SRC-009-002-001__bugfix-l2-gongzuoliuguifanyujiegoudingyi.md"
    )
    feat_text = feat_src.read_text(encoding="utf-8")
    tech_text = tech.read_text(encoding="utf-8")
    task_text = task.read_text(encoding="utf-8")

    assert "batch_approval_record" in feat_text
    assert "Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack" in feat_text
    assert "Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack" in tech_text
    assert "输入规范五字段定义" in task_text


def test_legacy_bugfix_feature_specs_match_canonical_stage_model():
    feat_120 = Path("spec/requirements/features/FEAT-120__bugfix-delivery-l2-workflow-definition.md")
    feat_131 = Path("spec/requirements/features/FEAT-131__bugfix-delivery-l2-gongzuoliudingyi.md")
    task_130 = Path("spec/tasks/FEAT-130/TASK-FEAT-130-001__feature-bugfix-delivery-l2-gongzuoliumobanshixian.md")
    feat_120_text = feat_120.read_text(encoding="utf-8")
    feat_131_text = feat_131.read_text(encoding="utf-8")
    task_130_text = task_130.read_text(encoding="utf-8")

    assert "Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence" in feat_120_text
    assert "batch_approval_record" in feat_131_text
    assert "Bugfix Delivery L2: Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack" in task_130_text
