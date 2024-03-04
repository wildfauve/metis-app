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

    response = None

    @classmethod
    def response(cls, response):
        cls.response = response

    def get_parameters_by_path(self, Path, WithDecryption):
        return type(self).response


class MockBoto3():
    def __init__(self, mock_client=MockAwsClient):
        self.mock_client= mock_client

    def client(self, service, region_name):
        return self.mock_client().client(service, region_name)

    def resource(self, service, region_name):
        return self.mock_client().resource(service, region_name)
