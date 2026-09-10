# -*- coding: utf-8 -*-
"""Attach a picture to one clause of the code of conduct.

    python build/add_clause_art.py 3 "C:/Users/you/Desktop/art.png" "alt text" "texto alternativo"

The clause becomes a full-width feature with its art beside the text. Every
second featured clause is mirrored, and that alternation is recomputed on each
run, so clauses can be illustrated in any order. Re-running on a clause that
already has art replaces the picture.
"""
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONDUCT = os.path.join(HERE, 'conduct.html')
I18N = os.path.join(HERE, 'i18n_es.py')
SRC_ART = os.path.join(HERE, 'src-art')
IMG = os.path.join(ROOT, 'img')

WIDTH = 1200            # displayed near 585px, so this covers 2x screens
VOID = (12, 13, 14)     # the page's own background, so cut-outs blend into it
I18N_ANCHOR = "    ('>Add to Google Calendar<', '>Agregar a Google Calendar<'),"


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def clause_lines(html):
    """The <li> lines of the clause list, in order."""
    start = html.index('<ol class="clauses">')
    end = html.index('</ol>', start)
    out = []
    for i, line in enumerate(html.split('\n')):
        off = sum(len(l) + 1 for l in html.split('\n')[:i])
        if start < off < end and '<li' in line:
            out.append(i)
    return out


def heading(line):
    return re.search(r'<h2 class="d cl">(.*?)</h2>', line).group(1)


def build_image(src, name):
    im = Image.open(src).convert('RGBA')
    os.makedirs(SRC_ART, exist_ok=True)
    keep = im.resize((1600, round(1600 * im.height / im.width)), Image.LANCZOS)
    keep.save(os.path.join(SRC_ART, name + '.webp'), 'WEBP', quality=90, method=6)

    small = im.resize((WIDTH, round(WIDTH * im.height / im.width)), Image.LANCZOS)
    flat = Image.new('RGB', small.size, VOID)
    flat.paste(small, (0, 0), small)
    out = os.path.join(IMG, name + '.jpg')
    flat.save(out, 'JPEG', quality=86, optimize=True, progressive=True)
    return small.height, os.path.getsize(out) // 1024


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    number, src, alt_en, alt_es = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]

    html = open(CONDUCT, encoding='utf-8').read()
    lines = html.split('\n')
    idx = clause_lines(html)
    if not 1 <= number <= len(idx):
        sys.exit('clause %d does not exist (there are %d)' % (number, len(idx)))
    li = idx[number - 1]
    line = lines[li]

    name = 'conduct-%02d-%s' % (number, slug(heading(line)))
    height, kb = build_image(src, name)
    fig = ('<figure class="art"><img src="img/%s.jpg" width="%d" height="%d" alt="%s" '
           'loading="lazy" decoding="async"></figure>' % (name, WIDTH, height, alt_en))

    if '<figure class="art">' in line:
        old_alt = re.search(r'<figure class="art"><img [^>]*alt="([^"]*)"', line).group(1)
        line = re.sub(r'<figure class="art">.*?</figure>', fig, line)
        drop_alt(old_alt)
    else:
        line = line.replace('<li>', '<li class="feature">', 1)
        line = line.replace('<h2 class="d cl">', '<div class="txt"><h2 class="d cl">', 1)
        line = line.replace('</p></li>', '</p></div>' + fig + '</li>', 1)
    lines[li] = line

    # mirror every second illustrated clause
    seen = 0
    for i in idx:
        if 'class="feature' not in lines[i]:
            continue
        seen += 1
        lines[i] = lines[i].replace('class="feature alt"', 'class="feature"')
        if seen % 2 == 0:
            lines[i] = lines[i].replace('class="feature"', 'class="feature alt"', 1)
    open(CONDUCT, 'w', encoding='utf-8').write('\n'.join(lines))

    add_alt(alt_en, alt_es)
    print('clause %d "%s" -> img/%s.jpg (%d KB), %d illustrated' % (
        number, heading(line), name, kb, seen))
    print('now run: python build/build_site.py')


def drop_alt(alt_en):
    i = open(I18N, encoding='utf-8').read()
    line = "    ('alt=\"%s\"'," % alt_en
    if line in i:
        start = i.index(line)
        end = i.index('),\n', start) + len('),\n')
        open(I18N, 'w', encoding='utf-8').write(i[:start] + i[end:])


def add_alt(alt_en, alt_es):
    i = open(I18N, encoding='utf-8').read()
    entry = "    ('alt=\"%s\"', 'alt=\"%s\"'),\n" % (alt_en, alt_es)
    if entry in i:
        return
    i = i.replace(I18N_ANCHOR, entry + I18N_ANCHOR, 1)
    open(I18N, 'w', encoding='utf-8').write(i)
    import ast
    ast.parse(i)


if __name__ == '__main__':
    main()
