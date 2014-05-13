from spotify.components.base import Component


class User(Component):
    def __init__(self, sp, username):
        super(User, self).__init__(sp)

        self.username = username

    def playlists(self, start=0, count=100, callback=None):
        return self.sp.playlists(
            self.username,
            start, count,
            callback
        )
