from typing import Optional, List, Dict, Tuple, Callable, Any, Protocol
import json

from metis_fn import monad


class SerialiserProtocol(Protocol):
    def __init__(self, serialisable: Any, serialisation: Callable):
        ...

    def serialise(self):
        ...

    @property
    def content_type(self):
        ...


class DictToJsonSerialiser(SerialiserProtocol):
    CONTENT_TYPE = "application/json"

    def __init__(self, serialisable, serialisaton=None):
        self.serialisable = serialisable
        self.serialisation = serialisaton

    def serialise(self):
        return json.dumps(self.serialisable)

    @property
    def content_type(self):
        return self.__class__.CONTENT_TYPE


class DictToJsonLDSerialiser(DictToJsonSerialiser):
    CONTENT_TYPE = "application/ld+json"


def json_parser(body: str) -> str:
    """
    Attempts to parse the body as JSON.  If it fails it just returns the body
    """
    parsed = try_parser(json.loads, body)
    if parsed.is_right():
        return parsed.value
    return body


@monad.monadic_try()
def try_parser(parser_fn, content):
    return parser_fn(content)


def noon_parser(body: str) -> str:
    return body
