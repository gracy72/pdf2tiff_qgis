# -*- coding: utf-8 -*-
"""Sprawdza, czy wszystkie klucze uzywane w kodzie istnieja w tabelach i18n."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.stdout.reconfigure(encoding='utf-8')

src = open(os.path.join(ROOT, 'i18n.py'), encoding='utf-8').read()
env = set(re.findall(r"^        '([a-z0-9_]+)':", src, re.M))

used = set()
for name in ('converter.py', 'dialog.py', 'algorithm.py', 'plugin.py',
             'skrypt_pdf2tiff.py'):
    text = open(os.path.join(ROOT, name), encoding='utf-8').read()
    used.update(re.findall(r"\btr\(\s*'([a-z0-9_]+)'", text))

print('klucze w tabelach  :', len(env))
print('klucze uzyte w kodzie:', len(used))
print('brakujace w tabelach:', sorted(used - env))
print('nieuzywane w kodzie :', sorted(env - used))
