from spotify.objects import Parser


class TunigoResponse(object):
    def __init__(self):
        self.items = None
        self.total = None

        self.regions = None
        self.products = None

    @classmethod
    def construct(cls, sp, data):
        obj = TunigoResponse()

        # Parse items
        obj.items = []

        for container in data.get('items', []):
            for tag, item in container.items():
                obj.items.append(Parser.parse(sp, Parser.Tunigo, tag, item))

        # Fill extras
        obj.total = data.get('totalItems')
        obj.regions = data.get('regions')
        obj.products = data.get('products')

        return obj
