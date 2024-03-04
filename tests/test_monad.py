import pytest
from pymonad.tools import curry
from metis_fn import monad

from metis_app import error

def test_try_success():
    assert success_function().is_right()


def test_custom_expection_test_fn():
    assert success_function_with_custom_success().is_left()


def test_exception_calls_error_return_fn():
    expected_result = {'error_fn':{'error': 'division by zero', 'code': 500, 'step': 'exception_thrower', 'ctx': {}}}
    assert exception_thrower(error_result_fn_arg={'error_fn': None}) == expected_result


#
# Helpers
#
def turn_true_into_error(result):
    if result.is_right() and result.value:
        return monad.Left(True)
    return result


@curry(2)
def wrap_error_in_dict(arg, result):
    arg.update({'error_fn': result.error().error()})
    return arg

@monad.monadic_try()
def success_function():
    return True


@monad.monadic_try(exception_test_fn=turn_true_into_error)
def success_function_with_custom_success():
    return True


@monad.monadic_try(error_result_fn=wrap_error_in_dict, error_cls=error.BaseError, status=500)
def exception_thrower(error_result_fn_arg):
    return 1/0
