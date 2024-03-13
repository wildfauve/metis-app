from metis_app import aws_client_helpers

from .shared import aws_helpers


def test_configure_client_setup():
    services = {'s3': {}, 'ssm': {},  'dynamodb': {'table': 'table1'}}
    aws_client_helpers.AwsClientConfig().configure(region_name="ap_southeast_2",
                                                   aws_client_lib=aws_helpers.MockBoto3(),
                                                   services=services)

    ctx = aws_client_helpers.aws_ctx()

    assert ctx.s3.service == 's3'
    assert ctx.s3.region_name == 'ap_southeast_2'

    assert ctx.ssm.service == 'ssm'
    assert ctx.ssm.region_name == 'ap_southeast_2'

    assert ctx.table.service == 'dynamodb'
    assert ctx.table.region_name == 'ap_southeast_2'
    assert ctx.table.table_name == 'table1'


def test_configure_cognito_idp():
    services = {'cognito_idp': {}}

    aws_client_helpers.invalidate_cache()

    aws_client_helpers.AwsClientConfig().configure(region_name="ap_southeast_2",
                                                   aws_client_lib=aws_helpers.MockBoto3(),
                                                   services=services)
    ctx = aws_client_helpers.aws_ctx()

    assert ctx.cognito_idp.service == "cognito-idp"
