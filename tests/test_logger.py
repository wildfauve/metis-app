import pytest

from datetime import datetime
from metis_fn import chronos, monad

from metis_app import logger


def it_coerses_non_serialisable_objects():
    result = try_logging("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


def it_writes_error_log():
    result = try_error_logging("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


def it_writes_debug_log():
    result = try_debug_logging("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


def it_writes_warn_log():
    result = try_warn_logging("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


def it_removes_non_coersable_vals_from_ctx():
    result = try_logging("Test", status=200, ctx={'non_coerseable': lambda x: x,
                                                  'time': chronos.time_now()})

    assert result.is_left()


def it_takes_kwargs_as_context():
    result = try_logging_with_kw_ctx("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


@monad.Try()
def try_logging(msg, ctx):
    logger.info("Test", status=200, ctx={'time': chronos.time_now()})


@monad.Try()
def try_debug_logging(msg, ctx):
    logger.LogConfig().configure(level="debug")
    logger.debug("Test", status=200, ctx={'time': chronos.time_now()})


@monad.Try()
def try_warn_logging(msg, ctx):
    logger.debug("Test", status=200, ctx={'time': chronos.time_now()})


@monad.Try()
def try_error_logging(msg, ctx):
    logger.error("Test", status=200, ctx={'time': chronos.time_now()})


@monad.Try()
def try_logging_with_kw_ctx(msg, ctx):
    logger.info("Test",
                status=200,
                ctx=ctx,
                timeStamp=chronos.time_now(),
                aKey1=1,
                aKey2=2)
