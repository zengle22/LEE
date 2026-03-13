from lee.policy.granularity_evaluator import GranularityPolicyEvaluator


def test_single_bug_mode_requires_exactly_one_bug():
    evaluator = GranularityPolicyEvaluator()

    decision = evaluator.evaluate(bug_ids=["BUG-1"], batch_mode=False)
    assert decision.allowed is True
    assert decision.mode == "single_bug"

    rejected = evaluator.evaluate(bug_ids=["BUG-1", "BUG-2"], batch_mode=False)
    assert rejected.allowed is False
    assert rejected.split_required is True


def test_batch_mode_requires_all_five_same_flags():
    evaluator = GranularityPolicyEvaluator()

    decision = evaluator.evaluate(
        bug_ids=["BUG-1", "BUG-2"],
        batch_mode=True,
        batch_context={
            "same_module": True,
            "same_root_cause_class": True,
            "same_fix_strategy": True,
            "same_verification_surface": True,
            "same_release_window": True,
        },
    )
    assert decision.allowed is True
    assert decision.reason == "five_same_rule_passed"

    rejected = evaluator.evaluate(
        bug_ids=["BUG-1", "BUG-2"],
        batch_mode=True,
        batch_context={
            "same_module": True,
            "same_root_cause_class": False,
            "same_fix_strategy": True,
            "same_verification_surface": True,
            "same_release_window": True,
        },
    )
    assert rejected.allowed is False
    assert rejected.split_required is True
    assert rejected.checks["same_root_cause_class"] is False
