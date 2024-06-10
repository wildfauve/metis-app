from typing import Dict, List, Union, Callable
from http import cookies
from pymonad.tools import curry

from metis_fn import fn

class SessionProperty:

    def __init__(self, name: str, value: Union[cookies.Morsel, str], attributes: Dict = None):
        self.name = name
        self.attributes = attributes
        self.morsel = self.coerse_value(name, value, attributes)
        self.transformer = fn.identity

    def coerse_value(self, name, val, attributes):
        if isinstance(val, cookies.Morsel):
            return val
        morsel = cookies.Morsel()
        morsel.set(name, val, val)
        self.add_attributes(morsel, attributes)
        return morsel

    def update(self, val, attributes):
        self.morsel.set(self.name, val, val)
        self.add_attributes(self.morsel, attributes)
        pass

    def add_attributes(self, morsel, attributes):
        if not attributes:
            return morsel
        for cookie_attr in attributes.items():
            morsel[cookie_attr[0]] = cookie_attr[1]
        return morsel


    def value_transformer(self, transform_fn: Callable = fn.identity):
        
        self.transformer = transform_fn
        return self

    def serialise(self) -> str:
        return self.morsel.OutputString()

    def value(self):
        return self.transformer(self.morsel.value)

    def is_name(self, search_name):
        return self.name == search_name


class WebSession():

    def __init__(self):
        self.properties = []

    def session_from_headers(self, headers: Dict):
        if not headers:
            return self

        hdrs = headers.get('cookie', None)

        if not hdrs:
            return self
        cookie = cookies.SimpleCookie()
        cookie.load(hdrs)
        self.properties = [SessionProperty(item[0], item[1]) for item in cookie.items()]
        return self

    def serialise_state_as_multi_header(self) -> Dict[str, List]:
        if not self.properties:
            return {}
        return {'Set-Cookie': [prop.serialise() for prop in self.properties]}

    def get(self, name: str, transform_fn: Callable = fn.identity) -> SessionProperty:
        if not self.properties:
            return None
        found = fn.find(self.prop_name_predicate(name), self.properties)
        return found.value_transformer(transform_fn)

    def set(self, name, value: str, attributes: Dict = None):
        prop = self.get(name)
        if prop:
            prop.update(value, attributes)
        else:
            self.properties.append(SessionProperty(name, value, attributes))
        return self

    def clear_all(self):
        self.properties = []
        return self

    @curry(3)
    def prop_name_predicate(self, name, prop):
        return prop.is_name(name)

