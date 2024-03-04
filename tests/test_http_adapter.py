import pytest
import requests

from metis_app import http_adapter, circuit

from .shared import *

def setup_module(module):
    circuit.CircuitConfiguration().configure(max_retries=1)


def test_success_http_call(request_mock):
    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"},
                               http_timeout=10.0)

    assert(result.is_right()) == True

    status, body = result.value

    assert status == 200
    assert body == {'hello': 'there'}


def test_failed_http_call(request_http_failure_mock):
    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"})

    assert(result.is_left()) == True
    assert(result.error().ctx) == {'status': 'boom'}
    assert(result.error().code) == 401

def test_failed_http_call_with_circuit(request_http_failure_mock,
                                       circuit_state_provider):
    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"},
                               circuit_state_provider=circuit_state_provider)

    assert(result.is_left()) == True
    assert circuit_state_provider.circuit_state == 'half_open'

def test_failed_http_call_performs_backoff_retry(request_http_2_call_retryable_failure_mock,
                                                 circuit_state_provider,
                                                 mocker):
    circuit.CircuitConfiguration().configure(max_retries=2)

    post_invoke_spy = mocker.spy(http_adapter, 'post_invoke')

    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"},
                               circuit_state_provider=circuit_state_provider)

    assert result.is_left() == True
    assert result.error().retryable
    assert circuit_state_provider.circuit_state == 'half_open'
    assert post_invoke_spy.call_count == 2
    circuit.CircuitConfiguration().configure(max_retries=1)

def test_failed_non_retryable_http_call_no_backoff_retry(request_http_non_retryable_failure_mock,
                                                         circuit_state_provider,
                                                         mocker):
    circuit.CircuitConfiguration().configure(max_retries=2)

    post_invoke_spy = mocker.spy(http_adapter, 'post_invoke')

    result = http_adapter.post(endpoint="https://example.host/resource",
                               auth=None,
                               body={'a': "mock_body"},
                               circuit_state_provider=circuit_state_provider)

    assert result.is_left() == True
    assert not result.error().retryable
    assert circuit_state_provider.circuit_state == 'half_open'
    assert post_invoke_spy.call_count == 1
    circuit.CircuitConfiguration().configure(max_retries=1)


@pytest.fixture
def request_mock(requests_mock):
    requests_mock.post("https://example.host/resource", json={'hello': "there"}, headers={'Content-Type': 'application/json; charset=utf-8'})


@pytest.fixture
def request_http_failure_mock(requests_mock):
    requests_mock.post("https://example.host/resource",
                       json={'status': "boom"},
                       status_code=401,
                       headers={'Content-Type': 'application/json; charset=utf-8'})


@pytest.fixture
def request_http_2_call_retryable_failure_mock(requests_mock):
    requests_mock.post("https://example.host/resource",
                       [{'json': {'status': "boom"}, 'status_code': 500, 'headers': {'Content-Type': 'application/json; charset=utf-8'}},
                        {'json': {'status': "boom"}, 'status_code': 500, 'headers': {'Content-Type': 'application/json; charset=utf-8'}}])

@pytest.fixture
def request_http_non_retryable_failure_mock(requests_mock):
    requests_mock.post("https://example.host/resource",
                       json={'status': "boom"},
                       status_code=401,
                       headers={'Content-Type': 'application/json; charset=utf-8'})