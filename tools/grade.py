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
    """Adaptive sharpening for web copies: the softer the photo, the stronger the lift. A threshold
    keeps grain and smooth walls from turning into noise. Out-of-focus shots get crisper, not perfect."""
    import numpy as np
    from PIL import ImageFilter
    g = im.convert('L'); g.thumbnail((800, 800))
    soft = float(np.asarray(g.filter(ImageFilter.FIND_EDGES), dtype=float).var())
    if soft < 1200:
        im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=140, threshold=3))
        return im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=3))
    if soft < 2500:
        return im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=100, threshold=3))
    return im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=3))
