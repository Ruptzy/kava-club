# -*- coding: utf-8 -*-
"""Build the weekly member email from the recaps and the calendar.

    python build/build_email.py [--date=YYYY-MM-DD] [--out=DIR]

Writes email.html, email.txt and meta.json (subject, preheader, campaign name) to DIR,
and an email-sized photo to img/email/. It sends nothing: a separate step hands the
result to the email service, which does the scheduling and the tracking.

No member data lives here or anywhere in this repository. The list exists only inside
the email service.

Why it is built the way it is
-----------------------------
* 84% of the list is on Gmail and two thirds of the site's visitors are on phones, so
  this is designed for the Gmail app on a phone first: one column, 17px body text,
  buttons at least 48px tall, and nothing that depends on a web font, which Gmail drops.
* Gmail clips a message at 102KB and hides everything after, including the unsubscribe
  link. The build fails if the HTML passes 80KB.
* Many clients hold images back until asked. Every fact a reader needs (what happened,
  what is on, when, where) is live text; the photo and the logo are extras.
* One idea per section and one button per idea. The recap button comes first because
  the recap is what the email is for.
* Each link carries its own utm_content, so the report can tell the recap button from
  the come-back button. That second number is the one that says whether it is working.
* If no recap was posted since the last email, it builds nothing and says so.
* A recap can carry an "email" block in nights.json for a week when one story should
  own the email: {"lead": true} holds the top even if a later recap is posted, and
  subject, preheader, title, intro, wins ([award, name, note] rows), body (a list of
  paragraphs) and button replace what would otherwise be taken from the recap; also (how many other
  recaps to list, 3 by default) and comeback ({label, title, text, button}) trim and reword the rest;
  intro "" drops the opening paragraph, and notes "booked" keeps calendar notes only for one-off events;
  press ([{source, title, url, note}]) adds a small "In the press" item under the standings.
"""
import html
import json
import os
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_nights as B          # noqa: E402
import post_tonight as T          # noqa: E402

OUT = B.OUT
SITE = 'https://kavasocialchessclub.com/'
LADDER = 'https://ladder.kavasocialchessclub.com/'
MAPS = 'https://maps.google.com/?q=Kava+Social+Club,+540+13th+St+W,+Bradenton,+FL+34205'
SOCIAL = [('Instagram', 'https://www.instagram.com/kavasocialchessclub/'),
          ('Facebook', 'https://www.facebook.com/KavaSocialChessClub'),
          ('Discord', 'https://discord.gg/sYCb7RnTgZ'),
          ('Directions', MAPS)]
# the Gmail app in dark mode flips any picture that is mostly black, so the map pin sits on a
# white tile like the Maps app icon and the club's badge sits large on a red tile (the plain dark
# badge came out as a white negative on Harold's Android phone; small on red it was hard to see)
ICON = {'Directions': 'directions-tile'}
ADDRESS = 'Kava Social Chess Club · Kava Social Club, 540 13th St W, Bradenton, FL 34205'
MAX_BYTES = 80 * 1024
COMEBACK = {'label': 'Haven’t played lately', 'title': 'Been a while?',
            'text': 'Nothing has changed. No dues, nothing to bring, and nobody keeps track of how long you were gone. '
                    'Sundays and Tuesdays at eight, same back patio. Pull up a chair.',
            'button': 'Come back this week'}

VOID, PANEL, CREAM, INK2, INK3, SCARLET, RULE, GOLD = (
    '#0C0D0E', '#17181B', '#FFF6E8', '#C9CCD1', '#9A9DA3', '#FE273A', '#2A2C31', '#E4B02F')
TILE = '#222428'
# Gmail drops web fonts, and its serif and typewriter fallbacks are what made this look old,
# so everything is the phone's own sans. FD, FS and FM stay separate names for the jobs they do.
FD = FS = FM = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
KIND_EMOJI = {'league': '\u265f\ufe0f', 'social': '\u2615', 'study': '\U0001F4DA', 'adobe': '\U0001F9E0', 'battle': '\u2694\ufe0f',
              'theme': '\U0001F389', 'outing': '\U0001F3AC'}
GRID = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">'
PLAIN = '<table role="presentation" cellpadding="0" cellspacing="0" border="0">'

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December']
NIGHT_NAMES = {'league': 'League night', 'social': 'Social Sunday', 'study': 'Study night',
               'adobe': 'Intermediate+ study'}
NIGHT_BLURB = {'league': 'Season games in your bracket. In-house ratings, just for fun.',
               'social': 'Free play. Nothing to sign up for, just turn up.',
               'adobe': 'Harder material, smaller room. Message Harold first.'}

esc = lambda t: html.escape(str(t), quote=True)


def d8(s):
    return date(*(int(x) for x in s.split('-')))


def nice(day, year=False):
    return '%s %d %s%s' % (DAYS[day.weekday()], day.day, MONTHS[day.month - 1], (' %d' % day.year) if year else '')


def link(path, slot, campaign):
    """A site link that the email report and the site's own analytics can both attribute."""
    base = path if path.startswith('http') else SITE + path.lstrip('/')
    sep = '&' if '?' in base else '?'
    return '%s%sutm_source=newsletter&utm_medium=email&utm_campaign=%s&utm_content=%s' % (base, sep, campaign, slot)


def first_sentences(text, limit=300):
    """The opening of the write-up, cut at a sentence, never mid-word."""
    para = (text or '').split('\n')[0].strip()
    if len(para) <= limit:
        return para
    cut = para[:limit]
    stop = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return (cut[:stop + 1] if stop > 120 else cut.rsplit(' ', 1)[0] + '…').strip()


def whole_sentences(text, limit):
    """As many whole sentences as fit in limit characters; a calendar note never ends mid-thought."""
    out = ''
    for s in text.replace('! ', '!\n').replace('? ', '?\n').replace('. ', '.\n').split('\n'):
        if out and len(out) + 1 + len(s) > limit:
            break
        out = (out + ' ' + s).strip()
    return out if len(out) <= limit else out[:limit].rsplit(' ', 1)[0] + '…'


def email_photo(n):
    """A 3:2 photo sized for email, cut from the recap's own picture. Returns its public URL."""
    src = os.path.join(OUT, n['photo'])
    if not os.path.exists(src):
        return None
    from PIL import Image
    im = Image.open(src).convert('RGB')
    w, h = im.size
    th = round(w * 2 / 3)
    if th < h:
        top = round((h - th) * 0.42)
        im = im.crop((0, top, w, top + th))
    im = im.resize((1200, 800), Image.LANCZOS)
    os.makedirs(os.path.join(OUT, 'img', 'email'), exist_ok=True)
    name = 'img/email/%s.jpg' % n['date']
    im.save(os.path.join(OUT, name), 'JPEG', quality=70, optimize=True, progressive=True)
    return SITE + name


# ------------------------------------------------------------------ pieces

def btn(label, href, primary=True):
    """A full-width rounded button: the easiest thing to hit with a thumb."""
    bg, fg, bd = (SCARLET, VOID, SCARLET) if primary else (TILE, CREAM, RULE)
    return (GRID + '<tr><td align="center" bgcolor="%s" style="background:%s;border:1px solid %s;border-radius:12px">'
            '<a href="%s" style="display:block;padding:14px 18px;font-family:%s;font-size:15px;font-weight:700;line-height:20px;'
            'color:%s;text-decoration:none;border-radius:12px">%s&nbsp;&rarr;</a></td></tr></table>'
            % (bg, bg, bd, esc(href), FM, fg, esc(label)))


def label(text, color=INK3, tag='div'):
    """A small quiet line above a name: what it is, before who."""
    return ('<%s style="margin:0;font-family:%s;font-size:13px;font-weight:600;line-height:18px;color:%s">%s</%s>'
            % (tag, FM, color, esc(text), tag))


def heading(emoji, text):
    return ('<h2 style="margin:0;font-family:%s;font-size:18px;font-weight:800;line-height:24px;letter-spacing:-.2px;color:%s">%s&nbsp; %s</h2>'
            % (FD, CREAM, emoji, esc(text)))


def chips(items):
    """Small rounded tags in a row; the first one in the club's red."""
    return PLAIN + '<tr>' + ''.join(
        '<td style="padding:0 6px 6px 0"><div style="display:inline-block;padding:4px 10px;border-radius:999px;background:%s;'
        'font-family:%s;font-size:12px;font-weight:700;line-height:16px;color:%s;white-space:nowrap">%s</div></td>'
        % (SCARLET if i == 0 else TILE, FM, VOID if i == 0 else INK2, esc(t)) for i, t in enumerate(items)) + '</tr></table>'


def row(inner, pad='0 4px 12px', bg=None):
    """One line of the page, outside any card."""
    return '<tr><td style="padding:%s">%s</td></tr>' % (pad, inner)


def card(inner, pad='20px', border=RULE, top=''):
    """A rounded panel. Everything in the email sits on one of these, 12px apart."""
    return ('<tr><td style="padding:0 0 12px">' + GRID.replace('border="0">', 'border="0" bgcolor="%s" style="background:%s;border:1px solid %s;'
            'border-radius:16px;border-collapse:separate">' % (PANEL, PANEL, border)) +
            top + '<tr><td style="padding:%s">%s</td></tr></table></td></tr>' % (pad, inner))


def text(t, size=16, color=INK2, pad='0'):
    return ('<p style="margin:0;padding:%s;font-family:%s;font-size:%dpx;line-height:%dpx;color:%s">%s</p>'
            % (pad, FS, size, round(size * 1.5), color, esc(t)))


def divided(rows):
    """Rows in a card, a hairline between them and none above the first."""
    return GRID + ''.join('<tr><td style="padding:%s;%s">%s</td></tr>'
                          % ('12px 0' if i else '0 0 12px', 'border-top:1px solid %s' % RULE if i else '', r)
                          for i, r in enumerate(rows)) + '</table>'


def leaders(n, campaign):
    st = n.get('standings') or []
    if not st:
        return ''
    rows = []
    for b in st:
        top = b['rows'][0]['pts']
        names = [r['name'] for r in b['rows'] if (r.get('place') == 1 if r.get('place') else r['pts'] == top)]
        pts = ('%g' % top).replace('.5', '½') if isinstance(top, (int, float)) else str(top)
        rows.append(GRID + '<tr><td>%s<div style="font-family:%s;font-size:17px;font-weight:800;line-height:22px;color:%s;padding-top:2px">%s</div></td>'
                    '<td align="right" valign="middle" style="font-family:%s;font-size:20px;font-weight:800;color:%s;white-space:nowrap;padding-left:12px">%s'
                    '<span style="font-size:12px;font-weight:600;color:%s">&nbsp;/ %s</span></td></tr></table>'
                    % (label(b.get('bracket', '')), FD, CREAM, esc(', '.join(names)), FD, GOLD, esc(pts), INK3, esc(n.get('rounds', ''))))
    ups = n.get('upsets') or []
    upset = ''
    if ups:
        upset = ('<div style="margin-top:4px;padding:12px 14px;border-radius:12px;background:%s;font-family:%s;font-size:14px;line-height:21px;color:%s">'
                 '<b style="color:%s">\u26a1 Upsets</b>&nbsp; %s</div>'
                 % (TILE, FS, INK2, CREAM, esc(' \u00b7 '.join('%s over %s' % (u[0], u[1]) for u in ups))))
    return card(heading('\U0001F3C6', 'Top of the table') + '<div style="padding-top:14px">%s</div>%s<div style="padding-top:14px">%s</div>'
                % (divided(rows), upset, btn('Full standings', link(LADDER, 'standings', campaign), primary=False)))


def wins(mail):
    """The week's honours, one row each: what was won, who won it, and a line about it."""
    rows = mail.get('wins') or []
    if not rows:
        return ''
    cells = [label(r[0], GOLD) +
             '<div style="font-family:%s;font-size:18px;font-weight:800;line-height:24px;color:%s;padding-top:2px">%s</div>%s'
             % (FD, CREAM, esc(r[1]), text(r[2], 15, INK2, '2px 0 0') if len(r) > 2 and r[2] else '')
             for r in rows]
    return card(heading(mail.get('wins_emoji') or '\U0001F3C5', mail.get('wins_label') or 'What we brought home') +
                '<div style="padding-top:14px">%s</div>' % divided(cells))


def week_ahead(send_day, events, campaign, notes='all'):
    rows, special = [], []
    plan = T.study_plan()
    for i in range(1, 8):
        day = send_day + timedelta(days=i)
        for e in T.whats_on(day, events):
            kind = e.get('type', '')
            booked = kind not in NIGHT_NAMES
            title = e.get('title') if booked else NIGHT_NAMES[kind]
            if kind == 'study' and plan.get('number'):
                blurb = 'Carrying on from %s %d of %s.' % (plan.get('unit', 'chapter'), plan['number'], plan['book'])
            elif booked:
                blurb = whole_sentences(' '.join((e.get('note') or '').split()), 130)
            else:
                blurb = NIGHT_BLURB.get(kind, '')
            if notes == 'booked' and not booked:
                blurb = ''
            where = e.get('venue') or ('Adobe Kava' if kind == 'adobe' else 'Kava Social Club')
            when = (e.get('time') or '8:00 PM').replace(':00 ', '').replace(' ', '').lower()
            item = dict(day=day, title=title, blurb=blurb, where=where, when=when, booked=booked, url=e.get('url'), kind=kind)
            (special if booked else rows).append(item)
    out = []
    for it in sorted(special + rows, key=lambda i: i['day']):
        extra = ''
        if it['booked'] and it['url']:
            extra = ('<div style="padding-top:6px"><a href="%s" style="font-family:%s;font-size:14px;font-weight:700;color:%s;text-decoration:underline">%s&nbsp;&rarr;</a></div>'
                     % (esc(it['url']), FM, CREAM, 'Get tickets' if it['kind'] == 'outing' else 'Register'))
        out.append(
            GRID + '<tr><td width="56" valign="top"><table role="presentation" width="56" cellpadding="0" cellspacing="0" border="0"><tr>'
            '<td align="center" bgcolor="%s" style="background:%s;border-radius:12px;padding:8px 0 7px;%s">'
            '<div style="font-family:%s;font-size:11px;font-weight:700;line-height:13px;color:%s">%s</div>'
            '<div style="font-family:%s;font-size:22px;font-weight:800;line-height:26px;color:%s">%d</div></td></tr></table></td>'
            '<td valign="top" style="padding-left:14px">'
            '<div style="font-family:%s;font-size:16px;font-weight:800;line-height:21px;color:%s">%s&nbsp; %s</div>'
            '<div style="font-family:%s;font-size:13px;line-height:19px;color:%s;padding-top:2px">%s &middot; %s</div>%s%s</td></tr></table>'
            % (TILE, TILE, ('border:1px solid %s' % SCARLET) if it['booked'] else 'border:1px solid %s' % TILE,
               FM, SCARLET if it['booked'] else INK3, DAYS[it['day'].weekday()][:3].upper(), FD, CREAM, it['day'].day,
               FD, CREAM, KIND_EMOJI.get(it['kind'], '\U0001F4CC'), esc(it['title']), FM, INK3, esc(it['when'].upper()), esc(it['where']),
               text(it['blurb'], 14, INK2, '4px 0 0') if it['blurb'] else '', extra))
    if not out:
        return '', []
    body = (heading('\U0001F4C5', 'This week at the club') + '<div style="padding-top:14px">%s</div><div style="padding-top:6px">%s</div>'
            % (divided(out), btn('See the calendar', link('calendar/', 'calendar', campaign), primary=False)))
    return card(body), sorted(special + rows, key=lambda i: i['day'])


# ------------------------------------------------------------------ the email

def build(send_day, out_dir):
    nights = sorted(json.load(open(os.path.join(OUT, 'nights.json'), encoding='utf-8')).get('nights', []),
                    key=lambda n: n['date'], reverse=True)
    events = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8')).get('events', [])
    since = send_day - timedelta(days=7)
    fresh = [n for n in nights if since < d8(n['date']) <= send_day]
    if not fresh:
        print('No recap posted since %s. Nothing to send this week.' % since.isoformat())
        return None
    # the newest recap leads, unless one of the week's recaps is marked to hold the top
    lead = next((n for n in fresh if (n.get('email') or {}).get('lead')), fresh[0])
    # a promotion for a night that has since happened ("email": {"skip": true}) is not news any more
    rest = [n for n in fresh if n is not lead and not (n.get('email') or {}).get('skip')]
    mail = lead.get('email') or {}
    campaign = 'weekly-%s' % send_day.isoformat()
    no = B.night_number(B.when(lead))
    kind = B.night_type(lead, False)
    recap_url = link('nights/%s/' % lead['date'], 'recap', campaign)
    photo = email_photo(lead) if lead.get('photo') else None

    subject = mail.get('subject') or lead.get('title') or kind
    if len(subject) > 48:
        subject = subject[:48].rsplit(' ', 1)[0] + '…'
    body_week, coming = week_ahead(send_day, events, campaign, mail.get('notes', 'all'))
    preheader = (mail.get('preheader') or lead.get('line') or first_sentences(lead.get('commentary'), 90)).rstrip()
    booked = [c for c in coming if c['booked']]
    if booked and len(preheader) < 80 and not mail.get('preheader'):
        preheader += ' Plus: %s, %s.' % (booked[0]['title'].split(':')[0], nice(booked[0]['day']).split(' ', 1)[0])

    P = []
    P.append(row(
        GRID + '<tr><td width="74" valign="middle"><a href="%s"><img src="%simg/email/logo-badge.png" width="64" height="64" alt="Kava Social Chess Club" '
        'style="display:block;border:0;border-radius:10px"></a></td>'
        '<td valign="middle" style="font-family:%s;font-size:16px;font-weight:800;line-height:20px;color:%s">Kava Social Chess Club</td>'
        '<td align="right" valign="middle" style="font-family:%s;font-size:13px;font-weight:600;color:%s;white-space:nowrap">%s %d</td></tr></table>'
        % (link('', 'masthead', campaign), SITE, FD, CREAM, FM, INK3, MONTHS[send_day.month - 1][:3], send_day.day),
        '6px 4px 14px'))

    hero = ''
    if photo:
        hero = ('<tr><td style="padding:0"><a href="%s"><img src="%s" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;'
                'height:auto;border:0;border-radius:15px 15px 0 0"></a></td></tr>' % (esc(recap_url), esc(photo), esc(lead.get('photo_alt') or subject)))
    opening = mail['intro'] if 'intro' in mail else first_sentences(lead.get('commentary'))
    facts = [('\U0001F465', lead.get('played'), 'players'), ('\U0001F501', lead.get('rounds'), 'rounds'),
             ('\U0001F3C6', len(lead.get('standings') or []) or None, 'brackets')]
    facts = [f for f in facts if f[1]]
    stats = ''
    if facts:
        cells = []
        for i, (em, v, k) in enumerate(facts):
            if i:
                cells.append('<td width="8" style="font-size:0;line-height:0">&nbsp;</td>')
            cells.append('<td align="center" bgcolor="%s" style="background:%s;border-radius:12px;padding:10px 4px">'
                         '<div style="font-family:%s;font-size:20px;font-weight:800;line-height:24px;color:%s">%s</div>'
                         '<div style="font-family:%s;font-size:12px;font-weight:600;line-height:16px;color:%s">%s %s</div></td>'
                         % (TILE, TILE, FD, CREAM, esc(v), FM, INK3, em, k))
        stats = '<div style="padding-top:16px">' + GRID + '<tr>' + ''.join(cells) + '</tr></table></div>'
    P.append(card(
        chips([B.night_tag(lead, False), kind, '%s %d %s' % (DAYS[d8(B.when(lead)).weekday()][:3], d8(B.when(lead)).day, MONTHS[d8(B.when(lead)).month - 1][:3])]) +
        '<h1 style="margin:0;padding-top:6px;font-family:%s;font-size:28px;font-weight:800;line-height:33px;letter-spacing:-.6px;color:%s">'
        '<a href="%s" style="color:%s;text-decoration:none">%s</a></h1>' % (FD, CREAM, esc(recap_url), CREAM, esc(mail.get('title') or lead.get('title') or kind)) +
        (text(lead['line'], 17, CREAM, '10px 0 0') if lead.get('line') else '') +
        (text(opening, 16, INK2, '10px 0 0') if opening else '') +
        stats + '<div style="padding-top:16px">%s</div>' % btn(mail.get('button') or 'Read the full recap', recap_url),
        top=hero))
    P.append(wins(mail))
    said = list(mail.get('body') or [])
    if said:
        P.append(card(''.join(text(t, 16, INK2, '0' if i == 0 else '10px 0 0') for i, t in enumerate(said))))
    P.append(leaders(lead, campaign))
    # the club in the paper: one linked headline per piece, nothing more
    if mail.get('press'):
        P.append(card(heading('\U0001F4F0', 'In the press') + '<div style="padding-top:14px">%s</div>' % divided([
            label(x['source']) +
            '<div style="padding-top:2px"><a href="%s" style="font-family:%s;font-size:16px;font-weight:800;line-height:21px;color:%s;text-decoration:none">%s&nbsp;&rarr;</a></div>%s'
            % (esc(x['url']), FD, CREAM, esc(x['title']), text(x.get('note', ''), 14, INK2, '4px 0 0')) for x in mail['press']])))

    if rest:
        P.append(card(heading('\U0001F4D6', 'Also last week') + '<div style="padding-top:14px">%s</div>' % divided([
            label('%s \u00b7 %s' % (DAYS[d8(B.when(n)).weekday()], B.night_type(n, False))) +
            '<div style="padding-top:2px"><a href="%s" style="font-family:%s;font-size:16px;font-weight:800;line-height:21px;color:%s;text-decoration:none">%s&nbsp;&rarr;</a></div>%s'
            % (esc(link('nights/%s/' % n['date'], 'also-%s' % n['date'], campaign)), FD, CREAM, esc(n.get('title') or B.night_type(n, False)),
               text(n.get('line') or first_sentences(n.get('commentary'), 110), 14, INK2, '4px 0 0'))
            for n in rest[:mail.get('also', 3)]])))
    if body_week:
        P.append(body_week)

    # for anyone who has drifted: the one card with a red edge
    back = dict(COMEBACK, **(mail.get('comeback') or {}))
    P.append(card(
        label(back['label'], SCARLET) +
        '<h2 style="margin:0;padding-top:2px;font-family:%s;font-size:22px;font-weight:800;line-height:28px;letter-spacing:-.3px;color:%s">\U0001F44B&nbsp; %s</h2>'
        % (FD, CREAM, esc(back['title'])) + text(back['text'], 16, INK2, '8px 0 0') +
        '<div style="padding-top:16px">%s</div>' % btn(back['button'], link('beginners/', 'comeback', campaign)),
        border=SCARLET))

    P.append(row(
        PLAIN + '<tr>%s</tr></table>' % ''.join(
            '<td style="padding-right:14px"><a href="%s" style="text-decoration:none"><img src="%simg/email/%s.png" width="32" '
            'height="32" alt="%s" style="display:block;border:0;font-family:%s;font-size:11px;color:%s"></a></td>'
            % (href, SITE, ICON.get(name, name.lower()), name, FM, CREAM) for name, href in SOCIAL),
        '10px 4px 14px'))
    P.append(row(
        '<div style="font-family:%s;font-size:12px;line-height:19px;color:%s">'
        '\U0001F4CD <a href="%s" style="color:%s;text-decoration:underline">kavasocialchessclub.com</a> &nbsp;&middot;&nbsp; '
        '<a href="%s" style="color:%s;text-decoration:underline">Directions</a><br><br>'
        'You\u2019re a member of Kava Social Chess Club. One email a week.<br>'
        '%s<br><br>'
        '<a href="{{ unsubscribe }}" style="color:%s;text-decoration:underline">Unsubscribe</a> &nbsp;&middot;&nbsp; '
        '<a href="{{ mirror }}" style="color:%s;text-decoration:underline">View in your browser</a></div>'
        % (FM, INK3, link('', 'footer', campaign), INK2, MAPS, INK2, esc(ADDRESS), INK2, INK2),
        '0 4px 28px'))

    doc = (
        '<!doctype html>\n<html lang="en" xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="x-apple-disable-message-reformatting">\n<meta name="format-detection" content="telephone=no,date=no,address=no,email=no">\n'
        '<meta name="color-scheme" content="dark">\n<meta name="supported-color-schemes" content="dark">\n'
        '<title>%s</title>\n'
        '<style>:root{color-scheme:dark}body{margin:0;padding:0;background:%s}a{color:%s}img{-ms-interpolation-mode:bicubic}'
        'a[x-apple-data-detectors]{color:inherit !important;text-decoration:none !important;font:inherit !important}'
        'u+#body a{color:inherit}</style>\n</head>\n'
        '<body id="body" style="margin:0;padding:0;background:%s">\n'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:%s;font-size:1px;line-height:1px">%s%s</div>\n'
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="%s" style="background:%s">'
        '<tr><td align="center" style="padding:10px 10px 0">\n'
        '<table role="presentation" class="px" width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%%;max-width:600px">\n%s\n</table>\n</td></tr></table>\n</body>\n</html>\n'
        % (esc(subject), VOID, CREAM, VOID, VOID, esc(preheader), '&nbsp;&zwnj;' * 40, VOID, VOID, '\n'.join(p for p in P if p)))

    size = len(doc.encode('utf-8'))
    assert size < MAX_BYTES, 'email is %d bytes; Gmail clips at 102KB' % size

    txt = [subject.upper(), '', '%s · %s · %s' % (B.night_tag(lead, False), kind, nice(d8(B.when(lead)), True)), '']
    if lead.get('line'):
        txt += ['"%s"' % lead['line'], '']
    txt += [opening, ''] if opening else []
    if mail.get('wins'):
        txt += [(mail.get('wins_label') or 'What we brought home').upper()] + [
            ('- %s: %s. %s' % (r[1], r[0], r[2] if len(r) > 2 else '')).rstrip() for r in mail['wins']] + ['']
    for t in said:
        txt += [t, '']
    txt += ['%s: %s' % (mail.get('button') or 'Read the full recap', recap_url), '']
    if mail.get('press'):
        txt += ['IN THE PRESS'] + ['- %s, %s: %s' % (x['source'], x['title'], x['url']) for x in mail['press']] + ['']
    if rest:
        txt += ['ALSO LAST WEEK'] + ['- %s: %s' % (n.get('title'), link('nights/%s/' % n['date'], 'also-%s' % n['date'], campaign)) for n in rest[:mail.get('also', 3)]] + ['']
    if coming:
        txt += ['THIS WEEK AT THE CLUB'] + ['- %s: %s, %s, %s' % (nice(c['day']), c['title'], c['when'], c['where']) for c in coming] + ['']
    txt += [back['title'].upper(), back['text'],
            link('beginners/', 'comeback', campaign), '', ADDRESS, 'Unsubscribe: {{ unsubscribe }}']

    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'email.html'), 'w', encoding='utf-8').write(doc)
    open(os.path.join(out_dir, 'email.txt'), 'w', encoding='utf-8').write('\n'.join(txt) + '\n')
    meta = {'subject': subject, 'preheader': preheader, 'campaign': campaign, 'from_name': 'Kava Social Chess Club',
            'send_at': '%sT15:00:00 America/New_York' % send_day.isoformat(), 'bytes': size, 'lead': lead['date'],
            'photo': photo}
    json.dump(meta, open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('subject   (%d chars) %s' % (len(subject), subject))
    print('preheader (%d chars) %s' % (len(preheader), preheader))
    print('size      %.1f KB of the 102 KB Gmail allows' % (size / 1024))
    return meta


if __name__ == '__main__':
    args = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    day = d8(args['date']) if 'date' in args else datetime.now(T.EASTERN).date()
    build(day, args.get('out', os.path.join(OUT, 'build', 'out-email')))
