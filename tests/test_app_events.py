import pytest
from aws_lambda_powertools.utilities.data_classes import S3Event
from metis_fn import monad

from .shared import *

from metis_app import app, app_serialisers, app_value, pip, pdp, app_events


class UnAuthorised(app.AppError):
    pass

def it_creates_a_route_matched_on_string():
    template, route_fn, opts = app_events.route_fn_from_kind('hello')
    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'hello': 'there'}


def it_routes_based_on_tuple_and_template():
    template, route_fn, opts = app_events.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1/resource/uuid2'))

    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'resource': 'uuid1'}


def it_implements_the_serialiser_protocol_for_the_response():
    template, route_fn, opts = app_events.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1/resource/uuid2'))

    result = route_fn(dummy_request())

    assert result.value.response.value.serialisable == {'resource': 'uuid1'}
    assert result.value.response.value.serialise() == '{"resource": "uuid1"}'


def it_defaults_to_no_matching_routes_when_not_found():
    template, route_fn, opts = app_events.route_fn_from_kind("bad_route")

    result = route_fn(dummy_request())

    assert result.error().error.message == 'no matching route'


def it_finds_the_route_pattern_by_function():
    template, route_fn, opts = app_events.route_fn_from_kind(('API', 'GET', '/resourceBase/resource/uuid1'))

    assert app.template_from_route_fn(route_fn) == ('API', 'GET', '/resourceBase/resource/{id1}')


def it_parses_the_json_body(api_gateway_event_post_with_json_body):
    event = app_events.event_factory(api_gateway_event_post_with_json_body)

    assert event.body == {'test': 1}


#
# Request Builder Functions
#

def it_identifies_an_s3_event(s3_event_hello):
    event = app_events.event_factory(event=s3_event_hello)

    assert isinstance(event, app.S3StateChangeEvent)
    assert event.kind == 'hello'
    assert len(event.objects) == 1
    assert event.objects[0].bucket == 'hello'
    assert event.objects[0].key == 'hello_file.json'


def it_uses_the_event_source_cls(s3_event_hello):
    event = app_events.event_factory(event=s3_event_hello, event_source_class=S3Event)

    assert isinstance(event, app.S3StateChangeEvent)
    assert event.kind == 'hello'
    assert len(event.objects) == 1
    assert event.objects[0].bucket == 'hello'
    assert event.objects[0].key == 'hello_file.json'


def it_decodes_the_body_when_base64_encoded():
    event = app_events.event_factory(event=api_gateway_event_with_base64_encoded_body())
    assert event.body == 'grant_type=client_credentials'


def it_downcases_all_headers():
    event = app_events.event_factory(event=api_gateway_event_with_base64_encoded_body())
    assert set(event.headers.keys()) == {'content-type', 'authorization'}


def it_identifies_an_s3_event_using_custom_factory(s3_event_hello):
    event = app_events.event_factory(event=s3_event_hello, factory_overrides={'s3': overrided_s3_factory})

    assert isinstance(event, app.S3StateChangeEvent)
    assert event.kind == 'bonjour'
    assert len(event.objects) == 1
    assert event.objects[0].bucket == 'hello'
    assert event.objects[0].key == 'hello_file.json'


def it_identifies_an_api_gateway_get_event(api_gateway_event_get):
    event = app_events.event_factory(api_gateway_event_get)

    assert isinstance(event, app.ApiGatewayRequestEvent)

    assert event.kind == ('API', 'GET', '/resourceBase/resource/uuid1')
    assert event.request_function
    assert event.path_params == {'id1': 'uuid1'}
    assert event.headers
    assert event.query_params == {'param1': 'a', 'param2': 'b'}


def it_identifies_an_api_gateway_get_event_for_a_nested_resource(api_gateway_event_get_nested_resource):
    event = app_events.event_factory(api_gateway_event_get_nested_resource)

    assert isinstance(event, app.ApiGatewayRequestEvent)

    assert event.kind == ('API', 'GET', '/resourceBase/resource/uuid1/resource/resource-uuid2')
    assert event.request_function
    assert event.path_params == {'id1': 'uuid1', 'id2': 'resource-uuid2'}


def it_identifies_a_kafka_event(kafka_event):
    event = app_events.event_factory(event=kafka_event)

    assert isinstance(event, app.KafkaRecordsEvent)
    assert event.kind == 'hello-kafka'
    assert len(event.events) == 1
    assert event.events[0].value == {"event": "someevent"}

def it_handles_a_kafka_event_without_a_key(kafka_event_without_key):
    event = app_events.event_factory(event=kafka_event_without_key)

    assert isinstance(event, app.KafkaRecordsEvent)
    assert event.kind == 'hello-kafka'
    assert len(event.events) == 1
    assert event.events[0].value == {"event": "someevent"}


#
# Local Fixtures
#

#
# Helpers
#

def overrided_s3_factory(objects: List[app_value.S3Object]) -> str:
    domain = {object.bucket for object in objects}
    if len(domain) > 1:
        return app.NO_MATCHING_ROUTE
    return 'bonjour'


@app.route(pattern="hello")
def hello_handler(request):
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'hello': 'there'}))))


@app.route(pattern="bonjour")
def bonjour_handler(request):
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'bonjour': 'there'}))))


@app.route(pattern="no_matching_route")
def handler_404(request):
    return monad.Left(request.replace('error', app.AppError(message='no matching route', code=404)))


@app.route(pattern=('API', 'GET', '/resourceBase/JWTBang!/{id1}'))
def get_resource_with_jwt_failure(request):
    @pdp.token_pdp_decorator(name="app-test",
                             namespace="Testing",
                             error_cls=app.AppError)
    def command(request):
        if request.event:
            pass
        request.status_code = app_value.HttpStatusCode.CREATED
        return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))

    return command(request)


@app.route(pattern=('API', 'GET', '/resourceBase/resource/{id1}'))
def get_resource(request):
    def command(request):
        if request.event:
            pass
        request.status_code = app_value.HttpStatusCode.CREATED
        return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))
    return command(request)


@app.route(pattern=('API', 'GET', '/resourceBase/authz_resource/{id1}'))
def get_resource_protected_by_authz(request):
    result = get_authz_resource(request)
    request.status_code = app_value.HttpStatusCode(result.error().code)
    return monad.Left(request.replace('error', result.error()))


@pdp.activity_pdp_decorator("a_service", "service:resource:domain1:action1", None, UnAuthorised)
def get_authz_resource(request):
    pass  # because it will be unauthorised


@app.route(pattern=('API', 'GET', '/resourceBase/resource/{id1}/resource/{id2}'))
def get_nested_resource(request):
    if request.event:
        breakpoint()
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))


@app.route(pattern=('API', 'POST', '/resourceBase/resource/{id1}'),
           opts={'body_parser': app_serialisers.json_parser})
def get_nested_resource(request):
    return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))


def noop_callable(value):
    return monad.Right(value)


def failed_env_expectations(value):
    return monad.Left(app.AppError(message="Env expectations failure", code=500))


@pdp.token_pdp_decorator(name="a_service", error_cls=UnAuthorised)
def failed_token_expectation(value):
    return monad.Right(None)


def dummy_request():
    return app.Request(event={}, context={}, tracer={})


def pip_wrapper(request):
    request.pip = pip.pip(pip.PipConfig(), request)
    return monad.Right(request)


def change_path_to_authz_fn(event):
    event['path'] = '/resourceBase/authz_resource/uuid1'
    return event


def api_request_with_token(event, token=None):
    token_to_add = token if token else crypto_helpers.generate_signed_jwt(crypto_helpers.Idp().jwk)
    event['headers']['Authorization'] = event['headers']['Authorization'].replace("{}", token_to_add)
    return event
