# -*- coding: utf-8 -*-
"""
Algorytm Processing: konwersja plikow PDF z katalogu do TIFF.

Dzieki temu konwersje mozna uruchamiac z Panelu przetwarzania, z modeli
(Graphic Modeler) i z wiersza polecen qgis_process.

Obslugiwane sa PDF wielostronicowe - wybor stron dziala tak samo jak w oknie
wtyczki: tylko rysunki (domyslnie), wszystkie strony albo wskazana lista.
"""

import os

from qgis.core import (
    QgsProcessingAlgorithm, QgsProcessingException, QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum, QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination, QgsProcessingParameterNumber,
    QgsProcessingParameterString, QgsProcessingProvider,
)

from .converter import (
    DEFAULT_MIN_FORMAT, DEFAULT_MIN_INK, PAGE_MODE_ALL, PAGE_MODE_CUSTOM,
    PAGE_MODE_DRAWINGS, SHEET_NAMES, build_dest_path, convert_pdf_file,
    detect_gdal_translate, list_pdf_files,
)


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

#: Etykiety trybow stron (kolejnosc = wartosci listy wyboru)
PAGE_MODE_LABELS = [
    'tylko rysunki (domyślnie)',
    'wszystkie strony',
    'wskazane strony',
]
PAGE_MODE_VALUES = [PAGE_MODE_DRAWINGS, PAGE_MODE_ALL, PAGE_MODE_CUSTOM]


class PdfToTiffAlgorithm(QgsProcessingAlgorithm):
    """PDF -> TIFF (bezstratnie, GDAL)."""

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
        return 'Konwertuj PDF do TIFF (bezstratnie)'

    def group(self):
        return 'Konwersja PDF'

    def groupId(self):
        return 'pdf2tiff'

    def shortHelpString(self):
        return (
            'Konwertuje pliki *.pdf z katalogu do plików *.tif przy pomocy '
            'gdal_translate. Renderowanie w zadanym DPI i kompresja bezstratna DEFLATE, '
            'więc jakość nie jest tracona.\n\n'
            'PDF wielostronicowe: każda strona jest osobnym podzbiorem GDAL '
            '("PDF:<numer>:<plik>"). Domyślnie zapisywane są tylko rysunki, czyli strony '
            'większe niż wybrany format (A3 = większe niż A4) - opisówki A4 są pomijane. '
            'Można też wybrać wszystkie strony albo listę stron (np. 1,3,5-8).\n\n'
            'Nazwy plików: PDF jednostronicowy -> "nazwa.tif", PDF wielostronicowy -> '
            '"nazwa_p01.tif", "nazwa_p02.tif", ...\n\n'
            'Dla PDF rastrowych (np. PZT z CAD) 200 DPI = natywna rozdzielczość, czyli '
            'odtworzenie 1:1. Wyższe DPI (400/600) to już interpolacja.\n\n'
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
        self.addParameter(QgsProcessingParameterEnum(
            self.PAGE_MODE, 'Strony PDF', options=PAGE_MODE_LABELS,
            defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.PAGES, 'Wskazane strony (np. 1,3,5-8; puste = wszystkie)',
            defaultValue='', optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.MIN_FORMAT, 'Minimalny format rysunku',
            options=SHEET_NAMES,
            defaultValue=SHEET_NAMES.index(DEFAULT_MIN_FORMAT.upper())))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_INK, 'Minimalne pokrycie tuszem %% (0 = bez filtra)',
            type=_NUMBER_DOUBLE, defaultValue=DEFAULT_MIN_INK,
            minValue=0.0, maxValue=90.0))
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

        mode_index = self.parameterAsEnum(parameters, self.PAGE_MODE, context)
        if 0 <= mode_index < len(PAGE_MODE_VALUES):
            page_mode = PAGE_MODE_VALUES[mode_index]
        else:
            page_mode = PAGE_MODE_DRAWINGS
        page_spec = self.parameterAsString(parameters, self.PAGES, context).strip()

        format_index = self.parameterAsEnum(parameters, self.MIN_FORMAT, context)
        if 0 <= format_index < len(SHEET_NAMES):
            min_format = SHEET_NAMES[format_index]
        else:
            min_format = DEFAULT_MIN_FORMAT
        min_ink = self.parameterAsDouble(parameters, self.MIN_INK, context)

        files = list_pdf_files(in_dir, recursive)
        if not files:
            raise QgsProcessingException('W katalogu nie znaleziono plików *.pdf.')

        feedback.pushInfo('gdal_translate : %s' % gdal)
        feedback.pushInfo('Katalog źródłowy: %s' % in_dir)
        feedback.pushInfo('Katalog docelowy: %s' % out_dir)
        feedback.pushInfo('DPI / kompresja : %d / DEFLATE (bezstratna)' % dpi)
        feedback.pushInfo('Tryb stron      : %s%s' % (
            PAGE_MODE_LABELS[max(0, min(mode_index, len(PAGE_MODE_LABELS) - 1))],
            '' if page_mode != PAGE_MODE_DRAWINGS else
            ' (min. format %s, min. tusz %.1f%%)' % (min_format, min_ink)))
        feedback.pushInfo('Plików do konwersji: %d' % len(files))

        ok_count = 0
        fail_count = 0
        skipped_count = 0
        total = len(files)

        for index, src in enumerate(files):
            if feedback.isCanceled():
                feedback.pushInfo('Przerwano na żądanie użytkownika.')
                break

            feedback.setProgress(int(index * 100.0 / total))

            base_dst, dst_dir = build_dest_path(src, in_dir, out_dir, recursive)
            feedback.pushInfo('[%d/%d] %s' % (index + 1, total, os.path.basename(src)))

            try:
                os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                fail_count += 1
                feedback.reportError('Nie można utworzyć katalogu %s (%s)' % (dst_dir, exc),
                                     fatalError=False)
                continue

            ok, fail, skipped = convert_pdf_file(
                gdal, src, base_dst, dpi,
                page_mode, page_spec, min_format, min_ink,
                skip_existing, feedback.pushInfo)
            ok_count += ok
            fail_count += fail
            skipped_count += skipped

        feedback.setProgress(100)
        feedback.pushInfo('=== KONIEC: udane strony=%d, błędy=%d, pominięte=%d ===' % (
            ok_count, fail_count, skipped_count))
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
