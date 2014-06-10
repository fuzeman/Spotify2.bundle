from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)

CATALOGUE_NAME_MAP = {
    # SUBSCRIPTION
    'premium':   1,
    'unlimited': 1,
    # AD
    'free':      0
}

CATALOGUE_ID_MAP = {
    0: 'free',
    1: 'premium',
    3: 'shuffle'
}


def parse_catalogues(value):
    return [
        CATALOGUE_ID_MAP[x]
        for x in value
        if x in CATALOGUE_ID_MAP
    ]


def parse_countries(value):
    if value is None:
        return None

    return [value[i:i+2] for i in range(0, len(value), 2)]


class Restriction(Descriptor):
    __protobuf__ = metadata_pb2.Restriction
    __node__ = 'restriction'

    catalogues = PropertyProxy('catalogue', func=parse_catalogues)
    countries_allowed = PropertyProxy(func=parse_countries)
    countries_forbidden = PropertyProxy(func=parse_countries)
    type = PropertyProxy

    def check(self):
        available = True
        allowed = True

        if self.countries_allowed is not None:
            available = len(self.countries_allowed) != 0
            allowed = self.sp.country in self.countries_allowed
        elif self.countries_forbidden is not None:
            allowed = self.sp.country not in self.countries_forbidden

        return available, allowed


    @classmethod
    def from_node_dict(cls, sp, data, types):
        catalogue = [
            CATALOGUE_NAME_MAP[name]
            for name in data.get('catalogues', '').split(',')
            if name in CATALOGUE_NAME_MAP
        ]

        return cls(sp, {
            'catalogue': catalogue,
            'countries_allowed': data.get('allowed', '').replace(',', ''),
            'countries_forbidden': data.get('forbidden', '').replace(',', '')
        }, types)
