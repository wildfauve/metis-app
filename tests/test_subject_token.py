from metis_fn import monad
from metis_app import subject_token, http_adapter, crypto as Cy, cache

from metis_crypto import jwk, jwt
import time

from .shared import *


class JwtPersistenceProvider(cache.KeyValueCachePersistenceProviderProtocol):

    def __init__(self):
        self.jwks = None

    def write(self, key, value):
        self.jwks = value
        return monad.Right(value)

    def read(self, key):
        self.value = self.jwks
        return monad.Right(self)


def setup_module():
    crypto_helpers.Idp().init_keys(jwk=jwk_rsa_key_pair())


def setup_function(fn):
    set_up_token_config()
    subject_token.jwk_cache_invalidate()


def test_get_jwks(jwks_mock):
    jwks = subject_token.cacheable_jwks()

    assert jwks.is_right()
    assert isinstance(jwks.value, jwk.JWKSet)

def test_jwks_are_persisted(jwks_mock):
    jwks = subject_token.cacheable_jwks()

    assert 'keys' in subject_token.SubjectTokenConfig().jwks_persistence_provider.read("JWKS").value.value

def test_read_jwks_from_cache(mocker):
    subject_token.SubjectTokenConfig().jwks_persistence_provider.write("JWKS", crypto_helpers.Idp().jwks_to_json())

    get_http_spy = mocker.spy(http_adapter, 'get_invoke')

    jwks = subject_token.cacheable_jwks()

    assert get_http_spy.call_count == 0
    assert isinstance(jwks.value, jwk.JWKSet)

def test_get_jwks_request_failure(jwks_request_failure_mock):
    jwks = subject_token.cacheable_jwks()

    assert jwks.is_left()
    assert jwks.error().name == "jwks_service"
    assert jwks.error().message == "http_failure"


def test_get_jwks_with_key_id(jwks_mock):
    jwks = subject_token.cacheable_jwks().value
    assert isinstance(jwks.get_key("1"), jwk.JWK)
    assert jwks.get_key("bad_key_id") is None


def test_generate_id_token_from_jwt(jwks_mock):
    jwt = crypto_helpers.generate_signed_jwt(crypto_helpers.Idp().jwk)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_right()
    assert id_token.value.id_claims().sub == "1@clients"


def test_token_failed_when_expired(jwks_mock):
    exp = (int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) - (60))
    jwt = crypto_helpers.generate_signed_jwt(crypto_helpers.Idp().jwk, exp)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_left()
    assert isinstance(id_token.error(), Cy.JwtDecodingError)
    assert "Expired at {}".format(exp) in id_token.error().message


def test_token_failed_when_jwks_failure(jwks_request_failure_mock):
    jwt = crypto_helpers.generate_signed_jwt(crypto_helpers.Idp().jwk)

    id_token = subject_token.parse_generate_id_token(jwt)

    assert id_token.is_left()
    assert isinstance(id_token.error(), subject_token.JwksGetError)
    assert id_token.error().message == "http_failure"


#
# Helpers
#
def set_up_token_config():
    subject_token.SubjectTokenConfig().configure(
        jwks_persistence_provider=JwtPersistenceProvider(),
        jwks_endpoint="https://idp.example.com/.well-known/jwks",
        asserted_iss="https://idp.example.com/")
