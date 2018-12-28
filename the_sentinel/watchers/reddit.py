"""
Classes dedicated to watching and gathering posts and comments from reddit
"""
from typing import Union, Callable, Any, Optional, List, TYPE_CHECKING
import asyncio
import praw
# types
# pylint: disable=invalid-name
StreamTarget = Callable[..., praw.models.ListingGenerator]
if TYPE_CHECKING: # pragma: no cover
    RedditQueue = asyncio.Queue[praw.models.reddit.base.RedditBase]
else:
    RedditQueue = asyncio.Queue
# pylint: enable=invalid-name

class RedditWatcher:
    """
    Aggregates and manages SubredditWatcher instances
    """
    def __init__(self,
                 reddit: praw.Reddit,
                 watchers: Optional[List['SubredditWatcher']] = None):
        self.reddit = reddit
        self._outqueue: RedditQueue
        self._outqueue = asyncio.Queue()

        if watchers is None:
            watchers = []
        self.watchers: List[SubredditWatcher]
        self.watchers = watchers

    def watch(self, pause_after: int = -1, **kwargs: Any):
        """
        Creates tasks for all watcher instances, passing down stream arguments
        """
        for watcher in self.watchers:
            asyncio.get_event_loop().create_task(
                watcher.watch(pause_after=pause_after, **kwargs)
                )

    def add_watcher(self, subreddit: Union[praw.models.Subreddit, str]):
        """
        Adds a watcher
        """
        watcher = SubredditWatcher(self.reddit, subreddit, self._outqueue)
        if watcher in self.watchers:
            raise RuntimeError(
                "You may not have multiple watchers for a single subreddit")
        self.watchers.append(watcher)

    def kill(self): # pragma: no cover
        """
        Cleanly kill all watchers
        """
        for watcher in self.watchers:
            watcher.kill()

    async def get(self): # pragma: no cover
        """
        Trivial wrapper for asyncio.Queue.get
        """
        return await self._outqueue.get()

class SubredditWatcher:
    """
    Gathers comments, submissions (any RedditBase derived classes) from a
    single subreddit.
    """
    def __init__(self,
                 reddit: praw.Reddit,
                 subreddit: Union[praw.models.Subreddit, str],
                 queue: Optional[RedditQueue] = None):
        self.reddit = reddit

        if queue is None:
            queue = asyncio.Queue()
        self._outqueue = queue

        if isinstance(subreddit, str):
            self.subreddit = self.reddit.subreddit(subreddit)
        else: # pragma: no cover
            self.subreddit = subreddit

        self._streams = [self.subreddit.stream.comments,
                         self.subreddit.stream.submissions]

        self.watching: List[StreamTarget]
        self.watching = []
        self._kill = False

    async def watch(self,
                    stream_target: Optional[StreamTarget] = None,
                    pause_after: int = -1,
                    **kwargs: Any):
        """
        Takes a subreddit stream, and asyncronously puts returned items there
        into the _outqueue

        If no stream_target is provided, use self._streams which is by default
        comments and submissions
        """
        if stream_target is None:
            for stream in self._streams:
                asyncio.get_event_loop().create_task(
                    self.watch(stream, pause_after=pause_after, **kwargs))
            return

        if stream_target in self.watching:
            raise RuntimeError("You may only watch a given stream one time")
        self.watching.append(stream_target)
        for item in stream_target(pause_after=pause_after, **kwargs):
            if self._kill:
                break
            if item is None:
                await asyncio.sleep(0)
                continue
            await self._outqueue.put(item)

    def kill(self): # pragma: no cover
        """
        Cleanly kill all watched streams
        """
        self._kill = True

    async def get(self): # pragma: no cover
        """
        Trivial wrapper for asyncio.Queue.get
        """
        return await self._outqueue.get()
