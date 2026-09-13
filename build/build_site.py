"""Build the site from build/template.html:  /index.html (English) and /es/index.html (Spanish).

Run from anywhere:   python build/build_site.py
Needs on this machine:
  - SRC: the club photo folder, sorted into the 01-05 subfolders
  - LOGO_SRC: the club logo PNG
  - COVER: the promo video cover frame
Everything else (partner logos, hall background, bracket art, promo video) is in build/src-logos.
"""
from PIL import Image, ImageOps
import os, re, shutil, hashlib, json, sys

HERE  = os.path.dirname(os.path.abspath(__file__))
OUT   = os.path.dirname(HERE)
LG    = os.path.join(HERE, 'src-logos')
SRC   = r'D:\Pictures\Kava Social Chess picture stuff\Website photo sort'   # moved off the Desktop 2026-09-09
LOGO_SRC = os.path.join(HERE, 'src-logos', 'club-logo.png')   # kept in the repo: the Desktop original is gone
COVER = r'D:\Desktop_Moved\Chess\Video Project kava Social Chess club\Kava Social Chess club night out!\Kava Social Chess club night out!-Cover.jpg'
DOMAIN = 'kavasocialchessclub.com'
URL = 'https://' + DOMAIN + '/'
sys.path.insert(0, HERE)
import i18n_es

for d in ['img', 'img/gallery', 'img/logos', 'media', 'es']:
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

def jpg(src, w, q, name):
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(OUT, 'img', name), 'JPEG', quality=q, optimize=True, progressive=True)
    return 'img/' + name, im.width / im.height

def png(src, w, name, square=False):
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGBA')
    im = im.resize((w, w), Image.LANCZOS) if square else (im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) if im.width > w else im)
    im.save(os.path.join(OUT, 'img', name), 'PNG', optimize=True)
    return 'img/' + name

# ---------------- assets (written once, shared by both languages) ----------------
M = {'LOGO': png(LOGO_SRC, 224, 'logo.png', square=True)}
hero = [('HERO', os.path.join(LG, 'hero-crop.jpg'), 1000, 76, 'hero.jpg'), ('SOCIAL', 'Kava social chess girls.png', 1100, 80, 'social.jpg'), ('SOCIAL2', 'chrome_6xZgOTnRDj.png', 1100, 80, 'social2.jpg'),
        ('STUDY', 'chrome_GRnR26LSto.png', 1100, 80, 'study.jpg'), ('COACH', 'chrome_q4UzvZj71T.png', 1100, 80, 'coach.jpg'),
        ('COACH2', 'Tournament Harold.jpg', 1100, 80, 'coach2.jpg'), ('SEASON', 'IMG_8373.jpg', 1200, 78, 'season.jpg'),
        ('SETUP', 'Kava social venue.png', 1400, 78, 'setup.jpg'), ('NIGHTPIC', 'Kava social group 3.png', 1000, 78, 'sunday.jpg')]
used = set()
for k, f, w, q, name in hero:
    M[k], _ = jpg(f if os.path.isabs(f) else os.path.join(SRC, f), w, q, name); used.add(f)
used.add('IMG_9978.jpg')
# desktop hero: the exact band the 1392x640 slot shows (aspect ~2.1), cut from the full-res crop so nothing upscales
_src = ImageOps.exif_transpose(Image.open(os.path.join(LG, 'hero-crop.jpg'))).convert('RGB')
_bh = int(_src.width / 2.11); _top = int((_src.height - _bh) * 0.62)
_band = _src.crop((0, _top, _src.width, _top + _bh)).resize((1600, round(1600 * _bh / _src.width)), Image.LANCZOS)
_band.save(os.path.join(OUT, 'img', 'hero-wide.jpg'), 'JPEG', quality=72, optimize=True, progressive=True); M['HEROWIDE'] = 'img/hero-wide.jpg'
M['VENUE'], _ = jpg(os.path.join(LG, 'ksc-store.jpg'), 1400, 78, 'venue.jpg')
M['BG'], _ = jpg(os.path.join(LG, 'bg.jpg'), 1086, 66, 'bg.jpg')
M['VPOSTER'], _ = jpg(COVER, 1080, 82, 'promo-poster.jpg')
for key, fn, out in [('L_MANASOTA', 'manasota.png', 'manasota.png'), ('L_TAMPA', 'tampa.png', 'tampa.png'), ('L_ORCA', 'orca.png', 'orca.png'),
                     ('L_ORLANDO', 'orlandocc.png', 'orlando.png'), ('L_STPETE', 'stpete.png', 'stpete.png'), ('L_OCA', 'orlandoassoc.png', 'orlando-assoc.png'), ('L_KSC', 'ksc1.png', 'kava-social-club.png'),
                     ('L_CLB', 'clb.png', 'chesslinebook.png'), ('L_BVILA', 'bvila.png', 'brandon-vila.png')]:
    M[key] = png(os.path.join(LG, fn), 400, 'logos/' + out)
for key, fn, out in [('TAB_ALL', 'all.png', 'bracket-all.png'), ('TAB_O1400', 'over-1400.png', 'bracket-over-1400.png'),
                     ('TAB_U1400', 'u1400.png', 'bracket-u1400.png'), ('TAB_U1000', 'u1000.png', 'bracket-u1000.png')]:
    M[key] = png(os.path.join(LG, fn), 900, out)
shutil.copy(os.path.join(LG, 'uschess.svg'), os.path.join(OUT, 'img', 'logos', 'uschess.svg')); M['L_USCHESS'] = 'img/logos/uschess.svg'
shutil.copy(os.path.join(LG, 'c67-dark.svg'), os.path.join(OUT, 'img', 'logos', 'chess67.svg')); M['L_C67'] = 'img/logos/chess67.svg'
shutil.copy(os.path.join(LG, 'promo-web.mp4'), os.path.join(OUT, 'media', 'promo.mp4')); M['VIDEO'] = 'media/promo.mp4'
if os.path.exists(os.path.join(LG, 'promo-720.mp4')):
    shutil.copy(os.path.join(LG, 'promo-720.mp4'), os.path.join(OUT, 'media', 'promo-720.mp4')); M['VIDEO_SMALL'] = 'media/promo-720.mp4'
else:
    M['VIDEO_SMALL'] = 'media/promo.mp4'

# gallery: curated lead order, then the rest alphabetically; duplicates and two weak shots dropped
LEAD = ['Kava social tourney 1.jpg', 'bodie.png', 'IMG_2081.jpg', 'kava chess night pic.png', 'Group pictures.png', 'Kava social squad 2.png', 'Kava social squad 1.png', 'kava patio pic.png', 'Kava social night 1.jpg', 'IMG_0777.jpg', 'IMG_0754.jpg', 'chrome_E9Ajt8XCgX.png', 'chess girls.jpg', 'IMG_1023.jpg', 'vegas 2025.png', 'chess pic 2.png', 'benji smile chess.png', 'that boi chess.png', 'chess kava cup.png', 'cade chess pic.png', 'stevo harold pics.png', 'stevo wham.png', 'maddie chess.webp', '30 bday.jpg', 'chrome_6DdiixDQtF.png', 'kava social club.jpg', 'Kava social group 3.png', 'chrome_6xZgOTnRDj.png', 'Kava social venue.png', 'de584ff4-615b-411f-8875-7e090e25171d.jpg', 'IMG_1050.jpg', 'chess club orlando.png', 'IMG_9764.jpg', 'Brian chess.jpg', 'kava vs orlando 4.png', 'kava chess pic.png', 'Chess club day 2.jpg', 'kava winners.png', 'kava patio pics.png', 'Tournament Harold.jpg', 'Taylor chess.jpg', 'Chess club night 2.jpg']
BLOCK = {'20250318_210927.jpg', 'IMG_4350.jpg', 'Kava social store front.webp'}  # storefront already leads chapter 09
alts = {'01 Club nights': ('A club night at Kava Social Chess Club in Bradenton', 'nights'),
        '02 Club events and group photos': ('Kava Social Chess Club members at a club event', 'events'),
        '03 Tournaments and travel': ('Kava Social Chess Club members at a tournament', 'travel'),
        '04 Venue': ('The club patio at Kava Social in downtown Bradenton', 'venue'),
        '05 Trophies and awards': ('Trophies won at Kava Social Chess Club events', 'trophies')}
used.discard('Tournament Harold.jpg')
def rank(f): return (LEAD.index(f), '') if f in LEAD else (len(LEAD), f.lower())
seen, tiles = set(), []
for folder in sorted(alts):
    for f in sorted(os.listdir(os.path.join(SRC, folder))):
        if f in used or f in BLOCK: continue
        p = os.path.join(SRC, folder, f); hsh = hashlib.md5(open(p, 'rb').read()).hexdigest()
        if hsh in seen: continue
        seen.add(hsh); tiles.append((f, p, alts[folder][0], alts[folder][1], hsh[:6]))
tiles.sort(key=lambda t: rank(t[0]))
GALLERY_OPEN = 14      # photos shown before the show-all button
gal = ''
made = set()
for i, (f, p, alt, cat, hsh) in enumerate(tiles):
    # position + content hash: a reorder changes the name, so no browser keeps showing the old photo
    path, ar = jpg(p, 720, 74, 'gallery/%02d-%s.jpg' % (i + 1, hsh)); made.add(os.path.basename(path))
    lazy = '' if i < 10 else ' loading="lazy"'
    hide = ' hidden' if i >= GALLERY_OPEN else ''   # the rest appear behind the show-all button
    gal += '\n      <img src="%s" alt="%s" data-cat="%s" data-ar="%s"%s%s>' % (path, alt, cat, round(ar, 4), lazy, hide)
for _old in os.listdir(os.path.join(OUT, 'img', 'gallery')):
    if _old not in made: os.remove(os.path.join(OUT, 'img', 'gallery', _old))

# favicon: cream knight on scarlet, built by hand for legibility at 16px (img/favicon*.png)

# ---------------- page assembly ----------------
TEMPLATE = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
# the sub-pages: English slug -> (Spanish slug, body file)
PAGES = {
    'code-of-conduct': ('es/codigo-de-conducta', 'conduct.html'),
    'beginners': ('es/principiantes', 'beginners.html'),
    'lessons': ('es/clases', 'lessons.html'),
    'calendar': ('es/calendario', None),   # assembled from the home page's calendar chapter
}


def es_links(html):
    """Point the page links at their Spanish twins."""
    for en, (es, _) in PAGES.items():
        html = html.replace('href="/%s/"' % en, 'href="/%s/"' % es)
    return html


DISCORD = 'https://discord.gg/sYCb7RnTgZ'
_head_end = TEMPLATE.index('</style>') + len('</style>')
STYLE = TEMPLATE[:_head_end]
MAST = TEMPLATE[TEMPLATE.index('<!-- ============ MASTHEAD ============ -->'):TEMPLATE.index('<!-- ============ HERO ============ -->')]
FOOT = TEMPLATE[TEMPLATE.index('<!-- ============ FOOTER ============ -->'):]
CAL = TEMPLATE[TEMPLATE.index('<!-- ============ 03 WHAT\'S ON'):TEMPLATE.index('<!-- ============ 04 WATCH')]
CAL = re.sub(r'<div class="chhead">.*?</div>\s*', '', CAL, count=1, flags=re.S)
CAL = CAL.replace('class="ch" id="events"', 'class="ch cal" id="events"').replace('<h2 class="d h2 rv">This month at the club</h2>', '<h1 class="d h2 rv">This month at the club</h1>')
CAL = '<main class="wrap page">' + CAL + '</main>'
BOOKED = json.load(open(os.path.join(OUT, 'events.json'), encoding='utf-8')).get('events', [])
addr = {"@type": "PostalAddress", "streetAddress": "540 13th St W", "addressLocality": "Bradenton", "addressRegion": "FL", "postalCode": "34205", "addressCountry": "US"}
place = {"@type": "Place", "name": "Kava Social Club", "address": "540 13th St W, Bradenton, FL 34205"}
adobe = {"@type": "Place", "name": "Adobe Kava", "address": {"@type": "PostalAddress", "streetAddress": "1302 13th Ave W", "addressLocality": "Bradenton", "addressRegion": "FL", "postalCode": "34205", "addressCountry": "US"}}

def build_page(lang):
    es = (lang == 'es')
    prefix = '../' if es else ''
    page_url = URL + ('es/' if es else '')
    h = TEMPLATE.replace('{{GALLERY}}', gal)
    h = h.replace('{{GALLERY_MORE}}', ('Ver las %d fotos' if es else 'Show all %d photos') % len(tiles))
    for k, v in M.items(): h = h.replace('{{%s}}' % k, v)
    assert '{{' not in h, 'unreplaced placeholder'
    if es:
        h = es_links(i18n_es.localize(h))
        # asset paths relative to /es/
        h = re.sub(r'(src|srcset|href|poster)="(img/|media/)', lambda m: '%s="%s%s' % (m.group(1), prefix, m.group(2)), h)
        h = h.replace('url(img/', 'url(../img/')
    # placeholders still pending from Harold: Google place ID (review link), Yelp URL
    if es:
        # language switch: mark ES active, load booked events from the site root
        h = h.replace('<a class="on" href="/">EN</a><a href="/es/">ES</a>', '<a href="/">EN</a><a class="on" href="/es/">ES</a>')
        h = h.replace('var EVENTS_URL="events.json";', 'var EVENTS_URL="../events.json";')
        h = h.replace('var REVIEWS_URL="reviews.json", MANUAL_URL="reviews-manual.json";', 'var REVIEWS_URL="../reviews.json", MANUAL_URL="../reviews-manual.json";')

    title = i18n_es.META['title'] if es else 'Kava Social Chess Club — Bradenton, FL'
    desc = i18n_es.META['desc'] if es else ("Bradenton's social chess club. Sundays and Tuesdays 8PM–midnight at Kava Social Club, 540 13th St W. "
                                            "Every level welcome, 21+, US Chess affiliate. Se habla español.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": URL + "#site", "url": URL, "name": "Kava Social Chess Club", "alternateName": "Kava Social Chess", "inLanguage": ["en", "es"]},
        {"@type": "SportsClub", "@id": URL + "#club", "name": "Kava Social Chess Club", "url": page_url, "logo": URL + "img/logo.png", "image": URL + "img/hero.jpg",
         "description": desc, "foundingDate": "2021", "telephone": "+1-786-250-8993", "email": "kavasocialchess@gmail.com", "address": addr,
         "geo": {"@type": "GeoCoordinates", "latitude": 27.4958, "longitude": -82.5720},
         "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Sunday", "Tuesday"], "opens": "20:00", "closes": "23:59"},
            {"@type": "OpeningHoursSpecification", "dayOfWeek": "Thursday", "opens": "19:00", "closes": "23:00"}],
         "sameAs": ["https://www.instagram.com/kavasocialchessclub/", "https://www.facebook.com/KavaSocialChessClub",
                    "https://chess67.com/club/kava-social-chess-club", "https://new.uschess.org/user/132555/affiliates/3151294",
                    "https://ladder.kavasocialchessclub.com/", "https://www.yelp.com/biz/kava-social-chess-club-bradenton"],
         "location": {"@type": "Place", "name": "Kava Social Club", "url": "https://www.thekavasocialclub.com/", "address": addr},
         "knowsLanguage": ["en", "es"]},
        {"@type": "Event", "name": ("Kava Social Chess Club — noche de domingo" if es else "Kava Social Chess Club — Sunday night"),
         "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Sunday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
         "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"},
        {"@type": "Event", "name": ("Kava Social Chess Club — noche de estudio (martes)" if es else "Kava Social Chess Club — Tuesday study night"),
         "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Tuesday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
         "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"},
        {"@type": "Event", "name": ("Kava Social Chess Club — noche de estudio intermedio+ (jueves)" if es else "Kava Social Chess Club — Intermediate+ study night (Thursday)"),
         "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Thursday", "startTime": "19:00", "endTime": "23:00", "repeatFrequency": "P1W"},
         "location": adobe, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"}]}
    for ev in booked_ld(es):
        ld['@graph'].append(ev)
    q = lambda s: s.replace('"', '&quot;')
    head = ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n' % lang +
            '<title>' + title + '</title>\n<meta name="description" content="' + q(desc) + '">\n'
            '<link rel="canonical" href="' + page_url + '">\n'
            '<link rel="alternate" hreflang="en" href="' + URL + '">\n<link rel="alternate" hreflang="es" href="' + URL + 'es/">\n<link rel="alternate" hreflang="x-default" href="' + URL + '">\n'
            '<link rel="icon" href="' + prefix + 'img/favicon-v3-32.png" sizes="32x32" type="image/png">\n<link rel="icon" href="' + prefix + 'img/favicon-v3-192.png" sizes="192x192" type="image/png">\n<link rel="apple-touch-icon" href="' + prefix + 'img/favicon-v3-180.png">\n'
            '<meta property="og:site_name" content="Kava Social Chess Club">\n<meta property="og:type" content="website">\n<meta property="og:title" content="' + title + '">\n<meta property="og:description" content="' + q(desc) + '">\n'
            '<meta property="og:url" content="' + page_url + '">\n<meta property="og:image" content="' + URL + 'img/hero.jpg">\n<meta property="og:locale" content="' + ('es_US' if es else 'en_US') + '">\n'
            '<meta name="twitter:card" content="summary_large_image">\n<meta name="theme-color" content="#0C0D0E">\n<link rel="preload" as="image" href="' + prefix + 'img/hero-wide.jpg" media="(min-width:1101px)">\n<link rel="preload" as="image" href="' + prefix + 'img/hero.jpg" media="(max-width:1100px)">\n'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n')
    body = re.sub(r'^<title>[^<]*</title>\n', '', h)
    cut = body.index('</style>') + len('</style>')
    doc = head + body[:cut] + '\n</head>\n<body>' + body[cut:] + '\n</body>\n</html>\n'
    out = os.path.join(OUT, 'es', 'index.html') if es else os.path.join(OUT, 'index.html')
    open(out, 'w', encoding='utf-8').write(doc)
    return os.path.getsize(out) // 1024

ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
         'stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>')


def booked_ld(es):
    """Event entities for the booked one-offs that are still ahead."""
    import datetime
    today = datetime.date.today().isoformat()
    out = []
    for e in BOOKED:
        if e.get('date', '') < today:
            continue
        name = (e.get('title_es') if es else None) or e.get('title', '')
        note = (e.get('note_es') if es else None) or e.get('note', '')
        loc = ({"@type": "Place", "name": e['venue'], "address": e.get('addr', e['venue'])} if e.get('venue') else place)
        ev = {"@type": "Event", "name": "Kava Social Chess Club: " + name, "startDate": e['date'], "description": note,
              "location": loc, "organizer": {"@id": URL + "#club"},
              "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled"}
        if e.get('url'):
            ev['url'] = e['url']
        if e.get('age'):
            ev['typicalAgeRange'] = e['age'].replace('+', '-')
        out.append(ev)
    return out


def build_subpage(lang, slug_en, meta):
    """One sub-page and its Spanish twin, sharing the site's masthead, styles and footer."""
    es = (lang == 'es')
    slug_es, body_file = PAGES[slug_en]
    slug = slug_es if es else slug_en
    depth = '../../' if es else '../'
    page_url = URL + slug + '/'
    home = '/es/' if es else '/'
    page = open(os.path.join(HERE, body_file), encoding='utf-8').read() if body_file else CAL

    body = MAST + page + FOOT
    btn = ('<a class="btn btn-p" href="%s" target="_blank" rel="noopener">Join the Discord<i class="disc">%s</i></a>'
           % (DISCORD, ARROW)) if DISCORD else ''
    body = body.replace('{{DISCORD_BTN}}', btn).replace('{{HOME}}', home).replace('{{ARROW}}', ARROW)
    body = body.replace('var EVENTS_URL="events.json";', 'var EVENTS_URL="%sevents.json";' % depth)
    for k, v in M.items():
        body = body.replace('{{%s}}' % k, v)
    assert '{{' not in body, 'unreplaced placeholder on ' + slug
    switch = '<a class="on" href="/">EN</a><a href="/es/">ES</a>'
    if es:
        body = es_links(i18n_es.localize(body))
        body = body.replace(switch, '<a href="/%s/">EN</a><a class="on" href="/%s/">ES</a>' % (slug_en, slug_es))
    else:
        body = body.replace(switch, '<a class="on" href="/%s/">EN</a><a href="/%s/">ES</a>' % (slug_en, slug_es))
    # the masthead's in-page anchors have to point back at the home page from here
    body = re.sub(r'href="#([a-z0-9]+)"', lambda m: 'href="%s#%s"' % (home, m.group(1)), body)
    # away from the home page, the Calendar link is the calendar page
    body = body.replace('href="%s#events"' % home, 'href="/%s/"' % ('es/calendario' if es else 'calendar'))
    body = re.sub(r'(src|srcset|href|poster)="(img/|media/)', lambda m: '%s="%s%s' % (m.group(1), depth, m.group(2)), body)
    body = body.replace('url(img/', 'url(%simg/' % depth)

    title = meta['title_es' if es else 'title']
    desc = meta['desc_es' if es else 'desc']
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "name": title, "url": page_url, "description": desc,
         "isPartOf": {"@type": "WebSite", "url": URL}, "publisher": {"@id": URL + "#club"}, "inLanguage": lang}]}
    for ev in booked_ld(es):
        ld['@graph'].append(ev)
    faq = re.findall(r'<details><summary>(.*?)</summary><p class="body">(.*?)</p></details>', body)
    if faq:
        import html as _html
        plain = lambda t: _html.unescape(re.sub(r'<[^>]+>', '', t))
        ld["@graph"].append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": plain(q), "acceptedAnswer": {"@type": "Answer", "text": plain(ans)}} for q, ans in faq]})
    q = lambda t: t.replace('"', '&quot;')
    head = ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n' % lang +
            '<title>' + title + '</title>\n<meta name="description" content="' + q(desc) + '">\n'
            '<link rel="canonical" href="' + page_url + '">\n'
            '<link rel="alternate" hreflang="en" href="' + URL + slug_en + '/">\n'
            '<link rel="alternate" hreflang="es" href="' + URL + slug_es + '/">\n'
            '<link rel="alternate" hreflang="x-default" href="' + URL + slug_en + '/">\n'
            '<link rel="icon" href="' + depth + 'img/favicon-v3-32.png" sizes="32x32" type="image/png">\n'
            '<link rel="icon" href="' + depth + 'img/favicon-v3-192.png" sizes="192x192" type="image/png">\n'
            '<link rel="apple-touch-icon" href="' + depth + 'img/favicon-v3-180.png">\n'
            '<meta property="og:site_name" content="Kava Social Chess Club">\n<meta property="og:type" content="article">\n<meta property="og:title" content="' + title + '">\n'
            '<meta property="og:description" content="' + q(desc) + '">\n'
            '<meta property="og:url" content="' + page_url + '">\n'
            '<meta property="og:image" content="' + URL + meta.get('image', 'img/hero-wide.jpg') + '">\n'
            '<meta name="theme-color" content="#0C0D0E">\n'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n')
    style = re.sub(r'^<title>[^<]*</title>\n', '', STYLE)
    doc = head + style + '\n</head>\n<body>' + body + '\n</body>\n</html>\n'
    out_dir = os.path.join(OUT, *slug.split('/'))
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(doc)
    return os.path.getsize(os.path.join(out_dir, 'index.html')) // 1024


SUBPAGES = {
    'calendar': {
        'title': 'Calendar — Kava Social Chess Club, Bradenton',
        'title_es': 'Calendario — Kava Social Chess Club, Bradenton',
        'desc': ('What\'s on at Bradenton\'s social chess club: Sundays alternate social and league, Tuesdays are study '
                 'night, plus tournaments, lectures and simuls as they are booked. Add the club to your calendar.'),
        'desc_es': ('Qué hay en el club de ajedrez social de Bradenton: los domingos alternan social y liga, los martes son '
                    'noche de estudio, más torneos, charlas y simultáneas según se programan. Agrega el club a tu calendario.'),
    },
    'code-of-conduct': {
        'title': 'Code of conduct — Kava Social Chess Club',
        'title_es': 'Código de conducta — Kava Social Chess Club',
        'desc': ('The rules at Kava Social Chess Club: every level welcome, no chess bullying, and US Chess '
                 'Safe Play and fair play rules respected at club nights and rated events.'),
        'desc_es': ('Las reglas del Kava Social Chess Club: todos los niveles son bienvenidos, nada de bullying '
                    'ajedrecístico, y las reglas Safe Play de US Chess aplican en nuestras noches de club.'),
    },
    'beginners': {
        'title': 'Your first night — a beginner\'s guide to Kava Social Chess Club',
        'title_es': 'Tu primera noche — guía para principiantes del Kava Social Chess Club',
        'desc': ('Never played, or not since school? How a club night works in Bradenton: when to come, what to bring '
                 '(nothing), who you\'ll play, and answers to the questions everyone asks first.'),
        'desc_es': ('¿Nunca has jugado, o no desde la escuela? Cómo funciona una noche de club en Bradenton: cuándo venir, '
                    'qué traer (nada), con quién jugarás y respuestas a las preguntas que todos hacen primero.'),
        'image': 'img/sunday.jpg',
    },
    'lessons': {
        'title': 'Private chess lessons in Bradenton & Sarasota — Kava Social Chess Club',
        'title_es': 'Clases privadas de ajedrez en Bradenton y Sarasota — Kava Social Chess Club',
        'desc': ('One-on-one chess coaching with club director Harold Gonzalez. Beginner lessons from $40/hr, tournament '
                 'training from $55/hr. Over the board in Bradenton and Sarasota, online anywhere, in English or Spanish.'),
        'desc_es': ('Clases de ajedrez uno a uno con el director del club, Harold Gonzalez. Nivel principiante desde $40/hr, '
                    'entrenamiento de torneo desde $55/hr. Presencial en Bradenton y Sarasota, en línea en cualquier parte, '
                    'en inglés o español.'),
        'image': 'img/coach.jpg',
    },
}


en_kb = build_page('en'); es_kb = build_page('es')
sub_kb = {slug: (build_subpage('en', slug, SUBPAGES[slug]), build_subpage('es', slug, SUBPAGES[slug])) for slug in PAGES}
open(os.path.join(OUT, 'CNAME'), 'w').write(DOMAIN + '\n')
open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: ' + URL + 'sitemap.xml\n')
def _url(loc, en, es, freq, pri):
    return ('<url><loc>' + loc + '</loc><xhtml:link rel="alternate" hreflang="en" href="' + en + '"/>'
            '<xhtml:link rel="alternate" hreflang="es" href="' + es + '"/><changefreq>' + freq + '</changefreq>'
            '<priority>' + pri + '</priority></url>\n')


_rows = [_url(URL, URL, URL + 'es/', 'weekly', '1.0'), _url(URL + 'es/', URL, URL + 'es/', 'weekly', '0.9')]
for _en, (_es, _) in PAGES.items():
    _freq, _pri = ('yearly', '0.5') if _en == 'code-of-conduct' else (('weekly', '0.9') if _en == 'calendar' else ('monthly', '0.8'))
    _rows.append(_url(URL + _en + '/', URL + _en + '/', URL + _es + '/', _freq, _pri))
    _rows.append(_url(URL + _es + '/', URL + _en + '/', URL + _es + '/', _freq, str(float(_pri) - 0.1)))
open(os.path.join(OUT, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + ''.join(_rows) + '</urlset>\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')


def ics():
    """calendar.ics: every club night as a repeating event, plus the booked one-offs."""
    def esc(t):
        return t.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
    VENUE = 'Kava Social Club, 540 13th St W, Bradenton, FL 34205'
    ADOBE = 'Adobe Kava, 1302 13th Ave W, Bradenton, FL 34205'
    L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Kava Social Chess Club//kavasocialchessclub.com//EN', 'CALSCALE:GREGORIAN',
         'METHOD:PUBLISH', 'X-WR-CALNAME:Kava Social Chess Club', 'X-WR-TIMEZONE:America/New_York', 'REFRESH-INTERVAL;VALUE=DURATION:P1D',
         'BEGIN:VTIMEZONE', 'TZID:America/New_York',
         'BEGIN:DAYLIGHT', 'TZOFFSETFROM:-0500', 'TZOFFSETTO:-0400', 'TZNAME:EDT', 'DTSTART:19700308T020000', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU', 'END:DAYLIGHT',
         'BEGIN:STANDARD', 'TZOFFSETFROM:-0400', 'TZOFFSETTO:-0500', 'TZNAME:EST', 'DTSTART:19701101T020000', 'RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU', 'END:STANDARD',
         'END:VTIMEZONE']
    def vevent(uid, summary, start, end, where, desc, rrule=None):
        L.extend(['BEGIN:VEVENT', 'UID:' + uid + '@kavasocialchessclub.com', 'DTSTAMP:20260910T000000Z',
                  'DTSTART;TZID=America/New_York:' + start, 'DTEND;TZID=America/New_York:' + end,
                  'SUMMARY:' + esc(summary), 'LOCATION:' + esc(where), 'DESCRIPTION:' + esc(desc), 'URL:' + URL + 'calendar/'])
        if rrule:
            L.append('RRULE:' + rrule)
        L.append('END:VEVENT')
    vevent('league', 'League night - Kava Social Chess Club', '20260830T200000', '20260830T235900', VENUE,
           'Every other Sunday. Season games in your bracket. In-house ratings, only at the club, for fun. 21+.', 'FREQ=WEEKLY;INTERVAL=2;BYDAY=SU')
    vevent('social', 'Social Sunday - Kava Social Chess Club', '20260906T200000', '20260906T235900', VENUE,
           'Every other Sunday. Free play: come and play, hang out, talk. 21+.', 'FREQ=WEEKLY;INTERVAL=2;BYDAY=SU')
    vevent('study', 'Study night - Kava Social Chess Club', '20260901T200000', '20260901T235900', VENUE,
           'Every Tuesday. The room works through books, puzzles and grandmaster games together. 21+.', 'FREQ=WEEKLY;BYDAY=TU')
    # Thursday is not in the feed on purpose: it is not a drop-in night, people contact Harold first
    for e in BOOKED:
        d = e['date'].replace('-', '')
        m = re.match(r'(\d{1,2}):(\d{2}) ?(AM|PM)', e.get('time', '') or '')
        hh = 20
        if m:
            hh = int(m.group(1)) % 12 + (12 if m.group(3) == 'PM' else 0)
        vevent('booked-' + e['date'] + '-' + re.sub(r'[^a-z0-9]+', '-', e.get('title', '').lower())[:40],
               e.get('title', 'Club event') + ' - Kava Social Chess Club', '%sT%02d0000' % (d, hh), '%sT%02d0000' % (d, min(hh + 4, 23)),
               e.get('addr') or e.get('venue') or VENUE, e.get('note', ''))
    L.append('END:VCALENDAR')
    open(os.path.join(OUT, 'calendar.ics'), 'w', encoding='utf-8', newline='').write('\r\n'.join(L) + '\r\n')


ics()
print('built index.html (%d KB), es/index.html (%d KB), %s, %d gallery photos'
      % (en_kb, es_kb, ', '.join('%s (%d/%d KB)' % (k, v[0], v[1]) for k, v in sub_kb.items()), len(tiles)))
