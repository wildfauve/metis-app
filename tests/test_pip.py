from metis_fn import monad
from metis_app import pip, app, subject_token

from .shared import *


def setup_module():
    crypto_helpers.Idp().init_keys(jwk=jwk_rsa_key_pair())


def setup_function(fn):
    set_up_token_config()
    subject_token.jwk_cache_invalidate()


def test_returns_pip_with_valid_token(api_gateway_event_get, jwks_mock):
    result = pip.pip(pip.PipConfig(), api_request(api_gateway_event_get))

    assert isinstance(result, pip.Pip)
    assert result.id_token.is_right()
    assert result.id_token.value.sub() == "1@clients"


def test_failures_to_validate_token(api_gateway_event_get, jwks_mock):
    result = pip.pip(pip.PipConfig(), api_request(api_gateway_event_get, token="bad_token"))

    assert not result.token_valid()


def test_fails_find_a_token(api_gateway_event_get, jwks_mock):
    api_gateway_event_get['headers'].pop('Authorization')
    result = pip.pip(pip.PipConfig(), api_request(api_gateway_event_get, no_token=True))

    assert not result.token_valid()


def test_dont_get_userinfo_on_invalid_token(api_gateway_event_get, jwks_mock):
    config = pip.PipConfig(userinfo=True,
                           userinfo_get_fn=get_userinfo_mock)

    result = pip.pip(config, api_request(api_gateway_event_get, token="bad_token"))

    assert not result.token_valid()
    assert not result.subject


def test_gets_userinfo(api_gateway_event_get,
                       jwks_mock):
    config = pip.PipConfig(userinfo=True,
                           userinfo_get_fn=get_userinfo_mock)
    result = pip.pip(config, api_request(api_gateway_event_get))
    assert result.subject.is_right()


def test_userinfo_meets_protocol_for_getting_activities(api_gateway_event_get,
                                                        jwks_mock):
    config = pip.PipConfig(userinfo=True,
                           userinfo_get_fn=get_userinfo_mock)
    result = pip.pip(config, api_request(api_gateway_event_get))

    assert result.subject.value.activities() == ['activity1', 'activity2']


def test_doesnt_throw_error_when_cache_provider_not_set(api_gateway_event_get,
                                                        jwks_mock):
    config = pip.PipConfig()
    result = pip.pip(config, api_request(api_gateway_event_get))

    assert result.token_valid()


#
# Helpers
#
def set_up_token_config():
    subject_token.SubjectTokenConfig().configure(jwks_endpoint="https://idp.example.com/.well-known/jwks",
                                                 asserted_iss="https://idp.example.com/")


def api_request(event, no_token: bool = False, token=None):
    if not no_token:
        token_to_add = token if token else crypto_helpers.generate_signed_jwt(crypto_helpers.Idp().jwk)
        event['headers']['Authorization'] = event['headers']['Authorization'].replace("{}", token_to_add)
    return app.Request(event=app.event_factory(event), context={}, tracer={})


def get_userinfo_mock(id_token):
    class Subject(pip.UserinfoStateProtocol):
        def __init__(self, state):
            self.state = state

        def activities(self):
            return self.state['activities']

    return monad.Right(Subject(state={'sub': 'subject1', 'activities': ['activity1', 'activity2']}))
