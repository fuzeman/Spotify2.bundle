from plugin import SpotifyPlugin, ViewMode

VERSION     = 0.1
PREFIX      = "/music/spotify"
ROUTEBASE   = PREFIX + '/'

''' Globals '''
shared_plugin = SpotifyPlugin()

def plugin_callback(method, plugin = None, *args, **kwargs):
    ''' Invokes callbacks on a plugin instance '''
    global shared_plugin
    if not plugin:
        plugin = shared_plugin
    return method(plugin, *args, **kwargs)


def play_track(plugin = None, **kwargs):
    ''' Top-level function to retrieve a specific playlist '''
    return plugin_callback(SpotifyPlugin.play_track, plugin, **kwargs)


def get_artist_albums(plugin = None, **kwargs):
    ''' Top-level function to retrieve an artists albums '''
    return plugin_callback(SpotifyPlugin.get_artist_albums, plugin, **kwargs)


def get_album_tracks(plugin = None, **kwargs):
    ''' Top-level function to retrieve the tracks in an album '''
    return plugin_callback(SpotifyPlugin.get_album_tracks, plugin, **kwargs)


def get_playlist(plugin = None, **kwargs):
    ''' Top-level function to retrieve a specific playlist '''
    return plugin_callback(SpotifyPlugin.get_playlist, plugin, **kwargs)


def get_playlists(plugin = None):
    ''' Top-level function to retrieve user playlists '''
    return plugin_callback(SpotifyPlugin.get_playlists, plugin)


def search(plugin = None, **kwargs):
    ''' Top-level function to execute a search '''
    return plugin_callback(SpotifyPlugin.search, plugin, **kwargs)


def search_menu(plugin = None):
    ''' Top-level function to retrieve the search menu '''
    return plugin_callback(SpotifyPlugin.search_menu, plugin)


def main_menu(plugin = None):
    ''' Top-level function to retrieve the main menu '''
    return plugin_callback(SpotifyPlugin.main_menu, plugin)


def Start():
    ''' Entrypoint '''
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

