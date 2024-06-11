from typing import List, Dict
import uuid

from . import env


class SpanTracer():

    def __init__(self,
                 environment: env.EnvironmentProtocol,
                 tags: list[str] = None,
                 kv: dict[str, str] = None,
                 span_id: str = None):
        self.environment = environment
        self.span_id = span_id if span_id else str(uuid.uuid4())
        self.tags = tags if tags else []
        self.kv = kv if kv else {}
        self.trace_id = uuid.uuid4()

    def span_child(self, tags: list[str] = [], kv: dict[str, str] = {}):
        child = SpanTracer(environment=self.environment,
                           span_id=self.span_id,
                           tags=tags,
                           kv=kv)
        return child

    def serialise(self):
        return {**{'env': self.environment.env,
                   'trace_id': self.uuid_to_s(self.trace_id),
                   'span_id': self.span_id,
                   'tags': self.tags}, **self.kv}

    def uuid_to_s(self, uu_id):
        return str(uu_id) if isinstance(uu_id, uuid.UUID) else uu_id

    def aws_request_id(self):
        return self.kv.get('handler_id', None)


def init_tracing(env):
    return SpanTracer(env)
