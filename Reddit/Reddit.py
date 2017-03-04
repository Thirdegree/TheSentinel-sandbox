import praw
import json, jsonpickle
import os, re, sys, time, requests, threading, configparser
from datetime import datetime
from collections import deque
from ..helpers.responses import *
from ..helpers import getSentinelLogger, SlackNotifier, ShadowbanDatabase
from ..ModLogger import ModLogger
from ..ModmailArchiver import ModmailArchiver
from ..exceptions import TooFrequent
from ..RabbitMQ import Rabbit_Producer
import prawcore.exceptions


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
        self.subscriberLimit = 20000000
        self.notifier = SlackNotifier()
        self.modlogger = ModLogger(self.r, [str(i) for i in self.subsModded])
        self.modmailArchiver = ModmailArchiver(self.r, [str(i) for i in self.subsModded])
        self.edited_done = deque()
        self.shadowban_db = ShadowbanDatabase()

        self.can_global_action = [self.r.redditor('thirdegree'), self.r.redditor('d0cr3d')]

        self.blacklisted_subs = ['pokemongo']

        self.load_config()
        self.SentinelProducer = Rabbit_Producer(exchange=self.ex_SentinelExchange, routing_key=self.rk_Sentinel_ToProcess, QueueName=self.rk_Sentinel_ToProcess)
        

    def __str__(self):
        return self.me.name

    def load_config(self):
        Config = configparser.ConfigParser()
        mydir = os.path.dirname(os.path.abspath(__file__))
        Config.read(os.path.join(mydir, "..", "global_config.ini"))

        self.ex_SentinelExchange    = Config.get('RabbitMQ', 'ex_SentinelExchange')
        self.rk_Sentinel_ToProcess  = Config.get('RabbitMQ', 'rk_Sentinel_ToProcess')
        #self.rk_Sentinel_Results    = Config.get('RabbitMQ', 'rk_Sentinel_AnalysisResults')
        #self.rk_Dirtbag_ToProcess    = Config.get('RabbitMQ', 'rk_Dirtbag_ToProcess')

    def messageSubreddits(self, title, message):
        for sub in self.subsModded:
            sub.message(title, message)
        self.logger.info("{} | Mod Alerts sent".format(self.me))
        return True

    def globalMessage(self, message):
        if message.author not in self.can_global_action:
            message.reply("You do not have the permissions to do this.")
            raise KeyError
        matchstring = r"(.*)\n\n---\n\n(.*)"
        match = re.match(matchstring, message.body)
        if not match:
            return False
        return self.masterClass.messageSubreddits(match.group(1), match.group(2))



    def clearQueue(self):
        processed = []
        while not self.removalQueue.empty():
            data = self.removalQueue.get()

            if isinstance(data, dict):
                # Data came from internal ToProcess queue
                try:
                    things = self.r.info([data['thing_id']])
                    self.logger.info('Data came from internal ToProcess: {}'.format(data['thing_id']))
                # Data came from Dirtbag
                except KeyError:
                    things = self.r.info([data['ThingID']])
                    self.logger.info('Data came from Dirtbag: {}'.format(data['ThingID']))aise e
            # Else, is a thing object
            else:
                things = self.r.info([data.fullname])
                
            for thing in things:
                try:
                    message = self.masterClass.getInfo(thing)
                except KeyError:
                    message = [{
                        'media_author': None,
                        'media_link': None,
                        'media_channel_id': None,
                        'media_platform':None,
                    }]

                if isinstance(thing, praw.models.Submission):
                    perma = thing.shortlink
                else:
                    perma = "http://reddit.com" + thing.permalink()

                seen = []
                for item in message:
                    item['author'] = str(thing.author)
                    item['Subreddit'] = str(thing.subreddit)
                    item['permalink'] = perma
                    if item['media_author'] not in seen and item['media_author']:
                        self.notifier.send_message(str(thing.subreddit), item)
                        self.notifier.send_message('yt_killer', item)
                        seen.append(item['media_author'])

                thing.subreddit.mod.remove() # https://www.reddit.com/r/redditdev/comments/5h2r1c/-/daxk71u/
                self.masterClass.markActioned(thing, type_of='tsb')
                processed.append(thing.fullname)
        if processed:
            self.logger.info('{} | Removed items: {}'.format(self.me, processed))

    def get_permissions(self, mod_name, subreddit): #both strings
        perms = list(self.r.subreddit(subreddit).moderator())
        for mod in perms:
            if str(mod) == mod_name:
                self.logger.debug("{} | Moderator {} perimissions {}".format(self.me, mod, mod.mod_permissions))
                return mod.mod_permissions


    def canAction(self, thing, subreddit=None):
        try:
            if not thing:
                if any([subreddit.lower() == str(x).lower() for x in self.subsModded]): # stupid workaround for the oauth shit
                    self.logger.debug('Subreddit {} matches subs bot mods'.format(subreddit))
                    return True
                return False
            # Dict
            if any([str(thing['Subreddit'.lower()]).lower() == str(x).lower() for x in self.subsModded]): # stupid workaround for the oauth shit
                self.logger.debug('Thing {} matches subs bot mods'.format(thing['ThingID']))
                return thing
            return False
        except prawcore.exceptions.Forbidden:
            self.logger.debug('PRAW Forbidden Error')
            return False
        except IndexError:
            return False

    def forceModlogHistory(self, body, author):
        matchstring = "(?:\/?r\/(\w+)|(all))"
        match = re.findall(matchstring, body, re.I)
        if not match:
            return
        if match[0][1] == 'all':
            subs = [str(i).lower() for i in self.subsModded]
            subs_asked = subs
        else:
            subs_asked = [i[0].lower() for i in match]
            subs = list(set(subs_asked) & set([str(i).lower() for i in self.subsModded]))
        if not subs:
            self.logger.info("{} | Found no matching subs to force modlog history from {}".format(self.me, subs_asked))
            return
        modlogger = ModLogger(self.r, subs)
        threads = []
        for sub in modlogger.subs_intersec: # I'm not sure why, but this works far better than a single modlogger for all the subs to force
            temp = ModLogger(self.r, [sub,])
            threads.append(threading.Thread(target=temp.log, args=(None, author)))
        if modlogger.modLogMulti:
            self.logger.info("{} | Forcing Modlog history for subs: {}".format(self.me, [str(i) for i in modlogger.subs_intersec]))
        for thread in threads:
            thread.start()

    def forceModMailHistory(self, body, author):
        matchstring = "(?:\/?r\/(\w+)|(all))"
        match = re.findall(matchstring, body, re.I)
        if not match:
            return
        if match[0][1] == 'all':
            subs = [str(i).lower() for i in self.subsModded]
            subs_asked = subs
        else:
            subs_asked = [i[0].lower() for i in match]
            subs = list(set(subs_asked) & set([str(i).lower() for i in self.subsModded]))
        if not subs:
            self.logger.info("{} | Found no matching subs to force modmail history from {}".format(self.me, subs_asked))
            return
        modmailArchiver = ModmailArchiver(self.r, subs)
        threads = []
        for sub in modmailArchiver.subs_intersec:
            temp = ModmailArchiver(self.r, [sub,])
            threads.append(threading.Thread(target=temp.log, args=(None, author)))
        if modmailArchiver.modMailMulti:
            self.logger.info("{} | Forcing Mod Mail history for subs: {}".format(self.me, [str(i) for i in modmailArchiver.subs_intersec]))
        for thread in threads:
            thread.start()


    def checkInbox(self):
        for message in self.r.inbox.unread(limit=None):
            self.logger.info('{} | Processing Unread Inbox, MailID: {}'.format(self.me, message.name))
            message.mark_read()

            if message.body.startswith('**gadzooks!'):
                self.acceptModInvite(message)
                self.save_permissions(str(message.subreddit))
                self.forceModlogHistory("r/" + str(message.subreddit), None)
                self.modlogger = ModLogger(self.r, [str(i) for i in self.subsModded])
                self.masterClass.websync.ping_accept(str(message.subreddit))
                continue

            if "force modlog history" in message.subject.lower() and message.author in self.can_global_action:
                self.masterClass.forceModlogHistory(message.body, str(message.author))

            if "force modmail history" in message.subject.lower() and message.author in self.can_global_action:
                self.masterClass.forceModMailHistory(message.body, str(message.author))

            if "alertbroadcast" in message.subject.lower():
                self.logger.info("Sending global modmail alert")
                try:
                    if self.globalMessage(message):
                        message.reply("Message sent")
                    else:
                        message.reply("At least one send failed.")
                except TooFrequent as e:
                    message.reply("You have sent a message too recently. Please wait {} minutes.".format(e.waitTime))
                except KeyError:
                    pass

            if "add to user shadowban" in message.subject.lower():
                try:
                    subreddits, user = self.add_user_shadowban(message)
                    message.reply("User {} shadowbaned for subs {}".format(user, subreddits))
                except TypeError:
                    message.reply("User shadowban failed")

            if "remove from user shadowban" in message.subject.lower():
                try:
                    subreddits, user = self.remove_user_shadowban(message)
                    message.reply("User {} shadowban removed for subs {}".format(user, subreddits))
                except TypeError:
                    message.reply("User shadowban failed")

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
                self.modlogger = ModLogger(self.r, [str(i) for i in self.subsModded])
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

    def checkContent(self):
        toAdd = []
        self.logger.info('{} | Getting Content'.format(self.me))
        self.logger.debug('{} | Getting Reddit New'.format(self.me))
        for post in self.modMulti.new(limit=200):
            if not post.fullname in self.masterClass.done:# and not self.masterClass.isProcessed(post):
                self.logger.debug("{} | Added Post to toAdd - {}".format(self.me, post.fullname))
                toAdd.append(post)
                self.masterClass.done.add(post.fullname)

        self.logger.debug('{} | Getting Reddit Comments'.format(self.me))
        for comment in self.modMulti.comments(limit=300):
            if not comment.fullname in self.masterClass.done:# and not self.masterClass.isProcessed(comment):
                self.logger.debug("{} | Added comment to toAdd - {}".format(self.me, comment.fullname))
                toAdd.append(comment)
                self.masterClass.done.add(comment.fullname)

        self.logger.debug('{} | Getting Reddit Edited'.format(self.me))
        editlist = []
        for edit in self.modMulti.mod.edited(limit=100):
            # stupid why would that make sesnse after edited
            if not edit.fullname in self.edited_done:# and not self.masterClass.isProcessed(edit):
                self.logger.debug("{} | Added edit to toAdd - {}".format(self.me, edit.fullname))
                editlist.append(edit)
                self.edited_done.append(edit.fullname)

        self.logger.debug('{} | Getting Reddit Spam'.format(self.me))
        for spam in self.modMulti.mod.spam(limit=200):
            if not spam.fullname in self.masterClass.done:# and not self.masterClass.isProcessed(spam):
                self.logger.debug("{} | Added spam to toAdd - {}".format(self.me, spam.fullname))                
                toAdd.append(spam)
                self.masterClass.done.add(spam.fullname)
        shadowbanned = []
        if (toAdd + editlist):
            self.logger.debug("Adding {} items to cache".format(len(toAdd+editlist)))
            
            for i in toAdd + editlist:
                self.logger.debug("Adding {} to cache".format(i.fullname))
                if self.user_shadowbanned(i):
                    self.removalQueue.put(i)
                    shadowbanned.append(i)
                else:
                    # Rabbit
                    self.add_to_rabbit(i)
        self.masterClass.markProcessed(toAdd)
        for thing in shadowbanned:
            self.masterClass.markActioned(thing, type_of='botban')

    def add_to_rabbit(self, item, exchange='Sentinel', routing_key='Sentinel_ToProcess'):
        if isinstance(item, dict):
            data = json.dumps(item)
        elif isinstance(item, praw.models.Submission) or isinstance(item, praw.models.Comment):
            data = json.dumps(self.create_dict_item(item))

        try:
            # Make sure we're sending to a Producer that maches the routing key we want
            if self.SentinelProducer.routing_key == routing_key:
                self.SentinelProducer.send(data)
                #self.logger.info('sent data via add_to_rabbit')
            else:
                self.SentinelProducer = Rabbit_Producer(exchange=exchange, routing_key=routing_key, QueueName=self.rk_Sentinel_ToProcess)
                self.SentinelProducer.send(data)
                #self.logger.info('sent data via add_to_rabbit')
        except Exception as e:
            self.logger.error('Unable to send to SentinelProducer, likely dead connection')
            self.SentinelProducer = Rabbit_Producer(exchange=exchange, routing_key=routing_key, QueueName=self.rk_Sentinel_ToProcess)
            self.SentinelProducer.send(data)
            #self.logger.info('sent data via add_to_rabbit')

    def create_dict_item(self, thing):

        if isinstance(thing, praw.models.Submission):
            link = 'http://reddit.com/{}'.format(thing.id)
        elif isinstance(thing, praw.models.Message):
            link = ''
        else:
            link = 'http://reddit.com/comments/{}/-/{}'.format(thing.link_id[3:], thing.id) 

        info_dict = {
            'Subreddit': str(thing.subreddit),
            'thing_id': thing.fullname,
            'author': str(thing.author),
            'Author_Created': str(datetime.utcfromtimestamp(thing.author.created_utc).date()),
            'Author_CommentKarma': thing.author.comment_karma,
            'Author_LinkKarma': thing.author.link_karma,
            'thingcreated_utc': datetime.utcfromtimestamp(thing.created_utc),
            'thingedited_utc': datetime.utcfromtimestamp(thing.edited) if thing.edited else None,
            'parent_thing_id': thing.submission.fullname if type(thing) == praw.models.Comment else None,
            'permalink': link,
            'media_author': '',
            'media_channel_id': '',
            'media_platform': '',
            'media_link': '',
            'title': thing.title if type(thing) == praw.models.Submission else None,
            'url': thing.url if type(thing) == praw.models.Submission else link,
            'flair_class': thing.link_flair_css_class if type(thing) == praw.models.Submission else None,
            'flair_text': thing.link_flair_text if type(thing) == praw.models.Submission else None,
            'body': (thing.body if type(thing) != praw.models.Submission else thing.selftext),
            }
        return info_dict

    def user_shadowbanned(self, thing):
        if not str(thing.subreddit) in self.shadowbans:
            return False
        if str(thing.author).lower() in self.shadowbans[str(thing.subreddit)]:
            return True
        return False

    def add_user_shadowban(self, thing):
        
        try:
            regex_subreddits = "r\/(\w*)"
            regex_username = "u\/(\w*)"
            subs = re.findall(regex_subreddits, thing.body)
            user = re.search(regex_username, thing.subject)
            self.logger.info('{} | Processessing add user shadowban {} for subs {}'.format(self.me, user.group(1), subs))
        except AttributeError:
            return False
        if (not user) or (not subs):
            return False

        ok_subs = []
        for sub in subs:
            try:
                if thing.author in self.r.subreddit(sub).moderator():
                    ok_subs.append(sub)
            except prawcore.exceptions.Forbidden:
                pass
        args = {
            'subreddits': ok_subs,
            'username': user.group(1),
            'bannedby': str(thing.author),
            'bannedon': datetime.utcfromtimestamp(thing.created_utc),
        }

        if args['subreddits'] and self.shadowban_db.add_shadowban(args):
            return (args['subreddits'], args['username'])
        return False

    def remove_user_shadowban(self, thing):

        regex_subreddits = "r/(\w*)"
        regex_username = "u/(\w*)"
        subs = re.findall(regex_subreddits, thing.body)
        user = re.search(regex_username, thing.subject)
        if (not user) or (not subs):
            return False
        ok_subs = []
        for sub in subs:
            try:
                if thing.author in self.r.subreddit(sub).moderator():
                    ok_subs.append(sub)
            except prawcore.exceptions.Forbidden:
                pass
        args = {
            'subreddits': ok_subs,
            'username': user.group(1),
            'bannedby': str(thing.author),
            'bannedon': datetime.utcfromtimestamp(thing.created_utc),
        }
        if args['subreddits'] and self.shadowban_db.remove_shadowban(args):
            return (args['subreddits'], args['username'])
        return False

    def addBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.\n\nPlease try using [our site](http://beta.layer7.solutions/sentinel/edit/) if you are still having issues. Thanks.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator()]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))
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
            thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))

    def removeBlacklist(self, thing):
        sub_string = re.search(self.subextractor, thing.subject)
        if not sub_string:
            thing.reply("I'm sorry, your message appears to be missing a subreddit specification.\n\nPlease try using [our site](http://beta.layer7.solutions/sentinel/edit/) if you are still having issues. Thanks.")
        subreddit = self.r.subreddit(sub_string.group(1))

        try:
            mods = [i for i in subreddit.moderator()]

            if self.me not in mods:
                thing.reply(ForbiddenResponse.format(self.getCorrectBot(subreddit)))
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
            elif message.subreddit.display_name.lower() in self.blacklisted_subs:
                message.reply("No.")
                message.mark_read()
            elif self.subCount + message.subreddit.subscribers <= self.subscriberLimit:
                message.subreddit.mod.accept_invite()
                message.mark_read()
                self.subsModded.append(message.subreddit)
                self.logger.info(u'{} | Accepted mod invite for /r/{}'.format(self.me, message.subreddit))
                self.logger.info(u'{} | Now mods {} users'.format(self.me, self.subCount))
                
                self.masterClass.add_subreddit(str(message.subreddit), str(self.me), message.subreddit.subscribers)
                self.masterClass.writeSubs()
            else:
                self.logger.info(u'{} | Bot at capacity'.format(self.me))
                message.reply(CurrentInstanceOverloaded)
                message.subreddit.moderator.leave()

                message.mark_read()
        except praw.exceptions.APIException:
            self.logger.error(u'API Error Accepting Mod Invite for sub {}'.format(message.subreddit))
            #message.mark_read()
        except praw.exceptions.ClientException:
            self.logger.error(u'Client Error Accepting Mod Invite for sub {}'.format(message.subreddit))
            #message.mark_read()
        except:
            self.logger.critical(u'General Error Accepting Mod Invite: {}'.format(message.name))
            message.mark_read()

    def getCorrectBot(self, subreddit):
        return self.masterClass.getBot(subreddit)

    def save_permissions(self, subreddit=None):
        if subreddit:
            subs = [subreddit]
        else:
            subs = self.subsModded

        for sub in subs:
            for mod in self.r.subreddit(str(sub)).moderator():
                if mod == self.me:
                    perms = ","
                    self.masterClass.save_sentinel_permissions(perms.join(mod.mod_permissions), str(sub))
                    break

    def start(self):
        try:
            self.save_permissions()
        except praw.exceptions.APIException:
            self.logger.error('Reddit HTTP Connection Error')
        while not self.masterClass.killThreads:
            #self.logger.debug('{} | Cycling..'.format(self.me.name))
            try:
                self.masterClass.done = set(self.masterClass.isProcessed(self.subsModded))
                self.shadowbans = self.shadowban_db.get_shadowbanned()
                #self.modMulti = self.r.subreddit('mod')

                self.checkContent()
                self.checkInbox()
                #self.checkModmail() # Not Used
                self.clearQueue()
                self.modlogger.log()
                self.modmailArchiver.log()
                if self.masterClass.killThreads:
                    self.logger.info("{} | Acknowledging killThread".format(self.me))
            except praw.exceptions.APIException:
                self.logger.error('Reddit HTTP Connection Error')
            except Exception as e:
                self.logger.error(u"{} | General Error - {}: Sleeping 30".format(self.me, e))
                time.sleep(30)

    
