# -*- coding: utf-8 -*-

__author__ = 'José Fernando Menes'
__date__ = '2024-05-23'
__copyright__ = '(C) 2024 by José Fernando Menes'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from .zonal_stats_provider import ZonalStatsProvider

def classFactory(iface):
    """Load ZonalStatsPlugin class from file ZonalStatsPlugin.

    :param iface: A QgsInterface instance.
    """
    from .zonal_stats_plugin import ZonalStatsPlugin
    return ZonalStatsPlugin(iface)
