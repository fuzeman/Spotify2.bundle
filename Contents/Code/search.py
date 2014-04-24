from routing import route_path, function_path
from utils import localized_format

import locale
import urllib


class SpotifySearch(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.client = self.plugin.client

    def run(self, query, limit=7):
        query = urllib.unquote(query)

        Log('Searching for "%s"' % query)

        result = self.client.search(query, max_results=7)

        oc = ObjectContainer(title2="Results")

        def media_append(title, func, key=None):
            if key is None:
                key = title

            items = list(getattr(result, 'get%s' % key)())
            total = getattr(result, 'get%sTotal' % key)()

            if not items or not len(items):
                return

            self.add_header(oc, '%s (%s)' % (
                title,
                locale.format('%d', total, grouping=True)
            ))

            for x in range(limit):
                if x < len(items):
                    func(oc, items[x])
                else:
                    # Add a placeholder to fix alignment on PHT
                    self.add_header(oc, '')

        media_append('Artists', self.add_artist)
        media_append('Albums', self.add_album)
        media_append('Tracks', self.add_track)
        media_append('Playlists', self.add_playlist)

        if not len(oc):
            oc = MessageContainer(
                header=L("MSG_TITLE_NO_RESULTS"),
                message=localized_format("MSG_FMT_NO_RESULTS", query)
            )

        return oc

    #
    # Create objects
    #

    @staticmethod
    def create_artist(artist):
        image_url = artist.portrait.large if artist.portrait else None

        return ArtistObject(
            key=route_path('artist', artist.uri),
            rating_key=artist.uri,

            title=artist.name,
            source_title='Spotify',

            art=function_path('image.png', uri=image_url),
            thumb=function_path('image.png', uri=image_url)
        )

    @staticmethod
    def create_album(album):
        title = album.name

        # TODO displayAlbumYear
        #if Prefs["displayAlbumYear"] and album.getYear() != 0:
        #    title = "%s (%s)" % (title, album.getYear())

        return AlbumObject(
            key=route_path('album', album.uri),
            rating_key=album.uri,

            title=title,
            # TODO artist=album.getArtists(nameOnly=True),

            # TODO track_count=album.getNumTracks(),
            source_title='Spotify',

            art=function_path('image.png', uri=album.cover_large),
            thumb=function_path('image.png', uri=album.cover_large),
        )

    @staticmethod
    def create_track(track):
        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(key=function_path('play', uri=track.uri, ext='mp3'))],
                    container=Container.MP3,
                    audio_codec=AudioCodec.MP3
                )
            ],

            key=track.title,
            rating_key=track.title,

            title=track.title,
            album=track.album.name,
            # TODO artist=track.getArtists(nameOnly=True),

            index=int(track.number),
            duration=int(track.length),

            source_title='Spotify',

            art=function_path('image.png', uri=track.album.cover_large),
            thumb=function_path('image.png', uri=track.album.cover_large)
        )

    #
    # Add objects to container
    #

    @staticmethod
    def add_header(oc, title):
        oc.add(
            DirectoryObject(
                key='',
                title=title
            )
        )

    def add_artist(self, oc, artist):
        oc.add(self.create_artist(artist))

    def add_album(self, oc, album):
        if not self.client.is_album_playable(album):
            Log("Ignoring unplayable album: %s" % album.name())
            return

        oc.add(self.create_album(album))

    def add_track(self, oc, track):
        if not self.client.is_track_playable(track):
            Log("Ignoring unplayable track: %s" % track.name())
            return

        oc.add(self.create_track(track))

    @staticmethod
    def add_playlist(oc, playlist):
        oc.add(
            DirectoryObject(
                key=route_path('playlist', playlist.uri),
                title=playlist.name.decode("utf-8"),
                thumb=playlist.image
            )
        )
