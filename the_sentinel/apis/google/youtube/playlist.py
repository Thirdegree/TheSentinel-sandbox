"""
Module for youtube playlists
"""
from typing import Optional, Dict, Any
import re
from . import youtube

class Playlist(youtube.Youtube):
    """
    Representing things rootied at /playlists endpoint
    """
    ENDPOINT_BASE = 'playlists'
    URL_REGEX = re.compile(
        r'(?<!watch).*?list=(?P<id>(?!videoseries).*?)(?:#|\/|\?|\&|$)'
        )

    def videos(self,
               query: Optional[str] = None,
               params: Optional[Dict[str, str]] = None,
               **kwargs: Any):
        """
        Returns any videos in this channel
        """
        if params is None:
            params = {}
        params.update({
            'type': 'video',
            'playlistId': self.id,
            })
        return self.search(endpoint='playlistItems', query=query, params=params, **kwargs)
