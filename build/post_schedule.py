"""Post the month's schedule to Discord. Run by .github/workflows/schedule-post.yml on the
first of each month, and by hand from the Actions tab.

Needs DISCORD_WEBHOOK (a webhook URL for #club-schedule).
Optional: MONTH=YYYY-MM to post a specific month instead of the current one.

Every date goes out as a Discord timestamp, so each member sees it in their own timezone
and gets "in 3 days" on hover. The recurring nights are worked out the same way the website
works them out, so the two can never drift.
"""
import json, os, sys, calendar, urllib.request, urllib.error
from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('America/New_York')
except Exception:
    TZ = None

WEBHOOK = os.environ.get('DISCORD_WEBHOOK', '').strip()
if not WEBHOOK:
    sys.exit('DISCORD_WEBHOOK is not set (add it as a GitHub Actions secret)')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = 'https://kavasocialchessclub.com/'
ANCHOR = date(2026, 8, 30)          # a league Sunday; league every 14 days
THURSDAYS_FROM = date(2026, 9, 10)  # the Adobe Kava night started here
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December']


def stamp(d, hour, minute=0, style='f'):
    """A Discord timestamp: shown in each reader's own timezone, relative time on hover."""
    dt = datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ) if TZ else datetime(d.year, d.month, d.day, hour, minute)
    return '<t:%d:%s>' % (int(dt.timestamp()), style)


def league_sunday(d):
    return ((d - ANCHOR).days // 7) % 2 == 0


def month_wanted():
    m = os.environ.get('MONTH', '').strip()
    if m:
        y, mo = m.split('-')
        return int(y), int(mo)
    now = datetime.now(TZ) if TZ else datetime.utcnow()
    return now.year, now.month


year, month = month_wanted()
first = date(year, month, 1)
last = date(year, month, calendar.monthrange(year, month)[1])
days = [first + timedelta(days=i) for i in range((last - first).days + 1)]

sundays = [d for d in days if d.weekday() == 6]
tuesdays = [d for d in days if d.weekday() == 1]
thursdays = [d for d in days if d.weekday() == 3 and d >= THURSDAYS_FROM]

booked = []
try:
    doc = json.load(open(os.path.join(ROOT, 'events.json'), encoding='utf-8'))
    for e in doc.get('events', []):
        d = date.fromisoformat(e['date'])
        if first <= d <= last:
            booked.append((d, e))
    booked.sort(key=lambda x: x[0])
except Exception as ex:
    print('events.json unreadable, carrying on without booked events:', ex)

fields = []
if sundays:
    fields.append({
        'name': 'Sundays · 8PM to midnight',
        'value': '\n'.join('%s — %s' % (stamp(d, 20), 'League night' if league_sunday(d) else 'Social Sunday')
                           for d in sundays)[:1024],
        'inline': False})
if tuesdays:
    fields.append({
        'name': 'Tuesdays · study night, 8PM to midnight',
        'value': '\n'.join(stamp(d, 20) for d in tuesdays)[:1024],
        'inline': False})
if thursdays:
    fields.append({
        'name': 'Thursdays · Intermediate+ at Adobe Kava, 7–11PM',
        'value': ('\n'.join(stamp(d, 19) for d in thursdays)
                  + '\nMessage Harold first — this one is not a drop-in.')[:1024],
        'inline': False})
for d, e in booked:
    hour, minute = 20, 0
    t = (e.get('time') or '').strip().upper().replace('.', '')
    try:
        if t:
            head = t.split('–')[0].split('-')[0].strip()
            pm = 'PM' in head
            hm = head.replace('AM', '').replace('PM', '').strip()
            hour = int(hm.split(':')[0]); minute = int(hm.split(':')[1]) if ':' in hm else 0
            if pm and hour < 12:
                hour += 12
    except Exception:
        pass
    body = [stamp(d, hour, minute)]
    if e.get('venue'):
        body.append(e['venue'] + (' · ' + e['addr'].split(', ', 1)[1] if e.get('addr') and ', ' in e['addr'] else ''))
    if e.get('note'):
        body.append(e['note'])
    if e.get('url'):
        body.append('[Details and registration](%s)' % e['url'])
    fields.append({'name': '★ ' + e.get('title', 'Event'), 'value': '\n'.join(body)[:1024], 'inline': False})

payload = {
    'username': 'Kava Social Chess Club',
    'embeds': [{
        'title': '%s %d at the club' % (MONTHS[month - 1], year),
        'url': SITE + '#events',
        'color': 0xFE273A,
        'description': ('Every date below shows in your own timezone — hover for how far off it is.\n'
                        '[Full calendar](%s#events) · [Season standings](https://ladder.kavasocialchessclub.com/)'
                        % SITE),
        'fields': fields[:25],
        'footer': {'text': 'Kava Social Club · 540 13th St W, Bradenton · 21+ · every level welcome'},
    }],
}

# Discord sits behind Cloudflare, which rejects the default urllib user agent outright
req = urllib.request.Request(WEBHOOK, data=json.dumps(payload).encode(),
                             headers={'Content-Type': 'application/json',
                                      'User-Agent': 'KavaSocialChessClub/1.0 (+https://kavasocialchessclub.com)'})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print('posted %s %d to Discord (%s) — %d recurring blocks, %d booked event(s)'
              % (MONTHS[month - 1], year, r.status, len(fields) - len(booked), len(booked)))
except urllib.error.HTTPError as e:
    sys.exit('Discord refused the post (%s): %s' % (e.code, e.read().decode('utf-8', 'replace')[:300]))
