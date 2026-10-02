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
ADDRESS = 'Kava Social Chess Club · Kava Social Club, 540 13th St W, Bradenton, FL 34205'
MAX_BYTES = 80 * 1024

VOID, PANEL, CREAM, INK2, INK3, SCARLET, RULE, GOLD = (
    '#0C0D0E', '#151618', '#FFF6E8', '#C9C1B5', '#8E877D', '#FE273A', '#2A2C2F', '#E4B02F')
# Gmail ignores web fonts, so each stack has to look right on its second name
FD = "Archivo,'Arial Black','Helvetica Neue',Arial,sans-serif"
FS = "Newsreader,Georgia,'Times New Roman',serif"
FM = "'JetBrains Mono','Courier New',Courier,monospace"

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
    bg, fg, bd = (SCARLET, VOID, SCARLET) if primary else (VOID, CREAM, '#5A5F66')
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            '<td bgcolor="%s" style="background:%s;border:1px solid %s;border-radius:999px">'
            '<a href="%s" style="display:inline-block;padding:16px 30px;font-family:%s;font-size:13px;'
            'font-weight:700;letter-spacing:2px;line-height:16px;text-transform:uppercase;color:%s;'
            'text-decoration:none;border-radius:999px">%s&nbsp;&rarr;</a></td></tr></table>'
            % (bg, bg, bd, esc(href), FM, fg, esc(label)))


def label(text, color=SCARLET, tag='div'):
    return ('<%s style="margin:0;font-family:%s;font-size:12px;font-weight:700;letter-spacing:3px;line-height:18px;'
            'text-transform:uppercase;color:%s">%s</%s>' % (tag, FM, color, esc(text), tag))


def row(inner, pad='0 28px', bg=VOID):
    return '<tr><td bgcolor="%s" style="background:%s;padding:%s">%s</td></tr>' % (bg, bg, pad, inner)


def rule():
    return row('<div style="border-top:1px solid %s;font-size:0;line-height:0">&nbsp;</div>' % RULE, '0 28px')


def leaders(n, campaign):
    st = n.get('standings') or []
    if not st:
        return ''
    cells = []
    for b in st:
        top = b['rows'][0]['pts']
        names = [r['name'] for r in b['rows'] if r['pts'] == top]
        pts = ('%g' % top).replace('.5', '½') if isinstance(top, (int, float)) else str(top)
        cells.append(
            '<tr><td style="padding:12px 0;border-top:1px solid %s">%s'
            '<div style="font-family:%s;font-size:19px;font-weight:900;line-height:24px;color:%s;padding-top:4px">%s</div></td>'
            '<td align="right" valign="bottom" style="padding:12px 0;border-top:1px solid %s;font-family:%s;font-size:22px;'
            'font-weight:900;color:%s;white-space:nowrap">%s<span style="font-family:%s;font-size:11px;font-weight:400;'
            'letter-spacing:1px;color:%s">&nbsp;/ %s</span></td></tr>'
            % (RULE, label(b.get('bracket', ''), INK3), FD, CREAM, esc(', '.join(names)), RULE, FD, GOLD, esc(pts), FM, INK3,
               esc(n.get('rounds', ''))))
    ups = n.get('upsets') or []
    upset = ''
    if ups:
        upset = ('<tr><td colspan="2" style="padding:14px 0 0;font-family:%s;font-size:16px;line-height:24px;color:%s">'
                 '<span style="color:%s;font-family:%s;font-size:12px;font-weight:700;letter-spacing:3px">UPSETS&nbsp;&nbsp;</span>%s</td></tr>'
                 % (FS, INK2, SCARLET, FM, esc(' · '.join('%s over %s' % (u[0], u[1]) for u in ups))))
    return row(
        label('Top of the table', tag='h2') +
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px">%s%s</table>'
        '<div style="padding-top:18px">%s</div>'
        % (''.join(cells), upset, btn('Full standings', link(LADDER, 'standings', campaign), primary=False)),
        '30px 28px 34px', PANEL)


def week_ahead(send_day, events, campaign):
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
                blurb = ' '.join((e.get('note') or '').split())
                blurb = blurb if len(blurb) <= 150 else blurb[:150].rsplit(' ', 1)[0] + '…'
            else:
                blurb = NIGHT_BLURB.get(kind, '')
            where = e.get('venue') or ('Adobe Kava' if kind == 'adobe' else 'Kava Social Club')
            when = (e.get('time') or '8:00 PM').replace(':00 ', '').replace(' ', '').lower()
            item = dict(day=day, title=title, blurb=blurb, where=where, when=when, booked=booked, url=e.get('url'))
            (special if booked else rows).append(item)
    out = []
    for it in sorted(special + rows, key=lambda i: i['day']):
        edge = SCARLET if it['booked'] else RULE
        extra = ''
        if it['booked'] and it['url']:
            extra = ('<div style="padding-top:8px"><a href="%s" style="font-family:%s;font-size:12px;font-weight:700;'
                     'letter-spacing:2px;text-transform:uppercase;color:%s;text-decoration:underline">Register&nbsp;&rarr;</a></div>'
                     % (esc(it['url']), FM, CREAM))
        out.append(
            '<tr><td width="76" valign="top" style="padding:16px 0;border-top:1px solid %s">'
            '<div style="font-family:%s;font-size:11px;font-weight:700;letter-spacing:2px;color:%s">%s</div>'
            '<div style="font-family:%s;font-size:34px;font-weight:900;line-height:36px;color:%s">%d</div></td>'
            '<td valign="top" style="padding:16px 0;border-top:1px solid %s">'
            '<div style="font-family:%s;font-size:19px;font-weight:900;line-height:24px;text-transform:uppercase;color:%s">%s</div>'
            '<div style="font-family:%s;font-size:12px;letter-spacing:1px;line-height:20px;color:%s;padding-top:2px">%s &middot; %s</div>'
            '<div style="font-family:%s;font-size:16px;line-height:24px;color:%s;padding-top:6px">%s</div>%s</td></tr>'
            % (edge, FM, SCARLET if it['booked'] else INK3, DAYS[it['day'].weekday()][:3].upper(), FD, CREAM, it['day'].day,
               edge, FD, CREAM, esc(it['title']), FM, INK3, esc(it['when'].upper()), esc(it['where']), FS, INK2,
               esc(it['blurb']), extra))
    if not out:
        return '', []
    body = (label('This week at the club', tag='h2') +
            '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px">%s</table>'
            '<div style="padding-top:22px">%s</div>'
            % (''.join(out), btn('See the calendar', link('calendar/', 'calendar', campaign), primary=False)))
    return row(body, '34px 28px 36px'), sorted(special + rows, key=lambda i: i['day'])


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
    lead, rest = fresh[0], fresh[1:]
    campaign = 'weekly-%s' % send_day.isoformat()
    no = B.night_number(B.when(lead))
    kind = B.night_type(lead, False)
    recap_url = link('nights/%s/' % lead['date'], 'recap', campaign)
    photo = email_photo(lead) if lead.get('photo') else None

    subject = lead.get('title') or kind
    if len(subject) > 48:
        subject = subject[:48].rsplit(' ', 1)[0] + '…'
    body_week, coming = week_ahead(send_day, events, campaign)
    preheader = (lead.get('line') or first_sentences(lead.get('commentary'), 90)).rstrip()
    booked = [c for c in coming if c['booked']]
    if booked and len(preheader) < 80:
        preheader += ' Plus: %s, %s.' % (booked[0]['title'].split(':')[0], nice(booked[0]['day']).split(' ', 1)[0])

    P = []
    P.append(row(
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td width="52" valign="middle"><a href="%s"><img src="%simg/email/logo.png" width="44" height="44" alt="Kava Social Chess Club" '
        'style="display:block;border:0"></a></td>'
        '<td valign="middle" style="font-family:%s;font-size:17px;font-weight:900;line-height:20px;letter-spacing:.3px;'
        'text-transform:uppercase;color:%s">Kava Social<br>Chess Club</td>'
        '<td align="right" valign="middle" style="font-family:%s;font-size:11px;letter-spacing:2px;line-height:16px;'
        'text-transform:uppercase;color:%s">The week<br>%d %s</td></tr></table>'
        % (link('', 'masthead', campaign), SITE, FD, CREAM, FM, INK3, send_day.day, MONTHS[send_day.month - 1][:3]),
        '22px 28px 22px'))
    if photo:
        P.append(row('<a href="%s"><img src="%s" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;'
                     'height:auto;border:0"></a>' % (esc(recap_url), esc(photo), esc(lead.get('photo_alt') or subject)), '0'))
    P.append(row(label('%s · %s · %s' % (B.night_tag(lead, False), kind, nice(d8(B.when(lead))))), '30px 28px 0'))
    P.append(row('<h1 style="margin:0;font-family:%s;font-size:34px;font-weight:900;line-height:36px;letter-spacing:-.4px;'
                 'text-transform:uppercase;color:%s"><a href="%s" style="color:%s;text-decoration:none">%s</a></h1>'
                 % (FD, CREAM, esc(recap_url), CREAM, esc(lead.get('title') or kind)), '12px 28px 0'))
    if lead.get('line'):
        P.append(row('<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0"><tr>'
                     '<td width="3" bgcolor="%s" style="background:%s;font-size:0;line-height:0">&nbsp;</td>'
                     '<td style="padding:2px 0 2px 18px;font-family:%s;font-size:21px;font-style:italic;line-height:29px;color:%s">'
                     '&ldquo;%s&rdquo;<div style="font-family:%s;font-size:11px;font-style:normal;font-weight:700;letter-spacing:2px;'
                     'text-transform:uppercase;color:%s;padding-top:8px">Harold Gonzalez &middot; Club director</div></td></tr></table>'
                     % (SCARLET, SCARLET, FS, CREAM, esc(lead['line']), FM, INK3), '24px 28px 0'))
    P.append(row('<p style="margin:0;font-family:%s;font-size:17px;line-height:27px;color:%s">%s</p>'
                 % (FS, INK2, esc(first_sentences(lead.get('commentary')))), '22px 28px 0'))
    facts = [(lead.get('played'), 'players'), (lead.get('rounds'), 'rounds'), (len(lead.get('standings') or []) or None, 'brackets')]
    facts = [f for f in facts if f[0]]
    if facts:
        P.append(row('<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>%s</tr></table>' % ''.join(
            '<td style="padding-right:30px"><div style="font-family:%s;font-size:30px;font-weight:900;line-height:32px;color:%s">%s</div>'
            '<div style="font-family:%s;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:%s">%s</div></td>'
            % (FD, CREAM, esc(v), FM, INK3, k) for v, k in facts), '24px 28px 0'))
    P.append(row(btn('Read the full recap', recap_url), '28px 28px 36px'))
    P.append(leaders(lead, campaign))

    if rest:
        items = ''.join(
            '<tr><td style="padding:14px 0;border-top:1px solid %s">%s'
            '<div style="padding-top:4px"><a href="%s" style="font-family:%s;font-size:18px;font-weight:900;line-height:23px;'
            'text-transform:uppercase;color:%s;text-decoration:none">%s&nbsp;&rarr;</a></div>'
            '<div style="font-family:%s;font-size:16px;line-height:24px;color:%s;padding-top:4px">%s</div></td></tr>'
            % (RULE, label('%s · %s' % (DAYS[d8(B.when(n)).weekday()], B.night_type(n, False)), INK3),
               esc(link('nights/%s/' % n['date'], 'also-%s' % n['date'], campaign)), FD, CREAM,
               esc(n.get('title') or B.night_type(n, False)), FS, INK2, esc(n.get('line') or first_sentences(n.get('commentary'), 110)))
            for n in rest[:3])
        P.append(row(label('Also last week', tag='h2') + '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" '
                     'style="margin-top:12px">%s</table>' % items, '34px 28px 8px'))
    if body_week:
        P.append(rule())
        P.append(body_week)

    # for anyone who has drifted: inverted, so it is the one block that looks different
    P.append(row(
        '%s<h2 style="margin:0;font-family:%s;font-size:28px;font-weight:900;line-height:30px;letter-spacing:-.3px;text-transform:uppercase;'
        'color:%s;padding-top:10px">Been a while?</h2>'
        '<p style="margin:0;padding-top:12px;font-family:%s;font-size:17px;line-height:27px;color:#3A3631">'
        'Nothing has changed. No dues, nothing to bring, and nobody keeps track of how long you were gone. '
        'Sundays and Tuesdays at eight, same back patio. Pull up a chair.</p>'
        '<div style="padding-top:22px">%s</div>'
        % (label('Haven’t played lately'), FD, VOID, FS,
           btn('Come back this week', link('beginners/', 'comeback', campaign))),
        '34px 28px 38px', CREAM))

    P.append(row(
        label('Find the club', INK3) +
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px"><tr>%s</tr></table>' % ''.join(
            '<td style="padding-right:22px"><a href="%s" style="text-decoration:none"><img src="%simg/email/%s.png" width="36" '
            'height="36" alt="%s" style="display:block;border:0;font-family:%s;font-size:11px;color:%s"></a></td>'
            % (href, SITE, name.lower(), name, FM, CREAM) for name, href in SOCIAL),
        '34px 28px 0'))
    P.append(row(
        '<div style="font-family:%s;font-size:12px;line-height:20px;letter-spacing:.5px;color:%s">'
        '<a href="%s" style="color:%s;text-decoration:underline">kavasocialchessclub.com</a> &nbsp;&middot;&nbsp; '
        '<a href="%s" style="color:%s;text-decoration:underline">Directions</a><br><br>'
        'You are getting this because you are a member of Kava Social Chess Club. One email a week, on Mondays.<br>'
        '%s<br><br>'
        '<a href="{{ unsubscribe }}" style="color:%s;text-decoration:underline">Unsubscribe</a> &nbsp;&middot;&nbsp; '
        '<a href="{{ mirror }}" style="color:%s;text-decoration:underline">View in your browser</a></div>'
        % (FM, INK3, link('', 'footer', campaign), INK2, MAPS, INK2, esc(ADDRESS), INK2, INK2),
        '30px 28px 40px'))

    doc = (
        '<!doctype html>\n<html lang="en" xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="x-apple-disable-message-reformatting">\n<meta name="format-detection" content="telephone=no,date=no,address=no,email=no">\n'
        '<meta name="color-scheme" content="dark">\n<meta name="supported-color-schemes" content="dark">\n'
        '<title>%s</title>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@900&family=Newsreader:ital,wght@0,400;1,400&'
        'family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">\n'
        '<style>:root{color-scheme:dark}body{margin:0;padding:0;background:%s}a{color:%s}img{-ms-interpolation-mode:bicubic}'
        'a[x-apple-data-detectors]{color:inherit !important;text-decoration:none !important;font:inherit !important}'
        'u+#body a{color:inherit}'
        '@media (max-width:480px){.px h1{font-size:30px !important;line-height:32px !important}}</style>\n</head>\n'
        '<body id="body" style="margin:0;padding:0;background:%s">\n'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:%s;font-size:1px;line-height:1px">%s%s</div>\n'
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="%s" style="background:%s">'
        '<tr><td align="center" style="padding:0">\n'
        '<table role="presentation" class="px" width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%%;max-width:600px;background:%s">\n%s\n</table>\n</td></tr></table>\n</body>\n</html>\n'
        % (esc(subject), VOID, CREAM, VOID, VOID, esc(preheader), '&nbsp;&zwnj;' * 40, VOID, VOID, VOID, '\n'.join(p for p in P if p)))

    size = len(doc.encode('utf-8'))
    assert size < MAX_BYTES, 'email is %d bytes; Gmail clips at 102KB' % size

    txt = [subject.upper(), '', '%s · %s · %s' % (B.night_tag(lead, False), kind, nice(d8(B.when(lead)), True)), '']
    if lead.get('line'):
        txt += ['"%s"' % lead['line'], '']
    txt += [first_sentences(lead.get('commentary')), '', 'Read the full recap: ' + recap_url, '']
    if rest:
        txt += ['ALSO LAST WEEK'] + ['- %s: %s' % (n.get('title'), link('nights/%s/' % n['date'], 'also-%s' % n['date'], campaign)) for n in rest[:3]] + ['']
    if coming:
        txt += ['THIS WEEK AT THE CLUB'] + ['- %s: %s, %s, %s' % (nice(c['day']), c['title'], c['when'], c['where']) for c in coming] + ['']
    txt += ['BEEN A WHILE?', 'Nothing has changed. No dues, nothing to bring. Sundays and Tuesdays at eight.',
            link('beginners/', 'comeback', campaign), '', ADDRESS, 'Unsubscribe: {{ unsubscribe }}']

    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'email.html'), 'w', encoding='utf-8').write(doc)
    open(os.path.join(out_dir, 'email.txt'), 'w', encoding='utf-8').write('\n'.join(txt) + '\n')
    meta = {'subject': subject, 'preheader': preheader, 'campaign': campaign, 'from_name': 'Kava Social Chess Club',
            'send_at': '%sT18:00:00 America/New_York' % send_day.isoformat(), 'bytes': size, 'lead': lead['date'],
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
