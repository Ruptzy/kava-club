# -*- coding: utf-8 -*-
"""A one-off member email for a special event's photo gallery, sent the moment it is asked for.

    python build/special_email.py --id=battle-for-the-bay-2 --dry      build it, contact nobody
    python build/special_email.py --id=battle-for-the-bay-2 --test     send it to the Brevo account owner only
    python build/special_email.py --id=battle-for-the-bay-2 --send     send it to the member list now

Run by .github/workflows/special-email.yml. The gallery comes from galleries.json and the
design is the weekly email's own (build_email.py), so the two look like one club.

special-sent.json records every gallery already sent, so a second --send for the same
gallery refuses instead of emailing everyone twice. The weekly email's ledger is not touched.
"""
import json
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_email as E           # noqa: E402
import send_email as S            # noqa: E402
import post_tonight as T          # noqa: E402

OUT = E.OUT
LEDGER = os.path.join(OUT, 'special-sent.json')
esc = E.esc


def email_grid_photos(g):
    """The email's photos: email "wide" (shown at its own shape) and four "tiles" that are 3:2
    already, so the grid is even with no bars and no cropping. Saved beside the weekly photos."""
    from PIL import Image
    mail = g.get('email') or {}
    by = {p['img']: p for p in g['photos']}
    os.makedirs(os.path.join(OUT, 'img', 'email'), exist_ok=True)
    def save(path, n, width):
        im = Image.open(os.path.join(OUT, path)).convert('RGB')
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        name = 'img/email/%s-%d.jpg' % (g['id'], n)
        im.save(os.path.join(OUT, name), 'JPEG', quality=72, optimize=True, progressive=True)
        return E.SITE + name, by[path]['alt'], im.size
    wide = save(mail['wide'], 1, 1120) if mail.get('wide') else None
    tiles = [save(t, k + 2, 600) for k, t in enumerate(mail.get('tiles') or [])]
    return wide, tiles


def build(gid, out_dir):
    doc = json.load(open(os.path.join(OUT, 'galleries.json'), encoding='utf-8'))
    g = [x for x in doc['galleries'] if x['id'] == gid][0]
    mail = g.get('email') or {}
    today = datetime.now(T.EASTERN).date()
    campaign = 'special-%s' % gid
    page = E.link('photos/#%s' % gid, 'gallery', campaign)
    day = E.d8(g['date'])
    n = len(g['photos'])
    subject = mail.get('subject') or '%s: the photos are in' % g['title']
    preheader = mail.get('preheader') or '%d photos by %s.' % (n, g['credit'])

    if mail.get('hero'):
        hero_url = E.SITE + mail['hero']          # the website's cover, title and credit included, as one picture
    else:
        from PIL import Image
        cover = Image.open(os.path.join(OUT, g['cover'])).convert('RGB')
        w, h = cover.size
        th = round(w * 2 / 3)
        if th < h:
            cover = cover.crop((0, round((h - th) / 2), w, round((h - th) / 2) + th))
        cover = cover.resize((1200, 800), Image.LANCZOS)
        cname = 'img/email/%s-cover.jpg' % gid
        os.makedirs(os.path.join(OUT, 'img', 'email'), exist_ok=True)
        cover.save(os.path.join(OUT, cname), 'JPEG', quality=70, optimize=True, progressive=True)
        hero_url = E.SITE + cname
    shots = email_grid_photos(g)

    P = []
    P.append(E.row(
        E.GRID + '<tr><td width="74" valign="middle"><a href="%s"><img src="%simg/email/logo-email.png" width="64" height="64" alt="Kava Social Chess Club" '
        'style="display:block;width:64px;height:64px;border:0;border-radius:50%%"></a></td>'
        '<td valign="middle" style="font-family:%s;font-size:16px;font-weight:800;line-height:20px;color:%s">Kava Social Chess Club</td>'
        '<td align="right" valign="middle" style="font-family:%s;font-size:13px;font-weight:600;color:%s;white-space:nowrap">Special edition</td></tr></table>'
        % (E.link('', 'masthead', campaign), E.SITE, E.FD, E.CREAM, E.FM, E.SCARLET), '6px 4px 14px'))

    hero = ('<tr><td style="padding:0"><a href="%s"><img src="%s" width="600" alt="%s" style="display:block;width:100%%;max-width:600px;'
            'height:auto;border:0;border-radius:15px 15px 0 0"></a></td></tr>' % (esc(page), esc(hero_url), esc(g['cover_alt'])))
    credit = ('<p style="margin:0;padding:12px 0 0;font-family:%s;font-size:14px;font-weight:700;line-height:20px;color:%s">'
              '\U0001F4F8&nbsp; Photos by <a href="%s" style="color:%s;text-decoration:underline">%s</a></p>'
              % (E.FM, E.INK2, esc(g['credit_url']), E.CREAM, esc(g['credit'])))
    P.append(E.card(
        E.chips(['Special event', 'Photo gallery', '%s %d %s' % (E.DAYS[day.weekday()][:3], day.day, E.MONTHS[day.month - 1][:3])]) +
        '<h1 style="margin:0;padding-top:6px;font-family:%s;font-size:28px;font-weight:800;line-height:33px;letter-spacing:-.6px;color:%s">'
        '<a href="%s" style="color:%s;text-decoration:none">%s</a></h1>' % (E.FD, E.CREAM, esc(page), E.CREAM, esc(mail.get('title') or subject)) +
        E.text(mail.get('intro') or g['dek'], 16, E.INK2, '10px 0 0') + credit +
        '<div style="padding-top:16px">%s</div>' % E.btn(mail.get('button') or 'See all %d photos' % n, page),
        top=hero))

    wide, tiles = shots
    if wide or tiles:
        img = lambda src, alt, w: ('<a href="%s"><img src="%s" width="%d" alt="%s" style="display:block;width:100%%;height:auto;border:0;'
                                   'border-radius:10px"></a>' % (esc(page), esc(src), w, esc(alt)))
        rows = []
        if wide:
            rows.append('<tr><td colspan="3" style="padding:0 0 8px">%s</td></tr>' % img(wide[0], wide[1], 560))
        for k in range(0, len(tiles), 2):
            a, b = tiles[k], tiles[k + 1] if k + 1 < len(tiles) else None
            rows.append('<tr><td width="276" valign="top" style="width:49%%;padding:0 0 8px">%s</td>'
                        '<td width="8" style="width:2%%;font-size:0;line-height:0">&nbsp;</td>'
                        '<td width="276" valign="top" style="width:49%%;padding:0 0 8px">%s</td></tr>'
                        % (img(a[0], a[1], 276), img(b[0], b[1], 276) if b else ''))
        P.append(E.card(E.heading('🖼️', mail.get('grid_title') or 'A few from the night') +
                        '<div style="padding-top:14px">' + E.GRID + ''.join(rows) + '</table></div>' +
                        '<div style="padding-top:6px">%s</div>' % E.btn('Open the gallery', page, primary=False)))

    for para in mail.get('body') or []:
        P.append(E.card(E.text(para, 16, E.INK2)))

    events = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8')).get('events', [])
    week, coming = E.week_ahead(today - timedelta(days=1), events, campaign, 'all')
    if week:
        P.append(week)

    pill = lambda words, href: ('<td style="padding:0 4px"><a href="%s" style="display:inline-block;padding:7px 14px;border:1px solid %s;border-radius:999px;'
                                'font-family:%s;font-size:12px;font-weight:600;line-height:16px;color:%s;text-decoration:none;white-space:nowrap">%s</a></td>'
                                % (href, E.RULE, E.FM, E.INK2, words))
    P.append(E.row(
        '<div style="text-align:center;font-family:%s;font-size:12px;line-height:18px;color:%s">'
        'You’re a member of Kava Social Chess Club. A special edition, outside the weekly email.<br>%s</div>'
        '<table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:12px auto 0"><tr>%s%s</tr></table>'
        % (E.FM, E.INK3, esc(E.ADDRESS), pill('Unsubscribe', '{{ unsubscribe }}'), pill('View in browser', '{{ mirror }}')),
        '6px 4px 28px'))

    V = E.VOID
    html = (
        '<!doctype html>\n<html lang="en" xmlns="http://www.w3.org/1999/xhtml">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="x-apple-disable-message-reformatting">\n'
        '<meta name="format-detection" content="telephone=no,date=no,address=no,email=no">\n'
        '<meta name="color-scheme" content="dark">\n<meta name="supported-color-schemes" content="dark">\n<title>%s</title>\n'
        '<style>:root{color-scheme:dark}body{margin:0;padding:0;background:%s}a{color:%s}img{-ms-interpolation-mode:bicubic}'
        'a[x-apple-data-detectors]{color:inherit !important;text-decoration:none !important;font:inherit !important}u+#body a{color:inherit}</style>\n</head>\n'
        '<body id="body" style="margin:0;padding:0;background:%s">\n'
        '<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:%s;font-size:1px;line-height:1px">%s%s</div>\n'
        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" border="0" bgcolor="%s" style="background:%s">'
        '<tr><td align="center" style="padding:10px 10px 0">\n'
        '<table role="presentation" class="px" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%%;max-width:600px">\n%s\n'
        '</table>\n</td></tr></table>\n</body>\n</html>\n'
        % (esc(subject), V, E.CREAM, V, V, esc(preheader), '&nbsp;&zwnj;' * 40, V, V, '\n'.join(p for p in P if p)))
    size = len(html.encode('utf-8'))
    assert size < E.MAX_BYTES, 'email is %d bytes' % size
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'email.html'), 'w', encoding='utf-8').write(html)
    meta = {'subject': subject, 'preheader': preheader, 'campaign': campaign, 'from_name': 'Kava Social Chess Club',
            'bytes': size, 'photos': [hero_url] + ([shots[0][0]] if shots[0] else []) + [t[0] for t in shots[1]]}
    json.dump(meta, open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('subject   (%d chars) %s' % (len(subject), subject))
    print('preheader (%d chars) %s' % (len(preheader), preheader))
    print('size      %.1f KB' % (size / 1024))
    return meta, html


def main(argv):
    args = dict(a[2:].split('=', 1) for a in argv if a.startswith('--') and '=' in a)
    gid = args.get('id', '').strip()
    if not gid:
        print('Say which gallery: --id=<gallery id from galleries.json>')
        return 1
    out = os.path.join(OUT, 'build', 'out-special')
    meta, html = build(gid, out)
    if '--dry' in argv:
        print('DRY  would send "%s" to the list "%s"' % (meta['subject'], S.LIST_NAME))
        return 0
    key = os.environ.get('BREVO_API_KEY', '').strip()
    if not key:
        print('The BREVO_API_KEY secret is missing.')
        return 1
    senders = [s for s in S.call('GET', '/senders', key).get('senders', []) if s.get('active')]
    own = [s for s in senders if s.get('email', '').endswith('@kavasocialchessclub.com')]
    if not senders:
        print('Brevo has no active sender.')
        return 1
    sender = (own or senders)[0]
    for url in meta['photos']:
        if not S.wait_for(url):
            print('A photo is not on the live site yet (%s), so nothing was sent.' % url)
            return 1
    reply = os.environ.get('REPLY_TO', '').strip()

    if '--test' in argv:
        # the account owner's own address, so no address ever appears in the repo or the logs
        to = S.call('GET', '/account', key).get('email', '')
        if not to:
            print('Brevo did not say who owns the account, so no test was sent.')
            return 1
        body = {'sender': {'name': meta['from_name'], 'email': sender['email']}, 'to': [{'email': to}],
                'subject': '[TEST] ' + meta['subject'], 'htmlContent': html}
        if reply:
            body['replyTo'] = {'email': reply}
        try:
            S.call('POST', '/smtp/email', key, body)
        except RuntimeError as e:
            print(str(e).replace(to, '(the test address)').replace(reply or '\0', '(the reply address)'))
            return 1
        print('Test sent to the Brevo account owner.')
        return 0

    if '--send' not in argv:
        print('Nothing asked for: use --dry, --test or --send.')
        return 1
    try:
        led = json.load(open(LEDGER, encoding='utf-8'))
    except Exception:
        led = {}
    if gid in (led.get('sent') or {}):
        print('The %s email already went out (campaign %s). Not sending it twice.' % (gid, led['sent'][gid]['id']))
        return 1
    lists = S.call('GET', '/contacts/lists?limit=50', key).get('lists', [])
    match = [l for l in lists if l.get('name', '').strip().lower() == S.LIST_NAME.lower()]
    if not match:
        print('Brevo has no list called "%s".' % S.LIST_NAME)
        return 1
    body = {'name': 'Special · %s' % gid, 'subject': meta['subject'], 'previewText': meta['preheader'],
            'sender': {'name': meta['from_name'], 'email': sender['email']}, 'htmlContent': html,
            'recipients': {'listIds': [match[0]['id']]}}
    if reply:
        body['replyTo'] = reply
    try:
        made = S.call('POST', '/emailCampaigns', key, body)
    except RuntimeError as e:
        raise RuntimeError(str(e).replace(reply, '(the reply address)') if reply else str(e))
    cid = made.get('id')
    # recorded before the send call, so a retry after a network blip cannot double up
    led.setdefault('sent', {})[gid] = {'id': cid, 'at': datetime.now(T.EASTERN).isoformat(timespec='seconds')}
    led['_comment'] = 'Special one-off emails already sent, by gallery id. Written by build/special_email.py.'
    json.dump(led, open(LEDGER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    open(LEDGER, 'a', encoding='utf-8').write('\n')
    S.call('POST', '/emailCampaigns/%s/sendNow' % cid, key)
    status = S.call('GET', '/emailCampaigns/%s' % cid, key).get('status')
    print('Sent "%s" to %d members. Brevo campaign %s reports "%s".'
          % (meta['subject'], match[0].get('uniqueSubscribers', match[0].get('totalSubscribers', 0)), cid, status))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
