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

DATA_DIR = os.path.join(PLUGINS_DIR, 'aggregates')


class Aggregates(object):
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
    show_default = False
    show_diff = True
    show_real = True
    survey_scenario = None
    totals_df = None
    varlist = None

    def __init__(self, survey_scenario = None):
        if survey_scenario is not None:
            self.set_survey_scenario(survey_scenario)

    def clear(self):
        self.totals_df = None

    def compute(self):
        """
        Compute the whole table
        """
        self.compute_aggregates(self.filter_by)
        self.load_amounts_from_file()
        self.compute_real()
        self.compute_diff()

    def compute_aggregates_base(self, filter_by = None):
        """
        Compute aggregate amounts
        """
        base_data_frame = pandas.DataFrame()

        for simulation_type in ['reference', 'reform', 'actual']:
            for variable in self.varlist:
                # amounts and beneficiaries from current data and default data if exists
                montant_benef = self.get_aggregate(
                    variable, filter_by = filter_by,
                    simulation_type = simulation_type
                    )

                V.append(column_by_name[var].label)
                entity = column_by_name[var].entity_key_plural


        import itertools
        lists = [
,
            ['amounts', 'beneficiaries'],
            ]
        columns = [
            '{}_{}'.format(situation, value) for (situation, value) in itertools.product(*lists)
            ]


    def compute_aggregates(self, filter_by = None):
        """
        Compute aggregate amounts
        """
        column_by_name = self.simulation.tax_benefit_system.column_by_name
        V = []
        M = {'data': [], 'default': []}
        B = {'data': [], 'default': []}
        U = []

        amounts_label = {'data': self.labels['dep'],
                   'default': self.labels['dep_default']}
        beneficiaries_label = {'data': self.labels['benef'],
                   'default': self.labels['benef_default']}

        for var in self.varlist:
            # amounts and beneficiaries from current data and default data if exists
            montant_benef = self.get_aggregate(var, filter_by)
            V.append(column_by_name[var].label)
            entity = column_by_name[var].entity_key_plural

            U.append(entity)
            for dataname in montant_benef:
                M[dataname].append(montant_benef[dataname][0])
                B[dataname].append(montant_benef[dataname][1])

        # build items list
        items = [(self.labels['var'], V)]

        for dataname in M:
            if M[dataname]:
                items.append((amounts_label[dataname], M[dataname]))
                items.append((beneficiaries_label[dataname], B[dataname]))

        items.append((self.labels['entity'], U))
        data_frame = pandas.DataFrame.from_items(items)

        self.data_frame = None
        for code, label in self.labels.iteritems():
            try:
                col = data_frame[label]
                if self.data_frame is None:
                    self.data_frame = pandas.DataFrame(col)
                else:
                    self.data_frame = self.data_frame.join(col, how="outer")
            except:
                pass




    def compute_diff(self):
        '''
        Computes and adds relative differences to the data_frame
        '''

        dep = self.data_frame[self.labels['dep']]
        benef = self.data_frame[self.labels['benef']]

        if self.show_default:
            ref_dep_label, ref_benef_label = self.labels['dep_default'], self.labels['benef_default']
            if ref_dep_label not in self.data_frame:
                return
        elif self.show_real:
            ref_dep_label, ref_benef_label = self.labels['dep_real'], self.labels['benef_real']
        else:
            return

        ref_dep = self.data_frame[ref_dep_label]
        ref_benef = self.data_frame[ref_benef_label]

        self.data_frame[self.labels['dep_diff_rel']] = (dep - ref_dep) / abs(ref_dep)
        self.data_frame[self.labels['benef_diff_rel']] = (benef - ref_benef) / abs(ref_benef)
        self.data_frame[self.labels['dep_diff_abs']] = dep - ref_dep
        self.data_frame[self.labels['benef_diff_abs']] = benef - ref_benef

    def compute_real(self):
        '''
        Adds administrative data to dataframe
        '''
        if self.totals_df is None:
            return
        A, B = [], []
        for var in self.varlist:
            # totals from administrative data
            if var in self.totals_df.index:
                A.append(self.totals_df.get_value(var, "amount"))
                B.append(self.totals_df.get_value(var, "benef"))
            else:
                A.append(nan)
                B.append(nan)
        self.data_frame[self.labels['dep_real']] = A
        self.data_frame[self.labels['benef_real']] = B

    def create_description(self):
        '''
        Creates a description dataframe
        '''
        now = datetime.now()
        return DataFrame([
            u'OpenFisca',
            u'Calculé le %s à %s' % (now.strftime('%d-%m-%Y'), now.strftime('%H:%M')),
            u'Système socio-fiscal au %s' % self.simulation.period.start,
            u"Données d'enquêtes de l'année %s" % str(self.simulation.input_table.survey_year),
            ])


    def get_aggregate2(self, variable, filter_by = None, simulation_type):



    def get_aggregate(self, variable, filter_by = None):
        """
        Returns aggregate spending, and number of beneficiaries
        for the relevant entity level

        Parameters
        ----------
        variable : string
                   name of the variable aggregated according to its entity
        """
        simulation = self.simulation
        column_by_name = self.simulation.tax_benefit_system.column_by_name
        column = column_by_name[variable]
        weight_name = self.weight_column_name_by_entity_key_plural[column.entity_key_plural]
        filter_by_name = "{}_{}".format(filter_by, column.entity_key_plural)
        # amounts and beneficiaries from current data and default data if exists
        # Build weights for each entity
        data = DataFrame(
            {
                variable: simulation.calculate_add(variable),
                weight_name: simulation.calculate(weight_name),
                }
            )
        data_default = None

        datasets = {'data': data}
        if data_default is not None:
            datasets['default'] = data_default
        filter_indicator = True
        if filter_by:
            filtered_data = pandas.DataFrame(
                {
                    variable: simulation.calculate(variable),
                    weight_name: simulation.calculate(weight_name),
                    filter_by_name: simulation.calculate(filter_by_name),
                    }
                )
            filter_indicator = filtered_data[filter_by_name]

        m_b = {}

        weight = data[weight_name] * filter_indicator
        for name, data in datasets.iteritems():
            amount = data[variable]
            benef = data[variable].values != 0
            try:
                total_amount = int(round(sum(amount * weight) / 10 ** 6))
            except:
                total_amount = nan
            try:
                total_benef = int(round(sum(benef * weight) / 10 ** 3))
            except:
                total_benef = nan

            m_b[name] = [total_amount, total_benef]

        return m_b

    def load_amounts_from_file(self, filename = None, year = None):
        '''
        Loads totals from files
        '''
        if year is None:
            year = self.year
        if filename is None:
            data_dir = DATA_DIR

        try:
            filename = os.path.join(data_dir, "amounts.h5")
            store = pandas.HDFStore(filename)

            df_a = store['amounts']
            df_b = store['benef']
            store.close()
            self.totals_df = pandas.DataFrame(data = {
                "amount": df_a[year] / 10 ** 6,
                "benef": df_b[year] / 1000,
                })
            row = pandas.DataFrame({'amount': nan, 'benef': nan}, index = ['logt'])
            self.totals_df = self.totals_df.append(row)

            # Add some aditionnals totals
            for col in ['amount', 'benef']:
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
                    if col in ['amount']:
                        val = - self.totals_df.get_value(var, col)
                        self.totals_df.set_value(var, col, val)
        except:
            #  raise Exception(" No administrative data available for year " + str(year))
            import warnings
            warnings.warn("No administrative data available for year %s in file %s" % (str(year), filename))
            self.totals_df = None
            return

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
            boum
        else:
            self.reference_simulation = survey_scenario.new_simulation(
            debug = debug,
            debug_all = debug_all,
            reference = True,
            trace = debug_all
            )

            self.simulation = survey_scenario.simulation
        self.weight_column_name_by_entity_key_plural = survey_scenario.weight_column_name_by_entity_key_plural
        self.varlist = AGGREGATES_DEFAULT_VARS
        self.filter_by_var_list = FILTERING_VARS
        varname = self.filter_by_var_list[0]
        self.filter_by = varname
