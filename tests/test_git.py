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
from datetime import datetime
from dateutil import parser

sys.path.insert(0, '..')

import pandas as pd
from numpy.testing import assert_array_equal

from manuscripts2.metrics import git
from manuscripts2.elasticsearch import Query, Index, get_trend
from base import TestBaseElasticSearch


NAME = "git_commit"
ENRICH_INDEX = "git_enrich"

# All values as seen on 2018-07-10
TREND_LAST = 12
TREND_PRECENTAGE = -41

# files
AUTHORS_BY_PERIOD = "data/git_authors_by_months.csv"


class TestGit(TestBaseElasticSearch):
    """
    Test the git data source.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup necessary infrastructure to test the functions.
        """

        cls.name = NAME
        cls.enrich_index = ENRICH_INDEX
        super().setUpClass()

    def setUp(self):
        """
        Set up the necessary functions to run unittests.
        """

        self.git_index = Index(index_name=ENRICH_INDEX,
                               es=TestGit.es)

        # Set the interval for the data that is to be tested
        # This will set the interval for all the query objects used
        Query.interval_ = "month"

        # Make sure to change the CONSTANTS defined above if you change
        # the end date here before testing because tests might fail otherwise
        self.start = datetime(2015, 1, 1)  # from date
        self.end = datetime(2018, 7, 10)  # to date

    def test_commits_trend(self):
        """
        Test the aggregations for Commits class.
        """

        commits = git.Commits(self.git_index, self.start, self.end)
        last, trend_percentage = get_trend(commits.timeseries())
        self.assertEquals(last, TREND_LAST)
        self.assertEquals(trend_percentage, TREND_PRECENTAGE)

    def test_authors_timeseries_non_df(self):
        """
        Test if the timeseries for author metrics are returned
        correctly or not.
        """

        authors_ts = git.Authors(self.git_index, self.start, self.end)
        authors = authors_ts.timeseries()
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        authors_test['date'] = [parser.parse(item).date() for item in authors_test['date']]
        assert_array_equal(authors_test['value'], authors['value'])
        assert_array_equal(authors_test['date'], authors['date'])

    def test_authors_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for author metrics are
        returned correctly or not.
        """

        authors_ts = git.Authors(self.git_index, self.start, self.end)
        authors = authors_ts.timeseries(dataframe=True)
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        self.assertIsInstance(authors, pd.DataFrame)
        assert_array_equal(authors_test['value'], authors['value'])
