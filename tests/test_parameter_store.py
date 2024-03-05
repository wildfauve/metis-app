import pytest

import os

from metis_app import parameter_store, aws_client_helpers

from .shared import aws_helpers, ssm_helpers


def test_initialises_env_from_ps(setup_aws_ctx):
    parameter_store.set_env_from_parameter_store(path='/test/test_function/function_namespace/environment/')
    
    assert os.environ.get('CLIENT_ID') == "id"
    assert os.environ.get('CLIENT_SECRET') == "secret"
    assert os.environ.get('IDENTITY_TOKEN_ENDPOINT') == "https://test.host/token"

def test_can_inject_ssm_client():
    parameter_store.set_env_from_parameter_store(path='/test/test_function/function_namespace/environment/',
                                                 client=mock_ssm_with_response(ssm_helpers.ssm_param_response()))

    assert os.environ.get('CLIENT_ID') == "id"
    assert os.environ.get('CLIENT_SECRET') == "secret"
    assert os.environ.get('IDENTITY_TOKEN_ENDPOINT') == "https://test.host/token"


def test_write_and_mutate_env(setup_aws_ctx):
    os.environ.pop('A_PARAM', None)
    key = '/test/test_function/function_namespace/environment/A_PARAM'
    writer = parameter_store.writer(key, mutate_env=True, value_type=parameter_store.SecureString)

    result = writer("TEST")
    assert result.is_right
    assert result.value.state == "ok"
    assert result.value.name == "A_PARAM"
    assert result.value.value == "TEST"

    assert os.environ.get('A_PARAM') == "TEST"


def test_write_and_dont_mutate_env(setup_aws_ctx):
    os.environ.pop('A_PARAM', None)
    key = '/test/test_function/function_namespace/environment/A_PARAM'
    writer = parameter_store.writer(key, mutate_env=False, value_type=parameter_store.SecureString)

    result = writer("TEST")
    assert result.is_right

    assert not os.environ.get('A_PARAM', None)


def test_use_relative_keys_on_write(setup_aws_ctx):
    def is_in_env(param):
        return os.environ.get('A_PARAM', None)

    root_path = "/test/test_function/function_namespace/environment/"


    parameter_store.ParameterConfiguration().configure(root_path=root_path, update_test_fn=is_in_env)

    os.environ.pop('A_PARAM', None)
    key = 'A_PARAM'
    writer = parameter_store.writer(key, mutate_env=True, value_type=parameter_store.SecureString)

    result = writer("TEST")

    assert result.is_right
    assert result.value.state == "ok"
    assert result.value.name == "A_PARAM"
    assert result.value.value == "TEST"

    assert os.environ.get('A_PARAM') == "TEST"


def test_use_relative_keys_on_write_and_update(setup_aws_ctx):
    def is_in_env(param):
        return os.environ.get('A_PARAM', None)

    root_path = "/test/test_function/function_namespace/environment/"
    parameter_store.ParameterConfiguration().configure(root_path=root_path, update_test_fn=is_in_env)
    os.environ.pop('A_PARAM', None)
    key = 'A_PARAM'

    writer = parameter_store.writer(key, mutate_env=True, value_type=parameter_store.SecureString)

    result1 = writer("TEST")

    assert result1.is_right
    assert os.environ.get('A_PARAM') == "TEST"

    result2 = writer("TEST-UPDATE")

    assert result2.is_right()
    assert os.environ.get('A_PARAM') == "TEST-UPDATE"


@pytest.fixture
def setup_aws_ctx():
    services = {'ssm': {}}

    aws_client_helpers.invalidate_cache()

    ssm_client = mock_ssm_with_response(ssm_helpers.ssm_param_response())

    aws_client_helpers.AwsClientConfig().configure(region_name="ap_southeast_2",
                                                   aws_client_lib=aws_helpers.MockBoto3(mock_client=ssm_client),
                                                   services=services)

def mock_ssm_with_response(response):
    aws_helpers.MockSsm.response = response
    return aws_helpers.MockSsm