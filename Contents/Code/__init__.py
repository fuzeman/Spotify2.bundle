from revent import REvent
from host import SpotifyHost
from settings import PREFIX, VERSION, ROUTEBASE
from utils import ViewMode
import logging_handler

import locale

logging_handler.setup()

host = SpotifyHost()


def plugin_callback(method, kwargs=None, async=False):
    """ Invokes callbacks on the plugin instance

    :param method:     The method on the SpotifyPlugin class to call.
    :param kwargs:     A dictionary of keyward args to pass to the method.
    """

    Log.Debug('plugin_callback - method: %s, kwargs: %s, async: %s' % (method, kwargs, async))

    kwargs = kwargs or {}
    result = None

    if async:
        on_complete = REvent()

        kwargs['callback'] = lambda result: on_complete.set(result)

        method(host, **kwargs)

        result = on_complete.wait(10)
    else:
        result = method(host, **kwargs)

    if result is None:
        if async:
            return MessageContainer(
                header=L("MSG_CALLBACK_TIMEOUT_TITLE"),
                message=L("MSG_CALLBACK_TIMEOUT_BODY")
            )

        return MessageContainer(
            header=L("MSG_CALLBACK_FAILURE_TITLE"),
            message=L("MSG_CALLBACK_FAILURE_BODY")
        )

    return result


@route(ROUTEBASE + 'play')
def play(**kwargs):
    return plugin_callback(SpotifyHost.play, kwargs)


@route(ROUTEBASE + 'image')
def image(**kwargs):
    return plugin_callback(SpotifyHost.image, kwargs)


@route(ROUTEBASE + 'artist/{uri}')
def artist(**kwargs):
    return plugin_callback(SpotifyHost.artist, kwargs, async=True)


@route(ROUTEBASE + 'album/{uri}')
def album(**kwargs):
    return plugin_callback(SpotifyHost.album, kwargs, async=True)


@route(ROUTEBASE + 'playlists')
def playlists(**kwargs):
    return plugin_callback(SpotifyHost.playlists, kwargs, async=True)


@route(ROUTEBASE + 'playlist/{uri}')
def playlist(**kwargs):
    return plugin_callback(SpotifyHost.playlist, kwargs, async=True)


@route(ROUTEBASE + 'starred')
def starred(**kwargs):
    return plugin_callback(SpotifyHost.starred, kwargs, async=True)


@route(ROUTEBASE + 'metadata/{track_uri}')
def metadata(**kwargs):
    return plugin_callback(SpotifyHost.metadata, kwargs, async=True)


@route(ROUTEBASE + 'search')
def search(**kwargs):
    return plugin_callback(SpotifyHost.search, kwargs, async=True)


def main_menu(**kwargs):
    return plugin_callback(SpotifyHost.main_menu, kwargs)


def Start():
    """ Initialization function """
    Log("Starting Spotify (version %s)", VERSION)

    Plugin.AddPrefixHandler(PREFIX, main_menu, 'Spotify')
    ViewMode.AddModes(Plugin)

    ObjectContainer.title1 = 'Spotify'
    ObjectContainer.content = 'Items'
    ObjectContainer.art = R('art-default.png')
    DirectoryItem.thumb = R('icon-default.png')

    Log.Debug('Using locale: %s', locale.setlocale(locale.LC_ALL, ''))


def ValidatePrefs():
    """ Called when the user's prefs are changed """
    plugin_callback(SpotifyHost.preferences_updated)
