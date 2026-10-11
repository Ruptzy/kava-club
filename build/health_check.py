# -*- coding: utf-8 -*-
"""Check every key and connection the club's automation depends on, without posting anything.

    python build/health_check.py

Each secret is asked a read-only question: Brevo is asked for the account and the list, each
Discord webhook is asked for its own name (a GET posts nothing), Google is asked for the
listing's rating. Secrets are never printed. A failed check makes the run fail, which makes
GitHub email the repository owner.

The admin page's own token (kava-site) lives only on Harold's phone, so it cannot be checked
from here: unlocking it on the admin page is the test.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://kavasocialchessclub.com/'
UA = 'KavaSocialChessClub-health (https://kavasocialchessclub.com, 1.0)'
results = []


def get(url, headers=None, method='GET'):
    req = urllib.request.Request(url, method=method)
    req.add_header('User-Agent', UA)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw[:1] in (b'{', b'[') else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, str(e)[:80]


def check(area, name, ok, detail):
    results.append((area, name, ok, detail))


def secret(name):
    return os.environ.get(name, '').strip()


# ------------------------------------------------------------------ Brevo (the weekly email)
key = secret('BREVO_API_KEY')
if not key:
    check('Weekly email', 'Brevo key', False, 'BREVO_API_KEY is missing')
else:
    h = {'api-key': key, 'accept': 'application/json'}
    code, acct = get('https://api.brevo.com/v3/account', h)
    if code != 200:
        check('Weekly email', 'Brevo key', False, 'Brevo answered %s: the key is wrong or revoked' % code)
    else:
        plans = ', '.join('%s (%s credits)' % (p.get('type'), p.get('credits')) for p in acct.get('plan', []))
        check('Weekly email', 'Brevo key', True, 'accepted; plan: %s' % (plans or 'unknown'))
        code, lists = get('https://api.brevo.com/v3/contacts/lists?limit=50', h)
        club = [l for l in (lists or {}).get('lists', []) if l.get('name', '').strip().lower() == 'club members']
        check('Weekly email', 'Member list', bool(club),
              ('"Club members": %s contacts' % club[0].get('uniqueSubscribers', club[0].get('totalSubscribers')))
              if club else 'no list called "Club members"')
        code, snd = get('https://api.brevo.com/v3/senders', h)
        own = [s for s in (snd or {}).get('senders', []) if s.get('active') and s.get('email', '').endswith('@kavasocialchessclub.com')]
        check('Weekly email', 'Sender', bool(own), 'an active sender on kavasocialchessclub.com' if own else 'no active club sender')
        try:
            led = json.load(open(os.path.join(OUT, 'email-sent.json'), encoding='utf-8'))
        except Exception:
            led = {}
        if led.get('id'):
            code, camp = get('https://api.brevo.com/v3/emailCampaigns/%s' % led['id'], h)
            st = (camp or {}).get('status')
            check('Weekly email', 'Next/last campaign', st in ('queued', 'sent', 'in_process'),
                  'campaign %s for %s is "%s"' % (led['id'], led.get('last', '?').replace('weekly-', ''), st))
reply = secret('REPLY_TO')
check('Weekly email', 'Reply-to address', bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', reply)),
      'set and shaped like an email address' if reply else 'REPLY_TO is missing (replies go to club@ instead)')

# ------------------------------------------------------------------ Discord webhooks
for sec, what in (('NIGHT_RECAPS', 'Recap posts (+ Lenny)'), ('SCHEDULE_FOR_DAY', '3pm "tonight" post'),
                  ('DISCORD_WEBHOOK', 'Monthly schedule post')):
    hook = secret(sec)
    if not hook:
        check('Discord', what, False, '%s is missing' % sec)
        continue
    if not re.match(r'https://(discord|discordapp)\.com/api/webhooks/\d+/', hook):
        check('Discord', what, False, '%s does not look like a Discord webhook' % sec)
        continue
    code, info = get(hook)
    check('Discord', what, code == 200,
          ('webhook "%s" is live' % (info or {}).get('name', '?')) if code == 200
          else 'Discord answered %s: the webhook was deleted or its channel is gone' % code)

# ------------------------------------------------------------------ Google (reviews on the site)
gkey = secret('GOOGLE_PLACES_KEY')
if not gkey:
    check('Google reviews', 'Places key', False, 'GOOGLE_PLACES_KEY is missing')
else:
    place = secret('GOOGLE_PLACE_ID') or 'ChIJ-bv_E6gXw4gREBFXmc5jeEY'
    code, p = get('https://places.googleapis.com/v1/places/%s' % place,
                  {'X-Goog-Api-Key': gkey, 'X-Goog-FieldMask': 'displayName,rating,userRatingCount'})
    check('Google reviews', 'Places key', code == 200,
          ('%s: %s stars from %s reviews' % ((p or {}).get('displayName', {}).get('text', '?'), (p or {}).get('rating'),
                                              (p or {}).get('userRatingCount'))) if code == 200
          else 'Google answered %s: the key is wrong, restricted or out of quota' % code)

# ------------------------------------------------------------------ what members see
pages = [('Home page', ''), ('Calendar', 'calendar/'), ('Night recaps', 'nights/'), ('Admin page', 'admin/'),
         ('Email logo', 'img/email/logo-tile.png'), ('Email map pin', 'img/email/directions-tile.png')]
try:
    latest = sorted(json.load(open(os.path.join(OUT, 'nights.json'), encoding='utf-8'))['nights'],
                    key=lambda n: n['date'])[-1]['date']
    pages.append(('Latest recap (%s)' % latest, 'nights/%s/' % latest))
except Exception:
    pass
for name, path in pages:
    code, _ = get(SITE + path, method='HEAD')
    check('Website', name, code == 200, 'online' if code == 200 else 'answered %s' % code)
code, _ = get('https://ladder.kavasocialchessclub.com/', method='HEAD')
check('Website', 'Ladder', code == 200, 'online' if code == 200 else 'answered %s' % code)
code, c = get('https://kavasocialchessclub.goatcounter.com/counter/TOTAL.json')
check('Website', 'Visitor counter (polls)', code == 200, 'public counter answering' if code == 200 else 'answered %s' % code)

# ------------------------------------------------------------------ club@ mail
code, mx = get('https://dns.google/resolve?name=kavasocialchessclub.com&type=MX')
hosts = ' '.join(a.get('data', '') for a in (mx or {}).get('Answer', []))
check('club@ mail', 'Forwarding (ImprovMX)', 'improvmx' in hosts, 'MX points at ImprovMX' if 'improvmx' in hosts else 'no ImprovMX MX record')
code, txt = get('https://dns.google/resolve?name=kavasocialchessclub.com&type=TXT')
spf = [a.get('data', '') for a in (txt or {}).get('Answer', []) if 'v=spf1' in a.get('data', '')]
good = len(spf) == 1 and 'spf.improvmx.com' in spf[0] and 'spf.brevo.com' in spf[0]
check('club@ mail', 'SPF record', good, 'one record, covers ImprovMX and Brevo' if good else 'found %d SPF records: %s' % (len(spf), spf))

# ------------------------------------------------------------------ report
bad = [r for r in results if not r[2]]
area = None
for a, n, ok, d in results:
    if a != area:
        print('\n' + a.upper())
        area = a
    print('  %s  %-28s %s' % ('PASS' if ok else 'FAIL', n, d))
print('\n%d checks, %d passed, %d failed.' % (len(results), len(results) - len(bad), len(bad)))
sys.exit(1 if bad else 0)
