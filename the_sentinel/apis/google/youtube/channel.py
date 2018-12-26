"""
Module for youtube channels
"""
from .youtube import Youtube

class Channel(Youtube):
    """
    Representing things rootied at /channels endpoint
    """
    ENDPOINT_BASE = 'channels'

