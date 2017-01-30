from ..objects import MediaProcess, TwitterAPIProcess
from ..helpers import getSentinelLogger


class Twitter(MediaProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['twitter.com']
        self.logger.debug('Initiating TwitterAPI Datapull')
        super(Twitter, self).__init__(TwitterAPIProcess, mediaURLs)