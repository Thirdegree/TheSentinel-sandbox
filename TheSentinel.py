from multiprocessing import Queue
import threading
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')
import requests.exceptions
import praw, prawcore
import sys, os, time
import json, jsonpickle
import configparser

from .helpers import getSentinelLogger, Utility, Websync
from .YouTube import YouTube
from .DailyMotion import DailyMotion
from .Vimeo import Vimeo
from .SoundCloud import SoundCloud
from .Twitch import Twitch
from .Vidme import Vidme
from .Twitter import Twitter
from .objects import Memcache, SentinelDatabase
from .oAuths import oAuth
from .Reddit import SentinelInstance
from .exceptions import TooFrequent
from .RabbitMQ import *

class TheSentinel(object):
    def __init__(self):
        youtube = YouTube()
        dm = DailyMotion()
        vimeo = Vimeo()
        soundcloud = SoundCloud()
        twitch = Twitch()
        vidme = Vidme()
        twitter = Twitter()

        # Initialize the logger
        self.logger = getSentinelLogger()
        self.logger.debug(u'Logger Initialized')
        
        self.processes = {
            'YouTube': youtube,
            'DailyMotion': dm,
            'Vimeo': vimeo,
            'SoundCloud': soundcloud,
            'Twitch': twitch,
            'Vidme': vidme,
            'Twitter': twitter,
        }

        self.cache = Memcache()
        self.database = SentinelDatabase()
        self.utility = Utility()

        self.blacklistSub = 'TheSentinelBot'

        #must be added to manually until I find a better solution
        # List of (SentinelInstance(), queue) pairs
        self.sentinels = []
        auth = oAuth("tsb")
        self.logger.info(u"/*********Starting agents*********\\")
        for account in auth.accounts:
            queue = Queue()
            instance = SentinelInstance(account, queue, self)
            self.sentinels.append((instance, queue))
            self.logger.info(u'Started Instance: {}'.format(instance.r.user.me()))

        self.threads = []
        self.killThreads = False
        self.websync = Websync(self)

        self.last_mod_alert = None
        self.done = set()

        self.load_config()


    def load_config(self):
        Config = configparser.ConfigParser()
        mydir = os.path.dirname(os.path.abspath(__file__))
        Config.read(os.path.join(mydir, "global_config.ini"))

        self.ex_SentinelExchange    = Config.get('RabbitMQ', 'ex_SentinelExchange')
        self.rk_Sentinel_ToProcess  = Config.get('RabbitMQ', 'rk_Sentinel_ToProcess')
        self.rk_Sentinel_Results    = Config.get('RabbitMQ', 'rk_Sentinel_AnalysisResults')
        #self.rk_Dirtbag_ToProcess    = Config.get('RabbitMQ', 'rk_Dirtbag_ToProcess')

    def create_dict_item(self, thing):
        try:
            if isinstance(thing, praw.models.Submission):
                link = 'http://reddit.com/{}'.format(thing.id)
                url = str(thing.url) if thing.is_self == False else ''
                bodytext = thing.selftext_html if (thing.is_self == True and thing.selftext_html is not None) else ''
            elif isinstance(thing, praw.models.Message):
                link = ''
                url = ''
            else:
                link = 'http://reddit.com/comments/{}/-/{}'.format(thing.link_id[3:], thing.id)
                url = ''
                bodytext = thing.body_html if thing.body_html is not None else ''

            # Shadowbanned/Deleted user handling
            try:
                authCreated = str(datetime.utcfromtimestamp(thing.author.created_utc).date())
                authCKarma = thing.author.comment_karma
                authLKarma = thing.author.link_karma
            except Exception as e:
                authCreated = ''
                authCKarma = ''
                authLKarma = ''


            info_dict = {
                'subreddit': str(thing.subreddit),
                'thing_id': thing.fullname,
                'author': str(thing.author),
                'Author_Created': authCreated,
                'Author_CommentKarma': authCKarma,
                'Author_LinkKarma': authLKarma,
                'thingcreated_utc': str(datetime.utcfromtimestamp(thing.created_utc)),
                'thingedited_utc': str(datetime.utcfromtimestamp(thing.edited)) if thing.edited else None,
                'parent_thing_id': thing.submission.fullname if type(thing) == praw.models.Comment else '',
                'permalink': link,
                'media_author': '',
                'media_channel_id': '',
                'media_platform': '',
                'media_link': '',
                'title': thing.title if type(thing) == praw.models.Submission else '',
                'url': url,
                'flair_class': thing.link_flair_css_class if (type(thing) == praw.models.Submission and thing.link_flair_css_class is not None) else '',
                'flair_text': thing.link_flair_text if (type(thing) == praw.models.Submission and thing.link_flair_text is not None) else '',
                'body': bodytext,
                }
            self.logger.debug('Created dict for ThingID: {}'.format(info_dict['thing_id']))
            return info_dict
        except prawcore.exceptions.NotFound:
            self.logger.warning('Unable to get user data. Maybe Shadowbanned. ThingID: {}'.format(thing.fullname))
            return None
        except Exception as e:
            self.logger.error('Unable to create_dict_item. ThingID: {}'.format(thing.fullname))
            return None

    def get_items(self):
        # returns (thing, [urls])
        try:
            while not self.SentinelConsumer.processQueue.empty():
                item = self.SentinelConsumer.processQueue.get() # gets a json object out of a queue
                if item:
                    thing = json.loads(item) # creates a dictionary item
                    if thing:
                        self.logger.debug('Got item from get_items: {}'.format(thing['thing_id']))
                        yield self.get_urls(thing)
        except requests.exceptions.HTTPError:
            self.logger.warning(u"HTTPError - continue")

    def get_from_dirtbag(self):
        for item in iter(self.DirtbagConsumer.processQueue.get()):
            self.logger.info('Got data from DirtbagConsumer')
            data = json.loads(item)

            if data['RequiredAction'] == 'Remove': # Possible Values: ['Remove', 'Report', 'Nothing']
                #put in removal queue
                self.remove(thing)

    def messageSubreddits(self, title, body):
        if self.last_mod_alert:
            sincelast = datetime.now() - self.last_mod_alert
            if sincelast < timedelta(hours=1):
                raise TooFrequent(sincelast)
        sent = True
        for sentinel, _ in self.sentinels:
            sent = sent and sentinel.messageSubreddits(title, body)
        if sent:
            self.last_mod_alert = datetime.now()
        return sent

    def forceModlogHistory(self, body, author):
        for sentinel, _ in self.sentinels:
            sentinel.forceModlogHistory(body, author)

    def forceModMailHistory(self, body, author):
        for sentinel, _ in self.sentinels:
            sentinel.forceModMailHistory(body, author)

    def writeSubs(self):
        subs = []
        for sentinel, _ in self.sentinels:
            subs += [self.add_subreddit(str(i[0]), str(sentinel), i[1], i[0])  for i in sentinel.subsModdedWrite]
        #subs = sorted(subs, key=lambda x: x[1], reverse=True)  # by size
        subs = list(set([str(i[0]) for i in subs]))
        subs = sorted(subs, key=str.lower)    # alphabetically
        try:
            with open('C:\\inetpub\\wwwroot\\Layer7.Solutions\\resources\\TheSentinelSubs.txt', 'w') as file:    
                file.write("\n".join(subs))
        except Exception as e:
            self.logger.warning('Unable to locate TheSentinelSubs file')
            

    def remove_subreddit(self, subreddit):
        self.utility.remove_subreddit(subreddit)

    def add_subreddit(self, subreddit, botname, subscribers, thing=None):
        if not thing:
            self.utility.add_subreddit(subreddit, botname, subscribers)
        else:
            self.utility.add_subreddit(str(thing), botname, thing.subscribers)
            return (thing, subscribers)

    def save_sentinel_permissions(self, permissions, subreddit):
        self.utility.update_permissions(permissions, subreddit)
        #self.logger.debug('Updated permissions for: {} | Perms: {}'.format(subreddit, permissions))



    #REDDIT SPECIFIC HERE
    def get_urls(self, item):
        # takes a dict or thing
        urls = []
        noLink = False
        soup = None
        if not isinstance(item, dict):
            item = self.create_dict_item(item)

        if isinstance(item, dict):
            if item['url']:
                urls.append(item['url'])
                noLink = True
                self.logger.debug(u'Soup: Direct Link')
            else:
                if item['body'] is not None and len(item['body']) >= 5:
                    soup = BeautifulSoup(item['body'], 'html.parser')
                    self.logger.debug(u'Soup: Parsing Self Text')              

        if noLink:
            return (item, urls)

        if soup:
            for link in soup.find_all('a'):
                if 'http' in link.get('href'):
                    urls.append(link.get('href'))

        self.logger.debug(u'Found all links in Soup. Thing: {} | URLs: {}'.format(item['thing_id'], urls))
        return (item, urls) # returns dict, list

    def getBot(self, sub):
        for sentinel, _ in self.sentinels:
            sentinelSubs = [str(x).lower() for x in sentinel.subsModded]
            self.logger.debug(u"Checking sentinel {} modding subbs {}".format(sentinel, sentinelSubs))
            
            if any([str(sub).lower() == x for x in sentinelSubs]):
                self.logger.debug(u'Returned instance of bot for sub: {}'.format(sub.display_name))
                return sentinel
        return None

    def remove(self, thing):
        # takes thing as a dict
        for sentinel, queue in self.sentinels:
            temp = sentinel.canAction(thing)
            if temp:
                queue.put(temp)
                try:
                    self.logger.debug(u'Put Sentinel Thing: {} in removal queue'.format(temp['thing_id']))
                except KeyError:
                    self.logger.debug(u'Put Dirtbag Thing: {} in removal queue'.format(temp['ThingID']))
                return True
        return False

    #REDDIT SPECIFIC HERE
    def needsRemoval(self, item):
        # thing is a dictionary
        thing, urls = item # dict, list
        hasContent = 0
        for url in urls:
            hasContent = 1
            self.logger.debug(u'Checking blacklist for {} | URL: {}'.format(thing['thing_id'], url))

            for i, k in self.processes.items():
                try:
                    blacklisted = k.hasBlacklisted(thing, url)
                    if blacklisted:
                        self.logger.debug('Item blacklistd, about to put in removal queue: {}'.format(thing['thing_id']))
                        self.remove(thing)
                except requests.exceptions.SSLError:
                    continue

    def isProcessed(self, subreddits):
        return self.database.isProcessed([str(x) for x in subreddits])

    #There's a bottleneck here reguarding praw and refresh() in praw.objects.Refreshable.
    #Not worth worrying about atm, but it may be a problem in the future.
    def markProcessed(self, things):
        toDo = []
        if things:
            self.logger.debug(u"Preparing to add {} things to the database".format(len(things)))
        for thing in things:
            info_dict = self.create_dict_item(thing)
            try:
                data = self.getInfo(thing)
                temp = {
                    'media_author': [],
                    'media_channel_id': [],
                    'media_platform': [],
                    'media_link': [],
                }
                for i in data:
                    for k, v in i.items():
                        if k not in info_dict:
                            temp[k] = [v]
                        else:
                            temp[k].append(v)
                for k, v in temp.items():
                    info_dict[k] = ",".join([str(i) for i in v])
            except KeyError:
                pass
            toDo.append(info_dict)
            self.logger.debug(u"Prepared item {}".format(thing.fullname))
        self.database.markProcessed(toDo)

    def markActioned(self, thing, type_of):
        self.database.markActioned(thing.fullname, type_of)

    def markUsers(self, things): #[(contentCreator, things)]
        toDo = []
        users = filter(lambda x: str(x[1].subreddit).lower() in things)
        if users:
            self.logger.debug(u"Preparing to add {} users to the db".format(len(users)))
        for level, thing in things:
            redditor = thing.author
            if redditor.fullname in self.users:
                continue
            if isinstance(thing, praw.models.Comment):
                level = 0

            if isinstance(thing, praw.models.Submission):
                link = 'http://reddit.com/{}'.format(thing.id)
            else:
                link = 'http://reddit.com/{}/-/{}'.format(thing.link_id[3:], thing.id) 

            toDo.append({
                'author_id': author_id.fullname,
                'author': str(redditor),
                'thingcreated_utc': thing.created_utc,
                'permalink': link,
                'content_creator': level
                })
            self.logger.debug(u"Prepared item {}".format(thing.fullname))
        self.database.addUsers(toDo)

    def startThreads(self):
        for sentinel, queue in self.sentinels:
            # Existing Code
            thread = threading.Thread(target=sentinel.start)
            self.threads.append(thread)
        self.threads.append(threading.Thread(target=self.websync.main))
        self.logger.info(u'Starting Sentinel Instance Threads')
        for t in self.threads:
            t.start()

    def getInfo(self, thing, urls=[]):
        # takes a PRAW thing object
        data = []
        if thing:
            thing, urls = self.get_urls(thing) # returns dict, list
        for url in urls:
            temp = None
            self.logger.debug(u'Getting Media API Information. URL: {}'.format(url))
            for i, k in self.processes.items():
                try:
                    temp = k.getInformation(url)
                    for j in temp:
                        j['media_link'] = url
                except KeyError:
                    continue
                except requests.exceptions.HTTPError:
                    continue

                if temp:
                    data+=temp
            if temp:
                self.logger.debug(u"Processed url - {}; Media Author(s) - {}".format(url, [i['media_author'] for i in temp]))
        if data:
            return data
        else:
            raise KeyError(u"No match found - {}".format(urls))

    #REDDIT SPECIFIC HERE
    def addBlacklist(self, thing, subreddit, urls=[], isGlobal=False, values_dict=None):
        try:
            data = self.getInfo(thing, urls)
        except KeyError:
            return None
        authors = []
        for i in data:
            i['thingid'] = thing.fullname
            i['author'] = str(thing.author) if thing else values_dict['modname']
            i['subreddit'] = (self.blacklistSub if isGlobal else str(subreddit))
            i['thingcreated_utc'] = thing.created_utc if thing else time.time()
            try:
                i['permalink'] = thing.permalink if thing else None
            except AttributeError:
                i['permalink'] = None
            i['body'] = thing.body
            self.logger.info(u'Adding to database: {} for sub r/{}'.format(i['thingid'], i['subreddit']))
            success = self.database.addBlacklist(i)
            if success:
                authors.append(i['media_author'])
        return authors


    #REDDIT SPECIFIC HERE
    def removeBlacklist(self, thing, subreddit, urls=[], values_dict=None):
        data = self.getInfo(thing, urls)
                
        authors = []
        for i in data:
            i['subreddit'] = str(subreddit)
            i['date'] = datetime.today()
            i['author'] = str(thing.author) if thing else values_dict['modname']
            self.logger.info(u'Removing from database: {} for sub r/{}'.format(thing.fullname if thing else 'WebRequest', i['subreddit']))
            success = self.database.removeBlacklist(**i)
            if success:
                authors.append(i['media_author'])

        return authors

    def phone_home(self):
        for i in self.cache.get_new('marco_thesentinelbot'):
            self.cache.add_polo()

    def main(self):
        self.startThreads()
        self.writeSubs()
        # Creates Rabbit Consumer - For Sentinel Internal ToProcess queue
        self.SentinelConsumer = Rabbit_Consumer(exchange=self.ex_SentinelExchange, routing_key=self.rk_Sentinel_ToProcess, QueueName=self.rk_Sentinel_ToProcess, host='localhost')
        self.SentinelConsumer.channel.basic_consume(self.SentinelConsumer.callback, queue=self.rk_Sentinel_ToProcess)
        tsb_thread = threading.Thread(target=self.SentinelConsumer.channel.start_consuming)
        tsb_thread.start()

        # Creates Rabbit Consumer - For return data from Dirtbag to have Sentinel process
        self.DirtbagConsumer = Rabbit_Consumer(exchange=self.ex_SentinelExchange, routing_key=self.rk_Sentinel_Results, QueueName=self.rk_Sentinel_Results, host='localhost')
        self.DirtbagConsumer.channel.basic_consume(self.DirtbagConsumer.callback, queue=self.rk_Sentinel_Results)
        dirtbag_thread = threading.Thread(target=self.DirtbagConsumer.channel.start_consuming)
        dirtbag_thread.start()

        get_from_dirtbag_thread = threading.Thread(target=self.get_from_dirtbag)
        get_from_dirtbag_thread.start()
        
        running = True
        while running:
            try:
                for item in self.get_items():
                    try:
                        self.needsRemoval(item) # sends dict
                    except requests.exceptions.HTTPError:
                        continue

            except KeyboardInterrupt:
                self.logger.warning(u"Keyboard Interrrupt - exiting")
                running = False
            except requests.exceptions.RequestException:
                self.logger.error('General Exception - Connection Error - Sleeping 30')
                time.sleep(30)
            except:
                self.logger.critical(u"General exception - Sleeping 30")
                time.sleep(30)

        else:
            self.logger.warning(u"Killing threads then exiting.")
            self.killThreads = True
            for thread in self.threads:
                thread.join() #waits for all threads to die.
