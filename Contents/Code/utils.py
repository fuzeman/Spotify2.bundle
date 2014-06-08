from urlparse import urlparse, parse_qs
import time
import unicodedata


def LF(key, args):
    """ Return the a localized string formatted with the given args """
    return str(L(key)) % args


class ViewMode(object):
    Tracks              = "Tracks"
    FeaturedPlaylists   = "FeaturedPlaylists"
    Playlists           = "Playlists"
    Albums              = "Albums"
    Artists             = "Artists"

    @classmethod
    def AddModes(cls, plugin):
        plugin.AddViewGroup(cls.Tracks,             "List",     "songs")
        plugin.AddViewGroup(cls.Playlists,          "List",     "items")
        plugin.AddViewGroup(cls.FeaturedPlaylists,  "List",     "items")
        plugin.AddViewGroup(cls.Albums,             "Albums",   "items")
        plugin.AddViewGroup(cls.Artists,            "List",     "items")
        #ViewModes 
        # "List"
        # "InfoList", "MediaPreview", "Showcase", 
        # "Coverflow", "PanelStream", "WallStream", 
        # "Songs", "Albums", "ImageStream"
        # "Seasons", "Pictures", "Episodes"


class Track(object):
    def __init__(self, track, url):
        self.track = track
        self.url = url

        self.expires = None

    def valid(self):
        if not self.expires:
            return True

        current = time.time()

        Log.Debug('Track.valid: %s > %s', self.expires, current)
        return self.expires > current

    def matches(self, other_track):
        return False #self.track.getURI() == other_track.getURI() and self.valid()

    @classmethod
    def create(cls, track, url):
        result = cls(track, url)

        # Parse URL
        parsed_url = urlparse(url)

        query = parse_qs(parsed_url.query)

        # Parse 'Expires' value
        expires = query.get('Expires')

        if expires and type(expires) is list:
            result.expires = int(expires[0])

        return result

    def __repr__(self):
        return '<Track track: %s, expires: %s, url: %s>' % (
            repr(self.track),
            repr(self.expires),
            repr(self.url)
        )

    def __str__(self):
        return self.__repr__()


def authenticated(func):
    """ Decorator used to force a valid session for a given call

    We must return a class with a __name__ property here since the Plex
    framework uses it to generate a route and it stops us assigning
    properties to function objects.
    """

    class decorator(object):
        @property
        def __name__(self):
            return func.func_name

        def __call__(self, *args, **kwargs):
            host = args[0]
            client = host.client

            Log.Debug('authenticated')

            if not client or not client.constructed:
                Log.Debug('authenticated - initializing')
                return self.message('INITIALIZING')

            if not client.ready:
                Log.Debug('authenticated - login error')
                return self.message('LOGIN_ERROR')

            return func(*args, **kwargs)

        def message(self, key):
            return MessageContainer(
                header=L("MSG_%s_TITLE" % key),
                message=L("MSG_%s_BODY" % key)
            )

    return decorator()


def normalize(text):
    if text is None:
        return None

    if type(text) is Framework.components.localization.LocalString:
        text = str(text)

    if type(text) is unicode:
        text = unicodedata.normalize('NFKD', text)

    return text.encode('ascii', 'ignore')


def parse_xml(string):
    try:
        return XML.ElementFromString(string)
    except:
        return None
