from metis_fn import monad

from .shared import *

def test_1st_failure_to_half_open(circuit_state_provider):
    failure()(circuit_state_provider=circuit_state_provider)
    assert(circuit_state_provider.circuit_state) == "half_open"
    assert(circuit_state_provider.failures) == 1

def test_failure_then_success_to_closed(circuit_state_provider):
    failure()(circuit_state_provider=circuit_state_provider)
    success()(circuit_state_provider=circuit_state_provider)
    assert(circuit_state_provider.circuit_state) == "closed"
    assert(circuit_state_provider.failures) == 0

def test_gets_the_provider_from_the_config(circuit_state_provider):
    circuit.CircuitConfiguration().configure(circuit_state_provider=circuit_state_provider)
    failure()()
    assert(circuit_state_provider.circuit_state) == "half_open"
    assert(circuit_state_provider.failures) == 1

def test_noop_the_circuit_when_no_provider():
    result = failure()()

    assert result.is_left


def failure():
    @circuit.circuit_breaker()
    def run(circuit_state_provider=None):
        return monad.Left("boom")
    return run

def success():
    @circuit.circuit_breaker()
    def run(circuit_state_provider=None):
        return monad.Right("OK")
    return run
