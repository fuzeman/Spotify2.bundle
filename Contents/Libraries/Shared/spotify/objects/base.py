from spotify.components.base import Component
from spotify.core.helpers import etree_convert

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from lxml import etree
import datetime
import logging

log = logging.getLogger(__name__)


class PropertyProxy(object):
    def __init__(self, name=None, type=None, func=None):
        self.name = name
        self.type = type
        self.func = func

    def get_value(self, instance, key):
        if type(instance) is dict:
            return instance.get(key)

        if not isinstance(instance, Descriptor):
            return getattr(instance, key, None)

        return None

    def get_attribute(self, instance, path):
        if type(path) is str:
            path = path.split('.')

        key = path.pop(0)

        value = self.get_value(instance, key)
        if value is None:
            return None

        if not len(path):
            return value

        return self.get_attribute(value, path)

    def get(self, key, obj, data_type, parser):
        if key in obj._cache:
            return obj._cache[key]

        # Pull value from instance or protobuf
        data = (
            self.get_attribute(obj, self.name) or
            self.get_attribute(obj._data, self.name)
        )

        # Transform attribute values
        value = self.parse(obj, data, data_type, parser)

        # Cache for later use
        obj._cache[key] = value

        return value

    def parse(self, obj, data, data_type, parser):
        # Use 'func' if specified
        if self.func:
            return self.func(data)

        if not self.type:
            return data

        # Convert to 'type'
        if isinstance(data, (list, RepeatedCompositeFieldContainer)):
            return [self.construct(obj.sp, x, data_type, parser) for x in data]

        return self.construct(obj.sp, data, data_type, parser)

    def construct(self, sp, data, data_type, parser):
        if data is None:
            return None

        tag = self.type or self.name

        return parser.parse(sp, data_type, tag, data)

    @staticmethod
    def parse_date(value):
        try:
            return datetime.date(value.year, value.month, value.day)
        except:
            return None


class Descriptor(Component):
    __protobuf__ = None
    __node__ = None

    def __init__(self, sp, data=None, data_type=None, parser=None):
        super(Descriptor, self).__init__(sp)

        self._data = data
        self._data_type = data_type

        self._proxies = self._find_proxies()
        self._parser = parser
        self._cache = {}

    def dict_update(self, attributes):
        if not attributes:
            return self

        # Clear cache to ensure we don't use previous values
        self._cache = {}

        # Update 'self' with values from 'obj'
        for key, value in attributes.items():
            setattr(self, key, value)

        return self

    def protobuf_update(self, obj, *args):
        # Clear cache to ensure we don't use previous values
        self._cache = {}

        # Update 'self' with values from 'obj'
        for key in args:
            setattr(self, key, getattr(obj, key))

        return self

    def _find_proxies(self):
        proxies = {}

        for key in dir(self):
            if key.startswith('_'):
                continue

            value = getattr(self, key)

            if value is PropertyProxy:
                proxies[key] = PropertyProxy(key)
            elif isinstance(value, PropertyProxy):
                if value.name is None:
                    value.name = key

                proxies[key] = value

        return proxies

    def __getattribute__(self, name):
        if name.startswith('_'):
            return super(Descriptor, self).__getattribute__(name)

        if name in self.__dict__:
            return self.__dict__[name]

        # Check for property proxy
        proxies = getattr(self, '_proxies', None)

        if proxies and name in proxies:
            proxy = proxies.get(name)

            if isinstance(proxy, PropertyProxy):
                return proxy.get(name, self, self._data_type, self._parser)

        return super(Descriptor, self).__getattribute__(name)

    def __str__(self):
        return self.__repr__()

    @classmethod
    def from_protobuf(cls, sp, data, parser):
        return cls(sp, data, parser.Protobuf, parser)

    @classmethod
    def from_node(cls, sp, node, types):
        return cls.from_node_dict(sp, etree_convert(node), types)

    @classmethod
    def from_node_dict(cls, sp, data, types):
        raise NotImplementedError()

    @classmethod
    def construct(cls, sp, **kwargs):
        obj = cls(sp)

        for key, value in kwargs.items():
            setattr(obj, key, value)

        return obj
