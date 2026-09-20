# -*- coding: utf-8 -*-
"""At 2pm Eastern, tell #club-schedule what is on tonight.

The schedule here mirrors build/template.html exactly: Sunday alternates league and
social from the same anchor date, Tuesday is study night, Thursday is the
intermediate+ room at Adobe Kava from 10 September 2026, and anything booked in
events.json takes over the post for that day. If nothing is on, nothing is posted.

GitHub cron only speaks UTC, so the workflow fires at both 18:00 and 19:00 UTC and this
script posts only when it really is 2pm in Bradenton. That keeps the time right on both
sides of daylight saving without touching the workflow twice a year.

The webhook for the channel is the CLUB_SCHEDULE secret and is never written in this
repo. Without it the script says so and exits cleanly.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo('America/New_York')
except Exception:                                  # pragma: no cover
    EASTERN = None

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
UA = 'KavaSocialChessClub-schedule (https://kavasocialchessclub.com, 1.0)'

# these three constants are the calendar; they must match build/template.html
ANCHOR = date(2026, 8, 30)        # a league Sunday; Sundays alternate league / social
ADOBE_FROM = date(2026, 9, 10)    # first Thursday at Adobe Kava
POST_HOUR = 14                    # 2pm, Bradenton time


def whats_on(day, events):
    """Everything happening on this date, the booked event first if there is one."""
    booked = [e for e in events if e.get('date') == day.isoformat()]
    if booked:
        return booked
    wd = day.weekday()                              # Monday is 0
    if wd == 6:
        league = ((day - ANCHOR).days // 7) % 2 == 0
        return [{'type': 'league', 'time': '8:00 PM'} if league else {'type': 'social', 'time': '8:00 PM'}]
    if wd == 1:
        return [{'type': 'study', 'time': '8:00 PM'}]
    if wd == 3 and day >= ADOBE_FROM:
        return [{'type': 'adobe', 'time': '7:00 PM', 'venue': 'Adobe Kava'}]
    return []


# a few wordings per night, so the channel does not read like a robot.
# picked by the date, so the same night never gets the same opener two weeks running.
LINES = {
    'league': [
        ("Tonight is a league night, so every game you play counts toward your in-house elo.",
         "Challenge whoever you like and go get those points."),
        ("League night tonight! Your results go straight into the club ladder.",
         "Come pick up some rating, or take some off somebody else."),
        ("It's a league night, which means real games for real in-house elo.",
         "Bring your best and let's get the boards full."),
    ],
    'social': [
        ("Tonight is free play and exhibition matches, and you can still have them count toward your in-house elo.",
         "Challenge anyone you want for the rating gains."),
        ("Social night tonight! Free play, casual boards, and elo games if you want them.",
         "Come hang out and get a few games in."),
        ("Free play tonight, with the option to make your games count for in-house elo.",
         "Grab a board, grab an opponent."),
    ],
    'study': [
        ("Study night tonight, carrying on through 40 Lessons for the Club Player.",
         "We go through it together, then put the books away and play."),
        ("Another study night! We keep working our way through 40 Lessons for the Club Player.",
         "Everyone's welcome, whatever your level."),
        ("Study night tonight. We read a lesson together, then test it over the board.",
         "No prep needed, just turn up."),
    ],
    'adobe': [
        ("Intermediate+ study night at Adobe Kava tonight. Harder material, tougher positions, less hand-holding.",
         "Message Harold first if you haven't been before, this one isn't a drop-in."),
        ("Tonight is the intermediate+ room at Adobe Kava, and we go deep.",
         "Message Harold before you come, it's not a drop-in night."),
    ],
}
FALLBACK = ("Club night tonight!", "Come play.")


def pick(kind, day):
    """Same night, different opener week to week, but always the same for a given date."""
    opts = LINES.get(kind)
    if not opts:
        return FALLBACK
    seed = int(hashlib.sha256(('%s|%s' % (kind, day.isoformat())).encode()).hexdigest()[:8], 16)
    return opts[seed % len(opts)]


def message(day, on):
    """The post, as Discord will see it."""
    e = on[0]
    kind = e.get('type', '')
    when = (e.get('time') or '8:00 PM').replace(':00 ', '').lower().replace(' ', '')
    if kind in LINES:
        first, second = pick(kind, day)
        where = ' at Adobe Kava' if kind == 'adobe' else ''
        body = '%s\n\n%s\n\nStarts at %s%s. See you all there!' % (first, second, when, where)
    else:
        # something booked in the calendar: use what the listing itself says
        title = e.get('title') or 'Club event'
        note = ' '.join((e.get('note') or '').split())
        if len(note) > 260:
            note = note[:260].rsplit(' ', 1)[0] + '…'
        venue = e.get('venue') or 'Kava Social Club'
        body = '**%s** tonight!%s\n\nKicks off at %s at %s. See you there!' % (
            title, ('\n\n' + note) if note else '', when, venue)
    return 'Hey @everyone!\n\n' + body


def send(hook, text):
    payload = {'content': text, 'allowed_mentions': {'parse': ['everyone']}}
    req = urllib.request.Request(hook.split('?')[0] + '?wait=true',
                                 data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        raise RuntimeError('Discord said %d: %s' % (e.code, e.read()[:300]))


def main(argv):
    dry = '--dry' in argv
    force = '--force' in argv
    day_arg = [a for a in argv if a.startswith('--date=')]

    if day_arg:
        day = date(*(int(x) for x in day_arg[0].split('=', 1)[1].split('-')))
    elif EASTERN:
        now = datetime.now(EASTERN)
        if now.hour != POST_HOUR and not (dry or force):
            print('Not 2pm in Bradenton (it is %02d:%02d there); the other cron will do it.'
                  % (now.hour, now.minute))
            return 0
        day = now.date()
    else:
        print('No timezone database available; not guessing at the hour.')
        return 0

    events = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8')).get('events', [])
    on = whats_on(day, events)
    if not on:
        print('Nothing on %s; nothing posted.' % day.isoformat())
        return 0
    text = message(day, on)

    if dry:
        print('--- %s (%s) ---\n%s\n' % (day.isoformat(), day.strftime('%A'), text))
        return 0

    hook = os.environ.get('CLUB_SCHEDULE', '').strip()
    if not hook:
        print('No CLUB_SCHEDULE secret set, nothing posted.')
        return 0
    if not hook.startswith(('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/')):
        print('The secret does not look like a Discord webhook URL; nothing posted.')
        return 0
    send(hook, text)
    print('Posted the %s for %s.' % (on[0].get('type', 'event'), day.isoformat()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
