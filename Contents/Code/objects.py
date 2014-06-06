from routing import route_path, function_path
from utils import normalize


class Objects(object):
    def __init__(self, host):
        self.host = host

    def get(self, item):
        node = getattr(item, '__node__', None)

        if node == 'artist':
            return self.artist(item)

        if node == 'album':
            return self.album(item)

        if node == 'track':
            return self.track(item)

        if node == 'playlist':
            return self.playlist(item)

        Log.Debug('Unknown object with node: %s, type: %s' % (node, type(item)))
        return None

    def artist(self, artist):
        image_url = function_path('image.png', uri=self.image(artist.portraits))

        return ArtistObject(
            key=route_path('artist', artist.uri),
            rating_key=artist.uri,

            title=normalize(artist.name),
            source_title='Spotify',

            art=image_url,
            thumb=image_url
        )

    def album(self, album):
        title = normalize(album.name)

        # TODO album years
        #if Prefs["displayAlbumYear"] and album.getYear() != 0:
        #    title = "%s (%s)" % (title, album.getYear())

        image_url = function_path('image.png', uri=self.image(album.covers))

        track_count = None

        if album.discs:
            track_count = len(album.discs[0].tracks)

        return AlbumObject(
            key=route_path('album', album.uri),
            rating_key=album.uri,

            title=title,
            artist=', '.join([normalize(ar.name) for ar in album.artists]),

            track_count=track_count,
            source_title='Spotify',

            art=image_url,
            thumb=image_url,
        )

    def track(self, track):
        image_url = function_path('image.png', uri=self.image(track.album.covers))

        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(
                        key=self.track_url(track),
                        duration=int(track.duration)
                    )],
                    duration=int(track.duration),
                    container=Container.MP3,
                    audio_codec=AudioCodec.MP3
                )
            ],

            key=route_path('metadata', str(track.uri)),
            rating_key=str(track.uri),

            title=normalize(track.name),
            album=normalize(track.album.name),
            artist=', '.join([normalize(ar.name) for ar in track.artists]),

            index=int(track.number),
            duration=int(track.duration),

            source_title='Spotify',

            art=image_url,
            thumb=image_url
        )

    def track_url(self, track):
        if self.host.proxy_tracks and self.host.server:
            return self.host.server.get_track_url(track.uri)

        return function_path('play', uri=str(track.uri), ext='mp3')

    @classmethod
    def playlist(cls, item):
        if item.uri and item.uri.type == 'group':
            # (Playlist Folder)
            return DirectoryObject(
                key=route_path('playlists', group=item.uri, title=normalize(item.name)),
                title=normalize(item.name),
                thumb=R("placeholder-playlist.png")
            )

        thumb = R("placeholder-playlist.png")

        if item.image and item.image.file_uri:
            # Ensure we don't use invalid image uris
            if len(item.image.file_uri.code) == 27:
                thumb = function_path('image.png', uri=cls.image([item.image]))

        return DirectoryObject(
            key=route_path('playlist', item.uri),
            title=normalize(item.name),
            thumb=thumb
        )

    @staticmethod
    def image(covers):
        if covers:
            # TODO might want to sort by 'size' (to ensure this is correct in all cases)
            # Pick largest cover
            return covers[-1].file_url

        Log.Info('Unable to select image, available covers: %s' % covers)
        return None
