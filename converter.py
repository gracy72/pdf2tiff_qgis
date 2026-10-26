# -*- coding: utf-8 -*-
"""
Konwerter PDF -> TIFF (bezstratny, GDAL) - logika wspolna.

Modul nie tworzy widgetow, wiec korzysta z niego zarowno okno wtyczki
(dialog.py), jak i algorytm Processing (algorithm.py).

Wywoływana komenda jest identyczna jak w programie Laz_PDF_tiff:

    gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff
        -co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER
        "wejscie.pdf" "wyjscie.tif"
"""

import codecs
import glob
import os
import re
import shutil
import subprocess

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

#: CREATE_NO_WINDOW - zeby w Windows nie mrugalo okno konsoli
CREATE_NO_WINDOW = 0x08000000


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
def detect_gdal_translate():
    """Zwraca sciezke do gdal_translate (najlepsze trafienie) lub nazwe programu."""
    candidates = []

    # 1. Program z PATH
    found = shutil.which('gdal_translate')
    if found:
        candidates.append(found)

    # 2. Instalacja QGIS, w ktorej uruchomiona jest wtyczka
    try:
        from qgis.core import QgsApplication
        prefix = QgsApplication.prefixPath()
        candidates.append(os.path.join(prefix, 'bin', 'gdal_translate.exe'))
        candidates.append(os.path.join(prefix, '..', '..', 'bin', 'gdal_translate.exe'))
    except Exception:  # pragma: no cover - poza QGIS
        pass

    # 3. Typowe lokalizacje
    candidates.extend(GDAL_CANDIDATES)

    for path in candidates:
        try:
            if path and os.path.isfile(path):
                return os.path.normpath(path)
        except OSError:
            continue

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
        try:
            names = os.listdir(folder)
        except OSError:
            return []
        for name in names:
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
#  Konwersja jednego pliku - wersja synchroniczna (Processing)
# ----------------------------------------------------------------------
def run_gdal_sync(gdal, src, dst, dpi):
    """Uruchamia gdal_translate i czeka na koniec.

    Zwraca krotke (ok, kod_wyjscia, rozmiar, pelny_tekst_wyjscia).
    """
    args = [gdal] + build_gdal_arguments(dpi, src, dst)
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = CREATE_NO_WINDOW
    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs
        )
    except OSError as exc:
        return False, -1, '', str(exc)

    text = proc.stdout.decode('utf-8', 'replace') if proc.stdout else ''
    ok = proc.returncode == 0 and os.path.isfile(dst)
    return ok, proc.returncode, find_size(text), text


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
        done(int, int)      - (udane, bledy) po zakonczeniu
    """

    fileProgress = pyqtSignal(int)
    totalProgress = pyqtSignal(int)
    statusMessage = pyqtSignal(str)
    logMessage = pyqtSignal(str)
    done = pyqtSignal(int, int)

    WAIT_MS = 150

    def __init__(self, gdal, out_dir, base_in, dpi, files,
                 skip_existing=False, keep_sub=False, parent=None):
        super().__init__(parent)
        self.gdal = gdal
        self.out_dir = out_dir
        self.base_in = base_in
        self.dpi = int(dpi)
        self.files = list(files)
        self.skip_existing = bool(skip_existing)
        self.keep_sub = bool(keep_sub)

        self.count = len(self.files)
        self.cur_pct = 0
        self._stop = False
        self._proc = None

    # -- sterowanie ----------------------------------------------------
    def request_stop(self):
        """Zadanie zatrzymania - konczy biezacy proces GDAL."""
        self._stop = True
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    # -- pomocnicze ----------------------------------------------------
    def _set_total(self, index):
        if self.count <= 0:
            return
        pct = int(round(((index + self.cur_pct / 100.0) / self.count) * 100))
        self.totalProgress.emit(max(0, min(100, pct)))

    def _run_one(self, src, dst, index):
        """Uruchamia gdal_translate dla jednego pliku; zwraca (ok, kod, rozmiar)."""
        self.cur_pct = 0
        proc = QProcess()
        proc.setProcessChannelMode(_MERGED_CHANNELS)
        self._proc = proc

        try:
            proc.start(self.gdal, build_gdal_arguments(self.dpi, src, dst))
        except Exception as exc:
            self.logMessage.emit('        BŁĄD: nie można uruchomić gdal_translate (%s)' % exc)
            self._proc = None
            return False, -1, ''

        if not proc.waitForStarted(20000):
            self.logMessage.emit('        BŁĄD: nie można uruchomić gdal_translate')
            self._proc = None
            return False, -1, ''

        decoder = codecs.getincrementaldecoder('utf-8')('replace')
        accum = ''
        last_pct = -1

        while proc.state() != _NOT_RUNNING:
            if self._stop:
                try:
                    proc.kill()
                    proc.waitForFinished(5000)
                except Exception:
                    pass
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
                        self._set_total(index)

        rest = decoder.decode(bytes(proc.readAll()), final=True)
        if rest:
            accum += rest
        proc.waitForFinished(3000)

        if proc.exitStatus() == _NORMAL_EXIT:
            rc = proc.exitCode()
        else:
            rc = -1

        self._proc = None
        try:
            proc.deleteLater()
        except Exception:
            pass

        ok = (not self._stop) and rc == 0 and os.path.isfile(dst)
        return ok, rc, find_size(accum)

    # -- glowna petla --------------------------------------------------
    def run(self):
        ok_count = 0
        fail_count = 0

        for index, src in enumerate(self.files):
            if self._stop:
                break

            dst, dst_dir = build_dest_path(src, self.base_in, self.out_dir, self.keep_sub)
            try:
                if not os.path.isdir(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                fail_count += 1
                self.logMessage.emit('[%d/%d] %s' % (index + 1, self.count, os.path.basename(src)))
                self.logMessage.emit('        BŁĄD: nie można utworzyć katalogu %s (%s)' % (dst_dir, exc))
                self.cur_pct = 100
                self._set_total(index)
                continue

            self.statusMessage.emit('[%d/%d] %s' % (index + 1, self.count, os.path.basename(src)))
            self.logMessage.emit('[%d/%d] %s  ->  %s' % (
                index + 1, self.count, os.path.basename(src), os.path.basename(dst)))

            if self.skip_existing and os.path.isfile(dst):
                self.logMessage.emit('        pominięto (plik TIFF już istnieje)')
                ok_count += 1
                self.cur_pct = 100
                self.fileProgress.emit(100)
                self._set_total(index)
                continue

            self.cur_pct = 0
            self.fileProgress.emit(0)
            self._set_total(index)

            success, rc, size_info = self._run_one(src, dst, index)

            if success:
                ok_count += 1
                if size_info:
                    self.logMessage.emit('        OK  (%s px, DPI %d, bezstratnie)' % (size_info, self.dpi))
                else:
                    self.logMessage.emit('        OK  (DPI %d, bezstratnie)' % self.dpi)
            else:
                fail_count += 1
                if self._stop:
                    self.logMessage.emit('        PRZERWANO')
                else:
                    self.logMessage.emit('        BŁĄD (kod %d)' % rc)

            self.cur_pct = 100
            self.fileProgress.emit(100)
            self._set_total(index)

        self.done.emit(ok_count, fail_count)
