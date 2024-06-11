import pytest

import os
from typing import List, Tuple

from metis_app import env


@pytest.fixture
def set_up_env():
    pass


# Global Object
class Env(env.EnvironmentProtocol):
    env = os.environ.get('ENVIRONMENT', default=None)

    region_name = os.environ.get('REGION_NAME', default='ap-southeast-2')

    expected_environment_variables = []

    _instance = None
    def __new__(self):
        if self._instance is None:
            self._instance = super(Env, self).__new__(self)
        return self._instance

    @property
    def development(self):
        return Env.env == "development"

    @property
    def test(self):
        return Env.env == "test"

    @property
    def production(self):
        return not (Env.development() or Env.test())

    @property
    def has_expected_environment_variables(self):
        return all(getattr(Env, var)() for var in Env.expected_envs)
