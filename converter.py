# -*- coding: utf-8 -*-
"""
Konwerter PDF -> TIFF (bezstratny, GDAL) - logika wspolna.

Modul nie tworzy widgetow, wiec korzysta z niego zarowno okno wtyczki
(dialog.py), jak i algorytm Processing (algorithm.py).

Wywoływana komenda jest identyczna jak w programie Laz_PDF_tiff:

    gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
        -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
        "wejscie.pdf" "wyjscie.tif"

PDF wielostronicowe: GDAL udostepnia kazda strone jako podzbior
("PDF:<numer>:<plik>"), wiec konwertujemy strony po kolei i zapisujemy
nazwa_p01.tif, nazwa_p02.tif, ... (PDF jednosnej... -> nazwa.tif).

Uwaga bezpieczenstwa: program zewnetrzny uruchamiany jest wylacznie przez
QProcess, z lista argumentow (bez powloki systemowej, bez subprocess),
a sciezka do gdal_translate pochodzi ze wskazania uzytkownika lub z
automatycznego wykrywania instalacji QGIS / OSGeo4W.
"""

import codecs
import glob
import os
import re
import shutil

from qgis.PyQt.QtCore import QProcess, QThread, pyqtSignal

#: Sciezki sprawdzane, gdy nie uda sie znalezc gdal_translate w inny sposob
GDAL_CANDIDATES = [
    r'C:\QGIS\bin\gdal_translate.exe',
    r'C:\OSGeo4W\bin\gdal_translate.exe',
    r'C:\OSGeo4W64\bin\gdal_translate.exe',
    r'C:\Program Files\OSGeo4W\bin\gdal_translate.exe',
    r'C:\Program Files\QGIS 3.40.0\bin\gdal_translate.exe',
]

#: Wzorce katalogow instalacyjnych (QGIS / OSGeo4W w dowolnej wersji)
GDAL_GLOBS = [
    r'C:\Program Files\QGIS*\bin\gdal_translate.exe',
    r'C:\QGIS*\bin\gdal_translate.exe',
    r'C:\OSGeo4W*\bin\gdal_translate.exe',
    r'C:\Program Files\OSGeo4W*\bin\gdal_translate.exe',
]

_PROGRESS_RE = re.compile(r'(\d{1,3})\s*\.\.\.')
_SIZE_RE = re.compile(r'size is\s+(\d+)\s*,\s*(\d+)')


def _qenum(owner, name):
    """Zwraca wartosc enum QProcess dzialajaca i w PyQt5, i w PyQt6.

    PyQt5: QProcess.MergedChannels
    PyQt6: QProcess.ProcessChannelMode.MergedChannels
    """
    value = getattr(owner, name, None)
    if value is not None:
        return value
    for scope_name in ('ProcessChannelMode', 'ProcessState', 'ExitStatus'):
        scope = getattr(owner, scope_name, None)
        if scope is not None and hasattr(scope, name):
            return getattr(scope, name)
    raise AttributeError('%s.%s' % (owner.__name__, name))


_MERGED_CHANNELS = _qenum(QProcess, 'MergedChannels')
_NOT_RUNNING = _qenum(QProcess, 'NotRunning')
_NORMAL_EXIT = _qenum(QProcess, 'NormalExit')


# ----------------------------------------------------------------------
#  Wykrywanie gdal_translate
# ----------------------------------------------------------------------
def _qgis_prefix():
    """Sciezka instalacji QGIS albo pusty tekst, gdy modul qgis jest niedostepny."""
    try:
        from qgis.core import QgsApplication
    except ImportError:
        return ''
    return QgsApplication.prefixPath()


def detect_gdal_translate():
    """Zwraca sciezke do gdal_translate (najlepsze trafienie) lub nazwe programu."""
    candidates = []

    # 1. Program z PATH
    found = shutil.which('gdal_translate')
    if found:
        candidates.append(found)

    # 2. Instalacja QGIS, w ktorej uruchomiona jest wtyczka
    prefix = _qgis_prefix()
    if prefix:
        candidates.append(os.path.join(prefix, 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(os.path.dirname(prefix), 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(prefix)),
                                       'bin', 'gdal_translate.exe'))

    # 3. Typowe lokalizacje
    candidates.extend(GDAL_CANDIDATES)

    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.normpath(path)

    # 4. Dopasowanie wzorcami (dowolna wersja QGIS / OSGeo4W)
    for pattern in GDAL_GLOBS:
        hits = sorted(glob.glob(pattern), reverse=True)
        if hits:
            return os.path.normpath(hits[0])

    return candidates[-1] if candidates else 'gdal_translate.exe'


# ----------------------------------------------------------------------
#  Budowanie listy plikow, sciezek i argumentow GDAL
# ----------------------------------------------------------------------
def list_pdf_files(folder, recursive=False):
    """Zwraca posortowana liste plikow *.pdf (rozszerzenie bez wzgledu na wielkosc liter)."""
    result = []
    if recursive:
        for root, dirs, files in os.walk(folder):
            dirs.sort(key=str.lower)
            for name in files:
                if name.lower().endswith('.pdf'):
                    result.append(os.path.join(root, name))
    else:
        if not os.path.isdir(folder):
            return []
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and name.lower().endswith('.pdf'):
                result.append(path)

    result.sort(key=lambda p: (os.path.dirname(p).lower(), os.path.basename(p).lower()))
    return result


def build_dest_path(src, base_in, out_dir, keep_sub=False):
    """Zwraca (sciezka_tif, katalog_docelowy) dla pliku zrodlowego.

    Gdy keep_sub=True, struktura podkatalogow jest odtwarzana w katalogu
    docelowym (tak jak opcja "Podkatalogi" w programie Lazarus).
    """
    try:
        rel = os.path.relpath(src, base_in)
    except ValueError:          # inny dysk
        rel = os.path.basename(src)

    if os.path.isabs(rel) or rel.startswith('..') or ':' in rel:
        rel = os.path.basename(src)

    sub = os.path.dirname(rel)
    if keep_sub and sub:
        dst_dir = os.path.join(out_dir, sub)
    else:
        dst_dir = out_dir

    name = os.path.splitext(os.path.basename(src))[0] + '.tif'
    return os.path.join(dst_dir, name), dst_dir


def page_dest(base_tif, page, page_count):
    """Nazwa pliku wyniku: nazwa.tif dla PDF jednosnej..., nazwa_p01.tif dla wielosnej..."""
    if page_count <= 1:
        return base_tif
    root, ext = os.path.splitext(base_tif)
    width = max(2, len(str(int(page_count))))
    return '%s_p%0*d%s' % (root, width, int(page), ext)


def build_gdal_arguments(dpi, src, dst):
    """Argumenty gdal_translate - dokladnie jak w wersji Lazarus."""
    return [
        '--config', 'GDAL_PDF_DPI', str(int(dpi)),
        '-of', 'GTiff',
        '-co', 'COMPRESS=DEFLATE',
        '-co', 'PREDICTOR=2',
        '-co', 'TILED=YES',
        '-co', 'BIGTIFF=IF_SAFER',
        src, dst,
    ]


# ----------------------------------------------------------------------
#  Strony PDF - wykrywanie i wybor stron do konwersji
# ----------------------------------------------------------------------
PAGE_MODE_DRAWINGS = 'drawings'
PAGE_MODE_ALL = 'all'
PAGE_MODE_CUSTOM = 'custom'

#: (wartosc, etykieta) - kolejnosc jak w oknie wtyczki i w algorytmie
PAGE_MODES = [
    (PAGE_MODE_DRAWINGS, 'tylko rysunki (pomijaj opisówki)'),
    (PAGE_MODE_ALL, 'wszystkie strony'),
    (PAGE_MODE_CUSTOM, 'wskazane strony (np. 1,3,5-8)'),
]

#: Formaty arkuszy w mm (krotny bok, dlugi bok)
SHEET_MM = [
    ('A4', 210.0, 297.0),
    ('A3', 297.0, 420.0),
    ('A2', 420.0, 594.0),
    ('A1', 594.0, 841.0),
    ('A0', 841.0, 1189.0),
]
SHEET_NAMES = [item[0] for item in SHEET_MM]
DEFAULT_MIN_FORMAT = 'A3'
DEFAULT_MIN_INK = 0.0

SIZE_DPI = 72          # DPI do pomiaru formatu strony (px / DPI * 25.4 = mm)
INK_DPI = 36           # DPI do pomiaru pokrycia tuszem (szybkie, orientacyjne)
INK_THRESHOLD = 250    # piksel ciemniejszy od tej wartosci = "tusz"
SIZE_TOLERANCE = 0.9   # zapas na zaokraglenia formatu (90% powierzchni arkusza)


def _gdal():
    """Import osgeo.gdal z wlaczonymi wyjatkami (bezpieczniej niz kody powrotu)."""
    from osgeo import gdal
    use_exceptions = getattr(gdal, 'UseExceptions', None)
    if use_exceptions is not None:
        use_exceptions()
    return gdal


def list_pdf_pages(path):
    """Nazwy podzbiorow GDAL (stron) dla PDF-a.

    Pusta lista oznacza PDF jednosnej... (GDAL nie tworzy wtedy podzbiorow).
    """
    gdal = _gdal()
    try:
        dataset = gdal.Open(path)
    except RuntimeError:
        return []
    if dataset is None:
        return []
    subs = dataset.GetSubDatasets()
    dataset = None
    return [name for name, _ in subs]


def _page_open(name, dpi):
    """Otwiera strone z ustawionym GDAL_PDF_DPI; zwraca (dataset, poprzednie_DPI)."""
    gdal = _gdal()
    previous = gdal.GetConfigOption('GDAL_PDF_DPI')
    gdal.SetConfigOption('GDAL_PDF_DPI', str(int(dpi)))
    try:
        dataset = gdal.Open(name)
    except RuntimeError:
        dataset = None
    return dataset, previous


def page_size_mm(name, dpi=SIZE_DPI):
    """Format strony w milimetrach (szerokosc, wysokosc)."""
    gdal = _gdal()
    dataset, previous = _page_open(name, dpi)
    if dataset is None:
        gdal.SetConfigOption('GDAL_PDF_DPI', previous)
        return 0.0, 0.0
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    dataset = None
    gdal.SetConfigOption('GDAL_PDF_DPI', previous)
    return width / float(dpi) * 25.4, height / float(dpi) * 25.4


def page_ink_percent(name, dpi=INK_DPI):
    """Pokrycie strony tuszem w procentach (piksele ciemniejsze od INK_THRESHOLD)."""
    gdal = _gdal()
    dataset, previous = _page_open(name, dpi)
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
        dark = int((data < INK_THRESHOLD).sum())
    except (AttributeError, TypeError):
        return 0.0
    if total <= 0:
        return 0.0
    return 100.0 * dark / float(total)


def sheet_area_mm2(name):
    """Powierzchnia arkusza (mm2) dla nazwy formatu, np. 'A3'."""
    key = str(name or '').strip().upper()
    for item in SHEET_MM:
        if item[0] == key:
            return item[1] * item[2]
    return SHEET_MM[1][1] * SHEET_MM[1][2]


def is_drawing_page(name, min_format=DEFAULT_MIN_FORMAT, min_ink=DEFAULT_MIN_INK):
    """Ocena strony: (czy_rysunek, opis_decyzji).

    Rysunki techniczne sa zwykle wieksze niz A4 (A3, A2, A1, A0) - dlatego
    podstawowym kryterium jest format strony. Opcjonalnie (min_ink > 0)
    odrzucane sa takze strony prawie puste.
    """
    width, height = page_size_mm(name)
    area = width * height
    needed = sheet_area_mm2(min_format) * SIZE_TOLERANCE
    opis = '%.0f x %.0f mm' % (width, height)
    if area < needed:
        return False, '%s (mniejsza niż %s)' % (opis, str(min_format).upper())
    if min_ink > 0:
        ink = page_ink_percent(name)
        if ink < float(min_ink):
            return False, '%s, tusz %.2f%% (min. %.2f%%)' % (opis, ink, float(min_ink))
        return True, '%s, tusz %.2f%%' % (opis, ink)
    return True, opis


def parse_page_spec(spec, page_count):
    """Zamienia '1,3,5-8' na liste numerow stron (posortowana, bez powtorzen)."""
    pages = []
    text = str(spec or '').replace(';', ',').replace(' ', ',')
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            first, _, last = part.partition('-')
            try:
                start = int(first)
                stop = int(last)
            except ValueError:
                continue
            if start > stop:
                start, stop = stop, start
            pages.extend(range(start, stop + 1))
        else:
            try:
                pages.append(int(part))
            except ValueError:
                continue
    unique = sorted(set(page for page in pages if 1 <= page <= int(page_count)))
    return unique


def _pages_text(pages, limit=24):
    """Krotki opis listy stron do logu."""
    shown = ', '.join(str(page) for page in pages[:limit])
    if len(pages) > limit:
        shown += ', ...'
    return shown


def plan_pdf_pages(path, page_mode=PAGE_MODE_DRAWINGS, page_spec='',
                   min_format=DEFAULT_MIN_FORMAT, min_ink=DEFAULT_MIN_INK):
    """Ustala, ktore strony PDF-a konwertowac.

    Zwraca (liczba_stron, zadania, pominiete, uwaga):
        zadania   - [(numer_strony, zrodlo_dla_gdal)]
        pominiete - [(numer_strony, powod)]
        uwaga     - dodatkowy komunikat do logu ('' = brak)

    Gdy zaden arkusz nie jest wiekszy niz wybrany format (np. caly PDF to
    rysunki na A4), filtr formatu nie jest uzywany - lepiej przekonwertowac
    wszystkie strony niz nie zapisac nic. Taka sytuacja jest opisana w uwadze.
    """
    subs = list_pdf_pages(path)
    count = len(subs) if subs else 1

    def source(page):
        if subs:
            return subs[page - 1]
        return path

    tasks = []
    skipped = []

    if count <= 1:
        # PDF jednosnej... - zawsze konwertujemy (heurystyki nie maja sensu)
        return count, [(1, source(1))], skipped, ''

    if page_mode == PAGE_MODE_CUSTOM:
        wanted = parse_page_spec(page_spec, count)
        if not wanted:
            wanted = list(range(1, count + 1))
        tasks = [(page, source(page)) for page in wanted]
        note = 'wybrane strony (%d z %d): %s' % (len(wanted), count, _pages_text(wanted))
        return count, tasks, [], note

    if page_mode == PAGE_MODE_ALL:
        for page in range(1, count + 1):
            tasks.append((page, source(page)))
        return count, tasks, skipped, ''

    # tryb "tylko rysunki" - najpierw format strony
    needed = sheet_area_mm2(min_format) * SIZE_TOLERANCE
    bigger = []
    opisy = {}
    for page in range(1, count + 1):
        width, height = page_size_mm(source(page))
        opis = '%.0f x %.0f mm' % (width, height)
        if width * height < needed:
            skipped.append((page, '%s (mniejsza niż %s)' % (opis, str(min_format).upper())))
        else:
            bigger.append(page)
            opisy[page] = opis

    if not bigger:
        note = ('żadna strona nie jest większa niż %s - konwertuję wszystkie strony '
                '(zmień "Min. format rysunku", aby filtrować)' % str(min_format).upper())
        return count, [(page, source(page)) for page in range(1, count + 1)], [], note

    # opcjonalny filtr stron prawie pustych (tylko wśród uznanych za rysunki)
    if min_ink > 0:
        tasks = []
        for page in bigger:
            ink = page_ink_percent(source(page))
            if ink < float(min_ink):
                skipped.append((page, '%s, tusz %.2f%% (min. %.2f%%)' % (
                    opisy[page], ink, float(min_ink))))
            else:
                tasks.append((page, source(page)))
        skipped.sort()
        return count, tasks, skipped, ''

    return count, [(page, source(page)) for page in bigger], skipped, ''


# ----------------------------------------------------------------------
#  Parsowanie komunikatow GDAL
# ----------------------------------------------------------------------
def parse_progress(text, last_pct=-1):
    """Wyciaga procenty z tekstu postepu GDAL, np. "0...10...20...100"."""
    best = last_pct
    for match in _PROGRESS_RE.finditer(text):
        value = int(match.group(1))
        if 0 <= value <= 100 and value > best:
            best = value
    return best


def find_size(text):
    """Wyciaga "W, H" z komunikatu "Input file size is W, H"."""
    match = _SIZE_RE.search(text or '')
    if match:
        return '%s, %s' % (match.group(1), match.group(2))
    return ''


# ----------------------------------------------------------------------
#  Konwersja jednej strony - wersja synchroniczna (Processing)
# ----------------------------------------------------------------------
def run_gdal_sync(gdal_path, src, dst, dpi, timeout_ms=-1):
    """Uruchamia gdal_translate przez QProcess i czeka na koniec.

    timeout_ms = -1 oznacza czekanie bez limitu (QProcess: 0 = nie czekaj).
    Zwraca krotke (ok, kod_wyjscia, rozmiar, pelny_tekst_wyjscia).
    """
    proc = QProcess()
    proc.setProcessChannelMode(_MERGED_CHANNELS)
    proc.start(gdal_path, build_gdal_arguments(dpi, src, dst))

    if not proc.waitForStarted(20000):
        return False, -1, '', 'Nie można uruchomić gdal_translate: %s' % gdal_path

    proc.waitForFinished(timeout_ms)
    text = bytes(proc.readAll()).decode('utf-8', 'replace')
    rc = proc.exitCode() if proc.exitStatus() == _NORMAL_EXIT else -1
    ok = rc == 0 and os.path.isfile(dst)
    return ok, rc, find_size(text), text


def convert_pdf_file(gdal_path, path, base_dst, dpi,
                     page_mode=PAGE_MODE_DRAWINGS, page_spec='',
                     min_format=DEFAULT_MIN_FORMAT, min_ink=DEFAULT_MIN_INK,
                     skip_existing=False, log=None):
    """Konwersja wszystkich wybranych stron jednego PDF-a (wersja synchroniczna).

    Zwraca (udane, bledy, pominiete) - liczby stron.
    """
    emit = log if log is not None else (lambda text: None)
    count, tasks, skipped, note = plan_pdf_pages(path, page_mode, page_spec,
                                                 min_format, min_ink)

    emit('        stron: %d, do konwersji: %d' % (count, len(tasks)))
    if note:
        emit('        %s' % note)
    for page, reason in skipped:
        emit('        str. %d: pominięta (%s)' % (page, reason))
    if not tasks:
        emit('        brak stron do konwersji')
        return 0, 0, 0

    ok_count = 0
    fail_count = 0
    skip_count = 0
    for page, src in tasks:
        dst = page_dest(base_dst, page, count)
        if skip_existing and os.path.isfile(dst):
            emit('        str. %d -> %s : pominięto (plik istnieje)' % (page, os.path.basename(dst)))
            skip_count += 1
            continue
        success, rc, size_info, output = run_gdal_sync(gdal_path, src, dst, dpi)
        if success:
            ok_count += 1
            if size_info:
                emit('        str. %d -> %s : OK (%s px)' % (page, os.path.basename(dst), size_info))
            else:
                emit('        str. %d -> %s : OK' % (page, os.path.basename(dst)))
        else:
            fail_count += 1
            emit('        str. %d -> %s : BŁĄD (kod %d)' % (page, os.path.basename(dst), rc))
            if output:
                tail = '\n'.join(output.strip().splitlines()[-5:])
                emit('            %s' % tail.replace('\n', ' | '))
    return ok_count, fail_count, skip_count


# ----------------------------------------------------------------------
#  Watek konwersji dla okna wtyczki
# ----------------------------------------------------------------------
class ConversionThread(QThread):
    """Konwersja w tle - odpowiednik TConvertThread z wersji Lazarus.

    Sygnaly (zamiast Synchronize):
        fileProgress(int)   - postep biezacego pliku w %
        totalProgress(int)  - postep calosci w %
        statusMessage(str)  - tekst na gornej etykiecie
        logMessage(str)     - wpis do logu
        done(int, int)      - (udane_strony, bledne_strony) po zakonczeniu
    """

    fileProgress = pyqtSignal(int)
    totalProgress = pyqtSignal(int)
    statusMessage = pyqtSignal(str)
    logMessage = pyqtSignal(str)
    done = pyqtSignal(int, int)

    WAIT_MS = 150

    def __init__(self, gdal_path, out_dir, base_in, dpi, files,
                 skip_existing=False, keep_sub=False,
                 page_mode=PAGE_MODE_DRAWINGS, page_spec='',
                 min_format=DEFAULT_MIN_FORMAT, min_ink=DEFAULT_MIN_INK,
                 parent=None):
        super().__init__(parent)
        self.gdal = gdal_path
        self.out_dir = out_dir
        self.base_in = base_in
        self.dpi = int(dpi)
        self.files = list(files)
        self.skip_existing = bool(skip_existing)
        self.keep_sub = bool(keep_sub)
        self.page_mode = page_mode
        self.page_spec = page_spec
        self.min_format = min_format
        self.min_ink = float(min_ink)

        self.count = len(self.files)
        self.cur_pct = 0
        self._stop = False
        self._proc = None
        self.total_pages = 0
        self.done_pages = 0

    # -- sterowanie ----------------------------------------------------
    def request_stop(self):
        """Zadanie zatrzymania - konczy biezacy proces GDAL."""
        self._stop = True
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except RuntimeError:
                # proces zdazyl sie zakonczyc, obiekt Qt jest juz usuniety
                self._proc = None

    # -- pomocnicze ----------------------------------------------------
    def _set_total(self):
        if self.total_pages <= 0:
            return
        pct = int(round(self.done_pages * 100.0 / self.total_pages))
        self.totalProgress.emit(max(0, min(100, pct)))

    def _analyse(self):
        """Faza 1: ustala liste stron do konwersji dla kazdego pliku."""
        plan = []
        for index, src in enumerate(self.files):
            if self._stop:
                break
            self.statusMessage.emit('Analiza stron [%d/%d] %s' % (
                index + 1, self.count, os.path.basename(src)))
            base_dst, dst_dir = build_dest_path(src, self.base_in, self.out_dir, self.keep_sub)
            try:
                count, tasks, skipped, note = plan_pdf_pages(
                    src, self.page_mode, self.page_spec, self.min_format, self.min_ink)
            except (RuntimeError, ValueError, OSError) as exc:
                self.logMessage.emit('%s: nie można odczytać stron (%s)' % (
                    os.path.basename(src), exc))
                count, tasks, skipped, note = 1, [(1, src)], [], ''
            plan.append((src, base_dst, dst_dir, count, tasks, skipped, note))
        return plan

    def _run_one(self, src, dst):
        """Uruchamia gdal_translate dla jednej strony; zwraca (ok, kod, rozmiar)."""
        self.cur_pct = 0
        proc = QProcess()
        proc.setProcessChannelMode(_MERGED_CHANNELS)
        self._proc = proc

        try:
            proc.start(self.gdal, build_gdal_arguments(self.dpi, src, dst))
        except RuntimeError as exc:
            self.logMessage.emit('            BŁĄD: nie można uruchomić gdal_translate (%s)' % exc)
            self._proc = None
            return False, -1, ''

        if not proc.waitForStarted(20000):
            self.logMessage.emit('            BŁĄD: nie można uruchomić gdal_translate')
            self._proc = None
            return False, -1, ''

        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        accum = ''
        last_pct = -1

        while proc.state() != _NOT_RUNNING:
            if self._stop:
                proc.kill()
                proc.waitForFinished(5000)
                break
            if proc.waitForReadyRead(self.WAIT_MS):
                chunk = decoder.decode(bytes(proc.readAll()))
                if chunk:
                    accum += chunk
                    new_pct = parse_progress(accum, last_pct)
                    if new_pct > last_pct:
                        last_pct = new_pct
                        self.cur_pct = new_pct
                        self.fileProgress.emit(new_pct)

        rest = decoder.decode(bytes(proc.readAll()), final=True)
        if rest:
            accum += rest
        proc.waitForFinished(3000)

        if proc.exitStatus() == _NORMAL_EXIT:
            rc = proc.exitCode()
        else:
            rc = -1

        self._proc = None      # QProcess zwolni sie razem z obiektem Pythona

        ok = (not self._stop) and rc == 0 and os.path.isfile(dst)
        return ok, rc, find_size(accum)

    # -- glowna petla --------------------------------------------------
    def run(self):
        ok_count = 0
        fail_count = 0

        plan = self._analyse()
        self.total_pages = sum(len(item[4]) for item in plan)

        for index, (src, base_dst, dst_dir, count, tasks, skipped, note) in enumerate(plan):
            if self._stop:
                break

            self.statusMessage.emit('[%d/%d] %s' % (index + 1, self.count, os.path.basename(src)))
            self.logMessage.emit('[%d/%d] %s  (stron: %d, do konwersji: %d)' % (
                index + 1, self.count, os.path.basename(src), count, len(tasks)))
            if note:
                self.logMessage.emit('        %s' % note)
            for page, reason in skipped:
                self.logMessage.emit('        str. %d: pominięta (%s)' % (page, reason))
            if not tasks:
                self.logMessage.emit('        brak stron do konwersji')
                continue

            try:
                if not os.path.isdir(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                fail_count += len(tasks)
                self.done_pages += len(tasks)
                self.logMessage.emit('        BŁĄD: nie można utworzyć katalogu %s (%s)' % (dst_dir, exc))
                self._set_total()
                continue

            for position, (page, page_src) in enumerate(tasks, start=1):
                if self._stop:
                    break

                dst = page_dest(base_dst, page, count)
                self.statusMessage.emit('[%d/%d] %s  str. %d/%d' % (
                    index + 1, self.count, os.path.basename(src), page, count))
                self.logMessage.emit('        str. %d -> %s' % (page, os.path.basename(dst)))

                if self.skip_existing and os.path.isfile(dst):
                    self.logMessage.emit('            pominięto (plik TIFF już istnieje)')
                    ok_count += 1
                    self.done_pages += 1
                    self.fileProgress.emit(int(position * 100.0 / len(tasks)))
                    self._set_total()
                    continue

                self.cur_pct = 0
                self.fileProgress.emit(int((position - 1) * 100.0 / len(tasks)))
                self._set_total()

                success, rc, size_info = self._run_one(page_src, dst)

                if success:
                    ok_count += 1
                    if size_info:
                        self.logMessage.emit('            OK  (%s px, DPI %d, bezstratnie)' % (
                            size_info, self.dpi))
                    else:
                        self.logMessage.emit('            OK  (DPI %d, bezstratnie)' % self.dpi)
                else:
                    fail_count += 1
                    if self._stop:
                        self.logMessage.emit('            PRZERWANO')
                    else:
                        self.logMessage.emit('            BŁĄD (kod %d)' % rc)

                self.done_pages += 1
                self.fileProgress.emit(int(position * 100.0 / len(tasks)))
                self._set_total()

            self.fileProgress.emit(100)

        self.totalProgress.emit(100)
        self.done.emit(ok_count, fail_count)
