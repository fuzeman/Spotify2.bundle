from urlparse import urlparse, parse_qs
import time


def localized_format(key, args):
    """ Return the a localized string formatted with the given args """
    return str(L(key)) % args


class ViewMode(object):
    Tracks = "Tracks"
    Playlists = "Playlists"
    Albums = "Albums"
    Artists = "Artists"

    @classmethod
    def AddModes(cls, plugin):
        plugin.AddViewGroup(cls.Tracks, "List", "songs")
        plugin.AddViewGroup(cls.Playlists, "List", "items")
        plugin.AddViewGroup(cls.Albums, "List", "items")
        plugin.AddViewGroup(cls.Artists, "List", "items")


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
        if not self.valid():
            return False

        return self.track.getURI() == other_track.getURI()

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
            plugin = args[0]
            client = plugin.client
            if not client or not client.is_logged_in():
                return self.access_denied_message(plugin, client)
            return func(*args, **kwargs)

        def access_denied_message(self, plugin, client):
            if not client:
                return MessageContainer(
                    header=L("MSG_TITLE_MISSING_LOGIN"),
                    message=L("MSG_BODY_MISSING_LOGIN")
                )
            elif not client.spotify.api.ws:
                return MessageContainer(
                    header=L("MSG_TITLE_LOGIN_IN_PROGRESS"),
                    message=L("MSG_BODY_LOGIN_IN_PROGRESS")
                )
            else:
                # Trigger a re-connect
                Log.Warn('Connection failed, reconnecting...')
                plugin.start()

                return MessageContainer(
                    header=L("MSG_TITLE_LOGIN_FAILED"),
                    message=L("MSG_TITLE_LOGIN_FAILED")
                )

    return decorator()
