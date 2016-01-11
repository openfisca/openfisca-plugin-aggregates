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


import openfisca_france
from openfisca_france.surveys import SurveyScenario
from openfisca_survey_manager.surveys import SurveyCollection
from openfisca_plugin_aggregates.aggregates import Aggregates


def create_survey_scenario(year = None):
    assert year is not None
    openfisca_survey_collection = SurveyCollection.load(collection = "openfisca")
    openfisca_survey = openfisca_survey_collection.surveys["openfisca_data_{}".format(year)]
    input_data_frame = openfisca_survey.get_values(table = "input")
    input_data_frame.reset_index(inplace = True)
    assert "wprm" in input_data_frame.columns
    TaxBenefitSystem = openfisca_france.init_country()
    tax_benefit_system = TaxBenefitSystem()
    survey_scenario = SurveyScenario().init_from_data_frame(
        input_data_frame = input_data_frame,
        tax_benefit_system= tax_benefit_system,
        year = year,
        )
    return survey_scenario


def test_aggregates(year = 2006):
    survey_scenario = create_survey_scenario(year)
    aggregates = Aggregates()
    aggregates.set_survey_scenario(survey_scenario)
    aggregates.compute_aggregates()
    print aggregates.aggr_frame
    aggregates.compute()


if __name__ == '__main__':
    import logging
    log = logging.getLogger(__name__)
    import sys
    logging.basicConfig(level = logging.INFO, stream = sys.stdout)
    test_aggregates()
