from ..helpers import getSentinelLogger, ModloggerDB


class ModLogger(object):
    def __init__(self, r, subs): #subs is a list of strings
        self.r = r
        self.logger = getSentinelLogger()
        self.db = ModloggerDB()
        self.opt_ins = self.db.get_subs_enabled()
        subs_intersec = list(set(subs) & set(self.opt_ins))
        self.modLogMulti = self.r.subreddit("+".join(subs_intersec))


    def gather_items(self):
        arg_dicts = []
        last_seen = self.db.get_last_seen()
        log_generator = self.modLogMulti.mod.log()
        try:
            item = log_generator.next()

            while item not in last_seen:
                arg_dict = {
                    "thing_id": item.target_fullname,
                    "mod_name": str(item.mod),
                    "author_name": str(item.target_author),
                    "action": item.action,
                    "action_reason": item.details,
                    "permalink": item.target_permalink,
                    "thingcreated_utc": item.created_utc,
                    "subreddit": str(item.subreddit),
                    "modaction_id": item.id,
                    "title": item.target_title
                }

                arg_dicts.append(arg_dict)
                item = log_generator.next()

        except StopIteration:
            pass

        return arg_dicts

    def log(self):
        arg_dicts = self.gather_items()
        self.db.log_items(arg_dicts)