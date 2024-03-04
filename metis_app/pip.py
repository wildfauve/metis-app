from dataclasses import dataclass, field
from typing import Protocol, Any, List, Optional
from pymonad.tools import curry

from metis_fn import fn, monad

from . import subject_token, crypto
"""
Take a request and adds a Policy information Object.

The request must contain a header containing the bearer token.  This will be parsed and the result (which may be a failure) 
is available in the PIP for a PEP to interrogate.  The token is validated by the subject_token module.  This must have been
configured with the JWKS endpoint to allow for JWT signature validation.

The PIP is controlled by the apps handler.  If it is used, it must provide the following:
+ pip_config.  An instance of PipConfig with the following properties:
    + userinfo. Bool.  Whether to get userinfo or not.  The default is False.  This means pip will not cache the subject.
    + userinfo_fn.  A function which returns the result of the userinfo endpoint.  The result must be in the form of a 
                    standard OIDC claims set, and must have a 'sub' claim.

To use the PIP with the app handler, add a wrapper function which calls pip with its config and the app.request object:
The wrapper must add the generated PIP to the request.pip property.  For example:
   > request.pip = pip.pip(pip.PipConfig(), request)
   > return monad.Right(request)


"""

@dataclass
class PipConfig:
    validate_id_token: bool = True
    userinfo: bool = False
    userinfo_get_fn: callable = None
    parse_generate_id_token_fn: Optional[callable] = field(default_factory=lambda: subject_token.parse_generate_id_token)

    def execute_userinfo_get(self):
        return self.userinfo and self.userinfo_get_fn


class UserinfoStateProtocol(Protocol):
    def __init__(self, state: Any):
        ...

    def activities(self) -> List[str]:
        """
        Returns a list of str activities providing for activity information to be provided for an activity-based decision
        """
        ...


@dataclass
class Pip:
    id_token: monad.EitherMonad[crypto.IdToken] = None
    subject: monad.EitherMonad[UserinfoStateProtocol] = None

    def token_valid(self):
        return self.id_token and self.id_token.is_right()

    def subject_activities(self):
        if not self.subject or self.subject.is_left() or not self.subject.value.activities():
            return None
        return self.subject.value.activities()

@curry(2)
def pip(config: PipConfig, request):
    info = Pip(id_token=jwt_parser(config, request))

    return fn.compose_iter([userinfo(config)], info)

@curry(2)
def userinfo(config, pip):
    if not pip.token_valid():
        return pip
    if (not config.execute_userinfo_get()) and pip.token_valid():
        return pip

    pip.subject = config.userinfo_get_fn(pip.id_token)

    return pip

def jwt_parser(config, request) -> monad.Either[Any, crypto.IdToken]:
    if config.validate_id_token:
        return config.parse_generate_id_token_fn(subject_token.parse_bearer_token(request.event.headers))
    return None
