import requests
import time

from .database import ModloggerDB
from .SentinelLogger import getSentinelLogger

class Websync(object):
    def __init__(self, masterClass): #sentinels is a list of agents
        self.db = ModloggerDB()
        self.logger = getSentinelLogger()

        self.masterClass = masterClass
        self.synccalls = {
            'tsbaccept': "http://beta.layer7.solutions/admin/resync?type=tsbaccept&subreddit={subreddit}",
            'addmoderator': "http://beta.layer7.solutions/admin/resync?type=addmoderator&subreddit={subreddit}&moderator={target}",
            'acceptmoderatorinvite': "http://beta.layer7.solutions/admin/resync?type=acceptmoderatorinvite&subreddit={subreddit}&moderator={mod}",
            'removemoderator': "http://beta.layer7.solutions/admin/resync?type=removemoderator&subreddit={subreddit}&moderator={target}",
            'setpermissions': "http://beta.layer7.solutions/admin/resync?type=setpermissions&subreddit={subreddit}&moderator={target}&new_state={new_state}",
            }
        self.sentinels = [i[0] for i in self.masterClass.sentinels] #don't need the queues
        self.logger.info("Websync Thread Started")

    def get_unprocessed(self):
        return self.db.get_unprocessed()

    def ping_accept(self, subreddit):
        requests.get(self.synccalls['tsbaccept'].format(subreddit=subreddit))

    def process(self, unprocessed):
        if unprocessed:
            self.logger.debug("{} | Processing {} items".format('Websync', len(unprocessed)))
        done = []
        actions = []
        for item in unprocessed:
            try:
                
                if item['action'] == 'setpermissions':
                    for sentinel in self.sentinels:
                        if sentinel.canAction(None, subreddit=item['subreddit']):
                            new_state = ','.join(sentinel.get_permissions(item['target'], item['subreddit']))
                            #self.logger.info("{} | New state is {} ".format('Websync', new_state))

                            item['new_state'] = new_state
                            self.logger.debug("{} | New state is {} ".format('Websync', item['new_state']))
                url = self.synccalls[item['action']].format(**item)
                self.logger.debug("{} | Calling url: {}".format('Websync', url))
                requests.get(url)
                self.logger.info("{} | Processed {} action on {}".format('Websync', item['action'], item['mod'] if item['action'] == 'acceptmoderatorinvite' else item['target']))
            except KeyError:
                pass
            finally:
                done.append(item['modactionid'])
                actions.append(item['action'])
        #if actions:
        #    self.logger.info("{} | Saw actions {}".format('Websync', actions))
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