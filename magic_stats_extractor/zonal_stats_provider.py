# -*- coding: utf-8 -*-

from qgis.core import QgsProcessingProvider
from .zonal_stats_algorithm import ZonalStatsAlgorithm
from qgis.PyQt.QtGui import QIcon
import os
from .translations import tr

class ZonalStatsProvider(QgsProcessingProvider):

    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(ZonalStatsAlgorithm())

    def id(self, *args, **kwargs):
        """The ID of your plugin, used for identifying the provider.

        This string should be unique for, unique for your plugin,
        and should contain not contain spaces.
        """
        return 'magicstatsextractor'

    def name(self, *args, **kwargs):
        """The human readable name of your plugin in Processing."""
        return tr('NAME')

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))
