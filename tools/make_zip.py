# -*- coding: utf-8 -*-
"""Pakuje wtyczke do pliku ZIP gotowego do wgrania w Menedzerze wtyczek QGIS.

W archiwum pliki leza na najwyzszym poziomie (metadata.txt, __init__.py, ...),
bo tak wymaga instalator QGIS. Katalogi tools/, .git i __pycache__ sa pomijane.

Uruchomienie:  python tools/make_zip.py
"""

import os
import zipfile

FILES = [
    '__init__.py',
    'metadata.txt',
    'plugin.py',
    'dialog.py',
    'converter.py',
    'algorithm.py',
    'skrypt_pdf2tiff.py',
    'icon.png',
    'README.md',
    'LICENSE',
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    out = os.path.join(root, 'pdf2tiff_qgis.zip')

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                raise SystemExit('Brak pliku: %s' % path)
            archive.write(path, name)

    print('zapisano %s (%d bajtow, %d plikow)' % (out, os.path.getsize(out), len(FILES)))


if __name__ == '__main__':
    main()
