# -*- coding: utf-8 -*-
"""Post each night recap to the club Discord, as a card with the photo and a link.

Runs in the Night recaps workflow after the pages are built. The webhook URL is a
GitHub secret (DISCORD_RECAPS_WEBHOOK) and is never written anywhere in this repo.
Without it the script says so and exits cleanly, so the recap build never fails
because of Discord.

discord-posted.json is the ledger: one entry per night, holding the Discord message id
and a fingerprint of what was posted. It keeps the channel in step with the site:
  - a night not in the ledger is posted,
  - a night whose words or photo changed has its message edited in place,
  - a night removed from the site has its message deleted.
The first time the ledger is created, every night except the newest is recorded as
already handled, so switching this on does not flood the channel with old recaps.

The photo is uploaded with the message rather than linked, because Discord fetches a
linked image the moment the message is sent, which can be before the site has
finished deploying.
"""
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_nights as B  # noqa: E402

OUT = B.OUT
LEDGER = os.path.join(OUT, 'discord-posted.json')
SCARLET = 0xFE273A
UA = 'KavaSocialChessClub-recaps (https://kavasocialchessclub.com, 1.0)'


# ---------------------------------------------------------------- Lenny

# Lenny, the club's resident know-it-all, introduces every recap. His lines sit above
# the card; the card itself is still the recap exactly as it reads on the site.
#
# His lines live in build/lenny/*.txt and are read by lenny_bank.py: about a thousand of them.
# A given recap always gets the same Lenny, so an edited recap keeps its joke, and his lines
# are kept out of the fingerprint so they can never make an old message look "changed".
#
# Everything in facts.txt is a real, checkable fact; opinions live in takes.txt and are never
# introduced as facts. Nothing is made up about the club or its members: the lines about the
# night only restate what the recap already records.
LENNY_NAME = 'Lenny'
LENNY_AVATAR = 'https://kavasocialchessclub.com/img/lenny.png'

import lenny_bank as L  # noqa: E402


def lenny_says(n):
    """Lenny's introduction to one recap.

    Each pool is walked in a fixed shuffled order, one step per club night, so nothing
    repeats until its whole pool has been used. The same night always gets the same Lenny.
    """
    when = B.when(n)
    news = bool(n.get('venue'))
    no = B.night_number(when)
    # club news has no night number of its own, so it steps by the calendar instead
    k = datetime.strptime(when, '%Y-%m-%d').toordinal() if news else no
    text = ' '.join([B.loc(n, 'title', False), B.loc(n, 'line', False), B.loc(n, 'commentary', False)]).lower()
    topical = [f for key, f in L.TOPICAL if re.search(r'\b%s\b' % re.escape(key.lower()), text)]
    if topical and k % 2 == 0:
        middle = '%s %s' % (L.pick(L.FACT_LEADS, 'fact-lead', k), L.pick(topical, 'topical', k // 2))
    else:
        middle = L.knowledge(k)
    values = {'no': no, 'type': B.night_type(n, False), 'date': B.long_date(when, False), 'n': n.get('played') or 0}
    if news:
        record = L.pick(L.NEWS, 'news', k)
    elif n.get('played') and k % 3 == 0:
        record = L.pick(L.PLAYED, 'played', k // 3)
    else:
        record = L.pick(L.NIGHT, 'night', k)
    return '\n\n'.join(['\U0001F4F0 ' + L.pick(L.INTROS, 'intro', k), middle, record.format(**values),
                        L.pick(L.SIGNOFFS, 'signoff', k) + ' \u2014 Lenny'])


# ---------------------------------------------------------------- the card

def _clip(text, limit):
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:')
    return cut + '…'


def card(n):
    """The Discord message for one night: a line of text and one embed."""
    no = B.night_number(B.when(n))
    title = B.loc(n, 'title', False) or B.night_type(n, False)
    url = B.URL + B.slug(n, False) + '/'
    line = B.loc(n, 'line', False)
    first = (B.loc(n, 'commentary', False).split('\n') or [''])[0]
    desc = []
    if line:
        desc.append('> *%s*' % _clip(line, 220))
    if first:
        desc.append(_clip(first, 330))
    desc.append('**[Read the full recap →](%s)**' % url)
    embed = {
        'title': _clip('%s · %s' % (B.night_tag(n, False), title), 250),
        'url': url,
        'description': '\n\n'.join(desc),
        'color': SCARLET,
        'author': {'name': B.night_type(n, False)},
        'footer': {'text': '%s · %s' % (B.long_date(B.when(n), False), B.venue(n, False))},
    }
    if n.get('played'):
        embed['fields'] = [{'name': 'Players', 'value': str(n['played']), 'inline': True}]
        if n.get('rounds'):
            embed['fields'].append({'name': 'Rounds', 'value': str(n['rounds']), 'inline': True})
    photo = os.path.join(OUT, n['photo']) if n.get('photo') else None
    if photo and os.path.exists(photo):
        embed['image'] = {'url': 'attachment://night.jpg'}
    else:
        photo = None
    return {'content': lenny_says(n), 'embeds': [embed], 'username': LENNY_NAME,
            'avatar_url': LENNY_AVATAR, 'allowed_mentions': {'parse': []}}, photo


def fingerprint(n):
    """Changes whenever anything a reader would see in the card changes."""
    payload, photo = card(n)
    h = hashlib.sha256(json.dumps(payload['embeds'], sort_keys=True, ensure_ascii=False).encode('utf-8'))
    if photo:
        h.update(open(photo, 'rb').read())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- the webhook

def _multipart(payload, photo):
    boundary = 'kava' + uuid.uuid4().hex
    parts = [('--%s\r\nContent-Disposition: form-data; name="payload_json"\r\n'
              'Content-Type: application/json\r\n\r\n' % boundary).encode('utf-8'),
             json.dumps(payload, ensure_ascii=False).encode('utf-8'), b'\r\n']
    if photo:
        parts += [('--%s\r\nContent-Disposition: form-data; name="files[0]"; filename="night.jpg"\r\n'
                   'Content-Type: image/jpeg\r\n\r\n' % boundary).encode('utf-8'),
                  open(photo, 'rb').read(), b'\r\n']
    parts.append(('--%s--\r\n' % boundary).encode('utf-8'))
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


def call(method, url, payload=None, photo=None):
    """One webhook request, waiting out a rate limit once. Returns the parsed reply."""
    if payload is not None:
        if photo:
            payload = dict(payload, attachments=[{'id': 0, 'filename': 'night.jpg'}])
        body, ctype = _multipart(payload, photo)
    else:
        body, ctype = None, None
    for attempt in (1, 2):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('User-Agent', UA)
        if ctype:
            req.add_header('Content-Type', ctype)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 1:
                try:
                    wait = float(json.loads(e.read()).get('retry_after', 2))
                except Exception:
                    wait = 2.0
                time.sleep(min(wait, 30) + 0.5)
                continue
            if e.code == 404 and method in ('PATCH', 'DELETE'):
                return None          # someone deleted it by hand in Discord
            raise RuntimeError('Discord said %d to %s: %s' % (e.code, method, e.read()[:300]))
    raise RuntimeError('Discord kept rate-limiting')


def poll_message(n):
    """A recap's poll as a Discord poll, open until the recap says it closes. Only when the poll
    says "discord": true: Harold asks for a Discord poll recap by recap; the site's poll is the default."""
    p = n.get('poll') or {}
    if not p.get('q') or not p.get('options') or not p.get('discord'):
        return None
    hours = 48
    if p.get('closes'):
        try:
            left = (datetime.fromisoformat(p['closes']) - datetime.now(timezone.utc)).total_seconds() / 3600
        except (ValueError, TypeError):
            left = hours
        if left < 1:
            return None            # already over: a poll nobody can answer is noise
        hours = max(1, min(768, int(left)))
    return {'poll': {'question': {'text': p['q'][:300]},
                     'answers': [{'poll_media': {'text': o[1][:55]}} for o in p['options'][:10]],
                     'duration': hours, 'allow_multiselect': False},
            'username': LENNY_NAME, 'avatar_url': LENNY_AVATAR, 'allowed_mentions': {'parse': []}}


# ---------------------------------------------------------------- the run

def load_nights():
    d = json.load(open(os.path.join(OUT, 'nights.json'), encoding='utf-8'))
    return sorted(d.get('nights', []), key=lambda n: n['date'], reverse=True)


def main(dry=False):
    hook = os.environ.get('DISCORD_RECAPS_WEBHOOK', '').strip()
    if not hook and not dry:
        print('Discord: no DISCORD_RECAPS_WEBHOOK secret set, nothing posted.')
        return 0
    if hook and not hook.startswith('https://discord.com/api/webhooks/') \
            and not hook.startswith('https://discordapp.com/api/webhooks/'):
        print('Discord: the secret does not look like a Discord webhook URL; nothing posted.')
        return 0
    base = hook.split('?')[0]

    nights = load_nights()
    by_date = {n['date']: n for n in nights}

    if os.path.exists(LEDGER):
        ledger = json.load(open(LEDGER, encoding='utf-8'))
    else:
        # first run: the newest night is news, everything older is history
        ledger = {'_comment': 'Which recaps are on the club Discord. Written by build/post_discord.py.',
                  'posted': {n['date']: {'id': None, 'fp': fingerprint(n), 'seeded': True} for n in nights[1:]}}
        print('Discord: new ledger; %d older nights recorded as already handled.' % max(len(nights) - 1, 0))
    posted = ledger.setdefault('posted', {})
    did = []

    # new and changed, oldest first so the channel reads in order
    for n in reversed(nights):
        d, fp = n['date'], fingerprint(n)
        seen = posted.get(d)
        payload, photo = card(n)
        if seen is None:
            if dry:
                print('DRY post  %s  %s' % (d, payload['embeds'][0]['title']))
                continue
            msg = call('POST', base + '?wait=true', payload, photo)
            posted[d] = {'id': msg.get('id'), 'fp': fp}
            did.append('posted ' + d)
        elif seen.get('fp') != fp and seen.get('id'):
            if dry:
                print('DRY edit  %s' % d)
                continue
            edit = {k: v for k, v in payload.items() if k not in ('username', 'avatar_url')}
            if call('PATCH', '%s/messages/%s' % (base, seen['id']), edit, photo) is None:
                msg = call('POST', base + '?wait=true', payload, photo)   # it was deleted by hand: post again
                seen['id'] = msg.get('id')
            seen['fp'] = fp
            did.append('edited ' + d)
        elif seen.get('fp') != fp:
            seen['fp'] = fp      # an old night from before the bot existed; leave the channel alone

        # the prediction goes out as its own message, once, right under the recap
        seen = posted.get(d)
        pm = poll_message(n)
        if pm and dry and not (seen or {}).get('poll'):
            print('DRY poll  %s  %s' % (d, pm['poll']['question']['text']))
        elif pm and seen and seen.get('id') and not seen.get('poll'):
            try:
                seen['poll'] = call('POST', base + '?wait=true', pm).get('id')
                did.append('poll ' + d)
            except RuntimeError as e:
                print('Discord: the poll for %s was not posted: %s' % (d, e))

    # removed from the site
    for d in [d for d in posted if d not in by_date]:
        mid = posted[d].get('id')
        if dry:
            print('DRY delete %s' % d)
            continue
        if mid:
            call('DELETE', '%s/messages/%s' % (base, mid))
        if posted[d].get('poll'):
            call('DELETE', '%s/messages/%s' % (base, posted[d]['poll']))
        del posted[d]
        did.append('removed ' + d)

    if not dry:
        json.dump(ledger, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        open(LEDGER, 'a', encoding='utf-8').write('\n')
    print('Discord: ' + (', '.join(did) if did else 'nothing new.'))
    return 0


if __name__ == '__main__':
    sys.exit(main(dry='--dry' in sys.argv))
