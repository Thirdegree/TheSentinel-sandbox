from ..objects import MediaProcess, VMOAPIProcess
from ..helpers import getSentinelLogger


class Vimeo(MediaProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['vimeo.com',]
        self.logger.debug('Initializing Vimeo Datapull')
        super(Vimeo, self).__init__(VMOAPIProcess, mediaURLs)
