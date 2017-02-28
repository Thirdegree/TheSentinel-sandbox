from ..helpers import getSentinelLogger, ModloggerDB
from datetime import datetime


class ModLogger(object):
    def __init__(self, r, subs): #subs is a list of strings
        self.r = r
        self.me = self.r.user.me()

        self.logger = getSentinelLogger()
        self.db = ModloggerDB()
        self.subs = subs

    @property
    def opt_ins(self):
        return [i.lower() for i in self.db.get_subs_enabled()]

    @property
    def subs_intersec(self):
        #return list(set([i.lower() for i in self.subs]) & set(self.opt_ins))
        return self.subs

    @property
    def modLogMulti(self):
        subs_intersec = self.subs_intersec
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
                    "author_name": None if len(item.target_author) == 0 else item.target_author,
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

    def __str__(self):
        return  "Modlogger ({})".format(self.me)


    def log(self, limit=100, author=None):
        if (not limit):
            self.logger.info("{} | Force Modlog History started for {}".format(self.me, self.subs_intersec))
        arg_dicts = self.gather_items(limit)
        logged = self.db.log_items(arg_dicts)
        if len(arg_dicts) > 5:
            self.logger.info("{} | Added {} items to modlog".format(self, len(arg_dicts)))
        self.logger.debug("{} | Added {} items to modlog".format(self, len(arg_dicts)))
        if (not limit) and self.subs_intersec:
            self.logger.info("{} | Force Modlog History complete for {}, {} updated/inserted".format(self, self.subs_intersec, logged))
            if author:
                self.r.redditor("Layer7Solutions").message('Force Modlog History Results', 'Finished for {}, {} updated/inserted'.format(self.subs_intersec, logged))
        elif logged:
            self.logger.info('{me} | Processed {amount} Modlog things'.format(me=self, amount=logged))

