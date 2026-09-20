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


# The post is assembled from parts, not chosen from a list of finished messages: a
# greeting, an opener, a second line, sometimes an aside, and a sign-off, each drawn on
# its own from the date. That is thousands of combinations per night type rather than a
# handful, so the channel never reads like the same message coming round again. A given
# date always produces the same post, so a re-run cannot contradict itself.

GREETINGS = ["Hey @everyone!", "Alright @everyone!", "@everyone", "Yo @everyone!",
             "Evening @everyone!", "@everyone, listen up!", "Hey chess people @everyone!"]

OPENERS = {
    'league': [
        "Tonight is a league night, so every game counts toward your in-house elo.",
        "League night tonight! Results go straight into the club ladder.",
        "It's a league night, which means real games for real in-house elo.",
        "League night is on. Your bracket, your games, your rating on the line.",
        "Tonight we play for points. League night, in-house elo, the works.",
        "Season games tonight! League night is here again.",
        "League night! Time to find out where you really sit in your bracket.",
    ],
    'social': [
        "Tonight is free play and exhibition matches, and they can still count toward your in-house elo.",
        "Social night tonight! Free play, casual boards, and elo games if you want them.",
        "Free play tonight, with the option to make your games count for in-house elo.",
        "Tonight is the relaxed one. Free play, and you can still challenge for elo.",
        "Social Sunday! Nothing forced, just boards and whoever shows up.",
        "Open boards tonight. Play whoever you like, count it for elo if you want.",
        "Tonight is free play night, so bring whatever mood you're in.",
    ],
    'study': [
        "Study night tonight, carrying on through 40 Lessons for the Club Player.",
        "Another study night! We keep working our way through 40 Lessons for the Club Player.",
        "Study night tonight. We read a lesson together, then test it over the board.",
        "Tonight we hit the books. Study night, next lesson in the series.",
        "Study night is on! We keep chipping away at 40 Lessons for the Club Player.",
        "Books out tonight. Study night, all levels, same as always.",
        "Study night tonight, and everyone learns something whatever their rating.",
    ],
    'adobe': [
        "Intermediate+ study night at Adobe Kava tonight. Harder material, tougher positions.",
        "Tonight is the intermediate+ room at Adobe Kava, and we go deep.",
        "Adobe Kava tonight for the intermediate+ session. Less hand-holding, more work.",
        "The intermediate+ room runs tonight at Adobe Kava.",
        "Tonight's the harder study room, over at Adobe Kava.",
    ],
}

SECONDS = {
    'league': [
        "Challenge whoever you like and go get those points.",
        "Come pick up some rating, or take some off somebody else.",
        "Bring your best and let's get the boards full.",
        "Every result moves the ladder, so play like it.",
        "Good chance to close the gap on whoever's above you.",
        "Pairings are handled, you just have to turn up and play.",
    ],
    'social': [
        "Challenge anyone you want for the rating gains.",
        "Come hang out and get a few games in.",
        "Grab a board, grab an opponent.",
        "Perfect night to bring a friend who's never come before.",
        "No pressure, no pairings, just chess.",
        "Blitz, long games, whatever you're in the mood for.",
    ],
    'study': [
        "We go through it together, then put the books away and play.",
        "Everyone's welcome, whatever your level.",
        "No prep needed, just turn up.",
        "Bring a notebook if you like taking notes, plenty of us do.",
        "We work through it as a room, so questions are encouraged.",
        "Then the boards come out and we try it for real.",
    ],
    'adobe': [
        "Message Harold first if you haven't been before, this one isn't a drop-in.",
        "Message Harold before you come, it's not a drop-in night.",
        "Not a drop-in night, so check with Harold first.",
    ],
}

# occasional colour, added maybe a third of the time
ASIDES = {
    'home': [
        "We'll get spots under the tiki if the rain comes through.",
        "Back patio as always, covered if the weather turns.",
        "Boards, clocks and scoresheets are all provided.",
        "New faces welcome, just say it's your first night.",
        "21+, and the club is alcohol-free.",
        "Kava Social has us on the back patio as always.",
    ],
    'adobe': [
        "Bring something to write on, this one moves fast.",
        "Smaller room, so it's a proper working session.",
    ],
}

SIGNOFFS = ["See you all there!", "See you tonight!", "See you guys tonight!",
            "Come through!", "See you at the boards!", "Let's fill the room!",
            "See you all at the tables!", "Don't be late!"]

FALLBACK_OPEN = "Club night tonight!"
FALLBACK_SECOND = "Come play."


def draw(pool, day, slot, fallback=None):
    """Pick one item, using a hash stream of its own so the slots vary independently."""
    if not pool:
        return fallback
    seed = int(hashlib.sha256(('%s|%s' % (slot, day.isoformat())).encode()).hexdigest()[:12], 16)
    return pool[seed % len(pool)]


def chance(day, slot, one_in):
    seed = int(hashlib.sha256(('roll|%s|%s' % (slot, day.isoformat())).encode()).hexdigest()[:12], 16)
    return seed % one_in == 0


def countdown(day, events):
    """A nudge about the next booked event, but only when it is close and not today."""
    ahead = sorted(e for e in (x.get('date') for x in events) if e and e > day.isoformat())
    if not ahead:
        return None
    nxt = [e for e in events if e.get('date') == ahead[0]][0]
    days = (date(*(int(x) for x in ahead[0].split('-'))) - day).days
    if days > 21:
        return None
    when = 'tomorrow' if days == 1 else 'in %d days' % days
    title = nxt.get('title') or 'our next event'
    shapes = ['%s is %s, by the way.' % (title, when),
              'Heads up: %s is %s.' % (title, when),
              "Don't forget %s, %s." % (title, when),
              '%s %s. Get ready.' % (title, 'is ' + when if days > 1 else 'is tomorrow')]
    return draw(shapes, day, 'countword')


def time_words(raw):
    """'8:00 PM' reads better as '8pm', and '8:10 PM' has to keep its minutes."""
    t = (raw or '8:00 PM').strip()
    return t.replace(':00 ', '').replace(' ', '').lower()


def message(day, on, events=()):
    """The post, as Discord will see it. Every part is drawn separately."""
    e = on[0]
    kind = e.get('type', '')
    when = time_words(e.get('time'))
    hello = draw(GREETINGS, day, 'hello')
    bye = draw(SIGNOFFS, day, 'bye')

    if kind in OPENERS:
        first = draw(OPENERS[kind], day, 'open' + kind, FALLBACK_OPEN)
        second = draw(SECONDS[kind], day, 'second' + kind, FALLBACK_SECOND)
        where = ' at Adobe Kava' if kind == 'adobe' else ''
        parts = [first, second]
        if chance(day, 'aside', 3):
            aside = draw(ASIDES['adobe' if kind == 'adobe' else 'home'], day, 'aside' + kind)
            if aside:
                parts.append(aside)
        parts.append('Starts at %s%s. %s' % (when, where, bye))
    else:
        # booked in the calendar: let the listing speak, it is the thing people need
        title = e.get('title') or 'Club event'
        note = ' '.join((e.get('note') or '').split())
        if len(note) > 260:
            note = note[:260].rsplit(' ', 1)[0] + '…'
        parts = ['**%s** tonight!' % title]
        if note:
            parts.append(note)
        parts.append('Kicks off at %s at %s. %s' % (when, e.get('venue') or 'Kava Social Club', bye))

    nudge = countdown(day, events) if kind in OPENERS and chance(day, 'count', 3) else None
    if nudge:
        parts.insert(len(parts) - 1, nudge)
    return hello + '\n\n' + '\n\n'.join(parts)


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
    text = message(day, on, events)

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
