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

text = os.environ.get('ANNOUNCE', '').replace('\\n', '\n').strip()   # the workflow box is one line, so \n is typed literally
hook = os.environ.get('CLUB_SCHEDULE', '').strip()
if not text:
    sys.exit('No announcement text given.')
if not hook.startswith(('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/')):
    sys.exit('The SCHEDULE_FOR_DAY secret is missing or is not a Discord webhook.')
if len(text) > 1900:
    sys.exit('Too long for one Discord message (%d characters).' % len(text))
cards = []
raw = os.environ.get('EMBEDS', '').strip()
if raw:
    import json
    for c in json.loads(raw)[:10]:   # a board image per card, with the line written under it
        e = {'color': 0xFE273A}
        if c.get('title'): e['title'] = str(c['title'])[:256]
        if c.get('description'): e['description'] = str(c['description']).replace('\\n', '\n')[:4000]
        if c.get('url'): e['url'] = str(c['url'])
        if c.get('image'): e['image'] = {'url': str(c['image'])}
        cards.append(e)
msg = T.send(hook, text, cards)
print('Posted announcement, message %s.' % msg.get('id'))
