class Range(object):
    def __init__(self, start=None, end=None, unit='bytes'):
        self.unit = unit
        self._start = start
        self._end = end

        self.original = None

    @property
    def start(self):
        if self._start is None:
            return ''

        return self._start

    @start.setter
    def start(self, value):
        self._start = value

    @property
    def end(self):
        if self._end is None:
            return ''

        return self._end

    @end.setter
    def end(self, value):
        self._end = value

    def content_range(self, length):
        o = ContentRange()
        o.unit = self.unit

        if self._start is None and self._end is None:
            return None

        if self._start is None:
            o.start = length - o.end
            o.end = length - 1
        elif self._end is None:
            o.start = self._start
            o.end = length - 1
        else:
            o.start = self._start
            o.end = self._end

        o.length = length

        return o

    def tuple(self):
        return (
            self.start,
            self.end
        )

    def __str__(self):
        return '%s=%s-%s' % (
            self.unit,

            self.start,
            self.end,
        )

    def __repr__(self):
        return '<Range %s>' % str(self)

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

            self.start,
            self.end,
            self.length
        )

    def __repr__(self):
        return '<ContentRange %s>' % str(self)

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
