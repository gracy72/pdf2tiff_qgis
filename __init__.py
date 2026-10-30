# -*- coding: utf-8 -*-
"""
PDF2TIFF - konwerter PDF do TIFF (bezstratny, GDAL) - wtyczka QGIS.

Konwersja PDF-ow do GeoTIFF przez gdal_translate: renderowanie w zadanym DPI,
kompresja bezstratna DEFLATE, PDF wielostronicowe z wyborem stron,
pomijanie istniejacych plikow i zachowywanie struktury podkatalogow.
"""


def classFactory(iface):  # noqa: N802 (nazwa wymagana przez QGIS)
    """Punkt wejscia wtyczki QGIS."""
    from .plugin import PdfToTiffPlugin
    return PdfToTiffPlugin(iface)
