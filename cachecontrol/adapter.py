from requests.adapters import HTTPAdapter

from cachecontrol.controller import CacheController
from cachecontrol.cache import DictCache


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = set(['PUT', 'DELETE'])

    def __init__(self, cache=None, *args, **kw):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = cache or DictCache()
        self.controller = CacheController(self.cache)

    def send(self, request, **kw):
        """Send a request. Use the request information to see if it
        exists in the cache.
        """
        if request.method == 'GET':
            cached_response = self.controller.cached_request(
                request.url, request.headers
            )
            if cached_response:
                return cached_response
            # check for etags and add headers if appropriate
            headers = self.controller.add_headers(request.url)
            request.headers.update(headers)

        resp = super(CacheControlAdapter, self).send(request, **kw)
        return resp

    def build_response(self, request, response):
        resp = super(CacheControlAdapter, self).build_response(
            request, response
        )

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Try to store the response if it is a GET
        elif request.method == 'GET':
            if response.status == 304:
                resp = self.controller.get_cached_response(request)
            else:
                self.controller.cache_response(request, resp)
            print self.controller.cache.data

        # Give the request a from_cache attr to let people use it
        # rather than testing for hasattr.
        if not hasattr(resp, 'from_cache'):
            resp.from_cache = False

        return resp
