"""TheSentinel constants."""

__app_name__    = 'TheSentinelBot'
__description__ = 'Anti-Media spam'
__author__      = 'Thirdegree, D0cR3d'
__version__     = '1.2.1'



DIRTBAG_API_PATH = {
    'VIDEO_ANALYSIS':   'https://videosdirtbag.snoonotes.com/api/Analysis/videos'
    }


WEBSYNC_API_PATH = {
    'tsbaccept':                "http://beta.layer7.solutions/admin/resync?type=tsbaccept&subreddit={subreddit}",
    'addmoderator':             "http://beta.layer7.solutions/admin/resync?type=addmoderator&subreddit={subreddit}&moderator={target}",
    'acceptmoderatorinvite':    "http://beta.layer7.solutions/admin/resync?type=acceptmoderatorinvite&subreddit={subreddit}&moderator={mod}",
    'removemoderator':          "http://beta.layer7.solutions/admin/resync?type=removemoderator&subreddit={subreddit}&moderator={target}",
    'setpermissions':           "http://beta.layer7.solutions/admin/resync?type=setpermissions&subreddit={subreddit}&moderator={target}&new_state={new_state}",
    }