# -*- coding: utf-8 -*-
"""
Algorytm Processing: konwersja wszystkich plikow PDF z katalogu do TIFF.

Dzieki temu konwersje mozna uruchamiac z Panelu przetwarzania, z modeli
(Graphic Modeler) i z wiersza polecen qgis_process.
"""

import os

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterBoolean,
    QgsProcessingParameterFile, QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber, QgsProcessingProvider,
)

from .converter import (
    build_dest_path, detect_gdal_translate, list_pdf_files, run_gdal_sync,
)

# Qt5/Qt6 i QGIS 3/QGIS 4 - numery typow parametrow roznia sie zapisem
try:
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Integer
except AttributeError:  # QGIS 4 / PyQt6
    _NUMBER_INTEGER = QgsProcessingParameterNumber.Type.Integer

try:
    _FILE_FOLDER = QgsProcessingParameterFile.Folder
    _FILE_FILE = QgsProcessingParameterFile.File
except AttributeError:  # QGIS 4 / PyQt6
    _FILE_FOLDER = QgsProcessingParameterFile.Behavior.Folder
    _FILE_FILE = QgsProcessingParameterFile.Behavior.File


class PdfToTiffAlgorithm(QgsProcessingAlgorithm):
    """PDF -> TIFF (bezstratnie, GDAL)."""

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
            'gdal_translate. Renderowanie w zadanym DPI i kompresja bezstratna DEFLATE, '
            'więc jakość nie jest tracona.\n\n'
            'Dla PDF rastrowych (np. PZT z CAD) 200 DPI = natywna rozdzielczość, czyli '
            'odtworzenie 1:1. Wyższe DPI (400/600) to już interpolacja - gładsze, ale bez '
            'nowego detalu.\n\n'
            'Wywoływana komenda:\n'
            'gdal_translate --config GDAL_PDF_DPI <DPI> -of GTiff '
            '-co COMPRESS=DEFLATE -co PREDICTOR=2 -co TILED=YES -co BIGTIFF=IF_SAFER '
            '"wejście.pdf" "wyjście.tif"'
        )

    def createInstance(self):
        return PdfToTiffAlgorithm()

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

        files = list_pdf_files(in_dir, recursive)
        if not files:
            raise QgsProcessingException('W katalogu nie znaleziono plików *.pdf.')

        feedback.pushInfo('gdal_translate : %s' % gdal)
        feedback.pushInfo('Katalog źródłowy: %s' % in_dir)
        feedback.pushInfo('Katalog docelowy: %s' % out_dir)
        feedback.pushInfo('DPI / kompresja : %d / DEFLATE (bezstratna)' % dpi)
        feedback.pushInfo('Plików do konwersji: %d' % len(files))

        ok_count = 0
        fail_count = 0
        total = len(files)

        for index, src in enumerate(files):
            if feedback.isCanceled():
                feedback.pushInfo('Przerwano na żądanie użytkownika.')
                break

            feedback.setProgress(int(index * 100.0 / total))

            dst, dst_dir = build_dest_path(src, in_dir, out_dir, recursive)
            feedback.pushInfo('[%d/%d] %s  ->  %s' % (
                index + 1, total, os.path.basename(src), os.path.basename(dst)))

            if skip_existing and os.path.isfile(dst):
                feedback.pushInfo('        pominięto (plik TIFF już istnieje)')
                ok_count += 1
                continue

            try:
                os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                fail_count += 1
                feedback.reportError('Nie można utworzyć katalogu %s (%s)' % (dst_dir, exc), fatalError=False)
                continue

            success, rc, size_info, output = run_gdal_sync(gdal, src, dst, dpi)
            if success:
                ok_count += 1
                if size_info:
                    feedback.pushInfo('        OK  (%s px, DPI %d, bezstratnie)' % (size_info, dpi))
                else:
                    feedback.pushInfo('        OK  (DPI %d, bezstratnie)' % dpi)
            else:
                fail_count += 1
                feedback.pushInfo('        BŁĄD (kod %d)' % rc)
                if output:
                    tail = '\n'.join(output.strip().splitlines()[-5:])
                    feedback.reportError('gdal_translate: %s' % tail, fatalError=False)

        feedback.setProgress(100)
        feedback.pushInfo('=== KONIEC: udane=%d, błędy=%d ===' % (ok_count, fail_count))
        return {self.OUTPUT_FOLDER: out_dir}


class PdfToTiffProvider(QgsProcessingProvider):
    """Dostawca algorytmow PDF -> TIFF."""

    def id(self):
        return 'pdf2tiff'

    def name(self):
        return 'PDF -> TIFF (GDAL)'

    def longDescription(self):
        return 'Konwersja PDF do GeoTIFF (bezstratna, gdal_translate).'

    def icon(self):
        from qgis.PyQt.QtGui import QIcon
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))

    def loadAlgorithms(self):
        self.addAlgorithm(PdfToTiffAlgorithm())
