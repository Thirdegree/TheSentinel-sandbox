"""
Module for youtube channels
"""
from typing import Optional, Dict, Any
from . import youtube

class Channel(youtube.Youtube):
    """
    Representing things rootied at /channels endpoint
    """
    ENDPOINT_BASE = 'channels'
    URL_REGEX = r'(?i)channel\/(.*?)(?:\/|\?|$)'

    def videos(self,
               query: Optional[str] = None,
               limit: Optional[int] = None,
               params: Optional[Dict[str, str]] = None,
               **kwargs: Any):
        """
        Returns any videos in this channel
        """
        if params is None:
            params = {}
        params.update({
            'type': 'video',
            'channelId': self.id,
            'maxResults': params.get('maxResults', limit)
            })
        return self.search(query=query, params=params, **kwargs)
