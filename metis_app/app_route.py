from typing import Optional, Dict, Any, List, Callable, Union, Tuple
from pymonad.tools import curry

from metis_fn import singleton, fn, monad

from . import app


class RouteMap(singleton.Singleton):
    routes = {}

    def add_route(self, pattern: Union[str, Tuple[str,str,str]], f: Callable, opts: Dict):
        self.routes[pattern] = (f, opts)
        pass

    def no_route(self, return_template=False) -> Union[Callable, Tuple[str, Callable]]:
        no_route_route = self.routes.get('no_matching_route', None)
        if not no_route_route:
            no_route_route = (self.default_no_route, None)
        if return_template:
            return 'no_matching_routes', no_route_route[0], no_route_route[1]
        return no_route_route

    def default_no_route(self, request):
        return monad.Left(request.replace('error', app.AppError(message='no matching route', code=404)))

    def get_route(self, route: Union[str, Tuple]) -> Tuple[Union[str, Tuple], Callable]:
        if isinstance(route, str):
            match = self.routes.get(route, self.no_route())
            return route, match[0], match[1]
        possible_matching_routes = self._multi_match_determination(route,
                                                                   self.event_matches(route[0], route[1], route[2]))
        if not possible_matching_routes:
            return self.no_route(True)

        # return the route_pattern, route_fn, and route_opts
        return possible_matching_routes[0][0], possible_matching_routes[0][1][0], possible_matching_routes[0][1][1],

    def _multi_match_determination(self, route, matches):
        """
        Only for APIs with the route defined as ('API', 'GET', '/resourceBase/resource/ACollection')".

        When a path has both an instance (id-based) and collection based route defined.
        E.g. @app.route(pattern=('API', 'GET', '/resourceBase/resource/ACollection')) is the same as
             @app.route(pattern=('API', 'GET', '/resourceBase/resource/{id1}'))
        when the event path is /resourceBase/resource/ACollection (ACollection also matches {id1}
        """
        if not matches or len(matches) == 1:
            return matches  # no matching routes or only 1 route
        if all(["{" in m[0][2] for m in matches]):  # Each match is a templated path, so ambiguous
            return None
        # Otherwise the first one defined is used for the path.
        return [matches[0]]



    def route_pattern_from_function(self, route_fn: Callable):
        route_item = fn.find(self.route_function_predicate(route_fn), self.routes.items())
        if route_item:
            return route_item[0]
        return None

    @curry(3)
    def route_function_predicate(self, route_fn, route):
        return route[1][0] == route_fn

    def event_matches(self, pos1, pos2, pos3) -> Dict[Tuple, str]:
        return list(fn.select(self.match_predicate(pos1, pos2, pos3), self.routes.items()))

    @curry(5)
    def match_predicate(self, pos1, pos2, pos3, route_item: Tuple[Union[str, Tuple], Callable]):
        if isinstance(route_item[0], str):
            return None
        event_type, event_qual, event_template = route_item[0]
        if event_type == pos1 and event_qual == pos2 and self.template_matches(event_template, pos3):
            return True
        return None

    def template_matches(self, template, event):
        return self.matcher(fn.rest(template.split("/")), fn.rest(event.split("/")))

    def matcher(self, template_xs: List, event_xs: List):
        template_fst, template_rst = fn.first(template_xs), fn.rest(template_xs)
        ev_fst, ev_rst = fn.first(event_xs), fn.rest(event_xs)
        if not template_fst and not ev_fst:
            return True
        if not template_fst and ev_fst:
            return False
        if template_fst and not ev_fst:
            return False
        if not self.ismatch(template_fst, ev_fst):
            return False
        return self.matcher(template_rst, ev_rst)

    def ismatch(self, template_token, ev_token):
        return ("{" in template_token and "}" in template_token) or template_token == ev_token


def route(pattern: Union[str, Tuple[str, str, str]], opts: Dict = None):
    """
    Route Mapper
    """
    def inner(fn):
        RouteMap().add_route(pattern=pattern, f=fn, opts=opts)
    return inner


def std_noop_response(request):
    return monad.Right(request.replace('response', monad.Right({})))

