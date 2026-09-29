# -*- coding: utf-8 -*-
"""Hand the weekly email to Brevo, scheduled for Monday 6pm in Bradenton.

    python build/send_email.py            the normal run: acts on a Monday, once a week
    python build/send_email.py --dry      build it and say what would happen; contacts nobody
    python build/send_email.py --test=me@example.com   send the built email to one address, now

Brevo does the timekeeping and the tracking. This only has to run at some point on
Monday before six, which is as much as GitHub's scheduler can be trusted with.

The API key is the BREVO_API_KEY secret and is never written in this repository. The
member list lives only inside Brevo; this script never sees an address. It asks Brevo
for the list by name and for the sender Brevo already has on file.

email-sent.json records the last week handed over, so a second run cannot create a
second campaign. A week with no new recap builds nothing and sends nothing.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_email as E           # noqa: E402
import post_tonight as T          # noqa: E402

OUT = E.OUT
LEDGER = os.path.join(OUT, 'email-sent.json')
API = 'https://api.brevo.com/v3'
LIST_NAME = 'Club members'        # the list Harold imported the members into
SEND_HOUR = 18                    # 6pm, Bradenton time
LAST_HOUR = 21                    # after 9pm on Monday it is too late to be "Monday's email"
UA = 'KavaSocialChessClub-weekly (https://kavasocialchessclub.com, 1.0)'


def call(method, path, key, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode('utf-8') if body is not None else None)
    req.add_header('api-key', key)
    req.add_header('accept', 'application/json')
    req.add_header('content-type', 'application/json')
    req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError('Brevo said %d to %s %s: %s' % (e.code, method, path, e.read()[:400].decode('utf-8', 'replace')))


def ledger():
    try:
        return json.load(open(LEDGER, encoding='utf-8'))
    except Exception:
        return {}


def remember(campaign, cid, when):
    led = ledger()
    led['_comment'] = 'The last weekly email handed to Brevo. Written by build/send_email.py.'
    led.update(last=campaign, id=cid, scheduled=when)
    json.dump(led, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    open(LEDGER, 'a', encoding='utf-8').write(chr(10))


def wait_for(url, tries=30):
    """The photo has to be on the live site before anyone opens the email."""
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(20)
    return False


def main(argv):
    dry = '--dry' in argv
    test = [a.split('=', 1)[1] for a in argv if a.startswith('--test=')]
    now = datetime.now(T.EASTERN)
    day = now.date()

    if not (dry or test):
        if day.weekday() != 0:
            print('Today is %s in Bradenton. The email goes on Mondays.' % E.DAYS[day.weekday()])
            return 0
        if ledger().get('last') == 'weekly-%s' % day.isoformat():
            print('This week is already with Brevo (campaign %s).' % ledger().get('id'))
            return 0
        if now.hour >= LAST_HOUR:
            print('It is past %d:00 on Monday; too late for this week.' % LAST_HOUR)
            return 1

    out = os.path.join(OUT, 'build', 'out-email')
    meta = E.build(day, out)
    if not meta:
        return 0
    html = open(os.path.join(out, 'email.html'), encoding='utf-8').read()

    target = now.replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
    if now >= target - timedelta(minutes=10):
        target = now + timedelta(minutes=15)          # a late Monday run: send shortly, not next week
    when = target.isoformat(timespec='seconds')

    if dry:
        print('DRY  would schedule "%s" for %s to the list "%s"' % (meta['subject'], when, LIST_NAME))
        return 0

    key = os.environ.get('BREVO_API_KEY', '').strip()
    if not key:
        print('No BREVO_API_KEY secret set, so nothing was handed over.')
        return 0

    senders = [s for s in call('GET', '/senders', key).get('senders', []) if s.get('active')]
    if not senders:
        print('Brevo has no active sender. Add and verify one in Brevo first.')
        return 1
    own = [s for s in senders if s.get('email', '').endswith('@kavasocialchessclub.com')]
    sender = (own or senders)[0]

    if test:
        # "owner" is the address the Brevo account itself is registered to, so a test can
        # be asked for without an address ever appearing in this repository or its logs
        to = call('GET', '/account', key).get('email', '') if test[0] == 'owner' else test[0]
        if not to:
            print('Brevo did not say who owns the account, so no test was sent.')
            return 1
        try:
            call('POST', '/smtp/email', key, {
                'sender': {'name': meta['from_name'], 'email': sender['email']},
                'to': [{'email': to}], 'subject': '[TEST] ' + meta['subject'], 'htmlContent': html})
        except RuntimeError as e:
            print(str(e).replace(to, '(the test address)'))
            return 1
        print('Test sent, from an address on %s.' % sender['email'].split('@')[-1])
        found = [l for l in call('GET', '/contacts/lists?limit=50', key).get('lists', [])
                 if l.get('name', '').strip().lower() == LIST_NAME.lower()]
        print('The list "%s" %s.' % (LIST_NAME, 'is there' if found else 'was NOT found in Brevo'))
        return 0

    lists = call('GET', '/contacts/lists?limit=50', key).get('lists', [])
    match = [l for l in lists if l.get('name', '').strip().lower() == LIST_NAME.lower()]
    if not match:
        print('Brevo has no list called "%s". Lists there: %s' % (LIST_NAME, ', '.join(l.get('name', '') for l in lists) or 'none'))
        return 1

    if meta.get('photo') and not wait_for(meta['photo']):
        print('The photo is not on the live site yet, so the email was not scheduled.')
        return 1

    made = call('POST', '/emailCampaigns', key, {
        'name': 'Weekly · %s' % day.isoformat(),
        'subject': meta['subject'],
        'previewText': meta['preheader'],
        'sender': {'name': meta['from_name'], 'email': sender['email']},
        'htmlContent': html,
        'recipients': {'listIds': [match[0]['id']]},
        'scheduledAt': when,
    })
    remember(meta['campaign'], made.get('id'), when)
    print('Scheduled "%s" for %s. %d members on the list. Brevo campaign %s.'
          % (meta['subject'], when, match[0].get('uniqueSubscribers', match[0].get('totalSubscribers', 0)), made.get('id')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
