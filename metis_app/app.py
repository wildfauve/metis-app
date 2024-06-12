from functools import reduce
from aws_lambda_powertools.utilities.data_classes import (
    S3Event,
    APIGatewayProxyEvent,
    KafkaEvent)
from aws_lambda_powertools.utilities.data_classes.s3_event import S3EventRecord

from typing import Callable, Any, Type

from metis_fn import monad, fn, chronos
from . import (env as environment,
               span_tracer,
               logger,
               app_events,
               app_value,
               app_route,
               app_serialisers, observable)

DEFAULT_SUCCESS_HTTP_CODE = 200
DEFAULT_FAILURE_HTTP_CODE = 400

"""
App provides a number of helpers to build a Lambda event handling pipeline.  

@app.route
---------- 
Maintains simple routing state; mapping a function to a route "symbol.  The function will receive a app_value.Request object 
and is expected to pass it back wrapped in an monad.MEither, with the following state options (which will be understood by the 
app.responder fn.
+ monad.Right(app_value.Request.response), with a value JSON serialisable.
+ monad.Left(app_value.Request.response), with a value JSON serialisable.
+ monad.Left(app_value.Request), with error property containing an object which responds to 'error()' and returns a value JSON serialisable.

Example: 
@app.route('s3_bucket_name_part')
def run_a_handler(request: app_value.RequestEvent) -> monad.MEither:
    return handler(request=request)

Another approach is to use the 3-part tuple form for the route template.  This is useful when wanting to pattern match on the 
event.  For an API Gateway event, the event kind is constructed like this:

                        ('API', {METHOD}, {path-template}); for example...

> ('API', 'GET', '/resourceBase/resource/uuid1')

Therefore a route defined as follows will match this pattern:
> @app.route(('API', 'GET', '/resourceBase/resource/{id}'))

Additionally, the app_value.Request.event property will (an instance of ApiGatewayapp_value.RequestEvent) will include a 'path_params'
property (dict) which will extract the templated arguments; for example:

> {'id': uuid1}     

 

app.pipeline
------------
The main event pipeline handler.  Your lambda initiates the pipeline by calling this function with:
+ the aws event.
+ the aws event context
+ the env (as a str)
+ an optional request parser
+ an optional policy information point initiator
+ a handler guard condition function.

It parses the event, using hints within the event to determine the app.route to be called.
+ S3 events.  The object S3StateChangeEvent is created with a collection of S3Object.  S3StateChangeEvent.kind is 
              used to determine the app.route symbol.  The fn domain_from_bucket_name() collects the unique bucket names
              (there should only be one), and takes the most significant part based on the default separator (DEFAULT_S3_BUCKET_SEP)
              This then is the symbol expected on an app.route.  

On Errors.  Remember when you want your handler to generate an error that is parsable by the responder:
+ Use the request.error property to hold the error.
+ Unwrap any monad before adding to request.error.
+ Use app_value.AppError as a super type for your error as it sets up a JSON serialiser and returns it on the error() call wrapping the 
  exception message generated by the error.  You can implement your own in the fashion of the serialisers in app_serialisers 
"""

DEFAULT_RESPONSE_HDRS = {'Content-Type': 'application/json'}

Request = app_value.Request
RequestEvent = app_value.RequestEvent
ApiGatewayRequestEvent = app_value.ApiGatewayRequestEvent
S3StateChangeEvent = app_value.S3StateChangeEvent
S3Object = app_value.S3Object
KafkaRecordsEvent = app_value.KafkaRecordsEvent

Serialiser = app_serialisers.SerialiserProtocol
DictToJsonSerialiser = app_serialisers.DictToJsonSerialiser

AppError = app_value.AppError


def route(pattern, opts=None):
    return app_route.route(pattern, opts)


def pipeline(event: dict,
             context: dict,
             env: environment.EnvironmentProtocol,
             params_parser: Callable,
             pip_initiator: Callable,
             handler_guard_fn: Callable,
             event_source_cls: Type[S3Event | APIGatewayProxyEvent] | None = None,
             factory_overrides: dict = None):
    """
    Runs a general event handler pipeline.  Initiated by the main handler function.

    It takes the Lambda Event and Context objects.  It builds a request object and invokes the handler based on the event
    context and the routes provided by the handler via the @app.route decorator


    The main handler can then insert 3 functions to configure the pipeline:
    + params_parser: Mandatory.  Callable.  Takes the request object optionally transforms it, and returns it wrapper in an Either.
    + pip_initiator:  Mandatory.  Callable.  Policy Information Point
    + factory_overrides: Optional. dict.  Overrides the routing factory token constructor.  Only supports S3 overrides.  For an
                                          s3 override provide a dict in the form of {'s3': callable_function}
    + handler_guard_fn: A pre-processing guard fn to determine whether the handler should be invoked.  It returns an Either.  When the handler
                        shouldnt run the Either wraps an Exception.  In this case, the request is passed directly to the responder
    """

    request = pip_initiator(build_value(event,
                                        context,
                                        env,
                                        event_source_cls,
                                        factory_overrides if factory_overrides else {}).value)

    guard_outcome = handler_guard_fn(request)

    if guard_outcome.is_right():
        result = run_pipeline(request=request,
                              params_parser=params_parser)
    else:
        result = monad.Left(build_value(event=event,
                                        context=context,
                                        env=env,
                                        status_code=app_value.HttpStatusCode(guard_outcome.error().code),
                                        error=guard_outcome.error()).value)
    return responder(result)


def run_pipeline(request: monad.EitherMonad[app_value.Request],
                 params_parser: Callable):
    return request >> log_start >> params_parser >> route_invoker


def build_value(event,
                context,
                env,
                event_source_cls=None,
                factory_overrides: dict = None,
                status_code: app_value.HttpStatusCode = None,
                error=None) -> monad.EitherMonad[app_value.Request]:
    """
    Initialises the app_value.Request object to be passed to the pipeline
    """
    req = app_value.Request(event=app_events.event_factory(event, factory_overrides, event_source_cls),
                            context=context,
                            tracer=init_tracer(env=env, aws_context=context),
                            event_time=chronos.time_now(tz=chronos.tz_utc()),
                            observer=observable.Observer() if observable.Observer().is_configured else None,
                            pip=None,
                            response=None,
                            status_code=status_code,
                            error=error)
    return monad.Right(req)


def route_invoker(request):
    return request.event.request_function(request=request)


def template_from_route_fn(route_fn: Callable) -> str | tuple:
    return app_route.RouteMap().route_pattern_from_function(route_fn)


def log_start(request):
    logger.info(msg='Start Handler',
                tracer=request.tracer,
                ctx={'event': event_kind_to_log_ctx(request)})
    return monad.Right(request)


def event_kind_to_log_ctx(request: app_value.Request) -> str:
    return "{event_type}:{kind}".format(event_type=type(request.event).__name__, kind=request.event.kind)


def responder(request_or_error: monad.Either) -> dict:
    """
    The app_value.Request object must be returned with the following outcomes:
    + Wrapped in an Either.
    + 'response' property with the response to be sent wrapped in an Either.  The app_value.Request.value.result.value
      must be able to be serialised to JSON; using the Serialiser protocol
    + The app_value.Request can be Right, but the contained response is left.  In this case the response needs to implement an
      error() fn which returns an object serialisable to JSON.
    + Otherwise, app_value.Request.error() should be an Either-wrapping an object which responds to error() which is JSON serialisable
    + Finally, request_or_error may be a common-or-garden monad[app.AppError]
    """
    if request_or_error.is_left() and isinstance(request_or_error.error(), Exception):
        return _body_from_base_error(request_or_error.error())
    return _body_from_pipeline_response(request_or_error)


def _body_from_pipeline_response(request):
    response = {'multiValueHeaders': build_multi_headers(request.lift().event)}

    if request.is_right() and request.value.response.is_right():
        # When the processing pipeline completes successfully and the response dict is a success
        body = request.value.response.value
        response['headers'] = build_headers(request.value.response_headers, body)
        response['statusCode'] = request.value.status_code.value if request.value.status_code else 200
        response['body'] = body.serialise()
        status = 'ok'
    elif request.is_right() and request.value.response.is_left():
        # When the processing pipeline completes successfully but the response dict is a failure
        # Get the error property from the response and serialise this.
        body = request.value.response.error().error
        response['headers'] = build_headers(request.value.response_headers, body)
        response['statusCode'] = _error_status_code(request.value)
        response['body'] = body.serialise()
        status = 'fail'
    else:
        # When the processing pipeline fails, with the error in the 'error' property of the request.
        body = request.error().error.error()
        response['headers'] = build_headers(request.error().response_headers, body)
        response[
            'statusCode'] = request.error().status_code.value if request.error().status_code else DEFAULT_FAILURE_HTTP_CODE
        response['body'] = body.serialise()
        status = 'fail'

    logger.info(msg="End Handler", tracer=request.lift().tracer, ctx={}, status=status)

    return response


def _body_from_base_error(error: AppError):
    body = {'headers': {}, 'multiValueHeaders': {}}
    body['statusCode'] = error.code
    body['body'] = error.serialise()

    logger.info(msg="End Handler--with base Error",
                ctx={'error': error.message},
                status='fail')
    return body


def _error_status_code(request: Request):
    if isinstance(request.response, monad.MEither) and request.response.is_left():
        return request.response.error().code
    if request.status_code:
        return request.status_code
    return DEFAULT_SUCCESS_HTTP_CODE


def build_headers(hdrs: dict | None = None, returning_serialiser: Any | None = None) -> dict:
    if not hdrs and not returning_serialiser:
        return {}
    provided_headers = hdrs if hdrs else {}
    body_content_type = {'Content-Type': returning_serialiser.content_type} if returning_serialiser else {}
    return {**provided_headers, **body_content_type}


def build_multi_headers(event: app_value.RequestEvent) -> dict:
    """
    Only attempts to set headers for 'Set-Cookie' and mostly for session state
    """
    if event.returnable_session_state() and event.web_session:
        return event.web_session.serialise_state_as_multi_header()
    return {}


def init_tracer(env: env.EnvironmentProtocol, aws_context=None):
    aws_request_id = aws_context.aws_request_id if aws_context else None
    return span_tracer.SpanTracer(environment=env,
                                  kv={'handler_id': aws_request_id})
