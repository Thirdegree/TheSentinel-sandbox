from ..helpers import getSentinelLogger, ModloggerDB
from datetime import datetime


class ModLogger(object):
    def __init__(self, r, subs): #subs is a list of strings
        self.r = r
        self.logger = getSentinelLogger()
        self.db = ModloggerDB()
        self.subs = subs

    @property
    def opt_ins(self):
        return [i.lower() for i in self.db.get_subs_enabled()]

    @property
    def modLogMulti(self):
        subs_intersec = list(set([i.lower() for i in self.subs]) & set(self.opt_ins))
        try:
            return self.r.subreddit("+".join(subs_intersec))
        except TypeError:
            return None

    def gather_items(self, limit):
        arg_dicts = []
        last_seen = self.db.get_last_seen()
        if self.modLogMulti:
            log_generator = self.modLogMulti.mod.log(limit=limit)
        else:
            return
        try:
            #item = log_generator.next()

            for item in log_generator:
                if limit and self.db.is_logged(item.id):
                    continue
                arg_dict = {
                    "description": item.description,
                    "thing_id": item.target_fullname,
                    "mod_name": str(item.mod),
                    "author_name": str(item.target_author),
                    "action": item.action,
                    "action_reason": item.details,
                    "permalink": item.target_permalink,
                    "thingcreated_utc": datetime.utcfromtimestamp(item.created_utc),
                    "subreddit": str(item.subreddit),
                    "modaction_id": item.id,
                    "title": item.target_title
                }

                arg_dicts.append(arg_dict)
                item = log_generator.next()

        except StopIteration:
            pass

        return arg_dicts

    def log(self, limit=100):
        arg_dicts = self.gather_items(limit)
        self.db.log_items(arg_dicts)
        if not limit:
            self.r.redditor('thirdegree').message('force modlog history', 'Finished for {}'.format(self.subs))