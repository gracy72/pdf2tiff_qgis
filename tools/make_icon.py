# -*- coding: utf-8 -*-
"""Generator ikony wtyczki (icon.png 64x64) - czysty Python, bez bibliotek zewnetrznych.

Uruchomienie:  python tools/make_icon.py
"""

import os
import struct
import zlib

SIZE = 64

BG = (0, 0, 0, 0)
RED = (192, 57, 43, 255)
RED_DARK = (142, 40, 30, 255)
BLUE = (41, 128, 185, 255)
BLUE_DARK = (27, 88, 128, 255)
GREY = (70, 70, 70, 255)
WHITE = (255, 255, 255, 255)


class Canvas(object):
    def __init__(self, size):
        self.size = size
        self.pixels = [[BG for _ in range(size)] for _ in range(size)]

    def put(self, x, y, color):
        if 0 <= x < self.size and 0 <= y < self.size:
            self.pixels[y][x] = color

    def rect(self, x0, y0, x1, y1, color, border=None):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, color)
        if border is not None:
            for x in range(x0, x1 + 1):
                self.put(x, y0, border)
                self.put(x, y1, border)
            for y in range(y0, y1 + 1):
                self.put(x0, y, border)
                self.put(x1, y, border)

    def hline(self, x0, x1, y, color):
        for x in range(x0, x1 + 1):
            self.put(x, y, color)

    def vline(self, x, y0, y1, color):
        for y in range(y0, y1 + 1):
            self.put(x, y, color)

    def triangle_right(self, x0, y0, height, color):
        """Trojkat skierowany w prawo (grot strzalki)."""
        half = height // 2
        for i in range(half + 1):
            for y in range(y0 + half - i, y0 + half + i + 1):
                self.put(x0 + i, y, color)

    def png_bytes(self):
        raw = bytearray()
        for row in self.pixels:
            raw.append(0)  # filtr 0
            for pixel in row:
                raw.extend(pixel)

        def chunk(tag, data):
            body = tag + data
            return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

        header = struct.pack('>IIBBBBB', self.size, self.size, 8, 6, 0, 0, 0)
        return (b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', header)
                + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
                + chunk(b'IEND', b''))


def build():
    c = Canvas(SIZE)

    # --- dokument PDF (czerwony, z zagietym rogiem)
    c.rect(3, 8, 25, 52, RED, border=RED_DARK)
    for i, y in enumerate((16, 21, 26, 31, 36, 41)):
        width = 17 if i % 3 else 12
        c.hline(7, 7 + width, y, WHITE)
    # zagięcie rogu
    for i in range(7):
        for j in range(7 - i):
            c.put(25 - i, 8 + j, (250, 250, 250, 255))
    for i in range(7):
        c.put(25 - i, 8 + (6 - i), RED_DARK)

    # --- strzalka
    c.rect(28, 29, 35, 32, GREY)
    c.triangle_right(36, 23, 15, GREY)

    # --- obraz TIFF (niebieski, z siatka)
    c.rect(44, 12, 61, 50, BLUE, border=BLUE_DARK)
    c.hline(46, 59, 24, WHITE)
    c.hline(46, 59, 36, WHITE)
    c.vline(51, 14, 48, WHITE)
    c.vline(56, 14, 48, WHITE)

    return c


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(os.path.dirname(here), 'icon.png')
    data = build().png_bytes()
    with open(out, 'wb') as handle:
        handle.write(data)
    print('zapisano %s (%d bajtow)' % (out, len(data)))


if __name__ == '__main__':
    main()
