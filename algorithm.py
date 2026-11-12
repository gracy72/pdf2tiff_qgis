# -*- coding: utf-8 -*-
"""
Algorytm Processing: konwersja plikow PDF z katalogu do TIFF.

Dzieki temu konwersje mozna uruchamiac z Panelu przetwarzania, z modeli
(Graphic Modeler) i z wiersza polecen qgis_process.

Obslugiwane sa PDF wielostronicowe - wybor stron dziala tak samo jak w oknie
wtyczki: tylko rysunki (domyslnie), wszystkie strony albo wskazana lista.
Nazwy i opisy parametrow sa tlumaczone (i18n.py).
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
    detect_gdal_translate, list_pdf_files, page_mode_labels,
)
from .i18n import tr


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

#: Wartosci listy wyboru trybu stron (kolejnosc = etykiety z i18n)
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
        return tr('alg_name')

    def group(self):
        return tr('alg_group')

    def groupId(self):
        return 'pdf2tiff'

    def shortHelpString(self):
        return tr('alg_help')

    def createInstance(self):
        return PdfToTiffAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            self.INPUT_FOLDER, tr('p_input'), behavior=_FILE_FOLDER))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_FOLDER, tr('p_output')))
        self.addParameter(QgsProcessingParameterNumber(
            self.DPI, tr('p_dpi'),
            type=_NUMBER_INTEGER, defaultValue=200, minValue=72, maxValue=2400))
        self.addParameter(QgsProcessingParameterEnum(
            self.PAGE_MODE, tr('p_page_mode'), options=page_mode_labels(), defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.PAGES, tr('p_pages'), defaultValue='', optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.MIN_FORMAT, tr('p_min_format'), options=SHEET_NAMES,
            defaultValue=SHEET_NAMES.index(DEFAULT_MIN_FORMAT.upper())))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_INK, tr('p_min_ink'),
            type=_NUMBER_DOUBLE, defaultValue=DEFAULT_MIN_INK,
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
            raise QgsProcessingException(tr('exc_no_pdf'))

        labels = page_mode_labels()
        mode_label = labels[max(0, min(mode_index, len(labels) - 1))]

        feedback.pushInfo(tr('info_gdal', path=gdal))
        feedback.pushInfo(tr('info_in', path=in_dir))
        feedback.pushInfo(tr('info_out', path=out_dir))
        feedback.pushInfo(tr('info_dpi', dpi=dpi))
        if page_mode == PAGE_MODE_DRAWINGS:
            feedback.pushInfo(tr('mode_line_drawings', mode=mode_label,
                                 fmt=min_format, ink=min_ink))
        else:
            feedback.pushInfo(tr('mode_line', mode=mode_label))
        feedback.pushInfo(tr('info_files', count=len(files)))

        ok_count = 0
        fail_count = 0
        skipped_count = 0
        total = len(files)

        for index, src in enumerate(files):
            if feedback.isCanceled():
                feedback.pushInfo(tr('info_cancel'))
                break

            feedback.setProgress(int(index * 100.0 / total))

            base_dst, dst_dir = build_dest_path(src, in_dir, out_dir, recursive)
            feedback.pushInfo('[%d/%d] %s' % (index + 1, total, os.path.basename(src)))

            try:
                os.makedirs(dst_dir, exist_ok=True)
            except OSError as exc:
                fail_count += 1
                feedback.reportError(tr('info_mkdir', dir=dst_dir, err=exc), fatalError=False)
                continue

            ok, fail, skipped = convert_pdf_file(
                gdal, src, base_dst, dpi,
                page_mode, page_spec, min_format, min_ink,
                skip_existing, feedback.pushInfo)
            ok_count += ok
            fail_count += fail
            skipped_count += skipped

        feedback.setProgress(100)
        feedback.pushInfo(tr('info_done', ok=ok_count, fail=fail_count, skip=skipped_count))
        return {self.OUTPUT_FOLDER: out_dir}


class PdfToTiffProvider(QgsProcessingProvider):
    """Dostawca algorytmow PDF -> TIFF."""

    def id(self):
        return 'pdf2tiff'

    def name(self):
        return 'PDF -> TIFF (GDAL)'

    def longDescription(self):
        return tr('plugin_tip')

    def icon(self):
        from qgis.PyQt.QtGui import QIcon
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))

    def loadAlgorithms(self):
        self.addAlgorithm(PdfToTiffAlgorithm())
