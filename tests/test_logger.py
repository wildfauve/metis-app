import pytest

from datetime import datetime
from metis_fn import chronos, monad

from metis_app import logger


def it_coerses_non_serialisable_objects():
    result = try_logging("Test", ctx={'time': chronos.time_now()})
    assert result.is_right()


def it_removes_non_coersable_vals_from_ctx():
    result = try_logging("Test", status=200, ctx={'non_coerseable': lambda x: x,
                                                  'time': chronos.time_now()})

    assert result.is_left()


@monad.Try()
def try_logging(msg, ctx):
    logger.info("Test", status=200, ctx={'time': chronos.time_now()})
