from typing import Tuple, Protocol, Union, Callable
from metis_crypto import jwk, jwt
from pymonad.tools import curry
from simple_memory_cache import GLOBAL_CACHE
import re

from metis_fn import monad, singleton, chronos
from . import http_adapter, http, circuit, error, crypto, cache

jwks_cache = GLOBAL_CACHE.MemoryCachedVar('jwks_cache')

event_authorisation_hdr_key = "Authorization"

JWKS = "JWKS"  # name in cache


class JwksGetError(error.BaseError):
    pass


class SubjectTokenConfig(singleton.Singleton):
    """
    The Subject Token config is setup by the library caller to provide 2 arguments:

    + jwks_endpoint. Returns the endpoint of the IDP for the JWKS call.
    + circuit_state_provider.  An implementation of the CircuitStateProviderProtocol
    + asserted_iss: The iss must be asserted when decoding the JWT.  Provide the iss str as it will appear in the JWT
    """

    def configure(self,
                  jwks_endpoint: str,
                  asserted_iss: str = "",
                  jwks_persistence_provider: cache.KeyValueCachePersistenceProviderProtocol = None,
                  circuit_state_provider: circuit.CircuitStateProviderProtocol = None):
        self.jwks_persistence_provider = jwks_persistence_provider
        self.jwks_endpoint = jwks_endpoint
        self.circuit_state_provider = circuit_state_provider
        self.asserted_iss = asserted_iss
        pass


def parse_generate_id_token(serialised_jwt):
    """
    Takes an encoded JWT and returns an verified id_token
    """
    if not serialised_jwt:
        return monad.Left(JwksGetError('No JWT found', code=401))
    return cacheable_jwks() >> crypto.decode_jwt(claims_to_assert(), serialised_jwt) >> crypto.to_id_token


def claims_to_assert():
    return {'iss': SubjectTokenConfig().asserted_iss,
            'exp': int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()]))}


def cacheable_jwks():
    return jwks_cache.get()


@jwks_cache.on_first_access
def _jwks():
    """
    Takes a key id (kid), requests the jwks from the identity jwks well-known service,
    returning a monadic jwt.JWKkeys
    """
    return monad.Right(jwks_resource()) >> jwks_from_cache >> get_jwks >> cache_jwks >> jwks_from_json


def jwk_cache_invalidate():
    jwks_cache.invalidate()

def cache_jwks(jwks: Tuple[int, str]):
    _status, keys = jwks
    if SubjectTokenConfig().jwks_persistence_provider:
        SubjectTokenConfig().jwks_persistence_provider.write(JWKS, keys)
    return monad.Right(jwks)

@monad.monadic_try(name="jwks_from_json")
def jwks_from_json(jwks: Tuple[int, str]):
    """
    Takes a JSON JWKS keyset and returns a wrapper object
    """
    _status, keys = jwks
    return jwk.JWKSet.from_json(keys)


@curry(3)
@monad.monadic_try(name="")
def rsa_key_from_kid(kid, op, jwks):
    """
    Takes a jwks object, extracts a public key based on KID and returns an
    openssl.rsa._RSAPublicKey
    """
    return jwks.get_key(kid).get_op_key(op)


def jwks_from_cache(endpoint):
    if not SubjectTokenConfig().jwks_persistence_provider:
        return monad.Right((endpoint, None))

    result = cache_reader(SubjectTokenConfig().jwks_persistence_provider)

    if result is None or result.is_left():
        return monad.Right((endpoint, None))
    return monad.Right((endpoint, result.value.value))


def cache_reader(provider: cache.KeyValueCachePersistenceProviderProtocol):
    if not hasattr(provider, 'read'):
        return None
    return provider.read(key=JWKS)


def get_jwks(endpoint_tuple: Tuple[str, Union[str, None]]):
    """
    Get the JWKS json from the Identity well known resource.
    Inject the http_status_exception to test for a Right from the request, but a failure HTTP status

    The endpoint tuple has the jwks_endpoint and either None or jwks obtained from cache
    """
    endpoint, jwks = endpoint_tuple
    if not jwks:
        return http_adapter.get(endpoint=endpoint,
                                name='jwks_service',
                                circuit_state_provider=SubjectTokenConfig().circuit_state_provider,
                                exception_test_fn=http.http_response_monad(__name__, http.extract_fn_raw),
                                error_cls=JwksGetError)

    return monad.Right((200, jwks))


def jwks_resource():
    return SubjectTokenConfig().jwks_endpoint


def parse_bearer_token(hdrs: dict) -> str | None:
    """
    Takes HTTP hdrs and extracts the bearer token from the Authorization header
    Support Camel and lowercase versions of the header
    """
    auth_hdr = hdrs.get(event_authorisation_hdr_key, hdrs.get(event_authorisation_hdr_key.lower()))
    if not auth_hdr:
        return None
    bearer_group = re.search(r'(Bearer)\s(.*)', auth_hdr)
    if not bearer_group or len(bearer_group.groups()) != 2:
        return None
    return bearer_group.group(2)


def bearer_token_hdr(jwt):
    return {'authorization': "Bearer {}".format(jwt)}
