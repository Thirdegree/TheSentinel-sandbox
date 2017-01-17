import praw, re, time, requests, sys
from ..helpers.responses import *
from ..helpers import getSentinelLogger, SlackNotifier
from ..objects import Memcache
from ..ModLogger import ModLogger

class SentinelInstance():
    def __init__(self, oauth, queue, masterClass):
        # full logger setup
        self.logger = getSentinelLogger()

        #create reddit instance here
        self.r = oauth.login()
        #self.r.config.log_requests = 0
        self.me = self.r.user.me()
        self.subsModdedTemp = self.r.user.moderator_subreddits(limit=None)

        self.subsModded = [i for i in self.subsModdedTemp]
        self.subsModdedWrite = [(i, i.subscribers) for i in self.subsModded]
        self.logger.info(u"{} | Modding {} users in {}".format(self.me, self.subCount, [str(x) for x in self.subsModded]))
        self.modMulti = self.r.subreddit('mod')
        self.globalBlacklistSubs = ['YT_Killer','TheSentinelBot']
        self.subextractor = re.compile("r\/(.*)")


        #this is fucking awful. it's just a list of moderators of the above two subs.
        self.globalBlacklistMods = list(set([red for sub in self.globalBlacklistSubs for red in self.r.subreddit(sub).moderator]))
        self.removalQueue = queue
        self.masterClass = masterClass
        self.messageSub = 'Layer7'
        self.cache = Memcache()
        self.subscriberLimit = 20000000
        self.notifier = SlackNotifier()
        self.modlogger = ModLogger(self.r, [str(i) for i in self.subsModded])

        self.blacklisted_subs = ['pokemongo']

    def __str__(self):
        return self.me.name


    def clearQueue(self):
        processed = []
        while not self.removalQueue.empty():
            thing = self.removalQueue.get()
            things = self.r.info([thing.fullname])
            for thing in things:
                message = self.masterClass.getInfo(thing)

                if isinstance(thing, praw.models.Submission):
                    perma = thing.shortlink
                else:
                    perma = "http://reddit.com" + thing.permalink()

                seen = []
                for item in message:
                    item['author'] = str(thing.author)
                    item['subreddit'] = str(thing.subreddit)
                    item['permalink'] = perma
                    if item['media_author'] not in seen and self.masterClass.isBlacklisted(item['subreddit'], item['media_link']) :
                        self.notifier.send_message(str(thing.subreddit), item)
                        self.notifier.send_message('yt_killer', item)
                        seen.append(item['media_author'])

                thing.subreddit.mod.remove(thing) # https://www.reddit.com/r/redditdev/comments/5h2r1c/-/daxk71u/
                processed.append(thing.fullname)
        if processed:
            self.logger.info('{} | Removed items: {}'.format(self.me, processed))

    def canAction(self, thing):
        try:
            if any([str(thing.subreddit).lower() == str(x).lower() for x in self.subsModded]): # stupid workaround for the oauth shit
                self.logger.debug('Thing {} matches subs bot mods'.format(thing.fullname))
                return thing
            return False
        except praw.exceptions.APIException:
            self.logger.debug('PRAW Forbidden Error')
            return False


    def checkInbox(self):
        for message in self.r.inbox.unread(limit=None):
            self.logger.info('{} | Processing Unread Inbox, MailID: {}'.format(self.me, message.name))

            if message.body.startswith('**gadzooks!'):
                self.acceptModInvite(message)
                continue

            message.mark_read()
            if "add to blacklist" in message.subject.lower():
                self.addBlacklist(message)
                continue

            if "remove from blacklist" in message.subject.lower():
                self.removeBlacklist(message)
                continue

            if "You have been removed as a moderator from " in message.body:
                self.logger.info("{} | Removed from subreddit /r/{}".format(self.me, str(message.subreddit)))
                self.masterClass.remove_subreddit(str(message.subreddit))
                self.subsModded = [i for i in self.r.user.moderator_subreddits(limit=None)]
                self.masterClass.writeSubs()
                self.logger.info("{} | Now mods {} users.".format(self.me, self.subCount))
                continue


            if message.subject.strip().lower().startswith("moderator message from"):
                self.logger.debug('Moderator Message, ignoring')
                continue
            # Username Mentions
            if message.subject.strip().lower().startswith("username mention"):
                self.logger.debug('Wonder if this username mention is love-mail or hate-mail. Meh, ignorning')
                continue

            if message.distinguished == 'admin':
                self.r.send_message('/r/' + self.messageSub, 'New Admin Mail: FROM: /u/{} | SUBJECT: {}'.format(message.author.name.encode("ascii", "xmlcharrefreplace"), message.subject.encode("ascii", "xmlcharrefreplace")), "A new Admin mail has come in. \n\n[**Link to message**](https://www.reddit.com/message/messages/{}) \n\n---\n\n{}".format(message.id, message.body.encode("ascii", "xmlcharrefreplace")))
                self.logger.debug('Oh hey! We got Admin Mail!')

    """def checkModmail(self):
        toAdd = []
        for message in self.sub.modMulti.unread(limit=None):
            if message.fullname in self.done:
                continue
            toAdd.append(message)
            self.logger.debug('{} | Processing Mod Mail, MailID: {}'.format(self.me, message.name))
            if "add to global blacklist" in message.subject.lower():
                if message.author in self.globalBlacklistMods and message.subreddit.display_name in self.globalBlacklistSubs:
                    try:
                        self.masterClass.addBlacklist(message, message.subreddit, isGlobal=True)
                        message.reply("Channel added to Blacklist.")
                        message.mark_read()
                    except requests.exceptions.HTTPError:
                        continue
                        #message.reply("Channel add failed. If the channel you requested was from Soundcloud, this is a known bug by Soundcloud.")
                    except KeyError:
                        continue
                        #message.reply("Channel add failed. If the channel you requested was from Soundcloud, this is a known bug by Soundcloud.")

        self.masterClass.markProcessed(toAdd)"""

    def checkContent(self):
        toAdd = []
        self.logger.info('{} | Getting Content'.format(self.me))
        self.logger.debug('{} | Getting Reddit New'.format(self.me))
        for post in self.modMulti.new(limit=200):
            if not post.fullname in self.done:# and not self.masterClass.isProcessed(post):
                self.logger.debug("{} | Added Post to toAdd - {}".format(self.me, post.fullname))
                toAdd.append(post)
                self.done.add(post.fullname)
        self.logger.info('{} | Done w/ GetNew | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))

        self.logger.debug('{} | Getting Reddit Comments'.format(self.me))
        for comment in self.modMulti.comments(limit=300):
            if not comment.fullname in self.done:# and not self.masterClass.isProcessed(comment):
                self.logger.debug("{} | Added comment to toAdd - {}".format(self.me, comment.fullname))
                toAdd.append(comment)
                self.done.add(comment.fullname)
        self.logger.info('{} | Done w/ GetComments | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))

        self.logger.debug('{} | Getting Reddit Edited'.format(self.me))
        for edit in self.modMulti.mod.edited(limit=200):
            if not edit.fullname in self.done:# and not self.masterClass.isProcessed(edit):
                self.logger.debug("{} | Added edit to toAdd - {}".format(self.me, edit.fullname))
                toAdd.append(edit)
                self.done.add(edit.fullname)
        self.logger.info('{} | Done w/ GetEdited | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))

        self.logger.debug('{} | Getting Reddit Spam'.format(self.me))
        for spam in self.modMulti.mod.spam(limit=200):
            if not spam.fullname in self.done:# and not self.masterClass.isProcessed(spam):
                self.logger.debug("{} | Added spam to toAdd - {}".format(self.me, spam.fullname))                
                toAdd.append(spam)
                self.done.add(spam.fullname)
        self.logger.info('{} | Done w/ GetSpam | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))
        
        if toAdd:
            self.logger.debug("Adding {} items to cache".format(len(toAdd)))
            for i in toAdd:
                self.logger.debug("Adding {} to cache".format(i.fullname))
                self.cache.add(i)
        self.masterClass.markProcessed(toAdd)

    def addBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))
            elif thing.author in mods:
                self.logger.info(u'{} | Add To Blacklist request from: {}'.format(self.me, thing.author))
                try:
                    if self.masterClass.addBlacklist(thing, subreddit):
                        thing.reply("Channel added to the blacklist")
                    else:
                        thing.reply("Channel add failed.")
                except requests.exceptions.HTTPError:
                    self.logger.info(u'{} | Add to blacklist failed - HTTPError')
                    thing.reply("Channel add failed. If the channel you requested was from Soundcloud, this is a known bug by Soundcloud.")

        except praw.exceptions.APIException:
            self.logger.warning(u'PRAW Forbidden Error - Incorrect Sentinel Instance Messaged')
            thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))

    def removeBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))
            elif thing.author in mods:
                self.logger.info(u'{} | Remove From Blacklist request from: {}'.format(self.me, thing.author))
                try:
                    self.masterClass.removeBlacklist(thing, subreddit)
                    thing.reply("Channel removed from the blacklist")
                except requests.exceptions.HTTPError:
                    pass
        except praw.exceptions.APIException:
            self.logger.warning('PRAW Forbidden Error - Incorrect Sentinel Instance Messaged')
            thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))

    @property
    def subCount(self):
        return sum([i.subscribers for i in self.subsModded])

    def acceptModInvite(self, message):
        try:
            if self.masterClass.getBot(message.subreddit):
                message.reply("You already have an active Sentinel account. We appreciate the enthusiasm, though!\n\nIf you recently removed an old Sentinel account, please wait ~5 minutes to add a new one to allow for processing time.")
                message.mark_read()
                self.logger.info(u'Bot already mods /r/{}'.format(message.subreddit))
            elif message.subreddit.lower() in self.blacklisted_subs:
                message.reply("No.")
                message.mark_read()
            elif self.subCount + self.r.subreddit(message.subreddit).subscribers <= self.subscriberLimit:
                self.r.subreddit(message.subreddit).mod.accept_invite()
                message.mark_read()
                self.subsModded.append(self.r.subreddit(message.subreddit))
                self.logger.info(u'{} | Accepted mod invite for /r/{}'.format(self.me, message.subreddit))
                self.logger.info(u'{} | Now mods {} users'.format(self.me, self.subCount))
                
                self.masterClass.add_subreddit(str(message.subreddit), str(self.me), self.r.subreddit(message.subreddit).subscribers)
                self.masterClass.writeSubs()
            else:
                self.logger.info(u'{} | Bot at capacity'.format(self.me))
                message.reply(CurrentInstanceOverloaded)
                self.r.subreddit(message.subreddit).moderator.leave()

                message.mark_read()
        except praw.exceptions.APIException:
            self.logger.error(u'API Error Accepting Mod Invite for sub {}'.format(message.subreddit))
            #message.mark_read()
        except praw.exceptions.ClientException:
            self.logger.error(u'Client Error Accepting Mod Invite for sub {}'.format(message.subreddit))
            #message.mark_read()
        except:
            self.logger.error(u'General Error Accepting Mod Invite')
            message.mark_read()

    def getCorrectBot(self, subreddit):
        return self.masterClass.getBot(subreddit)

    def start(self):
        while not self.masterClass.killThreads:
            #self.logger.debug('{} | Cycling..'.format(self.me.name))
            try:
                time.sleep(10)
                self.done = set(self.masterClass.isProcessed(self.subsModded))
                #self.modMulti = self.r.subreddit('mod')

                self.checkContent()
                self.logger.info('{} | Done w/ checkContent | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))
                self.checkInbox()
                self.logger.info('{} | Done w/ checkInbox | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))
                #self.checkModmail()
                self.clearQueue()
                self.logger.info('{} | Done w/ clearQueue | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))
                self.modlogger.log()
                self.logger.info('{} | Done w/ modlogger.log | Ratelimits: Remaining: {}. Used: {}'.format(self.me, self.r._core._rate_limiter.remaining, self.r._core._rate_limiter.used))
                if self.masterClass.killThreads:
                    self.logger.info("{} | Acknowledging killThread".format(self.me))
            except praw.exceptions.APIException:
                self.logger.error('Reddit HTTP Connection Error')
            except Exception as e:
                self.logger.error(u"{} | General Error - {}: Sleeping 30".format(self.me, e))
                time.sleep(30)

    
