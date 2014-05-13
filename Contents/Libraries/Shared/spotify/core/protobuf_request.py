from spotify.core.request import Request
from spotify.objects import NAME_MAP
from spotify.proto.mercury_pb2 import MercuryRequest, MercuryMultiGetRequest, MercuryMultiGetReply

import base64
import httplib
import logging

log = logging.getLogger(__name__)


class ProtobufRequest(Request):
    def __init__(self, sp, name, requests, schema_response, header=None,
                 defaults=None):
        """
        :type sp: spotify.client.Spotify
        :type name: str
        :type requests: list of dict
        :type schema_response: dict or spotify.objects.base.Descriptor

        :type header: dict
        :type defaults: dict
        """
        super(ProtobufRequest, self).__init__(sp, name, None)

        self.schema_response = schema_response
        self.defaults = defaults

        self.request = None
        self.payload = None

        self.prepare(requests, header)

    def prepare(self, requests, header=None):
        if type(requests) is not list:
            requests = [requests]

        request = None
        payload = None

        if len(requests) == 1:
            request = self.prepare_single(requests[0])
        elif len(requests) > 1:
            if header is None:
                raise ValueError('A header is required to send multiple requests')

            header['content_type'] = 'vnd.spotify/mercury-mget-request'

            request, payload = self.prepare_multi(header, requests)
        else:
            raise ValueError('At least one request is required')

        self.request = request
        self.payload = payload

    def prepare_single(self, request):
        m_request = MercuryRequest()

        # Fill MercuryRequest
        m_request.uri = request.get('uri', '')
        m_request.content_type = request.get('content_type', '')
        m_request.method = request.get('method', '')
        m_request.source = request.get('source', '')

        return m_request

    def prepare_multi(self, header, requests):
        request = self.prepare_single(header)

        payload = MercuryMultiGetRequest()

        for r in requests:
            payload.request.extend([self.prepare_single(r)])

        return request, payload

    def process(self, data):
        log.debug('process data: %s', repr(data))
        result = data['result']

        header = MercuryRequest()
        header.ParseFromString(base64.b64decode(result[0]))

        if 400 <= header.status_code < 600:
            message = httplib.responses[header.status_code] or 'Unknown Error'

            if 400 <= header.status_code < 500:
                self.emit('error', 'Client Error: %s (%s)' % (message, header.status_code))
            elif 500 <= header.status_code < 600:
                self.emit('error', 'Server Error: %s (%s)' % (message, header.status_code))

            return

        if self.payload and header.content_type != 'vnd.spotify/mercury-mget-reply':
            self.emit('error', 'Server Error: Server didn\'t send a multi-GET reply for a multi-GET request!')
            return

        self.parse(header.content_type, base64.b64decode(result[1]))

    def parse(self, content_type, data):
        if content_type == 'vnd.spotify/mercury-mget-reply':
            response = MercuryMultiGetReply()
            response.ParseFromString(data)

            items = []

            for item in response.reply:
                if item.status_code != 200:
                    items.append(None)
                    continue

                items.append(self.parse_item(item.content_type, item.body))

            self.emit('success', items)
        else:
            self.emit('success', self.parse_item(content_type, data))

    def parse_item(self, content_type, data):
        parser_cls = self.schema_response

        if type(parser_cls) is dict:
            parser_cls = parser_cls.get(content_type)

        if parser_cls is None:
            self.emit('error', 'Unrecognized metadata type: "%s"' % content_type)
            return

        internal = parser_cls.__protobuf__()
        internal.ParseFromString(data)

        return parser_cls.from_protobuf(self.sp, internal, NAME_MAP, self.defaults)

    def build(self, seq):
        self.args = [
            self.get_number(self.request.method),
            base64.b64encode(self.request.SerializeToString())
        ]

        if self.payload:
            self.args.append(base64.b64encode(self.payload.SerializeToString()))

        return super(ProtobufRequest, self).build(seq)

    def get_number(self, method):
        if method == 'SUB':
            return 1

        if method == 'UNSUB':
            return 2

        return 0
