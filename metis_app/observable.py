from aws_lambda_powertools import Logger, Tracer, Metrics

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

    def configure(self,
                  service_name: str,
                  metrics_namespace: str,
                  post_init_fn: callable = fn.identity,
                  **kwargs):
        """
        Creates a Lambda powertools logger, tracer, and metrics instance, which are then available via the
        Observer as a singleton.
        Args:
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
        self.logger = Logger(service=self.service_name)
        self.tracer = Tracer(service=self.service_name)
        self.metrics = Metrics(namespace=self.metrics_namespace, service=self.service_name)
        self.other_observers = kwargs
        post_init_fn(self)
        return self

    def __getattr__(self, name):
        def obs(obj_name):
            return self.other_observers.get(obj_name, None)

        if name not in self.other_observers.keys():
            raise AttributeError
        return obs(name)

    @property
    def is_configured(self):
        return self.logger and self.tracer and self.metrics
