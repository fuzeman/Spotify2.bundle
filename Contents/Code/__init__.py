'''
Plugin entry-point
'''
from plugin import SpotifyPlugin, ViewMode
from settings import PLUGIN_ID, PREFIX, VERSION
from tornado.ioloop import IOLoop
from utils import IOLoopProxy


''' Globals '''
runloop = IOLoopProxy(IOLoop.instance())
plugin = SpotifyPlugin(runloop.ioloop)


def plugin_callback(method, async = False, **kwargs):
    ''' Invokes callbacks on the plugin instance

    To simplify things we bounce these calls to the reactor thread
    and wait on a signal for them to return.  This way we don't have to
    lock things all over the place which would be needed because libspotify
    is not thread-safe.  By passing everything through this function
    our entire plugin can be single-threaded.

    :param method:     The method on the SpotifyPlugin class to call.
    :param async:      Indicates if the method is asynchronous
                       (see the documentation for IOLoopProxy)
    :param kwargs:     A dictionary of keyward args to pass to the method.
    '''
    global plugin, runloop
    callback = lambda *a, **kw: method(plugin, *a, **kw)
    return runloop.invoke(callback, async = async, kwargs = kwargs)


def play_track(**kwargs):
    ''' Top-level function to retrieve a specific playlist '''
    return plugin_callback(SpotifyPlugin.play_track, **kwargs)


def get_artist_albums(**kwargs):
    ''' Top-level function to retrieve an artists albums '''
    return plugin_callback(
        SpotifyPlugin.get_artist_albums, async = True, **kwargs)


def get_album_tracks(**kwargs):
    ''' Top-level function to retrieve the tracks in an album '''
    return plugin_callback(
        SpotifyPlugin.get_album_tracks, async = True, **kwargs)


def get_playlist(**kwargs):
    ''' Top-level function to retrieve a specific playlist '''
    return plugin_callback(SpotifyPlugin.get_playlist, **kwargs)


def get_playlists(**kwargs):
    ''' Top-level function to retrieve user playlists '''
    return plugin_callback(SpotifyPlugin.get_playlists, **kwargs)


def search(**kwargs):
    ''' Top-level function to execute a search '''
    return plugin_callback(SpotifyPlugin.search, async = True, **kwargs)


def search_menu(**kwargs):
    ''' Top-level function to retrieve the search menu '''
    return plugin_callback(SpotifyPlugin.search_menu, **kwargs)


def main_menu(**kwargs):
    ''' Top-level function to retrieve the main menu '''
    return plugin_callback(SpotifyPlugin.main_menu, **kwargs)


def Start():
    ''' Initialization function '''
    Log("Starting Spotify (version %s)", VERSION)
    Plugin.AddPrefixHandler(PREFIX, main_menu, 'Spotify')
    ViewMode.AddModes(Plugin)
    ObjectContainer.title1 = 'Spotify'
    ObjectContainer.content = 'Items'
    ObjectContainer.art = R('art-default.png')
    DirectoryItem.thumb = R('icon-default.png')


def ValidatePrefs():
    ''' Called when the user's prefs are changed '''
    plugin_callback(SpotifyPlugin.preferences_updated)

