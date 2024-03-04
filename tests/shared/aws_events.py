import pytest
import json

@pytest.fixture
def s3_event_hello():
    return {
        'Records': [
            {'s3': {'bucket': {'name': 'hello'}, 'object': {'key': 'hello_file.json'}}}
        ]
    }

@pytest.fixture
def api_gateway_event_get():
    return {
        "body": "eyJ0ZXN0IjoiYm9keSJ9",
        "resource": "/{proxy+}",
        "path": "/resourceBase/resource/uuid1",
        "httpMethod": "GET",
        "isBase64Encoded": True,
        "queryStringParameters": {
            "param1": "a",
            "param2": "b"
        },
        "multiValueQueryStringParameters": {
        },
        "pathParameters": {
            "proxy": "/path/to/resource"
        },
        "stageVariables": {
        },
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Accept-Language": "en-US,en;q=0.8",
            "Authorization": "Bearer {}",
            "Cache-Control": "max-age=0",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Cookie": "session=session_uuid; session1=session1_uuid",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Custom User Agent String",
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "multiValueHeaders": {
            "Accept": [
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ],
            "Accept-Encoding": [
                "gzip, deflate, sdch"
            ],
            "Accept-Language": [
                "en-US,en;q=0.8"
            ],
            "Cache-Control": [
                "max-age=0"
            ],
            "CloudFront-Forwarded-Proto": [
                "https"
            ],
            "CloudFront-Is-Desktop-Viewer": [
                "true"
            ],
            "CloudFront-Is-Mobile-Viewer": [
                "false"
            ],
            "CloudFront-Is-SmartTV-Viewer": [
                "false"
            ],
            "CloudFront-Is-Tablet-Viewer": [
                "false"
            ],
            "CloudFront-Viewer-Country": [
                "US"
            ],
            "Host": [
                "0123456789.execute-api.us-east-1.amazonaws.com"
            ],
            "Upgrade-Insecure-Requests": [
                "1"
            ],
            "User-Agent": [
                "Custom User Agent String"
            ],
            "Via": [
                "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)"
            ],
            "X-Amz-Cf-Id": [
                "cDehVQoZnx43VYQb9j2-nvCh-9z396Uhbp027Y2JvkCPNLmGJHqlaA=="
            ],
            "X-Forwarded-For": [
                "127.0.0.1, 127.0.0.2"
            ],
            "X-Forwarded-Port": [
                "443"
            ],
            "X-Forwarded-Proto": [
                "https"
            ]
        },
        "requestContext": {
            "accountId": "123456789012",
            "resourceId": "123456",
            "stage": "prod",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "accessKey": None,
                "sourceIp": "127.0.0.1",
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": "Custom User Agent String",
                "user": None
            },
            "path": "/resourceBase/resource/uuid1",
            "resourcePath": "/{proxy+}",
            "httpMethod": "GET",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }

@pytest.fixture
def api_gateway_event_get_nested_resource():
    return {
        "body": "eyJ0ZXN0IjoiYm9keSJ9",
        "resource": "/{proxy+}",
        "path": "/resourceBase/resource/uuid1/resource/resource-uuid2",
        "httpMethod": "GET",
        "isBase64Encoded": True,
        "queryStringParameters": {
        },
        "multiValueQueryStringParameters": {
        },
        "pathParameters": {
            "proxy": "/path/to/resource"
        },
        "stageVariables": {
        },
        "headers": {},
        "requestContext": {
            "path": "/resourceBase/resource/uuid1/resource/resource-uuid2",
            "resourcePath": "/{proxy+}",
            "httpMethod": "GET",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }

@pytest.fixture
def api_gateway_event_post_with_json_body():
    return {
        "body": json.dumps({'test': 1}),
        "resource": "/{proxy+}",
        "path": "/resourceBase/resource/uuid1",
        "httpMethod": "POST",
        "isBase64Encoded": True,
        "queryStringParameters": {
        },
        "multiValueQueryStringParameters": {
        },
        "pathParameters": {
            "proxy": "/path/to/resource"
        },
        "stageVariables": {
        },
        "headers": {},
        "requestContext": {
            "path": "/resourceBase/resource/uuid1/resource/resource-uuid2",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }