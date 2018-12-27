"""
Module for gathering all the various api endpoints I need to talk to to find
spam
"""
from typing import List, Pattern, Dict, Tuple, Type, cast, Optional, Any
from lru import LRU # pylint: disable=no-name-in-module
import re
import requests

ItemCache = Dict[Tuple[str, Type['RestBase']], 'RestBase']

class RestBase(requests.Session):
    API_BASE = ''
    REST_BASE: List[str] = []
    ENDPOINT_BASE = ''

    URL_REGEX: Pattern = re.compile(r'')

    AUTH: Dict[str, str]
    AUTH = {}

    _CACHE: ItemCache = cast(ItemCache, LRU(128))

    def __new__(cls, id: str = '', **kwargs):
        """
        This allows us to cache multiple requests for the same object
        """
        if (id, cls) not in cls._CACHE:
            instance = super().__new__(cls)
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
        raise NotImplementedError

    @property
    def json(self) -> Any:
        if self._json is None:
            self._json = self.resp.json()
        return self._json

    def format_url(self, url):

        endpoint = '/'.join(self.REST_BASE)
        if url:
            endpoint += '/' + url
        elif self.ENDPOINT_BASE:
            endpoint += '/' + self.ENDPOINT_BASE

        # don't care about the original url at all,
        # don't even want to supply it
        url = '/'.join([self.API_BASE, endpoint])
        return url

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
