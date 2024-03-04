import requests
import backoff
from typing import Dict, Tuple, Any
from metis_fn import monad

from . import http, logger, circuit

DEFAULT_MAX_RETRIES = 2

def determine_retries():
    return circuit.max_retries() or DEFAULT_MAX_RETRIES


@circuit.circuit_breaker()
@backoff.on_predicate(backoff.expo, circuit.http_retryable_monad_failure_predicate, max_tries=determine_retries(), jitter=None)
def post(endpoint,
         body,
         auth=None,
         headers={},
         encoding='json',
         circuit_state_provider=None,
         name: str = __name__,
         http_timeout: float=5.0):
    return post_invoke(endpoint=endpoint,
                       headers=headers,
                       auth=auth,
                       body=body,
                       encoding=encoding,
                       name=name,
                       http_timeout=http_timeout)

@monad.monadic_try(name="http_adapter", exception_test_fn=http.http_response_monad(__name__, http.extract_by_content_type))
@logger.with_perf_log(perf_log_type='http', name=__name__)
def post_invoke(endpoint: str, headers: Dict, auth: Tuple, body: Any, encoding: str, name: str, http_timeout: float):
    if encoding == 'json':
        return requests.post(endpoint, auth=auth, headers=headers, json=body, timeout=http_timeout)
    else:
        return requests.post(endpoint, auth=auth, headers={**headers, **encoding_to_content_type(encoding)}, data=body, timeout=http_timeout)

@circuit.circuit_breaker()
@backoff.on_predicate(backoff.expo, circuit.monad_failure_predicate, max_tries=determine_retries(), jitter=None)
def get(endpoint,
        auth=None,
        headers={},
        circuit_state_provider=None,
        name: str = __name__,
        http_timeout: float=5.0,
        exception_test_fn: callable=None,
        error_cls: Any=None):
    return get_invoke(endpoint=endpoint,
                      headers=headers,
                      auth=auth,
                      name=name,
                      http_timeout=http_timeout,
                      exception_test_fn=exception_test_fn,
                      error_cls=error_cls)


@monad.monadic_try(name="http_adapter",
                   exception_test_fn=http.http_response_monad(__name__, http.extract_by_content_type),
                   error_cls=http.HttpError)
@logger.with_perf_log(perf_log_type='http', name=__name__)
def get_invoke(endpoint: str,
               headers: Dict,
               auth: Tuple,
               name: str,
               http_timeout: float,
               exception_test_fn: callable,
               error_cls: Any):
    return requests.get(endpoint, auth=auth)


def encoding_to_content_type(encoding):
    encodings = {'urlencoded': {'Content-Type': 'application/x-www-form-urlencoded'}}
    return encodings.get(encoding, {})
