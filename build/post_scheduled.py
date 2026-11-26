# -*- coding: utf-8 -*-
"""Post Lenny's scheduled one-off messages (a holiday note, a heads-up) when their time comes.

    python build/post_scheduled.py            (run by the Scheduled posts workflow)
    python build/post_scheduled.py --dry      (show what is due, post nothing)

Each entry in scheduled-posts.json has an id, "at" (Bradenton time, YYYY-MM-DDTHH:MM),
"channel" (schedule or recaps) and the text. A run posts every entry whose time has come
and marks it "posted", which the workflow commits, so a second run never posts it twice.
A run that lands a few minutes early waits; one more than six hours late leaves the entry
alone rather than post a stale message.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import post_tonight as T          # noqa: E402

FILE = os.path.join(os.path.dirname(HERE), 'scheduled-posts.json')
HOOKS = {'schedule': 'CLUB_SCHEDULE', 'recaps': 'NIGHT_RECAPS'}
EARLY = timedelta(minutes=20)     # wait for the minute if the run is this close
STALE = timedelta(hours=6)


def main(argv):
    dry = '--dry' in argv
    doc = json.load(open(FILE, encoding='utf-8'))
    now = datetime.now(T.EASTERN).replace(tzinfo=None)
    done = 0
    for p in doc.get('posts', []):
        if p.get('posted'):
            continue
        at = datetime.strptime(p['at'], '%Y-%m-%dT%H:%M')
        if now < at - EARLY:
            print('%s: not yet (due %s).' % (p['id'], p['at']))
            continue
        if now > at + STALE:
            print('%s: due %s, too late to post now; left alone.' % (p['id'], p['at']))
            continue
        text = p['text'].strip()
        if len(text) > 2000:
            sys.exit('%s is %d characters, over Discord\'s 2000.' % (p['id'], len(text)))
        if dry:
            print('--- %s (%s, %s) ---\n%s\n' % (p['id'], p['at'], p.get('channel', 'schedule'), text))
            continue
        hook = os.environ.get(HOOKS[p.get('channel', 'schedule')], '').strip()
        if not hook.startswith(('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/')):
            sys.exit('No Discord webhook for the %s channel.' % p.get('channel', 'schedule'))
        while datetime.now(T.EASTERN).replace(tzinfo=None) < at:
            time.sleep(15)
        msg = T.send(hook, text)
        p['posted'] = datetime.now(T.EASTERN).strftime('%Y-%m-%dT%H:%M')
        p['message'] = msg.get('id')
        print('%s: posted, message %s.' % (p['id'], msg.get('id')))
        done += 1
    if done:
        open(FILE, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
