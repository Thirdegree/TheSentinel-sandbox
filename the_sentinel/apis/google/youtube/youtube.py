from typing import Dict, Any
import requests


class Youtube(requests.Session):
    API_BASE='https://www.googleapis.com'
    REST_BASE=['youtube', 'v3']
    ENDPOINT_BASE=''
    AUTH = {}

    def __init__(self, key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if key:
            self.AUTH['key'] = key
        self._json: Optional[Dict[Any, Any]] = None
        self._resp: Optional[requests.Response] = None

    @property
    def resp(self) -> requests.Response:
        if self._resp is None:
            self._resp = self.get(params={'id': self.id})
            self._resp.raise_for_status()
        return self._resp

    @property
    def json(self) -> Dict[Any, Any]:
        return self.resp.json()

    def request(self, method, url='', params=None, **kwargs):
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

    def search(self, query, *args, **kwargs):
        endpoint = 'search'
        params = {
                'q': query
                }
        return self.get(url=endpoint, params=params)

    # getting rid of the requirement to supply the url
    def get(self, url='', **kwargs):
        return super().get(url, **kwargs)
    def put(self, url='', **kwargs):
        return super().put(url, **kwargs)
    def post(self, url='', **kwargs):
        return super().post(url, **kwargs)
    def delete(self, url='', **kwargs):
        return super().delete(url, **kwargs)



class Channel(Youtube):
    ENDPOINT_BASE='channels'
    def __init__(self, channel_id, key=None, *args, **kwargs):
        self.id = channel_id
        super().__init__(key=key, *args, **kwargs)

    def get(self, params=None, **kwargs):
        default_params = {
            'part': 'snippet',
            }

        if params is None:
            params = {}
        default_params.update(params)
        return super().get(params=default_params, **kwargs)


