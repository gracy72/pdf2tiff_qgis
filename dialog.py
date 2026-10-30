# -*- coding: utf-8 -*-
"""
Okno konwertera PDF -> TIFF.

Katalog PDF, katalog TIFF, sciezka gdal_translate, DPI, opcje
"Pomijaj istniejace TIFF" i "Podkatalogi", przyciski START/STOP,
dwa paski postepu (plik i calosc) oraz log na biezaco.

Dodatkowo (wersja 1.1.0) wybor stron PDF: domyslnie konwertowane sa tylko
rysunki (strony wieksze niz A4), do wyboru sa tez wszystkie strony albo
wskazana lista stron.
"""

import os
from datetime import datetime

from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget,
)

from .converter import (
    DEFAULT_MIN_FORMAT, DEFAULT_MIN_INK, PAGE_MODE_ALL, PAGE_MODE_CUSTOM,
    PAGE_MODE_DRAWINGS, SHEET_NAMES, ConversionThread, detect_gdal_translate,
    list_pdf_files,
)

TITLE = 'Konwerter PDF -> TIFF  (bezstratny, GDAL)'

#: Klucze QgsSettings
SET_IN = 'pdf2tiff/in_dir'
SET_OUT = 'pdf2tiff/out_dir'
SET_GDAL = 'pdf2tiff/gdal_translate'
SET_DPI = 'pdf2tiff/dpi'
SET_SKIP = 'pdf2tiff/skip_existing'
SET_SUB = 'pdf2tiff/subfolders'
SET_PAGE_MODE = 'pdf2tiff/page_mode'
SET_PAGE_SPEC = 'pdf2tiff/page_spec'
SET_MIN_FORMAT = 'pdf2tiff/min_format'
SET_MIN_INK = 'pdf2tiff/min_ink'


class PdfToTiffDialog(QDialog):
    """Glowne okno wtyczki."""

    def __init__(self, iface=None, parent=None):
        if parent is None and iface is not None:
            try:
                parent = iface.mainWindow()
            except Exception:
                parent = None
        super().__init__(parent)

        self.iface = iface
        self.thread = None

        self.setWindowTitle(TITLE)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icon.png')))
        self.setMinimumSize(720, 600)
        self.resize(880, 720)

        self._build_ui()
        self._restore_settings()
        self._update_page_widgets()

        self._log('Konwerter PDF -> TIFF (bezstratny). Wskaż katalog z PDF i naciśnij START.')
        self._log('Wskazówka: dla PDF rastrowych 200 DPI = natywna rozdzielczość (1:1, bez utraty jakości).')
        self._log('Kompresja TIFF: DEFLATE (bezstratna).')
        self._log('PDF wielostronicowe: domyślnie zapisywane są tylko rysunki '
                  '(strony większe niż wybrany format), jako nazwa_p01.tif, nazwa_p02.tif, ...')

    # ------------------------------------------------------------------
    #  Budowa interfejsu
    # ------------------------------------------------------------------
    def _build_ui(self):
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)

        # --- Katalog PDF
        self.edit_in = QLineEdit()
        self.btn_in = QPushButton('Wybierz...')
        self.btn_in.setFixedWidth(100)
        self.btn_in.clicked.connect(self._choose_input)
        grid.addWidget(QLabel('Katalog PDF:'), 0, 0)
        grid.addWidget(self.edit_in, 0, 1)
        grid.addWidget(self.btn_in, 0, 2)

        # --- Katalog TIFF
        self.edit_out = QLineEdit()
        self.edit_out.setPlaceholderText('puste = zapis obok plików PDF')
        self.btn_out = QPushButton('Wybierz...')
        self.btn_out.setFixedWidth(100)
        self.btn_out.clicked.connect(self._choose_output)
        grid.addWidget(QLabel('Katalog TIFF:'), 1, 0)
        grid.addWidget(self.edit_out, 1, 1)
        grid.addWidget(self.btn_out, 1, 2)

        # --- gdal_translate
        self.edit_gdal = QLineEdit()
        self.btn_gdal = QPushButton('Wybierz...')
        self.btn_gdal.setFixedWidth(100)
        self.btn_gdal.clicked.connect(self._choose_gdal)
        grid.addWidget(QLabel('gdal_translate:'), 2, 0)
        grid.addWidget(self.edit_gdal, 2, 1)
        grid.addWidget(self.btn_gdal, 2, 2)

        # --- DPI, opcje, START / STOP
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 2400)
        self.spin_dpi.setSingleStep(25)
        self.spin_dpi.setValue(200)
        self.spin_dpi.setFixedWidth(80)

        self.chk_skip = QCheckBox('Pomijaj istniejące TIFF')
        self.chk_skip.setChecked(True)
        self.chk_sub = QCheckBox('Podkatalogi')

        self.btn_start = QPushButton('START')
        self.btn_start.setFixedWidth(165)
        self.btn_start.setFixedHeight(34)
        self.btn_start.setDefault(True)
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton('STOP')
        self.btn_stop.setFixedWidth(165)
        self.btn_stop.setFixedHeight(34)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        options = QWidget()
        row = QHBoxLayout(options)
        row.setContentsMargins(0, 6, 0, 6)
        row.addWidget(QLabel('DPI:'))
        row.addWidget(self.spin_dpi)
        row.addSpacing(14)
        row.addWidget(self.chk_skip)
        row.addSpacing(14)
        row.addWidget(self.chk_sub)
        row.addStretch(1)
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_stop)
        grid.addWidget(options, 3, 0, 1, 3)

        # --- Strony PDF
        self.grp_pages = QGroupBox('Strony PDF')
        pages = QVBoxLayout(self.grp_pages)

        self.rad_drawings = QRadioButton('Tylko rysunki (domyślnie)')
        self.rad_drawings.setChecked(True)
        self.rad_drawings.setToolTip(
            'Zapisuje strony większe niż wybrany format - w typowych PDF-ach\n'
            '(opisówka A4 + rysunki A3/A2/A1/A0) zostają same rysunki.')
        self.rad_all = QRadioButton('Wszystkie strony')
        self.rad_custom = QRadioButton('Wskazane strony:')
        self.rad_drawings.toggled.connect(self._update_page_widgets)
        self.rad_all.toggled.connect(self._update_page_widgets)
        self.rad_custom.toggled.connect(self._update_page_widgets)

        self.edit_pages = QLineEdit()
        self.edit_pages.setPlaceholderText('np. 1,3,5-8   (puste = wszystkie strony)')
        self.edit_pages.setMinimumWidth(220)

        row_pages = QHBoxLayout()
        row_pages.addWidget(self.rad_drawings)
        row_pages.addSpacing(12)
        row_pages.addWidget(self.rad_all)
        row_pages.addSpacing(12)
        row_pages.addWidget(self.rad_custom)
        row_pages.addWidget(self.edit_pages, 1)
        pages.addLayout(row_pages)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(SHEET_NAMES)
        self.cmb_format.setCurrentIndex(SHEET_NAMES.index(DEFAULT_MIN_FORMAT.upper())
                                        if DEFAULT_MIN_FORMAT.upper() in SHEET_NAMES else 1)
        self.cmb_format.setFixedWidth(80)
        self.cmb_format.setToolTip(
            'Minimalny format strony uznawanej za rysunek.\n'
            'A3 = strony większe niż A4 (A3, A2, A1, A0 oraz ich obroty).\n'
            'A4 = bez filtra formatu (wszystkie strony niepuste).')

        self.spin_ink = QDoubleSpinBox()
        self.spin_ink.setRange(0.0, 90.0)
        self.spin_ink.setSingleStep(0.5)
        self.spin_ink.setDecimals(1)
        self.spin_ink.setValue(DEFAULT_MIN_INK)
        self.spin_ink.setFixedWidth(80)
        self.spin_ink.setToolTip(
            'Minimalne pokrycie strony tuszem (%). 0 = filtr wyłączony.\n'
            'Pomaga odrzucić strony puste (np. skany z plamami).')

        row_filters = QHBoxLayout()
        row_filters.addWidget(QLabel('Min. format rysunku:'))
        row_filters.addWidget(self.cmb_format)
        row_filters.addSpacing(18)
        row_filters.addWidget(QLabel('Min. pokrycie tuszem (%):'))
        row_filters.addWidget(self.spin_ink)
        row_filters.addStretch(1)
        pages.addLayout(row_filters)

        self.lbl_pages_info = QLabel(
            'Rysunek = strona większa niż wybrany format; PDF jednostronicowe są zawsze konwertowane. '
            'Każda decyzja jest zapisywana w logu.')
        self.lbl_pages_info.setWordWrap(True)
        pages.addWidget(self.lbl_pages_info)

        grid.addWidget(self.grp_pages, 4, 0, 1, 3)

        # --- status, paski postepu, log
        self.lbl_status = QLabel('Gotowy.')

        self.pb_file = QProgressBar()
        self.pb_file.setRange(0, 100)
        self.pb_file.setValue(0)
        self.pb_file.setToolTip('Postęp bieżącego pliku')

        self.pb_total = QProgressBar()
        self.pb_total.setRange(0, 100)
        self.pb_total.setValue(0)
        self.pb_total.setToolTip('Postęp całej konwersji')

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setFont(QFont('Consolas'))

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.pb_file)
        layout.addWidget(self.pb_total)
        layout.addWidget(self.log, 1)

    def _update_page_widgets(self):
        """Odblokowuje tylko te ustawienia stron, ktore maja znaczenie w danym trybie."""
        drawings = self.rad_drawings.isChecked()
        custom = self.rad_custom.isChecked()
        self.cmb_format.setEnabled(drawings)
        self.spin_ink.setEnabled(drawings)
        self.edit_pages.setEnabled(custom)

    def _page_mode(self):
        if self.rad_all.isChecked():
            return PAGE_MODE_ALL
        if self.rad_custom.isChecked():
            return PAGE_MODE_CUSTOM
        return PAGE_MODE_DRAWINGS

    def _page_mode_text(self):
        mode = self._page_mode()
        if mode == PAGE_MODE_ALL:
            return 'wszystkie strony'
        if mode == PAGE_MODE_CUSTOM:
            return 'wskazane strony: %s' % (self.edit_pages.text().strip() or 'wszystkie')
        return 'tylko rysunki (min. format %s)' % self.cmb_format.currentText()

    # ------------------------------------------------------------------
    #  Ustawienia (zapamietywanie pol miedzy uruchomieniami)
    # ------------------------------------------------------------------
    def _restore_settings(self):
        s = QgsSettings()
        self.edit_in.setText(s.value(SET_IN, '', type=str))
        self.edit_out.setText(s.value(SET_OUT, '', type=str))
        gdal = s.value(SET_GDAL, '', type=str)
        if not gdal or not os.path.isfile(gdal):
            gdal = detect_gdal_translate()
        self.edit_gdal.setText(gdal)
        try:
            self.spin_dpi.setValue(int(s.value(SET_DPI, 200)))
        except (TypeError, ValueError):
            self.spin_dpi.setValue(200)
        self.chk_skip.setChecked(self._as_bool(s.value(SET_SKIP, True)))
        self.chk_sub.setChecked(self._as_bool(s.value(SET_SUB, False)))

        mode = str(s.value(SET_PAGE_MODE, PAGE_MODE_DRAWINGS) or PAGE_MODE_DRAWINGS)
        if mode == PAGE_MODE_ALL:
            self.rad_all.setChecked(True)
        elif mode == PAGE_MODE_CUSTOM:
            self.rad_custom.setChecked(True)
        else:
            self.rad_drawings.setChecked(True)
        self.edit_pages.setText(s.value(SET_PAGE_SPEC, '', type=str))
        fmt = str(s.value(SET_MIN_FORMAT, DEFAULT_MIN_FORMAT) or DEFAULT_MIN_FORMAT).upper()
        if fmt in SHEET_NAMES:
            self.cmb_format.setCurrentIndex(SHEET_NAMES.index(fmt))
        try:
            self.spin_ink.setValue(float(s.value(SET_MIN_INK, DEFAULT_MIN_INK)))
        except (TypeError, ValueError):
            self.spin_ink.setValue(DEFAULT_MIN_INK)

    def _save_settings(self):
        s = QgsSettings()
        s.setValue(SET_IN, self.edit_in.text().strip())
        s.setValue(SET_OUT, self.edit_out.text().strip())
        s.setValue(SET_GDAL, self.edit_gdal.text().strip())
        s.setValue(SET_DPI, self.spin_dpi.value())
        s.setValue(SET_SKIP, self.chk_skip.isChecked())
        s.setValue(SET_SUB, self.chk_sub.isChecked())
        s.setValue(SET_PAGE_MODE, self._page_mode())
        s.setValue(SET_PAGE_SPEC, self.edit_pages.text().strip())
        s.setValue(SET_MIN_FORMAT, self.cmb_format.currentText())
        s.setValue(SET_MIN_INK, self.spin_ink.value())

    @staticmethod
    def _as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('1', 'true', 'yes', 'tak')

    # ------------------------------------------------------------------
    #  Wybor katalogow / programu
    # ------------------------------------------------------------------
    def _choose_input(self):
        start = self.edit_in.text().strip()
        if not os.path.isdir(start):
            start = os.path.expanduser('~')
        folder = QFileDialog.getExistingDirectory(self, 'Wybierz katalog z plikami PDF', start)
        if folder:
            self.edit_in.setText(os.path.normpath(folder))

    def _choose_output(self):
        start = self.edit_out.text().strip()
        if not os.path.isdir(start):
            start = self.edit_in.text().strip()
        if not os.path.isdir(start):
            start = os.path.expanduser('~')
        folder = QFileDialog.getExistingDirectory(self, 'Wybierz katalog docelowy na pliki TIFF', start)
        if folder:
            self.edit_out.setText(os.path.normpath(folder))

    def _choose_gdal(self):
        start = os.path.dirname(self.edit_gdal.text().strip())
        if not os.path.isdir(start):
            start = os.path.expanduser('~')
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Wskaż program gdal_translate.exe',
            start,
            'gdal_translate (gdal_translate.exe);;Programy (*.exe);;Wszystkie pliki (*)'
        )
        if path:
            self.edit_gdal.setText(os.path.normpath(path))

    # ------------------------------------------------------------------
    #  Pomocnicze
    # ------------------------------------------------------------------
    def _log(self, text):
        self.log.appendPlainText('%s  %s' % (datetime.now().strftime('%H:%M:%S'), text))

    def _set_status(self, text):
        self.lbl_status.setText(text)

    def _set_busy(self, busy):
        for widget in (self.btn_start, self.btn_in, self.btn_out, self.btn_gdal,
                       self.edit_in, self.edit_out, self.edit_gdal,
                       self.spin_dpi, self.chk_skip, self.chk_sub,
                       self.rad_drawings, self.rad_all, self.rad_custom,
                       self.cmb_format, self.spin_ink, self.edit_pages):
            widget.setEnabled(not busy)
        if not busy:
            self._update_page_widgets()
        self.btn_stop.setEnabled(busy)

    # ------------------------------------------------------------------
    #  START / STOP / KONIEC
    # ------------------------------------------------------------------
    def _start(self):
        if self.thread is not None:
            return

        gdal = self.edit_gdal.text().strip()
        if not os.path.isfile(gdal):
            QMessageBox.warning(
                self, TITLE,
                'Nie znaleziono gdal_translate:\n%s\n\n'
                'Wskaż poprawną ścieżkę do gdal_translate.exe.' % (gdal or '(pusta ścieżka)'))
            return

        in_dir = self.edit_in.text().strip()
        if not os.path.isdir(in_dir):
            QMessageBox.warning(self, TITLE, 'Wybierz istniejący katalog z plikami PDF.')
            return

        out_dir = self.edit_out.text().strip() or in_dir
        files = list_pdf_files(in_dir, self.chk_sub.isChecked())
        if not files:
            QMessageBox.information(self, TITLE, 'W katalogu nie znaleziono plików *.pdf.')
            return

        self._save_settings()

        self.log.clear()
        self._log('=== START ===')
        self._log('Plików do konwersji : %d' % len(files))
        self._log('Katalog źródłowy    : %s' % in_dir)
        self._log('Katalog docelowy    : %s' % out_dir)
        self._log('DPI / kompresja     : %d / DEFLATE (bezstratna)' % self.spin_dpi.value())
        self._log('Strony              : %s' % self._page_mode_text())
        if self._page_mode() == PAGE_MODE_DRAWINGS and self.spin_ink.value() > 0:
            self._log('Min. pokrycie tuszem: %.1f%%' % self.spin_ink.value())
        if self.chk_skip.isChecked():
            self._log('Tryb                : pomijanie istniejących TIFF')

        self.pb_file.setValue(0)
        self.pb_total.setValue(0)
        self._set_busy(True)

        self.thread = ConversionThread(
            gdal,
            out_dir,
            in_dir,
            self.spin_dpi.value(),
            files,
            self.chk_skip.isChecked(),
            self.chk_sub.isChecked(),
            self._page_mode(),
            self.edit_pages.text().strip(),
            self.cmb_format.currentText(),
            self.spin_ink.value(),
        )
        self.thread.fileProgress.connect(self.pb_file.setValue)
        self.thread.totalProgress.connect(self.pb_total.setValue)
        self.thread.statusMessage.connect(self._set_status)
        self.thread.logMessage.connect(self._log)
        self.thread.done.connect(self._on_done)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _stop(self):
        if self.thread is not None:
            self._log('Żądanie zatrzymania...')
            self.thread.request_stop()

    def _on_done(self, ok_count, fail_count):
        self.pb_file.setValue(100)
        self.pb_total.setValue(100)
        self._log('=== KONIEC: udane strony=%d, błędy=%d ===' % (ok_count, fail_count))
        self._set_status('Zakończono. Udane strony: %d, błędy: %d.' % (ok_count, fail_count))
        self._set_busy(False)
        self.thread = None
        QMessageBox.information(
            self, TITLE,
            'Konwersja zakończona.\nUdane strony: %d\nBłędy: %d' % (ok_count, fail_count))

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self._save_settings()
        if self.thread is not None:
            self.thread.request_stop()
            self.thread.wait(10000)
            self.thread = None
        super().closeEvent(event)
