# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Pranjal Aswani <aswani.pranjal@gmail.com>
#


import sys
from datetime import datetime
from dateutil import parser

sys.path.insert(0, '..')

import pandas as pd
from numpy.testing import assert_array_equal

from manuscripts2.metrics import github_prs
from manuscripts2.elasticsearch import Query, Index, get_trend
from base import TestBaseElasticSearch


ENRICH_INDEX = "github_prs_enrich"

# All values as seen on 2018-07-10
OPENED_TREND_LAST = 6
OPENED_TREND_PRECENTAGE = -33

CLOSED_TREND_LAST = 5
CLOSED_TREND_PRECENTAGE = -60

BMI_PR = 0.91
TIME_TO_CLOSE_DAYS_PR_MEDIAN = 2.71

# files
SUBMITTED_PRS_BY_MONTH = "data/test_data/github_submitted_prs_per_month.csv"
CLOSED_PRS_BY_MONTH = "data/test_data/github_closed_prs_per_month.csv"
TIME_TO_CLOSE_DAYS_MEDIAN_TS = "data/test_data/time_to_close_prs_days_median.csv"
TIME_TO_CLOSE_DAYS_AVERAGE_TS = "data/test_data/time_to_close_prs_days_average.csv"
BMI_PR_PER_MONTH = "data/test_data/github_prs_bmipr.csv"


class TestGitHubPRs(TestBaseElasticSearch):
    """
    Test the github_pull_requests data source.
    """

    def setUp(self):
        """
        Set up the necessary functions to run unittests.
        """

        self.github = ENRICH_INDEX
        self.github_index = Index(self.github,
                                  TestGitHubPRs.es)

        Query.interval_ = "month"

        # Make sure to change the CONSTANTS defined above if you change
        # the end date here before testing because tests might fail otherwise
        self.start = datetime(2015, 1, 1)  # from date
        self.end = datetime(2018, 7, 10)  # to date

    def test_submitted_prs(self):
        """
        Test the submitted pull requests metric.
        """

        submitted = github_prs.SubmittedPRs(self.github_index, self.start, self.end)
        last, trend_percentage = get_trend(submitted.timeseries())
        self.assertEquals(last, OPENED_TREND_LAST)
        self.assertEquals(trend_percentage, OPENED_TREND_PRECENTAGE)

    def test_closed_prs(self):
        """
        Test the closed pull requests metric.
        """

        closed = github_prs.ClosedPRs(self.github_index, self.start, self.end)
        last, trend_percentage = get_trend(closed.timeseries())
        self.assertEquals(last, CLOSED_TREND_LAST)
        self.assertEquals(trend_percentage, CLOSED_TREND_PRECENTAGE)

    def test_bmipr(self):
        """
        Test the closed BMIPR metric.
        """

        bmi_pr = github_prs.BMIPR(self.github_index, self.start, self.end)
        bmi_pr = bmi_pr.aggregations()
        bmi_pr = "%.2f" % bmi_pr
        bmi_pr = float(bmi_pr)
        self.assertEquals(bmi_pr, BMI_PR)

    def test_time_to_close_days_pr_median(self):
        """
        Test the the Days to close median PR metric aggregations.
        """

        days_to_close_pr_median = github_prs.DaysToClosePRMedian(self.github_index, self.start, self.end)
        ttc = days_to_close_pr_median.aggregations()
        ttc = "%.2f" % ttc
        ttc = float(ttc)
        self.assertEquals(ttc, TIME_TO_CLOSE_DAYS_PR_MEDIAN)

    def test_closed_prs_timeseries_non_df(self):
        """
        Test if the timeseries for closed prs metrics
        are returned correctly or not.
        """

        closed_prs = github_prs.ClosedPRs(self.github_index, self.start, self.end)
        closed_prs_ts = closed_prs.timeseries()
        closed_prs_test = pd.read_csv(CLOSED_PRS_BY_MONTH)
        closed_prs_test['date'] = [parser.parse(item).date() for item in closed_prs_test['date']]
        assert_array_equal(closed_prs_test['date'], closed_prs_ts['date'])
        assert_array_equal(closed_prs_test['value'], closed_prs_ts['value'])

    def test_closed_prs_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for closed prs metrics
        are returned correctly or not.
        """

        closed_prs = github_prs.ClosedPRs(self.github_index, self.start, self.end)
        closed_prs_ts = closed_prs.timeseries(dataframe=True)
        closed_prs_test = pd.read_csv(CLOSED_PRS_BY_MONTH)
        self.assertIsInstance(closed_prs_ts, pd.DataFrame)
        assert_array_equal(closed_prs_test['value'], closed_prs_ts['value'])

    def test_opened_prs_timeseries_non_df(self):
        """
        Test if the timeseries for submitted prs metrics
        are returned correctly or not.
        """

        opened_prs = github_prs.SubmittedPRs(self.github_index, self.start, self.end)
        opened_prs_ts = opened_prs.timeseries()
        opened_prs_test = pd.read_csv(SUBMITTED_PRS_BY_MONTH)
        opened_prs_test['date'] = [parser.parse(item).date() for item in opened_prs_test['date']]
        assert_array_equal(opened_prs_test['date'], opened_prs_ts['date'])
        assert_array_equal(opened_prs_test['value'], opened_prs_ts['value'])

    def test_opened_prs_timeseries_with_df(self):
        """
        Test if the timeseries dataframe for submitted prs metrics
        are returned correctly or not.
        """

        opened_prs = github_prs.SubmittedPRs(self.github_index, self.start, self.end)
        opened_prs_ts = opened_prs.timeseries(dataframe=True)
        opened_prs_test = pd.read_csv(SUBMITTED_PRS_BY_MONTH)
        self.assertIsInstance(opened_prs_ts, pd.DataFrame)
        assert_array_equal(opened_prs_test['value'], opened_prs_ts['value'])

    def test_time_to_close_days_pr_median_timeseries(self):
        """
        Test if the timeseries dataframe for the metrics related to the median values of number
        of days it took to close an pull requests are returned correctly or not.
        """

        median_values = github_prs.DaysToClosePRMedian(self.github_index, self.start, self.end)
        median_values_ts = median_values.timeseries(dataframe=True)
        median_values_test = pd.read_csv(TIME_TO_CLOSE_DAYS_MEDIAN_TS)
        self.assertIsInstance(median_values_ts, pd.DataFrame)
        assert_array_equal(median_values_test['value'], median_values_ts['value'])

    def test_time_to_close_days_pr_average_timeseries(self):
        """
        Test if the timeseries dataframe for the metrics related to the average values of number
        of days it took to close an pull requests are returned correctly or not.
        """

        average_values = github_prs.DaysToClosePRAverage(self.github_index, self.start, self.end)
        average_values_ts = average_values.timeseries(dataframe=True)
        average_values_test = pd.read_csv(TIME_TO_CLOSE_DAYS_AVERAGE_TS)
        self.assertIsInstance(average_values_ts, pd.DataFrame)
        assert_array_equal(average_values_test['value'], average_values_ts['value'])

    def test_bmipr_timeseries(self):
        """
        Test if timeseries dataframe for the BMI pull requests metrics are returned correctly
        or not.
        """

        bmi_values = github_prs.BMIPR(self.github_index, self.start, self.end)
        bmi_values_ts = bmi_values.timeseries(dataframe=True)
        bmi_values_test = pd.read_csv(BMI_PR_PER_MONTH)
        self.assertIsInstance(bmi_values_ts, pd.DataFrame)
        assert_array_equal(bmi_values_test['bmi'], bmi_values_ts['bmi'])
