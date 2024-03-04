from typing import Dict, Tuple
from pymonad.tools import curry
import requests

from metis_fn import monad
from . import error

class HttpError(error.BaseError):
    pass

class BearerTokenAuth(requests.auth.AuthBase):
    """
    Custom Bearer token Authn
    """
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


def extract_fn_raw(response):
    return response.text

def extract_fn_json(response):
    return response.json()

def extract_fn_text(response):
    return response.text()

def extract_by_content_type(response):
    """
    Looks for the content type in the response; e.g. application/json; charset=utf-8
    and find the appropriate extract fn and apply the response to that fn.  Otherwise return raw.
    """
    factory = {'application/json': extract_fn_json, 'application/text': extract_fn_text}
    return factory.get(response.headers['Content-Type'].split(";")[0], extract_fn_raw)(response)

@curry(3)
def http_response_monad(step, extract_fn, response) -> Tuple[int, dict]:
    """
    Only 200-series http status codes are successes.  400 and 500 series are failures.
    It is assumed that a REST call to a service will not return a 300-series code.
    """
    if response.value.status_code in [200,201]:
        return monad.Right((response.value.status_code, extract_fn(response.value)))
    else:
        return monad.Left(HttpError(message=format_error(response.value),
                                    name=step,
                                    code=response.value.status_code,
                                    ctx=extract_fn(response.value),
                                    retryable=http_retryable_status(response.value.status_code)))

def http_retryable_status(code):
    return code >= 500

def format_error(resp: requests.models.Response) -> str:
    return "HTTP Error Response; {mth} ; {url} ; {reason}".format(mth=resp.request.method,
                                                                  url=resp.request.url,
                                                                  reason=resp.reason)