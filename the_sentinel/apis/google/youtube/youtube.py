"""
Base module for youtube related things
"""
from typing import Dict, Any, Optional, cast, NamedTuple
import requests

class Kind(NamedTuple):
    key: str
    kind: 'Youtube'



class Youtube(requests.Session):
    """
    Base class, sets up authentication and url munging
    """
    API_BASE = 'https://www.googleapis.com'
    REST_BASE = ['youtube', 'v3']
    ENDPOINT_BASE = ''
    AUTH: Dict[str, str]
    AUTH = {}

    def __init__(self, *args,
                 id: str = '',
                 key: Optional[str] = None,
                 resp: Optional[requests.Response] = None,
                 **kwargs: Any):
        #pylint: disable=invalid-name
        super().__init__()
        self.id = id # pylint: disable=invalid-name
        if key:
            self.AUTH['key'] = key
        self._json: Optional[Any] = None
        self._resp: Optional[requests.Response] = resp

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
        # these apis ALWAYS return a list even if it's explicitly a single
        # thing
        if self._json is None:
            self._json = next(
                filter(
                    lambda x: self._getid(x) == self.id,
                    self.resp.json()['items']
                    )
                )
        return self._json

    @staticmethod
    def _getid(item: Dict[str, Any]) -> str:
        item_id = item['id']
        if isinstance(item_id, dict):
            return cast(str, item_id[KIND_MAPPING[item_id['kind']].key])
        return cast(str, item_id)

    def request(self, method, url='', params=None, **kwargs):
        # pylint: disable=arguments-differ
        endpoint = '/'.join(self.REST_BASE)
        if url:
            endpoint += '/' + url
        elif self.ENDPOINT_BASE:
            endpoint += '/' + self.ENDPOINT_BASE

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
        resp = self.get(url=endpoint, params=params, **kwargs)
        ret = []
        for item in resp.json()['items']:
            kind = KIND_MAPPING[item['id']['kind']].kind
            ret.append(kind(id=self._getid(item), resp=resp))
        return ret

    @property
    def title(self):
        return self.json['snippet']['title']

    # getting rid of the requirement to supply the url
    def get(self, url='', **kwargs):
        return super().get(url, **kwargs)

    def put(self, url='', data=None, **kwargs):
        return super().put(url, data=data, **kwargs)

    def post(self, url='', data=None, json=None, **kwargs):
        return super().post(url, data=data, json=json, **kwargs)

    def delete(self, url='', **kwargs):
        return super().delete(url, **kwargs)


# these need to be at the bottom or neither can import the other
from . import video
from . import channel
from . import playlist
KIND_MAPPING = {
    'youtube#video': Kind(key='videoId', kind=video.Video),
    'youtube#channel': Kind(key='channelId', kind=channel.Channel),
    'youtube#playlist': Kind(key='playlistId', kind=playlist.Playlist),
    }
