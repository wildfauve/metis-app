import logging
from typing import Any

from aws_lambda_powertools import Logger, Tracer, Metrics
from metis_app import logger as base_logger
from metis_fn import singleton, fn


class Observer(singleton.Singleton):
    """
    Observer is a singleton which initialises Powertools Tracer, Logger, and Metrics.  Additional observables may
    also be added.  There is nothing special about the observer class, except that it constructs the necessary
    AWS Lambda Powertools classes.
    """
    logger = None
    tracer = None
    metric = None
    other_observers = {}

    def clear(self):
        self.logger = None
        self.tracer = None
        self.metrics = None

    def configure(self,
                  service_name: str,
                  metrics_namespace: str,
                  logger: Any = Logger,
                  tracer: Any = Tracer,
                  metrics: Any = Metrics,
                  custom_log_level: int = logging.INFO,
                  post_init_fn: callable = fn.identity,
                  **kwargs):
        """
        Creates a Lambda powertools logger, tracer, and metrics instance, which are then available via the
        Observer as a singleton.
        Args:
            service_name: The canonical name of the service to appear on logs and traces,
            metrics_namespace: The namespace of metrics
            logger: A logger cls, defaults to the powertools Logger
            tracer: A tracer cls, defaults to the powertools Tracer
            metrics: A metrics cls, defaults to the powertools Metrics
            custom_log_level: int log level, overrides the level set in the env or the LogConfig.
            post_init_fn: callable: Optionally provide a fn which will be called with self once initialised.
                          Use to add initialisation steps to the powertools instances.
            **kwargs:  any additional observers can be added to the observer singleton by providing them as the last
                       kwargs.  Then call the kwarg name on the observer singleton.  If it does not exist, an
                       AttributeError is raised.
        Returns:
            self
        >>>  obs = Observer().configure(service_name="a", metrics_namespace="b", my_observer=MyObserver())
        >>> obs.my_observer
        MyObserver()
        """
        self.service_name = service_name
        self.metrics_namespace = metrics_namespace
        self.logger = self._configure_logger(logger, custom_log_level)
        self.tracer = self._configure_tracer(tracer, self.service_name)
        self.metrics = self._configure_metrics(metrics, self.metrics_namespace, self.service_name)
        self.other_observers = kwargs
        post_init_fn(self)
        return self

    def add_custom(self, **kwargs):
        """
        Adds a custom observer to the Observer singleton.  It is available via the function named for the custom
        observer key in the kwargs
        """
        self.other_observers = kwargs
        return self

    def _configure_metrics(self, metrics_cls, namespace, service):
        if metrics_cls:
            return metrics_cls(namespace=self.metrics_namespace, service=self.service_name)
        return Metrics(namespace=self.metrics_namespace, service=self.service_name)

    def _configure_tracer(self, tracer_cls, service):
        if tracer_cls:
            return tracer_cls(service=self.service_name)
        return Tracer(service=self.service_name)

    def _configure_logger(self, logger_cls: Logger | Any, custom_log_level: int):
        """
        Sets the required logger in the LogConfig singleton.
        When the logger is the Powertools logger (the default), it must be wrapped in PowerToolsLoggerWrapper.
        Otherwise, passes the custom logger through.
        For the powertools logger, the level will be set from the env var POWERTOOLS_LOG_LEVEL
        """
        lgr = logger_cls(service=self.service_name)
        if isinstance(lgr, Logger):
            base_logger.LogConfig().configure(custom_logger=base_logger.PowerToolsLoggerWrapper(lgr))
        else:
            base_logger.LogConfig().configure(level=custom_log_level, custom_logger=lgr)
        return lgr

    def __getattr__(self, name):
        def obs(obj_name):
            return self.other_observers.get(obj_name, None)

        if name not in self.other_observers.keys():
            raise AttributeError
        return obs(name)

    @property
    def is_configured(self):
        return self.logger and self.tracer and self.metrics
