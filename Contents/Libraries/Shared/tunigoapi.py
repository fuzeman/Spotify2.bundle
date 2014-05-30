import logging
import requests
import time

log = logging.getLogger(__name__)


class Tunigo():
    def __init__(self, region="us"):
        self.region = region
        self.root_url = "https://api.tunigo.com/v3/space/"
        log.debug("Starting with Tunigo. Region: "  + self.region)

    def getFeaturedPlaylists(self):
      action       = "featured-playlists"
      fixed_params = "page=0&per_page=50&suppress_response_codes=1&locale=en&product=premium&version=6.31.1&platform=web"
      date_param   = "dt=" + time.strftime("%Y-%m-%dT%H:%M:%S") #2014-05-29T02%3A01%3A00"
      region_param = "region=" + self.region
      full_url = self.root_url + action + '?' + fixed_params + '&' + date_param + '&' + region_param

      log.debug("Tunigo - getFeaturedPlaylists url: " + full_url)
      r = requests.get(full_url)
      log.debug("Tunigo - getFeaturedPlaylists response: " + str(r.json()))
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

      log.debug("Tunigo - getTopPlaylists url: " + full_url)
      r = requests.get(full_url)
      log.debug("Tunigo - getTopPlaylists response: " + str(r.json()))
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

      log.debug("Tunigo - getNewReleases url: " + full_url)
      r = requests.get(full_url)
      log.debug("Tunigo - getNewReleases response: " + str(r.json()))
      if r.status_code != 200 or r.headers['content-type'] != 'application/json':
        return { 'items': [] }
      return r.json()
