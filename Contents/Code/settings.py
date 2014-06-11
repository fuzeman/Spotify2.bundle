PLUGIN_ID   = "com.plexapp.plugins.spotify2"
VERSION     = '0.5.2-beta'
PREFIX      = "/music/spotify"
ROUTEBASE   = PREFIX + '/'
SERVER_PORT = 32420

LOGGERS     = [
    'spotify2',

    'cherrypy',
    'plugin',
    'pyemitter',
    'requests',
    'spotify'
]
