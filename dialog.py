# -*- coding: utf-8 -*-
"""
Okno konwertera PDF -> TIFF - odpowiednik formularza TForm1 z wersji Lazarus.

Uklad, etykiety i zachowanie sa takie same jak w programie Laz_PDF_tiff:
katalog PDF, katalog TIFF, sciezka gdal_translate, DPI, opcje
"Pomijaj istniejace TIFF" i "Podkatalogi", przyciski START/STOP,
dwa paski postepu (plik i calosc) oraz log na biezaco.
"""

import os
from datetime import datetime

from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from .converter import ConversionThread, detect_gdal_translate, list_pdf_files

TITLE = 'Konwerter PDF -> TIFF  (bezstratny, GDAL)'

#: Klucze QgsSettings
SET_IN = 'pdf2tiff/in_dir'
SET_OUT = 'pdf2tiff/out_dir'
SET_GDAL = 'pdf2tiff/gdal_translate'
SET_DPI = 'pdf2tiff/dpi'
SET_SKIP = 'pdf2tiff/skip_existing'
SET_SUB = 'pdf2tiff/subfolders'


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
        self.setMinimumSize(700, 520)
        self.resize(818, 646)

        self._build_ui()
        self._restore_settings()

        self._log('Konwerter PDF -> TIFF (bezstratny). Wskaż katalog z PDF i naciśnij START.')
        self._log('Wskazówka: dla PDF rastrowych 200 DPI = natywna rozdzielczość (1:1, bez utraty jakości).')
        self._log('Kompresja TIFF: DEFLATE (bezstratna).')

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

    def _save_settings(self):
        s = QgsSettings()
        s.setValue(SET_IN, self.edit_in.text().strip())
        s.setValue(SET_OUT, self.edit_out.text().strip())
        s.setValue(SET_GDAL, self.edit_gdal.text().strip())
        s.setValue(SET_DPI, self.spin_dpi.value())
        s.setValue(SET_SKIP, self.chk_skip.isChecked())
        s.setValue(SET_SUB, self.chk_sub.isChecked())

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
                       self.spin_dpi, self.chk_skip, self.chk_sub):
            widget.setEnabled(not busy)
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
        self._log('=== KONIEC: udane=%d, błędy=%d ===' % (ok_count, fail_count))
        self._set_status('Zakończono. Udane: %d, błędy: %d.' % (ok_count, fail_count))
        self._set_busy(False)
        self.thread = None
        QMessageBox.information(
            self, TITLE,
            'Konwersja zakończona.\nUdane: %d\nBłędy: %d' % (ok_count, fail_count))

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self._save_settings()
        if self.thread is not None:
            self.thread.request_stop()
            self.thread.wait(10000)
            self.thread = None
        super().closeEvent(event)
