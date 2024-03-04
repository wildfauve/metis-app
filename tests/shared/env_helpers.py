import pytest

import os
from typing import List, Tuple

@pytest.fixture
def set_up_env():
    pass

# Global Object
class Env:
    env = os.environ.get('ENVIRONMENT', default=None)

    region_name = os.environ.get('REGION_NAME', default='ap-southeast-2')

    expected_envs = []


    @staticmethod
    def development():
        return Env.env == "development"

    @staticmethod
    def test():
        return Env.env == "test"

    @staticmethod
    def production():
        return not (Env.development() or Env.test())

    @staticmethod
    def expected_set():
        return all(getattr(Env, var)() for var in Env.expected_envs)