# -*- coding: utf-8 -*-
"""Lenny's lines, read from the plain text files in build/lenny/.

The lines live in text files, one per line, so that adding a joke never means touching
code or escaping a quote. Blank lines and lines starting with # are ignored.

    facts.txt     real, checkable chess facts                 -> FACTS
    takes.txt     opinions and maxims, never called "facts"   -> TAKES
    leads.txt     what goes in front of a fact or a take      -> FACT_LEADS, TAKE_LEADS
    intros.txt    how a recap post opens                      -> INTROS
    signoffs.txt  how a recap post ends                       -> SIGNOFFS
    records.txt   his line about the night itself             -> NIGHT, PLAYED, NEWS
    topical.txt   facts used only when the recap mentions it  -> TOPICAL  [(word, fact)]
    tonight.txt   extra lines for the 3pm post                -> TONIGHT_GREETINGS, TONIGHT_SIGNOFFS

pick() walks each pool in a fixed shuffled order, one step per club night, so a line
cannot come round again until every other line in its pool has been used.
"""
import os
import random

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lenny')


def _lines(name):
    out = []
    for raw in open(os.path.join(HERE, name), encoding='utf-8'):
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


FACTS = _lines('facts.txt')
TAKES = _lines('takes.txt')
INTROS = _lines('intros.txt')
SIGNOFFS = _lines('signoffs.txt')
_leads = _sections('leads.txt')
FACT_LEADS, TAKE_LEADS = _leads['fact'], _leads['take']
_rec = _sections('records.txt')
NIGHT, PLAYED, NEWS = _rec['night'], _rec['played'], _rec['news']
TOPICAL = [tuple(x.strip() for x in line.split('|', 1)) for line in _lines('topical.txt')]
_ton = _sections('tonight.txt')
TONIGHT_GREETINGS, TONIGHT_SIGNOFFS = _ton['greeting'], _ton['signoff']

_ORDER = {}


def pick(pool, name, k):
    """The k-th line of a pool, taken in a shuffled order that never changes."""
    key = (name, len(pool))
    if key not in _ORDER:
        order = list(range(len(pool)))
        random.Random('lenny|' + name).shuffle(order)
        _ORDER[key] = order
    return pool[_ORDER[key][k % len(pool)]]


def knowledge(k):
    """A fact or a take with its lead-in. Two facts for every take."""
    if k % 3 == 2:
        return '%s %s' % (pick(TAKE_LEADS, 'take-lead', k), pick(TAKES, 'take', k // 3))
    return '%s %s' % (pick(FACT_LEADS, 'fact-lead', k), pick(FACTS, 'fact', k - k // 3))


def total():
    return (len(FACTS) + len(TAKES) + len(INTROS) + len(SIGNOFFS) + len(FACT_LEADS) + len(TAKE_LEADS) + len(NIGHT)
            + len(PLAYED) + len(NEWS) + len(TOPICAL) + len(TONIGHT_GREETINGS) + len(TONIGHT_SIGNOFFS))


if __name__ == '__main__':
    for label, pool in [('facts', FACTS), ('takes', TAKES), ('intros', INTROS), ('sign-offs', SIGNOFFS),
                        ('fact lead-ins', FACT_LEADS), ('take lead-ins', TAKE_LEADS), ('night lines', NIGHT),
                        ('attendance lines', PLAYED), ('news lines', NEWS), ('topical facts', TOPICAL),
                        ('3pm greetings', TONIGHT_GREETINGS), ('3pm sign-offs', TONIGHT_SIGNOFFS)]:
        print('%4d  %s' % (len(pool), label))
    print('%4d  lines in all' % total())
