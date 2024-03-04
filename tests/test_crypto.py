import pytest

from metis_app import crypto

from .shared import crypto_helpers as fixture_crypto

def setup_module():
    fixture_crypto.Idp().init_keys(jwk=fixture_crypto.jwk_rsa_key_pair())

def test_extract_claims_from_token():
    jwt = fixture_crypto.generate_signed_jwt(fixture_crypto.Idp().jwk)

    result = crypto.parse_generate_id_token(jwt, fixture_crypto.Idp().jwks_from_json())

    assert result.is_right()

    assert result.value.id_claims().sub == "1@clients"

def test_malformed_jwt():
    result = crypto.parse_generate_id_token(fixture_crypto.Idp().jwks_from_json(), "malformed")

    assert result.is_left()
