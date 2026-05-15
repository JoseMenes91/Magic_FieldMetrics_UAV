# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsProcessingAlgorithm,
                       QgsApplication)
import processing
import os
from .zonal_stats_provider import ZonalStatsProvider
from .translations import tr

class ZonalStatsPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.provider = None

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.initProcessing()
        
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(QIcon(icon_path), tr('NAME'), self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToRasterMenu('Magic FieldMetrics', self.action)

        # Add toolbar button
        self.toolbar = self.iface.addToolBar('Magic FieldMetrics')
        self.toolbar.setObjectName('MagicFieldMetricsToolbar')
        self.toolbar.addAction(self.action)

    def initProcessing(self):
        """Initialize the processing provider."""
        self.provider = ZonalStatsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def run(self):
        """Run the processing algorithm."""
        processing.execAlgorithmDialog('magicstatsextractor:magic_stats_extractor')

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginRasterMenu('Magic Stats', self.action)
        
        # Remove toolbar
        del self.toolbar
