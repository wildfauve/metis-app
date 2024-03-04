from metis_app import coerser, chronos
#
# nested_coerse
#
def it_replaces_things():

    d = {"a": {"b": {'c': chronos.time_now()}, 'd': 2}, 'x': [1,2,3]}

    result = coerser.nested_coerse({}, d)

    assert isinstance(result['a']['b']['c'], str)

def it_tests_something_more_complex():
    d = {'body': {'c': [{'@context': 'a', 'serviceOffering': 'x'},{'@context': 'a', 'serviceOffering': 'x'}]}}

    result = coerser.nested_coerse({}, d)

    assert result == d