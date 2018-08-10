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

from utils import load_json_file
from base import TestBaseElasticSearch


ENRICH_INDEX = "git_enrich"

# All values as seen on 2018-07-10
TREND_LAST = 12
TREND_PRECENTAGE = -41

# files
AUTHORS_BY_PERIOD = "data/test_data/git_authors_by_months.csv"
COMMITS_BY_PERIOD = "data/test_data/git_commits_by_months.csv"
TOP_AUTHORS = "data/test_data/git_top_authors.json"
TOP_ORGANIZATIONS = "data/test_data/git_top_organizations.json"


class TestGit(TestBaseElasticSearch):
    """
    Test the git data source.
    """

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

    def test_commits_timeseries_non_df(self):
        """
        Test if the timeseries for commits metrics are returned
        correctly or not.
        """

        commits = git.Commits(self.git_index, self.start, self.end)
        commits_ts = commits.timeseries()
        commits_test = pd.read_csv(COMMITS_BY_PERIOD)
        commits_test['date'] = [parser.parse(item).date() for item in commits_test['date']]
        assert_array_equal(commits_test['value'], commits_ts['value'])
        assert_array_equal(commits_test['date'], commits_ts['date'])

    def test_commits_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for commits metrics are returned
        correctly or not.
        """

        commits = git.Commits(self.git_index, self.start, self.end)
        commits_ts = commits.timeseries(dataframe=True)
        commits_test = pd.read_csv(COMMITS_BY_PERIOD)
        self.assertIsInstance(commits_ts, pd.DataFrame)
        assert_array_equal(commits_test['value'], commits_ts['value'])

    def test_authors_timeseries_non_df(self):
        """
        Test if the timeseries for author metrics are returned
        correctly or not.
        """

        authors = git.Authors(self.git_index, self.start, self.end)
        authors_ts = authors.timeseries()
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        authors_test['date'] = [parser.parse(item).date() for item in authors_test['date']]
        assert_array_equal(authors_test['value'], authors_ts['value'])
        assert_array_equal(authors_test['date'], authors_ts['date'])

    def test_authors_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for author metrics are
        returned correctly or not.
        """

        authors = git.Authors(self.git_index, self.start, self.end)
        authors_ts = authors.timeseries(dataframe=True)
        authors_test = pd.read_csv(AUTHORS_BY_PERIOD)
        self.assertIsInstance(authors_ts, pd.DataFrame)
        assert_array_equal(authors_test['value'], authors_ts['value'])

    def test_authors_list(self):
        """
        Test if the list of top authors is returned correctly or not.
        """

        authors = git.Authors(self.git_index, self.start, self.end)
        authors_list = authors.aggregations()
        authors_test = load_json_file(TOP_AUTHORS)
        assert_array_equal(authors_list['keys'], authors_test['keys'])
        assert_array_equal(authors_list['values'], authors_test['values'])

    def test_organization_list(self):
        """
        Test if the list of top organizations is returned correctly or not.
        """

        orgs = git.Organizations(self.git_index, self.start, self.end)
        orgs_list = orgs.aggregations()
        orgs_test = load_json_file(TOP_ORGANIZATIONS)
        assert_array_equal(orgs_list['keys'], orgs_test['keys'])
        assert_array_equal(orgs_list['values'], orgs_test['values'])
