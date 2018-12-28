import pytest
from the_sentinel.apis.google.youtube import Channel, \
                                             Video

import pytest
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
