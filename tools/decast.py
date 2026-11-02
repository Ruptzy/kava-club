# -*- coding: utf-8 -*-
"""Take the purple-pink patio lighting out of a photo: neutralise the colour cast, then calm what is left of the magenta."""
import numpy as np
from PIL import Image, ImageOps

def decast(im, strength=0.5, magenta_keep=0.5, green_keep=0.35):
    a = np.asarray(im.convert('RGB'), dtype=np.float32) / 255.0
    lin = np.power(a, 2.2)
    # grey-world on the mid-tones only: blown lights and black shadows say nothing about the cast
    lum = lin.mean(axis=2)
    mask = (lum > 0.02) & (lum < 0.7)
    means = lin[mask].mean(axis=0)
    gains = (means.mean() / means) ** strength
    lin = np.clip(lin * gains, 0, 1)
    out = np.power(lin, 1 / 2.2)
    # whatever is still magenta or violet: pull it towards grey, so skin and walls stop glowing
    img = Image.fromarray((out * 255).astype(np.uint8), 'RGB').convert('HSV')
    h, s, v = [np.asarray(c, dtype=np.float32) for c in img.split()]
    deg = h * 360 / 255
    w = np.clip(1 - np.abs(deg - 300) / 60, 0, 1)      # 240-360 degrees, strongest at 300
    s = s * (1 - w * (1 - magenta_keep))
    g = np.clip(1 - np.abs(deg - 110) / 60, 0, 1)      # the green the correction pushes shadows and walls into
    s = s * (1 - g * (1 - green_keep))
    img = Image.merge('HSV', [Image.fromarray(x.astype(np.uint8), 'L') for x in (h, s, v)]).convert('RGB')
    return img

if __name__ == '__main__':
    import sys
    U = 'C:/Users/17862/.claude/uploads/e2a9828e-6455-4cc8-97fb-4c197435b234/'
    S = sys.argv[1]
    names = ['1bdde8e1', '402eb45a', '92fe024a', '8fadc8d2', '3e03d1d2']
    sheet = Image.new('RGB', (5 * 340, 2 * 340), '#222')
    for i, n in enumerate(names):
        im = ImageOps.exif_transpose(Image.open(U + n + '-image.jpg')).convert('RGB')
        im.thumbnail((1000, 1000))
        b = im.copy(); b.thumbnail((330, 330)); sheet.paste(b, (i * 340 + 5, 5))
        c = decast(im); c.thumbnail((330, 330)); sheet.paste(c, (i * 340 + 5, 345))
    sheet.save(S + '/decast.jpg', quality=85)
