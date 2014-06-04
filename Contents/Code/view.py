from objects import Objects

COLUMNS = 7


class ViewBase(object):
    columns = COLUMNS

    def __init__(self, host):
        self.host = host

        self.objects = Objects(host)

    @property
    def sp(self):
        return self.host.sp

    @property
    def client(self):
        return self.host.client

    @staticmethod
    def use_placeholders():
        return Client.Product in [
            'Plex Home Theater'
        ]

    @classmethod
    def append_header(cls, oc, title='', key=''):
        oc.add(DirectoryObject(key=key, title=title))

    def append_items(self, oc, items, count=COLUMNS, plain=False, placeholders=None):
        """Append spotify metadata `items` to an ObjectContainer"""

        if placeholders is None:
            placeholders = self.use_placeholders()

        for x in range(count):
            if x < len(items):
                # Build object for metadata item
                oc.add(self.objects.get(items[x]))
            elif not plain and placeholders:
                # Add a placeholder to fix alignment on PHT
                self.append_header(oc)
