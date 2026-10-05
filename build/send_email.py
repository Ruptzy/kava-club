# -*- coding: utf-8 -*-
"""Hand the weekly email to Brevo, scheduled for Monday 3pm in Bradenton.

    python build/send_email.py            the normal run: schedules or updates the coming Monday's email
    python build/send_email.py --dry      build it and say what would happen; contacts nobody
    python build/send_email.py --test=me@example.com   send the built email to one address, now

Brevo does the timekeeping and the tracking. This only has to run at some point on
Monday before three, which is as much as GitHub's scheduler can be trusted with.

The API key is the BREVO_API_KEY secret and is never written in this repository. The
member list lives only inside Brevo; this script never sees an address. It asks Brevo
for the list by name and for the sender Brevo already has on file.

email-sent.json records the last week handed over, so a second run cannot create a
second campaign. A week with no new recap builds nothing and sends nothing.

It is safe to run as often as anything likes to run it, on any day. Each run works
towards the coming Monday, so the campaign is usually with Brevo days ahead:
  nothing scheduled yet      create the campaign, then read it back to see Brevo queued it
  scheduled, recap added     put the newer recap into the campaign already waiting
  scheduled, time changed    move the waiting campaign to SEND_HOUR
  scheduled, nothing new     do nothing
  past the send time         ask Brevo whether it went out, and fail if it did not
A run that fails makes GitHub email the repository owner.
"""
import hashlib
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
SEND_HOUR = 15                    # 3pm, Bradenton time
LAST_HOUR = 21                    # after 9pm on Monday it is too late to be "Monday's email"
CLOSE = 10                        # minutes before the send when the email stops being changed
WAITING = ('queued', 'in_process')
GONE = ('sent', 'in_process', 'archive')
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


def settle(how):
    led = ledger()
    led['confirmed'] = how
    json.dump(led, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    open(LEDGER, 'a', encoding='utf-8').write(chr(10))


def remember(campaign, cid, when, mark):
    led = ledger()
    led['_comment'] = 'The last weekly email handed to Brevo. Written by build/send_email.py.'
    led.update(last=campaign, id=cid, scheduled=when, mark=mark, confirmed=False)
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


def went_out(mine, key, now):
    """After the send time: ask Brevo whether it really left. A failed run emails Harold."""
    status = call('GET', '/emailCampaigns/%s' % mine['id'], key).get('status')
    due = datetime.fromisoformat(mine['scheduled'])
    if status in GONE:
        print('The email for %s has gone out (campaign %s).' % (mine['last'], mine['id']))
        settle(True)
        return 0
    if status in WAITING and now < due + timedelta(minutes=30):
        print('The email is queued for %s (campaign %s).' % (mine['scheduled'], mine['id']))
        return 0
    print('Campaign %s was due at %s and Brevo reports it as "%s". Open Brevo and send it by hand.'
          % (mine['id'], mine['scheduled'], status))
    if now > due + timedelta(days=1):
        settle('missed')          # said once, loudly; do not fail every run for ever after
    return 1


def keep_current(mine, meta, html, mark, key, when):
    """A campaign is already waiting. If a recap has been posted since, put it in; if the send time
    was changed here, move it."""
    status = call('GET', '/emailCampaigns/%s' % mine['id'], key).get('status')
    if status not in WAITING:
        print('Campaign %s should be waiting to send and Brevo reports it as "%s".' % (mine['id'], status))
        return 0 if status in GONE else 1
    moved = mine.get('scheduled') != when
    if mine.get('mark') == mark and not moved:
        print('This week is already with Brevo, unchanged, for %s (campaign %s).' % (mine['scheduled'], mine['id']))
        return 0
    if meta.get('photo') and not wait_for(meta['photo']):
        print('A newer recap was posted but its photo is not live, so the scheduled email was left as it was.')
        return 1
    # the words, and the time if SEND_HOUR changed; the list stays. If Brevo refuses, the
    # campaign already waiting still goes out, so the worst case is an older recap or the old time.
    body = {'subject': meta['subject'], 'previewText': meta['preheader'], 'htmlContent': html}
    if moved:
        body['scheduledAt'] = when
    call('PUT', '/emailCampaigns/%s' % mine['id'], key, body)
    remember(mine['last'], mine['id'], when if moved else mine['scheduled'], mark)
    if moved:
        print('The scheduled email was moved from %s to %s.' % (mine['scheduled'], when))
    if mine.get('mark') != mark:
        print('The scheduled email now leads with "%s". Going at %s.' % (meta['subject'], when if moved else mine['scheduled']))
    return 0


def remove(cid, key):
    """Delete a campaign, or failing that make sure it can never send.

    Brevo refuses to delete a campaign that has ever been scheduled, so those are
    suspended, which stops them, and then archived out of the way.
    """
    try:
        call('DELETE', '/emailCampaigns/%s' % cid, key)
        return 'deleted'
    except RuntimeError:
        pass
    for status in ('suspended', 'archive'):
        try:
            call('PUT', '/emailCampaigns/%s/status' % cid, key, {'status': status})
        except RuntimeError:
            pass
    status = call('GET', '/emailCampaigns/%s' % cid, key).get('status')
    return 'stopped and %s' % ('archived' if status == 'archive' else 'suspended') if status in ('archive', 'suspended') else None


def rehearse(meta, html, sender, key, now):
    """Walk the real Brevo calls with a draft that has no recipients, then delete it.

    A draft cannot send. The scheduled state was rehearsed once, on 28 September 2026,
    against a list holding only the account owner: Brevo queued the campaign and accepted
    a change to it while queued. That is not repeated here because Brevo will not delete a
    campaign once it has been scheduled, so every rehearsal would leave one behind.
    """
    bad = 0
    for status in ('queued', 'suspended', 'draft'):
        for c in call('GET', '/emailCampaigns?status=%s&limit=50' % status, key).get('campaigns', []):
            if c.get('name', '').startswith('REHEARSAL'):
                how = remove(c['id'], key)
                print('left over from before, campaign %s: %s' % (c['id'], how or 'STILL ABLE TO SEND'))
                bad += 0 if how else 1
    cid = None
    try:
        body = {'name': 'REHEARSAL, safe to delete', 'subject': meta['subject'], 'previewText': meta['preheader'],
                'htmlContent': html, 'sender': {'name': meta['from_name'], 'email': sender['email']}}
        reply = os.environ.get('REPLY_TO', '').strip()
        if reply:
            body['replyTo'] = reply
        try:
            cid = call('POST', '/emailCampaigns', key, body).get('id')
        except RuntimeError as e:
            raise RuntimeError(str(e).replace(reply, '(the reply address)') if reply else str(e))
        if reply:
            kept = call('GET', '/emailCampaigns/%s' % cid, key).get('replyTo') == reply
            print('draft: reply address %s' % ('accepted by Brevo' if kept else 'NOT kept by Brevo'))
            bad += 0 if kept else 1
        print('draft: created, Brevo reports "%s"' % call('GET', '/emailCampaigns/%s' % cid, key).get('status'))
        call('PUT', '/emailCampaigns/%s' % cid, key, {
            'subject': meta['subject'] + ' (changed)', 'previewText': meta['preheader'], 'htmlContent': html})
        ok = call('GET', '/emailCampaigns/%s' % cid, key).get('subject', '').endswith('(changed)')
        print('draft: changed after creation: %s' % ('yes' if ok else 'NO'))
        bad += 0 if ok else 1
    except RuntimeError as e:
        print('draft: %s' % e)
        bad += 1
    finally:
        if cid:
            how = remove(cid, key)
            print('draft: %s' % (how or 'COULD NOT BE REMOVED, delete campaign %s in Brevo' % cid))
            bad += 0 if how else 1
    return 1 if bad else 0


def main(argv):
    dry = '--dry' in argv
    test = [a.split('=', 1)[1] for a in argv if a.startswith('--test=')]
    now = datetime.now(T.EASTERN)
    # the Monday this run is working towards: today if it is Monday and not yet too late,
    # otherwise the one coming. The campaign is handed to Brevo as soon as there is a
    # recap to put in it, days ahead if need be, so nothing depends on a run on the day.
    ahead = (7 - now.weekday()) % 7
    if ahead == 0 and now.hour >= LAST_HOUR:
        ahead = 7
    day = now.date() + timedelta(days=ahead)

    key = os.environ.get('BREVO_API_KEY', '').strip()
    led = ledger()
    mine = led if led.get('last') == 'weekly-%s' % day.isoformat() else None
    late = 0

    if not (dry or test):
        if not key:
            print('The BREVO_API_KEY secret is missing, so the weekly email cannot be handed over.')
            return 1
        if mine and not mine.get('id'):
            print('This week\'s email was sent by hand, so there is nothing to do.')
            return 0
        if mine and now >= datetime.fromisoformat(mine['scheduled']) - timedelta(minutes=CLOSE):
            return went_out(mine, key, now)
        if not mine and led.get('id') and not led.get('confirmed'):
            late = went_out(led, key, now)        # last week's: did it really leave?

    out = os.path.join(OUT, 'build', 'out-email')
    meta = E.build(day, out)
    if not meta and test:
        # a test or rehearsal needs something to show, so use last week's email
        meta = E.build(day - timedelta(days=7), out)
    if not meta:
        if mine and not (dry or test):
            print('A campaign is scheduled but there is no longer a recap to build it from.')
            return 1
        if ahead == 0 and not (dry or test):
            print('It is Monday and there is no recap from the past week, so no email goes out.')
        return late
    html = open(os.path.join(out, 'email.html'), encoding='utf-8').read()
    mark = hashlib.sha256((meta['subject'] + meta['preheader'] + html).encode('utf-8')).hexdigest()[:16]

    target = datetime(day.year, day.month, day.day, SEND_HOUR, tzinfo=T.EASTERN)
    if now >= target - timedelta(minutes=CLOSE):
        target = now + timedelta(minutes=15)          # a late Monday run: send shortly, not next week
    when = target.isoformat(timespec='seconds')

    if dry:
        print('DRY  would schedule "%s" for %s to the list "%s"' % (meta['subject'], when, LIST_NAME))
        return 0

    if mine and not test:
        return keep_current(mine, meta, html, mark, key, when)

    senders = [s for s in call('GET', '/senders', key).get('senders', []) if s.get('active')]
    if not senders:
        print('Brevo has no active sender. Add and verify one in Brevo first.')
        return 1
    own = [s for s in senders if s.get('email', '').endswith('@kavasocialchessclub.com')]
    sender = (own or senders)[0]

    if test and test[0] == 'rehearse':
        return rehearse(meta, html, sender, key, now)

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

    body = {
        'name': 'Weekly · %s' % day.isoformat(),
        'subject': meta['subject'],
        'previewText': meta['preheader'],
        'sender': {'name': meta['from_name'], 'email': sender['email']},
        'htmlContent': html,
        'recipients': {'listIds': [match[0]['id']]},
        'scheduledAt': when,
    }
    # where a member's reply lands. Optional, a secret, and never printed: without it
    # replies go to the sending address, which only works if that mailbox exists.
    reply = os.environ.get('REPLY_TO', '').strip()
    if reply:
        body['replyTo'] = reply
    try:
        made = call('POST', '/emailCampaigns', key, body)
    except RuntimeError as e:
        raise RuntimeError(str(e).replace(reply, '(the reply address)') if reply else str(e))
    print('Replies go to %s.' % ('the address in the REPLY_TO secret' if reply else 'the sending address'))
    remember('weekly-%s' % day.isoformat(), made.get('id'), when, mark)
    print('Scheduled "%s" for %s. %d members on the list. Brevo campaign %s.'
          % (meta['subject'], when, match[0].get('uniqueSubscribers', match[0].get('totalSubscribers', 0)), made.get('id')))
    # read it back: a campaign Brevo did not queue is a campaign that will not go out
    status = call('GET', '/emailCampaigns/%s' % made.get('id'), key).get('status')
    if status not in WAITING + GONE:
        print('Brevo created the campaign but reports it as "%s", not scheduled.' % status)
        return 1
    return late


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except RuntimeError as e:
        print(e)
        sys.exit(1)
