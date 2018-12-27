import pytest
import sys
from mock import MagicMock
from pytest_mock import mocker
import the_sentinel
from the_sentinel.apis.google.youtube import Youtube, Channel, \
                                             Video, Playlist, User
import logins

    # example mock
    # mock_rep = mocker.patch('the_sentinel.apis.google.youtube.Youtube.resp')
    # mock_rep.return_value = 'hi there'
    # y = Youtube(key=logins.GOOGLE['youtube'])
    # assert y.resp() == 'hi there'

@pytest.fixture
def base_youtube():
    # yotube doesn't need an id, but it doesn't hur it either
    return Youtube(key=logins.GOOGLE['youtube'], id='5')

@pytest.fixture
def mock_request():
    mock_request = MagicMock(name='mock_request')
    mock_resp = MagicMock(name='mock_resp', return_value=5)
    mock_request.return_value = mock_resp
    return mock_request

def test_resp(mocker, base_youtube, mock_request):
    mocker.patch.object(Youtube, 'request',
                        new=mock_request)
    mock_resp = mock_request()
    base_youtube.resp
    mock_request.assert_called_with('GET', '',
                                    allow_redirects=True, params={'id': '5'})
    mock_resp.raise_for_status.assert_called()
    assert base_youtube._resp == mock_resp



@pytest.mark.parametrize("video,channel", [
    # https://www.youtube.com/watch?v=ZsxQxS0AdBY
    ('ZsxQxS0AdBY', 'UCBJycsmduvYEL83R_U4JriQ') ,
    # https://www.youtube.com/watch?v=FyUcXeO16XM&t=27s
    ('FyUcXeO16XM', 'UCm9K6rby98W8JigLoZOh6FQ'),
    ])
def test_video_to_channel(base_youtube, video, channel):
    vid = Video(id=video)
    channel_expected = Channel(channel)
    assert vid.channel == channel_expected
