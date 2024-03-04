import pytest
from moto import mock_aws

@pytest.fixture
def dynamo_mock_empty():
    mock = mock_aws()
    mock.start()

    from . base_model import BaseModel

    if not BaseModel.exists():
        BaseModel.create_table()

    yield BaseModel

    mock.stop()
