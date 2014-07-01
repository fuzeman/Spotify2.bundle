from spotify.core.request import Request
from spotify.core.search_response import SearchResponse

import logging
import operator

log = logging.getLogger(__name__)


class SearchRequest(Request):
    types = {
        'tracks':       1,
        'albums':       2,
        'artists':      4,
        'playlists':    8
    }

    def __init__(self, sp, query, query_type='all', start=0, count=50):
        super(SearchRequest, self).__init__(
            sp, 'sp/search', [
                query,
                self.get_type(query_type),
                count,
                start
            ]
        )

    def get_type(self, query_type):
        # Build list of type keys
        if isinstance(query_type, basestring):
            if query_type == 'all':
                query_type = self.types.keys()
            else:
                query_type = [query_type]

        # Bit-shift query type values
        return reduce(operator.or_, [
            self.types[name]
            for name in query_type
            if name in self.types
        ])

    def process(self, data):
        if 'error' in data:
            return self.emit('error', data['error'])

        if 'result' not in data:
            return self.emit('error', 'Invalid search response')

        self.emit('success', SearchResponse.parse(self.sp, data))
