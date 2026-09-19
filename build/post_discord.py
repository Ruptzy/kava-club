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
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_nights as B  # noqa: E402

OUT = B.OUT
LEDGER = os.path.join(OUT, 'discord-posted.json')
SCARLET = 0xFE273A
UA = 'KavaSocialChessClub-recaps (https://kavasocialchessclub.com, 1.0)'


# ---------------------------------------------------------------- the card

def _clip(text, limit):
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip(',;:')
    return cut + '…'


def card(n):
    """The Discord message for one night: a line of text and one embed."""
    no = B.night_number(n['date'])
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
        'title': _clip('Night %d · %s' % (no, title), 250),
        'url': url,
        'description': '\n\n'.join(desc),
        'color': SCARLET,
        'author': {'name': B.night_type(n, False)},
        'footer': {'text': '%s · %s' % (B.long_date(n['date'], False), B.venue(n, False))},
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
    return {'content': '📰 **New recap is up!** ♟️', 'embeds': [embed],
            'allowed_mentions': {'parse': []}}, photo


def fingerprint(n):
    """Changes whenever anything a reader would see in the card changes."""
    payload, photo = card(n)
    h = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8'))
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
            if call('PATCH', '%s/messages/%s' % (base, seen['id']), payload, photo) is None:
                msg = call('POST', base + '?wait=true', payload, photo)   # it was deleted by hand: post again
                seen['id'] = msg.get('id')
            seen['fp'] = fp
            did.append('edited ' + d)
        elif seen.get('fp') != fp:
            seen['fp'] = fp      # an old night from before the bot existed; leave the channel alone

    # removed from the site
    for d in [d for d in posted if d not in by_date]:
        mid = posted[d].get('id')
        if dry:
            print('DRY delete %s' % d)
            continue
        if mid:
            call('DELETE', '%s/messages/%s' % (base, mid))
        del posted[d]
        did.append('removed ' + d)

    if not dry:
        json.dump(ledger, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        open(LEDGER, 'a', encoding='utf-8').write('\n')
    print('Discord: ' + (', '.join(did) if did else 'nothing new.'))
    return 0


if __name__ == '__main__':
    sys.exit(main(dry='--dry' in sys.argv))
