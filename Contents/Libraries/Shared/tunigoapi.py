# -*- coding: utf-8 -*-

import time
import requests
import base64
from spotify_web.friendly import Spotify
from spotify_web.spotify import Logging

from spotify_web.proto import mercury_pb2, metadata_pb2, playlist4changes_pb2,\
    playlist4ops_pb2, playlist4service_pb2, toplist_pb2


class Logging():
    log_level = 3

    hooks = {}

    @classmethod
    def hook(cls, level, handler):
        cls.hooks[level] = handler

    @classmethod
    def write(cls, level, str):
        if level in cls.hooks:
            cls.hooks[level](str)
            return True

        if cls.log_level < level:
            return True

        return False

    @classmethod
    def debug(cls, str):
        if cls.write(3, str):
            return

        print "[DEBUG] " + str

    @classmethod
    def notice(cls, str):
        if cls.write(2, str):
            return

        print "[NOTICE] " + str

    @classmethod
    def warn(cls, str):
        if cls.write(1, str):
            return

        print "[WARN] " + str

    @classmethod
    def error(cls, str):
        if cls.write(0, str):
            return

        print "[ERROR] " + str

IMAGE_HOST = "d3rt1990lpmkn.cloudfront.net"

class Tunigo():

    def __init__(self, region="us", log_level=1):
        Logging.log_level = log_level
        self.region = region
        self.root_url = "https://api.tunigo.com/v3/space/"
        Logging.debug("Starting with Tunigo. Region: "  + self.region)

    def getFeaturedPlaylists(self):
      action       = "featured-playlists"
      fixed_params = "page=0&per_page=50&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web"
      date_param   = "dt=" + time.strftime("%Y-%m-%dT%H:%M:%S") #2014-05-29T02%3A01%3A00"
      region_param = "region=" + self.region
      full_url = self.root_url + action + '?' + fixed_params + '&' + date_param + '&' + region_param
      
      Logging.debug("Tunigo - getFeaturedPlaylists url: " + full_url)
      r = requests.get(full_url)
      Logging.debug("Tunigo - getFeaturedPlaylists response: " + str(r.json()))
      if r.status_code != 200 or r.headers['content-type'] != 'application/json':
        return { 'items': [] }
      return r.json()

    def getTopPlaylists(self):
      #https://api.tunigo.com/v3/space/toplists?region=ar&page=0&per_page=50&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web
      # "items": [ "playlist": { "title":"", "description":"", "image":"", "uri":"spotify:user:spotify:playlist:0JvRcIxfujqdEYN3a1aYOw"} ]
      action       = "toplists"
      fixed_params = "page=0&per_page=100&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web"
      date_param   = "dt=" + time.strftime("%Y-%m-%dT%H:%M:%S") #2014-05-29T02%3A01%3A00"
      region_param = "region=" + self.region
      full_url = self.root_url + action + '?' + fixed_params + '&' + date_param + '&' + region_param
      
      Logging.debug("Tunigo - getTopPlaylists url: " + full_url)
      r = requests.get(full_url)
      Logging.debug("Tunigo - getTopPlaylists response: " + str(r.json()))
      if r.status_code != 200 or r.headers['content-type'] != 'application/json':
        return { 'items': [] }
      return r.json()

    def getNewReleases(self):
      #https://api.tunigo.com/v3/space/new-releases?callback=callqqa4q0rw0&region=ar&page=0&per_page=50&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web
      # "items": [ "release":{ "albumName":"", "uri":"spotify:album:2QgK0XPPaPxEsaoZ3FeCSU", "artistName":"", "image":"" } ]
      action       = "new-releases"
      fixed_params = "page=0&per_page=100&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web"
      date_param   = "dt=" + time.strftime("%Y-%m-%dT%H:%M:%S") #2014-05-29T02%3A01%3A00"
      region_param = "region=" + self.region
      full_url = self.root_url + action + '?' + fixed_params + '&' + date_param + '&' + region_param
      
      Logging.debug("Tunigo - getNewReleases url: " + full_url)
      r = requests.get(full_url)
      Logging.debug("Tunigo - getNewReleases response: " + str(r.json()))
      if r.status_code != 200 or r.headers['content-type'] != 'application/json':
        return { 'items': [] }
      return r.json()


