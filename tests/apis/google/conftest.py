from the_sentinel.apis.google.youtube import Youtube, Channel, \
                                             Video, Playlist, User
import pytest
import logins
from mock import MagicMock
@pytest.fixture
def base_youtube():
    """
    Youtube object with id='5'
    """
    # yotube doesn't need an id, but it doesn't hur it either
    return Youtube(key=logins.GOOGLE['youtube'], id='5')

@pytest.fixture
def mock_request():
    mock_request = MagicMock(name='mock_request')
    mock_resp = MagicMock(name='mock_resp')
    mock_request.return_value = mock_resp
    return mock_request

