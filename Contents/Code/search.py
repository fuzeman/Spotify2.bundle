from routing import route_path
from utils import localized_format
from view import ViewBase, COLUMNS

import locale
import urllib


class SpotifySearch(ViewBase):
    def run(self, query, callback, type='all', count=COLUMNS, plain=False):
        query = urllib.unquote_plus(query)
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
                oc, '%s (%s)' % (self.get_title(type, True), locale.format('%d', total, grouping=True)),
                route_path('search', query=query, type=type, count=50, plain=True)
            )

        self.append_items(oc, items, count, plain, placeholders)

    @staticmethod
    def get_title(type, plain=False):
        title = ""

        if type == 'artists':
            title = "Artists"
        elif type == 'albums':
            title = "Albums"
        elif type == 'tracks':
            title = "Tracks"
        elif type == 'playlists':
            title = "Playlists"

        if title and plain:
            return title
        elif title:
            return "Results - %s" % title

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
