class BaseError(Exception):

    def __init__(self,
                 message="",
                 name="",
                 ctx={},
                 request_kwargs: dict = {},
                 traceback=None,
                 code=500,
                 klass="",
                 exception_klass=None,
                 retryable=False):
        self.code = 500 if code is None else code
        self.retryable = retryable
        self.message = message
        self.name = name
        self.ctx = ctx
        self.klass = klass
        self.exception_klass = exception_klass
        self.traceback = traceback
        self.request_kwargs = request_kwargs
        super().__init__(self.message)

    def error(self):
        return {'error': self.message, 'code': self.code, 'step': self.name, 'ctx': self.ctx}

    def print(self):
        print(f"{self.message}\n\n{self.traceback}")


class ParameterStoreError(BaseError):
    ...
