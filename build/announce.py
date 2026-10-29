# -*- coding: utf-8 -*-
"""Post a one-off announcement to the club Discord, as Lenny, in the channel the 3pm posts go to.

    ANNOUNCE="text" python build/announce.py         (run by the Announce workflow)

The text comes from the workflow's input, so nothing needs committing to post it. The
webhook is the SCHEDULE_FOR_DAY secret, the same one the daily "tonight" post uses.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import post_tonight as T          # noqa: E402

text = os.environ.get('ANNOUNCE', '').replace('\n', '\n').strip()
hook = os.environ.get('CLUB_SCHEDULE', '').strip()
if not text:
    sys.exit('No announcement text given.')
if not hook.startswith(('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/')):
    sys.exit('The SCHEDULE_FOR_DAY secret is missing or is not a Discord webhook.')
if len(text) > 1900:
    sys.exit('Too long for one Discord message (%d characters).' % len(text))
msg = T.send(hook, text)
print('Posted announcement, message %s.' % msg.get('id'))
