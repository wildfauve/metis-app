from dataclasses import dataclass
from functools import partial
from typing import Callable
import os
from metis_fn import monad, fn, singleton
from metis_app import aws_client_helpers, error

SecureString = "SecureString"
String = "String"


class ParameterConfiguration(singleton.Singleton):
    """
    Optionally set up configuration in the situation where keys can be passed in without a path.
    The default path is configured here.
    """

    def configure(self,
                  root_path: str,
                  update_test_fn: Callable | None = fn.identity):
        self.root_path = root_path
        self.update_test_fn = update_test_fn
        pass

    def fn_for_update_test(self):
        if (f := getattr(self, 'update_test_fn', None)):
            return f
        return fn.identity


@dataclass
class ParameterState:
    state: str
    name: str
    value: str


"""
set_env_from_parameter_store
----------------------------
Reads from a Path in AWS Parameter Store (SSM) and injects each parameter as an environment variable.
Provide the path to the variables.
The SSM client is expected to be available via the aws_client_helpers.aws_ctx function, or optionally, it can be passed in
"""


def set_env_from_parameter_store(path: str, client=None):
    result = (monad.Right(ssm_client(client)) >>
              partial(get_parameters, path) >>
              set_env >>
              test_set)
    return result


def writer(key: str,
           mutate_env: bool = True,
           value_type: str = SecureString) -> Callable:
    """
    A HOF.  Allows for the partial application of a PS write function.  Returns the write fn
    which then takes the value to write and an optional builder fn which can transform the parameter
    before setting the env.
    :param key: The PS Key
    :param mutate_env: bool; whether to update os.environ with the read written parameter
    :param value_type: String | SecureString.  Defaults to SecureString
    :return:
    """
    return partial(write, key, mutate_env, value_type)


def write(key: str,
          mutate_env: bool,
          value_type: str,
          value: str,
          builder: Callable = fn.identity) -> monad.Either:
    """
    Implements a cache style interface that take a key/value
    and writes it to Parameter Store
    """
    result = (monad.Right(ssm_client())
              >> partial(put_parameter, value_type, key, value)
              >> partial(build_parameter, key, value, builder)
              >> partial(set_env_var, mutate_env))
    return result


def get_parameter_from_store(key, with_decryption: bool = True):
    return get_parameter(key, ssm_client(), with_decryption)


#
# Helpers
#

def set_env(parameters):
    return monad.Right(list(map(partial(set_env_var, True), parameters['Parameters'])))


def test_set(results):
    return monad.Right(results)


def set_env_var(mutate_env: bool, parameter) -> monad.Either[error.ParameterStoreError, ParameterState]:
    if not mutate_env:
        return monad.Right(ParameterState(state="ok",
                                          name=parameter['Name'],
                                          value=parameter['Value']))
    name = parameter['Name'].split("/")[-1]
    os.environ[name] = parameter['Value']
    return monad.Right(ParameterState(state="ok",
                                      name=name,
                                      value=parameter['Value']))


def aws_error_test_fn(result):
    statuses = {'200': True}
    if result.is_right() and statuses.get(str(result.value['ResponseMetadata']['HTTPStatusCode']), None):
        return result
    else:
        return monad.Left(error.ParameterStoreError(result.value['ResponseMetadata']['HTTPHeaders']))


@monad.monadic_try(name="get_parameters",
                   exception_test_fn=aws_error_test_fn,
                   error_cls=error.ParameterStoreError)
def get_parameters(path, client):
    result = client.get_parameters_by_path(Path=path, WithDecryption=True, Recursive=True)
    return result


@monad.monadic_try(name="get_parameter",
                   exception_test_fn=aws_error_test_fn,
                   error_cls=error.ParameterStoreError)
def get_parameter(key, client, with_decryption: bool = True):
    return client.get_parameter(Name=key if _is_absolute_path(key) else parameter_link(key),
                                WithDecryption=with_decryption)


@monad.monadic_try(name="put parameter",
                   exception_test_fn=aws_error_test_fn,
                   error_cls=error.ParameterStoreError)
def put_parameter(value_type, key, value, client):
    if ParameterConfiguration().fn_for_update_test()(key):
        return update_parameter(value_type, key, value, client)
    return create_parameter(value_type, key, value, client)


def create_parameter(value_type, key, param, client):
    result = client.put_parameter(Name=key if _is_absolute_path(key) else parameter_link(key),
                                  Value=param,
                                  Type=value_type,
                                  Overwrite=False)
    return result


def update_parameter(value_type, key, value, client):
    result = client.put_parameter(Name=key if _is_absolute_path(key) else parameter_link(key),
                                  Value=value,
                                  Type=value_type,
                                  Overwrite=True)
    return result


def build_parameter(key, param, builder, _response):
    return monad.Right({'Name': key, 'Value': builder(param)})


def parameter_link(key):
    return "{}{}".format(parameter_path(), key)


def parameter_path():
    return ParameterConfiguration().root_path


def _is_absolute_path(key):
    return "/" in key


def ssm_client(ssm_client=None):
    if ssm_client:
        return ssm_client
    return aws_client_helpers.aws_ctx().ssm
