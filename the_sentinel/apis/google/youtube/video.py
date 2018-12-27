"""
Module for youtube videos
"""
import re
from . import youtube
from . import channel

class Video(youtube.Youtube):
    """
    Representing things rootied at /videos endpoint
    """
    ENDPOINT_BASE = 'videos'
    URL_REGEX = re.compile(
                    r'(?:youtu\.be\/|watch\?v=|\/embed\/)(?P<id>.*?)(?:\W|$)'
                    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = None

    @property
    def channel(self):
        """
        Gets a channel object for the video
        """
        if self._channel is None:
            self._channel = channel.Channel(
                                id=self.json['snippet']['channelId']
                                )
        return self._channel
