import logging, logging.config
import requests, json
import os
from ...const import __version__, __app_name__

LoggerConfigLocation = 'TheSentinel\helpers\SentinelLogger\_Logger_Config.json'
with open(LoggerConfigLocation, 'rt') as f:
    config = json.load(f)

# Replaces the filename with one specific to each bot
config['handlers']['rotateFileHandler']['filename'] = "logs\\_BotName__Logs.log".replace('_BotName_', __app_name__)
config['handlers']['rotateFileHandler_debug']['filename'] = "logs\\_BotName__Logs_Debug.log".replace('_BotName_', __app_name__)

logging.config.dictConfig(config)
logger = logging.getLogger("root")

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """
    def filter(self, record):

        record.BotName = __app_name__
        record.APP_VERS = __version__
        return True

def getSentinelLogger():
    
    return SentinelLogger(logger)


class SentinelLogger(object):
    def __init__(self, logger):

        cf = ContextFilter()
        logger.addFilter(cf)

        self.logger = logger

    def debug(self, *args):
        self.logger.debug(*args)

    def info(self, *args):
        self.logger.info(*args)

    def warning(self, *args):
        self.logger.warning(*args)

    def error(self, *args):
        self.logger.error(*args, exc_info=True)

    def critical(self, *args):
        self.logger.critical(*args, exc_info=True)
