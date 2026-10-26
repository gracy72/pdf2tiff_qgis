# -*- coding: utf-8 -*-
"""
Konwerter PDF -> TIFF (bezstratny, GDAL) - samodzielny skrypt QGIS.
==============================================================================

Ten plik wystarczy sam - nie wymaga instalowania wtyczki.
Robi dokladnie to samo co program Laz_PDF_tiff (Lazarus / Free Pascal).

DWA SPOSOBY UZYCIA
------------------
1) Panel przetwarzania (Processing):
   Panel przetwarzania -> Skrypty -> Dodaj skrypt z pliku... -> skrypt_pdf2tiff.py
   Potem: Skrypty -> Konwersja PDF -> "Konwertuj PDF do TIFF (bezstratnie)".
   Skrypt działa tez w modelach i w qgis_process.

2) Konsola Pythona w QGIS:
   Wtyczki -> Konsola Pythona, potem np.:

       import sys
       sys.path.append(r"C:\sciezka\do\katalogu")
       from skrypt_pdf2tiff import konwertuj_pdf_do_tiff
       konwertuj_pdf_do_tiff(r"D:\PZT", dpi=200, podkatalogi=True)

WYWOLYWANA KOMENDA (identyczna jak w wersji Lazarus)
----------------------------------------------------
  gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
      -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
      "wejscie.pdf" "wyjscie.tif"

Dla PDF rastrowych (np. PZT z CAD) 200 DPI = natywna rozdzielczosc (1:1).
Kompresja DEFLATE jest bezstratna, wiec jakosc nie jest tracona.
"""

import glob
import os
import re
import shutil
import subprocess

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterBoolean,
    QgsProcessingParameterFile, QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
)

# ----------------------------------------------------------------------
#  Stale i pomocnicze
# ----------------------------------------------------------------------
GDAL_CANDIDATES = [
    r'C:\QGIS\bin\gdal_translate.exe',
    r'C:\OSGeo4W\bin\gdal_translate.exe',
    r'C:\OSGeo4W64\bin\gdal_translate.exe',
    r'C:\Program Files\OSGeo4W\bin\gdal_translate.exe',
    r'C:\Program Files\QGIS 3.40.0\bin\gdal_translate.exe',
]

GDAL_GLOBS = [
    r'C:\Program Files\QGIS*\bin\gdal_translate.exe',
    r'C:\QGIS*\bin\gdal_translate.exe',
    r'C:\OSGeo4W*\bin\gdal_translate.exe',
    r'C:\Program Files\OSGeo4W*\bin\gdal_translate.exe',
]

PROGRESS_RE = re.compile(r'(\d{1,3})\s*\.\.\.')
SIZE_RE = re.compile(r'size is\s+(\d+)\s*,\s*(\d+)')

CREATE_NO_WINDOW = 0x08000000

try:
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Integer
except AttributeError:                              # QGIS 4 / PyQt6
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Type.Integer

try:
    _FILE_FOLDER = QgsProcessingParameterFile.Folder
    _FILE_FILE = QgsProcessingParameterFile.File
except AttributeError:                              # QGIS 4 / PyQt6
    _FILE_FOLDER = QgsProcessingParameterFile.Behavior.Folder
    _FILE_FILE = QgsProcessingParameterFile.Behavior.File


def detect_gdal_translate():
    """Zwraca sciezke do gdal_translate (albo sama nazwe programu jako fallback)."""
    candidates = []

    found = shutil.which('gdal_translate')
    if found:
        candidates.append(found)

    try:
        from qgis.core import QgsApplication
        prefix = QgsApplication.prefixPath()
        candidates.append(os.path.join(prefix, 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(prefix, '..', '..', 'bin', 'gdal_translate.exe'))
    except Exception:
        pass

    candidates.extend(GDAL_CANDIDATES)

    for path in candidates:
        try:
            if path and os.path.isfile(path):
                return os.path.normpath(path)
        except OSError:
            continue

    for pattern in GDAL_GLOBS:
        hits = sorted(glob.glob(pattern), reverse=True)
        if hits:
            return os.path.normpath(hits[0])

    return candidates[-1] if candidates else 'gdal_translate.exe'


def lista_pdf(katalog, podkatalogi=False):
    """Posortowana lista plikow *.pdf w katalogu (opcjonalnie z podkatalogami)."""
    result = []
    if podkatalogi:
        for root, dirs, files in os.walk(katalog):
            dirs.sort(key=str.lower)
            for name in files:
                if name.lower().endswith('.pdf'):
                    result.append(os.path.join(root, name))
    else:
        try:
            names = os.listdir(katalog)
        except OSError:
            return []
        for name in names:
            path = os.path.join(katalog, name)
            if os.path.isfile(path) and name.lower().endswith('.pdf'):
                result.append(path)

    result.sort(key=lambda p: (os.path.dirname(p).lower(), os.path.basename(p).lower()))
    return result


def sciezka_docelowa(src, katalog_wejsciowy, katalog_docelowy, podkatalogi=False):
    """Zwraca (sciezka_tif, katalog_docelowy_pliku)."""
    try:
        rel = os.path.relpath(src, katalog_wejsciowy)
    except ValueError:                              # inny dysk
        rel = os.path.basename(src)

    if os.path.isabs(rel) or rel.startswith('..') or ':' in rel:
        rel = os.path.basename(src)

    sub = os.path.dirname(rel)
    if podkatalogi and sub:
        dst_dir = os.path.join(katalog_docelowy, sub)
    else:
        dst_dir = katalog_docelowy

    name = os.path.splitext(os.path.basename(src))[0] + '.tif'
    return os.path.join(dst_dir, name), dst_dir


def argumenty_gdal(dpi, src, dst):
    """Argumenty gdal_translate - dokladnie jak w programie Laz_PDF_tiff."""
    return [
        '--config', 'GDAL_PDF_DPI', str(int(dpi)),
        '-of', 'GTiff',
        '-co', 'COMPRESS=DEFLATE',
        '-co', 'PREDICTOR=2',
        '-co', 'TILED=YES',
        '-co', 'BIGTIFF=IF_SAFER',
        src, dst,
    ]


def parsuj_postep(tekst, ostatni=-1):
    """Wyciaga procenty z tekstu postepu GDAL, np. "0...10...20...100"."""
    best = ostatni
    for match in PROGRESS_RE.finditer(tekst or ''):
        value = int(match.group(1))
        if 0 <= value <= 100 and value > best:
            best = value
    return best


def rozmiar_z_tekstu(tekst):
    """Wyciaga "W, H" z komunikatu "Input file size is W, H"."""
    match = SIZE_RE.search(tekst or '')
    if match:
        return '%s, %s' % (match.group(1), match.group(2))
    return ''


def konwertuj_pdf_do_tiff(katalog_pdf, katalog_tiff=None, dpi=200,
                          podkatalogi=False, pomijaj_istniejace=True,
                          gdal_translate=None, log=print):
    """Konwersja wszystkich PDF-ow z katalogu do TIFF (bezstratnie).

    Zwraca slownik: {'udane': int, 'bledy': int, 'pominiete': int, 'pliki': int}.
    """
    if not katalog_pdf or not os.path.isdir(katalog_pdf):
        raise ValueError('Katalog z PDF nie istnieje: %s' % katalog_pdf)

    katalog_tiff = katalog_tiff or katalog_pdf
    gdal = gdal_translate or detect_gdal_translate()
    if not os.path.isfile(gdal):
        raise ValueError('Nie znaleziono gdal_translate: %s' % gdal)

    pliki = lista_pdf(katalog_pdf, podkatalogi)
    log('gdal_translate : %s' % gdal)
    log('Katalog PDF     : %s' % katalog_pdf)
    log('Katalog TIFF    : %s' % katalog_tiff)
    log('DPI / kompresja : %d / DEFLATE (bezstratna)' % dpi)
    log('Plików          : %d' % len(pliki))

    kwargs = {'creationflags': CREATE_NO_WINDOW} if os.name == 'nt' else {}
    udane = bledy = pominiete = 0

    for index, src in enumerate(pliki, start=1):
        dst, dst_dir = sciezka_docelowa(src, katalog_pdf, katalog_tiff, podkatalogi)
        log('[%d/%d] %s  ->  %s' % (index, len(pliki), os.path.basename(src), os.path.basename(dst)))

        if pomijaj_istniejace and os.path.isfile(dst):
            log('        pominięto (plik TIFF już istnieje)')
            pominiete += 1
            continue

        try:
            os.makedirs(dst_dir, exist_ok=True)
        except OSError as exc:
            log('        BŁĄD: nie można utworzyć katalogu %s (%s)' % (dst_dir, exc))
            bledy += 1
            continue

        try:
            proc = subprocess.run([gdal] + argumenty_gdal(dpi, src, dst),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        except OSError as exc:
            log('        BŁĄD: nie można uruchomić gdal_translate (%s)' % exc)
            bledy += 1
            continue

        tekst = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
        if proc.returncode == 0 and os.path.isfile(dst):
            udane += 1
            rozmiar = rozmiar_z_tekstu(tekst)
            if rozmiar:
                log('        OK  (%s px, DPI %d, bezstratnie)' % (rozmiar, dpi))
            else:
                log('        OK  (DPI %d, bezstratnie)' % dpi)
        else:
            bledy += 1
            log('        BŁĄD (kod %d)' % proc.returncode)
            for line in tekst.strip().splitlines()[-3:]:
                log('        %s' % line)

    log('=== KONIEC: udane=%d, błędy=%d, pominięte=%d ===' % (udane, bledy, pominiete))
    return {'udane': udane, 'bledy': bledy, 'pominiete': pominiete, 'pliki': len(pliki)}


# ----------------------------------------------------------------------
#  Algorytm dla Panelu przetwarzania
# ----------------------------------------------------------------------
class KonwertujPdfDoTiff(QgsProcessingAlgorithm):
    """PDF -> TIFF (bezstratnie, GDAL) jako algorytm Processing."""

    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    DPI = 'DPI'
    SKIP_EXISTING = 'SKIP_EXISTING'
    RECURSIVE = 'RECURSIVE'
    GDAL_TRANSLATE = 'GDAL_TRANSLATE'

    def name(self):
        return 'pdf_to_tiff'

    def displayName(self):
        return 'Konwertuj PDF do TIFF (bezstratnie)'

    def group(self):
        return 'Konwersja PDF'

    def groupId(self):
        return 'pdf2tiff'

    def shortHelpString(self):
        return (
            'Konwertuje wszystkie pliki *.pdf z katalogu do plików *.tif przy pomocy '
            'gdal_translate (renderowanie w zadanym DPI, kompresja bezstratna DEFLATE).\n\n'
            'Dla PDF rastrowych (np. PZT z CAD) 200 DPI = natywna rozdzielczość (1:1). '
            'Wyższe DPI to interpolacja - gładsze, ale bez nowego detalu.\n\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff '
            '-co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER '
            '"wejście.pdf" "wyjście.tif"'
        )

    def createInstance(self):
        return KonwertujPdfDoTiff()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            self.INPUT_FOLDER, 'Katalog z plikami PDF', behavior=_FILE_FOLDER))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_FOLDER, 'Katalog wynikowy (TIFF)'))
        self.addParameter(QgsProcessingParameterNumber(
            self.DPI, 'DPI renderowania (200 = natywne dla PDF rastrowych)',
            type=_NUMBER_INTEGER, defaultValue=200, minValue=72, maxValue=2400))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SKIP_EXISTING, 'Pomijaj istniejące TIFF', defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.RECURSIVE, 'Przetwarzaj podkatalogi', defaultValue=False))
        self.addParameter(QgsProcessingParameterFile(
            self.GDAL_TRANSLATE, 'gdal_translate (puste = wykryj automatycznie)',
            behavior=_FILE_FILE, optional=True, defaultValue=''))

    def processAlgorithm(self, parameters, context, feedback):
        gdal = self.parameterAsString(parameters, self.GDAL_TRANSLATE, context).strip()
        if not gdal:
            gdal = detect_gdal_translate()
        if not os.path.isfile(gdal):
            raise QgsProcessingException('Nie znaleziono gdal_translate: %s' % gdal)

        in_dir = self.parameterAsString(parameters, self.INPUT_FOLDER, context)
        if not os.path.isdir(in_dir):
            raise QgsProcessingException('Katalog źródłowy nie istnieje: %s' % in_dir)

        out_dir = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        if not out_dir:
            raise QgsProcessingException('Wskaż katalog wynikowy.')

        dpi = self.parameterAsInt(parameters, self.DPI, context)
        skip_existing = self.parameterAsBool(parameters, self.SKIP_EXISTING, context)
        recursive = self.parameterAsBool(parameters, self.RECURSIVE, context)

        pliki = lista_pdf(in_dir, recursive)
        if not pliki:
            raise QgsProcessingException('W katalogu nie znaleziono plików *.pdf.')

        feedback.pushInfo('gdal_translate : %s' % gdal)
        feedback.pushInfo('Katalog źródłowy: %s' % in_dir)
        feedback.pushInfo('Katalog docelowy: %s' % out_dir)
        feedback.pushInfo('DPI / kompresja : %d / DEFLATE (bezstratna)' % dpi)
        feedback.pushInfo('Plików do konwersji: %d' % len(pliki))

        kwargs = {'creationflags': CREATE_NO_WINDOW} if os.name == 'nt' else {}
        udane = bledy = 0
        total = len(pliki)

        for index, src in enumerate(pliki):
            if feedback.isCanceled():
                feedback.pushInfo('Przerwano na żądanie użytkownika.')
                break

            feedback.setProgress(int(index * 100.0 / total))
            dst, dst_dir = sciezka_docelowa(src, in_dir, out_dir, recursive)
            feedback.pushInfo('[%d/%d] %s  ->  %s' % (
                index + 1, total, os.path.basename(src), os.path.basename(dst)))

            if skip_existing and os.path.isfile(dst):
                feedback.pushInfo('        pominięto (plik TIFF już istnieje)')
                udane += 1
                continue

            try:
                os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                bledy += 1
                feedback.reportError('Nie można utworzyć katalogu %s (%s)' % (dst_dir, exc), fatalError=False)
                continue

            try:
                proc = subprocess.run([gdal] + argumenty_gdal(dpi, src, dst),
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
            except OSError as exc:
                bledy += 1
                feedback.reportError('Nie można uruchomić gdal_translate (%s)' % exc, fatalError=False)
                continue

            tekst = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
            if proc.returncode == 0 and os.path.isfile(dst):
                udane += 1
                rozmiar = rozmiar_z_tekstu(tekst)
                if rozmiar:
                    feedback.pushInfo('        OK  (%s px, DPI %d, bezstratnie)' % (rozmiar, dpi))
                else:
                    feedback.pushInfo('        OK  (DPI %d, bezstratnie)' % dpi)
            else:
                bledy += 1
                feedback.pushInfo('        BŁĄD (kod %d)' % proc.returncode)
                if tekst:
                    tail = '\n'.join(tekst.strip().splitlines()[-5:])
                    feedback.reportError('gdal_translate: %s' % tail, fatalError=False)

        feedback.setProgress(100)
        feedback.pushInfo('=== KONIEC: udane=%d, błędy=%d ===' % (udane, bledy))
        return {self.OUTPUT_FOLDER: out_dir}


# ----------------------------------------------------------------------
#  Uruchomienie z konsoli Pythona (opcjonalne)
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # W konsoli Pythona QGIS ten blok sie nie wykona przy imporcie - sluzy tylko
    # jako szybki test na przykladowym katalogu (podaj sciezke recznie).
    print('Użyj funkcji konwertuj_pdf_do_tiff(katalog_pdf, dpi=200) '
          'albo dodaj skrypt w Panelu przetwarzania.')
