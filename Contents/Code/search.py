from objects import Objects
from routing import route_path
from utils import localized_format

import locale


class SpotifySearch(object):
    def __init__(self, host):
        self.host = host

        self.objects = Objects(host)

    @property
    def sp(self):
        return self.host.sp

    def run(self, query, callback, type='all', count=7, plain=False):
        count = int(count)

        Log('Search query: "%s", type: %s, count: %s, plain: %s' % (query, type, count, plain))
        placeholders = self.use_placeholders()

        @self.sp.search(query, type, count=count)
        def on_search(result):
            callback(self.build(result, query, type, count, plain, placeholders))

    def build(self, result, query, type, count, plain, placeholders=False):
        oc = ObjectContainer(
            title2=self.get_title(type),
            content=self.get_content(type)
        )

        if result:
            # Fill with results for each media type
            for type in result.media_types:
                self.fill(result, oc, query, count, plain, placeholders, type)

            if len(oc):
                return oc

        return MessageContainer(
            header=L("MSG_TITLE_NO_RESULTS"),
            message=localized_format("MSG_FMT_NO_RESULTS", query)
        )

    def fill(self, result, oc, query, count, plain, placeholders, type):
        items = getattr(result, type)
        total = getattr(result, '%s_total' % type)

        if not items or not len(items):
            return

        if not plain:
            self.append_header(
                oc, '%s (%s)' % (self.get_title(type), locale.format('%d', total, grouping=True)),
                route_path('search', query=query, type=type, count=50, plain=True)
            )

        for x in range(count):
            if x < len(items):
                oc.add(self.objects.get(items[x]))
            elif not plain and placeholders:
                # Add a placeholder to fix alignment on PHT
                self.append_header(oc, '')

    @classmethod
    def append_header(cls, oc, title, key=''):
        oc.add(DirectoryObject(key=key, title=title))

    @staticmethod
    def use_placeholders():
        return Client.Product in [
            'Plex Home Theater'
        ]

    @staticmethod
    def get_title(type):
        if type == 'artists':
            return "Results - Artists"

        if type == 'albums':
            return "Results - Albums"

        if type == 'tracks':
            return "Results - Tracks"

        if type == 'playlists':
            return "Results - Playlists"

        return "Results"

    @staticmethod
    def get_content(type):
        if type == "artists":
            return ContainerContent.Artists

        if type == "albums":
            return ContainerContent.Albums

        if type == "tracks":
            return ContainerContent.Tracks

        if type == "playlists":
            return ContainerContent.Playlists

        return ContainerContent.Mixed
