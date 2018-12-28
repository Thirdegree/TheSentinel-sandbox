import pytest
from pytest_mock import mocker
from the_sentinel.apis.google.youtube import User
import logins

@pytest.fixture
def user():
    return User(id='thingy')

def test_resp(mocker, user):
    mock_get = mocker.patch.object(user, 'get')
    mock_resp = mock_get.return_value
    user.resp
    mock_resp.raise_for_status.assert_called()
    mock_get.assert_called_with('', params={'forUsername': user.id})




