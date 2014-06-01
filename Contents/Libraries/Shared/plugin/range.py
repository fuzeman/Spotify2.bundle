class Range(object):
    def __init__(self, start=None, end=None, unit='bytes'):
        self.unit = unit
        self.start = start
        self.end = end

        self.original = None

    def content_range(self, length):
        o = ContentRange()
        o.length = length
        o.unit = self.unit

        if self.start is None and self.end is None:
            return None

        if self.start is None:
            o.start = length - o.end
            o.end = length - 1
        elif self.end is None:
            o.start = self.start
            o.end = length - 1
        else:
            o.start = self.start
            o.end = self.end

        return o

    @classmethod
    def parse(cls, value):
        if not value:
            return None

        o = cls()
        o.original = value

        # Unit
        parts = value.split('=')
        if len(parts) != 2:
            return None

        o.unit, value = parts

        # Range
        parts = value.split('-')
        if len(parts) != 2:
            return None

        o.start, o.end = [int(x) if x else None for x in parts]

        return o


class ContentRange(Range):
    def __init__(self, start=None, end=None, length=None, unit='bytes'):
        super(ContentRange, self).__init__(start, end, unit)

        self.length = length

    def __str__(self):
        return '%s %s-%s/%s' % (
            self.unit,

            self.start, self.end,
            self.length
        )

    @classmethod
    def parse(cls, value):
        if not value:
            return None

        o = cls()
        o.original = value

        # Unit
        parts = value.split(' ')
        if len(parts) != 2:
            return None

        o.unit, value = parts

        # Length
        parts = value.split('/')
        if len(parts) != 2:
            return None

        value, o.length = parts[0], int(parts[1])

        # Range
        parts = value.split('-')
        if len(parts) != 2:
            return None

        o.start, o.end = [int(x) if x else None for x in parts]

        return o
