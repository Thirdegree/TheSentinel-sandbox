"""
Base module for youtube related things
"""
from typing import Dict, Any, Optional, cast, Type, Tuple, Callable
import requests
from ... import RestBase


class Youtube(RestBase):
    """
    Base class, sets up authentication and url munging
    """
    API_BASE = 'https://www.googleapis.com'
    REST_BASE = ['youtube', 'v3']


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
        try:
            # item is from a search result
            return KIND_MAPPING[item['kind']](item)[0]
        except (KeyError, TypeError):
            item_id = item['id']
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

    def search(self, endpoint='', query='', params=None,
               limit: Optional[int] = None, **kwargs):
        """
        Searches youtube for ANY kinds that match these values
        """
        endpoint = endpoint or 'search'
        if params is None:
            params = {}
        params.update({
            'q': query,
            'maxResults': params.get('maxResults', limit)
            })
        resp = self.get(url=endpoint, params=params, **kwargs)
        ret = []
        for item in resp.json()['items']:
            try:
                item_id, kind = KIND_MAPPING[item['kind']](item)
            except KeyError:
                from pprint import pprint
                pprint(item)
                raise
            item = kind(id=item_id, resp=resp)
            ret.append(item)
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

KIND_MAPPING: Dict[str, Callable[[Dict[str, Any]], Tuple[str, Type[Youtube]]]]
KIND_MAPPING = {
    # ALL KINDS HERE MUST BE THE resp.json()['items'][i]['kind']
    # functions should expect resp.json()['items'][i] and return
    # (id, Kind)
    'youtube#video': lambda item: (item['id']['videoId'],
                                   video.Video),
    'youtube#channel': lambda item: (item['id']['channelId'],
                                     channel.Channel),
    'youtube#playlist': lambda item: (item['id']['playlistId'],
                                      playlist.Playlist),
    # pylint: disable=unnecessary-lambda
    'youtube#searchResult': lambda item:\
                                KIND_MAPPING[item['id']['kind']](item),
    'youtube#playlistItem': lambda item: (item['snippet']\
                                              ['resourceId']['videoId'],
                                          video.Video),

    }
