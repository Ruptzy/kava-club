"""Build index.html + assets from build/template.html.

Run from anywhere:   python build/build_site.py
Needs on this machine:
  - SRC: the club photo folder, sorted into the 01-05 subfolders
  - the club logo PNG (LOGO_SRC)
  - the promo video cover frame (COVER)
Everything else (partner logos, hall background, bracket art, promo video) is in build/src-logos.
"""
from PIL import Image, ImageOps
import os, re, shutil, hashlib, json

HERE  = os.path.dirname(os.path.abspath(__file__))
OUT   = os.path.dirname(HERE)
LG    = os.path.join(HERE, 'src-logos')
SRC   = r'C:\Users\17862\Desktop\Kava social website pictures'
LOGO_SRC = r'C:\Users\17862\Desktop\Kava logo.png'
COVER = r'D:\Desktop_Moved\Chess\Video Project kava Social Chess club\Kava Social Chess club night out!\Kava Social Chess club night out!-Cover.jpg'
DOMAIN = 'kavasocialchessclub.com'
URL = 'https://' + DOMAIN + '/'

for d in ['img', 'img/gallery', 'img/logos', 'media']:
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

M = {'LOGO': png(LOGO_SRC, 224, 'logo.png', square=True)}
hero = [('HERO', 'IMG_9978.jpg', 1800, 78, 'hero.jpg'), ('SOCIAL', 'Kava social chess girls.png', 1100, 80, 'social.jpg'),
        ('STUDY', 'chrome_GRnR26LSto.png', 1100, 80, 'study.jpg'), ('COACH', 'chrome_q4UzvZj71T.png', 1100, 80, 'coach.jpg'),
        ('COACH2', 'Tournament Harold.jpg', 1100, 80, 'coach2.jpg'), ('SEASON', 'IMG_8373.jpg', 1200, 78, 'season.jpg'),
        ('SETUP', 'Kava social venue.png', 1400, 78, 'setup.jpg'), ('NIGHTPIC', 'Kava social group 3.png', 1000, 78, 'sunday.jpg')]
used = set()
for k, f, w, q, name in hero:
    M[k], _ = jpg(os.path.join(SRC, f), w, q, name); used.add(f)
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

h = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read().replace('{{GALLERY}}', gal)
for k, v in M.items(): h = h.replace('{{%s}}' % k, v)
assert '{{' not in h, 'unreplaced placeholder'

# public-site tweaks (the template is shared with the Claude artifact mockup)
h = h.replace('if(!d){note.textContent="Showing the regular schedule. Booked events load when this page is opened in Claude."; return;}', 'if(!d){return;}')
h = h.replace('} else { note.textContent="Showing the regular schedule."; }', '}')
h = h.replace('href="https://search.google.com/local/writereview?placeid=REPLACE_WITH_PLACE_ID"', 'href="https://www.google.com/search?q=Kava+Social+Chess+Club+Bradenton+reviews"')
h = h.replace('        <a href="#yelp">Yelp</a>\n', '')

title = 'Kava Social Chess Club — Bradenton, FL'
desc = ("Bradenton's social chess club. Sundays and Tuesdays 8PM–midnight at Kava Social Club, 540 13th St W. Every level welcome, 21+, "
        "US Chess affiliate. Se habla español.")
addr = {"@type": "PostalAddress", "streetAddress": "540 13th St W", "addressLocality": "Bradenton", "addressRegion": "FL", "postalCode": "34205", "addressCountry": "US"}
place = {"@type": "Place", "name": "Kava Social Club", "address": "540 13th St W, Bradenton, FL 34205"}
ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "SportsClub", "@id": URL + "#club", "name": "Kava Social Chess Club", "url": URL, "logo": URL + "img/logo.png", "image": URL + "img/hero.jpg",
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
    {"@type": "Event", "name": "Kava Social Chess Club — Sunday night",
     "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Sunday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
     "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"},
    {"@type": "Event", "name": "Kava Social Chess Club — Tuesday study night",
     "eventSchedule": {"@type": "Schedule", "byDay": "https://schema.org/Tuesday", "startTime": "20:00", "endTime": "23:59", "repeatFrequency": "P1W"},
     "location": place, "organizer": {"@id": URL + "#club"}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "typicalAgeRange": "21-"}]}
q = lambda s: s.replace('"', '&quot;')
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>' + title + '</title>\n<meta name="description" content="' + q(desc) + '">\n'
        '<link rel="canonical" href="' + URL + '">\n<link rel="icon" href="img/favicon.png" type="image/png">\n<link rel="apple-touch-icon" href="img/favicon.png">\n'
        '<meta property="og:type" content="website">\n<meta property="og:title" content="' + title + '">\n<meta property="og:description" content="' + q(desc) + '">\n'
        '<meta property="og:url" content="' + URL + '">\n<meta property="og:image" content="' + URL + 'img/hero.jpg">\n<meta name="twitter:card" content="summary_large_image">\n'
        '<meta name="theme-color" content="#0C0D0E">\n<link rel="preload" as="image" href="img/hero.jpg">\n'
        '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n')
body = re.sub(r'^<title>[^<]*</title>\n', '', h)
cut = body.index('</style>') + len('</style>')
doc = head + body[:cut] + '\n</head>\n<body>' + body[cut:] + '\n</body>\n</html>\n'
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(doc)

# favicon: the knight only, cropped from the logo
lg = Image.open(LOGO_SRC).convert('RGBA'); w, hh = lg.size
fav = lg.crop((int(w*0.30), int(hh*0.17), int(w*0.70), int(hh*0.62))).resize((180, 180), Image.LANCZOS)
bg = Image.new('RGBA', (180, 180), (12, 13, 14, 255)); bg.alpha_composite(fav); bg.save(os.path.join(OUT, 'img', 'favicon.png'))

open(os.path.join(OUT, 'CNAME'), 'w').write(DOMAIN + '\n')
open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nAllow: /\nSitemap: ' + URL + 'sitemap.xml\n')
open(os.path.join(OUT, 'sitemap.xml'), 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n<url><loc>' + URL + '</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n</urlset>\n')
open(os.path.join(OUT, '.nojekyll'), 'w').write('')
print('built index.html (%d KB), %d gallery photos' % (os.path.getsize(os.path.join(OUT, 'index.html')) // 1024, len(tiles)))
