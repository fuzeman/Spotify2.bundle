from routing import route_path, function_path


class Objects(object):
    @staticmethod
    def artist():
        pass

    @staticmethod
    def album():
        pass

    @classmethod
    def track(cls, track):
        image_url = function_path('image.png', uri=cls.image(track.album.covers))

        return TrackObject(
            items=[
                MediaObject(
                    parts=[PartObject(
                        #key=cls.get_track_location(track),
                        duration=int(track.duration)
                    )],
                    duration=int(track.duration),
                    container=Container.MP3,
                    audio_codec=AudioCodec.MP3
                )
            ],

            key=route_path('metadata', str(track.uri)),
            rating_key=str(track.uri),

            title=track.name,
            album=track.album.name,
            artist=', '.join([ar.name for ar in track.artists]),

            index=int(track.number),
            duration=int(track.duration),

            source_title='Spotify',

            art=image_url,
            thumb=image_url
        )

    @staticmethod
    def playlist(item):
        if item.uri and item.uri.type == 'group':
            # (Playlist Folder)
            return DirectoryObject(
                key=route_path('playlists', group=item.uri, name=item.name),
                title=item.name,
                thumb=R("placeholder-playlist.png")
            )

        return DirectoryObject(
            key=route_path('playlist', item.uri),
            title=item.name,
            thumb=R("placeholder-playlist.png")
        )

    @staticmethod
    def image(covers):
        #if images.get('640'):
        #    return images['640']
        #elif images.get('300'):
        #    return images['300']

        Log.Info('Unable to select image, available covers: %s' % covers)
        return None
