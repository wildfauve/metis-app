import pytest

from datetime import datetime

from metis_app import logger, chronos

def it_coerses_non_serialisable_objects():
    serialise = logger.meta(tracer=None, status=200, ctx={'time': datetime(2021, 8, 2, 9, 5, tzinfo=chronos.tz_utc())})

    assert isinstance(serialise['ctx']['time'], str)

def it_removes_non_coersable_vals_from_ctx():
    serialise = logger.meta(tracer=None, status=200, ctx={'non_coerseable': lambda x: x,
                                                          'time': datetime(2021, 8, 2, 9, 5, tzinfo=chronos.tz_utc())})

    assert 'non_coerseable' not in serialise['ctx'].keys()
