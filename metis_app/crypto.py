import json
from typing import Tuple, Union, Optional
from metis_crypto import jwk, jwt
from pymonad.tools import curry
import collections

from metis_fn import monad, chronos
from . import error

class JwtDecodingError(error.BaseError):
    pass

class IdToken:
    claims_value = collections.namedtuple('IdTokenClaims', ['iss', 'sub', 'aud', 'iat', 'exp', 'azp'])

    def __init__(self, jwt, claims=None):
        self.jwt = jwt
        self.claims = claims

    def id_claims(self):
        return self.claims_value(iss=self.claims['iss'],
                                 sub=self.claims['sub'],
                                 aud=self.claims['aud'],
                                 iat=self.claims['iat'],
                                 exp=self.claims['exp'],
                                 azp=self.claims['azp'])

    def sub(self):
        return self.claims['sub']
    
    def exp(self):
        return self.claims['exp']

    def expired(self):
        return self.exp() < int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))


def parse_generate_id_token(serialised_jwt, jwks=None, claims_to_assert=None):
    """
    Takes an encoded JWT and returns an verified id_token
    """
    return monad.Right(jwks) >> decode_jwt(claims_to_assert, serialised_jwt) >> to_id_token

def bearer_token_valid(serialised_jwt: str) -> bool:
    return parse_generate_id_token(serialised_jwt) >> validate
#
# Helpers
#

def validate(token):
    return not token.expired()

@curry(3)
@monad.monadic_try(name="decode_jwt", status=401, error_cls=JwtDecodingError)
def decode_jwt(claims_to_assert, serialised_jwt: str, jwks: Optional[jwk.JWKSet]) -> Tuple:
    """
    Parses the jwt, validing the signature (from JWKS) and the EXP/AUD claims
    """
    if jwks is None:
        return serialised_jwt, json.loads(jwt.JWT(jwt=serialised_jwt).token.objects['payload'])
    return serialised_jwt, jwt.JWT(jwt=serialised_jwt, key=jwks, check_claims=claims_to_assert)


def to_id_token(jwt_claims: Tuple[str, Union[dict, jwt.JWT]]):
    """
    Takes a Tuple of the serialised JWT and one of a dict or jwt.JWT.
    When a Dict is provided is it assumed to be the already decoded claims; this occurs when the JWT is not decoded with a JWK
    """
    serialised_jwt, decoded_jwt = jwt_claims
    if isinstance(decoded_jwt, dict):
        return monad.Right(IdToken(serialised_jwt, decoded_jwt))
    return monad.Right(IdToken(serialised_jwt, (json.loads(decoded_jwt.claims))))


def bearer_token_hdr(jwt):
    return {'authorization': "Bearer {}".format(jwt)}
