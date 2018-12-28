import pytest
from pytest_mock import mocker
from mock import call, MagicMock
from the_sentinel.watchers.reddit import SubredditWatcher, RedditWatcher
import logins
import praw
import asyncio
from asynctest import CoroutineMock

def reddit():
    return praw.Reddit(**logins.PRAW)

@pytest.fixture
def subwatcher():
    # personall testing subreddit, there's almost always something testable
    # there
    return SubredditWatcher(reddit=reddit(), subreddit='thirdegree')

@pytest.fixture
def redditwatcher():
    return RedditWatcher(reddit=reddit())

@pytest.mark.asyncio
async def test_subwatcher_watch_callback(mocker, subwatcher):
    outqueue_mock = mocker.patch.object(subwatcher, '_outqueue',
                                        new=CoroutineMock(name='put_mock'))
    outqueue_mock.put = CoroutineMock()
    stream_target_mock = mocker.MagicMock(name='stream_target')
    stream_target_mock.return_value = iter(
           ['a', 'b', None, 'c'])

    callback = MagicMock(name='callback')
    await subwatcher.watch(item_callback=callback,
                           pause_after=-1,
                           stream_target=stream_target_mock)

    stream_target_mock.assert_called_with(pause_after=-1)
    callback.assert_has_calls([call('a'), call('b'), call('c')])

@pytest.mark.asyncio
async def test_subwatcher_watch(mocker, subwatcher):
    outqueue_mock = mocker.patch.object(subwatcher, '_outqueue',
                                        new=CoroutineMock(name='put_mock'))
    outqueue_mock.put = CoroutineMock()
    stream_target_mock = mocker.MagicMock(name='stream_target')
    stream_target_mock.return_value = iter(
           ['a', 'b', None, 'c'])
    await subwatcher.watch(pause_after=-1, stream_target=stream_target_mock)

    stream_target_mock.assert_called_with(pause_after=-1)
    outqueue_mock.put.assert_has_calls([call('a'), call('b'), call('c')])

@pytest.mark.asyncio
async def test_subwatcher_watch_default(mocker, subwatcher):
    outqueue_mock = mocker.patch.object(subwatcher, '_outqueue',
                                        new=CoroutineMock(name='put_mock'))
    outqueue_mock.put = CoroutineMock()
    stream_target_mock = mocker.MagicMock(name='stream_target')
    stream_target_mock.return_value = iter(
           ['a', 'b', None, 'c'])
    mocker.patch.object(subwatcher, '_streams', new=[stream_target_mock,])
    await subwatcher.watch(pause_after=-1)

    # we need to gather everything EXCEPT the current task or we create
    # a deadlock
    # took me like an hour to figure that one out. I blame the angry orchard.
    pending = asyncio.Task.all_tasks()
    current = asyncio.Task.current_task()
    await asyncio.gather(*(pending - {current}))

    stream_target_mock.assert_called_with(pause_after=-1)
    outqueue_mock.put.assert_has_calls([call('a'), call('b'), call('c')])

def test_redditwatcher_watch(mocker, redditwatcher):
    mockwatcher = MagicMock(name='mock_watcher')
    redditwatcher.watchers = [mockwatcher]
    redditwatcher.watch(pause_after=-1)
    mockwatcher.watch.assert_called_with(pause_after=-1)

def test_add_watcher(mocker, redditwatcher):
    subredditwatcher_mock = mocker.patch(
            'the_sentinel.watchers.reddit.SubredditWatcher')
    redditwatcher.add_watcher('fake_subreddit')
    subredditwatcher_mock.assert_called_with(redditwatcher.reddit,
                                             'fake_subreddit',
                                             redditwatcher._outqueue)
    with pytest.raises(RuntimeError):
        redditwatcher.add_watcher('fake_subreddit')


