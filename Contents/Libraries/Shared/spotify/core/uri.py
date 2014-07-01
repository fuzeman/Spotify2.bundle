import binascii

base62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Uri(object):
    def __init__(self, type, code, username=None, title=None):
        self.type = type
        self.code = code

        self.username = username
        self.title = title

    def to_id(self, size=32):
        v = 0

        for c in self.code:
            v = v * 62 + base62.index(c)

        return hex(v)[2:-1].rjust(size, '0')

    def to_gid(self, size=32):
        try:
            return binascii.unhexlify(self.to_id(size=size))
        except TypeError:
            return None

    def __str__(self):
        parts = []

        if self.username:
            parts.extend(['user', self.username])

        parts.append(self.type)

        if self.code:
            parts.append(self.code)

        if self.title:
            parts.append(self.title)

        return 'spotify:%s' % (':'.join(parts))

    def __repr__(self):
        return '<Uri %s>' % (self.__str__())

    @classmethod
    def from_id(cls, type, id):
        if not id:
            return None

        res = []
        v = int(id, 16)

        while v > 0:
            res = [v % 62] + res
            v /= 62

        code = ''.join([base62[i] for i in res])

        return cls(type, code.rjust(22, '0'))

    @classmethod
    def from_gid(cls, type, gid):
        if gid is None:
            return None

        id = binascii.hexlify(gid).rjust(32, '0')

        return cls.from_id(type, id)

    @classmethod
    def from_uri(cls, uri):
        if not uri:
            return None

        if type(uri) is Uri:
            return uri

        parts = uri.split(':')

        if not parts:
            return None

        # Strip 'spotify' from start
        if parts[0] == 'spotify':
            parts = parts[1:]

        # Check if 'user' part exists
        # ('user:<username>:<type>:<code>')
        if parts[0] == 'user':
            return cls(
                username=parts[1],
                type=parts[2],
                code=parts[3] if len(parts) > 3 else None
            )

        # Spotify groups (playlist folders)
        # ('spotify;start-group:<code>:<title>')
        if parts[0] == 'group' or parts[0].endswith('-group'):
            return cls(
                type=parts[0],
                code=parts[1],
                title=parts[2] if len(parts) > 2 else None
            )

        return cls(parts[0], parts[1])
