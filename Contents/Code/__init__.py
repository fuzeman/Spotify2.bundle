from plugin import SpotifyPlugin

VERSION     = 0.1
PREFIX      = "/music/spotify"
ROUTEBASE   = PREFIX + '/'

''' Globals '''
shared_plugin = SpotifyPlugin()


def plugin_callback(method, plugin = None):
    ''' Invokes callbacks on a plugin instance '''
    global shared_plugin
    if not plugin:
        plugin = shared_plugin
    return method(plugin)


def get_playlists(plugin = None):
    ''' Top-level function to retrieve user playlists '''
    return plugin_callback(SpotifyPlugin.get_playlists, plugin)


def main_menu(plugin = None):
    ''' Top-level function to retrieve the main menu '''
    return plugin_callback(SpotifyPlugin.main_menu, plugin)


def Start():
    ''' Entrypoint '''
    Log("Starting Spotify (version %s)", VERSION)
    Plugin.AddPrefixHandler(PREFIX, main_menu, 'Spotify (New)')


def ValidatePrefs():
    ''' Called when the user's prefs are changed '''
    plugin_callback(SpotifyPlugin.preferences_updated)

