from . import Channel
import requests

# User is essentially an alias for channels, except the ids don't match as
# nicely so it's a bit of a pain
class User(Channel):
    """
    Class for youtube Users
    """
    URL_REGEX = r'user\/(.*)(?:\?|$|\/)'
    @property
    def resp(self) -> requests.Response:
        if self._resp is None:
            self._resp = self.get(params={'forUsername': self.id})
            self._resp.raise_for_status()
        return self._resp

    @property
    def json(self):
        if self._json is None:
            self._json = next(iter(self.resp.json()['items']))
        return self._json

