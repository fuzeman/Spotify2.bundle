from objects import Objects
from utils import ViewMode


class Containers(object):
    def __init__(self, host):
        self.host = host

        self.objects = Objects(host)

    def playlists(self, playlists, group=None, name=None):
        oc = ObjectContainer(
            title2=name or L("MENU_PLAYLISTS"),
            content=ContainerContent.Playlists,
            view_group=ViewMode.Playlists
        )

        for item in playlists.fetch(group):
            oc.add(self.objects.playlist(item))

        return oc

    def playlist(self, playlist):
        name = playlist.name

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

    def metadata(self, track):
        oc = ObjectContainer()
        oc.add(self.objects.track(track))

        return oc
