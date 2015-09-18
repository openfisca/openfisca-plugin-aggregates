# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
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


from __future__ import division

import collections
from datetime import datetime
import os

from numpy import nan
import pandas

from openfisca_france_data import AGGREGATES_DEFAULT_VARS, FILTERING_VARS, PLUGINS_DIR
from openfisca_france_data.tests import base

DATA_DIR = os.path.join(PLUGINS_DIR, 'aggregates')


# TODO: units for amount and beneficiaries

class Aggregates(object):
    base_data_frame = None
    filter_by = None
    labels = collections.OrderedDict((
        ('var', u"Mesure"),
        ('entity', u"Entité"),
        ('dep', u"Dépenses\n(millions d'€)"),
        ('benef', u"Bénéficiaires\n(milliers)"),
        ('dep_default', u"Dépenses initiales\n(millions d'€)"),
        ('benef_default', u"Bénéficiaires\ninitiaux\n(milliers)"),
        ('dep_real', u"Dépenses\nréelles\n(millions d'€)"),
        ('benef_real', u"Bénéficiaires\nréels\n(milliers)"),
        ('dep_diff_abs', u"Diff. absolue\nDépenses\n(millions d'€)"),
        ('benef_diff_abs', u"Diff absolue\nBénéficiaires\n(milliers)"),
        ('dep_diff_rel', u"Diff. relative\nDépenses"),
        ('benef_diff_rel', u"Diff. relative\nBénéficiaires"),
        ))  # TODO: localize
    survey_scenario = None
    totals_df = None
    varlist = None

    def __init__(self, survey_scenario = None):
        if survey_scenario is not None:
            self.set_survey_scenario(survey_scenario)

    def compute_aggregates(self, reference = True, reform = True, actual = True):
        """
        Compute aggregate amounts
        """
        filter_by = self.filter_by
        self.load_amounts_from_file()
        base_data_frame = pandas.DataFrame()

        simulation_types = list()
        if reference:
            simulation_types.append('reference')
        if reform:
            simulation_types.append('reform')
        if actual:
            simulation_types.append('actual')

        for simulation_type in simulation_types:
            if simulation_type == 'actual':
                if base_data_frame.empty:
                    base_data_frame = self.totals_df.copy()
                else:
                    base_data_frame = pandas.concat((base_data_frame, self.totals_df), axis = 1)
            else:
                for variable in self.varlist:
                    variable_data_frame = self.compute_variable_aggregates(
                        variable, filter_by = filter_by, simulation_type = simulation_type)
                    if variable not in base_data_frame.index:
                        base_data_frame = pandas.concat((base_data_frame, variable_data_frame))
                    else:
                        base_data_frame = base_data_frame.merge(variable_data_frame)

        self.base_data_frame = base_data_frame
        return base_data_frame

    def compute_difference(self, target = "reference", default = 'actual', amount = True, beneficiaries = True,
            absolute = True, relative = True):
        '''
        Computes and adds relative differences to the data_frame
        '''
        assert relative or absolute
        assert amount or beneficiaries
        base_data_frame = self.base_data_frame if self.base_data_frame is not None else self.compute_aggregates()

        difference_data_frame = base_data_frame[['label', 'entity']].copy()
        quantities = ['amount'] if amount else None + ['beneficiaries'] if beneficiaries else None

        for quantity in quantities:
            difference_data_frame['{}_absolute_difference'.format(quantity)] = (
                base_data_frame['{}_{}'.format(target, quantity)] - base_data_frame['{}_{}'.format(default, quantity)]
                )
            difference_data_frame['{}_relative_difference'.format(quantity)] = (
                base_data_frame['{}_{}'.format(target, quantity)] - base_data_frame['{}_{}'.format(default, quantity)]
                ) / abs(base_data_frame['{}_{}'.format(default, quantity)])
        return difference_data_frame

    def create_description(self):
        '''
        Creates a description dataframe
        '''
        now = datetime.now()
        return pandas.DataFrame([
            u'OpenFisca',
            u'Calculé le %s à %s' % (now.strftime('%d-%m-%Y'), now.strftime('%H:%M')),
            u'Système socio-fiscal au %s' % self.simulation.period.start,
            u"Données d'enquêtes de l'année %s" % str(self.simulation.input_table.survey_year),
            ])

    def compute_variable_aggregates(self, variable, filter_by = None, simulation_type = 'reference'):
        """
        Returns aggregate spending, and number of beneficiaries
        for the relevant entity level

        Parameters
        ----------
        variable : string
                   name of the variable aggregated according to its entity
        filter_by : string
                    name of the variable to filter by
        simulation_type : string
                          reference or reform or actual
        """
        assert simulation_type in ['reference', 'reform']
        prefixed_simulation = '{}_simulation'.format(simulation_type)
        simulation = getattr(self, prefixed_simulation)
        column_by_name = simulation.tax_benefit_system.column_by_name
        column = column_by_name[variable]
        weight = self.weight_column_name_by_entity_key_plural[column.entity_key_plural]
        assert weight in column_by_name, "{} not a variable of the system".format(weight)
        # amounts and beneficiaries from current data and default data if exists
        # Build weights for each entity
        data = pandas.DataFrame({
            variable: simulation.calculate_add(variable),
            weight: simulation.calculate(weight),
            })
        if filter_by:
            filter_dummy = simulation.calculate("{}_{}".format(filter_by, column.entity_key_plural))

        try:
            amount = int(
                (data[variable] * data[weight] * filter_dummy / 10 ** 6).sum().round()
                )
        except:
            amount = nan
        try:
            beneficiaries = int(
                ((data[variable] != 0) * weight * filter_dummy / 10 ** 3).sum().round()
                )
        except:
            beneficiaries = nan

        variable_data_frame = pandas.DataFrame(
            data = {
                'label': column_by_name[variable].label,
                'entity': column_by_name[variable].entity_key_plural,
                '{}_amount'.format(simulation_type): amount,
                '{}_beneficiaries'.format(simulation_type): beneficiaries,
                },
            index = [variable],
            )

        return variable_data_frame

    def load_amounts_from_file(self, filename = None, year = None):
        '''
        Loads totals from files
        '''
        if year is None:
            year = self.year
        if filename is None:
            data_dir = DATA_DIR

#        try:
        filename = os.path.join(data_dir, "amounts.h5")
        store = pandas.HDFStore(filename)

        df_a = store['amounts']
        df_b = store['benef']
        store.close()
        self.totals_df = pandas.DataFrame(data = {
            "actual_amount": df_a[year] / 10 ** 6,
            "actual_beneficiaries": df_b[year] / 10 ** 3,
            })
        row = pandas.DataFrame({'actual_amount': nan, 'actual_beneficiaries': nan}, index = ['logt'])
        self.totals_df = self.totals_df.append(row)

        # Add some aditionnals totals
        for col in ['actual_amount', 'actual_beneficiaries']:
            # Deals with logt
            logt = 0
            for var in ['apl', 'alf', 'als']:
                logt += self.totals_df.get_value(var, col)
            self.totals_df.set_value('logt', col, logt)

            # Deals with rsa rmi
            rsa = 0
            for var in ['rmi', 'rsa']:
                rsa += self.totals_df.get_value(var, col)
            self.totals_df.set_value('rsa', col, rsa)

            # Deals with irpp, csg, crds
            for var in ['irpp', 'csg', 'crds', 'cotsoc_noncontrib']:
                if col in ['actual_amount']:
                    val = - self.totals_df.get_value(var, col)
                    self.totals_df.set_value(var, col, val)
#        except:
#            #  raise Exception(" No administrative data available for year " + str(year))
#            import warnings
#            warnings.warn("No administrative data available for year %s in file %s" % (str(year), filename))
#            self.totals_df = None
#            return

    def save_table(self, directory = None, filename = None, table_format = None):
        '''
        Saves the table to some format
        '''
        now = datetime.now()
        if table_format is None:
            if filename is not None:
                extension = filename[-4:]
                if extension == '.xls':
                    table_format = 'xls'
                elif extension == '.csv':
                    table_format = 'csv'
            else:
                table_format = 'xls'

        if directory is None:
            directory = "."
        if filename is None:
            filename = 'Aggregates_%s.%s' % (now.strftime('%d-%m-%Y'), table_format)

        fname = os.path.join(directory, filename)

        try:
            df = self.data_frame
            if table_format == "xls":
                writer = pandas.ExcelWriter(str(fname))
                df.to_excel(writer, "aggregates", index= False, header= True)
                descr = self.create_description()
                descr.to_excel(writer, "description", index = False, header=False)
                writer.save()
            elif table_format == "csv":
                df.to_csv(fname, "aggregates", index= False, header = True)
        except Exception, e:
                raise Exception("Aggregates: Error saving file", str(e))

    def set_survey_scenario(self, survey_scenario, debug = False, debug_all = False, trace = False):
        self.year = survey_scenario.year
        if survey_scenario.simulation is not None:
            raise('A simulation already exists')

        else:
            self.reference_simulation = survey_scenario.new_simulation(
                debug = debug,
                debug_all = debug_all,
                reference = base.france_data_tax_benefit_system,
                trace = debug_all
                )
            self.reform_simulation = survey_scenario.new_simulation(
                debug = debug,
                debug_all = debug_all,
                trace = debug_all
                )

        self.weight_column_name_by_entity_key_plural = survey_scenario.weight_column_name_by_entity_key_plural
        self.varlist = AGGREGATES_DEFAULT_VARS
        self.filter_by_var_list = FILTERING_VARS
        varname = self.filter_by_var_list[0]
        self.filter_by = varname