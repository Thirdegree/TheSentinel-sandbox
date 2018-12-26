"""
Module for youtube playlists
"""
from .youtube import Youtube

class Playlist(Youtube):
    """
    Representing things rootied at /playlists endpoint
    """
    ENDPOINT_BASE = 'playlists'


