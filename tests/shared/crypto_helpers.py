import pytest
from jwcrypto import jwk, jws, jwt
import json
import time
from typing import Tuple
import requests

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from metis_fn import chronos, singleton

"""
Test fixtures for JWTs and JWKS

Example:
    To generate a serialised and signed JWT for inbound API tests (that is, events which include a Bearer token
    in the HTTP headers):
        $ key = rsa_private_key()
        $ jwt = generate_signed_jwt(key)

Example:
    To generate a JWK Set (JWKS) to simulate the /.well-known/jwks.json of an OpenID Connect Authorisation Service:
        $ rsa_key = rsa_key_pair(kid="kid_id_1")
        $ jwks = jwk_key_set(rsa_key)

"""

class Idp(singleton.Singleton):
    def init_keys(self, jwk):
        self.jwk = jwk
        pass

    def jwks(self):
        return jwk_key_set(self.jwk)

    def jwks_to_json(self):
        return json.dumps(self.jwks())

    def jwks_from_json(self):
        return jwk.JWKSet.from_json(json.dumps(self.jwks()))


@pytest.fixture
def jwks_mock(requests_mock):
    """
    create a requests mock for getting the JWKSet.
    """
    requests_mock.get("https://idp.example.com/.well-known/jwks",
                      json=Idp().jwks(),
                      headers={'Content-Type': 'application/json; charset=utf-8'})
    return requests_mock


@pytest.fixture
def jwks_request_failure_mock(requests_mock):
    requests_mock.get("https://idp.example.com/.well-known/jwks",
                      exc=requests.exceptions.ConnectionError('http_failure'))


def rsa_private_key():
    """
    Args:
        kid: a unique id for the key

    Returns:
        JWK pub/priv key pair with a KID
    """
    return rsa.generate_private_key(backend=default_backend(), public_exponent=65537, key_size=2048)


@pytest.fixture
def rsa_key_pair_as_jwk(kid="1"):
    """
    Args:
        kid: a unique id for the key

    Returns:
        JWK pub/priv key pair with a KID
    """
    return jwk_rsa_key_pair(kid=kid)


def jwk_rsa_key_pair(kid="1"):
    return jwk.JWK.generate(kty='RSA', size=2048, kid=kid)


def generate_signed_jwt(jwk, exp=None):
    """
    Generates an RSA signed JWT is serialised form
    """
    token = jwt.JWT(header={"alg": "RS256", "kid": jwk.kid}, claims=jwt_claims(exp))
    token.make_signed_token(jwk)
    return token.serialize()


@pytest.fixture
def generate_expired_signed_jwt():
    """
    Generates an RSA signed JWT is serialised form which is expired
    """
    token = jwt.JWT(header={"alg": "RS256", "kid": Idp().jwk.kid}, claims=jwt_claims_expired())
    token.make_signed_token(Idp().jwk)
    return token.serialize()


@pytest.fixture
def generate_valid_signed_jwt():
    return generate_signed_jwt(Idp().jwk)


def jwk_key_set(rsa_key_pair_as_jwk):
    """
    Takes an RSA key pair and returns a JWKS containing the public key
    """
    priv, pub = jwk_to_key_pair(rsa_key_pair_as_jwk)
    return dict(keys=[json.loads(pub)])


def jwk_to_key_pair(pair) -> Tuple:
    """
    Returns a tuple of the priv and pub keys as a JSON encoded JWK
    """
    return pair.export_private(), pair.export_public()


def jwt_claims_expired():
    claims = jwt_claims((int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) - (60 * 60)))
    return claims


def jwt_claims(exp):
    return dict(iss="https://idp.example.com/",
                sub="1@clients",
                aud="https://api.example.com",
                iat=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])),
                exp=exp or (int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])) + (60 * 60 * 24)),
                azp="CJ5HhFu2H303aKMukkW9SDhJS1mQVzVD",
                gty="client-credentials")
