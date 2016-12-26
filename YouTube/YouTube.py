from ..objects import MediaProcess, GAPIProcess
from ..helpers import getSentinelLogger


class YouTube(MediaProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['youtube.com', 'youtu.be']
        self.logger.debug('Initiating GAPI Datapull')
        super(YouTube, self).__init__(GAPIProcess, mediaURLs)