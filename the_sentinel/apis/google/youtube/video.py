"""
Module for youtube videos
"""
from . import youtube
from . import channel

class Video(youtube.Youtube):
    """
    Representing things rootied at /videos endpoint
    """
    ENDPOINT_BASE = 'videos'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._channel = None

    @property
    def channel(self):
        if self._channel is None:
            self._channel= channel.Channel(
                                id=self.json['snippet']['channelId']
                                )
        return self._channel

