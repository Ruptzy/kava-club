# -*- coding: utf-8 -*-
"""The house photo grade, shared by the home page build and the recap photos, so every photo on
the site reads as one set. Flyers and posters are graphics and are never graded."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decast import decast


def grade(im):
    """The patio's purple-pink cast is taken out where it is strong, then one gentle tone curve for everything."""
    from PIL import ImageEnhance
    hsv = im.copy(); hsv.thumbnail((200, 200)); hsv = hsv.convert('HSV')
    px = list(hsv.getdata())
    magenta = sum(1 for h, sat, v in px if 190 <= h <= 235 and sat > 90 and v > 40) / max(1, len(px))
    if magenta > 0.15:                 # heavy purple: the full correction
        im = decast(im, strength=0.75, magenta_keep=0.35, green_keep=0.6)
    elif magenta > 0.08:               # a tint: a lighter touch
        im = decast(im, strength=0.45, magenta_keep=0.55, green_keep=0.6)
    im = ImageEnhance.Contrast(im).enhance(1.05)
    return ImageEnhance.Color(im).enhance(0.94)
