from .youtube import Youtube

class Video(Youtube):
    """
    Representing things rootied at /videos endpoint
    """
    ENDPOINT_BASE = 'videos'
