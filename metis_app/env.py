from typing import Protocol


class EnvironmentProtocol(Protocol):
    env: str
    expected_environment_variables: list[str]

    def has_expected_environment_variables(self) -> bool:
        ...
