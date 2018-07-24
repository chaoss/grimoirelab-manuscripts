#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CHAOSS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#     Pranjal Aswani <aswani.pranjal@gmail.com>


import sys
import unittest
from datetime import datetime
from dateutil import parser

sys.path.insert(0, '..')

import pandas as pd
from numpy.testing import assert_array_equal
from elasticsearch import Elasticsearch

from manuscripts2.metrics import git
from manuscripts2.elasticsearch import Query, Index, get_trend
from utils import setup_data_source, teardown_data_source, DATA_SOURCES


ES_URL = "http://localhost:9200"

# All values as seen on 2018-07-10
TREND_LAST = 12
TREND_PRECENTAGE = -41

# files
AUTHORS_BY_PERIOD = "data/git_authors_by_months.csv"


class TestGit(unittest.TestCase):
    """
    Test the git data source
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup necessary infrastructure to test the functions
        """

        cls.git = DATA_SOURCES['git']
        setup_data_source('git', cls.git[0], cls.git[1])

    def setUp(self):
        """
        Set up the necessary functions to run unittests
        """

        self.es = Elasticsearch(ES_URL)
        self.git = DATA_SOURCES['git']
        self.git_index = Index(self.git[1])

        # Set the interval for the data that is to be tested
        # This will set the interval for all the query objects used
        Query.interval_ = "month"

        # Make sure to change the CONSTANTS defined above if you change
        # the end date here before testing because tests might fail otherwise
        self.start = datetime(2015, 1, 1)  # from date
        self.end = datetime(2018, 7, 10)  # to date

    def test_overview_trend(self):
        """
        Test if activity metrics are returned correctly or not
        """

        overview = git.overview(self.git_index, self.start, self.end)

        last, trend_percentage = get_trend(overview['activity_metrics'][0].timeseries())
        self.assertEquals(last, TREND_LAST)
        self.assertEquals(trend_percentage, TREND_PRECENTAGE)

    def test_overview_timeseries_non_df(self):
        """
        Test if author metrics are returned correctly or not
        """

        overview = git.overview(self.git_index, self.start, self.end)

        authors = overview['author_metrics'][0].timeseries()
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        authors_test['date'] = [parser.parse(item).date() for item in authors_test['date']]
        assert_array_equal(authors_test['value'], authors['value'])
        assert_array_equal(authors_test['date'], authors['date'])

    def test_overview_timeseries_with_df(self):
        """
        Test if author metrics are returned correctly or not
        """

        overview = git.overview(self.git_index, self.start, self.end)

        authors = overview['author_metrics'][0].timeseries(dataframe=True)
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        self.assertIsInstance(authors, pd.DataFrame)
        assert_array_equal(authors_test['value'], authors['value'])

    @classmethod
    def tearDownClass(cls):
        """
        Destroy the infrastructure created for unittests
        """

        teardown_data_source(cls.git[0], cls.git[1])
