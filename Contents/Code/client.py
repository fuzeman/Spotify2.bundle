from settings import PLUGIN_ID

from spotify_web.friendly import Spotify
from spotify_web.spotify import Logging
from tunigoapi import Tunigo


class SpotifyClient(object):
    audio_buffer_size = 50
    user_agent = PLUGIN_ID

    def __init__(self, username, password, region):
        """ Initializer

        :param username:       The username to connect to spotify with.
        :param password:       The password to authenticate with.
        """

        # Hook logging
        Logging.hook(3, Log.Debug)
        Logging.hook(2, Log.Info)
        Logging.hook(1, Log.Warn)
        Logging.hook(0, Log.Error)

        self.spotify = Spotify(username, password, log_level=3)
        self.username = username
        
        self.tunigo  = Tunigo(region)


    #
    # Public methods
    #

    def is_logged_in(self):
        return self.spotify.logged_in()

    def shutdown(self):
        self.spotify.api.shutdown()

    def search(self, query, query_type='all', max_results=50, offset=0):
        """ Execute a search

        :param query:          A query string.
        """
        return self.spotify.search(query, query_type, max_results, offset)

    #
    # Media
    #

    def get(self, uri):
        return self.spotify.objectFromURI(uri)

    def is_album_playable(self, album):
        """ Check if an album can be played by a client or not """
        return True

    def is_track_playable(self, track):
        """ Check if a track can be played by a client or not """
        return True

    #
    # Playlists
    #
    def get_featured_playlists(self):
        """ Return the featured playlists"""
        pl_json = self.tunigo.getFeaturedPlaylists()

        playlist_uris  = []
        playlist_descs = {}
        playlist_imgs  = {}
        for item_json in pl_json['items']:
            playlist_uri  = item_json['playlist']['uri']
            playlist_desc = item_json['playlist']['description']
            playlist_img  = item_json['playlist']['image']
            
            uri_parts = playlist_uri.split(':')
            if len(uri_parts) < 2:
                continue

            # TODO support playlist folders properly
            if uri_parts[1] in ['start-group', 'end-group']:
                continue
            
            playlist_uris.append(playlist_uri)
            playlist_descs[playlist_uri]= playlist_desc
            playlist_imgs[playlist_uri]= playlist_img
            
        playlists = self.spotify.objectFromURI(playlist_uris, asArray=True)
        
        for pl in playlists:
            pl.description   = playlist_descs[pl.getURI()]
            pl.image_id = playlist_imgs[pl.getURI()]
        
        return playlists

    def get_top_playlists(self):
        """ Return the top playlists"""
        pl_json = self.tunigo.getTopPlaylists()

        playlist_uris  = []
        playlist_descs = {}
        playlist_imgs  = {}
        for item_json in pl_json['items']:
            playlist_uri  = item_json['playlist']['uri']
            playlist_desc = item_json['playlist']['description']
            playlist_img  = item_json['playlist']['image']
            
            uri_parts = playlist_uri.split(':')
            if len(uri_parts) < 2:
                continue

            # TODO support playlist folders properly
            if uri_parts[1] in ['start-group', 'end-group']:
                continue
            
            playlist_uris.append(playlist_uri)
            playlist_descs[playlist_uri]= playlist_desc
            playlist_imgs[playlist_uri]= playlist_img
            
        playlists = self.spotify.objectFromURI(playlist_uris, asArray=True)
        
        for pl in playlists:
            pl.description   = playlist_descs[pl.getURI()]
            pl.image_id = playlist_imgs[pl.getURI()]
        
        return playlists

    def get_new_releases(self):
        """ Return the top playlists"""
        al_json = self.tunigo.getNewReleases()
        album_uris  = []
        for item_json in al_json['items']:
            album_uris.append(item_json['release']['uri'])
            
        return self.spotify.objectFromURI(album_uris, asArray=True)


    def get_playlists(self):
        """ Return the user's playlists"""
        return self.spotify.getPlaylists()

    def get_starred(self):
        """ Return the user's starred tracks"""
        return self.get('spotify:user:%s:starred' % self.username)

    #
    # My Music
    #

    def get_my_albums(self):
        """ Return the user's albums"""
        return self.spotify.getMyMusic(type="albums")

    def get_my_artists(self):
        """ Return the user's artists"""
        return self.spotify.getMyMusic(type="artists")

