# -*- coding: utf-8 -*-
"""
Konwerter PDF -> TIFF (bezstratny, GDAL) - samodzielny skrypt QGIS.
==============================================================================

Ten plik wystarczy sam - nie wymaga instalowania wtyczki.

DWA SPOSOBY UZYCIA
------------------
1) Panel przetwarzania (Processing):
   Panel przetwarzania -> Skrypty -> Dodaj skrypt z pliku... -> skrypt_pdf2tiff.py
   Potem: Skrypty -> Konwersja PDF -> "Konwertuj PDF do TIFF (bezstratnie)".
   Skrypt działa tez w modelach i w qgis_process.

2) Konsola Pythona w QGIS:
   Wtyczki -> Konsola Pythona, potem np.:

       import sys
       sys.path.append(r"C:\\sciezka\\do\\katalogu")
       from skrypt_pdf2tiff import konwertuj_pdf_do_tiff
       konwertuj_pdf_do_tiff(r"D:\\PZT", dpi=200, podkatalogi=True)

WYWOLYWANA KOMENDA
------------------
  gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
      -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
      "wejscie.pdf" "wyjscie.tif"

PDF WIELOSTRONICOWE (od 1.1.0)
------------------------------
GDAL udostepnia kazda strone PDF jako osobny podzbior ("PDF:<numer>:<plik>").
Domyslnie konwertowane sa tylko rysunki, czyli strony wieksze niz wybrany
format (A3 = wieksze niz A4); opisowki A4 sa pomijane. Do wyboru sa tez
wszystkie strony albo lista stron (np. "1,3,5-8").

Nazwy plikow: PDF jednosnej... -> nazwa.tif,
              PDF wielostron.  -> nazwa_p01.tif, nazwa_p02.tif, ...

Dla PDF rastrowych (np. PZT z CAD) 200 DPI = natywna rozdzielczosc (1:1).
Kompresja DEFLATE jest bezstratna, wiec jakosc nie jest tracona.

Uwaga bezpieczenstwa: gdal_translate uruchamiany jest wylacznie przez QProcess
z lista argumentow - bez powloki systemowej i bez modulu subprocess.

JEZYK KOMUNIKATOW
-----------------
Komunikaty (nazwy parametrow, opisy, log) pochodza z modulu i18n.py, ktory
znajduje sie obok tego pliku w paczce wtyczki. Jezyk jest brany z ustawien QGIS
(interfejs polski = komunikaty polskie). Gdy i18n.py nie ma obok skryptu,
uzywane sa komunikaty angielskie.
"""

import glob
import os
import re
import shutil
import sys

from qgis.PyQt.QtCore import QProcess

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum, QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination, QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

# ----------------------------------------------------------------------
#  Tlumaczenia
# ----------------------------------------------------------------------
# Skrypt uzywa tego samego modulu i18n.py co wtyczka, wiec komunikaty zaleza
# od jezyka QGIS. Gdy i18n.py lezy obok skryptu (tak jest w paczce wtyczki),
# wystarczy dopisac katalog skryptu do sys.path. Gdy ktos skopiuje sam plik,
# uzywane sa komunikaty angielskie z tabeli awaryjnej _EN_FALLBACK.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE and _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from .i18n import tr                       # wtyczka: pakiet pdf2tiff
except (ImportError, ValueError):
    try:
        from i18n import tr                    # skrypt dodany z pliku
    except ImportError:                        # sam plik - awaryjnie po angielsku
        _EN_FALLBACK = {
            'alg_name': 'Convert PDF to TIFF (lossless)',
            'alg_group': 'PDF conversion',
            'alg_help': (
                'Converts *.pdf files from a folder to *.tif with gdal_translate: rendering at '
                'the chosen DPI, lossless DEFLATE compression.\n\n'
                'Multipage PDFs: every page is a separate GDAL subdataset. By default only '
                'drawings are saved (pages larger than the chosen sheet format - A3 means '
                '"larger than A4"), so A4 description pages are skipped. You can also choose '
                'all pages or a page list, e.g. 1,3,5-8.\n\n'
                'File names: single-page PDF -> name.tif, multipage PDF -> name_p01.tif, '
                'name_p02.tif, ...\n\n'
                'For raster PDFs (e.g. drawings exported from CAD) 200 DPI is the native '
                'resolution (1:1). Higher DPI only interpolates.\n\n'
                'Command used:\n'
                'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff -co COMPRESS=DEFLATE '
                '-co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER "input.pdf" "output.tif"'
            ),
            'p_input': 'Folder with PDF files',
            'p_output': 'Output folder (TIFF)',
            'p_dpi': 'Rendering DPI (200 = native for raster PDFs)',
            'p_page_mode': 'PDF pages',
            'p_pages': 'Selected pages (e.g. 1,3,5-8; empty = all)',
            'p_min_format': 'Minimum drawing sheet size',
            'p_min_ink': 'Minimum ink coverage in percent (0 = no filter)',
            'p_skip': 'Skip existing TIFF',
            'p_recursive': 'Process subfolders',
            'p_gdal': 'gdal_translate (empty = detect automatically)',
            'opt_mode_drawings': 'drawings only (default)',
            'opt_mode_all': 'all pages',
            'opt_mode_custom': 'selected pages',
            'mode_line': 'Pages mode      : %(mode)s',
            'mode_line_drawings': ('Pages mode      : %(mode)s '
                                   '(min. sheet %(fmt)s, min. ink %(ink).1f%%)'),
            'info_gdal': 'gdal_translate : %(path)s',
            'info_in': 'Source folder  : %(path)s',
            'info_out': 'Target folder  : %(path)s',
            'info_dpi': 'DPI / compression: %(dpi)d / DEFLATE (lossless)',
            'info_files': 'Files to convert: %(count)d',
            'info_cancel': 'Cancelled by the user.',
            'info_mkdir': 'Cannot create folder %(dir)s (%(err)s)',
            'info_done': ('=== DONE: pages ok=%(ok)d, errors=%(fail)d, '
                          'skipped=%(skip)d ==='),
            'exc_no_gdal': 'gdal_translate not found: %(path)s',
            'exc_no_in': 'Source folder does not exist: %(path)s',
            'exc_no_out': 'Choose the output folder.',
            'exc_no_pdf': 'No *.pdf files found in the folder.',
            'err_start_gdal_sync': 'Cannot start gdal_translate: %(path)s',
            'err_read_pages': '%(name)s: cannot read pages (%(err)s)',
            'sync_pages': '        pages: %(pages)d, to convert: %(todo)d',
            'sync_page_skip': '        page %(page)d -> %(file)s : skipped (file exists)',
            'sync_page_ok': '        page %(page)d -> %(file)s : OK (%(size)s px)',
            'sync_page_ok_short': '        page %(page)d -> %(file)s : OK',
            'sync_page_err': '        page %(page)d -> %(file)s : ERROR (code %(rc)d)',
            'log_page_skipped': '        page %(page)d: skipped (%(reason)s)',
            'log_no_pages': '        no pages to convert',
            'err_mkdir': '        ERROR: cannot create folder %(dir)s (%(err)s)',
            'reason_too_small': '%(size)s (smaller than %(fmt)s)',
            'reason_ink': '%(size)s, ink %(ink).2f%% (min. %(min).2f%%)',
            'reason_kept': '%(size)s, ink %(ink).2f%%',
            'note_no_big': ('no page is larger than %(fmt)s - converting all pages '
                            '(change "Min. drawing sheet size" to filter)'),
            'note_custom': 'selected pages (%(count)d of %(total)d): %(list)s',
        }

        def tr(key, **kwargs):
            """Tekst angielski z tabeli awaryjnej (gdy brak modulu i18n)."""
            text = _EN_FALLBACK.get(key, key)
            if kwargs:
                try:
                    text = text % kwargs
                except (KeyError, TypeError, ValueError):
                    return text
            return text


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


def _enum_value(owner, scope_name, name):
    """Wartosc enum parametru Processing niezalezna od wersji QGIS/PyQt.

    QGIS 3 / PyQt5 : QgsProcessingParameterNumber.Integer
    QGIS 4 / PyQt6 : QgsProcessingParameterNumber.Type.Integer
    """
    value = getattr(owner, name, None)
    if value is not None:
        return value
    scope = getattr(owner, scope_name, None)
    if scope is not None:
        nested = getattr(scope, name, None)
        if nested is not None:
            return nested
    raise AttributeError('%s.%s' % (getattr(owner, '__name__', owner), name))


_NUMBER_INTEGER = _enum_value(QgsProcessingParameterNumber, 'Type', 'Integer')
_NUMBER_DOUBLE = _enum_value(QgsProcessingParameterNumber, 'Type', 'Double')
_FILE_FOLDER = _enum_value(QgsProcessingParameterFile, 'Behavior', 'Folder')
_FILE_FILE = _enum_value(QgsProcessingParameterFile, 'Behavior', 'File')


def _qenum(owner, name):
    """Wartosc enum QProcess dzialajaca w PyQt5 i PyQt6."""
    value = getattr(owner, name, None)
    if value is not None:
        return value
    for scope_name in ('ProcessChannelMode', 'ProcessState', 'ExitStatus'):
        scope = getattr(owner, scope_name, None)
        if scope is not None and hasattr(scope, name):
            return getattr(scope, name)
    raise AttributeError('%s.%s' % (owner.__name__, name))


_MERGED_CHANNELS = _qenum(QProcess, 'MergedChannels')
_NORMAL_EXIT = _qenum(QProcess, 'NormalExit')


def _qgis_prefix():
    """Sciezka instalacji QGIS albo pusty tekst, gdy modul qgis jest niedostepny."""
    try:
        from qgis.core import QgsApplication
    except ImportError:
        return ''
    return QgsApplication.prefixPath()


def detect_gdal_translate():
    """Zwraca sciezke do gdal_translate (albo sama nazwe programu jako fallback)."""
    candidates = []

    found = shutil.which('gdal_translate')
    if found:
        candidates.append(found)

    prefix = _qgis_prefix()
    if prefix:
        candidates.append(os.path.join(prefix, 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(os.path.dirname(prefix), 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(prefix)),
                                       'bin', 'gdal_translate.exe'))

    candidates.extend(GDAL_CANDIDATES)

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.normpath(path)

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
        if not os.path.isdir(katalog):
            return []
        for name in os.listdir(katalog):
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


def sciezka_strony(bazowy_tif, strona, liczba_stron):
    """nazwa.tif dla PDF jednosnej..., nazwa_p01.tif dla wielostronicowego."""
    if liczba_stron <= 1:
        return bazowy_tif
    root, ext = os.path.splitext(bazowy_tif)
    width = max(2, len(str(int(liczba_stron))))
    return '%s_p%0*d%s' % (root, width, int(strona), ext)


def argumenty_gdal(dpi, src, dst):
    """Argumenty gdal_translate - renderowanie w DPI i kompresja bezstratna."""
    return [
        '--config', 'GDAL_PDF_DPI', str(int(dpi)),
        '-of', 'GTiff',
        '-co', 'COMPRESS=DEFLATE',
        '-co', 'PREDICTOR=2',
        '-co', 'TILED=YES',
        '-co', 'BIGTIFF=IF_SAFER',
        src, dst,
    ]


def uruchom_gdal(gdal, src, dst, dpi):
    """Uruchamia gdal_translate przez QProcess i czeka na koniec.

    Zwraca krotke (ok, kod_wyjscia, rozmiar, tekst_wyjscia).
    """
    proc = QProcess()
    proc.setProcessChannelMode(_MERGED_CHANNELS)
    proc.start(gdal, argumenty_gdal(dpi, src, dst))

    if not proc.waitForStarted(20000):
        return False, -1, '', tr('err_start_gdal_sync', path=gdal)

    proc.waitForFinished(-1)
    tekst = bytes(proc.readAll()).decode('utf-8', 'replace')
    kod = proc.exitCode() if proc.exitStatus() == _NORMAL_EXIT else -1
    return (kod == 0 and os.path.isfile(dst)), kod, rozmiar_z_tekstu(tekst), tekst


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


# ----------------------------------------------------------------------
#  Strony PDF - wykrywanie i wybor stron (GDAL subdatasety)
# ----------------------------------------------------------------------
TRYB_RYSUNKI = 'drawings'
TRYB_WSZYSTKIE = 'all'
TRYB_WYBRANE = 'custom'

TRYBY_STRON = [TRYB_RYSUNKI, TRYB_WSZYSTKIE, TRYB_WYBRANE]
WARTOSCI_TRYBOW = TRYBY_STRON


def etykiety_trybow():
    """Nazwy trybow stron w aktualnym jezyku (kolejnosc = TRYBY_STRON)."""
    return [tr('opt_mode_drawings'), tr('opt_mode_all'), tr('opt_mode_custom')]


def opis_trybu(tryb_stron):
    """Krotka nazwa trybu stron (do logu / parametrow)."""
    if tryb_stron == TRYB_WSZYSTKIE:
        return tr('opt_mode_all')
    if tryb_stron == TRYB_WYBRANE:
        return tr('opt_mode_custom')
    return tr('opt_mode_drawings')

#: Formaty arkuszy w mm (krotny bok, dlugi bok)
FORMATY_MM = [
    ('A4', 210.0, 297.0),
    ('A3', 297.0, 420.0),
    ('A2', 420.0, 594.0),
    ('A1', 594.0, 841.0),
    ('A0', 841.0, 1189.0),
]
NAZWY_FORMATOW = [item[0] for item in FORMATY_MM]
DOMYSLNY_FORMAT = 'A3'
DOMYSLNY_TUSZ = 0.0

DPI_ROZMIAR = 72       # pomiar formatu strony: px / DPI * 25.4 = mm
DPI_TUSZ = 36          # pomiar pokrycia tuszem (szybki, orientacyjny)
PROG_TUSZU = 250       # piksel ciemniejszy od tej wartosci = "tusz"
TOLERANCJA_FORMATU = 0.9


def _gdal():
    """Import osgeo.gdal z wlaczonymi wyjatkami."""
    from osgeo import gdal
    use_exceptions = getattr(gdal, 'UseExceptions', None)
    if use_exceptions is not None:
        use_exceptions()
    return gdal


def lista_stron_pdf(sciezka):
    """Nazwy podzbiorow GDAL (stron); pusta lista = PDF jednosnej..."""
    gdal = _gdal()
    try:
        dataset = gdal.Open(sciezka)
    except RuntimeError:
        return []
    if dataset is None:
        return []
    subs = dataset.GetSubDatasets()
    dataset = None
    return [nazwa for nazwa, _ in subs]


def _otworz_strone(nazwa, dpi):
    """Otwiera strone z ustawionym GDAL_PDF_DPI; zwraca (dataset, poprzednie_DPI)."""
    gdal = _gdal()
    previous = gdal.GetConfigOption('GDAL_PDF_DPI')
    gdal.SetConfigOption('GDAL_PDF_DPI', str(int(dpi)))
    try:
        dataset = gdal.Open(nazwa)
    except RuntimeError:
        dataset = None
    return dataset, previous


def rozmiar_strony_mm(nazwa, dpi=DPI_ROZMIAR):
    """Format strony w milimetrach (szerokosc, wysokosc)."""
    gdal = _gdal()
    dataset, previous = _otworz_strone(nazwa, dpi)
    if dataset is None:
        gdal.SetConfigOption('GDAL_PDF_DPI', previous)
        return 0.0, 0.0
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    dataset = None
    gdal.SetConfigOption('GDAL_PDF_DPI', previous)
    return width / float(dpi) * 25.4, height / float(dpi) * 25.4


def pokrycie_tuszem(nazwa, dpi=DPI_TUSZ):
    """Pokrycie strony tuszem w procentach."""
    gdal = _gdal()
    dataset, previous = _otworz_strone(nazwa, dpi)
    if dataset is None:
        gdal.SetConfigOption('GDAL_PDF_DPI', previous)
        return 0.0
    band = dataset.GetRasterBand(1)
    try:
        data = band.ReadAsArray()
    except (RuntimeError, ValueError):
        data = None
    dataset = None
    gdal.SetConfigOption('GDAL_PDF_DPI', previous)
    if data is None:
        return 0.0
    try:
        total = int(data.size)
        dark = int((data < PROG_TUSZU).sum())
    except (AttributeError, TypeError):
        return 0.0
    if total <= 0:
        return 0.0
    return 100.0 * dark / float(total)


def powierzchnia_formatu(nazwa):
    """Powierzchnia arkusza (mm2) dla nazwy formatu, np. 'A3'."""
    key = str(nazwa or '').strip().upper()
    for item in FORMATY_MM:
        if item[0] == key:
            return item[1] * item[2]
    return FORMATY_MM[1][1] * FORMATY_MM[1][2]


def czy_rysunek(nazwa, min_format=DOMYSLNY_FORMAT, min_tusz=DOMYSLNY_TUSZ):
    """Ocena strony: (czy_rysunek, opis_decyzji).

    Rysunki techniczne sa zwykle wieksze niz A4 (A3, A2, A1, A0), dlatego
    podstawowym kryterium jest format strony; opcjonalnie odrzucane sa
    tez strony prawie puste (min_tusz > 0).
    """
    width, height = rozmiar_strony_mm(nazwa)
    area = width * height
    needed = powierzchnia_formatu(min_format) * TOLERANCJA_FORMATU
    opis = '%.0f x %.0f mm' % (width, height)
    if area < needed:
        return False, tr('reason_too_small', size=opis, fmt=str(min_format).upper())
    if min_tusz > 0:
        tusz = pokrycie_tuszem(nazwa)
        if tusz < float(min_tusz):
            return False, tr('reason_ink', size=opis, ink=tusz, min=float(min_tusz))
        return True, tr('reason_kept', size=opis, ink=tusz)
    return True, opis


def parsuj_liste_stron(specyfikacja, liczba_stron):
    """'1,3,5-8' -> [1,3,5,6,7,8] (posortowane, bez powtorzen)."""
    strony = []
    tekst = str(specyfikacja or '').replace(';', ',').replace(' ', ',')
    for czesc in tekst.split(','):
        czesc = czesc.strip()
        if not czesc:
            continue
        if '-' in czesc:
            pierwsza, _, ostatnia = czesc.partition('-')
            try:
                start = int(pierwsza)
                stop = int(ostatnia)
            except ValueError:
                continue
            if start > stop:
                start, stop = stop, start
            strony.extend(range(start, stop + 1))
        else:
            try:
                strony.append(int(czesc))
            except ValueError:
                continue
    return sorted(set(s for s in strony if 1 <= s <= int(liczba_stron)))


def _tekst_stron(strony, limit=24):
    """Krotki opis listy stron do logu."""
    pokazane = ', '.join(str(s) for s in strony[:limit])
    if len(strony) > limit:
        pokazane += ', ...'
    return pokazane


def plan_stron_pdf(sciezka, tryb=TRYB_RYSUNKI, lista_stron='',
                   min_format=DOMYSLNY_FORMAT, min_tusz=DOMYSLNY_TUSZ):
    """Ustala strony do konwersji: (liczba_stron, zadania, pominiete, uwaga).

    zadania   - [(numer_strony, zrodlo_dla_gdal)]
    pominiete - [(numer_strony, powod)]
    uwaga     - dodatkowy komunikat ('' = brak)

    Gdy zaden arkusz nie jest wiekszy niz wybrany format (np. caly PDF to
    rysunki na A4), filtr formatu nie jest uzywany - lepiej przekonwertowac
    wszystkie strony niz nie zapisac nic.
    """
    subs = lista_stron_pdf(sciezka)
    count = len(subs) if subs else 1

    def zrodlo(strona):
        if subs:
            return subs[strona - 1]
        return sciezka

    if count <= 1:
        return count, [(1, zrodlo(1))], [], ''

    zadania = []
    pominiete = []

    if tryb == TRYB_WYBRANE:
        wybrane = parsuj_liste_stron(lista_stron, count) or list(range(1, count + 1))
        zadania = [(s, zrodlo(s)) for s in wybrane]
        uwaga = tr('note_custom', count=len(wybrane), total=count,
                   list=_tekst_stron(wybrane))
        return count, zadania, [], uwaga

    if tryb == TRYB_WSZYSTKIE:
        for strona in range(1, count + 1):
            zadania.append((strona, zrodlo(strona)))
        return count, zadania, pominiete, ''

    # tryb "tylko rysunki" - najpierw format strony
    potrzebna = powierzchnia_formatu(min_format) * TOLERANCJA_FORMATU
    wieksze = []
    opisy = {}
    for strona in range(1, count + 1):
        width, height = rozmiar_strony_mm(zrodlo(strona))
        opis = '%.0f x %.0f mm' % (width, height)
        if width * height < potrzebna:
            pominiete.append((strona, tr('reason_too_small', size=opis,
                                         fmt=str(min_format).upper())))
        else:
            wieksze.append(strona)
            opisy[strona] = opis

    if not wieksze:
        uwaga = tr('note_no_big', fmt=str(min_format).upper())
        return count, [(s, zrodlo(s)) for s in range(1, count + 1)], [], uwaga

    # opcjonalny filtr stron prawie pustych (tylko wśród uznanych za rysunki)
    if min_tusz > 0:
        for strona in wieksze:
            tusz = pokrycie_tuszem(zrodlo(strona))
            if tusz < float(min_tusz):
                pominiete.append((strona, tr('reason_ink', size=opisy[strona],
                                             ink=tusz, min=float(min_tusz))))
            else:
                zadania.append((strona, zrodlo(strona)))
        pominiete.sort()
        return count, zadania, pominiete, ''

    return count, [(s, zrodlo(s)) for s in wieksze], pominiete, ''


# ----------------------------------------------------------------------
#  Konwersja katalogu
# ----------------------------------------------------------------------
def konwertuj_pdf_do_tiff(katalog_pdf, katalog_tiff=None, dpi=200,
                          podkatalogi=False, pomijaj_istniejace=True,
                          gdal_translate=None, log=print,
                          tryb_stron=TRYB_RYSUNKI, lista_stron='',
                          min_format=DOMYSLNY_FORMAT, min_tusz=DOMYSLNY_TUSZ):
    """Konwersja wszystkich PDF-ow z katalogu do TIFF (bezstratnie).

    tryb_stron: TRYB_RYSUNKI (domyslnie), TRYB_WSZYSTKIE albo TRYB_WYBRANE.
    Zwraca slownik: {'udane': int, 'bledy': int, 'pominiete': int, 'pliki': int}.
    """
    if not katalog_pdf or not os.path.isdir(katalog_pdf):
        raise ValueError(tr('exc_no_in', path=katalog_pdf))

    katalog_tiff = katalog_tiff or katalog_pdf
    gdal = gdal_translate or detect_gdal_translate()
    if not os.path.isfile(gdal):
        raise ValueError(tr('exc_no_gdal', path=gdal))

    pliki = lista_pdf(katalog_pdf, podkatalogi)
    log(tr('info_gdal', path=gdal))
    log(tr('info_in', path=katalog_pdf))
    log(tr('info_out', path=katalog_tiff))
    log(tr('info_dpi', dpi=int(dpi)))
    if tryb_stron == TRYB_RYSUNKI:
        log(tr('mode_line_drawings', mode=opis_trybu(tryb_stron),
               fmt=str(min_format).upper(), ink=float(min_tusz)))
    elif tryb_stron == TRYB_WYBRANE:
        log(tr('mode_line', mode=tr('mode_text_custom',
                                    spec=lista_stron or tr('all_pages_word'))))
    else:
        log(tr('mode_line', mode=opis_trybu(tryb_stron)))
    log(tr('info_files', count=len(pliki)))

    udane = bledy = pominiete = 0

    for index, src in enumerate(pliki, start=1):
        bazowy, dst_dir = sciezka_docelowa(src, katalog_pdf, katalog_tiff, podkatalogi)
        log('[%d/%d] %s' % (index, len(pliki), os.path.basename(src)))

        try:
            liczba_stron, zadania, odrzucone, uwaga = plan_stron_pdf(
                src, tryb_stron, lista_stron, min_format, min_tusz)
        except (RuntimeError, ValueError, OSError) as exc:
            log(tr('err_read_pages', name=os.path.basename(src), err=exc))
            liczba_stron, zadania, odrzucone, uwaga = 1, [(1, src)], [], []

        log(tr('sync_pages', pages=liczba_stron, todo=len(zadania)))
        if uwaga:
            log('        %s' % uwaga)
        for strona, powod in odrzucone:
            log(tr('log_page_skipped', page=strona, reason=powod))
        if not zadania:
            log(tr('log_no_pages'))
            continue

        try:
            os.makedirs(dst_dir, exist_ok=True)
        except OSError as exc:
            log(tr('err_mkdir', dir=dst_dir, err=exc))
            bledy += len(zadania)
            continue

        for strona, zrodlo in zadania:
            dst = sciezka_strony(bazowy, strona, liczba_stron)

            if pomijaj_istniejace and os.path.isfile(dst):
                log(tr('sync_page_skip', page=strona, file=os.path.basename(dst)))
                pominiete += 1
                continue

            ok, kod, rozmiar, tekst = uruchom_gdal(gdal, zrodlo, dst, dpi)
            if ok:
                udane += 1
                if rozmiar:
                    log(tr('sync_page_ok', page=strona,
                           file=os.path.basename(dst), size=rozmiar))
                else:
                    log(tr('sync_page_ok_short', page=strona,
                           file=os.path.basename(dst)))
            else:
                bledy += 1
                log(tr('sync_page_err', page=strona,
                       file=os.path.basename(dst), rc=kod))
                if tekst:
                    for line in tekst.strip().splitlines()[-3:]:
                        log('            %s' % line)

    log(tr('info_done', ok=udane, fail=bledy, skip=pominiete))
    return {'udane': udane, 'bledy': bledy, 'pominiete': pominiete, 'pliki': len(pliki)}


# ----------------------------------------------------------------------
#  Algorytm dla Panelu przetwarzania
# ----------------------------------------------------------------------
class KonwertujPdfDoTiff(QgsProcessingAlgorithm):
    """PDF -> TIFF (bezstratnie, GDAL) jako algorytm Processing."""

    INPUT_FOLDER = 'INPUT_FOLDER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    DPI = 'DPI'
    PAGE_MODE = 'PAGE_MODE'
    PAGES = 'PAGES'
    MIN_FORMAT = 'MIN_FORMAT'
    MIN_INK = 'MIN_INK'
    SKIP_EXISTING = 'SKIP_EXISTING'
    RECURSIVE = 'RECURSIVE'
    GDAL_TRANSLATE = 'GDAL_TRANSLATE'

    def name(self):
        return 'pdf_to_tiff'

    def displayName(self):
        return tr('alg_name')

    def group(self):
        return tr('alg_group')

    def groupId(self):
        return 'pdf2tiff'

    def shortHelpString(self):
        return tr('alg_help')

    def createInstance(self):
        return KonwertujPdfDoTiff()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            self.INPUT_FOLDER, tr('p_input'), behavior=_FILE_FOLDER))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_FOLDER, tr('p_output')))
        self.addParameter(QgsProcessingParameterNumber(
            self.DPI, tr('p_dpi'),
            type=_NUMBER_INTEGER, defaultValue=200, minValue=72, maxValue=2400))
        self.addParameter(QgsProcessingParameterEnum(
            self.PAGE_MODE, tr('p_page_mode'), options=etykiety_trybow(), defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.PAGES, tr('p_pages'), defaultValue='', optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.MIN_FORMAT, tr('p_min_format'), options=NAZWY_FORMATOW,
            defaultValue=NAZWY_FORMATOW.index(DOMYSLNY_FORMAT)))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_INK, tr('p_min_ink'),
            type=_NUMBER_DOUBLE, defaultValue=DOMYSLNY_TUSZ,
            minValue=0.0, maxValue=90.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SKIP_EXISTING, tr('p_skip'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.RECURSIVE, tr('p_recursive'), defaultValue=False))
        self.addParameter(QgsProcessingParameterFile(
            self.GDAL_TRANSLATE, tr('p_gdal'),
            behavior=_FILE_FILE, optional=True, defaultValue=''))

    def processAlgorithm(self, parameters, context, feedback):
        gdal = self.parameterAsString(parameters, self.GDAL_TRANSLATE, context).strip()
        if not gdal:
            gdal = detect_gdal_translate()
        if not os.path.isfile(gdal):
            raise QgsProcessingException(tr('exc_no_gdal', path=gdal))

        in_dir = self.parameterAsString(parameters, self.INPUT_FOLDER, context)
        if not os.path.isdir(in_dir):
            raise QgsProcessingException(tr('exc_no_in', path=in_dir))

        out_dir = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        if not out_dir:
            raise QgsProcessingException(tr('exc_no_out'))

        dpi = self.parameterAsInt(parameters, self.DPI, context)
        skip_existing = self.parameterAsBool(parameters, self.SKIP_EXISTING, context)
        recursive = self.parameterAsBool(parameters, self.RECURSIVE, context)

        tryb_index = self.parameterAsEnum(parameters, self.PAGE_MODE, context)
        if 0 <= tryb_index < len(WARTOSCI_TRYBOW):
            tryb_stron = WARTOSCI_TRYBOW[tryb_index]
        else:
            tryb_stron = TRYB_RYSUNKI
        lista_stron = self.parameterAsString(parameters, self.PAGES, context).strip()

        format_index = self.parameterAsEnum(parameters, self.MIN_FORMAT, context)
        if 0 <= format_index < len(NAZWY_FORMATOW):
            min_format = NAZWY_FORMATOW[format_index]
        else:
            min_format = DOMYSLNY_FORMAT
        min_tusz = self.parameterAsDouble(parameters, self.MIN_INK, context)

        pliki = lista_pdf(in_dir, recursive)
        if not pliki:
            raise QgsProcessingException(tr('exc_no_pdf'))

        feedback.pushInfo(tr('info_gdal', path=gdal))
        feedback.pushInfo(tr('info_in', path=in_dir))
        feedback.pushInfo(tr('info_out', path=out_dir))
        feedback.pushInfo(tr('info_dpi', dpi=int(dpi)))
        if tryb_stron == TRYB_RYSUNKI:
            feedback.pushInfo(tr('mode_line_drawings', mode=opis_trybu(tryb_stron),
                                 fmt=str(min_format).upper(), ink=float(min_tusz)))
        else:
            feedback.pushInfo(tr('mode_line', mode=opis_trybu(tryb_stron)))
        feedback.pushInfo(tr('info_files', count=len(pliki)))

        udane = bledy = pominiete = 0
        total = len(pliki)

        for index, src in enumerate(pliki):
            if feedback.isCanceled():
                feedback.pushInfo(tr('info_cancel'))
                break

            feedback.setProgress(int(index * 100.0 / total))
            bazowy, dst_dir = sciezka_docelowa(src, in_dir, out_dir, recursive)
            feedback.pushInfo('[%d/%d] %s' % (index + 1, total, os.path.basename(src)))

            try:
                liczba_stron, zadania, odrzucone, uwaga = plan_stron_pdf(
                    src, tryb_stron, lista_stron, min_format, min_tusz)
            except (RuntimeError, ValueError, OSError) as exc:
                feedback.pushInfo(tr('err_read_pages', name=os.path.basename(src), err=exc))
                liczba_stron, zadania, odrzucone, uwaga = 1, [(1, src)], [], []

            feedback.pushInfo(tr('sync_pages', pages=liczba_stron, todo=len(zadania)))
            if uwaga:
                feedback.pushInfo('        %s' % uwaga)
            for strona, powod in odrzucone:
                feedback.pushInfo(tr('log_page_skipped', page=strona, reason=powod))
            if not zadania:
                feedback.pushInfo(tr('log_no_pages'))
                continue

            try:
                os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                bledy += len(zadania)
                feedback.reportError(tr('info_mkdir', dir=dst_dir, err=exc),
                                     fatalError=False)
                continue

            for strona, zrodlo in zadania:
                if feedback.isCanceled():
                    break
                dst = sciezka_strony(bazowy, strona, liczba_stron)

                if skip_existing and os.path.isfile(dst):
                    feedback.pushInfo(tr('sync_page_skip', page=strona,
                                         file=os.path.basename(dst)))
                    pominiete += 1
                    continue

                ok, kod, rozmiar, tekst = uruchom_gdal(gdal, zrodlo, dst, dpi)
                if ok:
                    udane += 1
                    if rozmiar:
                        feedback.pushInfo(tr('sync_page_ok', page=strona,
                                             file=os.path.basename(dst), size=rozmiar))
                    else:
                        feedback.pushInfo(tr('sync_page_ok_short', page=strona,
                                             file=os.path.basename(dst)))
                else:
                    bledy += 1
                    feedback.pushInfo(tr('sync_page_err', page=strona,
                                         file=os.path.basename(dst), rc=kod))
                    if tekst:
                        tail = '\n'.join(tekst.strip().splitlines()[-5:])
                        feedback.reportError('gdal_translate: %s' % tail, fatalError=False)

        feedback.setProgress(100)
        feedback.pushInfo(tr('info_done', ok=udane, fail=bledy, skip=pominiete))
        return {self.OUTPUT_FOLDER: out_dir}


# ----------------------------------------------------------------------
#  Uruchomienie z konsoli Pythona (opcjonalne)
# ----------------------------------------------------------------------
if __name__ == '__main__':
    # W konsoli Pythona QGIS ten blok sie nie wykona przy imporcie - sluzy tylko
    # jako szybka podpowiedz (podaj sciezke recznie).
    print('Użyj funkcji konwertuj_pdf_do_tiff(katalog_pdf, dpi=200) '
          'albo dodaj skrypt w Panelu Przetwarzania.')
