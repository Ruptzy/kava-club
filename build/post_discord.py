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
# His words are drawn at random but seeded by the night's date, so a given recap always
# gets the same Lenny. That matters: an edited recap keeps its joke, and his lines are
# kept out of the fingerprint so they can never make an old message look "changed".
#
# Every "Actually..." is a real, checkable fact. Nothing here is made up about the club
# or its members; the club-specific lines only restate what the recap already records.
LENNY_NAME = 'Lenny'
LENNY_AVATAR = 'https://kavasocialchessclub.com/img/lenny.png'

LENNY_INTROS = [
    "*pushes glasses up* A new recap has been filed.",
    "Ahem. The minutes of the last meeting are now available.",
    "Excuse me. Excuse me. New recap, for the record.",
    "I have catalogued another club night. You're welcome.",
    "*adjusts bow tie* The archive has been updated.",
    "Well, well. Another night, meticulously documented.",
    "Attention, fellow scholars of the sixty-four squares.",
    "Breaking news from the back patio, which I was monitoring closely.",
    "I've taken the liberty of writing everything down again.",
    "New entry in the historical record. Please hold your applause.",
    "According to my notes, which are extensive, there is a new recap.",
    "For posterity: another night has been recorded.",
    "*clears throat* The data from the last session is in.",
    "Good news, everyone. I have documentation.",
    "Someone has to keep the records. Naturally, it's me.",
    "Fresh recap. Peer-reviewed by me, personally.",
]

LENNY_FACTS = [
    "Actually, there are exactly 20 legal first moves for White.",
    "Actually, after one move each there are 400 possible positions.",
    "Actually, after two moves each there are 197,281 possible games.",
    "Actually, Claude Shannon estimated about 10^120 possible chess games. The observable universe has roughly 10^80 atoms.",
    "Actually, castling is the only move where two of your own pieces move at once.",
    "Actually, a bishop never leaves the colour it starts on. Loyal. Admirable.",
    "Actually, the queen used to move only one square diagonally. She got her modern powers in the late 1400s.",
    "Actually, \"checkmate\" comes from the Persian \"shah mat\", roughly \"the king is helpless\".",
    "Actually, the Elo rating system is named after Arpad Elo, a physics professor. My kind of guy.",
    "Actually, the first official World Championship was 1886, Steinitz against Zukertort.",
    "Actually, the longest tournament game on record is Nikolić vs Arsović, Belgrade 1989. 269 moves. A draw.",
    "Actually, a knight in the corner controls just two squares. In the centre, eight. Knights on the rim are dim.",
    "Actually, stalemate is a draw, not a win. I will die on this hill.",
    "Actually, the 50-move rule means nobody can shuffle pieces forever without a capture or a pawn move.",
    "Actually, Magnus Carlsen's peak classical rating was 2882, set in 2014.",
    "Actually, a promoting pawn can become a queen, rook, bishop or knight. Never a king. I checked.",
    "Actually, en passant is only legal on the very next move. Use it or lose it.",
    "Actually, a lone king and knight cannot checkmate a lone king. Mathematically impossible.",
    "Actually, the knight is the only piece that can jump over other pieces.",
    "Actually, nothing can block a knight's move, which is exactly why knight forks hurt so much.",
]

# only used when the recap itself mentions the subject
LENNY_TOPICAL = [
    ('960', "Actually, Chess960 has exactly 960 legal starting positions. Bobby Fischer proposed it in 1996."),
    ('960', "Actually, in Chess960 the king always starts between the rooks, so you can still castle."),
    ('fork', "Actually, nothing can block a knight's move, which is exactly why knight forks hurt so much."),
    ('deflection', "Actually, deflection works because a defender can only guard so many things at once. Overworked pieces, I relate."),
    ('rain', "Actually, not even a hurricane has cancelled a club night. The record stands."),
    ('tiki', "Actually, not even a hurricane has cancelled a club night. The record stands."),
    ('karpov', "Actually, Anatoly Karpov was world champion from 1975 to 1985."),
    ('blitz', "Actually, a blitz game gives each player ten minutes or less for the whole game."),
]

LENNY_SIGNOFFS = [
    "\u2014 Lenny \U0001F913",
    "Read it. There will be a quiz. \u2014 Lenny",
    "Citations available on request. \u2014 Lenny",
    "That is all. \u2014 Lenny",
    "Peer review welcome in the replies. \u2014 Lenny",
    "*pushes glasses up again* \u2014 Lenny",
    "Knowledge solves most things. \u2014 Lenny",
    "Curiosity leads further. \u2014 Lenny",
    "Facts > feelings. This recap is a fact. \u2014 Lenny",
    "Carry on. \u2014 Lenny",
    "I'll be in the library. \u2014 Lenny",
    "End of transmission. \u2014 Lenny",
]


def lenny_says(n):
    """Lenny's intro for one night. Same night, same Lenny, every time."""
    rng = random.Random('lenny|' + n['date'])
    no = B.night_number(n['date'])
    text = ' '.join([B.loc(n, 'title', False), B.loc(n, 'line', False), B.loc(n, 'commentary', False)]).lower()
    topical = [f for key, f in LENNY_TOPICAL if re.search(r'%s' % re.escape(key), text)]
    fact = rng.choice(topical) if topical and rng.random() < 0.6 else rng.choice(LENNY_FACTS)
    data = [
        "For the record, that was club night number %d." % no,
        "Night %d. I counted. Twice." % no,
        "That makes %d club nights since 2021, if anyone was keeping score. I was." % no,
        "Archive reference: Night %d, %s." % (no, B.long_date(n['date'], False)),
        "Filed under: %s. Night %d." % (B.night_type(n, False), no),
    ]
    if n.get('played'):
        data.append("%d players attended, a figure I find deeply satisfying." % n['played'])
    return '\n\n'.join(['\U0001F4F0 ' + rng.choice(LENNY_INTROS), fact, rng.choice(data), rng.choice(LENNY_SIGNOFFS)])


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
