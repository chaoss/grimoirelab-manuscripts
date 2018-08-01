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

sys.path.insert(0, '..')


from manuscripts2.metrics import github_prs
from manuscripts2.elasticsearch import Query, Index, get_trend
from base import TestBaseElasticSearch


NAME = "github_prs"
ENRICH_INDEX = "github_prs_enrich"

# All values as seen on 2018-07-10
OPENED_TREND_LAST = 6
OPENED_TREND_PRECENTAGE = -33

CLOSED_TREND_LAST = 5
CLOSED_TREND_PRECENTAGE = -60

BMI_PR = 0.91
TIME_TO_CLOSE_DAYS_PR_MEDIAN = 2.71


class TestGitHubPRs(TestBaseElasticSearch):
    """
    Test the github_pull_requests data source.
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
