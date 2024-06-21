import base64

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


def api_gateway_event_with_base64_encoded_body():
    return {
        "body": "Z3JhbnRfdHlwZT1jbGllbnRfY3JlZGVudGlhbHM=",
        "resource": "/{proxy+}",
        "path": "/oauth/token",
        "httpMethod": "POST",
        "isBase64Encoded": "True",
        "queryStringParameters": {},
        "multiValueQueryStringParameters": {},
        "pathParameters": {"proxy": "/oauth/token"},
        "stageVariables": {},
        "headers": {"Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": "Basic SOME-AUTH-HEADER"},
        "requestContext": {
            "path": "/oauth/token",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "apiId": "1234567890",
            "protocol": "HTTP/1.1"
        }
    }


@pytest.fixture
def kafka_event():
    return _kafka_event()


@pytest.fixture
def kafka_event_without_key():
    return _kafka_event(no_key=True)


def _kafka_event(no_key=False):
    key = [
        104,
        101,
        97,
        100,
        101,
        114,
        86,
        97,
        108,
        117,
        101
    ]
    encoded_key = "abcDEFghiJKLmnoPQRstuVWXyz1234=="
    event = base64.b64encode(json.dumps({"event": "someevent"}).encode('utf-8')).decode('utf-8')
    base_ev = {
        "topic": "hello-kafka",
        "partition": 0,
        "offset": 15,
        "timestamp": 1545084650987,
        "timestampType": "CREATE_TIME",
        "value": event,
        "headers": [
            {
                "headerKey": [] if no_key else key
            }
        ]

    }
    ev = base_ev if no_key else {**base_ev, **{'key': encoded_key}}

    return {
        "eventSourceArn": "arn:aws:kafka:sa-east-1:123456789012:cluster/vpc-2priv-2pub/751d2973-a626-431c-9d4e-d7975eb44dd7-2",
        "eventSource": "aws:kafka",
        "bootstrapServers": "b-2.demo-cluster-1.a1bcde.c1.kafka.us-east-1.amazonaws.com:9092,b-1.demo-cluster-1.a1bcde.c1.kafka.us-east-1.amazonaws.com:9092",
        "records": {
            "hello-kafka-0": [ev]
        }
    }
