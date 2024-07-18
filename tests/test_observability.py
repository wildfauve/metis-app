from .shared import *

from aws_lambda_powertools.metrics import MetricUnit
from metis_fn import monad

from metis_app import app, observable, app_value, logger

obs = observable.Observer().configure(service_name="test-service", metrics_namespace='module1')


def it_uses_the_configured_logger_tracer_and_metrics_from_powertools(set_up_env,
                                                                     api_gateway_event_get):
    result = handler(api_gateway_event_get, aws_context_obj())
    assert result['statusCode'] == 201


#
# Helpers
#
@obs.metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, ctx=None):
    return app.pipeline(event=event,
                        context=ctx,
                        env=Env(),
                        params_parser=noop_callable,
                        pip_initiator=noop_callable,
                        handler_guard_fn=noop_callable)


@app.route(pattern=('API', 'GET', '/resourceBase/resource/{id1}'))
@obs.tracer.capture_method
def get_resource(request):
    def command(request):
        if request.event:
            pass
        obs.tracer.put_annotation(key="Resource", value=request.event.path_params.get('id1'))
        # Directly use the Powertools logger
        obs.logger.info("Search for resource", uuid=request.event.path_params.get('id1'))
        obs.logger.error("error-example")
        obs.logger.warning("warn-example")
        obs.logger.debug("debug-example")
        # use logger wrapper
        logger.info("Info test")
        logger.warn("Warning test")
        logger.error("Error test")
        logger.debug("Debug test")

        obs.metrics.add_metric(name="Resource:Search", unit=MetricUnit.Count, value=1)

        request.observer.logger.info("logging from logger in request")

        request.status_code = app_value.HttpStatusCode.CREATED
        return monad.Right(request.replace('response', monad.Right(app.DictToJsonSerialiser({'resource': 'uuid1'}))))

    return command(request)


def noop_callable(value):
    return monad.Right(value)
