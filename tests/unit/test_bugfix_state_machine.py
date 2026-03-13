import pytest

from lee.state.bugfix_state_machine import BugfixStateMachine


def test_bugfix_state_machine_happy_path():
    machine = BugfixStateMachine()
    state = machine.INITIAL_STATE

    state = machine.next_state(state, "triage_completed")
    state = machine.next_state(state, "root_cause_started")
    state = machine.next_state(state, "fix_design_started")
    state = machine.next_state(state, "fix_impl_started")
    state = machine.next_state(state, "verification_started")
    state = machine.next_state(state, "evidence_pack_started")
    state = machine.next_state(state, "merge_decision_started")
    state = machine.next_state(state, "merge_completed")

    assert state == "COMPLETED"


def test_bugfix_state_machine_rejects_invalid_transition():
    machine = BugfixStateMachine()

    with pytest.raises(ValueError):
        machine.next_state("INIT", "merge_completed")

    with pytest.raises(ValueError):
        machine.next_state("COMPLETED", "triage_completed")
