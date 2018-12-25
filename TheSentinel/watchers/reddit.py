from typing import Union, Callable, Any, Optional, List
import asyncio
import praw

StreamTarget = Callable[..., praw.models.ListingGenerator]

class SubredditWatcher:
    def __init__(self,
                 reddit: praw.Reddit,
                 subreddit: Union[praw.models.Subreddit, str]):
        self.reddit = reddit
        self._outqueue: asyncio.Queue[praw.models.reddit.base.RedditBase]
        self._outqueue = asyncio.Queue()
        if isinstance(subreddit, str):
            self.subreddit = self.reddit.subreddit(subreddit)
        else:
            self.subreddit = subreddit

        self._streams = [self.subreddit.stream.comments,
                         self.subreddit.stream.submissions]

        self.watching: List[StreamTarget]
        self.watching = []

    async def watch(self,
                    stream_target: Optional[StreamTarget] = None,
                    pause_after: int =-1,
                    *args: Any, **kwargs: Any):
        """
        Takes a subreddit stream, and asyncronously puts returned items there
        into the _outqueue

        If no stream_target is provided, use self._streams which is by default
        comments and submissions
        """

        if stream_target is None:
            for stream in self._streams:
                asyncio.get_event_loop().create_task(self.watch(stream))
            return

        if stream_target in self.watching:
            raise RuntimeError("You may only watch a given stream one time")
        self.watching.append(stream_target)

        for item in stream_target(pause_after=pause_after, *args, **kwargs):
            if item is None:
                await asyncio.sleep(0)
                continue
            await self._outqueue.put(item)




