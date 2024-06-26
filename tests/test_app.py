import pytest
from metis_fn import monad

from .shared import *

from metis_app import app, app_serialisers, app_value, pip, subject_token, pdp


class UnAuthorised(app.AppError):
    pass

#
# Pipeline Functions
#

def it_executes_a_pipeline_from_s3_event(set_up_env,
                                         s3_event_hello):
    result = app.pipeline(event=s3_event_hello,
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)
    assert result['statusCode'] == 200
    assert result['headers']['Content-Type'] == 'application/json'
    assert result['body'] == '{"hello": "there"}'


def it_fails_on_expectations():
    result = app.pipeline(event={},
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=failed_env_expectations)
    assert result['statusCode'] == 500
    assert result['headers'] == {'Content-Type': 'application/json'}
    assert result['body'] == '{"error": "Env expectations failure", "code": 500, "step": "", "ctx": {}}'


def it_executes_the_noop_path():
    result = app.pipeline(event={},
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)
    assert result['statusCode'] == 400
    assert result['headers'] == {'Content-Type': 'application/json'}
    assert result['body'] == '{"error": "no matching route", "code": 404, "step": "", "ctx": {}}'


def it_adds_the_session_as_a_cookie(set_up_env,
                                    api_gateway_event_get):
    result = app.pipeline(event=api_gateway_event_get,
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)

    assert result['multiValueHeaders'] == {'Set-Cookie': ['session=session_uuid', 'session1=session1_uuid']}


def it_returns_a_201_created(set_up_env,
                             api_gateway_event_get):
    result = app.pipeline(event=api_gateway_event_get,
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=noop_callable,
                          handler_guard_fn=noop_callable)
    assert result['statusCode'] == 201


#
# Authorisation
#

def it_returns_a_subject_activities_401_unauthorised(set_up_env,
                                                     api_gateway_event_get,
                                                     set_up_mock_idp,
                                                     jwks_mock):
    subject_token.SubjectTokenConfig().configure(jwks_endpoint="https://idp.example.com/.well-known/jwks",
                                                 jwks_persistence_provider=None,
                                                 asserted_iss=None)

    result = app.pipeline(event=api_request_with_token(change_path_to_authz_fn(api_gateway_event_get)),
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=pip_wrapper,
                          handler_guard_fn=failed_token_expectation)
    assert result['statusCode'] == 401


def it_returns_a_invalid_token_401_unauthorised(set_up_env,
                                                api_gateway_event_get,
                                                set_up_mock_idp,
                                                jwks_mock):
    subject_token.SubjectTokenConfig().configure(jwks_endpoint="https://idp.example.com/.well-known/jwks",
                                                 jwks_persistence_provider=None,
                                                 asserted_iss=None)

    result = app.pipeline(event=api_request_with_token(api_gateway_event_get, "bad_token"),
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=pip_wrapper,
                          handler_guard_fn=failed_token_expectation)

    assert result['statusCode'] == 401


def test_fails_find_a_token(set_up_env,
                            api_gateway_event_get):
    api_gateway_event_get['headers'].pop('Authorization')
    api_gateway_event_get['path'] = '/resourceBase/JWTBang!/uuid1'

    result = app.pipeline(event=api_gateway_event_get,
                          context={},
                          env=Env(),
                          params_parser=noop_callable,
                          pip_initiator=pip_wrapper,
                          handler_guard_fn=noop_callable)

    body = json.loads(result['body'])
    assert body['error'] == "Unauthorised"
    assert body['code'] == 401


#
# Request Builder Functions
#

def it_includes_a_time_in_the_request(api_gateway_event_get):
    request = app.build_value(event=api_gateway_event_get,
                              context={},
                              env=Env())
    assert isinstance(request.value.event_time, datetime.datetime)



#
# Local Fixtures
#
@pytest.fixture
def set_up_mock_idp():
    crypto_helpers.Idp().init_keys(jwk=jwk_rsa_key_pair())


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
