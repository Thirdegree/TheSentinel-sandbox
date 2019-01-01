This is an anti-spam bot designed to help take care of specifically youtube and other media related spam.

NOTE: Praw stub files are being created as I need them, I will not upload them until I'll A) done all of them, and B)
valided their accurecy

Local installation:

```bash
git clone https://github.com/Thirdegree/TheSentinel.git
cd TheSentinel
pip install -e .
```

Usage:

```python
from the_sentinel.apis.googe.Youtube import Youtube, Video, Channel, Playlist
yt = Youtube(key='your_key')
video = Video.from_url('htts://youtu.be/your-video')
channel = video.channel
channel_id = channel.id
```

