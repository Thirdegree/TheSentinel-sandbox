import configparser
import os
import re
import memcache # https://pypi.python.org/pypi/python-memcached
from memcached_stats import MemcachedStats # https://github.com/dlrust/python-memcached-stats
import tweepy

from ..objects import datapulls
import requests

from ..helpers import Zion, getSentinelLogger, TheTraveler, Utility
from ..exceptions import InvalidAddition



class MediaProcess(object):
    def __init__(self, APIProcess, mediaURLs):
        # Initialize the logger
        self.logger = getSentinelLogger()

        self.db = SentinelDatabase()
        self.APIProcess = APIProcess()
        self.mediaURLs = mediaURLs

        self.logger.debug('Initialized MediaProcess')


    def validateURL(self, url):
        self.logger.debug(u'Checking if URL in MediaURLs list. URL: {}'.format(url))
        for i in self.mediaURLs:
            if i in url:
                return True
        return False

    def hasBlacklisted(self, subreddit, url):
        if not self.validateURL(url):
            self.logger.debug('Not valid media URL')
            return False
        channels = self.APIProcess.getInformation(url)
        for i in channels:
            if self.db.isBlacklisted(subreddit, **i):
                self.logger.debug('Channel is Blacklisted. URL: {}'.format(url))
                return True
        return False

    def addToBlacklist(self, subreddit, url, playlist=False):
        if not self.validateURL(url):
            return False
        channels = self.APIProcess.getInformation(url)
        if len(channels) != 1 and not playlist:
            self.logger.warning(u'Invalid blacklist addition; either playlist or owner could not be found. URL: {}'.format(url))
            raise InvalidAddition("Invalid blacklist addition; either playlist or owner could not be found - %s" % url)
        for ch in channels:
            self.logger.debug('Attemping to add to DB')
            self.db.addBlacklist(subreddit, **ch)

    def getInformation(self, url):
        self.logger.debug(u'Attemping to getInformation(). URL: {}'.format(url))
        if not self.validateURL(url):
            return []
        else:
            return self.APIProcess.getInformation(url)


class APIProcess(object):
    def __init__(self, API_URLS, regexs, data_pulls):
        # Initialize the logger
        self.logger = getSentinelLogger()

        self.API_URLS = API_URLS
        self.regexs = regexs
        self.data_pulls = data_pulls

        self.api_key = None
        self.headers = None

    def _getJSONResponse(self, data, key):
        response = requests.get(self.API_URLS[key].format(data, self.api_key), headers=self.headers)

        if response.status_code != 200:
            self.logger.error(u'Get API Data Error. Error Code: {} | Data: {}'.format(response.status_code, self.API_URLS[key].format(data, self.api_key)))
            response.raise_for_status()

        return key, response.json()

    #(key, data)
    def _getData(self, url):
        self.logger.debug('Getting URL Redirect Data')
        try:
            url = requests.get(url).url #deals with redirects
        except requests.exceptions.ConnectionError:
            raise KeyError("Problem resolving url. No match.")
        try:
            for i in self.regexs:
                match = re.search(self.regexs[i], url)
                if match:
                    self.logger.debug('Match Found')
                    break
            return (i, match.group(1))
        except AttributeError:
            self.logger.debug(u'No Match Found. URL: {}'.format(url))
            raise KeyError("No match found - %s" % url)

    def getInformation(self, url):
        self.logger.debug(u'Getting Infomration. URL: {}'.format(url))
        try:
            key, data = self._getData(url)
        except KeyError:
            return []
        key, jsonResponse = self._getJSONResponse(data, key)
        try:
            alldata = self.data_pulls[key](jsonResponse) or []
        except TypeError:
            return []
        except KeyError:
            return []
        if key == 'playlist':
            self.logger.debug('Getting Playlist Data')
            key, jsonResponse = self._getJSONResponse(data, 'playlist videos')
            try:
                alldata += self.data_pulls['playlist videos'](jsonResponse)
            except TypeError:
                pass
        return alldata

class TwitterAPIProcess(APIProcess):
    def __init__(self):

        self.logger = getSentinelLogger()


        Config = configparser.ConfigParser()
        Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))
        consumer_key = Config.get('TwitterAPI', 'CONSUMER_KEY')
        consumer_secret = Config.get('TwitterAPI', 'CONSUMER_SECRET')
        access_token = Config.get('TwitterAPI', 'ACCESS_TOKEN')
        access_token_secret = Config.get("TwitterAPI", "ACCESS_TOKEN_SECRET")

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

        Twitter_URLS = {
            'user': lambda x: self.api.get_user(x),
        }

        regexs = {
            'user': r"r\.com\/(.*?)(?:\/|\?|\&|$|#)"
        }

        super(TwitterAPIProcess, self).__init__(Twitter_URLS, regexs, datapulls.TwitterAPIPulls)

    def getInformation(self, url):
        self.logger.debug(u'Getting Information. URL: {}'.format(url))
        try:
            key, data = self._getData(url)
        except KeyError as e:
            return []
        try:
            obj = self.API_URLS[key](data)
        except tweepy.error.TweepError:
            return []
        try:
            alldata = self.data_pulls[key](obj) or []
        except TypeError:
            return []

        
        return alldata


class VidmeAPIProcess(APIProcess):
    def __init__(self):

        self.logger = getSentinelLogger()

        Vidme_URLS = {
            'video': 'https://api.vid.me/videoByUrl?url={}',
        }

        regexs = {
            'video': r'(https:\/\/vid\.me\/.*)',
        }

        super(VidmeAPIProcess, self).__init__(Vidme_URLS, regexs, datapulls.VidmeAPIPulls)

class TwitchAPIProcess(APIProcess):
    def __init__(self):

        self.logger = getSentinelLogger()

        Twitch_URLS = {
            'user': 'https://api.twitch.tv/kraken/users?login={}',
        }
        
        regexs = {
            'user': r'\.tv\/(.*?)(?:$|\/)',
        }

        Config = configparser.ConfigParser()
        Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))
        api_key = Config.get('TwitchAPI', 'AUTH_KEY')
        

        super(TwitchAPIProcess, self).__init__(Twitch_URLS, regexs, datapulls.TwitchAPIPulls)
        self.headers = {'Accept': 'application/vnd.twitchtv.v5+json', 'Client-ID': api_key}




class GAPIProcess(APIProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        GAPI_URLS = {
            'channel': 'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={}&fields=items(id%2Csnippet%2Ftitle)&key={}', #GOOD,
            'video': 'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={}&fields=items(snippet(channelId%2CchannelTitle))&key={}', #GOOD
            'playlist': 'https://www.googleapis.com/youtube/v3/playlists?part=snippet&id={}&fields=items(snippet(channelId%2CchannelTitle))&key={}', # GOOD
            'playlist videos': 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={}&fields=items(contentDetails%2FvideoId%2Csnippet(channelId%2CchannelTitle))&key={}', #GOOD
            'username': 'https://www.googleapis.com/youtube/v3/channels?part=snippet&forUsername={}&fields=items(id%2Csnippet%2Ftitle)&key={}' #GOOD}
        }
        regexs = {
            'channel': r'''(?i)channel\/(.*?)(?:\/|\?|$)''',
            'playlist': r'list=((?!videoseries).*?)(?:#|\/|\?|\&|$)',
            'username': r'user\/(.*)(?:\?|$|\/)',
            'video': r'(?:(?:watch\?.*?v=(.*?)(?:#.*)?)|youtu\.be\/(.*?)(?:\?.*)?)(?:#|\&|\/|$)'
        }

        Config = configparser.ConfigParser()
        Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))
        api_key = Config.get('GAPI', 'AUTH_KEY')

        self.logger.debug('Running GAPI Datapull')
        super(GAPIProcess, self).__init__(GAPI_URLS, regexs, datapulls.GAPIpulls)
        self.api_key = api_key

class DMAPIProcess(APIProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        DAILYMOTION_URLS = {
            'playlist': 'https://api.dailymotion.com/playlist/{}?fields=owner,owner.screenname',
            'playlist videos': 'https://api.dailymotion.com/playlist/{}/videos?fields=owner,owner.screenname',
            'username': 'https://api.dailymotion.com/user/{}?fields=id,screenname',
            'video': 'https://api.dailymotion.com/video/{}?fields=owner,owner.screenname'
        }

        regexs = {
            'playlist': r'playlist\/(.*?)_',
            'video': r'(?:video\/|dai\.ly\/)(.*?)(?:#|\/|\?|$)',
        }

        self.logger.debug('Running DailyMotion Datapull')
        super(DMAPIProcess, self).__init__(DAILYMOTION_URLS, regexs, datapulls.DMpulls)

    def _getData(self, url):
        try:
            return super(DMAPIProcess, self)._getData(url)
        except KeyError:
            try:
                match = re.search(r'\.com\/(.*?)(?:\/|\?|$)', url)
                self.logger.debug('DM Match Found')
                return ('username', match.group(1))
            except AttributeError:
                self.logger.debug(u'No match found. URL: {}'.format(url))
                raise KeyError("No match found - %s" % url)

class VMOAPIProcess(APIProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        VIMEO_URLS = {
            'user': 'https://api.vimeo.com/users/{}?fields=uri,name',
            'playlist': 'https://api.vimeo.com/channels/{}?fields=user.uri,user.name',
            'playlist videos': 'https://api.vimeo.com/channels/{}/videos',
            'video': 'https://api.vimeo.com/videos/{}?fields=user.name,user.uri'
        }

        regexs = {
            'user': r'\/user(.*?)(?:\/|\?|$)',
            'playlist': r'\/channels\/(.*?)(?:\/|\?|$)'
        }

        self.logger.debug('Running Vimeo Datapull')
        super(VMOAPIProcess, self).__init__(VIMEO_URLS, regexs, datapulls.VMOpulls)

        Config = configparser.ConfigParser()
        Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))

        api_key = Config.get('VIMEO', 'AUTH_KEY')
        self.headers = {"Authorization": "Bearer " + api_key}

    def _getData(self, url):
        try:
            return super(VMOAPIProcess, self)._getData(url)
        except KeyError:
            try:
                match = re.search(r'\.com\/([^(?:user)].*?)(?:#|\/|\?|$)', url)
                self.logger.debug('Viemo Match Found')
                return ('video', match.group(1))
            except AttributeError:
                self.logger.debug('No match found. URL: {}'.format(url))
                raise KeyError("No match found - %s" % url)

    def _getJSONResponse(self, data, key):
        try:
            self.logger.debug('Getting Vimeo Data')
            return super(VMOAPIProcess, self)._getJSONResponse(data, key)
        except requests.exceptions.HTTPError:
            self.logger.debug('Getting Vimeo User Data')
            return super(VMOAPIProcess, self)._getJSONResponse(data, 'user')

class SCAPIProcess(APIProcess):
    def __init__(self):
        # Initialize the logger
        self.logger = getSentinelLogger()

        SOUNDCLOUD_URLS = {
            'all': 'https://api.soundcloud.com/resolve?url={}&client_id={}',
            'playlist videos': 'https://api.soundcloud.com/resolve?url={}&client_id={}',
        }

        regexs = {
            'all': r'(https:\/\/soundcloud\.com\/.*?)(?:#t?|$)',
        }

        self.logger.debug('Running SoundCloud Datapull')
        super(SCAPIProcess, self).__init__(SOUNDCLOUD_URLS, regexs, datapulls.SCpulls)

        Config = configparser.ConfigParser()
        Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))

        api_key = Config.get('SOUNDCLOUD', 'AUTH_KEY')
        self.api_key = api_key

    def getInformation(self, url):
        try:
            try:
                key, data = self._getData(url)
            except KeyError:
                return []
        
            key, jsonResponse = self._getJSONResponse(data, key)
            try:
                alldata = self.data_pulls[key](jsonResponse) or []
            except TypeError:
                return []
            self.logger.debug('Received data response')
            if jsonResponse['kind'] == 'playlist':
                self.logger.debug('Parsing playlist data')
                key, jsonResponse = self._getJSONResponse(data, 'playlist videos')
                try:
                    alldata += self.data_pulls['playlist videos'](jsonResponse)
                except TypeError:
                    pass
            return alldata
        except TypeError:
            self.logger.error(u'Error Getting Soundcloud Data. URL: {}'.format(url))
            return []
        



class SentinelDatabase(Zion, TheTraveler):
    pass

class Memcache(object):
    def __init__(self, server_address='127.0.0.1', server_port=11211):
        # Initialize the logger
        self.logger = getSentinelLogger()

        self.memclient = memcache.Client(['{0}:{1}'.format(server_address, server_port)], debug=0)
        self.memstats = MemcachedStats()
        self.memstats = MemcachedStats(server_address, server_port)

    def get_new(self, keyString='tsb'):
        try:
            # Get keys in the Memcache
            memcachekeys = self.memstats.keys()
            #self.logger.debug('Got memcache keys from memstats') #this is not helpful :D

            for key in memcachekeys:
                if key.startswith(keyString):
                    # Get the item from the memcache
                    thing = self.memclient.get(key)
                    self.logger.debug(u'Got key: {} from memcache'.format(key))
                    # Delete it from memcache
                    self.memclient.delete(key)
                    yield thing

        except Exception:
            self.logger.error('Unable to access memcache queue')

    def add(self, thing, keyString='tsb'):
        self.memclient.set("{}_{}".format(keyString, thing.fullname), thing)
        self.logger.debug(u'Added {} to memcache queue from {}'.format(thing.fullname, thing.subreddit))

    def add_polo(self, botname='thesentinelbot'):
        self.memclient.set("{}_{}".format('polo', botname), botname)
        self.logger.info(u'Responding to marco_polo.')