from spotify.core.helpers import set_defaults, etree_convert
from spotify.core.uri import Uri
from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2

import logging

log = logging.getLogger(__name__)


class Track(Descriptor):
    __protobuf__ = metadata_pb2.Track

    gid = PropertyProxy
    uri = PropertyProxy('gid', func=lambda gid: Uri.from_gid('track', gid))
    name = PropertyProxy

    album = PropertyProxy('album', 'Album')
    artists = PropertyProxy('artist', 'Artist')

    number = PropertyProxy
    disc_number = PropertyProxy
    duration = PropertyProxy

    popularity = PropertyProxy
    explicit = PropertyProxy

    external_ids = PropertyProxy('external_id', 'ExternalId')
    restrictions = PropertyProxy('restriction', 'Restriction')
    files = PropertyProxy('file', 'AudioFile')
    alternatives = PropertyProxy('alternative', 'Track')
    # sale_period - []
    preview = PropertyProxy

    @staticmethod
    def __parsers__():
        return [XML]

    def is_available(self):
        catalogues = {}
        available = False

        for restriction in self.restrictions:
            re_available, re_allowed = restriction.check()

            if re_allowed and restriction.catalogues:
                for catalogue in restriction.catalogues:
                    catalogues[catalogue] = True

            if restriction.type is None or restriction.type == 'streaming':
                available |= re_available

        if catalogues.get(self.sp.catalogue):
            return True

        return False

    def find_alternative(self):
        if not self.alternatives:
            log.debug('No alternatives available for "%s"', self.uri)
            return False

        alternative = None

        # Try find an available alternative
        for alternative in self.alternatives:
            if alternative.is_available():
                break

        if alternative is None:
            log.debug('Unable to find alternative for "%s"', self.uri)
            return False

        # Update our object with new attributes
        self.protobuf_update(alternative, 'uri', 'gid', 'restrictions', 'files')
        return True

    def track_uri(self, callback=None):
        """Requests the track stream URI.

        :param callback: Callback to trigger on a successful response
        :type callback: function

        :return: decorate wrapper if no callback is provided, otherwise
                 returns the `Request` object.
        :rtype: function or `spotify.core.request.Request`
        """
        request = self.build('sp/track_uri', 'mp3160', self.uri.to_id())

        return self.request_wrapper(request, callback)

    def track_event(self, lid, event, time):
        """Send the "sp/track_event" event.

        :param lid: Stream lid (from "sp/track_uri")
        :param event: Event
        :param time: Current track playing position (in milliseconds)
        """
        return self.send(
            'sp/track_event',
            lid,
            event,
            time
        )

    def track_progress(self, lid, position, source='unknown', reason='unknown', latency=150,
                       context='unknown', referrer=None):
        """
        :type lid: str
        :type position: int
        :type source: str
        :type reason: str
        :type latency: int
        :type context: str
        :type referrer: dict {'referrer', 'version', 'vendor'}
        :return:
        """

        referrer = set_defaults(referrer, {
            'referrer': 'unknown',
            'version': '0.1.0',
            'vendor': 'com.spotify'
        })

        return self.send(
            'sp/track_progress',
            lid,

            # Start
            source,
            reason,

            # Timings
            position,
            latency,

            # Context
            context,
            str(self.uri),

            # Referrer
            referrer['referrer'],
            referrer['version'],
            referrer['vendor'],
        )

    def track_end(self, lid, position, seeks=None, latency=150, context='unknown',
                  source=None, reason=None, referrer=None):
        """
        :type lid: str
        :type position: int
        :type seeks: dict {'num_forward', 'num_backward', 'ms_forward', 'ms_backward'}
        :type latency: int
        :type context: str
        :type source: dict {'start', 'end'}
        :type reason: dict {'start', 'end'}
        :type referrer: dict {'referrer', 'version', 'vendor'}
        :return:
        """

        seeks = set_defaults(seeks, {
            'num_forward': 0,
            'num_backward': 0,
            'ms_forward': 0,
            'ms_backward': 0
        })

        source = set_defaults(source, {
            'start': 'unknown',
            'end': 'unknown'
        })

        reason = set_defaults(reason, {
            'start': 'unknown',
            'end': 'unknown'
        })

        referrer = set_defaults(referrer, {
            'referrer': 'unknown',
            'version': '0.1.0',
            'vendor': 'com.spotify'
        })

        return self.send(
            'sp/track_end',
            lid,

            # Timings
            position,  # ms_played
            position,  # ms_played_union

            # Seek count
            seeks['num_forward'],
            seeks['num_backward'],
            seeks['ms_forward'],
            seeks['ms_backward'],

            latency,

            # Context
            str(self.uri),
            context,

            # Source
            source['start'],
            source['end'],

            # Reason
            reason['start'],
            reason['end'],

            # Referrer
            referrer['referrer'],
            referrer['version'],
            referrer['vendor'],

            position  # max_continuous
        )


class XML(Track):
    __tag__ = 'track'

    @classmethod
    def parse(cls, sp, data, parser):
        if type(data) is not dict:
            data = etree_convert(data, {
                'artist-id': ('artist-id', 'artist')
            })

        uri = Uri.from_id('track', data.get('id'))

        return Track(sp, {
            'gid': uri.to_gid(),
            'uri': uri,
            'name': data.get('title'),

            'artist': [
                {
                    '$source': 'node',
                    'id': artist.get('artist-id'),
                    'name': artist.get('artist')
                }
                for artist in data.get('artist', [])
            ],

            'album': {
                '$source': 'node',
                'id': data.get('album-id'),
                'name': data.get('album'),

                'artist-id': data.get('album-artist-id'),
                'artist-name': data.get('album-artist'),

                'cover': data.get('cover'),
                'cover-small': data.get('cover-small'),
                'cover-large': data.get('cover-large'),
                },

            # TODO year
            'number': int(data.get('track-number')),
            'duration': int(data.get('length')),

            'popularity': float(data.get('popularity')),

            'external_id': data.get('external-ids'),
            'restriction': data.get('restrictions'),
            'file': data.get('files')
        }, parser.XML, parser)
