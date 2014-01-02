# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
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


import os

from openfisca_qt.gui.baseconfig import get_translation
from openfisca_qt.gui.config import get_icon
from openfisca_qt.gui.qt.QtCore import SIGNAL, Qt
from openfisca_qt.gui.qt.QtGui import QFileDialog, QGroupBox, QMenu, QMessageBox, QSizePolicy, QVBoxLayout, QWidget
from openfisca_qt.gui.qthelpers import DataFrameViewWidget, OfSs
from openfisca_qt.gui.utils.qthelpers import add_actions, create_action
from openfisca_qt.plugins import OpenfiscaPluginWidget, PluginConfigPage
from pandas import ExcelWriter

from .aggregates import Aggregates


_ = get_translation('openfisca_qt')


class AggregatesConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("Aggregates")

    def setup_page(self):

        export_group = QGroupBox(_("Export"))
        export_dir = self.create_browsedir(_("Export directory"), "table/export_dir")
        choices = [('cvs', 'csv'),
                   ('xls', 'xls'),]
        table_format = self.create_combobox(_('Table export format'), choices, 'table/format')
        export_layout = QVBoxLayout()
        export_layout.addWidget(export_dir)
        export_layout.addWidget(table_format)
        export_group.setLayout(export_layout)

        variables_group = QGroupBox(_("Columns"))
        show_dep = self.create_checkbox(_("Display expenses"),
                                        'show_dep')
        show_benef = self.create_checkbox(_("Display beneficiaries"),
                                        'show_benef')
        show_real = self.create_checkbox(_("Display actual values"),
                                        'show_real')
        show_diff = self.create_checkbox(_("Display differences"),
                                        'show_diff')
        show_diff_rel = self.create_checkbox(_("Display relative differences"),
                                        'show_diff_rel')
        show_diff_abs = self.create_checkbox(_("Display absolute differences"),
                                        'show_diff_abs')
        show_default = self.create_checkbox(_("Display default values"),
                                        'show_default')

        variables_layout = QVBoxLayout()
        for combo in [show_dep, show_benef, show_real, show_diff, show_diff_abs,
                       show_diff_rel, show_default]:
            variables_layout.addWidget(combo)
        variables_group.setLayout(variables_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(export_group)
        vlayout.addWidget(variables_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class AggregatesWidget(OpenfiscaPluginWidget):
    """
    Aggregates Widget
    """
    CONF_SECTION = 'aggregates'
    CONFIGWIDGET_CLASS = AggregatesConfigPage

    def __init__(self, parent = None):
        super(AggregatesWidget, self).__init__(parent)
        self.setStyleSheet(OfSs.dock_style)
        # Create geometry
        self.setObjectName(u"Aggrégats")
        self.setWindowTitle(u"Aggrégats")
        self.dockWidgetContents = QWidget()

        self.view = DataFrameViewWidget(self.dockWidgetContents)

        # Context Menu
        headers = self.view.horizontalHeader()
        self.headers = headers
        headers.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(self.headers,SIGNAL('customContextMenuRequested(QPoint)'), self.ctx_select_menu)
        verticalLayout = QVBoxLayout(self.dockWidgetContents)
        verticalLayout.addWidget(self.view)
        self.setLayout(verticalLayout)

        # Initialize attributes
        self.survey_year = None
        self.parent = parent
        self.aggregates = None

        self.show_dep = self.get_option('show_dep')
        self.show_benef = self.get_option('show_benef')
        self.show_real = self.get_option('show_real')
        self.show_diff = self.get_option('show_diff')
        self.show_diff_abs = self.get_option('show_diff_abs')
        self.show_diff_rel = self.get_option('show_diff_rel')
        self.show_default = self.get_option('show_default')

    def set_aggregates(self, aggregates):
        """
        Sets aggregates
        """
        self.aggregates = aggregates
        if self.aggregates.simulation.reforme is False:
            self.show_default = False
        else:
            self.show_default = True

    def ctx_select_menu(self, point):
        self.select_menu.exec_( self.headers.mapToGlobal(point) )


    def toggle_option(self, option, boolean):
        self.set_option(option, boolean)
        self.show_dep = boolean
        self.update_view()



    def update_view(self):
        '''
        Update aggregate amounts view
        '''
        if self.aggregates.aggr_frame is None:
            return

        cols = [self.aggregates.labels[code] for code in self.aggregates.labels_ordered_list]

        labels = self.aggregates.labels

        if not self.get_option('show_real'):
            cols.remove(labels['dep_real'])
            cols.remove(labels['benef_real'])

        if (not self.get_option('show_default')) or self.aggregates.simulation.reforme is False:
            cols.remove(labels['dep_default'])
            cols.remove(labels['benef_default'])

        remove_all_diffs =  not (self.aggregates.show_real or self.aggregates.show_default)
        if not remove_all_diffs:
            self.aggregates.compute_diff()

        if (not self.get_option('show_diff_abs')) or remove_all_diffs:

            cols.remove(labels['dep_diff_abs'])
            cols.remove(labels['benef_diff_abs'])

        if (not self.get_option('show_diff_rel')) or remove_all_diffs:
            cols.remove(labels['dep_diff_rel'])
            cols.remove(labels['benef_diff_rel'])

        if not self.get_option('show_dep'):
            for label in [labels['dep'], labels['dep_real'],
                          labels['dep_default'], labels['dep_diff_abs'],
                          labels['dep_diff_rel']]:

                if label in cols:
                    cols.remove(label)

        if not self.get_option('show_benef'):
            for label in [labels['benef'], labels['benef_real'],
                          labels['benef_default'], labels['benef_diff_abs'],
                          labels['benef_diff_rel']]:

                if label in cols:
                    cols.remove(label)

        self.view.set_dataframe(self.aggregates.aggr_frame[cols])
        self.view.resizeColumnsToContents()
        self.view.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)


    def calculated(self):
        '''
        Emits signal indicating that aggregates are computed
        '''
        self.emit(SIGNAL('calculated()'))


    def clear(self):
        self.view.clear()


    def save_table(self, table_format = None, float_format = "%.2f"):
        '''
        Saves the table to the designated format
        '''
        if table_format is None:
            table_format = self.get_option('table/format')

        output_dir = self.get_option('table/export_dir')
        filename = 'sans-titre.' + table_format
        user_path = os.path.join(output_dir, filename)

        extension = table_format.upper() + "   (*." + table_format + ")"
        fname = QFileDialog.getSaveFileName(self,
                                               _("Save table"), #"Exporter la table",
                                               user_path, extension)

        if fname:
            self.set_option('table/export_dir', os.path.dirname(str(fname)))
            try:
                df = self.view.model().dataframe
                if table_format == "xls":
                    writer = ExcelWriter(str(fname))
                    df.to_excel(writer, "aggregates", index= False, header= True, float_format = float_format)
                    descr = self.create_description()
                    descr.to_excel(writer, "description", index = False, header=False)
                    writer.save()
                elif table_format =="csv":
                    df.to_csv(writer, "aggregates", index= False, header = True, float_format = float_format)


            except Exception, e:
                QMessageBox.critical(
                    self, "Error saving file", str(e),
                    QMessageBox.Ok, QMessageBox.NoButton)

    #------ OpenfiscaPluginMixin API ---------------------------------------------

    def apply_plugin_settings(self, options):
        """
        Apply configuration file's plugin settings
        """
        show_options = ['show_default', 'show_real', 'show_diff_abs',
                        'show_diff_abs', 'show_diff_rel', 'show_dep', 'show_benef']

        for option in options:
            if option in show_options:
                self.toggle_option(option, self.get_option(option))

#        if option is

    #------ OpenfiscaPluginWidget API ---------------------------------------------

    def get_plugin_title(self):
        """
        Return plugin title
        Note: after some thinking, it appears that using a method
        is more flexible here than using a class attribute
        """
        return "Aggregates"


    def get_plugin_icon(self):
        """
        Return plugin icon (QIcon instance)
        Note: this is required for plugins creating a main window
              (see OpenfiscaPluginMixin.create_mainwindow)
              and for configuration dialog widgets creation
        """
        return get_icon('OpenFisca22.png')

    def get_plugin_actions(self):
        """
        Return a list of actions related to plugin
        Note: these actions will be enabled when plugin's dockwidget is visible
              and they will be disabled when it's hidden
        """
        raise NotImplementedError

    def refresh_plugin(self):
        '''
        Update aggregate output_table and refresh view
        '''

        simulation = self.main.survey_simulation
        self.starting_long_process(_("Refreshing aggregates table ..."))
        agg = Aggregates()
        agg.set_simulation(simulation)
        agg.compute()

        self.aggregates = agg
        self.survey_year = self.aggregates.simulation.input_table.survey_year
        self.description = self.aggregates.simulation.output_table.description

        self.select_menu = QMenu()
        action_dep = create_action(self, u"Dépenses",
                                   toggled = lambda boolean: self.toggle_option('show_dep', boolean))
        action_benef = create_action(self, u"Bénéficiaires",
                                     toggled = lambda boolean: self.toggle_option('show_benef', boolean))
        action_real = create_action(self, u"Réel",
                                   toggled = lambda boolean: self.toggle_option('show_real', boolean))
        action_diff_abs = create_action(self, u"Diff. absolue",
                                       toggled = lambda boolean: self.toggle_option('show_diff_abs', boolean))
        action_diff_rel = create_action(self, u"Diff. relative ",
                                       toggled = lambda boolean: self.toggle_option('show_diff_rel', boolean))
        action_default = create_action(self, u"Référence",
                                       toggled = lambda boolean: self.toggle_option('show_default', boolean))

        actions = [action_dep, action_benef]
        action_dep.toggle()
        action_benef.toggle()

        if self.aggregates.simulation.reforme is False:
            self.set_option('show_default', False)
            if self.aggregates.totals_df is not None: # real available
                actions.append(action_real)
                actions.append(action_diff_abs)
                actions.append(action_diff_rel)
                action_real.toggle()
                action_diff_abs.toggle()
                action_diff_rel.toggle()
            else:
                self.set_option('show_real', False)
                self.set_option('show_diff_abs', False)
                self.set_option('show_diff_rel', False)

        else:
            self.set_option('show_real', False)
            actions.append(action_default)
            actions.append(action_diff_abs)
            actions.append(action_diff_rel)

            action_default.toggle()
            action_diff_abs.toggle()
            action_diff_rel.toggle()

        add_actions(self.select_menu, actions)

        self.do_not_update = False
        self.update_view()
        self.calculated()
        self.ending_long_process(_("Aggregates table updated"))


    def closing_plugin(self, cancelable=False):
        """
        Perform actions before parent main window is closed
        Return True or False whether the plugin may be closed immediately or not
        Note: returned value is ignored if *cancelable* is False
        """
        return True

