import sys
from typing import Any, Callable, Dict, Optional
from simple_memory_cache import GLOBAL_CACHE
from dataclasses import dataclass, field
from functools import reduce

from metis_fn import singleton

"""
Configures an AWS Client context object which initialises various AWS Clients.  The context is cached so that it can be 
used anywhere in the app.

Creating aws client instances is typically performed outside the main lambda handler, allowing the state to be cached between
lambda invocations.

First initialise the aws client config with the services you want and the boto3 lib you're using;
> services = {'s3': {}, 'ssm': {},  'dynamodb': {'table': 'table1'}}
> AwsClientConfig().configure(region_name="ap_southeast_2", aws_client_lib=boto3, services=services)

Then get the context when required:
>aws_ctx().ssm
  
"""

aws_cache = GLOBAL_CACHE.MemoryCachedVar('aws_cache')


@dataclass
class AwsCtx():
    s3: Optional[Any] = None
    ssm: Optional[Any] = None
    event_bridge: Optional[Any] = None
    table: Optional[Any] = None
    cognito_idp: Optional[Any] = None


class AwsClientConfig(singleton.Singleton):

    def configure(self,
                  aws_client_lib: Callable,
                  region_name: str,
                  services: Dict):
        self.aws_client_lib = aws_client_lib
        self.region_name = region_name
        self.services = services
        pass


def aws_ctx():
    return aws_cache.get()


def invalidate_cache():
    aws_cache.invalidate()
    pass


@aws_cache.on_first_access
def initiate_ctx() -> AwsCtx:
    ctx = reduce(client_builder, AwsClientConfig().services.items(), {})
    return AwsCtx(**ctx)


def client_builder(injector, service):
    return {**injector, **getattr(sys.modules[__name__], service[0])(service[1])}


def s3(args):
    return {'s3': AwsClientConfig().aws_client_lib.client('s3', region_name=AwsClientConfig().region_name)}


def ssm(args):
    return {'ssm': AwsClientConfig().aws_client_lib.client('ssm', region_name=AwsClientConfig().region_name)}


def events(args):
    return {
        'event_bridge': AwsClientConfig().aws_client_lib.client('events', region_name=AwsClientConfig().region_name)}


def dynamodb(args):
    return {'table': AwsClientConfig().aws_client_lib.resource('dynamodb', region_name=AwsClientConfig().region_name)
    .Table(args['table'])}


def cognito_idp(args):
    return {'cognito_idp': AwsClientConfig().aws_client_lib.client('cognito-idp',
                                                                   region_name=AwsClientConfig().region_name)}


def result_status(try_result) -> str:
    statuses = {1: 'ok'}
    if try_result.is_right():
        return statuses.get(try_result.lift()['ConsumedCapacity']['CapacityUnits'], 'fail')
    else:
        return 'fail'
