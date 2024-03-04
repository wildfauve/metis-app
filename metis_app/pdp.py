from typing import Callable, Any, Optional, List
from pymonad.tools import curry
from collections import namedtuple
from metis_fn import monad, fn

from . import pip, app

activity_token = ":"

pdp_value = namedtuple("PdpValue", "pip, name, ctx, namespace, activities, decisions")

#
# PDPs
#
def token_pdp(pdp_value):
    """
    Interrogates the PIP which holds the id_token to determine it is valid.  The ID Token has been inserted in
    the PIP by the app being configured to use the subject_token module.

    The id_token in the PIP MUST be present and it MUST be valid according to the logic in the fn crypto.decode_jwt.
    """
    pdp_value.decisions.append(pdp_value.pip.token_valid())
    return pdp_value

def activity_pdp(pdp_value) -> monad.MEither:
    """
    Takes Activities from an activity collection, and tests the provided context against them.
    Example:
        $ activity_policy(['service:resource:action:action1'])("service:resource:action:action2")
    """
    if pdp_value.activities is None:
        return False
    pdp_value.decisions.append(any(activity_matcher(pdp_value.ctx, activity) for activity in
                                   filter_for_service(pdp_value.namespace, pdp_value.activities)))
    return pdp_value


#
# Decorators
#
def pdp_decorator(name: str,
                  pdps: List[callable],
                  ctx: str = None,
                  namespace: Optional[str] = None,
                  error_cls: Any = None):
    """
    A general PDP decorator.  It can run any PDP, the callables are provided in the pdps list.
    """

    def inner(f):
        def invoke(*args, **kwargs):
            pip = _get_pip(args, kwargs)
            if pip is None:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

            results = fn.compose_iter(pdps, pdp_value(pip, name, ctx, namespace, pip.subject.value.activities(), []))

            if all(results.decisions):
                return f(*args, **kwargs)
            else:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

        return invoke

    return inner


def token_pdp_decorator(name: str,
                        ctx: str = None,
                        namespace: Optional[str] = None,
                        error_cls: Any = None,
                        pdp: callable = token_pdp):
    """
    Policy to check the presence and validity of a bearer token.

    The decorated function must have a kwarg called "pip" which is an instance of pip.PipConfig.
    + The pip has fn "id_token", which returns a monad whose value is a token; id_token: monad.EitherMonad[crypto.IdToken]
    """

    def inner(fn):
        def invoke(*args, **kwargs):
            pip = _get_pip(args, kwargs)
            if pip is None or pip.id_token is None:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

            result = pdp(pdp_value(pip, name, ctx, namespace, pip.subject_activities(), []))

            if all(result.decisions):
                return fn(*args, **kwargs)
            else:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

        return invoke

    return inner

def _get_pip(args, kwargs):
    if args and isinstance(args[0], pip.Pip):
        return args[0]
    if (pip_from_kw:=kwargs.get('pip', None)):
        return pip_from_kw
    if args and isinstance(args[0], app.Request):
        return args[0].pip
    if (req_from_kw:=kwargs.get('request', None)):
        return req_from_kw.pip
    return None


def activity_pdp_decorator(name: str,
                           ctx: str,
                           namespace: Optional[str] = None,
                           error_cls: Any = None,
                           pdp: callable = activity_pdp):
    """
    Adds activity-based policy checking to the function.

    + name: (str); to be included in the error_cls on error.
    + ctx:  (str); the activity being tested against.
    + namespace (Optional[str])
    + error_cls: (Optional[Any]); In the case of an authorisation error, the error class to be used to encapsulate the failure.
                 If not provides, a monad wrapped str is returned.

    The decorated function must have a kwarg called "pip" which is an instance of pip.PipConfig.
    + The pip has fn "subject", which returns a monad whose value has an activities fn which returns List[str].
      pip.PipConfig implements this protocol
      e.g pip.subject.value.activities => ['activity1', 'activity2']
    """

    def inner(fn):
        def invoke(*args, **kwargs):
            pip = kwargs.get('pip', None)
            if pip is None:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

            result = pdp(pdp_value(pip=pip,
                                   name=name,
                                   ctx=ctx,
                                   namespace=namespace,
                                   activities=pip.subject_activities(),
                                   decisions=[]))


            if all(result.decisions):
                return fn(*args, **kwargs)
            else:
                return monad.Left(error_cls(message="Unauthorised",
                                            name=name,
                                            code=401)) if error_cls else monad.Left("Unauthorised")

        return invoke

    return inner


#
# Helpers
#

def filter_for_service(namespace, activities: list) -> list:
    if not namespace:
        return activities
    return list(filter(lambda ct: namespace in ct, activities))


@curry(2)
def activity_matcher(context, activity):
    return matcher(fn.rest(context.split(activity_token)), fn.rest(activity.split(activity_token)))


def matcher(ctx_xs: list, activity_xs: list):
    ctx_fst, ctx_rst = fn.first(ctx_xs), fn.rest(ctx_xs)
    act_fst, act_rst = fn.first(activity_xs), fn.rest(activity_xs)
    if ctx_fst is None:
        return True
    if not ismatch(ctx_fst, act_fst):
        return False
    return matcher(ctx_rst, act_rst)


def ismatch(ctx_token, act_token):
    return act_token == "*" or ctx_token == act_token
