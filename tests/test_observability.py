from dataclasses import dataclass, field

from .shared import *

from metis_app import app, observable, app_value, logger


@dataclass
class CustomPowertoolsLogger(logger.ConfiguredLoggerProtocol):
    service: str
    msgs: list = field(default_factory=lambda: [])

    def info(self, meta, msg):
        self.msgs.append(('info', msg, meta))


@dataclass
class CustomObserver:
    counter: int

    def inc(self):
        self.counter += 1
        return self


def setup_function():
    observable.Observer().clear()
    logger.LogConfig().clear()
    observable.Observer().configure(service_name="test-service",
                                    metrics_namespace='module1',
                                    custom_observer=CustomObserver(counter=0))


def it_uses_a_custom_logger(set_up_env):
    obs_custom_logger = observable.Observer().configure(service_name="test-service",
                                                        metrics_namespace='module1',
                                                        logger=CustomPowertoolsLogger,
                                                        custom_observer=CustomObserver(counter=0))

    logger.info("a", other_prop=1)
    assert len(obs_custom_logger.logger.msgs) == 1


def it_uses_the_configured_logger_tracer_and_metrics_from_powertools(set_up_env,
                                                                     api_gateway_event_get):
    from tests.shared import mock_handlers
    result = mock_handlers.handler_with_logging(api_gateway_event_get, aws_context_obj())
    assert result['statusCode'] == 201


def it_holds_any_observer_like_cls():
    obs = observable.Observer()
    obs.custom_observer.inc()

    assert obs.custom_observer.counter == 1

def it_adds_a_custom_observer_cls_after_construction():
    obs = observable.Observer()
    obs.add_custom(another_custom=CustomObserver(counter=0))
    obs.another_custom.inc()

    assert obs.another_custom.counter == 1



#
# Helpers
#

