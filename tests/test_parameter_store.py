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