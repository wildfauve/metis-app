from aws_lambda_powertools.metrics import MetricUnit
from metis_fn import monad


from metis_app import app, observable, logger, app_value

from . import env_helpers


@app.route(pattern=('API', 'GET', '/resourceBase/resource/{id1}'))
@observable.Observer().tracer.capture_method
def get_resource(request):
    def command(request):
        if request.event:
            pass
        obs = observable.Observer()
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


@observable.Observer().metrics.log_metrics(capture_cold_start_metric=True)
def handler_with_logging(event, ctx=None):
    return app.pipeline(event=event,
                        context=ctx,
                        env=env_helpers.Env(),
                        params_parser=noop_callable,
                        pip_initiator=noop_callable,
                        handler_guard_fn=noop_callable)


def noop_callable(value):
    return monad.Right(value)
