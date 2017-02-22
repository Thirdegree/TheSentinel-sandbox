from datetime import datetime, timedelta
from ...helpers import FlairbotDB


class Flairbot(object):
    def __init__(self, r, subs):
        self.r = r
        self.me = self.r.user.me()
        self.db = FlairbotDB()
        self.subs = subs

    @property
    def opt_ins(self):
        return [i.lower() for i in self.db.get_subs_enabled()]

    @property
    def subs_intersec(self):
        return list(set([i.lower() for i in self.subs]) & set(self.opt_ins))

    @property
    def flairbotmulti(self):
        subs_intersec = self.subs_intersec
        try:
            return self.r.subreddit("+".join(subs_intersec))
        except TypeError:
            return None

    def get_preferences(self):
        return self.db.get_preferences(self.subs_intersec)

    def is_remove_eligable(self, thing):
        time_posted = datetime.utcfromtimestamp(thing.created_utc)
        sub_prefs = self.preferences[str(thing.subreddit)]
        delta = timedelta(minutes=sub_prefs['time_delay'])

        if thing.approved_by: #has already been approved 
            return False

        if thing.num_reports > 0: # has reports
            return False

        return time_posted + delta < datetime.utcnow()

    def is_approve_eligable(self, thing):

        sub_prefs = self.preferences[str(thing.subreddit)]

        if not sub_prefs['approve_posts']: # prefs set to not approve
            return False

        if thing.approved_by: # has already been approved 
            return False

        if thing.num_reports > 0: # has reports
            return False

        return (not thing.banned_by) or (thing.banned_by == str(self.me) and not thing.fullname in self.sentinel_removed) # not removed, or removed by agent but not because sentinel

    def sentinel_removed(self):
        return self.db.get_sentinel_removed()
            

    def has_flair(self, thing):
        return  thing.link_flair_text or thing.link_flair_css_class




    def check_flairs(self):
