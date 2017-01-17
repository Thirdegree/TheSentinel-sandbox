from ..objects import MediaProcess, TwitchAPIProcess
from ..helpers import getSentinelLogger


class Twitch(MediaProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        mediaURLs = ['twitch.tv']
        self.logger.debug('Initiating TwitchAPI Datapull')
        super(Twitch, self).__init__(TwitchAPIProcess, mediaURLs)