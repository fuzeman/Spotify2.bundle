from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)

CATALOGUE_MAP = {
    # SUBSCRIPTION
    'premium':   1,
    'unlimited': 1,
    # AD
    'free':      0
}


def split_countries(value):
    if value is None:
        return None

    return [value[i:i+2] for i in range(0, len(value), 2)]


class Restriction(Descriptor):
    __protobuf__ = metadata_pb2.Restriction
    __node__ = 'restriction'

    catalogues = PropertyProxy('catalogue')
    countries_allowed = PropertyProxy(func=split_countries)
    countries_forbidden = PropertyProxy(func=split_countries)
    type = PropertyProxy

    def check(self):
        # Check restriction validity
        if not self.countries_allowed and not self.countries_forbidden:
            return False, 'invalid'

        # Check catalogue
        u_catalogue = CATALOGUE_MAP.get(self.sp.user_info.get('catalogue'))

        if u_catalogue not in self.catalogues:
            return False, 'catalogue not allowed'

        # Check country
        u_country = self.sp.user_info.get('country')

        allowed = not self.countries_allowed or u_country in self.countries_allowed
        forbidden = u_country in self.countries_forbidden

        # Assume allowed (if country is in both lists)
        if allowed and forbidden:
            forbidden = False

        # Passed restriction
        if allowed and not forbidden:
            return True, ''

        # Return failure reason
        if not allowed:
            return False, 'country not allowed'

        if forbidden:
            return False, 'country forbidden'

        return False, 'unknown failure'

    @classmethod
    def from_node_dict(cls, sp, data, types):
        catalogue = [
            CATALOGUE_MAP[name]
            for name in data.get('catalogues', '').split(',')
            if name in CATALOGUE_MAP
        ]

        return cls(sp, {
            'catalogue': catalogue,
            'countries_allowed': data.get('allowed', '').replace(',', ''),
            'countries_forbidden': data.get('forbidden', '').replace(',', '')
        }, types)
