from aws_lambda_powertools import Logger, Tracer, Metrics

from metis_fn import singleton


class Observer(singleton.Singleton):
    logger = None
    tracer = None
    metric = None

    def configure(self, service_name: str, metrics_namespace: str) -> None:
        self.service_name = service_name
        self.metrics_namespace = metrics_namespace
        self.logger = Logger(service=self.service_name)
        self.tracer = Tracer(service=self.service_name)
        self.metrics = Metrics(namespace=self.metrics_namespace, service=self.service_name)
        return self


    @property
    def is_configured(self):
        return self.logger and self.tracer and self.metrics
