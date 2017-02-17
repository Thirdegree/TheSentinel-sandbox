import requests
import time

from .database import ModloggerDB
from .SentinelLogger import getSentinelLogger

class Websync(object):
    def __init__(self, masterClass): #sentinels is a list of agents
        self.db = ModloggerDB()
        self.logger = getSentinelLogger()

        self.sentinels = [i[0] for i in masterClass.sentinels] #don't care about their queues
        self.masterClass = masterClass
        self.synccalls = {
            'tsbaccept': "http://beta.layer7.solutions/admin/resync?type=tsbaccept&subreddit={subreddit}",
            'addmoderator': "http://beta.layer7.solutions/admin/resync?type=addmoderator&subreddit={subreddit}&moderator={mod}",
            'acceptmoderatorinvite': "http://beta.layer7.solutions/admin/resync?type=acceptmoderatorinvite&subreddit={subreddit}&moderator={mod}",
            'removemoderator': "http://beta.layer7.solutions/admin/resync?type=removemoderator&subreddit={subreddit}&moderator={mod}",
            'setpermissions': "http://beta.layer7.solutions/admin/resync?type=setpermissions&subreddit={subreddit}&moderator={mod}&new_state={new_state}",}

    def get_unprocessed(self):
        return self.db.get_unprocessed()

    def process(self, unprocessed):
        done = []
        for item in unprocessed:
            try:
                action = item['action']
                if action == 'setpermissions':
                    for sentinel in self.sentinels:
                        if sentinel.canAction(item['thingid']):
                            break

                    item['new_state'] = sentinel.get_permissions(item['mod'], item['subreddit'])
                requests.get(self.synccalls[item[action]].format(item))
            except KeyError:
                pass
            finally:
                done.append()


        self.db.mark_processed(done)

    def main(self):
        while not self.masterClass.killThreads:
            #self.logger.debug('{} | Cycling..'.format(self.me.name))
            try:

                unprocessed = self.get_unprocessed()
                self.process(unprocessed)

                if self.masterClass.killThreads:
                    self.logger.info("{} | Acknowledging killThread".format('Websync'))
            except Exception as e:
                self.logger.error(u"{} | General Error - {}: Sleeping 30".format('Websync', e))
                time.sleep(30)