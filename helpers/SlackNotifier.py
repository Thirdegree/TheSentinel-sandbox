import requests, json
from retrying import retry

from .SentinelLogger import getSentinelLogger
from .database import SlackHooks

class SlackNotifier(object):
    def __init__(self):
        self.database = SlackHooks()
        
    @property
    def hook_table(self):
        hooks = self.database.getHooks()
        #make this a property that gets the new hooks on call
        ht = {}

        for subreddit, url, channel in hooks:
            ht[subreddit] = self._send_message(url, channel)

        return ht



    def _send_message(self, url, channel):

        @retry(stop_max_attempt_number=3)
        def send_message_closure(message):
            payload = {"channel": channel, "username": "TheSentinelBot", "text": u"*Attention:* _The following item has been removed._ \n*Channel Author:* {media_author} \n*Reddit Author:* {author} \n*Subreddit:* {subreddit} \n*Reddit Link:* {permalink} \n*Report Data:* http://beta.layer7.solutions/sentinel/reports/#subject={media_channel_id}".format(**message)}

            headers = {'content-type': 'application/json'}

            response = requests.post(url, data=json.dumps(payload), headers=headers)

            response.raise_for_status()

        
        return send_message_closure

    def send_message(self, subreddit, message):
        try:
            self.hook_table[subreddit](message)
        except requests.exceptions.HTTPError:
            pass
        except KeyError:
            pass