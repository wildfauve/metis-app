import base64
import json
from functools import reduce

from aws_lambda_powertools.utilities.data_classes import (
    S3Event,
    APIGatewayProxyEvent,
    KafkaEvent,
    EventBridgeEvent
)
from aws_lambda_powertools.utilities.data_classes.s3_event import S3EventRecord
from aws_lambda_powertools.utilities.data_classes.kafka_event import KafkaEventRecord
from metis_fn import fn

from . import app_value, app_route, app_web_session

DEFAULT_S3_BUCKET_SEP = "."
NO_MATCHING_ROUTE = "no_matching_route"


def event_factory(event: dict,
                  factory_overrides: dict = None,
                  event_source_class=None) -> app_value.RequestEvent:
    if event_source_class:
        ev_fn, ev = event_match_fn_from_event_source(event, event_source_class)
    else:
        ev_fn, ev = dynamic_event_match(event)
    return ev_fn(ev, factory_overrides if factory_overrides else {})


def dynamic_event_match(event):
    ev_keys = event.keys()
    if 'Records' in ev_keys:
        return build_s3_state_change_event, S3Event(event)
    if 'httpMethod' in ev_keys:
        return build_http_event, APIGatewayProxyEvent(event)
    if 'eventSource' in ev_keys:
        return build_kafka_event, KafkaEvent(event)
    if 'source' in ev_keys:
        return build_event_bridge_event, EventBridgeEvent(event)
    return build_noop_event, event


def event_match_fn_from_event_source(event, event_source_cls):
    match event_source_cls.__name__:
        case 'S3Event':
            return build_s3_state_change_event, event_source_cls(event)
        case _:
            return build_noop_event, event


def build_noop_event(event: app_value.RequestEvent, _factory_overrides: dict = None) -> app_value.RequestEvent:
    template, route_fn, opts = route_fn_from_kind(NO_MATCHING_ROUTE)
    return app_value.NoopEvent(event=event,
                               kind=template,
                               request_function=route_fn)


def build_s3_state_change_event(event: S3Event, factory_overrides: dict) -> app_value.S3StateChangeEvent:
    objects = _s3_objects_from_event(event)
    factory = _domain_from_bucket_name if not factory_overrides.get('s3', None) else factory_overrides.get('s3', None)
    kind = factory(objects)
    template, route_fn, _opts = route_fn_from_kind(kind)
    return app_value.S3StateChangeEvent(event=event,
                                        kind=kind,
                                        request_function=route_fn,
                                        objects=objects)


def build_kafka_event(event: KafkaEvent, factory_overrides) -> app_value.KafkaRecordsEvent:
    evs = _kafka_events_from_event(event)
    factory = _domain_from_kafka_topic if not factory_overrides.get('kafka', None) else factory_overrides.get('kafka',
                                                                                                              None)
    kind = factory(evs)
    template, route_fn, _opts = route_fn_from_kind(kind)
    return app_value.KafkaRecordsEvent(event=event,
                                       kind=kind,
                                       request_function=route_fn,
                                       events=evs)


def build_event_bridge_event(event: EventBridgeEvent, factory_overrides) -> app_value.EventBridgePublishEvent:
    if not factory_overrides.get('eventbridge', None):
        factory = _domain_from_event_bridge_topic
    else:
        factory_overrides.get('eventbridge', None)

    kind = factory(event.detail_type)
    template, route_fn, _opts = route_fn_from_kind(kind)
    return app_value.EventBridgePublishEvent(topic=event.detail_type,
                                             kind=kind,
                                             event=event,
                                             body=event.detail,
                                             request_function=route_fn)


def build_http_event(event: APIGatewayProxyEvent,
                     _factory_overrides: dict) -> app_value.ApiGatewayRequestEvent:
    """
    method: str
    headers: dict
    resource: str
    body: str
    query_params: Optional[dict]=None
    """
    kind = _route_from_http_event(event.http_method, event.path)
    template, route_fn, opts = route_fn_from_kind(kind)
    hdrs = _standardise_headers(event.headers)
    body = _body_parser(opts, event)
    return app_value.ApiGatewayRequestEvent(kind=kind,
                                            request_function=route_fn,
                                            event=event,
                                            method=event['httpMethod'],
                                            headers=hdrs,
                                            path=event['path'],
                                            path_params=_path_template_to_params(kind[2], template[2]),
                                            body=body,
                                            query_params=event['queryStringParameters'],
                                            web_session=app_web_session.WebSession().session_from_headers(hdrs))


def _body_parser(route_options, event: APIGatewayProxyEvent):
    body = event.body
    if route_options and (parse_fn := route_options.get('body_parser', None)):
        return parse_fn(body)
    if event.is_base64_encoded:
        return base64.b64decode(body).decode('utf-8')
    return body


def route_fn_from_kind(kind):
    """
    Assumes that noop_event function is defined
    """
    return app_route.RouteMap().get_route(kind)


def _s3_objects_from_event(s3_event: S3Event) -> list[dict]:
    return [_s3_object(s3_event.bucket_name, record) for record in s3_event.records]


def _kafka_events_from_event(event: KafkaEvent) -> list[dict]:
    """
    Assumes that the event is in JSON
    """
    return [_kafka_event(record) for record in event.records]


def _domain_from_bucket_name(objects: list[app_value.S3Object]) -> str:
    """
    The handler is expected to deal with only 1 bucket as its a domain concept.  Multiple buckets
    indicate concern separation issues.
    """
    domain = {obj.bucket for obj in objects}
    if len(domain) > 1:
        return NO_MATCHING_ROUTE
    return domain.pop().split(DEFAULT_S3_BUCKET_SEP)[0]


def _domain_from_kafka_topic(events: list[KafkaEventRecord]) -> str:
    """
    The handler is expected to deal with only 1 topic as it's a domain concept.  Multiple buckets
    indicate concern separation issues.
    """
    domain = {ev.topic for ev in events}
    if len(domain) > 1:
        return NO_MATCHING_ROUTE
    return domain.pop()


def _domain_from_event_bridge_topic(topic) -> str:
    if not topic:
        return NO_MATCHING_ROUTE
    return topic


def _s3_object(bucket_name, record: S3EventRecord) -> app_value.S3Object:
    return app_value.S3Object(bucket=bucket_name,
                              key=record.s3.get_object.key)


def _kafka_event(record: KafkaEventRecord) -> app_value.KafkaTopicEvent:
    return app_value.KafkaTopicEvent(topic=record.topic,
                                     key=record.decoded_key if 'key' in record._data.keys() else None,
                                     value=record.json_value)


def _route_from_http_event(method, path):
    return ('API', method, path)


def _path_template_to_params(kind, template) -> dict:
    """
    Remove the leading "/"
    """
    return _params_comparer_builder(kind[1::].split("/"), template[1::].split("/"), {})


def _params_comparer_builder(kind_xs, template_xs, injector):
    template_fst, template_rst = fn.first(template_xs), fn.rest(template_xs)
    kind_fst, kind_rst = fn.first(kind_xs), fn.rest(kind_xs)
    if not template_fst:
        return injector
    if "{" in template_fst:
        return _params_comparer_builder(kind_rst,
                                        template_rst,
                                        {**injector, **{template_fst.replace("{", "").replace("}", ""): kind_fst}})
    return _params_comparer_builder(kind_rst, template_rst, injector)


def _standardise_headers(hdrs):
    def to_lower(acc, kv):
        k, v = kv
        acc[k.lower()] = v
        return acc

    return reduce(to_lower, hdrs.items(), {})
