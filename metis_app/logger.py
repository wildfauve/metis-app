import json
import logging
from typing import Any, Protocol

from metis_fn import singleton
from pino import pino
import time

from .tracer import Tracer
from . import json_util

class ConfiguredLoggerProtocol(Protocol):

    def info(self, meta: dict, msg: str, **kwargs):
        ...

    def warn(self, meta: dict, msg: str, **kwargs):
        ...

    def error(self, meta: dict, msg: str, **kwargs):
        ...

    def debug(self, meta: dict, msg: str, **kwargs):
        ...


class LogConfig(singleton.Singleton):
    """
    Configure the logger and log level for all logging.  When using the log functions in this module (info, error, etc)
    the logger configured in LogConfig will be used as the logger.  The default logger is the Pino logger.
    The configured logger must implement the ConfiguredLoggerProtocol
    Note also that when using powertools via the observable module, the configured logged is the Powertools Logger cls.
    """
    default_level: int = logging.INFO
    configured_logger: Any = None

    def clear(self):
        self.configured_logger = None
        if getattr(self, 'logging_level', None):
            self.logging_level = None
        return self

    def configure(self, level: str | int = None, custom_logger: Any = None):
        if level:  # don't override the current level
            if isinstance(level, str):
                self.logging_level = self._level_from_name(level)
            else:
                self.logging_level = level
        self.configured_logger = custom_logger if custom_logger else self._standard_logger(self.level)
        return self

    def _level_from_name(self, name):
        if (lvl := getattr(logging, name.upper())):
            return lvl
        return

    @property
    def logger(self):
        if not getattr(self, 'configured_logger', None):
            return self._standard_logger(self.level)
        return self.configured_logger

    @property
    def level(self):
        if not getattr(self, 'logging_level', None):
            return self.default_level
        return self.logging_level

    def _standard_logger(self, level):
        return pino(bindings={"apptype": "prototype", "context": "main"},
                    dump_function=custom_pino_dump_fn,
                    level=self._level_as_name(level))

    def _level_as_name(self, lvl):
        return logging.getLevelName(lvl).lower()


class PowerToolsLoggerWrapper(ConfiguredLoggerProtocol):
    """
    The powertools logger is required to be wrapped to support this modules log function signature, which is
    consistent with the Pino logger (that is, an optional first arg of a context dict, and the second arg as a
    msg str.  For the Powertools logger, the meta (the ctx + other state) is passes as kwargs.  Implying that the
    meta dict will not be logged as a 'ctx' key in the structured logs, rather will be at the top level.
    """

    def __init__(self, lgr):
        self.logger = lgr

    def info(self, meta, msg):
        self.logger.info(msg, **meta)

    def warning(self, meta, msg):
        self.logger.warning(msg, **meta)

    def error(self, meta, msg):
        self.logger.error(msg, **meta)

    def debug(self, meta, msg):
        self.logger.debug(msg, **meta)


def info(msg: str,
         ctx: dict | None = None,
         tracer: Tracer | None = None,
         **kwargs) -> None:
    _log('info', msg, tracer, ctx if ctx else {}, **kwargs)


def debug(msg: str,
          ctx: dict | None = None,
          tracer: Tracer | None = None,
          **kwargs) -> None:
    _log('debug', msg, tracer, ctx if ctx else {}, **kwargs)


def warn(msg: str,
         ctx: dict | None = None,
         tracer: Tracer | None = None,
         **kwargs) -> None:
    _log('warning', msg, tracer, ctx if ctx else {}, **kwargs)


def error(msg: str,
          ctx: dict | None = None,
          tracer: Tracer | None = None,
          **kwargs) -> None:
    _log('error', msg, tracer, ctx if ctx else {}, **kwargs)


def _log(level: str,
         msg: str,
         tracer: Any,
         ctx: dict[str, str],
         **kwargs) -> None:
    if level not in level_functions.keys():
        return
    level_functions.get(level, info)(logger(), msg, meta(tracer, ctx, **kwargs))


def with_perf_log(perf_log_type: str = None, name: str = None):
    """
    Decorator which wraps the fn in a timer and writes a performance log
    """

    def inner(fn):
        def invoke(*args, **kwargs):
            t1 = time.time()
            result = fn(*args, **kwargs)
            t2 = time.time()
            if perf_log_type == 'http' and 'name' in kwargs:
                fn_name = kwargs['name']
            else:
                fn_name = name or fn.__name__
            perf_log(fn=fn_name, delta_t=(t2 - t1) * 1000.0)
            return result

        return invoke

    return inner


def log_decorator(fn):
    def log_writer(*args, **kwargs):
        _log(
            level='info',
            msg='Handling Command {fn}'.format(fn=fn.__name__),
            ctx=args[0].event,
            tracer=args[0].tracer
        )
        return fn(*args, **kwargs)

    return log_writer


def custom_pino_dump_fn(json_log):
    return json.dumps(json_log, cls=json_util.CustomLogEncoder)


def logger():
    return LogConfig().logger


def _info(lgr, msg: str, meta: dict) -> None:
    lgr.info(meta, msg)


def _debug(lgr, msg: str, meta: dict) -> None:
    lgr.debug(meta, msg)


def _warn(lgr, msg: str, meta: dict) -> None:
    lgr.warn(meta, msg)


def _error(lgr, msg: str, meta: dict) -> None:
    lgr.error(meta, msg)


def perf_log(fn: str, delta_t: float, callback: callable = None):
    if callback:
        callback(fn, delta_t)
    info("PerfLog", fn=fn, delta_t=delta_t)


def meta(tracer, ctx: dict, **kwargs):
    _meta = {**trace_meta(tracer),
             **kwargs}
    if not ctx:
        return _meta
    return {**_meta, **ctx}


def trace_meta(tracer):
    return tracer.serialise() if tracer else {}


level_functions = {'info': _info, 'error': _error, 'warn': _warn, 'debug': _debug}
