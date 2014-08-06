from routing import route_path
from utils import ViewMode, normalize
from view import ViewBase

from spotify.objects.playlist import Playlist


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
                oc, '%s (%s)' % (L('TOP_TRACKS'), len(track_uris)),
                route_path('artist', artist.uri, 'top_tracks')
            )
            self.append_items(oc, tracks)

            # Albums
            self.append_header(
                oc, '%s (%s)' % (L('ALBUMS'), len(album_uris)),
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

    def artist_top_tracks(self, artist, callback):
        oc = ObjectContainer(
            title2='%s - %s' % (normalize(artist.name), L('TOP_TRACKS')),
            content=ContainerContent.Albums
        )

        track_uris, _ = self.client.artist_uris(artist)

        @self.sp.metadata(track_uris)
        def on_albums(track):
            for track in track:
                oc.add(self.objects.get(track))

            callback(oc)

    def artist_albums(self, artist, callback):
        oc = ObjectContainer(
            title2='%s - %s' % (normalize(artist.name), L('ALBUMS')),
            content=ContainerContent.Albums
        )

        _, album_uris = self.client.artist_uris(artist)

        @self.sp.metadata(album_uris)
        def on_albums(albums):
            for album in albums:
                oc.add(self.objects.get(album))

            callback(oc)

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

    def playlists(self, playlists, group=None, title=None):
        oc = ObjectContainer(
            title2=normalize(title) or L('PLAYLISTS'),
            content=ContainerContent.Playlists,
            view_group=ViewMode.Playlists
        )

        if type(playlists) is Playlist:
            items = playlists.fetch(group)
        else:
            items = playlists

        for item in items:
            if not item:
                # Ignore playlists which fail to load
                continue

            oc.add(self.objects.playlist(item))

        return oc

    def playlist(self, playlist):
        name = normalize(playlist.name)

        if playlist.uri.type == 'starred':
            name = L('STARRED')

        oc = ObjectContainer(
            title2=name,
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        for x, track in enumerate(playlist.fetch()):
            oc.add(self.objects.track(track, index=x))

        return oc

    def artists(self, artists, callback):
        oc = ObjectContainer(
            title2=L('ARTISTS'),
            #content=ContainerContent.Artists
        )

        for artist in artists:
            oc.add(self.objects.artist(artist))

        callback(oc)

    def albums(self, albums, callback, title=None):
        if title is None:
            title = L('ALBUMS')

        oc = ObjectContainer(
            title2=title,
            #content=ContainerContent.Albums
        )

        for album in albums:
            oc.add(self.objects.album(album))

        callback(oc)
