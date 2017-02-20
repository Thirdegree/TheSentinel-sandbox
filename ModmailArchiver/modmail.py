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
                try:
                    for reply in mail.replies['data']['children']:
                        if limit and not self.db.is_logged(reply['data']['name']):
                            reply_dict = {
                                "thing_id": reply['data']['name'],
                                "message_root_thing_id": reply['data']['first_message_name'],
                                "message_from": reply['data']['author'],
                                "message_to": reply['data']['dest'].replace("#", "r/") if reply['data']['dest'].startswith("#") else reply['data']['dest'],
                                "created_utc": datetime.utcfromtimestamp(reply['data']['created_utc']),
                                "subject": reply['data']['subject'],
                                "body": reply['data']['body'],
                                "parent_thing_id": reply['data']['parent_id'],
                                "subreddit": reply['data']['subreddit']
                            }
                            arg_dicts.append(reply_dict)
                except TypeError:
                    # No replies to the message, so just pass along
                    pass
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

