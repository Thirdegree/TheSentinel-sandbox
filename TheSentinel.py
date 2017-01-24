from multiprocessing import Queue
import threading
from datetime import datetime
from bs4 import BeautifulSoup
import requests.exceptions
import praw
import sys
import time
import json

from .helpers import getSentinelLogger, Utility
from .YouTube import YouTube
from .DailyMotion import DailyMotion
from .Vimeo import Vimeo
from .SoundCloud import SoundCloud
from .Twitch import Twitch
from .Vidme import Vidme
from .objects import Memcache, SentinelDatabase
from .oAuths import oAuth
from .Reddit import SentinelInstance


#import DailyMotion

class TheSentinel(object):
    def __init__(self):
        youtube = YouTube()
        dm = DailyMotion()
        vimeo = Vimeo()
        soundcloud = SoundCloud()
        twitch = Twitch()
        vidme = Vidme()

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
        }

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

        self.cache = Memcache()
        self.database = SentinelDatabase()
        self.utility = Utility()
        self.blacklistSub = 'TheSentinelBot'


    def get_items(self):
        # returns (thing, [urls])
        try:
            for item in self.cache.get_new():
                if item:
                    self.logger.debug(u'Returning from memcache: {}'.format(item.fullname if item else item)) 
                    yield self.get_urls(item)
        except requests.exceptions.HTTPError:
            self.logger.warning(u"HTTPError - continue")

    def process_webrequest(self, values_dict):
        values_dict = json.loads(values_dict)
        func_dict = {
            'add': self.addBlacklist,
            'remove': self.removeBlacklist,
        }
        if values_dict['action'] in func_dict:
            func_dict[values_dict['action']](thing=None, subreddit=values_dict['subreddit'], urls=[values_dict['url']], values_dict=values_dict)
            self.cache.add(True, keyString='webrequest')

    def writeSubs(self):
        subs = []
        for sentinel, _ in self.sentinels:
            subs += [self.add_subreddit(str(i[0]), str(sentinel), i[1], i[0])  for i in sentinel.subsModdedWrite]
        #subs = sorted(subs, key=lambda x: x[1], reverse=True)  # by size
        subs = list(set([str(i[0]) for i in subs]))
        subs = sorted(subs, key=str.lower)    # alphabetically
        with open('C:\\inetpub\\wwwroot\\Layer7.Solutions\\resources\\TheSentinelSubs.txt', 'w') as file:    
            file.write("\n".join(subs))

    def remove_subreddit(self, subreddit):
        pass
        self.utility.remove_subreddit(subreddit)

    def add_subreddit(self, subreddit, botname, subscribers, thing=None):
        pass
        if not thing:
            self.utility.add_subreddit(subreddit, botname, subscribers)
        else:
            self.utility.add_subreddit(str(thing), botname, thing.subscribers)
            return (thing, subscribers)



    #REDDIT SPECIFIC HERE
    def get_urls(self, item):
        urls = []
        noLink = False
        try:
            soup = BeautifulSoup(item.selftext_html, 'html.parser')
            #self.logger.debug(u'Soup: Parsing Self Text')
        except AttributeError: # if it's a comment
            soup = BeautifulSoup(item.body_html, 'html.parser')
            #self.logger.debug(u'Soup: Parsing Comment')
        except TypeError: # if it's a direct link
            urls.append(item.url)
            noLink = True
            #self.logger.debug(u'Soup: Direct Link')

        if noLink:
            return (item, urls)

        for link in soup.find_all('a'):
            if 'http' in link.get('href'):
                urls.append(link.get('href'))

        #self.logger.debug(u'Found all links in Soup')

        return (item, urls)

    def getBot(self, sub):
        for sentinel, _ in self.sentinels:
            sentinelSubs = [str(x).lower() for x in sentinel.subsModded]
            self.logger.debug(u"Checking sentinel {} modding subbs {}".format(sentinel, sentinelSubs))
            
            if any([str(sub).lower() == x for x in sentinelSubs]):
                self.logger.debug(u'Returned instance of bot for sub: {}'.format(sub.display_name))
                return sentinel
        return None

    def remove(self, thing):
        for sentinel, queue in self.sentinels:
            temp = sentinel.canAction(thing)
            if temp:
                queue.put(temp)
                self.logger.debug(u'Put {} in queue'.format(temp.fullname))
                return True
        return False

    #REDDIT SPECIFIC HERE
    def needsRemoval(self, item):
        thing, urls = item
        hasContent = 0
        for url in urls:
            hasContent = 1
            self.logger.debug(u'Checking blacklist for {} | URL: {}'.format(thing.fullname, url))
            if self.isBlacklisted(str(thing.subreddit), url):
                return 2, thing
        return hasContent, None

    def isBlacklisted(self, subreddit, url):
        for i, k in self.processes.items():
            if k.hasBlacklisted(subreddit, url):
                return True
        return False

    def isProcessed(self, subreddits):

        return self.database.isProcessed([str(x) for x in subreddits])

    #There's a bottleneck here reguarding praw and refresh() in praw.objects.Refreshable.
    #Not worth worrying about atm, but it may be a problem in the future.
    def markProcessed(self, things):
        toDo = []
        if things:
            self.logger.debug(u"Preparing to add {} things to the database".format(len(things)))
        for thing in things:
            if isinstance(thing, praw.models.Submission):
                link = 'http://reddit.com/{}'.format(thing.id)
            elif isinstance(thing, praw.models.Message):
                link = ''
            else:
                link = 'http://reddit.com/comments/{}/-/{}'.format(thing.link_id[3:], thing.id) 

            info_dict = {
                'subreddit': str(thing.subreddit),
                'thing_id': thing.fullname,
                'author': str(thing.author),
                'thingcreated_utc': thing.created_utc,
                'thingedited_utc': thing.edited,
                'parent_thing_id': thing.submission.fullname if type(thing) == praw.models.Comment else None,
                'permalink': link,
                'media_author': '',
                'media_channel_id': '',
                'media_platform': '',
                'media_link': '',
                'title': thing.title if type(thing) == praw.models.Submission else None,
                'url': thing.url,
                'flair_class': thing.link_flair_css_class if type(thing) == praw.models.Submission else None,
                'flair_text': thing.link_flair_text if type(thing) == praw.models.Submission else None,
                'body': (thing.body if type(thing) != praw.models.Submission else thing.selftext_html),
                }
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
                    info_dict[k] = ",".join(v)
            except KeyError:
                pass
            toDo.append(info_dict)
            self.logger.debug(u"Prepared item {}".format(thing.fullname))
        self.database.markProcessed(toDo)

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

        self.logger.info(u'Starting Sentinel Instance Threads')
        for t in self.threads:
            t.start()

    def getInfo(self, thing, urls=[]):
        data = []
        if thing:
            thing, urls = self.get_urls(thing)
        for url in urls:
            temp = None
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
                self.logger.info(u"Processed url - {}; Media Author(s) - {}".format(url, [i['media_author'] for i in temp]))
        if data:
            return data
        else:
            raise KeyError(u"No match found - {}".format(urls))
    #REDDIT SPECIFIC HERE
    def addBlacklist(self, thing, subreddit, urls=[], isGlobal=False, values_dict=None):
        data = self.getInfo(thing, urls)
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
            return self.database.addBlacklist(i)


    #REDDIT SPECIFIC HERE
    def removeBlacklist(self, thing, subreddit, urls=[], values_dict=None):
        data = self.getInfo(thing, urls)
                
        for i in data:
            i['subreddit'] = str(subreddit)
            i['date'] = datetime.today()
            self.logger.info(u'Removing from database: {} for sub r/{}'.format(thing.fullname if thing else 'WebRequest', i['subreddit']))
            self.database.removeBlacklist(**i)

    def phone_home(self):
        for i in self.cache.get_new('marco_thesentinelbot'):
            self.cache.add_polo()


    def main(self):
        self.startThreads()
        self.writeSubs()
        running = True
        while running:
            
            try:
                #self.logger.debug('Cycling..')
                self.phone_home()
                items = self.get_items()
                for item in items:
                    try:
                        level, thing = self.needsRemoval(item)
                    except requests.exceptions.HTTPError:
                        continue
                    if level == 2:
                        self.remove(thing)
                time.sleep(10)

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
