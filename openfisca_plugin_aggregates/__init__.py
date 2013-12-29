# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


def register_plugin(qt_main_window = None):
    """Register OpenFisca plugin."""
    if qt_main_window is not None:
        from openfisca_qt.gui.baseconfig import get_translation
        from openfisca_qt.gui.config import CONF

        from . import widgets

    # TODO: Register this plugin to OpenFisca-Web-API.

    if qt_main_window is not None and not CONF.get('survey', 'bareme_only') and CONF.get('aggregates', 'enable'):
        _ = get_translation('openfisca_qt')
        qt_main_window.set_splash(_("Loading aggregates widget ..."))
        widget = widgets.AggregatesWidget(qt_main_window)
        qt_main_window.add_dockwidget(widget)
        qt_main_window.aggregates = widget
        qt_main_window.survey_plugins.append(widget)
