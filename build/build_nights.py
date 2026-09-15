# -*- coding: utf-8 -*-
"""The night recaps: one page per club night, an archive, an RSS feed, and the sitemap.

Reads nights.json (written by the admin console or by hand) and the shared masthead,
styles and footer from template.html. Needs nothing outside the repo and no image
libraries, so GitHub Actions can run it whenever nights.json changes:

    python build/build_nights.py

build_site.py calls main() too, so a local build stays complete.
"""
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import i18n_es  # noqa: E402

URL = 'https://kavasocialchessclub.com/'
DISCORD = 'https://discord.gg/sYCb7RnTgZ'
LADDER = 'https://ladder.kavasocialchessclub.com/'
GOATCOUNTER = 'kavasocialchessclub'
COUNTER = ('<script data-goatcounter="https://%s.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>'
           % GOATCOUNTER) if GOATCOUNTER else ''
ARROW = ('<i class="disc"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg></i>')

# the static pages, for the sitemap: english slug -> spanish slug
PAGES = {'code-of-conduct': 'es/codigo-de-conducta', 'beginners': 'es/principiantes',
         'lessons': 'es/clases', 'calendar': 'es/calendario', 'nights': 'es/noches'}

TYPES = {'league': ('League night', 'Noche de liga'), 'social': ('Social Sunday', 'Domingo social'),
         'study': ('Study night', 'Noche de estudio'), 'adobe': ('Intermediate+ study night', 'Noche de estudio intermedio+'),
         'special': ('Special event', 'Evento especial'), 'tournament': ('Tournament', 'Torneo')}
VENUE = {'adobe': ('Adobe Kava, 1302 13th Ave W, Bradenton', 'Adobe Kava, 1302 13th Ave W, Bradenton')}
VENUE_DEFAULT = ('Kava Social Club, 540 13th St W, Bradenton', 'Kava Social Club, 540 13th St W, Bradenton')
KEYWORDS = ["chess club Bradenton", "chess in Bradenton", "chess near me", "chess club near me", "Bradenton chess club",
            "Sarasota chess", "Manatee County chess", "where to play chess in Bradenton", "adult chess club Florida",
            "casual chess Bradenton", "chess league Bradenton", "Kava Social Club chess", "chess night Bradenton"]
KEYWORDS_ES = ["club de ajedrez en Bradenton", "ajedrez en Bradenton", "ajedrez cerca de mí", "club de ajedrez cerca de mí",
               "ajedrez Sarasota", "ajedrez condado de Manatee", "dónde jugar ajedrez en Bradenton", "club de ajedrez Florida",
               "noche de ajedrez Bradenton", "liga de ajedrez Bradenton"]


def about_block(es, nights=None):
    """The standing paragraph under every recap: what the club is, where it is, who it is for."""
    no = max([n.get('no', 0) for n in nights] or [0]) if nights else 0
    if es:
        return ('<section class="about"><h2 class="d sub">Sobre el club</h2>'
                '<p class="body"><a href="/es/">Kava Social Chess Club</a> es un club de ajedrez en Bradenton, Florida, que se reúne los domingos y martes '
                'de 8PM a medianoche en el patio trasero de Kava Social Club, 540 13th St W, en el centro de Bradenton. Es el club de ajedrez '
                'más activo del condado de Manatee y queda a media hora de Sarasota, Lakewood Ranch, Palmetto y Ellenton. Todos los niveles: '
                'principiantes, jugadores casuales, gente que no ha jugado desde la escuela y jugadores con rating de US Chess. '
                'Liga interna cada dos domingos, noche de estudio los martes, torneos con rating de US Chess varias veces al año. '
                'Mayores de 21, sin cuotas, sin alcohol, en inglés y español. Desde 2021%s.</p>'
                '<p class="body">Si buscas dónde jugar ajedrez en Bradenton o un club de ajedrez cerca de ti en la costa del golfo de Florida, '
                '<a href="/es/principiantes/">esta es tu primera noche</a>.</p></section>'
                % ((', %d noches de club registradas' % no) if no else ''))
    return ('<section class="about"><h2 class="d sub">About the club</h2>'
            '<p class="body"><a href="/">Kava Social Chess Club</a> is a chess club in Bradenton, Florida, meeting Sundays and Tuesdays from 8PM to '
            'midnight on the back patio at Kava Social Club, 540 13th St W in downtown Bradenton. It is the most active chess club in Manatee '
            'County and half an hour from Sarasota, Lakewood Ranch, Palmetto and Ellenton. Every level plays here: beginners, casual players, '
            'adults who have not played since school, and US Chess rated tournament players. An in-house chess league every other Sunday, '
            'study night on Tuesdays, US Chess rated tournaments a few times a year. 21+, no dues, alcohol-free, in English and Spanish. '
            'Established 2021%s.</p>'
            '<p class="body">If you are looking for where to play chess in Bradenton, or a chess club near you on Florida\'s Gulf Coast, '
            '<a href="/beginners/">this is your first night</a>.</p></section>'
            % ((', %d club nights on record' % no) if no else ''))


MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
DAYS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

TEMPLATE = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
TEMPLATE = TEMPLATE.replace('{{COUNTER}}', COUNTER).replace('{{LOGO}}', 'img/logo.png')
STYLE = TEMPLATE[:TEMPLATE.index('</style>') + len('</style>')]
MAST = TEMPLATE[TEMPLATE.index('<!-- ============ MASTHEAD ============ -->'):TEMPLATE.index('<!-- ============ HERO ============ -->')]
FOOT = TEMPLATE[TEMPLATE.index('<!-- ============ FOOTER ============ -->'):]


def esc(t):
    return html.escape(str(t), quote=True)


def loc(n, key, es):
    """A night's field in the page language, falling back to English."""
    return (n.get(key + '_es') if es else None) or n.get(key) or ''


def parse(d):
    return date(*[int(x) for x in d.split('-')])


def long_date(d, es):
    dt = parse(d)
    if es:
        return '%s %d de %s de %d' % (DAYS_ES[dt.weekday()], dt.day, MONTHS_ES[dt.month - 1], dt.year)
    return dt.strftime('%A, %d %B %Y').replace(' 0', ' ')


def short_date(d, es):
    dt = parse(d)
    if es:
        return '%d %s %d' % (dt.day, MONTHS_ES[dt.month - 1][:3], dt.year)
    return dt.strftime('%d %b %Y').lstrip('0')


def night_type(n, es):
    return TYPES.get(n.get('type', ''), (n.get('type', ''), n.get('type', '')))[1 if es else 0]


def venue(n, es):
    return VENUE.get(n.get('type', ''), VENUE_DEFAULT)[1 if es else 0]


def slug(n, es):
    return ('es/noches/' if es else 'nights/') + n['date']


# ---------------- page assembly ----------------

def chrome(body, es, depth, slug_en, slug_es, home):
    """Masthead + body + footer, with links and asset paths corrected for this page's depth."""
    body = MAST + body + FOOT
    if es:
        body = i18n_es.localize(body)
        for en, es_slug in PAGES.items():
            body = body.replace('href="/%s/"' % en, 'href="/%s/"' % es_slug)
    switch = '<a class="on" href="/">EN</a><a href="/es/">ES</a>'
    body = body.replace(switch, ('<a href="/%s/">EN</a><a class="on" href="/%s/">ES</a>' if es
                                 else '<a class="on" href="/%s/">EN</a><a href="/%s/">ES</a>') % (slug_en, slug_es))
    body = re.sub(r'href="#([a-z0-9]+)"', lambda m: 'href="%s#%s"' % (home, m.group(1)), body)
    body = body.replace('href="%s#events"' % home, 'href="/%s/"' % ('es/calendario' if es else 'calendar'))
    body = re.sub(r'(src|srcset|href|poster)="(img/|media/)', lambda m: '%s="%s%s' % (m.group(1), depth, m.group(2)), body)
    body = body.replace('url(img/', 'url(%simg/' % depth)
    return body


def head(lang, title, desc, page_url, slug_en, slug_es, depth, image, ld):
    q = lambda t: t.replace('"', '&quot;')
    return ('<!doctype html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n' % lang +
            '<title>' + esc(title) + '</title>\n<meta name="description" content="' + q(desc) + '">\n'
            '<link rel="canonical" href="' + page_url + '">\n'
            '<link rel="alternate" hreflang="en" href="' + URL + slug_en + '/">\n'
            '<link rel="alternate" hreflang="es" href="' + URL + slug_es + '/">\n'
            '<link rel="alternate" hreflang="x-default" href="' + URL + slug_en + '/">\n'
            '<link rel="alternate" type="application/rss+xml" title="Kava Social Chess Club — club nights" href="' + URL + 'nights.xml">\n'
            '<link rel="icon" href="/favicon.ico" sizes="any">\n'
            '<link rel="icon" href="' + depth + 'img/favicon-v4-32.png" sizes="32x32" type="image/png">\n'
            '<link rel="icon" href="' + depth + 'img/favicon-v4-192.png" sizes="192x192" type="image/png">\n'
            '<link rel="apple-touch-icon" href="' + depth + 'img/favicon-v4-180.png">\n'
            '<meta property="og:site_name" content="Kava Social Chess Club">\n<meta property="og:type" content="article">\n'
            '<meta property="og:title" content="' + q(title) + '">\n<meta property="og:description" content="' + q(desc) + '">\n'
            '<meta property="og:url" content="' + page_url + '">\n<meta property="og:image" content="' + URL + image + '">\n'
            '<meta name="twitter:card" content="summary_large_image">\n<meta name="theme-color" content="#0C0D0E">\n'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>\n' +
            re.sub(r'^<title>[^<]*</title>\n', '', STYLE) + '\n</head>\n<body>')


def write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(doc)
    return os.path.getsize(path) // 1024


# ---------------- one night ----------------

def standings_html(n, es):
    out = []
    for b in n.get('standings') or []:
        rows = b.get('rows') or []
        # shared places: equal points share a rank
        ranks, last_pts, rank = [], None, 0
        for i, r in enumerate(rows):
            if r.get('pts') != last_pts:
                rank = i + 1; last_pts = r.get('pts')
            ranks.append(rank)
        li = []
        for r, rk in zip(rows, ranks):
            medal = ' m%d' % rk if rk <= 3 else ''
            note = ((' <span class="nt">(%s)</span>' % esc(('se fue antes' if es and r.get('note') == 'left early' else r.get('note'))))
                    if r.get('note') else '')
            pts = r.get('pts', 0)
            pts = ('%g' % pts) if isinstance(pts, (int, float)) else esc(pts)
            li.append('<li><span class="rk%s">%d</span><span class="nm">%s%s</span><span class="pt">%s</span><span class="rc">%s</span></li>'
                      % (medal, rk, esc(r.get('name', '')), note, pts, esc(r.get('rec', ''))))
        out.append('<div class="bracket"><div class="m">%s</div><ol>%s</ol></div>' % (esc(b.get('bracket_es') if es else b.get('bracket', '')) or esc(b.get('bracket', '')), ''.join(li)))
    return ''.join(out)


def night_body(n, es, prev_n, next_n):
    t = night_type(n, es)
    title = loc(n, 'title', es) or t
    facts = []
    if n.get('played'):
        facts.append('<div><div class="d v">%d</div><div class="m">%s</div></div>' % (n['played'], 'jugadores' if es else 'players'))
    if n.get('rounds'):
        facts.append('<div><div class="d v">%d</div><div class="m">%s</div></div>' % (n['rounds'], 'rondas' if es else 'rounds'))
    if n.get('standings'):
        facts.append('<div><div class="d v">%d</div><div class="m">%s</div></div>' % (len(n['standings']), 'grupos' if es else 'brackets'))
    if n.get('season'):
        facts.append('<div><div class="d v">%d</div><div class="m">%s</div></div>' % (n['season'], 'temporada' if es else 'season'))
    line = loc(n, 'line', es)
    quote = ('<blockquote class="nline"><p>&ldquo;%s&rdquo;</p><div class="m"><b>Harold Gonzalez</b> &middot; <span>%s</span></div></blockquote>'
             % (esc(line), 'Director del club' if es else 'Club director')) if line else ''
    commentary = loc(n, 'commentary', es)
    comm = ''.join('<p class="body">%s</p>' % esc(p.strip()) for p in commentary.split('\n') if p.strip())
    photo = ('<figure class="nphoto"><img src="%s" alt="%s" width="1600" height="1600" decoding="async" fetchpriority="high"></figure>'
             % (esc(n['photo']), esc(loc(n, 'photo_alt', es)))) if n.get('photo') else ''
    standings = standings_html(n, es)
    st_block = ('<h2 class="d sub">%s</h2><div class="nstand">%s</div><p class="cap">%s</p>'
                % ('Resultados de la noche' if es else 'The night\'s standings', standings,
                   ('Ratings internos de la liga del club, solo cuentan aquí. W-D-L = victorias-tablas-derrotas.' if es
                    else 'In-house club league ratings; they only count here. W-D-L = wins-draws-losses.'))) if standings else ''
    nav = ''
    if prev_n or next_n:
        p = ('<a class="btn btn-s" href="/%s/">&larr; %s</a>' % (slug(prev_n, es), esc(short_date(prev_n['date'], es)))) if prev_n else '<span></span>'
        x = ('<a class="btn btn-s" href="/%s/">%s &rarr;</a>' % (slug(next_n, es), esc(short_date(next_n['date'], es)))) if next_n else '<span></span>'
        nav = '<div class="nnav">%s%s</div>' % (p, x)
    home = '/es/' if es else '/'
    return ('<main class="wrap page night">'
            '<div class="phead"><div class="m lbl"><a href="/%s/">%s</a> &middot; %s %d &middot; %s</div>'
            '<h1 class="d">%s</h1>'
            '<p class="dateline m">%s &middot; %s</p></div>'
            '<div class="ngrid">%s<div class="ntext">'
            '<div class="nfacts">%s</div>%s%s</div></div>'
            '%s'
            '<div class="pfoot"><p class="body">%s</p>'
            '<div class="cta"><a class="btn btn-p" href="%s#night">%s%s</a>'
            '<a class="btn btn-s" href="/%s/">%s%s</a>'
            '<a class="btn btn-s" href="%s" target="_blank" rel="noopener">%s%s</a></div>%s</div>'
            '</main>') % (
        'es/noches' if es else 'nights', 'Noches de club' if es else 'Club nights', 'Noche' if es else 'Night', n.get('no', 0), esc(t),
        esc(title),
        esc(long_date(n['date'], es)), esc(venue(n, es)),
        photo, ''.join(facts), quote, comm,
        st_block,
        ('Cada domingo y martes a las 8. Di que es tu primera noche.' if es else 'Every Sunday and Tuesday at eight. Say it\'s your first night.'),
        home, 'Tu primera noche' if es else 'Your first night', ARROW,
        'es/calendario' if es else 'calendar', 'Ver el calendario' if es else 'See the calendar', ARROW,
        LADDER, 'Tabla de la liga' if es else 'League standings', ARROW, nav)


def night_ld(n, es):
    page_url = URL + slug(n, es) + '/'
    title = loc(n, 'title', es) or night_type(n, es)
    desc = (loc(n, 'commentary', es) or loc(n, 'line', es) or title)[:300]
    dt = parse(n['date'])
    start_h, end_h = (19, 23) if n.get('type') == 'adobe' else (20, 23)
    art = {"@type": "Article", "@id": page_url + "#article", "headline": title, "datePublished": n['date'] + 'T23:59:00-04:00',
           "dateModified": n.get('updated', n['date']) + 'T23:59:00-04:00', "inLanguage": 'es' if es else 'en',
           "description": desc, "url": page_url, "mainEntityOfPage": page_url,
           "author": {"@type": "Person", "name": "Harold Gonzalez", "jobTitle": "Club director"},
           "keywords": ', '.join(KEYWORDS_ES if es else KEYWORDS), "articleSection": 'Noches de club' if es else 'Club nights',
           "about": {"@type": "Place", "name": "Kava Social Club", "address": "540 13th St W, Bradenton, FL 34205"},
           "contentLocation": {"@type": "City", "name": "Bradenton", "containedInPlace": {"@type": "State", "name": "Florida"}},
           "publisher": {"@id": URL + "#club"}, "isPartOf": {"@type": "WebSite", "@id": URL + "#site"}}
    if n.get('photo'):
        art["image"] = URL + n['photo']
    ev = {"@type": "Event", "name": "Kava Social Chess Club — " + title, "startDate": "%sT%02d:00:00-04:00" % (n['date'], start_h),
          "endDate": "%sT%02d:59:00-04:00" % (n['date'], end_h), "eventStatus": "https://schema.org/EventScheduled",
          "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "description": desc, "url": page_url,
          "location": {"@type": "Place", "name": "Adobe Kava" if n.get('type') == 'adobe' else "Kava Social Club",
                       "address": "1302 13th Ave W, Bradenton, FL 34205" if n.get('type') == 'adobe' else "540 13th St W, Bradenton, FL 34205"},
          "organizer": {"@id": URL + "#club"}, "typicalAgeRange": "21-",
          "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}
    if n.get('photo'):
        ev["image"] = URL + n['photo']
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Kava Social Chess Club", "item": URL + ('es/' if es else '')},
        {"@type": "ListItem", "position": 2, "name": 'Noches de club' if es else 'Club nights', "item": URL + ('es/noches/' if es else 'nights/')},
        {"@type": "ListItem", "position": 3, "name": title, "item": page_url}]}
    return {"@context": "https://schema.org", "@graph": [art, ev, crumbs]}


def build_night(n, es, prev_n, next_n):
    s_en, s_es = slug(n, False), slug(n, True)
    depth = '../../../' if es else '../../'
    page_url = URL + (s_es if es else s_en) + '/'
    title_txt = loc(n, 'title', es) or night_type(n, es)
    title = ('%s — %s — Kava Social Chess Club, club de ajedrez en Bradenton' if es else '%s — %s — Kava Social Chess Club, chess club in Bradenton FL') % (title_txt, short_date(n['date'], es))
    lead = ('%s en Kava Social Chess Club, club de ajedrez en Bradenton, Florida: ' if es else '%s at Kava Social Chess Club, a chess club in Bradenton, Florida: ') % night_type(n, es)
    desc = lead + (loc(n, 'commentary', es) or loc(n, 'line', es) or title_txt)
    desc = desc[:157] + '…' if len(desc) > 160 else desc
    body = chrome(night_body(n, es, prev_n, next_n).replace('</main>', about_block(es, ALL) + '</main>'), es, depth, s_en, s_es, '/es/' if es else '/')
    doc = head('es' if es else 'en', title, desc, page_url, s_en, s_es, depth, n.get('photo', 'img/hero-wide.jpg'), night_ld(n, es)) + body + '\n</body>\n</html>\n'
    return write(os.path.join(OUT, *(s_es if es else s_en).split('/'), 'index.html'), doc)


# ---------------- the archive ----------------

def archive_body(nights, es):
    cards = []
    for n in nights:
        t = night_type(n, es)
        title = loc(n, 'title', es) or t
        line = loc(n, 'line', es) or loc(n, 'commentary', es)
        if len(line) > 180:
            line = line[:177].rsplit(' ', 1)[0] + '…'
        img = ('<img src="%s" alt="" loading="lazy" decoding="async">' % esc(n['photo'])) if n.get('photo') else '<div class="noimg"></div>'
        meta = ' &middot; '.join(x for x in [esc(t), ('%d %s' % (n['played'], 'jugadores' if es else 'players')) if n.get('played') else '',
                                              ('%d %s' % (n['rounds'], 'rondas' if es else 'rounds')) if n.get('rounds') else ''] if x)
        cards.append('<a class="ncard" href="/%s/">%s<div class="nc"><div class="m">%s %d &middot; %s</div><h2 class="d">%s</h2>'
                     '<div class="m nmeta">%s</div><p class="body">%s</p></div></a>'
                     % (slug(n, es), img, 'Noche' if es else 'Night', n.get('no', 0), esc(long_date(n['date'], es)), esc(title), meta, esc(line)))
    return ('<main class="wrap page nights"><div class="phead"><div class="m lbl">%s</div><h1 class="d">%s</h1>'
            '<p class="body lead">%s</p></div>'
            '<div class="history"><div><div class="d v">2021</div><div class="m">%s</div></div><div><div class="d v">%d</div><div class="m">%s</div></div>'
            '<div><div class="d v">2,800+</div><div class="m">%s</div></div><div><div class="d v">10</div><div class="m">%s</div></div></div>'
            '<div class="nlist">%s</div>'
            '<div class="pfoot"><p class="body">%s</p><div class="cta">'
            '<a class="btn btn-p" href="%s#night">%s%s</a><a class="btn btn-s" href="/nights.xml">%s%s</a></div></div></main>') % (
        'Noches de club' if es else 'Club nights',
        'Cada noche de ajedrez en Bradenton, registrada' if es else 'Every chess night in Bradenton, on the record',
        ('Una foto, los números y una línea de cada noche del club de ajedrez de Bradenton, en Kava Social. Las más recientes primero.' if es
         else 'One photo, the numbers and a line from every night of Bradenton\'s chess club, at Kava Social. Newest first.'),
        'fundado' if es else 'established', max([n.get('no', 0) for n in nights] or [0]), 'noches de club' if es else 'club nights',
        'partidas registradas' if es else 'games recorded', 'temporadas de liga' if es else 'league seasons',
        ''.join(cards),
        ('Las noches siguen cada domingo y martes a las 8.' if es else 'The nights carry on every Sunday and Tuesday at eight.'),
        '/es/' if es else '/', 'Tu primera noche' if es else 'Your first night', ARROW, 'RSS', ARROW)


def build_archive(nights, es):
    s_en, s_es = 'nights', 'es/noches'
    depth = '../../' if es else '../'
    page_url = URL + (s_es if es else s_en) + '/'
    title = ('Noches de club — historia del club de ajedrez de Bradenton — Kava Social Chess Club' if es else 'Club nights — the history of Bradenton\'s chess club — Kava Social Chess Club')
    desc = ('Cada noche de ajedrez en Bradenton, Florida, desde 2021: una foto, los resultados de la liga y una línea sobre cómo estuvo. El club de ajedrez de Kava Social, domingos y martes, todos los niveles, cerca de Sarasota.' if es
            else 'Every chess night in Bradenton, Florida since 2021: a photo, the league results and a line on how it went. Kava Social Chess Club, Sundays and Tuesdays, every level, near Sarasota.')
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": title, "url": page_url, "description": desc, "inLanguage": 'es' if es else 'en',
         "isPartOf": {"@type": "WebSite", "@id": URL + "#site"}, "publisher": {"@id": URL + "#club"}, "keywords": ', '.join(KEYWORDS_ES if es else KEYWORDS),
         "hasPart": [{"@type": "Article", "headline": loc(n, 'title', es) or night_type(n, es), "url": URL + slug(n, es) + '/',
                      "datePublished": n['date']} for n in nights[:20]]}]}
    body = chrome(archive_body(nights, es).replace('</main>', about_block(es, nights) + '</main>'), es, depth, s_en, s_es, '/es/' if es else '/')
    doc = head('es' if es else 'en', title, desc, page_url, s_en, s_es, depth, nights[0]['photo'] if nights and nights[0].get('photo') else 'img/hero-wide.jpg', ld) + body + '\n</body>\n</html>\n'
    return write(os.path.join(OUT, *(s_es if es else s_en).split('/'), 'index.html'), doc)


# ---------------- feed + sitemap ----------------

def rss(nights):
    items = []
    for n in nights[:30]:
        title = loc(n, 'title', False) or night_type(n, False)
        desc = loc(n, 'commentary', False) or loc(n, 'line', False) or title
        pub = datetime(*[int(x) for x in n['date'].split('-')], 23, 59).strftime('%a, %d %b %Y %H:%M:%S -0400')
        link = URL + slug(n, False) + '/'
        enc = ('<enclosure url="%s" type="image/jpeg" length="%d"/>' % (URL + n['photo'], os.path.getsize(os.path.join(OUT, n['photo'])))
               if n.get('photo') and os.path.exists(os.path.join(OUT, n['photo'])) else '')
        items.append('<item><title>%s — %s</title><link>%s</link><guid isPermaLink="true">%s</guid><pubDate>%s</pubDate>'
                     '<description>%s</description>%s</item>' % (esc(title), esc(short_date(n['date'], False)), link, link, pub, esc(desc), enc))
    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           '<title>Kava Social Chess Club — club nights</title><link>%snights/</link>'
           '<description>One photo, the numbers and a line from every club night in Bradenton.</description><language>en-us</language>'
           '<atom:link href="%snights.xml" rel="self" type="application/rss+xml"/>%s</channel></rss>\n' % (URL, URL, ''.join(items)))
    open(os.path.join(OUT, 'nights.xml'), 'w', encoding='utf-8').write(doc)


def sitemap(nights):
    def url(loc, en, es, freq, pri, lastmod=None):
        return ('<url><loc>' + loc + '</loc>' + ('<lastmod>' + lastmod + '</lastmod>' if lastmod else '') +
                '<xhtml:link rel="alternate" hreflang="en" href="' + en + '"/><xhtml:link rel="alternate" hreflang="es" href="' + es + '"/>'
                '<changefreq>' + freq + '</changefreq><priority>' + pri + '</priority></url>\n')
    today = date.today().isoformat()
    rows = [url(URL, URL, URL + 'es/', 'weekly', '1.0', today), url(URL + 'es/', URL, URL + 'es/', 'weekly', '0.9', today)]
    for en, es in PAGES.items():
        freq, pri = {'code-of-conduct': ('yearly', '0.5'), 'calendar': ('weekly', '0.9'), 'nights': ('weekly', '0.9')}.get(en, ('monthly', '0.8'))
        rows.append(url(URL + en + '/', URL + en + '/', URL + es + '/', freq, pri, today if en in ('calendar', 'nights') else None))
        rows.append(url(URL + es + '/', URL + en + '/', URL + es + '/', freq, '%.1f' % (float(pri) - 0.1), today if en in ('calendar', 'nights') else None))
    for n in nights:
        en, es = URL + slug(n, False) + '/', URL + slug(n, True) + '/'
        rows.append(url(en, en, es, 'yearly', '0.6', n.get('updated', n['date'])))
        rows.append(url(es, en, es, 'yearly', '0.5', n.get('updated', n['date'])))
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + ''.join(rows) + '</urlset>\n')


ALL = []


def main():
    global ALL
    path = os.path.join(OUT, 'nights.json')
    nights = json.load(open(path, encoding='utf-8')).get('nights', []) if os.path.exists(path) else []
    nights = sorted(nights, key=lambda n: n['date'], reverse=True)
    ALL = nights
    sizes = []
    for i, n in enumerate(nights):
        newer = nights[i - 1] if i > 0 else None
        older = nights[i + 1] if i + 1 < len(nights) else None
        sizes.append((build_night(n, False, older, newer), build_night(n, True, older, newer)))
    build_archive(nights, False); build_archive(nights, True)
    rss(nights); sitemap(nights)
    print('nights: %d recaps (%s KB), archive, nights.xml, sitemap.xml' % (len(nights), '/'.join('%d' % a for a, b in sizes) or '0'))


if __name__ == '__main__':
    main()
