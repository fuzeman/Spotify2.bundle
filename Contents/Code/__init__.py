from plugin import SpotifyPlugin, ViewMode
from settings import PLUGIN_ID, PREFIX, VERSION


plugin = SpotifyPlugin()


def plugin_callback(method, **kwargs):
    """ Invokes callbacks on the plugin instance

    :param method:     The method on the SpotifyPlugin class to call.
    :param kwargs:     A dictionary of keyward args to pass to the method.
    """

    global plugin
    callback = lambda *a, **kw: method(plugin, *a, **kw)

    return callback(**kwargs)


def play_track(**kwargs):
    """ Top-level function to retrieve a specific playlist """
    return plugin_callback(SpotifyPlugin.play_track, **kwargs)


def get_artist_albums(**kwargs):
    """ Top-level function to retrieve an artists albums """
    return plugin_callback(
        SpotifyPlugin.get_artist_albums, **kwargs)


def get_album_tracks(**kwargs):
    """ Top-level function to retrieve the tracks in an album """
    return plugin_callback(
        SpotifyPlugin.get_album_tracks, **kwargs)


def get_playlist(**kwargs):
    """ Top-level function to retrieve a specific playlist """
    return plugin_callback(SpotifyPlugin.get_playlist, **kwargs)


def get_playlists(**kwargs):
    """ Top-level function to retrieve user playlists """
    return plugin_callback(SpotifyPlugin.get_playlists, **kwargs)


def get_starred_tracks(**kwargs):
    """ Top-level function to retrieve starred user tracks """
    return plugin_callback(SpotifyPlugin.get_starred_tracks, **kwargs)


def search(**kwargs):
    """ Top-level function to execute a search """
    return plugin_callback(SpotifyPlugin.search, **kwargs)


def main_menu(**kwargs):
    """ Top-level function to retrieve the main menu """
    return plugin_callback(SpotifyPlugin.main_menu, **kwargs)


def Start():
    """ Initialization function """
    Log("Starting Spotify (version %s)", VERSION)
    Plugin.AddPrefixHandler(PREFIX, main_menu, 'Spotify')
    ViewMode.AddModes(Plugin)

    ObjectContainer.title1 = 'Spotify'
    ObjectContainer.content = 'Items'
    ObjectContainer.art = R('art-default.png')
    DirectoryItem.thumb = R('icon-default.png')


def ValidatePrefs():
    """ Called when the user's prefs are changed """
    plugin_callback(SpotifyPlugin.preferences_updated)

