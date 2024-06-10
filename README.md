# Metis-App

## Introduction

Metis-App contains useful functions for the use primarily in Python-based AWS Lambda serverless functions. The majority
of the functions are generic (rather than AWS-specifc), however, all these functions have been useful in building
distributed serverless functions, based on local patterns.

The objective is to collect together useful functions found during the development of Lambda services.

For example, we have used monads (PyMonad) extensively for building composable pipelines and avoiding raising
exceptions. In the monad lib there is also a try decorator than wraps exception-throwing functions. We have a simple
circuit-breaker mechanism, and a method of performing an oauth client credentials grant.

This lib is not an AWS Lambda paved road or framework. Consider it as a collection of helpers.

## The App Pipeline

The app pipeline is a common "middleware" manager for a Lambda event. The function initiates the pipeline right from the
handle function. The pipeline takes care of building the request event structures, applying routing based on the event
type (currently s3 nd http lambda events are supported), calls the function's handler, and generates the response. Other
middleware services are also provided, such as creating a policy decision point (PDP) by parsing any token and calling
an appropriate userinfo point.

The handler invokes the middleware as follows:

```python
return app.pipeline(event=event,
                    context=context,
                    env=env.Env().env,
                    params_parser=request_builder,
                    pip_initiator=pip,
                    handler_guard_fn=check_env_established)

```

+ `event`. Mandatory. Dict. The Lambda provided event.
+ `context`. Mandatory. Dict. The Lambda provided context.
+ `params_parser`: Mandatory. Callable. Takes the request object optionally transforms it, and returns it wrapper in an
  Either. If no transformation is required simply return the request wrapped in an Either,
  e.g. `return monad.Right(request)`
+ `pip_initiator`:  Mandatory. Callable. Policy Information Point
+ `factory_overrides`: Optional. Dict. Overrides the routing factory token constructor. Only supports S3 overrides. For
  an s3 override provide a Dict in the form of {'s3': callable_function}. With s3 the standard factory token constructor
  takes the bucket name, and splits on ".", returning the token prior to the first ".". As a convention it is expecting
  environment specific bucket names to be separated by ".", e.g. `bucket-name.uat.example.io`, with the resulting token
  being `bucket-name`. However, if this is not the format of the bucket name implement the override function. The
  function takes a List[S3Object] and must return a string to be looked up in the routing table. Note, should the event
  not be handled, return the const `app.NO_MATCHING_ROUTE`
+ `handler_guard_fn`: A pre-processing guard fn to determine whether the handler should be invoked. It returns an
  Either. When the handler shouldnt run the Either wraps an Exception. In this case, the request is passed directly to
  the responder

## Using PowerTools Observability

Metis-app supports the integration of the [AWS Powertools](https://docs.powertools.aws.dev/lambda/python/latest/)
Logger, Tracer, and Metrics modules and decorators. To use them, install the dependencies and then build a 
`Observer` configuration in the handler module.

```shell
poetry add aws-lambda-powertools[aws-sdk]

# if using metrics...
poetry add aws-xray-sdk
```

```python
from metis_app import observable

obs = observable.Observer().configure(service_name="test-service", metrics_namespace='module1')
```

Then use them as normal.  Note, however, the logger, tracer, and metrics objects are now available through the 
`observer` object.

```python
from aws_lambda_powertools.metrics import MetricUnit

@obs.metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, ctx=None):
  ...
    

@obs.tracer.capture_method
def a_command(request):
    obs.tracer.put_annotation(key="Resource", value=request.event.path_params.get('id1'))
    obs.logger.info("Search for resource", uuid=request.event.path_params.get('id1'))
    obs.metrics.add_metric(name="Resource:Search", unit=MetricUnit.Count, value=1)
    ...
```

When the `Observer` is configured, it is also added to the `Request` object and passed to the command handler.

```python
def a_command(request):
    request.observer.logger.info("Search for resource", uuid=request.event.path_params.get('id1'))
    ...
```



## Getting a Self Token

### Configuration

Provide the token service with a configuration as follows:

```python
from metis_app import self_token

self_token.TokenConfig().configure(token_persistence_provider=TokenPersistenceProvider(),
                                   env=Env(),
                                   circuit_state_provider=circuit_store.CircuitStore(circuit_name="auth0"))
```

+ `token_persistence_provider`. A class that conforms to `TokenPersistenceProviderProtocol`. It has a write and read
  method.
    + The writer takes a key and value. The key defaults to `BEARER_TOKEN`, and the value is the JWT. It is the
      responsibility of the writer to persist where required. The writer must return the token wrapped in a Monad ;
      e.g. `monad.Right('eyJ0eXAiOiJK....')`
    + The reader takes a key and returns the value wrapped in a Monad; e.g. `monad.Right('eyJ0eXAiOiJK....')`

+ `env`. This should be a class that has the following methods:
    + `client_id`. Returns a client id as a string.
    + `client_secret`. Returns a client secret as a string.
    + `identity_token_endpoint`. Returns the url of the Oauth2 token endpoint as a str.

+ `circuit_state_provider`. Optional. A circuit state manager can optionally be provided. Doing so adds circuit breaker
  functionality to the call to the token endpoint. If not provided, failures do not enact the circuit breaker behaviour.
  The provider must conform to the `circuit.CircuitStateProviderProtocol`. This is a special case of a circuit; one that
  is used by the token getter. It will configure the circuit based on this arg. There is a more general way to use
  circuits for non-token interfaces. See [the circuit breaker section](#circuit-breaker).

## Circuit Breaker