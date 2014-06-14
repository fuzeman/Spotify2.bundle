import json
import logging
import os

log = logging.getLogger(__name__)


class ProfileManager(object):
    def __init__(self):
        self.profiles = {}

    def load_directory(self, path):
        log.debug('Loading profiles from "%s"', path)

        for root, dirs, files in os.walk(path):
            for filename in files:
                if not filename.endswith('.json'):
                    continue

                self.load_file(os.path.abspath(os.path.join(root, filename)))

    def load_file(self, path):
        log.debug('Loading profile "%s"', path)

        data = None

        try:
            with open(path, 'r') as fp:
                data = json.loads(fp.read())
        except Exception, ex:
            log.warn('Unable to read profile at "%s" - %s', path, ex)

        name = data.get('name')

        if not name:
            log.warn('Unable to load profile at "%s" - missing "name" attribute', path)
            return

        profile = Profile.parse(data)

        self.profiles[name.lower()] = profile
        log.info('Loaded profile with name "%s" (supports_ranges: %s)', profile.name, profile.supports_ranges)

    def get(self, name):
        if name:
            name = name.lower()

        if name in self.profiles:
            return self.profiles[name]

        return None

    def match(self, headers):
        # Find device name
        device = headers.get('X-Plex-Device')

        if device is None:
            log.debug('Missing "X-Plex-Device" header, returning generic profile - headers: %s', headers)
            return self.profiles.get('generic')

        # Find profile
        profile = self.get(device)

        if profile is None:
            log.debug('Unable to find profile for %s, returning generic profile - headers: %s', repr(device), headers)
            return self.profiles.get('generic')

        return profile


class Profile(object):
    def __init__(self):
        self.name = None

        self.supports_ranges = None

    @classmethod
    def parse(cls, data):
        supports = data.get('supports', {})

        obj = cls()
        obj.name = data.get('name')
        obj.supports_ranges = supports.get('ranges', True)

        return obj
