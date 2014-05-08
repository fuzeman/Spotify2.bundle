from spotify.components import Authentication, Connection, Metadata, Search


class ComponentManager(object):
    def __init__(self, sp):
        """
        :type sp: spotify.client.Spotify
        """

        self.sp = sp

        self.connection = Connection(self.sp)\
            .pipe(['error', 'connect'], self.sp)\
            .on('command', self.sp.on_command)

        self.authentication = Authentication(self.sp)\
            .pipe('error', self.sp)\
            .on('authenticated', self.sp.on_authenticated)

        self.metadata = Metadata(self.sp)

        self.search = Search(self.sp)
