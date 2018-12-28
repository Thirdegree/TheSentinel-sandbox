import pytest
from pytest_mock import mocker
from the_sentinel.apis import RestBase
import re

class RestBaseSub(RestBase):
    @property
    def resp(self):
        # abstract
        return

@pytest.fixture
def rest_base():
    """
    Subclass of RestBase with abstract method set to noop, id=10
    """
    return RestBaseSub(id=10)

def test_caching():
    """
    Testing the caching mechanism
    """
    tr1 = RestBaseSub(id=10)
    tr1._json = 'hello!'
    # tr1 is cached
    assert (10, RestBaseSub) in RestBaseSub._CACHE
    tr2 = RestBaseSub(id=10)
    # tr2 is the same as cached and has the same values
    assert tr2._json == 'hello!'
    assert tr1 is tr2

    tr3 = RestBaseSub(id=10, cached=False)
    # same object
    assert tr1 is tr3
    # but no cached values
    assert tr3._json is None

    tr1.refresh()
    # no longer cached
    assert (10, RestBaseSub) not in RestBaseSub._CACHE

@pytest.mark.parametrize(
        'API_BASE,REST_BASE,ENDPOINT_BASE,endpoint,target_url', [
        ('rest-base.com', ['api', 'latest'], 'api-endpoint','' ,
            'rest-base.com/api/latest/api-endpoint'),
        ('rest-base.com', ['api', 'latest'], 'api-endpoint','other-endpoint' ,
            'rest-base.com/api/latest/other-endpoint'),
        ])
def test_format_url(mocker, rest_base,
                    API_BASE,
                    REST_BASE,
                    ENDPOINT_BASE,
                    endpoint,
                    target_url):
    mocker.patch.object(rest_base, 'REST_BASE', new=REST_BASE)
    mocker.patch.object(rest_base, 'ENDPOINT_BASE', new=ENDPOINT_BASE)
    mocker.patch.object(rest_base, 'API_BASE', new=API_BASE)
    assert rest_base.format_url(endpoint) == target_url


@pytest.mark.parametrize('regex,test_str,result_group', [
    (r'(?P<target>.*)', 'simple match', 'simple match'),
    (r'(?P<target>exact)', 'exact', 'exact'),
    (r'we want (?P<target>part) of the string',
     'we want part of the string', 'part'),
    (r'(?P<target>not exact)',
     'this match is not exact at all', 'not exact'),
    ])
def test_match(mocker, rest_base, regex, test_str, result_group):
    mocker.patch.object(rest_base.__class__, 'URL_REGEX',
                        new=re.compile(regex))
    match = rest_base.match(test_str)
    assert match is not None
    assert match.group('target') == result_group

@pytest.mark.parametrize('regex,url,target_id', [
    (r'(?P<id>\d+)', 'hello1234goodbye', '1234'),
    (r'(?P<id>[a-z]+)', '1234goodbye5678', 'goodbye'),
    (r'(?P<id>.+)', '1234goodbye5678', '1234goodbye5678'),
    ])
def test_from_url(mocker, regex, url, target_id):
    mocker.patch.object(RestBaseSub, 'URL_REGEX',
                        new=re.compile(regex))
    mock_init = mocker.patch.object(RestBaseSub, '__init__')
    mock_init.return_value = None
    item = RestBaseSub.from_url(url)
    mock_init.assert_called_with(id=target_id)

