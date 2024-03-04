import pytest
from typing import Optional, Callable, Union
from datetime import datetime
from metis_app import circuit
from metis_fn import chronos

from . import dynamo_circuit_repo as repo

class CircuitStateProvider(circuit.CircuitStateProviderProtocol):
    def __init__(self, circuit_name=None):
        self.circuit_name = circuit_name
        self.circuit_state = None
        self.failures = 0
        self.last_state_chg_time = None

    def circuit_state(self, new_state):
        self.circuit_state = new_state
        return new_state

    def last_state_chg_time(self, new_time):
        self.last_state_chg_time = new_time
        return new_time

    def failures(self, count):
        self.failures = count
        return count

    def update_state(self, failures: int,  last_state_chg_time: datetime, circuit_state: Union[None, str]):
        self.failures = failures
        self.last_state_chg_time = last_state_chg_time
        self.circuit_state = circuit_state
        return self


class DynamoCircuitStore(circuit.CircuitStateProviderProtocol):
    def __init__(self, circuit_name=None):
        self.circuit_name = circuit_name
        self.store = self.find_or_create()
        self.circuit_state = self.store.circuit_state
        self.failures = self.store.failures
        self.last_state_chg_time = self.store.last_state_chg_time

    def circuit_state(self, new_state):
        self.circuit_state = new_state
        return new_state

    def last_state_chg_time(self, new_time):
        self.last_state_chg_time = new_time
        return new_time

    def failures(self, count):
        self.failures = count
        return count

    def update_state(self, failures: int,  last_state_chg_time: datetime, circuit_state: Union[None, str]):
        self.failures = failures
        self.last_state_chg_time = last_state_chg_time
        self.circuit_state = circuit_state
        self.update()
        return self

    def find_or_create(self):
        return repo.find_or_create_circuit(domain=self)

    def update(self):
        return repo.update_circuit(domain=self, repo=self.store)



@pytest.fixture
def circuit_state_provider():
    return CircuitStateProvider(circuit_name="test-circuit")

@pytest.fixture
def circuit_state_provider_in_open_state():
    circuit = CircuitStateProvider()
    circuit.circuit_state = 'open'
    circuit.last_state_chg_time = chronos.time_now(tz=chronos.tz_utc())
    circuit.failures = 3
    return circuit

