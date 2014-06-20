from spotify.components.base import Component
from spotify.tunigo.request import TunigoRequest


class Explore(Component):
    def featured_playlists(self, page=0, per_page=100, callback=None):
        request = TunigoRequest(self.sp, 'featured-playlists', {
            'page': page,
            'per_page': per_page
        })

        return self.request_wrapper(request, callback)

    def top_playlists(self, page=0, per_page=100, callback=None):
        request = TunigoRequest(self.sp, 'toplists', {
            'page': page,
            'per_page': per_page
        })

        return self.request_wrapper(request, callback)

    def new_releases(self, page=0, per_page=100, callback=None):
        request = TunigoRequest(self.sp, 'new-releases', {
            'page': page,
            'per_page': per_page
        })

        return self.request_wrapper(request, callback)
