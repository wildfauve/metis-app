from typing import List, Tuple, Callable
from dataclasses import dataclass
from pymonad.reader import Pipe
from pymonad.tools import curry

from metis_fn import fn, monad

@dataclass
class StateTransitionMap:
    stmap: List[Tuple[str, str, str]]

def state_transition_map(stmap: List[Tuple[str]]) -> StateTransitionMap:
    return StateTransitionMap(stmap)

def valid_transitions_from(state_map: StateTransitionMap, from_state: str) -> List[str]:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state, (from_state, None, None)))
           .then(extract_transition_from_map)
           .flush())

def valid_state_transition(state_map: StateTransitionMap, from_state: str, with_transition: str) -> bool:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state_and_transition, (from_state, with_transition, None)))
           .then(list)
           .then(fn.only_one)
           .flush())

def transition(state_map: StateTransitionMap, from_state: str, with_transition: str) -> monad.EitherMonad[str]:
    return (Pipe(state_map)
           .then(map_selector(extract_from_state_and_transition, (from_state, with_transition, None)))
           .then(list)
           .then(validate_and_extract_new_state)
           .flush())


@curry(3)
def map_selector(extractor_fn: Callable, map_tester: Tuple, state_map: StateTransitionMap) -> filter:
    return fn.select(fn.equality(extractor_fn, map_tester), state_map.stmap)

def validate_and_extract_new_state(state_map_items: List[Tuple[str, str, str]]) -> str:
    if fn.only_one(state_map_items):
        return monad.Right(state_map_items[0][2])
    return monad.Left("invalid transition")


def extract_from_state(state_map_item: Tuple) -> Tuple[str, None, None]:
    current, _transition, _new = state_map_item
    return (current, None, None)

def extract_from_state_and_transition(state_map_item: Tuple) -> Tuple:
    current, transition, _new = state_map_item
    return (current, transition, None)


def extract_transition(state_map_item: Tuple[str, str, str]) -> str:
    _current, transition, new = state_map_item
    return transition


def extract_transition_from_map(state_map: List[Tuple[str, str, str]]) -> str:
    return list(map(extract_transition, state_map))
