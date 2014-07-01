import cherrypy
import re


class Dispatcher(cherrypy.dispatch.Dispatcher):
    routes = {
        '/track': (re.compile(r"/track/(.*?)\.mp3", re.IGNORECASE), 'track')
    }

    def __init__(self, server):
        super(Dispatcher, self).__init__()
        self.server = server

    def __call__(self, path_info):
        matching_routes = [name for name in self.routes.keys() if path_info.startswith(name)]

        if not matching_routes:
            return super(Dispatcher, self).__call__(path_info)

        r_regex, r_func = self.routes[matching_routes[0]]

        match = r_regex.match(path_info)

        if not match:
            return super(Dispatcher, self).__call__(path_info)

        func = getattr(self.server, r_func)

        request = cherrypy.serving.request

        request.config = cherrypy.config.copy()
        request.config.update(getattr(func, '_cp_config', {}))

        request.handler = cherrypy.dispatch.LateParamPageHandler(func, *match.groups())
