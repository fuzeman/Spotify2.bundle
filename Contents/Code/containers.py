from objects import Objects
from utils import ViewMode


class Containers(object):
    @staticmethod
    def playlists(playlists, group=None, name=None):
        oc = ObjectContainer(
            title2=name or L("MENU_PLAYLISTS"),
            content=ContainerContent.Playlists,
            view_group=ViewMode.Playlists
        )

        for item in playlists.fetch(group):
            oc.add(Objects.playlist(item))

        return oc

    @staticmethod
    def playlist(playlist):
        oc = ObjectContainer(
            title2=playlist.name,
            content=ContainerContent.Tracks,
            view_group=ViewMode.Tracks
        )

        for track in playlist.items:
            oc.add(DirectoryObject(
                key=track.uri,
                title=track.uri,  # TODO use the real name
                thumb=R("placeholder-playlist.png")
            ))

        return oc
