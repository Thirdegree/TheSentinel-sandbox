"""
Collection of tools, scripts, and bots related to moderation and spam killing
"""
import praw
# NOTE: logins.praw is a dict with the required info for my personal account.
#       Replace with arguments before sending out

from .watchers import RedditWatcher
