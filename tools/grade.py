# -*- coding: utf-8 -*-
"""The house photo grade, shared by the home page build and the recap photos, so every photo on
the site reads as one set. Flyers and posters are graphics and are never graded."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decast import decast


def grade(im):
    """Kava's lights are pink and purple, and that glow is part of the club, so it stays. Only a strong
    cast gets a light touch so skin still looks like skin; then one gentle tone curve for everything.
    (Harold, 2026-11-22: allow the pink and purple.)"""
    from PIL import ImageEnhance
    hsv = im.copy(); hsv.thumbnail((200, 200)); hsv = hsv.convert('HSV')
    px = list(hsv.getdata())
    magenta = sum(1 for h, sat, v in px if 190 <= h <= 235 and sat > 90 and v > 40) / max(1, len(px))
    if magenta > 0.15:
        im = decast(im, strength=0.3, magenta_keep=0.8, green_keep=0.85)
    im = ImageEnhance.Contrast(im).enhance(1.05)
    return ImageEnhance.Color(im).enhance(0.98)


def sharpen(im):
    """Light, adaptive sharpening for web copies. Only soft photos get a small lift; photos that are
    already sharp are left alone. Kept gentle on purpose: the stronger version (2.2px at 140%) left
    halos and a crunchy "glaze" on every photo (Harold, 2026-11-22)."""
    import numpy as np
    from PIL import ImageFilter
    g = im.convert('L'); g.thumbnail((800, 800))
    soft = float(np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=float).var())
    if soft < 1200:
        return im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=4))
    if soft < 2500:
        return im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=35, threshold=4))
    return im
