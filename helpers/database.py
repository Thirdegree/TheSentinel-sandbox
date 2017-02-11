import psycopg2
import configparser
import os

from .SentinelLogger import getSentinelLogger

Config = configparser.ConfigParser()
Config.read(os.path.join(os.path.dirname(__file__), "Config.ini"))


defaultun = Config.get('Database', 'Username')
defaultpass = Config.get('Database', 'Password')
defaultdbnam = 'Zion'


class Database(object):
    def __init__(self, username=defaultun, password=defaultpass):
        # Initialize the logger
        self.logger = getSentinelLogger()
        self.username = username
        self.password = password
        
        super(Database, self).__init__()

    def get_conn(self, dbname = defaultdbnam):
        conn = psycopg2.connect("host='localhost' dbname='{}' user='{}' password='{}'".format(dbname, self.username, self.password))
        self.logger.info('Initialized Database connection to {}'.format(dbname))

        return conn



class Blacklist(Database):
    def __init__(self):
        super(Blacklist, self).__init__()
        self.blacklist_conn = self.get_conn()
        with self.blacklist_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")




    def isBlacklisted(self, subreddit, media_author=None, media_channel_id=None, media_platform=None, **kwargs):
        if (not media_author) and (not media_channel_id):
            self.logger.warning('No Video Provided')
            raise RuntimeError("No video provided")

        if subreddit.lower() == 'videos':
            self.logger.debug(u'READ ONLY sub: {} | ChanID: {} | MediaPlatform: {}'.format(subreddit, media_channel_id, media_platform))
            return False
        """
        if media_author:
            self.c.execute("SELECT * FROM thesentinel_view WHERE (lower(subreddit)=lower(%s) OR subreddit='YT_Killer' OR subreddit='TheSentinelBot') AND media_author=%s AND removed!=true and blacklisted=true", (subreddit, media_author))
            try:
                fetched = self.c.fetchone()
            except psycopg2.ProgrammingError:
                return False
            if fetched:
                self.logger.info(u'Media Author Blacklisted. Sub: {} | MediaAuth: {}'.format(subreddit, media_author))
                return True
        """
        if media_channel_id:
            subquery = "SELECT id FROM subreddit WHERE subreddit_name in ('YT_Killer', 'TheSentinelBot', \'{}\')".format(subreddit)
            query = "SELECT 1 FROM sentinel_blacklist WHERE subreddit_id in ({}) AND media_channel_id=%(media_channel_id)s".format(subquery)
            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    c.execute(query, {'media_channel_id':media_channel_id})            


                    try:
                        fetched = c.fetchone()
                    except psycopg2.ProgrammingError:
                        return False            
            if fetched:
                self.logger.info(u'Media Channel Blacklisted. Sub: {} | Media_Author: {} | MediaPlatform: {}'.format(subreddit, media_author, media_platform))
                return True
        self.logger.debug(u'Channel not blacklisted. Sub: {} | ChanID: {} | MediaAuth: {}'.format(subreddit, media_channel_id, media_author))
        return False
        

    def addBlacklist(self, kwargs):
        if "media_channel_id" not in kwargs:
            self.logger.warning('No channel_id provided')
            raise RuntimeError("No channel_id provided")
        subreddit = kwargs['subreddit']
        if self.isBlacklisted(subreddit, media_channel_id=kwargs['media_channel_id']):
            self.logger.debug(u'Channel already blacklisted: ChanID: {}'.format(kwargs['media_channel_id']))
            return True
        try:
            subreddit_id = "SELECT id FROM subreddit WHERE subreddit_name='%s'"%subreddit
            media_platform_id = "SELECT id FROM media_platform WHERE platform_name='%s'"%kwargs['media_platform']
            execString1 = "INSERT INTO sentinel_blacklist (subreddit_id, media_channel_id, media_author, media_platform_id, blacklist_utc, blacklist_by) VALUES (({subreddit}), %(media_channel_id)s, %(media_author)s, ({media_platform}), now(), %(author)s)".format(subreddit=subreddit_id, media_platform=media_platform_id)
            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    c.execute(execString1, kwargs)

            self.logger.info(u'Added to database. ThingID: {thingid} | MediaChanID: {media_channel_id} | MediaAuth: {media_author}'.format(**kwargs))
            return True
        except KeyError as e:
            self.logger.error(u'Missing required parameter - {}'.format(e))
            raise KeyError(u"Missing required parameter - {}".format(e))

    def removeBlacklist(self, subreddit, author, media_author=None, media_channel_id=None, media_platform=None, **kwargs):
        if (not media_author) and (not media_channel_id):
            self.logger.warning(u'No video provided')
            raise RuntimeError("No video provided")
        if not self.isBlacklisted(subreddit, media_author, media_channel_id):
            return True
        kwargs = {
            'media_channel_id':media_channel_id,
            'author': author,
            }
        subreddit_id = "SELECT id FROM subreddit WHERE subreddit_name='%s'"%subreddit

        execString1 = "INSERT INTO sentinel_blacklist_history SELECT *, now() as unblacklist_utc, %(author)s as unblacklist_by FROM sentinel_blacklist WHERE subreddit_id=({subreddit_id}) AND media_channel_id=%(media_channel_id)s;"
        execString2 = "DELETE FROM sentinel_blacklist WHERE subreddit_id=({subreddit_id}) AND media_channel_id=%(media_channel_id)s;"

        with self.blacklist_conn as conn:
            with conn.cursor() as c:
                c.execute((execString1+execString2).format(subreddit_id=subreddit_id), kwargs)


        self.logger.info(u'Removed from Blacklist. MediaAuth: {} | ChanAuth: {}'.format(media_author, media_channel_id))
        return True

    def isProcessed(self, subreddits=None):
        with self.blacklist_conn as conn:
            with conn.cursor() as c:
                statement = b"SELECT thing_id FROM sentinel_actions"
                c.execute(statement)
                fetched = c.fetchall()

        self.logger.debug("Fetched {} items".format(len(fetched)))

        return [i[0] for i in fetched] # list of tuples -> list of thingids

    def markProcessed(self, kwargs_list):
        if kwargs_list:
            self.logger.debug("Adding {} things".format(len(kwargs_list)))
            args = []
            args2 = []
            args3 = []
            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    for item in kwargs_list:

                        statement = "(%(thing_id)s, false, now())"
                        args3.append(c.mogrify(statement, item))
                        
                        statement = "(%(thing_id)s, (SELECT id FROM subreddit where subreddit_name=%(subreddit)s), %(author)s, %(thingcreated_utc)s, %(thingedited_utc)s, %(parent_thing_id)s, %(permalink)s, %(body)s, %(title)s, %(url)s, %(flair_class)s, %(flair_text)s)"
                        args.append(c.mogrify(statement, item))

                        if not item['media_link']:
                            continue
                        
                        media_info = {
                            'authors': item['media_author'].split(','),
                            'channel_ids': item['media_channel_id'].split(','),
                            'links': item['media_link'].split(','),
                            'platforms': item['media_platform'].split(','),

                        }
                        for i in range(len(media_info['links'])):
                            try:
                                query = "(%s, %s, %s, (SELECT id FROM media_platform WHERE platform_name=%s), %s, %s)"
                                call = (item['thing_id'], 
                                        media_info['authors'][i], 
                                        media_info['channel_ids'][i], 
                                        media_info['platforms'][i], 
                                        media_info['links'][i],
                                        item['thingcreated_utc'],)

                                statement = c.mogrify(query, call)
                                args2.append(statement)
                            except IndexError: #What??
                                continue

            args1len = len(args)
            args2len = len(args2)

            args = b",".join(args)
            args2 = b",".join(args2)
            args3 = b",".join(args3)
            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    if args:
                        execString = b"INSERT INTO reddit_thing (thing_id, subreddit_id, author, created_utc, edited_utc, parent_thing_id, permalink, thing_data, thing_title, link_url, flair_class, flair_text) VALUES " + args + b" ON CONFLICT DO NOTHING"
                        c.execute(execString)

            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    if args2:
                        execString2 = b"INSERT INTO media_info (thing_id, media_author, media_channel_id, media_platform_id, media_url, last_seen_utc) VALUES " + args2 + b" ON CONFLICT DO NOTHING"
                        c.execute(execString2)

            with self.blacklist_conn as conn:
                with conn.cursor() as c:
                    if args3:
                        execString3 = b"INSERT INTO sentinel_actions (thing_id, removed, action_utc) VALUES " + args3 + b" ON CONFLICT DO NOTHING"
                        c.execute(execString3)
            #self.logger.warning("execString: {}".format(execString))
            
            
            
            self.logger.debug("Added {} items to the reddit_thing database, and {} items to the media_info database.".format(args1len, args2len))

    def markActioned(self, thingid):
        with self.blacklist_conn as conn:
            with conn.cursor() as c:
                c.execute("UPDATE sentinel_actions SET removed=true, action_utc=now() where thing_id=%s and removed=false", (thingid,))



    """
    def next_value(self):
        with self.conn:
            with self.conn.cursor("next_value") as c:
                c.execute("SELECT id FROM thing ORDER BY id DESC LIMIT 1")
                result = c.fetchone()
        return result[0]+1
    """



class SlackHooks(Database):
    def __init__(self):
        super(SlackHooks, self).__init__()
        self.slackhooks_conn = self.get_conn()
        with self.slackhooks_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")

    def getHooks(self, slackTeam=None, subreddit=None):
        with self.slackhooks_conn as conn:
            with conn.cursor() as c:

                if (not slackTeam) and (not subreddit):
                    c.execute("SELECT srname, webhook_url, slack_channel FROM tsb_slackhooks")
                    self.logger.debug(u'Fetched all slackHooks')
                else:
                    c.execute("SELECT srname, webhook_url, slack_channel FROM tsb_slackhooks WHERE slack_team=%s OR srname=%s", (slackTeam, subreddit))
                    self.logger.debug(u'Fetched slackHook for /r/{} | SlackTeam: {}'.format(subreddit, slackTeam))
                hooks = c.fetchall()
        return hooks

    def addHook(self, subreddit, channel, hookURL, slackTeam):
        with self.slackhooks_conn as conn:
            with conn.cursor() as c:

                c.execute("INSERT INTO tsb_slackhooks (srname, webhook_url, slack_channel, slack_team) VALUES (%s, %s, %s, %s)", (subreddit, hookURL, channel, slackTeam))
        self.logger.debug(u'Hook added for /r/{} | SlackTeam: {}'.format(subreddit, slackTeam))

    def removeHook(self, slackTeam=None, subreddit=None):
        with self.slackhooks_conn as conn:
            with conn.cursor() as c:

                if subreddit and slackTeam is None:
                    c.execute("DELETE FROM tsb_slackhooks WHERE srname=%s", (subreddit,))
                    self.logger.debug(u'Removed hook for /r/{}'.format(subreddit))
                elif slackTeam and subreddit is None:
                    c.execute("DELETE FROM tsb_slackhooks WHERE slack_team=%s", (slackTeam,))
                    self.logger.debug(u'Removed hook for SlackTeam: {}'.format(slackTeam))
                else:
                    self.logger.warning(u'Please provide either a Subreddit or a Slack Team, not both')
                    raise RuntimeError("Please provide either a Subreddit or a Slack Team, not both")

class NSA(Database):
    def __init__(self):
        super(NSA, self).__init__()
        self.nsa_conn = self.get_conn(dbname='TheTraveler')
        with self.nsa_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")


    def addUsers(self, kwargs_list):
        with self.nsa_conn as conn:
            with conn.cursor() as c:
                if kwargs_list:
                    self.logger.debug("Adding {} users".format(len(kwargs_list)))

                    args = ",".join([c.mogrify("(%(author_id)s, %(author)s, %(permalink)s, EXTRACT(EPOCH from now()), %(thingcreated_utc)s, %(content_creator)s)", x) for x in kwargs_list])
                    execString = "INSERT INTO users (authorid, author, permalink, current_utc, authorcreated_utc, iscontentcreator) VALUES " +  args + " ON CONFLICT DO NOTHING"
                    c.execute(execString)
                    self.logger.debug("Added {} users to the database.".format(len(kwargs_list)))

    def knownUsers(self):
        newcur = self.nsa_conn.cursor('knownUsers')
        execString = "SELECT authorid FROM users"
        newcur.execute(execString)
        fetched = newcur.fetchall()
        self.nsa_conn.commit()
        newcur.close()
        self.nsa_conn.commit()
        self.logger.debug("Fetched {} users".format(len(fetched)))
        return [i[0] for i in fetched] # list of tuples -> list of thingids

class Utility(Database):
    def __init__(self):
        super(Utility, self).__init__()
        self.utility_conn = self.get_conn()
        with self.utility_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")

    def add_subreddit(self, subreddit, botname, subscribers):
        execString1 = "INSERT INTO subreddit (subreddit_name, sentinel_enabled, redditbot_name, subreddit_subscribers) VALUES (%s, %s, %s, %s)"
        updateString = "UPDATE subreddit SET sentinel_enabled=TRUE, redditbot_name=%s, subreddit_subscribers=%s WHERE subreddit_name=%s"
        with self.utility_conn as conn:
            with conn.cursor('add_subreddit_get') as c:
                c.execute("SELECT * FROM subreddit WHERE subreddit_name=%s", (subreddit,))
                fetched = c.fetchone()
        with self.utility_conn as conn:
            with conn.cursor() as c:
                if fetched:
                    c.execute(updateString, (botname, subscribers, subreddit))
                else:
                    c.execute(execString1, (subreddit, True, botname, subscribers))


    def remove_subreddit(self, subreddit):
        execString1 = "UPDATE subreddit SET sentinel_enabled=FALSE, dirtbag_enabled=FALSE WHERE subreddit_name=%s"
        with self.utility_conn as conn:
            with conn.cursor() as c:
                c.execute(execString1, (subreddit,))


class ModloggerDB(Database):
    def __init__(self):
        super(ModloggerDB, self).__init__()
        self.modlogger_conn = self.get_conn()
        with self.modlogger_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")

    def get_subs_enabled(self):
        execString1 = "SELECT subreddit_name FROM subreddit WHERE modlog_enabled=true"
        with self.modlogger_conn as conn:
            with conn.cursor('get_subs_enabled') as c:

                c.execute(execString1)
                fetched = c.fetchall()
        if fetched:
            return [i[0] for i in fetched]
        return []

    def get_last_seen(self, limit=1000):
        execString1 = "SELECT modactionid from modlog limit " + str(limit)
        with self.modlogger_conn as conn:
            with conn.cursor('get_last_seen') as c:

                c.execute(execString1)
                fetched = c.fetchall()
        if fetched:
            self.logger.debug("Found %s items"%len(fetched))
            return [i[0] for i in fetched]
        self.logger.debug("Found 0 items")
        return []

    def log_items(self, kwargs_list):
        try:
            with self.modlogger_conn as conn:
                with conn.cursor() as c:
                    if kwargs_list:
                        args = b",".join([c.mogrify("(%(thing_id)s, %(mod_name)s, %(action)s, %(action_reason)s, %(thingcreated_utc)s, %(modaction_id)s, (SELECT id FROM subreddit WHERE subreddit_name=%(subreddit)s))", x) for x in kwargs_list])

                        execString1 = b'INSERT INTO modlog (thing_id, mod, action, actionreason, action_utc, modactionid, subreddit_id) VALUES ' + args + b" ON CONFLICT (modactionid) DO UPDATE SET subreddit_id=excluded.subreddit_id WHERE modlog.modactionid=excluded.modactionid"
                        c.execute(execString1)
                        self.logger.info("Added {} items to modLogger database.".format(len(kwargs_list)))
        except Exception as e:
            self.logger.error("Unable to log items")
        


    def is_logged(self, modActionID):
        with self.modlogger_conn as conn:
            with conn.cursor('is_logged') as c:
                c.execute('SELECT * FROM modlog WHERE modactionid=%s', (modActionID,))
                return bool(c.fetchone())


class oAuthDatabase(Database):
    def __init__(self):
        super(oAuthDatabase, self).__init__()
        self.oAuth_conn = self.get_conn(dbname='TheTraveler')
        with self.oAuth_conn as conn:
            with conn.cursor() as c:
                c.execute("SET CLIENT_ENCODING TO 'UTF8';")


    def get_accounts(self, id):
        with self.oAuth_conn as conn:
            with conn.cursor('get_accounts') as c:
                c.execute("SELECT app_id, app_secret, username, password FROM oauth_data WHERE agent_of=%s", (id,))
                self.logger.debug(u'Retreived oAuth Credentials for Username: {}'.format(id))
                return c.fetchall()

class TheTraveler(NSA):
    def __init__(self):
        super(TheTraveler, self).__init__()


class Zion(SlackHooks, Blacklist):
    def __init__(self):
        super(Zion, self).__init__()

