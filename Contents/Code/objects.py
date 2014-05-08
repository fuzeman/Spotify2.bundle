from routing import route_path


class Objects(object):
    def artist(self):
        pass

    def album(self):
        pass

    def track(self):
        pass

    @staticmethod
    def playlist(item):
        if item.uri.startswith('spotify:group'):
            # (Playlist Folder)
            return DirectoryObject(
                key=route_path('playlists', group=item.uri, name=item.name),
                title=item.name,
                thumb=R("placeholder-playlist.png")
            )

        return DirectoryObject(
            key=route_path('playlist', item.uri),
            title=item.uri,  # TODO use the real name
            thumb=R("placeholder-playlist.png")
        )
