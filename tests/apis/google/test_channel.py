from the_sentinel.apis.google.youtube import Channel
import logins
import pytest

@pytest.fixture
def channel():
    return Channel(id='UCq6aw03lNILzV96UvEAASfQ')

@pytest.mark.parametrize('query,params', [
    ('this is a query', {'param1':'val1'}),
    ('this is a query', None)
    ])
def test_videos(mocker, base_youtube, channel, query, params):
    mock_search = mocker.patch(
            'the_sentinel.apis.google.youtube.Youtube.search')
    # output is covered by test_search in test_youtube.py
    mock_search.return_value = []

    vids = channel.videos(query=query, params=params)
    if params is None:
        params = {}
    params.update({'type': 'video',
                   'channelId': channel.id})
    mock_search.assert_called_with(query=query,
                                   params=params)
    assert channel.videos() == []
