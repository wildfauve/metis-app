import pytest

from metis_app import span_tracer

def test_serialise_a_span():
    tracer = span_tracer.SpanTracer(env="prod", span_id='1', tags=['ATag'], kv={'k': 'v'})

    output = tracer.serialise()

    # {'env': 'prod', 'trace_id': '49ed2197-9569-4c82-a22e-6ffc73297f3e', 'span_id': '1', 'tags': ['ATag'], 'k': 'v'}
    assert output['span_id'] == '1'

def test_aws_request_id():
    tracer = span_tracer.SpanTracer(env="prod", kv={'handler_id': "aws_request_id"})

    assert tracer.aws_request_id() == "aws_request_id"


def test_new_tracer_inherits_span_id():
    tracer = span_tracer.SpanTracer(env="prod", span_id='1', tags=['ATag'], kv={'k': 'v'})

    new_tracer = tracer.span_child(tags=['BTag'], kv={'k2': 'v2'})

    assert tracer.span_id == new_tracer.span_id
    assert tracer.trace_id != new_tracer.trace_id
    assert new_tracer.kv == {'k2': 'v2'}
    assert new_tracer.tags == ['BTag']


