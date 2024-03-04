import uuid

class Tracer():

    def __init__(self, env, aws_context=None):
        self.env = env
        self.aws_context = aws_context
        self.handler_id = uuid.uuid4()

    def serialise(self):
        return {'env': self.env, 'handler_id': self.handler_id_to_s(), 'aws_request_id': self.aws_request_id()}

    def handler_id_to_s(self):
        return str(self.handler_id) if isinstance(self.handler_id, uuid.UUID) else self.handler_id

    def aws_request_id(self):
        return self.aws_context.aws_request_id if self.aws_context else None


def init_tracing(env):
    return Tracer(env)
