import pytest

import os

from metis_fn import fn, monad

from metis_app import parameter_store, aws_client_helpers

from .shared import aws_helpers, ssm_helpers


def setup_function():
    aws_client_helpers.invalidate_cache()


def test_initialises_env_from_ps(setup_aws_ctx):
    parameter_store.set_env_from_parameter_store(path='/test/test_function/function_namespace/environment/')

    assert os.environ.get('CLIENT_ID') == "id"
    assert os.environ.get('CLIENT_SECRET') == "secret"
    assert os.environ.get('IDENTITY_TOKEN_ENDPOINT') == "https://test.host/token"


def test_can_inject_ssm_client():
    parameter_store.set_env_from_parameter_store(path='/test/test_function/function_namespace/environment/',
                                                 client=mock_ssm_object(ssm_helpers.ssm_param_response()))

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


def test_getting_nested_parameters(aws_mock,
                                   aws_ctx_with_boto):
    nested_params()
    params = parameter_store.get_parameters("/service1/env", parameter_store.ssm_client())

    expected_keys = {'/service1/env/PARAMETER_IN_ENV', '/service1/env/ns1/NS1_PARAMETER'}
    assert params.is_right()
    assert {param.get('Name') for param in params.value} == expected_keys


def test_setting_nested_parameters_in_env(aws_mock,
                                          aws_ctx_with_boto):
    nested_params()
    result = parameter_store.set_env_from_parameter_store("/service1/env")

    assert fn.bool_fn_with_predicate(result.value, all, monad.maybe_value_ok)

    assert os.environ.get('PARAMETER_IN_ENV') == "1"
    assert os.environ.get('NS1_PARAMETER') == "ns1"



def test_use_parameter_env_protocol(aws_mock, aws_ctx_with_boto):
    nested_params()

    parameter_store.ParameterConfiguration().configure(root_path="/service1/env",
                                                       parameter_env_cls=parameter_store.OsEnv)

    result = parameter_store.set_parameter_env_from_parameter_store("/service1/env")

    assert result.is_right()
    assert os.environ.get('PARAMETER_IN_ENV') == "1"
    assert os.environ.get('NS1_PARAMETER') == "ns1"


def test_writer_using_parameter_env_protocol(aws_mock, aws_ctx_with_boto):
    os.environ.pop('PARAMETER_IN_ENV', None)

    key = "/service1/env/PARAMETER_IN_ENV"
    parameter_store.ParameterConfiguration().configure(root_path="/service1/env",
                                                       parameter_env_cls=parameter_store.OsEnv)

    writer = parameter_store.writer(key,
                                    mutate_env=True,
                                    value_type=parameter_store.SecureString)


    result = writer("TEST")
    assert result.is_right
    assert result.value.state == "ok"
    assert result.value.name == "PARAMETER_IN_ENV"
    assert result.value.value == "TEST"

    assert os.environ.get('PARAMETER_IN_ENV') == "TEST"



@pytest.fixture
def setup_aws_ctx():
    services = {'ssm': {}}

    ssm_client = mock_ssm_cls(ssm_helpers.ssm_param_response())

    aws_client_helpers.AwsClientConfig().configure(region_name="ap_southeast_2",
                                                   aws_client_lib=aws_helpers.MockBoto3(mock_client=ssm_client),
                                                   services=services)


def mock_ssm_cls(response):
    aws_helpers.MockSsm.response = response
    return aws_helpers.MockSsm


def mock_ssm_object(response):
    aws_helpers.MockSsm.response = response
    return aws_helpers.MockSsm()


def nested_params():
    parameter_store.write("/service1/env/PARAMETER_IN_ENV",
                          False,
                          "String",
                          "Standard",
                          "1")
    parameter_store.write("/service1/env/ns1/NS1_PARAMETER",
                          False,
                          "String",
                          "Standard",
                          "ns1")
