from ..helpers import getSentinelLogger, ModmailArchiverDB
from datetime import datetime
import prawcore

class ModmailArchiver(object):
    def __init__(self, r, subs): #subs is a list of strings
        self.r = r
        self.me = str(self.r.user.me())
        self.logger = getSentinelLogger()
        self.db = ModmailArchiverDB()
        self.subs = subs

    @property
    def opt_ins(self):
        return [i.lower() for i in self.db.get_subs_enabled()]

    @property
    def modMailMulti(self):
        subs_intersec = list(set([i.lower() for i in self.subs]) & set(self.opt_ins))
        try:
            subs_with_mail_perms = []
            for sub in subs_intersec:
                for mod in self.r.subreddit(sub).moderator():
                    if mod == 'TheSentinelBot' and ('mail' in mod.mod_permissions or 'all' in mod.mod_permissions):
                        subs_with_mail_perms.append(sub)

            return self.r.subreddit("+".join(subs_with_mail_perms))
        except TypeError:
            return None

    def gather_items(self, limit):
        arg_dicts = []
        if self.modMailMulti:
            mail_generator = self.modMailMulti.mod.inbox(limit=limit)
        else:
            return
        try:
            for mail in mail_generator:
                if limit and not self.db.is_logged(mail.fullname):
                    arg_dict = {
                        "thing_id": mail.fullname,
                        "message_root_thing_id": mail.first_message_name,
                        "message_from": str(mail.author),
                        "message_to": str(mail.dest).replace("#", "r/") if str(mail.dest).startswith("#") else str(mail.dest),
                        "created_utc": datetime.utcfromtimestamp(mail.created_utc),
                        "subject": mail.subject,
                        "body": mail.body,
                        "parent_thing_id": mail.parent_id,
                        "subreddit": str(mail.subreddit)
                    }
                    arg_dicts.append(arg_dict)
                for reply in mail.replies:
                    if not self.db.is_logged(reply.fullname):
                        reply_dict = {
                            "thing_id": reply.fullname,
                            "message_root_thing_id": reply.first_message_name,
                            "message_from": str(reply.author),
                            "message_to": str(reply.dest).replace("#", "r/") if str(reply.dest).startswith("#") else str(reply.dest),
                            "created_utc": datetime.utcfromtimestamp(reply.created_utc),
                            "subject": reply.subject,
                            "body": reply.body,
                            "parent_thing_id": reply.parent_id,
                            "subreddit": str(reply.subreddit)
                        }
                        arg_dicts.append(reply_dict)
                mail = mail_generator.next()

        except StopIteration:
            pass
        except prawcore.exceptions.Forbidden:
            self.logger.warning('Missing `mail` permission')

        return arg_dicts

    def log(self, limit=100):
        arg_dicts = self.gather_items(limit)
        self.db.log_items(arg_dicts)
        #if not limit:
        #    self.r.redditor('thirdegree').message('force modmail history', 'Finished for {}'.format(self.subs))

