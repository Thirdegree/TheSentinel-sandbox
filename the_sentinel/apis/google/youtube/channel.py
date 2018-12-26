"""
Module for youtube channels
"""
from .youtube import Youtube

class Channel(Youtube):
    """
    Representing things rootied at /channels endpoint
    """
    ENDPOINT_BASE = 'channels'
    def __init__(self, channel_id: str, *args, key=None, **kwargs):
        super().__init__(key=key, *args, **kwargs)
        self.id = channel_id #pylint: disable=invalid-name

    def get(self, params=None, **kwargs): # pylint: disable=arguments-differ
        default_params = {
            'part': 'snippet',
            }

        if params is None:
            params = {}
        default_params.update(params)
        return super().get(params=default_params, **kwargs)
