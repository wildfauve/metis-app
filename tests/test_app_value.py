import pytest

from metis_app.app_value import AppError

def test_error_cls_serialisation():
    error = AppError(message="An Error Message", code=500)

    assert error.error().serialise() == '{"error": "An Error Message", "code": 500, "step": "", "ctx": {}}'

def test_error_as_dict():
    error = AppError(message="An Error Message", code=500)

    assert error.as_dict() == {'error': 'An Error Message', 'code': 500, 'step': '', 'ctx': {}}

