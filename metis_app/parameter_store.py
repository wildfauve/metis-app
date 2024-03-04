from typing import Tuple
import os
from pymonad.tools import curry
from metis_fn import monad
from metis_app import aws_client_helpers

"""
Warning: only set_env_from_parameter_store works generally at the mo.

set_env_from_parameter_store
----------------------------
Reads from a Path in AWS Parameter Store (SSM) and injects each parameter as an environment variable.
Provide the path to the variables.
The SSM client is expected to be available via the aws_client_helpers.aws_ctx function, or optionally, it can be passed in
"""

def set_env_from_parameter_store(path: str, ssm_client = None):
    return monad.Right(get_ssm_client(ssm_client)) >> get_parameters(path) >> set_env >> test_set

def write(key: str, param: str) -> monad.MEither:
    """
    Implements a cache style interface that take a key/value
    and writes it to Parameter Store
    """
    return monad.Right(ssm_client()) >> put_parameter(key, param) >> build_parameter(key, param)

def get_parameter_from_store(key):
    return get_parameter(key, ssm_client())
#
# Helpers
#

def set_env(parameters):
    return monad.Right(list(map(set_env_var, parameters['Parameters'])))

def test_set(results):
    return monad.Right(results)

def set_env_var(parameter) -> Tuple:
    name = parameter['Name'].split("/")[-1]
    os.environ[name] = parameter['Value']
    return monad.Right(('ok', name, parameter['Value']))

def aws_error_test_fn(result):
    statuses = {'200': True}
    if result.is_right() and statuses.get(str(result.value['ResponseMetadata']['HTTPStatusCode']), None):
        return result
    else:
        return monad.Left(error.ServiceError(result.value['ResponseMetadata']['HTTPHeaders']))

@curry(2)
@monad.monadic_try(name="get_parameters", exception_test_fn=aws_error_test_fn)
def get_parameters(path, client):
    return client.get_parameters_by_path(Path=path, WithDecryption=True)

@monad.monadic_try(name="get_parameter", exception_test_fn=aws_error_test_fn)
def get_parameter(key, client):
    return client.get_parameter(Name=parameter_link(key), WithDecryption=True)

@curry(3)
@monad.monadic_try(name="put parameter", exception_test_fn=aws_error_test_fn)
def put_parameter(key, param, client):
    return client.put_parameter(Name=parameter_link(key),
                                Value=param,
                                Type='SecureString',
                                Overwrite=True)

@curry(3)
def build_parameter(key, param, _response):
    return monad.Right({'Name': parameter_link(key), 'Value': param})

def parameter_link(key):
    return "{}{}".format(parameter_path(), key)

def get_ssm_client(ssm_client):
    if ssm_client:
        return ssm_client
    return aws_client_helpers.aws_ctx().ssm
