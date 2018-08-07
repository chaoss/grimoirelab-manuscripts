#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
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
# Author:
#   Pranjal Aswani <aswani.pranjal@gmail.com>

from manuscripts2.elasticsearch import PullRequests, calculate_bmi
from manuscripts2.utils import get_prev_month


class GitHubPRsMetrics():
    """Root of all metric classes based on queries to a github
    pull requests metrics.

    This class is not intended to be instantiated, but to be
    extened by child classes that will populate self.query with real
    queries.

    :param index: index object
    :param start: date to apply the filters from
    :param end: date to apply the filters upto
    """

    DS_NAME = "github_prs"

    def __init__(self, index, start, end):
        self.query = PullRequests(index)
        self.start = start
        self.end = end
        self.query.since(self.start).until(self.end)

    def timeseries(self, dataframe=False):
        """Obtain a time series from the current query."""

        return self.query.get_timeseries(dataframe=dataframe)

    def aggregations(self):
        """Obtain a single valued aggregation from the current query."""

        return self.query.get_aggs()


class SubmittedPRs(GitHubPRsMetrics):
    """Class for computing submitted pull requests metrics.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "submitted"
        self.name = "Submitted reviews"
        self.desc = "Number of submitted code review processes"
        self.query.get_cardinality("id").by_period()


class ClosedPRs(GitHubPRsMetrics):
    """Class for computing closed pull requests metrics.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "closed"
        self.name = "Closed reviews"
        self.desc = "Number of closed review processes (merged or abandoned)"
        self.query.is_closed()
        self.query.get_cardinality("id").by_period()


class DaysToClosePRMedian(GitHubPRsMetrics):
    """Class for computing the metrics related to median values
    for the number days it took to close a pull request.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "days_to_close_pr_median"
        self.name = "Days to close reviews (median)"
        self.desc = "Number of days needed to close a review (median)"
        self.query.is_closed()
        self.query.get_percentiles("time_to_close_days")

    def aggregations(self):
        """Get the single valued aggregations with respect to the
        previous time interval."""

        prev_month_start = get_prev_month(self.end, self.query.interval_)
        self.query.since(prev_month_start)
        agg = super().aggregations()
        if agg is None:
            agg = 0  # None is because NaN in ES. Let's convert to 0
        return agg

    def timeseries(self, dataframe=False):
        """Get the date histogram aggregations.

        :param dataframe: if true, return a pandas.DataFrame object
        """

        self.query.by_period()
        ts = super().timeseries(dataframe=dataframe)
        ts['value'] = ts['value'].apply(lambda x: float("%.2f" % x))
        return ts


class DaysToClosePRAverage(GitHubPRsMetrics):
    """Class for computing the metrics related to average values
    for the number days it took to close a pull request.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "days_to_close_pr_average"
        self.name = "Days to close reviews (average)"
        self.desc = "Number of days needed to close a review (average)"
        self.query.is_closed()
        self.query.get_average("time_to_close_days")

    def timeseries(self, dataframe=False):
        """Get the date histogram aggregations.

        :param dataframe: if true, return a pandas.DataFrame object
        """

        self.query.by_period()
        ts = super().timeseries(dataframe=dataframe)
        ts['value'] = ts['value'].apply(lambda x: float("%.2f" % x))
        return ts


class BMIPR():
    """This class calculates the efficiency of closing reviews. It is
    calculated as the number of closed prs out of the total number of
    submitted ones in a period.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    DS_NAME = "github_prs"

    def __init__(self, index, start, end):
        self.start = start
        self.end = end
        self.id = "bmipr"
        self.name = "BMI Pull Requests"
        self.desc = "Efficiency reviewing: (closed prs)/(submitted prs)"
        self.closed = ClosedPRs(index, start, end)
        self.opened = SubmittedPRs(index, start, end)

    def aggregations(self):
        """Get the single valued aggregations with respect to the
        previous time interval."""

        prev_month_start = get_prev_month(self.end,
                                          self.closed.query.interval_)
        self.closed.query.since(prev_month_start,
                                field="updated_at")
        closed_agg = self.closed.aggregations()
        self.opened.query.since(prev_month_start)
        opened_agg = self.opened.aggregations()

        if opened_agg == 0:
            bmi = 1.0  # if no submitted issues/prs, bmi is at 100%
        else:
            bmi = closed_agg / opened_agg
        return bmi

    def timeseries(self, dataframe=False):
        """Get BMIPR as a time series."""

        closed_timeseries = self.closed.timeseries(dataframe=dataframe)
        opened_timeseries = self.opened.timeseries(dataframe=dataframe)
        return calculate_bmi(closed_timeseries, opened_timeseries)


def overview(index, start, end):
    """Compute metrics in the overview section for enriched github issues
    indexes.
    Returns a dictionary. Each key in the dictionary is the name of
    a metric, the value is the value of that metric. Value can be
    a complex object (eg, a time series).

    :param index: index object
    :param start: date to apply the filters from
    :param end: date to apply the filters upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "activity_metrics": [SubmittedPRs(index, start, end),
                             ClosedPRs(index, start, end)],
        "author_metrics": [],
        "bmi_metrics": [BMIPR(index, start, end)],
        "time_to_close_metrics": [DaysToClosePRMedian(index, start, end)],
        "projects_metrics": []
    }

    return results


def project_activity(index, start, end):
    """Compute the metrics for the project activity section of the enriched
    github pull requests index.

    Returns a dictionary containing a "metric" key. This key contains the
    metrics for this section.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "metrics": [SubmittedPRs(index, start, end),
                    ClosedPRs(index, start, end)]
    }

    return results


def project_community(index, start, end):
    """Compute the metrics for the project community section of the enriched
    github pull requests index.

    Returns a dictionary containing "author_metrics", "people_top_metrics"
    and "orgs_top_metrics" as the keys and the related Metrics as the values.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "author_metrics": [],
        "people_top_metrics": [],
        "orgs_top_metrics": [],
    }

    return results


def project_process(index, start, end):
    """Compute the metrics for the project process section of the enriched
    github issues index.

    Returns a dictionary containing "bmi_metrics", "time_to_close_metrics",
    "time_to_close_review_metrics" and patchsets_metrics as the keys and
    the related Metrics as the values.
    time_to_close_title and time_to_close_review_title contain the file names
    to be used for time_to_close_metrics and time_to_close_review_metrics
    metrics data.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "bmi_metrics": [BMIPR(index, start, end)],
        "time_to_close_metrics": [],
        "time_to_close_review_metrics": [DaysToClosePRAverage(index, start, end),
                                         DaysToClosePRMedian(index, start, end)],
        "patchsets_metrics": []
    }

    return results
