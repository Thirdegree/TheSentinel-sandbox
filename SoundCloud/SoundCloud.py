from ..objects import MediaProcess, SCAPIProcess
from ..helpers import getSentinelLogger

class SoundCloud(MediaProcess):
    def __init__(self):
    	# Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['soundcloud.com']
        self.logger.debug('Initializing SoundCloud API Datapull')
        super(SoundCloud, self).__init__(SCAPIProcess, mediaURLs)
