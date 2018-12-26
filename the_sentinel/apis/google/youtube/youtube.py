"""
Base module for youtube related things
"""
from typing import Dict, Any, Optional
import requests


class Youtube(requests.Session):
    """
    Base class, sets up authentication and url munging
    """
    API_BASE = 'https://www.googleapis.com'
    REST_BASE = ['youtube', 'v3']
    ENDPOINT_BASE = ''
    AUTH: Dict[str, str]
    AUTH = {}

    def __init__(self, *args, key=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.id: Optional[str] = None # pylint: disable=invalid-name
        if key:
            self.AUTH['key'] = key
        self._json: Optional[Any] = None
        self._resp: Optional[requests.Response] = None

    @property
    def resp(self) -> requests.Response:
        """
        Lazy getter for youtube Response for given object
        """
        if self._resp is None:
            self._resp = self.get(params={'id': self.id})
            self._resp.raise_for_status()
        return self._resp

    @property
    def json(self) -> Any:
        """
        Takes advantage of self.resp for lazy json repr
        """
        return self.resp.json()

    def request(self, method, url='', params=None, **kwargs):
        # pylint: disable=arguments-differ
        endpoint = '/'.join(self.REST_BASE)
        if self.ENDPOINT_BASE:
            endpoint += '/' + self.ENDPOINT_BASE
        if url:
            endpoint += '/' + url

        # don't care about the original url at all,
        # don't even want to supply it
        url = '/'.join([self.API_BASE, endpoint])
        if params is None:
            params = {}
        params.update({
            'part': 'snippet',
            'key': self.AUTH.get('key', '')
            })
        return super().request(method, url, params=params, **kwargs)

    def search(self, query, params=None, **kwargs):
        """
        Searches youtube for ANY kinds that match these values
        """
        endpoint = 'search'
        if params is None:
            params = {}
        params.update({
            'q': query
            })
        return self.get(url=endpoint, params=params, **kwargs)

    # getting rid of the requirement to supply the url
    def get(self, url='', **kwargs):
        return super().get(url, **kwargs)

    def put(self, url='', data=None, **kwargs):
        return super().put(url, data=data, **kwargs)

    def post(self, url='', data=None, json=None, **kwargs):
        return super().post(url, data=data, json=json, **kwargs)

    def delete(self, url='', **kwargs):
        return super().delete(url, **kwargs)
