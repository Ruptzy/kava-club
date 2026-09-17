# -*- coding: utf-8 -*-
"""WebP siblings for every photo, and the <picture> wrapper that offers them.

The .jpg and .png files stay exactly where they were. Every <img> becomes a
<picture> that offers the WebP first and falls back to the original, so a
browser too old for WebP still gets a photo. A source is only ever written
when the .webp is really on disk, because a 404 inside <picture> is not
retried against the <img>.
"""
import os
import re

QUALITY = 76          # from the source pixels, not from the already-compressed JPEG


def emit(im, out_path, lossless=False):
    """Write a .webp beside an image we have just encoded, from the same pixels."""
    w = os.path.splitext(out_path)[0] + '.webp'
    if lossless:
        im.save(w, 'WEBP', lossless=True, method=6)
    else:
        im.save(w, 'WEBP', quality=QUALITY, method=6)
    return w


def convert_dir(root):
    """For photos that arrive already encoded and have no source to hand."""
    from PIL import Image          # only the encoders need Pillow; picturize does not
    made = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            low = f.lower()
            if not low.endswith(('.jpg', '.jpeg', '.png')):
                continue
            if 'favicon' in low:          # only ever reached through <link>, never <img>
                continue
            src = os.path.join(dirpath, f)
            dst = os.path.splitext(src)[0] + '.webp'
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            im = Image.open(src)
            if low.endswith('.png'):
                im.save(dst, 'WEBP', lossless=True, method=6)
            else:
                im.convert('RGB').save(dst, 'WEBP', quality=QUALITY, method=6)
            made += 1
    return made


_IMG = re.compile(r'<img\s([^>]*?)src="(img/[^"]+)\.(jpg|jpeg|png)"([^>]*?)>', re.I)
_PIC = re.compile(r'<picture>.*?</picture>', re.I | re.S)
_SRCSET = re.compile(r'<source\s([^>]*?)srcset="(img/[^"]+)\.(jpg|jpeg|png)"([^>]*?)>', re.I)
_PARK = '@@KSCPIC%d@@'


def picturize(html, out_root):
    """Offer a WebP for every photo. Paths must still be un-prefixed here.

    A <picture> the template already wrote (the hero, which swaps crop by
    viewport width) is widened in place rather than wrapped: a <picture>
    nested inside a <picture> has no direct <img> child, so the outer
    <source> elements stop applying and the desktop crop is lost.
    """
    def has(stem):
        return os.path.exists(os.path.join(out_root, stem + '.webp'))

    def widen(m):
        """Put a WebP twin above each <source>, and one above the <img>."""
        block = m.group(0)

        def source_twin(s):
            pre, stem, post = s.group(1), s.group(2), s.group(4)
            if not has(stem):
                return s.group(0)
            return '<source %ssrcset="%s.webp" type="image/webp"%s>%s' % (pre, stem, post, s.group(0))
        block = _SRCSET.sub(source_twin, block)

        def img_twin(s):
            if not has(s.group(2)):
                return s.group(0)
            return '<source srcset="%s.webp" type="image/webp">%s' % (s.group(2), s.group(0))
        return _IMG.sub(img_twin, block)

    def wrap(m):
        pre, stem, ext, post = m.group(1), m.group(2), m.group(3), m.group(4)
        if not has(stem):
            return m.group(0)
        return ('<picture><source srcset="%s.webp" type="image/webp">'
                '<img %ssrc="%s.%s"%s></picture>' % (stem, pre, stem, ext, post))

    # park the template's own <picture> blocks so the wrapper cannot nest inside them
    kept = []

    def park(m):
        kept.append(widen(m))
        return _PARK % (len(kept) - 1)

    html = _PIC.sub(park, html)
    html = _IMG.sub(wrap, html)
    for i, blk in enumerate(kept):
        html = html.replace(_PARK % i, blk, 1)
    return html
