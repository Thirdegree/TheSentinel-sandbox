from datapulls import Datapull
import time
import requests
import oAuth
import praw
import re
import sys

import logging, logging.config



class CallResponse():
    def __init__(self):
        self.r = oAuth.login()
        self.matchstring = "\[\[(.+?)\]\]" #[[searchquery]]
        self.lastquery = time.time()
        self.queryCount = 0
        self.subreddit = self.r.get_subreddit("DestinyTheGame")
        self.mods = self.subreddit.get_moderators()

        # ~~~~~~~~~~ LOGGER SETTINGS ~~~~~~~~~~ #

        # Setup logging
        LoggerConfigLocation = 'C:\Users\Administrator\Google Drive\VPS_Svr_Sync\RedditBots\_Logger_Config.ini'
        logging.config.fileConfig(LoggerConfigLocation, defaults={'BotName': BotName, 'APP_VERS': APP_VERS})
        self.ExtraParameters = {'BotName': BotName, 'APP_VERS': APP_VERS}
        self.logger = logging.LoggerAdapter(logging.getLogger(BotName+' v'+APP_VERS), extra=ExtraParameters)
        # ~~~~~~~~~~ LOGGER SETTINGS ~~~~~~~~~~ #

    def get_info(self, query, byMod):
        self.ratelimit(byMod)
        self.logger.debug("Getting info for %s"%query, extra = self.ExtraParameters)
        req = requests.get("http://db.destinytracker.com/api/finder?q=" + query)
        if req.status_code == 200:
            return Datapull(requests.get("http://db.destinytracker.com/api/finder?q=" + query).json())
        else:
            self.logger.debug("Bad response - sleeping 30", extra=self.ExtraParameters)
            time.sleep(30)
            return None

    def ratelimit(self, byMod=False):
        if byMod:
            return
        if (self.lastquery - (time.time())) > 1:
            self.lastquery = time.time()
            self.queryCount = 1
        elif self.queryCount < 4:
            self.queryCount += 1
        else:
            while self.lastquery + 1 > (time.time()):
                continue
            self.lastquery = time.time()
            self.queryCount = 1

    def compile_response(self, responses): #responses is a list of dicts
        header = "Name | Description\n----|-----------"
        lines = header
        for i in responses:
            if not i:
                continue
            name = "[{}]({})".format(i['Name'], i['Icon'])
            lines += "\n" + name + " | " + i['Description']
        return lines

    def get_all_asks(self, body, byMod=False):
        asks = []
        for q in re.findall(self.matchstring, body):
            asks.append(self.get_info(q, byMod))
        return asks

    def action(self):
        for comment in praw.helpers.comment_stream(self.subreddit, limit=None):
            if comment.author in self.mods:
                items = self.get_all_asks(comment.body, byMod=True)
            else:
                items = self.get_all_asks(comment.body)
            if any(items):
                self.logger.info("Replying to comment by %s"%str(comment.author), extra=self.ExtraParameters)
                response = self.compile_response(items)
                comment.reply(response)



def main(responder):
    try:
        responder.action()
    except UnicodeEncodeError:
        responder.logger.warning("Caught UnicodeEncodeError", extra=responder.ExtraParameters)
 
    except KeyboardInterrupt:
        responder.logger.warning('Caught KeyboardInterrupt', extra=responder.ExtraParameters)
        sys.exit()

    except praw.errors.HTTPException:
        responder.logger.warning('Reddit HTTP Error. Pausing 180 seconds.', exc_info=True, extra=responder.ExtraParameters)
        time.sleep(180)

    except requests.ConnectionError:
        responder.logger.warning('Connection / Timeout error. Pausing 180 seconds', exc_info=True, extra=responder.ExtraParameters)
        time.sleep(180)

    except requests.exceptions.ReadTimeout:
        responder.logger.warning('Connection error. Pausing 180 seconds', exc_info=True, extra=responder.ExtraParameters)
        time.sleep(180)

    except Exception:
        responder.logger.critical('General Exception. Exiting out.', extra=responder.ExtraParameters)
        sys.exit()

if __name__ == '__main__':
    responder = CallResponse()
    while True:
        main(responder)
