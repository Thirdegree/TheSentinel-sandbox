"""
Module for youtube playlists
"""
from . import youtube

class Playlist(youtube.Youtube):
    """
    Representing things rootied at /playlists endpoint
    """
    ENDPOINT_BASE = 'playlists'
