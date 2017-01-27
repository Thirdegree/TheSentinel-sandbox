GAPIpulls = { 
    'video': (lambda x: [{
        'media_author': (i['snippet']['channelTitle']),
        'media_channel_id': str(i['snippet']['channelId']),
        'media_platform': 'YouTube',
        } for i in x['items']]),
    'playlist': (lambda x: [{
        'media_author': (i['snippet']['channelTitle']),
        'media_channel_id': str(i['snippet']['channelId']),
        'media_platform': 'YouTube',
        } for i in x['items']]),
    'playlist videos': (lambda x: [{
        'media_author': (i['snippet']['channelTitle']),
        'media_channel_id': str(i['snippet']['channelId']),
        'media_platform': 'YouTube',
        } for i in x['items']]),
    'username': (lambda x: [{
        'media_author': (i['snippet']['title']),
        'media_channel_id': str(i['id']),
        'media_platform': 'YouTube',
        } for i in x['items']]),
    'channel': (lambda x: [{
        'media_author': (i['snippet']['title']),
        'media_channel_id': str(i['id']),
        'media_platform': 'YouTube',
        } for i in x['items']]),
}

TwitterAPIPulls = {
    'tweet': (lambda x: [{
            'media_author': i.user.screen_name,
            'media_channel_id': i.user.id,
            'media_platform': "Twitter"
        } for i in x]),
    'user': (lambda x: [{
            'media_author': x.screen_name,
            'media_channel_id': x.id,
            'media_platform': "Twitter" 
        }])
}

VidmeAPIPulls = {
    'video': (lambda x: [{
        'media_author': (x['video']['user']['username']),
        'media_channel_id': (x['video']['user']['user_id']),
        'media_platform': 'Vidme'
        }])
}

TwitchAPIPulls = {
    'channel': (lambda x: [{
        'media_author': (x['display_name']),
        'media_channel_id': (x['_id']),
        'media_platform': ('Twitch'),
        }])
}

DMpulls = {
    'video': (lambda x: [{
        'media_author': (x['owner.screenname']),
        'media_channel_id': str(x['owner']),
        'media_platform': 'DailyMotion',
        }]),
    'playlist': (lambda x: [{
        'media_author': (x['owner.screenname']),
        'media_channel_id': str(x['owner']),
        'media_platform': 'DailyMotion'
        }]),
    'playlist videos': (lambda x: [{
        'media_author': (i['owner.screenname']),
        'media_channel_id': str(i['owner']),
        'media_platform': 'DailyMotion',
        } for i in x['list']
        ]),
    'username': (lambda x: [{
        'media_author': (x['screenname']),
        'media_channel_id': str(x['id']),
        'media_platform': 'DailyMotion'
        }])
}

VMOpulls = {
    'user': (lambda x: [{
        'media_author': (x['name']),
        'media_channel_id': str(x['uri']),
        'media_platform': 'Vimeo',
        }]),
    'playlist': (lambda x: [{
        'media_author': (i['name']),
        'media_channel_id': str(i['uri']),
        'media_platform': 'Vimeo',
        } for i in x['user']]),
    'playlist videos': (lambda x: [{
        'media_author': (i['user']['uri']),
        'media_channel_id': str(i['user']['uri']),
        'media_platform': 'Vimeo',
        } for i in x['data']]),
    'video': (lambda x: [{
        'media_author': (x['user']['name']),
        'media_channel_id': str(x['user']['uri']),
        'media_platform': 'Vimeo',
        }])
}

SCpulls = {
    'all': lambda x: ([{
        'media_author': x['user']['username'],
        'media_channel_id': str(x['user']['id']),
        'media_platform': 'SoundCloud'
    } if x['kind'] != 'user' else {
        'media_author': (x['username']),
        'media_channel_id': str(x['id']),
        'media_platform': 'SoundCloud'
    }]),
    'playlist videos': (lambda x: [{
        'media_author':   i['user']['username'],
        'media_channel_id': str(i['user']['id']),
        'media_platform': 'SoundCloud'
        } for i in x['tracks']])
    }
    