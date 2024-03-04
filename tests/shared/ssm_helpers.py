import datetime


def ssm_param_response():
    return {'Parameters':
        [
            {'Name': '/test/test_function/function_namespace/environment/CLIENT_ID', 'Type': 'SecureString',
             'Value': 'id', 'Version': 1, 'LastModifiedDate': datetime.datetime(2022, 2, 14, 13, 8, 43, 259000),
             'ARN': 'arn:aws:ssm:us-east-1:123456789012:parameter/test/test_function/function_namespace/environment/CLIENT_ID',
             'DataType': 'text'},
            {'Name': '/test/test_function/function_namespace/environment/CLIENT_SECRET', 'Type': 'SecureString',
             'Value': 'secret', 'Version': 1, 'LastModifiedDate': datetime.datetime(2022, 2, 14, 13, 8, 43, 259000),
             'ARN': 'arn:aws:ssm:us-east-1:123456789012:parameter/test/test_function/function_namespace/environment/CLIENT_SECRET',
             'DataType': 'text'},
            {'Name': '/test/test_function/function_namespace/environment/IDENTITY_TOKEN_ENDPOINT', 'Type': 'String',
             'Value': 'https://test.host/token', 'Version': 1,
             'LastModifiedDate': datetime.datetime(2022, 2, 14, 13, 8, 43, 260000),
             'ARN': 'arn:aws:ssm:us-east-1:123456789012:parameter/test/test_function/function_namespace/environment/IDENTITY_TOKEN_ENDPOINT',
             'DataType': 'text'}
        ], 'ResponseMetadata': {'HTTPStatusCode': 200, 'HTTPHeaders': {'server': 'amazon.com'}, 'RetryAttempts': 0}
    }
