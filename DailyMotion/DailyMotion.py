from ..objects import MediaProcess, DMAPIProcess
from ..helpers import getSentinelLogger


class DailyMotion(MediaProcess):
    def __init__(self):
    	# Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['dailymotion.com', 'dai.ly']
        self.logger.debug('Initiating DM Datapull')
        super(DailyMotion, self).__init__(DMAPIProcess, mediaURLs)
    