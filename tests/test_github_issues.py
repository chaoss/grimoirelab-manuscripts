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

from manuscripts2.metrics import github_issues
from manuscripts2.elasticsearch import Query, Index, get_trend
from base import TestBaseElasticSearch


NAME = "github_issues"
ENRICH_INDEX = "github_issues_enrich"

# All values as seen on 2018-07-10
OPENED_TREND_LAST = 1
OPENED_TREND_PRECENTAGE = -100

CLOSED_TREND_LAST = 0
CLOSED_TREND_PRECENTAGE = -100

BMITICKETS = 0.67
TIME_TO_CLOSE_DAYS_MEDIAN = 2.10

# files
CLOSED_ISSUES_BY_MONTH = "data/test_data/github_closed_issues_per_month.csv"
OPENED_ISSUES_BY_MONTH = "data/test_data/github_opened_issues_per_month.csv"


class TestGitHubIssues(TestBaseElasticSearch):
    """
    Test the github_issues data source.
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

        self.github = ENRICH_INDEX
        self.github_index = Index(index_name=self.github,
                                  es=TestGitHubIssues.es)

        Query.interval_ = "month"

        # Make sure to change the CONSTANTS defined above if you change
        # the end date here before testing because tests might fail otherwise
        self.start = datetime(2015, 1, 1)  # from date
        self.end = datetime(2018, 7, 10)  # to date

    def test_opened_issues_trend(self):
        """
        Test the the opened issues metric trend.
        """

        opened_issues = github_issues.OpenedIssues(self.github_index, self.start, self.end)
        last, trend_percentage = get_trend(opened_issues.timeseries())
        self.assertEquals(last, OPENED_TREND_LAST)
        self.assertEquals(trend_percentage, OPENED_TREND_PRECENTAGE)

    def test_closed_issues_trend(self):
        """
        Test the the closed issues metric trend.
        """

        closed_issues = github_issues.ClosedIssues(self.github_index, self.start, self.end)
        last, trend_percentage = get_trend(closed_issues.timeseries())
        self.assertEquals(last, CLOSED_TREND_LAST)
        self.assertEquals(trend_percentage, CLOSED_TREND_PRECENTAGE)

    def test_BMI_tickets_aggregation(self):
        """
        Test the the BMI metric aggregations.
        """

        bmi = github_issues.BMI(self.github_index, self.start, self.end)
        bmitickets = bmi.aggregations()
        bmitickets = "%.2f" % bmitickets
        bmitickets = float(bmitickets)
        self.assertEquals(bmitickets, BMITICKETS)

    def test_days_to_close_median_aggregation(self):
        """
        Test the the Days to close median metric aggregations.
        """

        days_to_close_median = github_issues.DaysToCloseMedian(self.github_index, self.start, self.end)
        ttc = days_to_close_median.aggregations()
        ttc = "%.2f" % ttc
        ttc = float(ttc)
        self.assertEquals(ttc, TIME_TO_CLOSE_DAYS_MEDIAN)

    def test_closed_issues_timeseries_non_df(self):
        """
        Test if the timeseries for closed issues metrics
        are returned correctly or not.
        """

        closed_issues = github_issues.ClosedIssues(self.github_index, self.start, self.end)
        closed_issues_ts = closed_issues.timeseries()
        closed_issues_test = pd.read_csv(CLOSED_ISSUES_BY_MONTH)
        closed_issues_test['date'] = [parser.parse(item).date() for item in closed_issues_test['date']]
        assert_array_equal(closed_issues_test['date'], closed_issues_ts['date'])
        assert_array_equal(closed_issues_test['value'], closed_issues_ts['value'])

    def test_closed_issues_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for closed issues metrics
        are returned correctly or not.
        """

        closed_issues = github_issues.ClosedIssues(self.github_index, self.start, self.end)
        closed_issues_ts = closed_issues.timeseries(dataframe=True)
        closed_issues_test = pd.read_csv(CLOSED_ISSUES_BY_MONTH)
        self.assertIsInstance(closed_issues_ts, pd.DataFrame)
        assert_array_equal(closed_issues_test['value'], closed_issues_ts['value'])

    def test_opened_issues_timeseries_non_df(self):
        """
        Test if the timeseries for opened issues metrics
        are returned correctly or not.
        """

        opened_issues = github_issues.OpenedIssues(self.github_index, self.start, self.end)
        opened_issues_ts = opened_issues.timeseries()
        opened_issues_test = pd.read_csv(OPENED_ISSUES_BY_MONTH)
        opened_issues_test['date'] = [parser.parse(item).date() for item in opened_issues_test['date']]
        assert_array_equal(opened_issues_test['date'], opened_issues_ts['date'])
        assert_array_equal(opened_issues_test['value'], opened_issues_ts['value'])

    def test_opened_issues_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for opened issues metrics
        are returned correctly or not.
        """

        opened_issues = github_issues.OpenedIssues(self.github_index, self.start, self.end)
        opened_issues_ts = opened_issues.timeseries(dataframe=True)
        opened_issues_test = pd.read_csv(OPENED_ISSUES_BY_MONTH)
        self.assertIsInstance(opened_issues_ts, pd.DataFrame)
        assert_array_equal(opened_issues_test['value'], opened_issues_ts['value'])
