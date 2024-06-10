def aws_context_obj():
    class AwsContextMock:
        aws_request_id = 'handler-id-1'
        function_name = 'test-function'
    return AwsContextMock()

