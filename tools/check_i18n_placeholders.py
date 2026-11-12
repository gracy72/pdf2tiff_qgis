# -*- coding: utf-8 -*-
"""Porownuje symbole formatu (%(nazwa)s) w tlumaczeniach z tabela angielska.

Dzieki temu literowka w tlumaczeniu (np. %(strona)s zamiast %(page)d) nie
wysypuje komunikatow w czasie pracy wtyczki. Uruchomienie:
    python tools/check_i18n_placeholders.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.stdout.reconfigure(encoding='utf-8')

import i18n  # noqa: E402

PLACEHOLDER = re.compile(r'%\((\w+)\)')

base = i18n.TRANSLATIONS['en']
problems = 0
for code, table in i18n.TRANSLATIONS.items():
    if code == 'en':
        continue
    for key, text in table.items():
        want = set(PLACEHOLDER.findall(base[key]))
        got = set(PLACEHOLDER.findall(text))
        if want != got:
            problems += 1
            print('%s / %s: oczekiwano %s, jest %s'
                  % (code, key, sorted(want), sorted(got)))

print('jezyki:', ', '.join(sorted(i18n.TRANSLATIONS)))
print('problemy:', problems)
