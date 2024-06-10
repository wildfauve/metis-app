from base64 import urlsafe_b64decode, urlsafe_b64encode

from metis_app import app_web_session

def it_created_a_session_from_a_multi_property_cookie():
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1; session2=2"})

    assert len(session.properties) == 2

    props = [(prop.name, prop.serialise()) for prop in session.properties]

    assert props == [('session1', 'session1=1'), ('session2', 'session2=2')]

def it_created_a_session_from_a_multi_property_cookie_aith_attributes():
    cookie = {'cookie': "session1=1; Max-Age=600; Path=/; session2=2; Max-Age=100"}
    session = app_web_session.WebSession().session_from_headers(cookie)

    assert len(session.properties) == 2

    props = [(prop.name, prop.serialise()) for prop in session.properties]


    assert props == [('session1', 'session1=1; Max-Age=600; Path=/'), ('session2', 'session2=2; Max-Age=100')]


def it_serialises_session_as_multi_hdr_set_cookie():
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1; session2=2"})

    assert session.serialise_state_as_multi_header() == {'Set-Cookie': ['session1=1', 'session2=2']}


def it_gets_a_property():
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1; session2=2"})

    assert session.get('session1').value() == '1'


def it_gets_a_property_with_a_transform_fn():
    prop = b'12345'
    encoded_prop = bytes_to_base64url(prop)
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1; session2={}".format(encoded_prop)})

    assert session.get('session2').value() == encoded_prop
    assert session.get('session2', base64url_to_bytes).value() == prop


def it_doesnt_serialise_when_no_props():
    session = app_web_session.WebSession().session_from_headers(None)

    assert session.serialise_state_as_multi_header() == {}

def it_sets_new_property():
    session = app_web_session.WebSession().session_from_headers(None)

    session.set('session1', '1')

    assert session.get('session1').value() == '1'

def it_sets_a_property_with_path_and_max_age():
    session = app_web_session.WebSession().session_from_headers(None)

    session.set('session1', "1", {'max-age': 600, 'path': "/"})

    assert session.get('session1').serialise() == 'session1=1; Max-Age=600; Path=/'
    

def it_updates_a_property():
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1"})

    session.set('session1', '2')

    assert session.get('session1').value() == '2'


def it_clears_all_properties():
    session = app_web_session.WebSession().session_from_headers({'cookie': "session1=1"})

    session.clear_all()

    assert session.serialise_state_as_multi_header() == {}



#
# Helpers
#

def base64url_to_bytes(val: str) -> bytes:
    return urlsafe_b64decode(f"{val}===")

def bytes_to_base64url(val: bytes) -> str:
    return urlsafe_b64encode(val).decode("utf-8").replace("=", "")
