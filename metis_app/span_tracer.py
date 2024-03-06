from typing import List, Dict
import uuid

class SpanTracer():

    def __init__(self, env, tags: List[str]=[], kv: Dict[str, str]={}, span_id: str=None):
        self.env = env
        self.span_id = span_id if span_id else str(uuid.uuid4())
        self.tags = tags
        self.kv = kv
        self.trace_id = uuid.uuid4()

    def span_child(self, tags: List[str]=[], kv: Dict[str, str]={}):
        child = SpanTracer(env=self.env,
                           span_id=self.span_id,
                           tags=tags,
                           kv=kv)
        return child

    def serialise(self):
        return {**{'env': self.env,
                 'trace_id': self.uuid_to_s(self.trace_id),
                 'span_id': self.span_id,
                 'tags': self.tags}, **self.kv}

    def uuid_to_s(self, uu_id):
        return str(uu_id) if isinstance(uu_id, uuid.UUID) else uu_id

    def aws_request_id(self):
        return self.kv.get('handler_id', None)


def init_tracing(env):
    return SpanTracer(env)
