import pytest
from pytest_mock import mocker
from the_sentinel.apis.google.youtube import Playlist
import logins

@pytest.fixture
def playlist():
    return Playlist(id='thingy')

@pytest.mark.parametrize('query,params', [
    ('this is a query', {'param1':'val1'}),
    ('this is a query', None)
    ])
def test_videos(mocker, base_youtube, playlist, query, params):
    mock_search = mocker.patch(
            'the_sentinel.apis.google.youtube.Youtube.search')
    # output is covered by test_search in test_youtube.py
    mock_search.return_value = []

    vids = playlist.videos(query=query, params=params)
    if params is None:
        params = {}
    params.update({'type': 'video',
                   'playlistId': playlist.id})
    mock_search.assert_called_with(endpoint='playlistItems',
                                   query=query,
                                   params=params)
    assert playlist.videos() == []
