from typing import Tuple, Callable, Any, Protocol
from simple_memory_cache import GLOBAL_CACHE

from metis_fn import chronos, monad, singleton
from . import http_adapter, crypto, random_retry_window, logger, circuit, cache
from .tracer import Tracer

expected_envs = ['client_id',
                 'client_secret']

token_cache = GLOBAL_CACHE.MemoryCachedVar('token_cache')

BEARER_TOKEN = "BEARER_TOKEN"  # Name of bearer token in PS

_CTX = {}

def env_set_up(env):
    return all(getattr(env, var)() for var in expected_envs)


class Error(Exception):
    def __init__(self, message="", name="", ctx={}, code=500, klass="", retryable=False):
        self.code = 500 if code is None else code
        self.retryable = retryable
        self.message = message
        self.name = name
        self.ctx = ctx
        self.klass = klass
        super().__init__(self.message)

    def error(self):
        return {'error': self.message, 'code': self.code, 'step': self.name, 'ctx': self.ctx}

    def duplicate_error(self):
        return "Duplicate" in self.message


class TokenError(Error):
    pass


class TokenEnvError(Error):
    pass


"""
The token config is setup by the library caller to provide 4 arguments:

+  token_persistence_provider.  This is a caller provided class or function which is provided with a token for persisting.
   It also allows self_token to request a previously persisted token.  The token_persistence_provider must provide the following interfaces:
   + write.  Takes a key and a value and persists the token (value) with the key (key).  It must return a monad result.
   + read. Takes a key and returns an monad wrapping an object which responds to value which returns the token.
+  env.  An object which provides the following methods:
   + client_id.  Returns the client id of the service for making token requests.
   + client_secret. Returns the client secret of the service for making token requests.
   + identity_token_endpoint. Returns the endpoint for the token request (client credentials grant).
   + bearer_token.  Returns the bearer token if it exists in the env.
   + set_env_var_with_value.  Takes a key and value and writes it to the env for retieval later with the bearer_token method.
     Returns Tuple('ok', key, value)
+ window_width.  Int in seconds defining the width of the token getting window (used for randomly selecting a position to reduce
                 competing lambdas from obtaining the token at the same time).
+ expiry_threshold. Int in seconds.  The number of seconds before the token expires that it will be refreshed.
"""


class TokenConfig(singleton.Singleton):
    default_window_width = (60 * 60)  # chance of refreshing token within 1 hour band
    default_expiry_threshold = (60 * 60)  # The room to leave before the actual token expiry

    def configure(self,
                  token_persistence_provider: cache.KeyValueCachePersistenceProviderProtocol,
                  env: Any,
                  env_ready_test_fn: Callable = env_set_up,
                  circuit_state_provider: circuit.CircuitStateProviderProtocol = None,
                  window_width: int = default_window_width,
                  expiry_threshold: int = default_expiry_threshold) -> None:
        self.token_persistence_provider = token_persistence_provider
        self.env = env
        self.env_ready_test_fn = env_ready_test_fn
        self.circuit_state_provider = circuit_state_provider
        self.window_width = window_width
        self.expiry_threshold = expiry_threshold
        pass


def token(tracer: Tracer = None):
    _CTX['tracer'] = tracer
    if not TokenConfig().env_ready_test_fn(TokenConfig().env):
        return monad.Left(TokenEnvError(message="Token can not the retrieved due to a failure in env setup"))
    result = get()
    if result.is_right() and (result.value.expired() or in_token_retry_window(result.value)):
        logger.info(msg='Self Token Cache Miss',
                    ctx={'expired': result.value.expired(), 'in_window': in_token_retry_window(result.value)},
                    tracer=tracer_from_ctx())
        invalidate_cache()
        return get()
    return result


def get():
    result = cacheable_token()
    if result.is_right():
        return crypto.parse_generate_id_token(result.value)
    else:
        return result


def cacheable_token():
    return token_cache.get()


def invalidate_cache():
    token_cache.invalidate()
    pass


@token_cache.on_first_access
def get_token():
    """
    First ever access is when the token is not set in parameter store and hence the environment:
        + Check the env anyway
        + get a new token from the token service
        + write it to parameter store
        + add it to the env and return it
    All other scenarios; when in env in either expired or not expired state
        + Get from Env
        + get a new token from the token service (check whether expired)
        + write it to parameter store (only when expired)
        + add it to the env and return it (only when expired)
    """
    # returns Either((status, name, value))
    result = bearer_token_from_env() >> from_cache >> token_service >> cache

    if result.is_right():
        return monad.Right(result.value[2])
    else:
        return result


def token_service(bearer_token):
    if bearer_token and crypto.bearer_token_valid(bearer_token) and not_in_token_retry_window(bearer_token):
        if bearer_token_from_env().value is None:
            return monad.Right(('from_cache', bearer_token))
        else:
            return monad.Right(('from_env', bearer_token))

    if bearer_token:
        not_in_wind = not_in_token_retry_window(bearer_token)
        token_state = (crypto.bearer_token_valid(bearer_token), crypto.parse_generate_id_token(bearer_token).value.exp())
    else:
        not_in_wind = None
        token_state = ("No Token", "No Exp")

    logger.info(msg='Self Token Expired or not in Window',
                ctx={'valid': token_state[0],
                     'exp': token_state[1],
                     'in_window': not_in_wind},
                tracer=tracer_from_ctx())

    result = http_adapter.post(endpoint=identity_token_endpoint(),
                               auth=(client_id(), client_secret()),
                               headers={},
                               body=TokenConfig().env.client_credentials_request(),
                               encoding='urlencoded',
                               name='token_service',
                               circuit_state_provider=TokenConfig().circuit_state_provider)

    return monad.Right(('from_grant', result.value[1]['access_token'])) if result.is_right() else monad.Left(
        build_token_error(result.error()))


def from_cache(bearer_token):
    result = cache_reader(TokenConfig().token_persistence_provider)
    if result is None or result.is_left():
        return monad.Right(bearer_token)
    return monad.Right(result.value.value)


def cache(bearer_token_tuple: Tuple[str, str]) -> monad.MEither:
    """
    Cache the token.  This is a dispatcher.  It takes the configured token persistence provider (Parameter Store or Dynamo)
    and writes to the provider.
    """
    get_location, bearer_token = bearer_token_tuple
    if get_location == 'from_env':
        return monad.Right(('ok', BEARER_TOKEN, bearer_token))

    if get_location == "from_cache":
        TokenConfig().env.set_env_var_with_value(BEARER_TOKEN, bearer_token)
        return monad.Right(('ok', BEARER_TOKEN, bearer_token))

    result = cache_writer(TokenConfig().token_persistence_provider, bearer_token)
    TokenConfig().env.set_env_var_with_value(BEARER_TOKEN, bearer_token)
    return result


def cache_reader(provider: Callable):
    if not hasattr(provider, 'read'):
        return None
    return provider.read(key=BEARER_TOKEN)


def cache_writer(provider: Callable, bearer_token: str) -> monad.MEither:
    result = provider.write(BEARER_TOKEN, bearer_token)
    if result.is_right():
        return monad.Right(('ok', BEARER_TOKEN, bearer_token))
    return result


def client_id() -> str:
    return TokenConfig().env.client_id()


def client_secret() -> str:
    return TokenConfig().env.client_secret()


def identity_token_endpoint() -> str:
    return TokenConfig().env.identity_token_endpoint()


def bearer_token_from_env():
    return monad.Right(TokenConfig().env.bearer_token())


def not_in_token_retry_window(bearer_token: str) -> bool:
    id_token = crypto.parse_generate_id_token(bearer_token)
    return random_retry_window.left_of_window(width=TokenConfig().window_width,
                                              end=id_token.value.exp() - TokenConfig().expiry_threshold,
                                              at=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])))


def in_token_retry_window(id_token):
    return random_retry_window.in_window(width=TokenConfig().window_width,
                                         end=id_token.exp() - TokenConfig().expiry_threshold,
                                         at=int(chronos.time_now(tz=chronos.tz_utc(), apply=[chronos.epoch()])))


def build_token_error(result):
    return TokenError(message=result.message,
                      name="self token",
                      ctx=result.ctx,
                      code=result.code, retryable=False)



def tracer_from_ctx():
    return _CTX['tracer']
