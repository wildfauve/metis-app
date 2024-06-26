from typing import Any, Callable, Union, Optional, Protocol, TypeVar, Type
from datetime import datetime
from metis_fn import monad, chronos, singleton

from . import error, state_machine

T = TypeVar('T', bound='CircuitStateProviderProtocol')

# Circuit States, transitions, and state machine
transition_failure           = 'failure'
transition_persistent_failure = 'persistent_failure'
transition_success           = 'success'
state_half_open              = 'half_open'
state_half_closed            = 'half_closed'
state_open                   = 'open'
state_closed                 = 'closed'
circuit_state_map = state_machine.state_transition_map([(None,              transition_failure,            state_half_open),
                                                       (None,               transition_persistent_failure, state_open),
                                                       (None,               transition_success,            state_closed),
                                                       (state_half_open,    transition_persistent_failure, state_open),
                                                       (state_half_closed,  transition_persistent_failure, state_open),
                                                       (state_half_closed,  transition_failure,            state_half_open),
                                                       (state_half_open,    transition_success,            state_closed),
                                                       (state_open,         transition_success,            state_half_closed),
                                                       (state_closed,       transition_success,            state_closed),
                                                       (state_half_closed,  transition_success,            state_closed)])


class CircuitOpen(error.BaseError):
    pass


class CircuitStateProviderProtocol(Protocol):
    def __init__(self, circuit_name: Union[None, str]):
        ...

    def circuit_state(self) -> Union[None, str]:
        """
        Returns the current circuit state or None.  The circuit state machine is provided by the circuit breaker to the provider.
        It comes from the state machine defined in circuit_state_map
        """
        ...

    def failures(self) -> int:
        ...

    def last_state_chg_time(self) -> datetime:
        ...

    def update_state(self, failures: int,  last_state_chg_time: datetime, circuit_state: Union[None, str]) -> T:
        """
        Expects the circuit state to be updated
        """
        ...

class CircuitConfiguration(singleton.Singleton):
    # Factors that determine if a circuit should be placed in open state.
    # 3 failures in a 5 min period, opens the circuit
    failure_threshold_seconds = 5 * 60 # 5 minutes
    failure_count_threshold = 3

    # The number of minutes from the time a circuit transitioned to open before it can be retried
    open_stand_down_period = 5 * 60

    def configure(self,
                  max_retries: int =None,
                  circuit_state_provider: Optional[CircuitStateProviderProtocol] = None):
        self.circuit_state_provider = circuit_state_provider
        self.max_retries = 3 if max_retries is None else max_retries # used by the backoff decorator to configure the number of retry attempts
        pass

    def provider(self):
        return self.circuit_state_provider if hasattr(self, "circuit_state_provider") else None


def max_retries():
    return CircuitConfiguration().max_retries if hasattr(CircuitConfiguration(), 'max_retries') else None

def circuit_breaker():
    """
    Circuit Breaker Decorator.

    The kwargs to the wrapped function MAY include a 'circuit_state_provider' argument which can manage the state of the circuit
    over multiple invocations.  Its not implemented here, but must be injected in the args.
    If its available it must support the following methods:
    + circuit_state
    + failures
    + last_state_chg_time: Takes and returns the last state change time as a ISO8601 formatted str.
    + update_state

    When a circuit_state_provider is not provided, the circuit is a no-op.

    """
    def inner(fn):
        def breaker(*args, **kwargs):
            circuit_state_provider = get_a_provider(kwargs, CircuitConfiguration())
            if circuit_state_provider and is_open(circuit_state_provider) and is_in_stand_down_period(circuit_state_provider.last_state_chg_time):
                return monad.Left(CircuitOpen(message="Circuit Open",
                                              code=500,
                                              ctx={'circuit_state': circuit_state_provider.circuit_state, 'failures': circuit_state_provider.failures}))

            result = fn(*args, **kwargs)

            if circuit_state_provider:
                if result.is_left():
                    circuit_failure(circuit_state_provider)
                else:
                    transition_circuit_on_success(circuit_state_provider)
            return result
        return breaker
    return inner

def get_a_provider(from_args, from_config):
    """
    From Args takes precidence.
    """
    args_provider = from_args.get('circuit_state_provider', None)
    return from_config.provider() if args_provider is None else args_provider

def monad_failure_predicate(monad_result: Union[Any, monad.MEither]) -> bool:
    return isinstance(monad_result, monad.MEither) and monad_result.is_left()

def http_retryable_monad_failure_predicate(monad_result: Union[Any, monad.MEither]) -> bool:
    """
    HTTP Client-based errors (400-series) are not retryable 
    """
    if not isinstance(monad_result, monad.MEither):
        return False
    if monad_result.is_left() and isinstance(monad_result.error(), str):
        return False
    return monad_result.is_left() and monad_result.error().retryable

def circuit_failure(circuit_state_provider: Any) -> Any:
    if exhasted_failures_over_period(last_state_chg_time=circuit_state_provider.last_state_chg_time, failures=circuit_state_provider.failures):
        open_circuit(circuit_state_provider)
        pass
    else:
        update_circuit_failures(circuit_state_provider)
    pass

def transition_circuit_on_success(circuit_state_provider: Any) -> Any:
    transition = circuit_transition(from_state=circuit_state_provider.circuit_state, with_transition=transition_success)
    if circuit_state_provider.circuit_state != transition.value:
        circuit_state_provider.update_state(circuit_state=transition.value,
                                            last_state_chg_time=chronos.time_now(tz=chronos.tz_utc()),
                                            failures=0)
    return circuit_state_provider

def exhasted_failures_over_period(last_state_chg_time: datetime, failures: int) -> bool:
    if last_state_chg_time is None:
        return False
    return failures_within_time_threshold(last_state_chg_time) and (failures >= (CircuitConfiguration().failure_count_threshold) )

def failures_within_time_threshold(circuit_time: datetime) -> bool:
    """
    When the circuit is half open, we can retry until we reach the failure threshold.
    """
    return (chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]) - circuit_time.timestamp()) < CircuitConfiguration().failure_threshold_seconds

def is_in_stand_down_period(last_state_chg_time: datetime) -> bool:
    """
    When the circuit is open there is a stand down period where the circuit will not be retried
    """
    return (chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]) - last_state_chg_time.timestamp()) < CircuitConfiguration().open_stand_down_period

def open_circuit(circuit_state_provider: Any) -> Any:
    if circuit_state_provider.circuit_state == state_open:
        return circuit_state_provider

    circuit_state_provider.update_state(circuit_state=circuit_transition(from_state=circuit_state_provider.circuit_state, with_transition=transition_persistent_failure).value,
                                        last_state_chg_time=chronos.time_now(tz=chronos.tz_utc()),
                                        failures=0)
    return circuit_state_provider

def update_circuit_failures(circuit_state_provider: Any) -> Any:
    transition = circuit_transition(from_state=circuit_state_provider.circuit_state, with_transition=transition_failure).value
    if transition !=circuit_state_provider.circuit_state:
        circuit_state_provider.update_state(circuit_state=transition,
                                            last_state_chg_time=chronos.time_now(tz=chronos.tz_utc()),
                                            failures=1 if circuit_state_provider.failures is None else circuit_state_provider.failures + 1)

    return circuit_state_provider

#
# Circuit State Management
#
def circuit_transition(from_state: str, with_transition: str) -> monad.MEither:
    return state_machine.transition(state_map=circuit_state_map, from_state=from_state, with_transition=with_transition)

def is_open(config):
    return config.circuit_state == state_open
