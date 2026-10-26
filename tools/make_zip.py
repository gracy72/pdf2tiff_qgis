# -*- coding: utf-8 -*-
"""Pakuje wtyczke do pliku ZIP gotowego do wgrania na plugins.qgis.org.

Uwaga: witryna plugins.qgis.org wymaga, aby w archiwum byl KATALOG o nazwie
rownej identyfikatorowi wtyczki (tutaj: pdf2tiff), a w nim metadata.txt.
Same pliki na najwyzszym poziomie sa odrzucane komunikatem
"Cannot find a folder inside the compressed package".

Uruchomienie:  python tools/make_zip.py
"""

import os
import zipfile

#: katalog najwyzszego poziomu w archiwum = identyfikator wtyczki w repo QGIS
FOLDER = 'pdf2tiff'

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
        archive.writestr(FOLDER + '/', '')          # wpis katalogu
        for name in FILES:
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                raise SystemExit('Brak pliku: %s' % path)
            archive.write(path, FOLDER + '/' + name)

    print('zapisano %s (%d bajtow, %d plikow w katalogu %s/)'
          % (out, os.path.getsize(out), len(FILES), FOLDER))


if __name__ == '__main__':
    main()
