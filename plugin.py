# -*- coding: utf-8 -*-
"""Rejestracja wtyczki w QGIS: ikona na pasku narzedzi, menu i algorytmy Processing."""

import os

from qgis.core import QgsApplication

try:                                   # QGIS 4 / Qt6
    from qgis.PyQt.QtGui import QAction
except ImportError:                    # QGIS 3 / Qt5
    from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .algorithm import PdfToTiffProvider
from .dialog import PdfToTiffDialog

MENU_NAME = '&PDF -> TIFF'


class PdfToTiffPlugin(object):
    """Wtyczka PDF2TIFF."""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.provider = None
        self.dialog = None

    # ------------------------------------------------------------------
    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))

        self.action = QAction(icon, 'Konwerter PDF -> TIFF (bezstratny, GDAL)',
                              self.iface.mainWindow())
        self.action.setStatusTip('Konwersja wszystkich plików PDF z katalogu do TIFF (GDAL, DEFLATE)')
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU_NAME, self.action)

        # algorytm dostepny w Panelu przetwarzania / modelach
        if self.provider is None:
            self.provider = PdfToTiffProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(MENU_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.provider is not None:
            try:
                QgsApplication.processingRegistry().removeProvider(self.provider)
            except Exception:
                pass
            self.provider = None

        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    # ------------------------------------------------------------------
    def run(self):
        if self.dialog is None:
            self.dialog = PdfToTiffDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
