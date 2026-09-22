# -*- coding: utf-8 -*-
"""At 2pm Eastern, tell #club-schedule what is on tonight.

The schedule here mirrors build/template.html exactly: Sunday alternates league and
social from the same anchor date, Tuesday is study night, Thursday is the
intermediate+ room at Adobe Kava from 10 September 2026, and anything booked in
events.json takes over the post for that day. If nothing is on, nothing is posted.

GitHub cron only speaks UTC and its scheduled runs are best-effort: ours have landed two
to three hours late. So the workflow runs every hour and this script posts on the first
run at or after 2pm in Bradenton, gives up after 7pm so a post never lands once the night
has started, and records the day in tonight-posted.json so a late or repeated run still
posts exactly once. Working in Bradenton's own clock also keeps daylight saving right
without touching the workflow twice a year.

The webhook for the channel is the CLUB_SCHEDULE secret and is never written in this
repo. Without it the script says so and exits cleanly.
"""
import json
import os
import random
import re
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
# Lenny posts these. Discord fetches the picture itself, so it has to be a public URL.
AVATAR = 'https://kavasocialchessclub.com/img/lenny.png'

# these three constants are the calendar; they must match build/template.html
ANCHOR = date(2026, 8, 30)        # a league Sunday; Sundays alternate league / social
ADOBE_FROM = date(2026, 9, 10)    # first Thursday at Adobe Kava
POST_HOUR = 14                    # 2pm, Bradenton time: the earliest we will post
LATEST_HOUR = 19                  # and the latest, so it never lands after the night has started
LEDGER = os.path.join(OUT, 'tonight-posted.json')   # the day we last posted, so a retry cannot double up


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
# greeting, an opener, a second line, sometimes an aside, sometimes a nudge about the
# next event, and a sign-off. Each is drawn at random and independently, so the pools
# multiply out to thousands of possible posts per night type. `--count` prints the sums.
#
# Study nights say what is actually being studied. The book comes from study.json,
# which changes only when the room finishes a book. Where we have got to comes from the
# last study recap, because the recap already says it and that saves anyone keeping a
# second number up to date. Setting a number in study.json overrides the recap.

GREETINGS = [
    "Hey @everyone!", "Alright @everyone!", "@everyone", "Yo @everyone!",
    "Evening @everyone!", "@everyone, listen up!", "Hey chess people @everyone!",
    "Good afternoon @everyone!", "Right then @everyone!", "@everyone \u265f\ufe0f",
    "Chess tonight @everyone!", "Heads up @everyone!", "Hey all @everyone!",
    "What's good @everyone!",
]

SIGNOFFS = [
    "See you all there!", "See you tonight!", "See you guys tonight!", "Come through!",
    "See you at the boards!", "Let's fill the room!", "See you all at the tables!",
    "Don't be late!", "Bring a friend!", "Come get some games in!",
    "Pull up!", "Hope to see you there!", "The boards will be ready!",
    "Come say hi if you're new!",
]

OPENERS = {
    'league': [
        "Tonight is a league night, so every game counts toward your in-house elo.",
        "League night tonight! Results go straight into the club ladder.",
        "It's a league night, which means real games for real in-house elo.",
        "League night is on. Your bracket, your games, your rating on the line.",
        "Tonight we play for points. League night, in-house elo, the works.",
        "Season games tonight! League night is here again.",
        "League night! Time to find out where you really sit in your bracket.",
        "Tonight's a league night, so the results actually count.",
        "Bracket games tonight. League night, same as always, all levels.",
        "League night! Pairings get sorted for you, you just play.",
        "It's a league night, so tonight's games move the standings.",
        "Ladder night! Every result tonight goes on the record.",
        "League night tonight, and the boards fill up fast.",
        "Tonight is a scoring night. League games, in-house rating.",
    ],
    'social': [
        "Tonight is free play and exhibition matches, and they can still count toward your in-house elo.",
        "Social night tonight! Free play, casual boards, and elo games if you want them.",
        "Free play tonight, with the option to make your games count for in-house elo.",
        "Tonight is the relaxed one. Free play, and you can still challenge for elo.",
        "Social Sunday! Nothing forced, just boards and whoever shows up.",
        "Open boards tonight. Play whoever you like, count it for elo if you want.",
        "Tonight is free play night, so bring whatever mood you're in.",
        "Casual night tonight. No pairings, no brackets, just chess.",
        "Social night! Come play whoever you've been meaning to play.",
        "Tonight's an open night. Challenge anyone, or just watch and talk.",
        "Free play tonight, and exhibition games can still count for elo.",
        "Social night tonight, which is the easiest one to turn up to cold.",
        "Open boards, open invitation. Social night tonight.",
        "Tonight is the loose one. Play for elo or play for fun.",
    ],
    'study': [
        "Study night tonight, carrying on through {book}.",
        "Another study night! We keep working our way through {book}.",
        "Study night tonight. We read a lesson together, then test it over the board.",
        "Tonight we hit the books. Study night, next one in the series.",
        "Study night is on! We keep chipping away at {book}.",
        "Books out tonight. Study night, all levels, same as always.",
        "Study night tonight, and everyone learns something whatever their rating.",
        "It's a study night. We work through it as a room, then we play.",
        "Study night! Bring your brain, we'll bring the book.",
        "Tonight is study night, and we're still making our way through {book}.",
        "Study session tonight. One idea, properly understood, beats ten skimmed.",
        "Study night tonight. Come learn something and then go try it.",
    ],
    # used when a number is set by hand in study.json
    'study_numbered': [
        "Study night tonight! We're up to {unit} {number} of {book}.",
        "Study night tonight, {unit} {number} of {book}.",
        "Tonight we pick up at {unit} {number} of {book}.",
        "Study night! {unit} {number} tonight, still working through {book}.",
        "Another study night. {unit} {number} of {book} is on the table.",
        "Books out! {unit} {number} of {book} tonight.",
        "Study night: {unit} {number}. We're getting through {book} properly.",
        "Tonight's study night, and it's {unit} {number} of {book}.",
    ],
    # used when the number came from the last recap: say where we got to, not where we are
    'study_last': [
        "Study night tonight. Last time we worked through {unit} {number} of {book}, so we carry on from there.",
        "Another study night! We left off at {unit} {number} of {book}.",
        "Study night tonight, picking up after {unit} {number} of {book}.",
        "Books out tonight. We got as far as {unit} {number} of {book} last time.",
        "Study night! {book} again, carrying on from {unit} {number}.",
        "Tonight we keep going through {book}. Last session was {unit} {number}.",
        "Study night tonight, straight on from {unit} {number} of {book}.",
        "We're still deep in {book}. Last time was {unit} {number}, tonight we go further.",
    ],
    'adobe': [
        "Intermediate+ study night at Adobe Kava tonight. Harder material, tougher positions.",
        "Tonight is the intermediate+ room at Adobe Kava, and we go deep.",
        "Adobe Kava tonight for the intermediate+ session. Less hand-holding, more work.",
        "The intermediate+ room runs tonight at Adobe Kava.",
        "Tonight's the harder study room, over at Adobe Kava.",
        "Intermediate+ night at Adobe Kava. This is the one where we really dig in.",
        "Adobe Kava tonight. Intermediate and up, proper working session.",
        "The tougher study room is on tonight at Adobe Kava.",
        "Intermediate+ session tonight at Adobe Kava, for players who want the harder stuff.",
        "Tonight we're at Adobe Kava for the intermediate+ room.",
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
        "Win or lose, it all goes on the record.",
        "Show up and play your games, the software does the rest.",
        "Perfect night to take a scalp off somebody higher rated.",
        "Come defend your spot, or come take someone else's.",
        "The standings look different by midnight, every time.",
        "All brackets running, so there's a game at your level.",
    ],
    'social': [
        "Challenge anyone you want for the rating gains.",
        "Come hang out and get a few games in.",
        "Grab a board, grab an opponent.",
        "Perfect night to bring a friend who's never come before.",
        "No pressure, no pairings, just chess.",
        "Blitz, long games, whatever you're in the mood for.",
        "Easiest night to walk in cold and get playing.",
        "Come for one game or come for six.",
        "Boards are out from eight, stay as long as you like.",
        "Good night to try that opening you've been reading about.",
        "If you've been meaning to come along, this is the night.",
        "Come play, come watch, come talk chess. All fine.",
    ],
    'study': [
        "We go through it together, then put the books away and play.",
        "Everyone's welcome, whatever your level.",
        "No prep needed, just turn up.",
        "Bring a notebook if you like taking notes, plenty of us do.",
        "We work through it as a room, so questions are encouraged.",
        "Then the boards come out and we try it for real.",
        "You don't need to have been to the last one to follow along.",
        "Beginners get just as much out of these as the stronger players.",
        "We take it slowly and nobody gets left behind.",
        "Come learn something you'll actually use on Sunday.",
        "Ask anything. That's the whole point of the night.",
        "Then we test it over the board while it's fresh.",
    ],
    'adobe': [
        "Message Harold first if you haven't been before, this one isn't a drop-in.",
        "Message Harold before you come, it's not a drop-in night.",
        "Not a drop-in night, so check with Harold first.",
        "Message Harold to get a spot, the room is smaller than Sunday.",
        "Check in with Harold first. This one's by arrangement.",
        "Give Harold a message before you head over.",
    ],
}

ASIDES = {
    'home': [
        "We'll get spots under the tiki if the rain comes through.",
        "Back patio as always, covered if the weather turns.",
        "Boards, clocks and scoresheets are all provided.",
        "New faces welcome, just say it's your first night.",
        "21+, and the club is alcohol-free.",
        "Kava Social has us on the back patio as always.",
        "Nothing to pay, nothing to sign up for.",
        "We run until midnight, so late arrivals are fine.",
        "Plenty of sets, so you don't need to bring anything.",
        "If it's your first time, someone will pair you up.",
    ],
    'adobe': [
        "Bring something to write on, this one moves fast.",
        "Smaller room, so it's a proper working session.",
        "We run seven to eleven over there.",
        "Different venue to Sunday, so double-check the address.",
    ],
}

FALLBACK_OPEN = "Club night tonight!"
FALLBACK_SECOND = "Come play."
_UNIT_IN_TEXT = re.compile(r'\b(chapter|lesson)\s+(\d+)\b', re.I)


def latest_study_reference():
    """Where the room got to, read out of the most recent study recap."""
    try:
        nights = json.load(open(os.path.join(OUT, 'nights.json'), encoding='utf-8')).get('nights', [])
    except Exception:
        return {}
    for n in sorted(nights, key=lambda x: x.get('date', ''), reverse=True):
        if n.get('type') not in ('study', 'adobe'):
            continue
        m = _UNIT_IN_TEXT.search('%s %s' % (n.get('title') or '', n.get('commentary') or ''))
        if m:
            return {'unit': m.group(1).lower(), 'number': int(m.group(2)), 'date': n.get('date')}
    return {}


def study_plan():
    """The book, and where we are. Nothing here is ever guessed."""
    try:
        d = json.load(open(os.path.join(OUT, 'study.json'), encoding='utf-8'))
    except Exception:
        d = {}
    book = (d.get('book') or '').strip()
    if not book:
        return {}
    plan = {'book': book, 'unit': (d.get('unit') or 'chapter').strip().lower()}
    try:
        n = int(d.get('number'))
        if n > 0:
            plan['number'], plan['source'] = n, 'plan'
    except (TypeError, ValueError):
        pass
    if 'number' not in plan:
        ref = latest_study_reference()
        if ref:
            plan.update(number=ref['number'], unit=ref['unit'], source='recap')
    return plan


def study_pool(plan):
    """Only offer wordings the facts can actually fill in."""
    pool = [x for x in OPENERS['study'] if '{book}' not in x or plan.get('book')]
    if plan.get('book') and plan.get('number'):
        pool += OPENERS['study_numbered' if plan.get('source') == 'plan' else 'study_last']
    return pool


def fill(line, plan):
    if not plan:
        return line
    return (line.replace('{book}', plan.get('book', ''))
                .replace('{unit}', plan.get('unit', 'chapter'))
                .replace('{number}', str(plan.get('number', ''))))


def draw(pool, fallback=None):
    return random.choice(pool) if pool else fallback


def chance(one_in):
    return random.randrange(one_in) == 0


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
    return draw(shapes)


def time_words(raw):
    """'8:00 PM' reads better as '8pm', and '8:10 PM' has to keep its minutes."""
    t = (raw or '8:00 PM').strip()
    return t.replace(':00 ', '').replace(' ', '').lower()


def message(day, on, events=()):
    """The post, as Discord will see it. Every part is drawn on its own."""
    e = on[0]
    kind = e.get('type', '')
    when = time_words(e.get('time'))
    hello, bye = draw(GREETINGS), draw(SIGNOFFS)

    if kind in ('study', 'league', 'social', 'adobe'):
        plan = study_plan() if kind == 'study' else {}
        pool = study_pool(plan) if kind == 'study' else OPENERS[kind]
        first = fill(draw(pool, FALLBACK_OPEN), plan)
        second = draw(SECONDS[kind], FALLBACK_SECOND)
        where = ' at Adobe Kava' if kind == 'adobe' else ''
        parts = [first, second]
        if chance(3):
            aside = draw(ASIDES['adobe' if kind == 'adobe' else 'home'])
            if aside:
                parts.append(aside)
        parts.append('Starts at %s%s. %s' % (when, where, bye))
        nudge = countdown(day, events) if chance(3) else None
        if nudge:
            parts.insert(len(parts) - 1, nudge)
    else:
        # booked in the calendar: let the listing speak, it is what people need
        title = e.get('title') or 'Club event'
        note = ' '.join((e.get('note') or '').split())
        if len(note) > 260:
            note = note[:260].rsplit(' ', 1)[0] + '\u2026'
        parts = ['**%s** tonight!' % title]
        if note:
            parts.append(note)
        parts.append('Kicks off at %s at %s. %s' % (when, e.get('venue') or 'Kava Social Club', bye))
    return hello + '\n\n' + '\n\n'.join(parts)


def combinations():
    """How many different posts each night type can produce."""
    plan = study_plan()
    out = {}
    for kind in ('league', 'social', 'study', 'adobe'):
        openers = len(study_pool(plan)) if kind == 'study' else len(OPENERS[kind])
        asides = len(ASIDES['adobe' if kind == 'adobe' else 'home'])
        out[kind] = len(GREETINGS) * openers * len(SECONDS[kind]) * (1 + asides) * len(SIGNOFFS)
    return out


def send(hook, text):
    payload = {'content': text, 'allowed_mentions': {'parse': ['everyone']},
               'avatar_url': AVATAR, 'username': 'Lenny'}
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


def last_posted():
    try:
        return json.load(open(LEDGER, encoding='utf-8')).get('last', '')
    except Exception:
        return ''


def remember(day):
    json.dump({'_comment': 'The last day the schedule post went out. Written by build/post_tonight.py.',
               'last': day.isoformat()}, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(LEDGER, 'a', encoding='utf-8').write(chr(10))


def main(argv):
    if '--count' in argv:
        plan = study_plan()
        print('study plan: %s' % (plan or 'none set; study nights stay general'))
        for kind, n in sorted(combinations().items()):
            print('  %-7s %8d different posts' % (kind, n))
        return 0
    dry = '--dry' in argv
    force = '--force' in argv
    day_arg = [a for a in argv if a.startswith('--date=')]

    if day_arg:
        day = date(*(int(x) for x in day_arg[0].split('=', 1)[1].split('-')))
    elif EASTERN:
        now = datetime.now(EASTERN)
        day = now.date()
        if not (dry or force):
            # GitHub's schedules are best-effort and can run hours late, so the workflow runs every
            # hour and this posts on the first run inside the window that has not already posted.
            if now.hour < POST_HOUR:
                print('Too early in Bradenton (%02d:%02d); waiting for %d:00.' % (now.hour, now.minute, POST_HOUR))
                return 0
            if now.hour >= LATEST_HOUR:
                print('Too late in Bradenton (%02d:%02d); the night is about to start, so nothing posted.'
                      % (now.hour, now.minute))
                return 0
            if last_posted() == day.isoformat():
                print('Already posted for %s.' % day.isoformat())
                return 0
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
    remember(day)
    print('Posted the %s for %s.' % (on[0].get('type', 'event'), day.isoformat()))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
