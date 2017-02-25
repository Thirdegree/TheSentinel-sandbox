ListOfHelpCommands = """
#The current list of commands available:
\n\n---\n\n
###Subject:
- add to blacklist
- remove from blacklist
- add to global blacklist
\n
###Body:
- Link To The Video Only
\n\n---\n\n
###Subject:
- report
\n
###Body:
- blacklisted users
\n\n---\n\n
"""

IntoductaryInstructions = """

#Ready to get started?

###1. Adding the bot:

- Add the bot to the Mod List with **POST ONLY** permission

>  Adding as a mod is required to ensure only Authorized Users aka your mods can add or remove a channel from the blacklist

> Post Only permission is to be able to remove the post or comment

###2. To add a YouTube channel to the Blacklist:

- Go to [Layer7 Solutions](http://layer7.solutions/myaccount.php) and log in.
- Go to "YouTube Killer Blacklist Management."
- Select the subreddit you wish to ban the channel from, and enter the video from the channel to be banned.
- Select "Add to Blacklist."
- Submit.

###3. To remove a YouTube channel from the Blacklist:

- Go to [Layer7 Solutions](http://layer7.solutions/myaccount.php) and log in.
- Go to "YouTube Killer Blacklist Management."
- Select the subreddit you wish to unban the channel from, and enter the video from the channel to be unbanned.
- Select "Remove from Blacklist."
- Submit.

###4. To see if a channel is Blacklisted:

- Go to [Layer7 Solutions](http://layer7.solutions/myaccount.php) and log in.
- Go to "YouTube Killer Blacklist Management."
- Select the subreddit you wish to query, and enter the video you're searching for.
- Select "Check if channel is blacklisted."
- Submit.


###5. To see all blacklisted channels:

- Go to [Layer7 Solutions](http://layer7.solutions/myaccount.php) and log in.
- Go to "YouTube Killer Blacklist Management."
- Select the subreddit you wish to query, and leave the video field blank.
- Select "View all blacklisted channels."
- Submit.

---

#Global Blacklist

The bot also has a global blacklist, which is a curated list by the moderators of /r/YT_Killer to ensure only true actual spam is added, and not a local sub issue. If you would like a channel to be considered for a Global Blacklist, send a message to /r/YT_Killer with a link to the user account, a link to the post/comment and any other relevant data.

---

#Notes

The bot checks all content posted to the sub; Link Submissions, Self Post Submissions and Comments from all queues (New, Comments, SPAM which is removed content, and Edited in case someone ninja edits something in). If the post or comment is **NOT** on the blacklist, the Post/Comment is left alone, and added to its done list. If the Post/Comment **IS** on the blacklist, it is removed, with no reason. No PM or ModMail is sent to anyone. If you would like notifications it can send a message to a designated slack channel.

---

If you have any feedback/questions/anything, please send /r/YT_Killer or /u/D0cR3d a message.
"""

CurrentInstanceOverloaded = '''

Thank you for trying to add TheSentinel to your subreddit. Unfortunately, the account you attempted to add has reached it's subscriber limit and can not be added to a subreddit of your size. For more information on which Sentinel account can be added, please contact /r/theSentinelBot.
'''

NO_SUBREDDIT_SUBJECT_MSG = 'Please remember to include your Subreddit Name in the subject such as "add to blacklist for /r/SubredditName"'

ForbiddenResponse = '''
The bot you messaged cannot access your subreddit, and therefor cannot add the link you requested. Please ensure you messaged {}, and if you did please contact /r/theSentinelBot
'''