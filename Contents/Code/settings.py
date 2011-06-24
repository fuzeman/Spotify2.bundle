'''
Settings used throughout the plguin
'''

PLUGIN_ID = "com.plexapp.plugins.spotify"
VERSION     = 0.2
PREFIX      = "/music/spotify"
ROUTEBASE   = PREFIX + '/'
RESTART_URL = "http://localhost:32400/:/plugins/%s/restart" % PLUGIN_ID
SERVER_PORT = 32420
REQUEST_TIMEOUT = 15
POLL_INTERVAL = 0.1
POLL_TIMEOUT = 1
