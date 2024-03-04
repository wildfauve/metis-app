import collections.abc
import sys
from metis_fn import chronos

def nested_coerse(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = nested_coerse(d.get(k, {}), v)
        else:
            if type(v) in [str, int, bool, float, list]:
                d[k] = v
            else:
                coerse_fn = getattr(sys.modules[__name__], "coerser_{}".format(type(v).__name__), None)
                if coerse_fn:
                    d[k] = coerse_fn(v)
    return d

def coerser_datetime(dt):
    return chronos.iso8601()(dt)
