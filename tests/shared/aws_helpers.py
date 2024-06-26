import pytest
import boto3
from metis_app import aws_client_helpers

class MockAwsClient():
    def client(self, service, region_name):
        self.service = service
        self.region_name = region_name
        return self

    def resource(self, service, region_name):
        self.service = service
        self.region_name = region_name
        return self

    def Table(self, table_name):
        self.table_name = table_name
        return self


class MockSsm(MockAwsClient):
    parameters = {}

    response = None

    @classmethod
    def response(cls, response):
        cls.response = response

    def get_parameters_by_path(self, Path, WithDecryption, Recursive):
        return type(self).response

    def put_parameter(self, Name, Value, Type, Overwrite=False, Tier=None):
        self.__class__.parameters[Name] = Value
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200}
        }


class MockBoto3():
    def __init__(self, mock_client=MockAwsClient):
        self.mock_client = mock_client

    def client(self, service, region_name):
        return self.mock_client().client(service, region_name)

    def resource(self, service, region_name):
        return self.mock_client().resource(service, region_name)


@pytest.fixture
def aws_ctx_with_boto():
    services = {'ssm': {}}

    aws_client_helpers.invalidate_cache()

    aws_client_helpers.AwsClientConfig().configure(region_name="us-west-2",
                                                   aws_client_lib=boto3,
                                                   services=services)
