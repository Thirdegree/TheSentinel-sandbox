from ..objects import MediaProcess, VidmeAPIProcess
from ..helpers import getSentinelLogger


class Vidme(MediaProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['vid.me',]
        self.logger.debug('Initializing Vidme Datapull')
        super(Vimeo, self).__init__(VidmeAPIProcess, mediaURLs)
