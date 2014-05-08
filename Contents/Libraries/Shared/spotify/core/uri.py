import binascii

base62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Uri(object):
    def __init__(self, type, code, username=None):
        self.type = type
        self.code = code

        self.username = username

    def to_id(self):
        v = 0

        for c in self.code:
            v = v * 62 + base62.index(c)

        return hex(v)[2:-1].rjust(32, "0")

    def to_gid(self):
        id = self.to_id().rstrip('0')

        return binascii.unhexlify(id)

    def __str__(self):
        parts = []

        if self.username:
            parts.extend(['user', self.username])

        parts.extend([self.type, self.code])

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
        id = binascii.hexlify(gid).rjust(32, '0')

        return cls.from_id(type, id)

    @classmethod
    def from_uri(cls, uri):
        if not uri:
            return None

        parts = uri.split(':')

        if not parts:
            return None

        # Strip 'spotify' from start
        if parts[0] == 'spotify':
            parts = parts[1:]

        # Check if 'user' part exists
        # ('user:<username>:<type>:<code>')
        if parts[0] == 'user':
            if len(parts) < 4:
                return None

            return cls(parts[2], parts[3], parts[1])

        return cls(parts[0], parts[1])
