import pytest
from mock import MagicMock
from pytest_mock import mocker
from the_sentinel.apis.google.youtube import Youtube
from the_sentinel.apis.google.youtube.youtube import KIND_MAPPING
import logins


def test_resp(mocker, base_youtube, mock_request):
    mocker.patch.object(Youtube, 'request',
                        new=mock_request)
    mock_resp = mock_request()
    base_youtube.resp
    mock_request.assert_called_with('GET', '',
                                    allow_redirects=True, params={'id': '5'})
    mock_resp.raise_for_status.assert_called()
    assert base_youtube._resp == mock_resp

def test_json(mocker, base_youtube, mock_request):
    mock_resp = mock_request()
    mocker.patch.object(Youtube, 'resp', new=mock_resp)
    mock_json = MagicMock(name='json',
                          return_value={'id': '5',
                                        'items':[{'id':'5'}]})
    mock_resp.json = mock_json
    # not testing getid
    mocker.patch.object(Youtube, '_getid', new=lambda self, x: '5')
    assert base_youtube.json['id'] == '5'


@pytest.mark.parametrize('item,target_id', [
    # minimal  jsons, not all the availible info
    ({'id': '5'}, '5'), # will test keyerror path
    # tests kind path
    ({'kind': 'youtube#video',
      'id': {'kind': 'youtube#video', 'videoId': '10'}}, '10'),
    ])
def test_getid(base_youtube, item, target_id):
    real_id = base_youtube._getid(item)
    assert real_id == target_id


@pytest.mark.parametrize('method,url,params', [
    ('GET', 'endpoint', {'param1': 'val1'}),
    ('GET', '', {'param1': 'val1'}),
    ('GET', '', None),
    ])
def test_request(mocker, base_youtube, method, url, params):
    mock_request = mocker.patch('the_sentinel.apis.RestBase.request')
    base_youtube.request(method, url, params=params)
    if params is None: params={}
    params.update({
        'part':'snippet',
        'key': logins.GOOGLE.get('youtube')
        })
    mock_request.assert_called_with(method,
                                    base_youtube.format_url(url),
                                    params=params)

@pytest.mark.parametrize('items,endpoint,query,limit,params', [
    ([], 'endpoint', 'query', 5, {}),
    ([{'kind': 'youtube#video', 'id':{'videoId':'1234'}}],
     'endpoint', 'query', 5, {}),
    ])
def test_search(mocker, base_youtube, items, endpoint, query, limit, params):
    mock_get = mocker.patch.object(Youtube, 'get')
    mock_get.return_value.json.return_value = {'items': items}
    assert len(base_youtube.search(endpoint=endpoint,
                                   query=query, limit=limit)) == \
           len(items)
    params.update({
            'q': query,
            'maxResults': limit,
            })
    mock_get.assert_called_with(url=endpoint, params=params)

possible_params = set(KIND_MAPPING.keys())
@pytest.mark.parametrize('item,target_id', [
    ({'kind': 'youtube#video',
        'id': {'kind': 'youtube#video', 'videoId': '5'}}, '5'),
    ({'kind': 'youtube#channel',
        'id': {'kind': 'youtube#channel', 'channelId': '5'}}, '5'),
    ({'kind': 'youtube#playlist',
        'id': {'kind': 'youtube#playlist', 'playlistId': '5'}}, '5'),
    ({'kind': 'youtube#searchResult',
        'id': {'kind': 'youtube#playlist', 'playlistId': '5'}}, '5'),
    ({'kind': 'youtube#playlistItem',
      'snippet':
            {'resourceId':
                {'kind': 'youtube#playlist', 'videoId': '5'}
            }
     }, '5'),
    ])
def test_kind_mapping(item, target_id):
    # This test needs to be totally exaustive, all keys in KIND_MAPPING must be
    # tested.
    kind = item['kind']
    possible_params.remove(kind)
    assert KIND_MAPPING[kind](item)[0] == target_id

def test_kind_mapping_exaustive():
    """
    test that test_kind_mapping does an exaustive coverage of KIND_MAPPING
    keys
    """
    # tests are run in order of declaration which is why this works
    assert not possible_params


