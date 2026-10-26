# -*- coding: utf-8 -*-
"""
PDF2TIFF - konwerter PDF do TIFF (bezstratny, GDAL) - wtyczka QGIS.

Odpowiednik programu Laz_PDF_tiff (Lazarus / Free Pascal):
te same opcje, ten sam sposob wywolania gdal_translate, ta sama logika
pomijania istniejacych plikow i zachowywania podkatalogow.
"""


def classFactory(iface):  # noqa: N802 (nazwa wymagana przez QGIS)
    """Punkt wejscia wtyczki QGIS."""
    from .plugin import PdfToTiffPlugin
    return PdfToTiffPlugin(iface)
