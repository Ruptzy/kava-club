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
SRC   = r'C:\Users\17862\Desktop\Kava social website pictures'
LOGO_SRC = r'C:\Users\17862\Desktop\Kava logo.png'
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
hero = [('HERO', os.path.join(LG, 'hero-crop.jpg'), 1800, 78, 'hero.jpg'), ('SOCIAL', 'Kava social chess girls.png', 1100, 80, 'social.jpg'),
        ('STUDY', 'chrome_GRnR26LSto.png', 1100, 80, 'study.jpg'), ('COACH', 'chrome_q4UzvZj71T.png', 1100, 80, 'coach.jpg'),
        ('COACH2', 'Tournament Harold.jpg', 1100, 80, 'coach2.jpg'), ('SEASON', 'IMG_8373.jpg', 1200, 78, 'season.jpg'),
        ('SETUP', 'Kava social venue.png', 1400, 78, 'setup.jpg'), ('NIGHTPIC', 'Kava social group 3.png', 1000, 78, 'sunday.jpg')]
used = set()
for k, f, w, q, name in hero:
    M[k], _ = jpg(f if os.path.isabs(f) else os.path.join(SRC, f), w, q, name); used.add(f)
used.add('IMG_9978.jpg')
M['VENUE'], _ = jpg(os.path.join(LG, 'ksc-store.jpg'), 1400, 78, 'venue.jpg')
M['BG'], _ = jpg(os.path.join(LG, 'bg.jpg'), 1086, 66, 'bg.jpg')
M['VPOSTER'], _ = jpg(COVER, 720, 76, 'promo-poster.jpg')
for key, fn, out in [('L_MANASOTA', 'manasota.png', 'manasota.png'), ('L_TAMPA', 'tampa.png', 'tampa.png'), ('L_ORCA', 'orca.png', 'orca.png'),
                     ('L_ORLANDO', 'orlandocc.png', 'orlando.png'), ('L_STPETE', 'stpete.png', 'stpete.png'), ('L_KSC', 'ksc1.png', 'kava-social-club.png'),
                     ('L_CLB', 'clb.png', 'chesslinebook.png')]:
    M[key] = png(os.path.join(LG, fn), 400, 'logos/' + out)
for key, fn, out in [('TAB_ALL', 'all.png', 'bracket-all.png'), ('TAB_O1400', 'over-1400.png', 'bracket-over-1400.png'),
                     ('TAB_U1400', 'u1400.png', 'bracket-u1400.png'), ('TAB_U1000', 'u1000.png', 'bracket-u1000.png')]:
    M[key] = png(os.path.join(LG, fn), 900, out)
shutil.copy(os.path.join(LG, 'uschess.svg'), os.path.join(OUT, 'img', 'logos', 'uschess.svg')); M['L_USCHESS'] = 'img/logos/uschess.svg'
shutil.copy(os.path.join(LG, 'c67-dark.svg'), os.path.join(OUT, 'img', 'logos', 'chess67.svg')); M['L_C67'] = 'img/logos/chess67.svg'
shutil.copy(os.path.join(LG, 'promo-web.mp4'), os.path.join(OUT, 'media', 'promo.mp4')); M['VIDEO'] = 'media/promo.mp4'

# gallery: curated lead order, then the rest alphabetically; duplicates and two weak shots dropped
LEAD = ['Kava social tourney 1.jpg', 'Tournament Harold.jpg', 'chrome_6DdiixDQtF.png', 'kava social club.jpg', 'Kava social group 3.png', 'IMG_2081.jpg',
        'chrome_6xZgOTnRDj.png', 'Kava social venue.png', 'de584ff4-615b-411f-8875-7e090e25171d.jpg', 'IMG_1050.jpg', 'Kava social squad 2.png',
        'IMG_0754.jpg', 'IMG_9764.jpg', 'Kava social night 1.jpg']
BLOCK = {'20250318_210927.jpg', 'IMG_4350.jpg'}
alts = {'01 Club nights': ('A club night at Kava Social Chess Club in Bradenton', 'nights'),
        '02 Club events and group photos': ('Kava Social Chess Club members at a club event', 'events'),
        '03 Tournaments and travel': ('Kava Social Chess Club members at a tournament', 'travel'),
        '04 Venue': ('The club room at Kava Social in downtown Bradenton', 'venue'),
        '05 Trophies and awards': ('Trophies won at Kava Social Chess Club events', 'trophies')}
used.discard('Tournament Harold.jpg')
def rank(f): return (LEAD.index(f), '') if f in LEAD else (len(LEAD), f.lower())
seen, tiles = set(), []
for folder in sorted(alts):
    for f in sorted(os.listdir(os.path.join(SRC, folder))):
        if f in used or f in BLOCK: continue
        p = os.path.join(SRC, folder, f); hsh = hashlib.md5(open(p, 'rb').read()).hexdigest()
        if hsh in seen: continue
        seen.add(hsh); tiles.append((f, p, alts[folder][0], alts[folder][1]))
tiles.sort(key=lambda t: rank(t[0]))
gal = ''
for i, (f, p, alt, cat) in enumerate(tiles):
    path, ar = jpg(p, 720, 74, 'gallery/%02d.jpg' % (i + 1))
    lazy = '' if i < 10 else ' loading="lazy"'
    gal += '\n      <img src="%s" alt="%s" data-cat="%s" data-ar="%s"%s>' % (path, alt, cat, round(ar, 4), lazy)

# favicon: the knight only, cropped from the logo
lg = Image.open(LOGO_SRC).convert('RGBA'); w, hh = lg.size
fav = lg.crop((int(w*0.30), int(hh*0.17), int(w*0.70), int(hh*0.62))).resize((180, 180), Image.LANCZOS)
bg = Image.new('RGBA', (180, 180), (12, 13, 14, 255)); bg.alpha_composite(fav); bg.save(os.path.join(OUT, 'img', 'favicon.png'))

# ---------------- page assembly ----------------
TEMPLATE = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
addr = {"@type": "PostalAddress", "streetAddress": "540 13th St W", "addressLocality": "Bradenton", "addressRegion": "FL", "postalCode": "34205", "addressCountry": "US"}
place = {"@type": "Place", "name": "Kava Social Club", "address": "540 13th St W, Bradenton, FL 34205"}

def build_page(lang):
    es = (lang == 'es')
    prefix = '../' if es else ''
    page_url = URL + ('es/' if es else '')
    h = TEMPLATE.replace('{{GALLERY}}', gal)
    for k, v in M.items(): h = h.replace('{{%s}}' % k, v)
    assert '{{' not in h, 'unreplaced placeholder'
    if es:
        h = i18n_es.localize(h)
        # asset paths relative to /es/
        h = re.sub(r'(src|href|poster)="(img/|media/)', lambda m: '%s="%s%s' % (m.group(1), prefix, m.group(2)), h)
        h = h.replace('url(img/', 'url(../img/')
    # public-site tweaks (the template is shared with the Claude artifact mockup)
    h = h.replace('if(!d){note.textContent="Showing the regular schedule. Booked events load when this page is opened in Claude."; return;}', 'if(!d){return;}')
    h = h.replace('} else { note.textContent="Showing the regular schedule."; }', '}')
    h = h.replace('href="https://search.google.com/local/writereview?placeid=REPLACE_WITH_PLACE_ID"', 'href="https://www.google.com/search?q=Kava+Social+Chess+Club+Bradenton+reviews"')
    h = h.replace('        <a href="#yelp">Yelp</a>\n', '')
    # language switch: EN page -> /es/, ES page -> /
    h = h.replace('<a class="lang" href="#es">ES</a>', '<a class="lang" href="/es/">ES</a>')
    h = h.replace('<a class="btn btn-s" href="#es">Espa&ntilde;ol</a>', '<a class="btn btn-s" href="/es/">Espa&ntilde;ol</a>')
    if es:
        h = h.replace('<a class="btn btn-s" href="/es/">Espa&ntilde;ol</a>', '<a class="btn btn-s" href="/">English</a>')

    title = i18n_es.META['title'] if es else 'Kava Social Chess Club — Bradenton, FL'
    desc = i18n_es.META['desc'] if es else ("Bradenton's social chess club. Sundays and Tuesdays 8PM–midnight at Kava Social Club, 540 13th St W. "
                                            "Every level welcome, 21+, US Chess affiliate. Se habla español.")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "SportsClub", "@id": URL + "#club", "name": "Kava Social Chess Club", "url": page_url, "logo": URL + "img/logo.png", "image": URL + "img/hero.jpg",
         "description": desc, "foundingDate": "2021", "telephone": "+1-786-250-8993", "email": "kavasocialchess@gmail.com", "address": addr,
         "geo": {"@type": "GeoCoordinates", "latitude": 27.4958, "longitude": -82.5720},
         "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Sunday", "Tuesday"], "opens": "20:00", "closes": "23:59"},
            {"@type": "OpeningHoursSpecification", "dayOfWeek": "Thursday", "opens": "19:00", "closes": "23:00"}],
         "sameAs": ["https://www.instagram.com/kavasocialchessclub/", "https://www.facebook.com/KavaSocialChessClub",
                    "https://chess67.com/club/kava-social-chess-club", "https://new.uschess.org/user/132555/affiliates/3151294",
                    "https://ladder.kavasocialchessclub.com/"],
         "location": {"@type": "Place", "name": "Kava Social Club", "url": "https://www.thekavasocialclub.com/", "address": addr},
         "knowsLanguage": ["en", "es"]},
        {"@type": "Event", "name": ("Kava Social Chess Club — noche de domingo" if es else "Kava Social Chess Club — Sunday night"),
         "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Sunday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
         "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"},
        {"@type": "Event", "name": ("Kava Social Chess Club — noche de estudio (martes)" if es else "Kava Social Chess Club — Tuesday study night"),
         "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Tuesday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
         "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"}]}
    q = lambda s: s.replace('"', '&quot;')
    head = ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n' % lang +
            '<title>' + title + '</title>\n<meta name="description" content="' + q(desc) + '">\n'
            '<link rel="canonical" href="' + page_url + '">\n'
            '<link rel="alternate" hreflang="en" href="' + URL + '">\n<link rel="alternate" hreflang="es" href="' + URL + 'es/">\n<link rel="alternate" hreflang="x-default" href="' + URL + '">\n'
            '<link rel="icon" href="' + prefix + 'img/favicon.png" type="image/png">\n<link rel="apple-touch-icon" href="' + prefix + 'img/favicon.png">\n'
            '<meta property="og:type" content="website">\n<meta property="og:title" content="' + title + '">\n<meta property="og:description" content="' + q(desc) + '">\n'
            '<meta property="og:url" content="' + page_url + '">\n<meta property="og:image" content="' + URL + 'img/hero.jpg">\n<meta property="og:locale" content="' + ('es_US' if es else 'en_US') + '">\n'
            '<meta name="twitter:card" content="summary_large_image">\n<meta name="theme-color" content="#0C0D0E">\n<link rel="preload" as="image" href="' + prefix + 'img/hero.jpg">\n'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n')
    body = re.sub(r'^<title>[^<]*</title>\n', '', h)
    cut = body.index('</style>') + len('</style>')
    doc = head + body[:cut] + '\n</head>\n<body>' + body[cut:] + '\n</body>\n</html>\n'
    out = os.path.join(OUT, 'es', 'index.html') if es else os.path.join(OUT, 'index.html')
    open(out, 'w', encoding='utf-8').write(doc)
    return os.path.getsize(out) // 1024

en_kb = build_page('en'); es_kb = build_page('es')
open(os.path.join(OUT, 'CNAME'), 'w').write(DOMAIN + '\n')
open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\nSitemap: ' + URL + 'sitemap.xml\n')
open(os.path.join(OUT, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    '<url><loc>' + URL + '</loc><xhtml:link rel="alternate" hreflang="en" href="' + URL + '"/><xhtml:link rel="alternate" hreflang="es" href="' + URL + 'es/"/><changefreq>weekly</changefreq><priority>1.0</priority></url>\n'
    '<url><loc>' + URL + 'es/</loc><xhtml:link rel="alternate" hreflang="en" href="' + URL + '"/><xhtml:link rel="alternate" hreflang="es" href="' + URL + 'es/"/><changefreq>weekly</changefreq><priority>0.9</priority></url>\n'
    '</urlset>\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('built index.html (%d KB) and es/index.html (%d KB), %d gallery photos' % (en_kb, es_kb, len(tiles)))
