"""
Base module for youtube related things
"""
from typing import Dict, Any, Optional, cast, NamedTuple, Type, Tuple
import requests
from lru import LRU # pylint: disable=no-name-in-module

ItemCache = Dict[Tuple[str, Type['Youtube']], 'Youtube']

class Youtube(requests.Session):
    """
    Base class, sets up authentication and url munging
    """
    API_BASE = 'https://www.googleapis.com'
    REST_BASE = ['youtube', 'v3']
    ENDPOINT_BASE = ''

    URL_REGEX = r''

    AUTH: Dict[str, str]
    AUTH = {}

    _CACHE: ItemCache = cast(ItemCache, LRU(128))

    def __new__(cls, id: str = '', **kwargs):
        """
        This allows us to cache multiple requests for the same object
        """
        if (id, cls) not in cls._CACHE:
            instance = super(Youtube, cls).__new__(cls)
            instance.__init__(id=id, cached=False, **kwargs)
            cls._CACHE[(id, cls)] = instance

        return cls._CACHE[(id, cls)]

    def __init__(self,
                 id: str = '', # pylint: disable=invalid-name
                 key: Optional[str] = None,
                 resp: Optional[requests.Response] = None,
                 cached: bool = True):
        if cached:
            # we only want to do all this if this is the FIRST time this thing
            # has been created. We set cached to false in __new__ when that is
            # the case. ALL other cases of instanciation should return a cached
            # value
            return
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

    def search(self, query, params=None,
               limit: Optional[int] = None, **kwargs):
        """
        Searches youtube for ANY kinds that match these values
        """
        endpoint = 'search'
        if params is None:
            params = {}
        params.update({
            'q': query,
            'maxResults': params.get('maxResults', limit)
            })
        resp = self.get(url=endpoint, params=params, **kwargs)
        ret = []
        for item in resp.json()['items']:
            kind = KIND_MAPPING[item['id']['kind']].kind
            ret.append(kind(id=self._getid(item), resp=resp))
        return ret

    @property
    def title(self):
        """
        Gets a title from an object.
        If used on base Youtube objects, will raise a requests exception
        """
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

    def refresh(self):
        """
        Clears out all caching that has been done on a given object
        """
        self._resp = None
        self._json = None
        self._CACHE.pop((self.id, type(self)))

    def __repr__(self):
        if self.id:
            return f"<{self.__class__.__name__}:{self.id}>"
        return f"<{self.__class__.__name__}>"

    def __str__(self):
        return repr(self)

    def __hash__(self):
        return hash((self.__class__, self.id))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return not self == other


# these need to be at the bottom or neither can import the other
# pylint: disable=wrong-import-position
from . import video
from . import channel
from . import playlist
# pylint: enable=wrong-import-position

class Kind(NamedTuple):
    """
    Convienence type for dealing with getting id from things
    """
    key: str
    kind: Type['Youtube']

KIND_MAPPING = {
    'youtube#video': Kind(key='videoId', kind=video.Video),
    'youtube#channel': Kind(key='channelId', kind=channel.Channel),
    'youtube#playlist': Kind(key='playlistId', kind=playlist.Playlist),
    }
