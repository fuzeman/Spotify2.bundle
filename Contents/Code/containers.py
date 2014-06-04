from routing import route_path
from utils import ViewMode, normalize
from view import ViewBase


class Containers(ViewBase):
    #
    # Metadata
    #

    # TODO list singles?
    def artist(self, artist, callback):
        oc = ObjectContainer(
            title2=normalize(artist.name),
            content=ContainerContent.Albums
        )

        track_uris, album_uris = self.client.artist_uris(artist)
        tracks, albums = [], []

        def build():
            # Check if we are ready to build the response yet
            if len(albums) != len(album_uris[:self.columns]):
                return

            if len(tracks) != len(track_uris[:self.columns]):
                return

            # Top Tracks
            self.append_header(
                oc, 'Top Tracks (%s)' % len(track_uris),
                route_path('artist', artist.uri, 'top_tracks')
            )
            self.append_items(oc, tracks)

            # Albums
            self.append_header(
                oc, 'Albums (%s)' % len(album_uris),
                route_path('artist', artist.uri, 'albums')
            )
            self.append_items(oc, albums)

            callback(oc)

        if not track_uris and not album_uris:
            build()
            return

        # Request albums
        @self.sp.metadata(album_uris[:self.columns])
        def on_albums(items):
            albums.extend(items)
            build()

        # Request tracks
        @self.sp.metadata(track_uris[:self.columns])
        def on_tracks(items):
            tracks.extend(items)
            build()


    def artist_albums(self, artist, callback):
        oc = ObjectContainer(
            title2='%s - %s' % (normalize(artist.name), 'Albums'),
            content=ContainerContent.Albums
        )

        album_uris = [al.uri for al in artist.albums if al is not None]

        @self.sp.metadata(album_uris)
        def on_albums(albums):
            for album in albums:
                oc.add(self.objects.album(album))

            callback(oc)

    def artist_tracks(self, artist, callback):
        pass

    def album(self, album, callback):
        oc = ObjectContainer(
            title2=normalize(album.name),
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        track_uris = [tr.uri for tr in album.tracks]

        @self.sp.metadata(track_uris)
        def on_tracks(tracks):
            for track in tracks:
                oc.add(self.objects.track(track))

            callback(oc)

    def metadata(self, track):
        oc = ObjectContainer()
        oc.add(self.objects.track(track))

        return oc

    #
    # Your Music
    #

    def playlists(self, playlists, group=None, name=None):
        oc = ObjectContainer(
            title2=normalize(name) or L("MENU_PLAYLISTS"),
            content=ContainerContent.Playlists,
            view_group=ViewMode.Playlists
        )

        for item in playlists.fetch(group):
            oc.add(self.objects.playlist(item))

        return oc

    def playlist(self, playlist):
        name = normalize(playlist.name)

        if playlist.uri.type == 'starred':
            name = L("MENU_STARRED")

        oc = ObjectContainer(
            title2=name,
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        for track in playlist.fetch():
            oc.add(self.objects.track(track))

        return oc

    def artists(self, artists, callback):
        oc = ObjectContainer(
            title2=L("MENU_ARTISTS"),
            content=ContainerContent.Artists
        )

        for artist in artists:
            oc.add(self.objects.artist(artist))

        callback(oc)

    def albums(self, albums, callback):
        oc = ObjectContainer(
            title2=L("MENU_ALBUMS"),
            content=ContainerContent.Albums
        )

        for album in albums:
            oc.add(self.objects.album(album))

        callback(oc)
