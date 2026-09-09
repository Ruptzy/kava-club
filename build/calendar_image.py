"""Draw a month of club nights as a calendar image, in the site's own colours.

Used by post_schedule.py for the monthly Discord post; run directly to preview:
    python build/calendar_image.py 2026-10 out.png
"""
import calendar, json, os, sys
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont

VOID, PANEL, RULE, RULE2 = (12, 13, 14), (20, 22, 24), (36, 40, 44), (52, 58, 64)
CREAM, INK2, INK3 = (255, 246, 232), (189, 181, 169), (163, 155, 142)
SCARLET = (254, 39, 58)
TYPE_COLOUR = {
    'social': (59, 199, 154), 'league': (196, 26, 43), 'study': (79, 134, 232),
    'adobe': (240, 136, 62), 'tournament': (254, 39, 58), 'lecture': (255, 246, 232),
    'simul': (255, 246, 232), 'special': (167, 139, 250),
}
TYPE_LABEL = {
    'social': 'Social', 'league': 'League', 'study': 'Study', 'adobe': 'Int+',
    'tournament': 'Tournament', 'lecture': 'Lecture', 'simul': 'Simul', 'special': 'Special',
}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December']
ANCHOR = date(2026, 8, 30)
THURSDAYS_FROM = date(2026, 9, 10)

CELL_W, CELL_H, PAD = 168, 124, 44
TITLE_H, HEAD_H, LEGEND_H = 104, 46, 96


def font(size, bold=False):
    names = (['DejaVuSans-Bold.ttf', 'arialbd.ttf', 'Arial Bold.ttf'] if bold
             else ['DejaVuSans.ttf', 'arial.ttf', 'Arial.ttf'])
    roots = ['/usr/share/fonts/truetype/dejavu/', 'C:/Windows/Fonts/', '']
    for r in roots:
        for n in names:
            try:
                return ImageFont.truetype(r + n, size)
            except Exception:
                continue
    return ImageFont.load_default()


def recurring(d):
    out = []
    if d.weekday() == 6:
        out.append('league' if ((d - ANCHOR).days // 7) % 2 == 0 else 'social')
    elif d.weekday() == 1:
        out.append('study')
    elif d.weekday() == 3 and d >= THURSDAYS_FROM:
        out.append('adobe')
    return out


def booked_by_date(root):
    out = {}
    try:
        doc = json.load(open(os.path.join(root, 'events.json'), encoding='utf-8'))
        for e in doc.get('events', []):
            out.setdefault(e['date'], []).append(e)
    except Exception:
        pass
    return out


def draw_month(year, month, root, path):
    first = date(year, month, 1)
    start = first - timedelta(days=(first.weekday() + 1) % 7)   # grid starts on Sunday
    weeks = 6 if (start + timedelta(days=35)).month == month else 5
    W = PAD * 2 + CELL_W * 7
    H = TITLE_H + HEAD_H + CELL_H * weeks + LEGEND_H
    im = Image.new('RGB', (W, H), VOID)
    d = ImageDraw.Draw(im)
    booked = booked_by_date(root)

    f_title, f_dow, f_day, f_chip, f_legend = font(46, True), font(19, True), font(26, True), font(17, True), font(17, True)

    d.text((PAD, 34), '%s %d' % (MONTHS[month - 1].upper(), year), font=f_title, fill=CREAM)
    d.text((W - PAD, 46), 'KAVA SOCIAL CHESS CLUB', font=f_dow, fill=INK3, anchor='ra')
    d.line([(PAD, TITLE_H - 8), (W - PAD, TITLE_H - 8)], fill=CREAM, width=3)

    for i, name in enumerate(['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']):
        d.text((PAD + i * CELL_W + 10, TITLE_H + 14), name, font=f_dow, fill=INK3)

    top = TITLE_H + HEAD_H
    for w in range(weeks):
        for c in range(7):
            day = start + timedelta(days=w * 7 + c)
            x, y = PAD + c * CELL_W, top + w * CELL_H
            here = day.month == month
            d.line([(x, y), (x + CELL_W, y)], fill=RULE if here else PANEL, width=1)
            d.text((x + 10, y + 12), str(day.day), font=f_day, fill=CREAM if here else RULE2)
            if not here:
                continue
            chips = [(t, TYPE_LABEL[t]) for t in recurring(day)]
            for e in booked.get(day.isoformat(), []):
                t = e.get('type', 'special')
                chips.append((t, (e.get('title') or TYPE_LABEL.get(t, 'Event'))))
            cy = y + 50
            for t, label in chips[:2]:
                col = TYPE_COLOUR.get(t, SCARLET)
                text = label if d.textlength(label, font=f_chip) < CELL_W - 34 else label[:14] + '…'
                tw = d.textlength(text, font=f_chip)
                d.rounded_rectangle([x + 10, cy, x + 12 + tw + 12, cy + 28], radius=3, fill=col)
                ink = VOID if t in ('social', 'adobe', 'lecture', 'simul', 'special') else CREAM
                d.text((x + 16, cy + 5), text, font=f_chip, fill=ink)
                cy += 34

    ly = H - LEGEND_H + 24
    d.line([(PAD, ly - 18), (W - PAD, ly - 18)], fill=RULE, width=1)
    lx = PAD
    for t in ['social', 'league', 'study', 'adobe', 'tournament', 'special']:
        d.rounded_rectangle([lx, ly + 3, lx + 16, ly + 19], radius=2, fill=TYPE_COLOUR[t])
        label = {'social': 'Social Sunday', 'league': 'League night', 'study': 'Study · Tue',
                 'adobe': 'Intermediate+ · Thu', 'tournament': 'Tournament', 'special': 'Club battle'}[t]
        d.text((lx + 24, ly + 2), label, font=f_legend, fill=INK2)
        lx += 26 + int(d.textlength(label, font=f_legend)) + 30
    im.save(path, optimize=True)
    return path


if __name__ == '__main__':
    ym = sys.argv[1] if len(sys.argv) > 1 else None
    out = sys.argv[2] if len(sys.argv) > 2 else 'calendar.png'
    if ym:
        y, m = (int(x) for x in ym.split('-'))
    else:
        t = date.today(); y, m = t.year, t.month
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(draw_month(y, m, root, out))
