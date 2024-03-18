import pytest
from moto import mock_aws


@pytest.fixture
def aws_mock():
    mock = mock_aws()
    mock.start()
    yield
    mock.stop()
