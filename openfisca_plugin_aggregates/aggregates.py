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


from __future__ import division

import collections
from datetime import datetime
import os

from numpy import nan
from openfisca_core import model
from openfisca_core.simulations import SurveySimulation
from pandas import DataFrame, ExcelWriter


class Aggregates(object):
    data = None
    data_default = None
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
        ))
    show_default = False
    show_diff = True
    show_real = True
    simulation = None
    totals_df = None
    varlist = None

    def set_var_list(self, var_list):
        """
        Set list of variables to be aggregated
        """
        self.varlist = var_list

    def set_filter_by(self, varname):
        """
        Set the variable to filter by the amounts and beneficiaries that are
        to be taken into account
        """
        self.filter_by = varname

    def set_default_var_list(self):
        """
        Set list of variables to be aggregated
        """
        self.varlist = model.AGGREGATES_DEFAULT_VARS

    def set_default_filter_by_list(self):
        """
        Import country specific default filter by variables list
        """
        self.filter_by_var_list = model.FILTERING_VARS

    def set_default_filter_by(self):
        """
        Set country specific default filter by variable
        """
        self.set_default_filter_by_list()
        varname = self.filter_by_var_list[0]
        self.set_filter_by(varname)

    def set_simulation(self, simulation):

        if isinstance(simulation, SurveySimulation):
            self.simulation = simulation
        else:
            raise Exception('Aggregates:  %s should be an instance of %s class'  %(simulation, SurveySimulation))
        self.set_default_var_list()
        self.set_default_filter_by()

    def compute(self):
        """
        Compute the whole table
        """
        filter_by = self.filter_by
#        try:
        self.compute_aggregates(filter_by)
#        except Exception, e:
#            raise Exception("Cannot compute aggregates.\n compute_aggregates returned error '%s'" % e)
        self.load_amounts_from_file()
        self.compute_real()
        self.compute_diff()


    def compute_aggregates(self, filter_by = None):
        """
        Compute aggregate amounts
        """
        if self.simulation.output_table is None:
            raise Exception("No output_table found for the current survey_simulation")

        V  = []
        M = {'data': [], 'default': []}
        B = {'data': [], 'default': []}
        U = []

        M_label = {'data': self.labels['dep'],
                   'default': self.labels['dep_default']}
        B_label = {'data': self.labels['benef'],
                   'default': self.labels['benef_default']}

        simulation = self.simulation
        for var in self.varlist:
            # amounts and beneficiaries from current data and default data if exists
            montant_benef = self.get_aggregate(var, filter_by)
            V.append(simulation.var2label[var])
            try:
                varcol  = simulation.get_col(var)
                entity = varcol.entity
            except:
                entity = 'NA'

            U.append(entity)
            for dataname in montant_benef:
                M[dataname].append( montant_benef[dataname][0] )
                B[dataname].append( montant_benef[dataname][1] )

        # build items list
        items = [(self.labels['var'], V)]

        for dataname in M:
            if M[dataname]:
                items.append( (M_label[dataname], M[dataname]))
                items.append(  (B_label[dataname], B[dataname]) )

        items.append( (self.labels['entity'], U) )
        aggr_frame = DataFrame.from_items(items)

        self.aggr_frame = None
        for code, label in self.labels.iteritems():
            try:
                col = aggr_frame[label]
                if self.aggr_frame is None:
                    self.aggr_frame = DataFrame(col)
                else:
                    self.aggr_frame = self.aggr_frame.join(col, how="outer")
            except:
                pass



    def get_aggregate(self, variable, filter_by=None):
        """
        Returns aggregate spending, and number of beneficiaries
        for the relevant entity level

        Parameters
        ----------
        variable : string
                   name of the variable aggregated according to its entity
        """

        WEIGHT = model.WEIGHT
        simulation = self.simulation


        def aggregate(var, filter_by):  # TODO: should be a method of Presta
            varcol  = simulation.get_col(var)
            entity = varcol.entity
            # amounts and beneficiaries from current data and default data if exists
            data, data_default = simulation.aggregated_by_entity(entity, [var], all_output_vars = False, force_sum = True)

            filter = 1
            if filter_by is not None:
                data_filter, data_default_filter = simulation.aggregated_by_entity(entity, [filter_by], all_output_vars = False, force_sum = True)
                filter = data_filter[filter_by]
            datasets = {'data': data}
            m_b = {}
            weight = data[WEIGHT]*filter
            if data_default is not None:
                datasets['default'] = data_default

            for name, data in datasets.iteritems():
                montants = data[var]
                beneficiaires = data[var].values != 0
                try:
                    amount = int(round(sum(montants*weight)/10**6))
                except:
                    amount = nan
                try:
                    benef = int(round(sum(beneficiaires*weight)/10**3))
                except:
                    benef = nan

                m_b[name] = [amount, benef]

            return m_b

        return aggregate(variable, filter_by)


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
        self.aggr_frame[self.labels['dep_real']] = A
        self.aggr_frame[self.labels['benef_real']] = B


    def compute_diff(self):
        '''
        Computes and adds relative differences
        '''

        dep   = self.aggr_frame[self.labels['dep']]
        benef = self.aggr_frame[self.labels['benef']]

        if self.show_default:
            ref_dep_label, ref_benef_label = self.labels['dep_default'], self.labels['benef_default']
            if ref_dep_label not in self.aggr_frame:
                return
        elif self.show_real:
            ref_dep_label, ref_benef_label = self.labels['dep_real'], self.labels['benef_real']
        else:
            return

        ref_dep = self.aggr_frame[ref_dep_label]
        ref_benef = self.aggr_frame[ref_benef_label]

        self.aggr_frame[self.labels['dep_diff_rel']]   = (dep-ref_dep)/abs(ref_dep)
        self.aggr_frame[self.labels['benef_diff_rel']] = (benef-ref_benef)/abs(ref_benef)
        self.aggr_frame[self.labels['dep_diff_abs']]   = (dep-ref_dep)
        self.aggr_frame[self.labels['benef_diff_abs']] = (benef-ref_benef)



    def load_amounts_from_file(self, filename = None, year = None):
        '''
        Loads totals from files
        '''
        from pandas import HDFStore
        if year is None:
            year     = self.simulation.datesim.year
        if filename is None:
            data_dir = model.DATA_DIR


        try:
            filename = os.path.join(data_dir, "amounts.h5")
            store = HDFStore(filename)

            df_a = store['amounts']
            df_b = store['benef']
            store.close()
            self.totals_df = DataFrame(data = { "amount" : df_a[year]/10**6, "benef": df_b[year]/1000 } )
            row = DataFrame({'amount': nan, 'benef': nan}, index = ['logt'])
            self.totals_df = self.totals_df.append(row)

            # Add some aditionnals totals
            for col in ['amount', 'benef']:

                # Deals with logt
                logt = 0
                for var in ['apl', 'alf', 'als']:
                    logt += self.totals_df.get_value(var, col)
                self.totals_df.set_value('logt', col,  logt)

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
            warnings.warn(" No administrative data available for year %s in file %s" %( str(year), filename))
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
            df = self.aggr_frame
            if table_format == "xls":
                writer = ExcelWriter(str(fname))
                df.to_excel(writer, "aggregates", index= False, header= True)
                descr = self.create_description()
                descr.to_excel(writer, "description", index = False, header=False)
                writer.save()
            elif table_format =="csv":
                df.to_csv(fname, "aggregates", index= False, header = True)

        except Exception, e:
                raise Exception("Aggregates: Error saving file", str(e))


    def create_description(self):
        '''
        Creates a description dataframe
        '''
        now = datetime.now()
        descr =  [u'OpenFisca',
                         u'Calculé le %s à %s' % (now.strftime('%d-%m-%Y'), now.strftime('%H:%M')),
                         u'Système socio-fiscal au %s' % self.simulation.datesim,
                         u"Données d'enquêtes de l'année %s" %str(self.simulation.input_table.survey_year) ]
        return DataFrame(descr)


    def clear(self):
        self.data = None
        self.data_default = None
        self.totals_df = None

    def get_aggregates(self, variable):
        self.aggr_frame

