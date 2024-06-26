from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from aws_lambda_powertools.utilities.data_classes import (
    S3Event,
    APIGatewayProxyEvent,
    KafkaEvent,
    EventBridgeEvent)

from . import tracer, error, app_serialisers, observable


class HttpStatusCode(Enum):
    OK = 200
    CREATED = 201
    BadRequest = 400
    Unauthorized = 401
    InternalServerError = 500


@dataclass
class DataClassAbstract:
    def replace(self, key, value):
        setattr(self, key, value)
        return self


@dataclass
class RequestEvent(DataClassAbstract):
    event: S3Event | APIGatewayProxyEvent | KafkaEvent | EventBridgeEvent
    kind: str
    request_function: Callable

    def returnable_session_state(self):
        return False


@dataclass
class S3Object(DataClassAbstract):
    bucket: str
    key: str
    event_time: Optional[datetime] = None
    object: Optional[list] = None
    meta: Optional[Dict] = None

    def s3_event_path(self):
        return "{bucket}/{key}".format(bucket=self.bucket, key=self.key)


@dataclass
class KafkaTopicEvent(DataClassAbstract):
    topic: str
    key: str | bytes
    value: str


@dataclass
class NoopEvent(RequestEvent):
    pass


@dataclass
class S3StateChangeEvent(RequestEvent):
    objects: List[S3Object]


@dataclass
class KafkaRecordsEvent(RequestEvent):
    events: List[KafkaTopicEvent]


@dataclass
class EventBridgePublishEvent(RequestEvent):
    topic: str
    body: dict


@dataclass
class ApiGatewayRequestEvent(RequestEvent):
    method: str
    headers: Dict
    path: str
    path_params: Dict
    body: str
    query_params: Optional[dict] = None
    web_session: Optional[Any] = None

    def clear_session(self):
        self.web_session = None
        self

    def returnable_session_state(self):
        return True


@dataclass
class Request(DataClassAbstract):
    event: RequestEvent
    context: dict
    tracer: tracer.Tracer
    observer: observable.Observer = None
    event_time: datetime = None
    app_request_context: Dict = None
    status_code: Optional[HttpStatusCode] = None
    request_handler: Optional[Callable] = None
    pip: Optional[dict] = None
    results: Optional[list] = None
    error: Optional[Any] = None
    response: Optional[dict] = None
    response_headers: Optional[dict] = None


class AppError(error.BaseError):
    @classmethod
    def dict_to_json_serialiser(cls):
        return app_serialisers.DictToJsonSerialiser

    def error(self):
        return type(self).dict_to_json_serialiser()(super().error())

    def as_dict(self):
        return super(type(self), self).error()

    def serialise(self):
        return self.error().serialise()
