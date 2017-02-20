from ..helpers import getSentinelLogger, ModmailArchiverDB
from datetime import datetime


class ModmailArchiver(object):
    def __init__(self, r, subs): #subs is a list of strings
        self.r = r
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
            return self.r.subreddit("+".join(subs_intersec))
        except TypeError:
            return None

    def gather_items(self, limit=200):
        arg_dicts = []
        last_seen = self.db.get_last_seen()
        if self.modMailMulti:
            mail_generator = self.modMailMulti.mod.inbox(limit=limit)
        else:
            return
        try:
            for mail in mail_generator:
                if limit and self.db.is_logged(mail.id):
                    continue
                #['author', 'block', 'body', 'body_html', 'context', 'created', 'created_utc', 'dest', 'distinguished', 'first_message', 'first_message_name', 'fullname', 'id', 'mark_read', 'mark_unread', 'mute', 'name', 'new', 'parent_id', 'parse', 'replies', 'reply', 'subject', 'subreddit', 'subreddit_name_prefixed', 'unmute', 'was_comment']
                arg_dict = {
                    "thing_id": mail.fullname,
                    "message_root_thing_id": mail.first_message_name,
                    "message_from": str(mail.author),
                    "message_to": mail.dest.replace("#", "r/") if mail.dest.startswith("#") else mail.dest,
                    "created_utc": datetime.utcfromtimestamp(mail.created_utc),
                    "subject": mail.subject,
                    "body": mail.body,
                    "parent_thing_id": mail.parent_id,
                    "subreddit": mail.subreddit
                }
                arg_dicts.append(arg_dict)

                for reply in mail.replies:
                    reply_dict = {
                        "thing_id": reply.fullname,
                        "message_root_thing_id": reply.first_message_name,
                        "message_from": str(reply.author),
                        "message_to": reply.dest.replace("#", "r/") if reply.dest.startswith("#") else reply.dest,
                        "created_utc": datetime.utcfromtimestamp(reply.created_utc),
                        "subject": reply.subject,
                        "body": reply.body,
                        "parent_thing_id": reply.parent_id,
                        "subreddit": reply.subreddit
                    }
                    arg_dicts.append(reply_dict)

                mail = mail_generator.next()

        except StopIteration:
            pass

        return arg_dicts

    def log(self, limit=100):
        arg_dicts = self.gather_items(limit)
        self.db.log_items(arg_dicts)
        if not limit:
            self.r.redditor('thirdegree').message('force modlog history', 'Finished for {}'.format(self.subs))

