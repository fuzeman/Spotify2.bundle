from plugin import SpotifyPlugin, ViewMode
from settings import PLUGIN_ID, PREFIX, VERSION, ROUTEBASE


plugin = SpotifyPlugin()


def plugin_callback(method, **kwargs):
    """ Invokes callbacks on the plugin instance

    :param method:     The method on the SpotifyPlugin class to call.
    :param kwargs:     A dictionary of keyward args to pass to the method.
    """

    global plugin
    callback = lambda *a, **kw: method(plugin, *a, **kw)

    return callback(**kwargs)


@route(ROUTEBASE + 'play')
def play(**kwargs):
    return plugin_callback(SpotifyPlugin.play, **kwargs)


def artist(**kwargs):
    return plugin_callback(SpotifyPlugin.artist, **kwargs)


def album(**kwargs):
    return plugin_callback(SpotifyPlugin.album, **kwargs)


def playlist(**kwargs):
    return plugin_callback(SpotifyPlugin.playlist, **kwargs)


def playlists(**kwargs):
    return plugin_callback(SpotifyPlugin.playlists, **kwargs)


def starred(**kwargs):
    return plugin_callback(SpotifyPlugin.starred, **kwargs)


def search(**kwargs):
    return plugin_callback(SpotifyPlugin.search, **kwargs)


def main_menu(**kwargs):
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

