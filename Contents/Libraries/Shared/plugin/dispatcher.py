import cherrypy
import re


class Dispatcher(cherrypy.dispatch.Dispatcher):
    re_track = re.compile(r"/track/(.*?)\.mp3", re.IGNORECASE)

    def __init__(self, server):
        super(Dispatcher, self).__init__()
        self.server = server

    def __call__(self, path_info):
        if not path_info.startswith('/track'):
            return super(Dispatcher, self).__call__(path_info)

        ma_track = self.re_track.match(path_info)

        if not ma_track:
            return super(Dispatcher, self).__call__(path_info)

        func = self.server.track

        request = cherrypy.serving.request
        uri = ma_track.group(1)

        request.config = cherrypy.config.copy()
        request.config.update(getattr(func, '_cp_config', {}))

        request.handler = cherrypy.dispatch.LateParamPageHandler(func, uri)
