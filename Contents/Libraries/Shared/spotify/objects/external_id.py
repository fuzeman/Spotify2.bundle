from spotify.objects.base import Descriptor, PropertyProxy
from spotify.proto import metadata_pb2


class ExternalId(Descriptor):
    __protobuf__ = metadata_pb2.ExternalId
    __node__ = 'external_id'

    type = PropertyProxy
    id = PropertyProxy

    @classmethod
    def from_node_dict(cls, sp, data, types):
        return cls(sp, {
            'type': data.get('type'),
            'id': data.get('id')
        }, types)
