from ..helpers import getSentinelLogger, DomainBlacklistDB
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import urllib
import re


class DomainBlacklist(object):
    def __init__(self, r, subs):
        self.logger = getSentinelLogger()

        self.db = DomainBlacklistDB()
        self.last_checked = None
        self.last_checked_optins = None
        self.subs = subs

    @property
    def opt_ins(self):
        if not self.last_checked_optins or self.last_checked_optins < datetime.now() - timedelta(minutes=5):
            self.last_checked_optins = datetime.now()
            return [i.lower() for i in self.db.get_subs_enabled()]

    @property
    def subs_intersec(self):
        return list(set([i.lower() for i in self.subs]) & set(self.opt_ins))


    def get_blacklisted(self):
        if not self.last_checked or self.last_checked < datetime.now() - timedelta(minutes=5):
            self.blacklisted = self.db.get_blacklisted(self.subs) #dict of {'subreddit':['list.com', 'of.net', 'banned.gov', 'sites.org']}
            self.last_checked = datetime.now()

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
            return urls

        for link in soup.find_all('a'):
            if 'http' in link.get('href'):
                urls.append(link.get('href'))

        return urls

    def domain_match(self, matcher, url):
        m = urllib.parse.urlparse(url).netloc.split('.')
        m2 = urllib.parse.urlparse(matcher).netloc('.')
        for i in range(len(m)):
            if m[i] == '*' or m[i] == m2[i]:
                continue
            else:
                return False
        return True

    def is_blacklisted(self, thing):
        self.get_blacklisted()
        subreddit = str(thing.subreddit)
        if subreddit not in self.blacklisted:
            return False
        if subreddit not in self.subs_intersec:
            return False
        urls = self.get_urls(thing)
        if any(self.domain_match(y, x) for y in self.blacklisted[subreddit] for x in urls):
            return True
        return False 


