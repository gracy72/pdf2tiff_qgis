# -*- coding: utf-8 -*-
"""Waliduje paczke ZIP pod katem wymagan repozytorium plugins.qgis.org."""
import configparser
import io
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(ROOT, 'pdf2tiff_qgis.zip')

REQUIRED = ['name', 'description', 'version', 'qgisMinimumVersion', 'author', 'email',
            'about', 'repository', 'tracker', 'homepage', 'category', 'tags',
            'icon', 'experimental', 'deprecated', 'changelog']

OPTIONAL_OK = ['supportsQt6', 'server', 'qgisMaximumVersion']


def main():
    # --- metadata.txt
    with io.open(os.path.join(ROOT, 'metadata.txt'), encoding='utf-8') as handle:
        parser = configparser.ConfigParser()
        parser.optionxform = str           # zachowaj wielkosc liter w kluczach
        parser.read_file(handle)
    meta = dict(parser.items('general'))

    print('=== metadata.txt ===')
    missing = [key for key in REQUIRED if not meta.get(key, '').strip()]
    for key in REQUIRED + OPTIONAL_OK:
        if key in meta:
            value = meta[key].replace('\n', ' ')
            print('  %-20s %s' % (key, (value[:70] + '...') if len(value) > 70 else value))
    print('  BRAKUJACE POLA:', missing or 'brak')

    icon = meta.get('icon', '')
    print('  plik ikony istnieje:', os.path.isfile(os.path.join(ROOT, icon)))
    version = meta.get('version', '')
    changelog = meta.get('changelog', '')
    print('  wersja w changelogu:', version in changelog)

    # --- zip
    print()
    print('=== %s ===' % os.path.basename(ZIP))
    if not os.path.isfile(ZIP):
        print('  BRAK PLIKU ZIP')
        return
    print('  rozmiar: %.1f kB' % (os.path.getsize(ZIP) / 1024.0))
    with zipfile.ZipFile(ZIP) as archive:
        bad = archive.testzip()
        names = archive.namelist()
        for name in sorted(names):
            print('   %8d  %s' % (archive.getinfo(name).file_size, name))
    print('  archiwum uszkodzone:', bad or 'nie')
    print('  metadata.txt na najwyzszym poziomie:', 'metadata.txt' in names)
    print('  __init__.py na najwyzszym poziomie:', '__init__.py' in names)
    print('  brak katalogu nadrzednego:', all('/' not in n or n.startswith('tools/') for n in names))


if __name__ == '__main__':
    main()
