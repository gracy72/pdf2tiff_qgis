# -*- coding: utf-8 -*-
"""Test wtyczki bez okna QGIS (offscreen): import, okno, watek, algorytm Processing.

Uruchomienie:
    C:\\QGIS\\bin\\python-qgis.bat tools\\test_headless.py
"""

import os
import shutil
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PLUGIN_DIR))          # katalog nadrzedny -> pakiet
PKG = os.path.basename(PLUGIN_DIR)                       # nazwa pakietu = nazwa katalogu

from qgis.core import QgsApplication  # noqa: E402

app = QgsApplication([], False)
QgsApplication.setPrefixPath(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:\QGIS\apps\qgis')), True)
app.initQgis()
from qgis.core import Qgis  # noqa: E402

print('QGIS:', Qgis.QGIS_VERSION)
print('pakiet:', PKG)


def log(*args):
    print(*args)
    sys.stdout.flush()


# ---------------------------------------------------------------- import
import importlib  # noqa: E402

pkg = importlib.import_module(PKG)
factory = getattr(pkg, 'classFactory')
plugin_cls = factory(None).__class__
log('classFactory OK ->', plugin_cls.__name__)

conv = importlib.import_module(PKG + '.converter')
log('wykryty gdal_translate:', conv.detect_gdal_translate())

# ---------------------------------------------------------------- okno
dlg_mod = importlib.import_module(PKG + '.dialog')
dlg = dlg_mod.PdfToTiffDialog()
log('okno OK: tytul =', dlg.windowTitle())
log('  gdal w polu      :', dlg.edit_gdal.text())
log('  DPI              :', dlg.spin_dpi.value())
log('  pomijaj istniejace:', dlg.chk_skip.isChecked(), ' podkatalogi:', dlg.chk_sub.isChecked())
log('  widgety          :', len(dlg.findChildren(object)))

# ---------------------------------------------------------------- konwersja
sample = os.path.join(os.environ['USERPROFILE'], 'Desktop', 'D19950078Lj.pdf')
work = tempfile.mkdtemp(prefix='pdf2tiff_test_')
src_dir = os.path.join(work, 'we')
out_dir = os.path.join(work, 'wy')
os.makedirs(src_dir)
os.makedirs(os.path.join(src_dir, 'pod'))
if os.path.isfile(sample):
    shutil.copy2(sample, os.path.join(src_dir, 'test1.pdf'))
    shutil.copy2(sample, os.path.join(src_dir, 'pod', 'test2.pdf'))
else:
    log('UWAGA: brak pliku testowego', sample)

log('pliki PDF w katalogu:', len(conv.list_pdf_files(src_dir, True)))
dst, dst_dir = conv.build_dest_path(os.path.join(src_dir, 'pod', 'test2.pdf'), src_dir, out_dir, True)
log('sciezka docelowa (podkatalogi):', dst)
log('argumenty GDAL:', ' '.join(conv.build_gdal_arguments(200, 'a.pdf', 'a.tif')))
log('parse_progress("0...10...20...100") ->', conv.parse_progress('0...10...20...100'))
log('find_size("Input file size is 7016, 4961") ->', conv.find_size('Input file size is 7016, 4961'))

if os.path.isfile(os.path.join(src_dir, 'test1.pdf')):
    from qgis.PyQt.QtCore import QEventLoop, QTimer

    thread = conv.ConversionThread(
        conv.detect_gdal_translate(), out_dir, src_dir, 200,
        conv.list_pdf_files(src_dir, True), False, True,
        conv.PAGE_MODE_CUSTOM, '1', 'A3', 0.0)

    loop = QEventLoop()
    result = {}

    def on_done(ok, fail):
        result['ok'] = ok
        result['fail'] = fail
        QTimer.singleShot(0, loop.quit)

    thread.logMessage.connect(lambda s: log('   LOG:', s))
    thread.done.connect(on_done)
    thread.start()
    QTimer.singleShot(180000, loop.quit)
    loop.exec()
    thread.wait(5000)

    log('wynik watku: udane=%s, bledy=%s' % (result.get('ok'), result.get('fail')))
    for root, _dirs, files in os.walk(out_dir):
        for name in files:
            path = os.path.join(root, name)
            log('   plik:', os.path.relpath(path, out_dir), os.path.getsize(path), 'B')

    # ------------------------------------------------------- algorytm Processing
    alg_mod = importlib.import_module(PKG + '.algorithm')
    alg = alg_mod.PdfToTiffAlgorithm()
    alg.initAlgorithm()
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback
    ctx = QgsProcessingContext()
    fb = QgsProcessingFeedback()

    class Fb(QgsProcessingFeedback):
        def pushInfo(self, msg):
            log('   ALG:', msg)

        def pushWarning(self, msg):
            log('   ALG!:', msg)

    res = alg.processAlgorithm({
        'INPUT_FOLDER': src_dir,
        'OUTPUT_FOLDER': os.path.join(work, 'wy2'),
        'DPI': 150,
        'PAGE_MODE': 2,
        'PAGES': '1',
        'MIN_FORMAT': 1,
        'MIN_INK': 0.0,
        'SKIP_EXISTING': True,
        'RECURSIVE': True,
        'GDAL_TRANSLATE': '',
    }, ctx, Fb())
    log('algorytm zwrocil:', res)

    # ------------------------------------------------------- algorytm z pliku .py
    script = os.path.join(PLUGIN_DIR, 'skrypt_pdf2tiff.py')
    sys.path.insert(0, PLUGIN_DIR)
    import importlib.util
    spec = importlib.util.spec_from_file_location('skrypt_pdf2tiff', script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out3 = os.path.join(work, 'skrypt')
    stats = mod.konwertuj_pdf_do_tiff(src_dir, out3, dpi=150, podkatalogi=True,
                                      pomijaj_istniejace=False, log=lambda s: log('   SKR:', s),
                                      tryb_stron=mod.TRYB_WYBRANE, lista_stron='1')
    log('skrypt - statystyki:', stats)

# ---------------------------------------------------------------- PDF wielostronicowy
log('--- PDF wielostronicowy ---')
BIG = r'd:\Projekty\99999 Temp\temp_pdf\PB P&R Leśnica_zatwierdzony_PnB.pdf'
if os.path.isfile(BIG):
    strona = conv.page_dest(os.path.join(work, 'PB.tif'), 38, 172)
    log('  nazwa strony 38/172:', os.path.basename(strona))
    log('  nazwa strony 1/7   :', os.path.basename(conv.page_dest('a.tif', 1, 7)))
    log('  nazwa PDF 1-stron. :', os.path.basename(conv.page_dest('a.tif', 1, 1)))
    log('  parse_page_spec("1,3,5-8") dla 172 stron:',
        conv.parse_page_spec('1,3,5-8', 172)[:12])
    liczba, zadania, pominiete, uwaga = conv.plan_pdf_pages(BIG, conv.PAGE_MODE_DRAWINGS, '',
                                                           'A3', 0.0)
    log('  tryb rysunki: stron=%d, rysunkow=%d, pominieto=%d' % (
        liczba, len(zadania), len(pominiete)))
    log('  uwaga:', uwaga or '(brak)')
    log('  strony rysunkow (pierwsze 12):', [p for p, _ in zadania[:12]])
    log('  przyklad pominiecia:', pominiete[0] if pominiete else None)

    rozmiar_test = os.path.join(work, 'we', 'test1.pdf')
    if os.path.isfile(rozmiar_test):
        liczba2, zadania2, pominiete2, uwaga2 = conv.plan_pdf_pages(
            rozmiar_test, conv.PAGE_MODE_DRAWINGS, '', 'A3', 0.0)
        log('  PDF z samymi A4 (test1.pdf): stron=%d, zadania=%d' % (liczba2, len(zadania2)))
        log('  uwaga:', uwaga2 or '(brak)')

    mp_out = os.path.join(work, 'mp')
    os.makedirs(mp_out)
    ok, fail, skip = conv.convert_pdf_file(
        conv.detect_gdal_translate(), BIG, os.path.join(mp_out, 'PB.tif'), 72,
        conv.PAGE_MODE_CUSTOM, '1,38', 'A3', 0.0, False,
        lambda s: log('   MP:', s))
    log('  konwersja stron 1 i 38: udane=%d, bledy=%d, pominiete=%d' % (ok, fail, skip))
    for name in sorted(os.listdir(mp_out)):
        log('   plik:', name, os.path.getsize(os.path.join(mp_out, name)), 'B')
else:
    log('  brak pliku testowego:', BIG)

# ---------------------------------------------------------------- cykl zycia wtyczki
log('--- cykl zycia wtyczki (sztuczny iface) ---')


class FakeIface(object):
    def __init__(self):
        from qgis.PyQt.QtWidgets import QWidget
        self.win = QWidget()
        self.calls = []

    def mainWindow(self):
        return self.win

    def addToolBarIcon(self, action):
        self.calls.append('addToolBarIcon')

    def removeToolBarIcon(self, action):
        self.calls.append('removeToolBarIcon')

    def addPluginToMenu(self, menu, action):
        self.calls.append('addPluginToMenu')

    def removePluginMenu(self, menu, action):
        self.calls.append('removePluginMenu')


fake = FakeIface()
plugin = factory(fake)
plugin.initGui()
log('  initGui -> wywolania iface:', fake.calls)
log('  akcja istnieje:', plugin.action is not None)
log('  akcja widoczna:', plugin.action.isVisible() if plugin.action else None)
provider = QgsApplication.processingRegistry().providerById('pdf2tiff')
log('  provider w Processing:', provider is not None,
    '| algorytmy:', [a.name() for a in provider.algorithms()] if provider else [])
plugin.run()
log('  okno po run():', plugin.dialog is not None)
plugin.unload()
log('  po unload:', fake.calls[-2:],
    '| provider:', QgsApplication.processingRegistry().providerById('pdf2tiff'))

shutil.rmtree(work, ignore_errors=True)
app.exitQgis()
log('=== TEST ZAKONCZONY ===')
