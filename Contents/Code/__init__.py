from logging_handler import PlexHandler
from plugin import SpotifyPlugin
from search import SpotifySearch
from settings import PREFIX, VERSION, ROUTEBASE, LOGGERS
from utils import ViewMode

import locale
import logging

plugin = SpotifyPlugin()
sp_search = SpotifySearch(plugin)


def plugin_callback(method, kwargs=None):
    """ Invokes callbacks on the plugin instance

    :param method:     The method on the SpotifyPlugin class to call.
    :param kwargs:     A dictionary of keyward args to pass to the method.
    """

    global plugin
    callback = lambda kw: method(plugin, **kw)

    return callback(kwargs or {})


@route(ROUTEBASE + 'artist/{uri}')
def artist(**kwargs):
    return plugin_callback(SpotifyPlugin.artist, kwargs)


@route(ROUTEBASE + 'album/{uri}')
def album(**kwargs):
    return plugin_callback(SpotifyPlugin.album, kwargs)


@route(ROUTEBASE + 'playlist/{uri}')
def playlist(**kwargs):
    return plugin_callback(SpotifyPlugin.playlist, kwargs)


@route(ROUTEBASE + 'metadata/{track_uri}')
def metadata(**kwargs):
    return plugin_callback(SpotifyPlugin.metadata, kwargs)


@route(ROUTEBASE + 'playlists')
def playlists(**kwargs):
    return plugin_callback(SpotifyPlugin.playlists, kwargs)

@route(ROUTEBASE + 'starred')
def starred(**kwargs):
    return plugin_callback(SpotifyPlugin.starred, kwargs)

@route(ROUTEBASE + 'albums')
def albums(**kwargs):
    return plugin_callback(SpotifyPlugin.albums, kwargs)

@route(ROUTEBASE + 'artists')
def artists(**kwargs):
    return plugin_callback(SpotifyPlugin.artists, kwargs)

@route(ROUTEBASE + 'artists/{uri}/top_tracks')
def artist_top_tracks(**kwargs):
    return plugin_callback(SpotifyPlugin.artist_top_tracks, kwargs)

@route(ROUTEBASE + 'artists/{uri}/albums')
def artist_albums(**kwargs):
    return plugin_callback(SpotifyPlugin.artist_albums, kwargs)


@route(ROUTEBASE + 'search')
def search(**kwargs):
    return sp_search.run(**kwargs)


def main_menu(**kwargs):
    return plugin_callback(SpotifyPlugin.main_menu, kwargs)


@route(ROUTEBASE + 'play')
def play(**kwargs):
    return plugin_callback(SpotifyPlugin.play, kwargs)


@route(ROUTEBASE + 'image')
def image(**kwargs):
    return plugin_callback(SpotifyPlugin.image, kwargs)


def setup_logging():
    logging.basicConfig(level=logging.DEBUG)

    for name in LOGGERS:
        logger = logging.getLogger(name)

        logger.setLevel(logging.DEBUG)
        logger.handlers = [PlexHandler()]


def Start():
    """ Initialization function """
    Log("Starting Spotify (version %s)", VERSION)

    Plugin.AddPrefixHandler(PREFIX, main_menu, 'Spotify')
    ViewMode.AddModes(Plugin)

    ObjectContainer.title1 = 'Spotify'
    ObjectContainer.content = 'Items'
    ObjectContainer.art = R('art-default.png')
    DirectoryItem.thumb = R('icon-default.png')

    setup_logging()

    Log.Debug('Using locale: %s', locale.setlocale(locale.LC_ALL, ''))


def ValidatePrefs():
    """ Called when the user's prefs are changed """
    plugin_callback(SpotifyPlugin.preferences_updated)
