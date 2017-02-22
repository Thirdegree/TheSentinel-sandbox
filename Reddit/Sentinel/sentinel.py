import re
from ...helpers.responses import *
from ...helpers import getSentinelLogger
import praw, re, time, requests, sys, threading


class Sentinel(object):
    def __init__(self, r, subs, agent, masterClass):
        self.r = r
        self.me = self.r.user.me()
        self.masterClass = masterClass
        self.agent = agent
        self.subs = subs
        self.subextractor = re.compile(r"r/(.*)")
        self.logger = getSentinelLogger()


    def addBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.\n\nPlease try using [our site](http://beta.layer7.solutions/sentinel/edit/) if you are still having issues. Thanks.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.agent.getCorrectBot(subreddit)))
            elif thing.author in mods:
                self.logger.info(u'{} | Add To Blacklist request from: {}'.format(self.me, thing.author))
                try:
                    bl = self.masterClass.addBlacklist(thing, subreddit)
                    if bl:
                        thing.reply("Channel(s) added to the blacklist: {}".format(bl))
                    else:
                        thing.reply("Channel add failed.")
                except requests.exceptions.HTTPError:
                    self.logger.info(u'{} | Add to blacklist failed - HTTPError')
                    thing.reply("Channel add failed. If the channel you requested was from Soundcloud, this is a known bug by Soundcloud.")

        except praw.exceptions.APIException:
            self.logger.warning(u'PRAW Forbidden Error - Incorrect Sentinel Instance Messaged')
            thing.reply(ForbiddenResponse.format(self.agent.getCorrectBot(subreddit)))

    def removeBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.\n\nPlease try using [our site](http://beta.layer7.solutions/sentinel/edit/) if you are still having issues. Thanks.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.agent.getCorrectBot(subreddit)))
            elif thing.author in mods:
                self.logger.info(u'{} | Remove From Blacklist request from: {}'.format(self.me, thing.author))
                try:
                    bl = self.masterClass.removeBlacklist(thing, subreddit)
                    if bl:
                        thing.reply("Channel(s) removed from the blacklist: {}".format(bl))
                except requests.exceptions.HTTPError:
                    pass
        except praw.exceptions.APIException:
            self.logger.warning('PRAW Forbidden Error - Incorrect Sentinel Instance Messaged')
            thing.reply(ForbiddenResponse.format(self.agent.getCorrectBot(subreddit)))