"""
Base module for youtube related things
"""
from typing import Dict, Any, Optional, cast, NamedTuple, Type, Tuple, Pattern
import re
import requests
from ... import RestBase


class Youtube(RestBase):
    """
    Base class, sets up authentication and url munging
    """
    API_BASE = 'https://www.googleapis.com'
    REST_BASE = ['youtube', 'v3']

    URL_REGEX: Pattern = re.compile(r'')

    AUTH: Dict[str, str]
    AUTH = {}

    @property
    def resp(self) -> requests.Response:
        """
        Lazy getter for youtube Response for given object
        """
        if self._resp is None:
            self._resp = self.get('', params={'id': self.id})
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

    def request(self, method, url, params=None, **kwargs):
        # pylint: disable=arguments-differ
        url = self.format_url(url)
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
