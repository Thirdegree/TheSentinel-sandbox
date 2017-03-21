"""TheSentinel constants."""

__app_name__    = 'TheSentinelBot'
__description__ = 'Anti-Media spam'
__author__      = 'Thirdegree, D0cR3d'
__version__     = '1.2.1'



DIRTBAG_API_PATH = {
    'VIDEO_ANALYSIS':   'https://videosdirtbag.snoonotes.com/api/Analysis/videos'
    }


WEBSYNC_API_PATH = {
    'tsbaccept':                "https://beta.layer7.solutions/admin/websync?type=tsbaccept&subreddit={subreddit}",
    'addmoderator':             "https://beta.layer7.solutions/admin/websync?type=addmoderator&subreddit={subreddit}&moderator={target}",
    'acceptmoderatorinvite':    "https://beta.layer7.solutions/admin/websync?type=acceptmoderatorinvite&subreddit={subreddit}&moderator={mod}",
    'removemoderator':          "https://beta.layer7.solutions/admin/websync?type=removemoderator&subreddit={subreddit}&moderator={target}",
    'setpermissions':           "https://beta.layer7.solutions/admin/websync?type=setpermissions&subreddit={subreddit}&moderator={target}&new_state={new_state}",
    }