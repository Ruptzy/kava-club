# -*- coding: utf-8 -*-
"""Lenny's lines, read from the plain text files in build/lenny/.

The lines live in text files, one per line, so that adding a joke never means touching
code or escaping a quote. Blank lines and lines starting with # are ignored.

    facts*.txt    real, checkable chess facts                 -> FACTS
    takes*.txt    opinions, banter and maxims, never "facts"  -> TAKES
    leads.txt     what goes in front of a fact or a take      -> FACT_LEADS, TAKE_LEADS
    intros.txt    how a recap post opens                      -> INTROS
    signoffs.txt  how a recap post ends                       -> SIGNOFFS
    records.txt   his line about the night itself             -> NIGHT, PLAYED, NEWS
    tonight.txt   extra lines for the 3pm post                -> TONIGHT_GREETINGS, TONIGHT_SIGNOFFS

Facts and takes are one pool, KNOWLEDGE, walked in a fixed shuffled order by date. Each
day has two slots, one for the 3pm post and one for a recap filed under that date, so the
two posts never share a line and nothing comes round again for len(KNOWLEDGE) / 2 days.
`python build/lenny_bank.py` counts the pools and fails on any line that appears twice.
Adding lines reshuffles the order, so the very next posts may repeat an old line once.
"""
import glob
import os
import random
import re
import sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lenny')


def _lines(name):
    out = []
    for path in sorted(glob.glob(os.path.join(HERE, name))):
        for raw in open(path, encoding='utf-8'):
            line = raw.strip()
            if line and not line.startswith('#'):
                out.append(line)
    return out


def _sections(name):
    out, cur = {}, None
    for line in _lines(name):
        if line.startswith('[') and line.endswith(']'):
            cur = line[1:-1]
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


FACTS = _lines('facts*.txt')
TAKES = _lines('takes*.txt')
KNOWLEDGE = [('fact', x) for x in FACTS] + [('take', x) for x in TAKES]
INTROS = _lines('intros.txt')
SIGNOFFS = _lines('signoffs.txt')
_leads = _sections('leads.txt')
FACT_LEADS, TAKE_LEADS = _leads['fact'], _leads['take']
_rec = _sections('records.txt')
NIGHT, PLAYED, NEWS = _rec['night'], _rec['played'], _rec['news']
_ton = _sections('tonight.txt')
TONIGHT_GREETINGS, TONIGHT_SIGNOFFS = _ton['greeting'], _ton['signoff']

# the two posts that carry a fact or a take, each with its own slot in the day
TONIGHT, RECAP = 0, 1
SLOTS = 2

_ORDER = {}


def pick(pool, name, k):
    """The k-th line of a pool, taken in a shuffled order that never changes."""
    key = (name, len(pool))
    if key not in _ORDER:
        order = list(range(len(pool)))
        random.Random('lenny|' + name).shuffle(order)
        _ORDER[key] = order
    return pool[_ORDER[key][k % len(pool)]]


def knowledge(day, slot):
    """The fact or take for one post, with its lead-in. day is a date, slot TONIGHT or RECAP."""
    k = day.toordinal() * SLOTS + slot
    kind, line = pick(KNOWLEDGE, 'knowledge', k)
    return '%s %s' % (pick(FACT_LEADS if kind == 'fact' else TAKE_LEADS, kind + '-lead', k), line)


def _norm(line):
    return re.sub(r'[^a-z0-9]+', ' ', line.lower()).strip()


def duplicates():
    """Lines that appear more than once across all the pools, ignoring case and punctuation."""
    seen, out = {}, []
    for name, pool in [('knowledge', [x for _, x in KNOWLEDGE]), ('intros', INTROS), ('signoffs', SIGNOFFS),
                       ('fact leads', FACT_LEADS), ('take leads', TAKE_LEADS), ('night', NIGHT),
                       ('played', PLAYED), ('news', NEWS), ('3pm greetings', TONIGHT_GREETINGS),
                       ('3pm signoffs', TONIGHT_SIGNOFFS)]:
        for line in pool:
            key = (name, _norm(line))
            if key in seen:
                out.append('%s: %s' % (name, line))
            seen[key] = True
    return out


def total():
    return (len(KNOWLEDGE) + len(INTROS) + len(SIGNOFFS) + len(FACT_LEADS) + len(TAKE_LEADS) + len(NIGHT)
            + len(PLAYED) + len(NEWS) + len(TONIGHT_GREETINGS) + len(TONIGHT_SIGNOFFS))


if __name__ == '__main__':
    for label, pool in [('facts', FACTS), ('takes', TAKES), ('facts + takes, never repeated', KNOWLEDGE),
                        ('intros', INTROS), ('sign-offs', SIGNOFFS), ('fact lead-ins', FACT_LEADS),
                        ('take lead-ins', TAKE_LEADS), ('night lines', NIGHT), ('attendance lines', PLAYED),
                        ('news lines', NEWS), ('3pm greetings', TONIGHT_GREETINGS), ('3pm sign-offs', TONIGHT_SIGNOFFS)]:
        print('%5d  %s' % (len(pool), label))
    print('%5d  lines in all' % total())
    print('no fact or take repeats for %d days' % (len(KNOWLEDGE) // SLOTS))
    dup = duplicates()
    for d in dup:
        print('DUPLICATE  ' + d)
    sys.exit(1 if dup else 0)
