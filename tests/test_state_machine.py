import pytest

from metis_app import state_machine

def test_valid_transitions(state_map):
    assert state_machine.valid_transitions_from(state_map=state_map, from_state="half_open") == ['persistent_failure', 'success']

def test_valid_state_transition(state_map):
    result = state_machine.valid_state_transition(state_map=state_map, from_state="half_open", with_transition="success")
    assert result == True

def test_invalid_state_transition(state_map):
    result = state_machine.valid_state_transition(state_map=state_map, from_state="half_open", with_transition="failure")
    assert result == False

def test_transition_with_valid_state_transition(state_map):
    result = state_machine.transition(state_map=state_map, from_state="half_open", with_transition="success")

    assert result.is_right() == True
    assert result.value == 'closed'

def test_transition_with_invalid_state_transition(state_map):
    result = state_machine.transition(state_map=state_map, from_state="half_open", with_transition="failure")

    assert result.is_right() == False


@pytest.fixture
def state_map():
    #           State               Event                Next State
    map = [(None,                "failure",               "half_open"),
           ("half_open",         "persistent_failure",    "open"),
           ("half_open",         "success",               "closed"),
           ("open",              "success",               "closed")]
    return state_machine.state_transition_map(map)
