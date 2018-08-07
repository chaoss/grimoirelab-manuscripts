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

from manuscripts2.elasticsearch import Issues, calculate_bmi
from manuscripts2.utils import get_prev_month


class GitHubIssuesMetrics():
    """Root of all metric classes based on queries to a github
    enriched issues index.

    This class is not intended to be instantiated, but to be
    extened by child classes that will populate self.query with real
    queries.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    DS_NAME = "github_issues"

    def __init__(self, index, start, end):
        self.query = Issues(index)
        self.start = start
        self.end = end
        self.query.since(self.start).until(self.end)

    def timeseries(self, dataframe=False):
        """Obtain a time series from the current query."""

        return self.query.get_timeseries(dataframe=dataframe)

    def aggregations(self):
        """Obtain a single valued aggregation from the current query."""

        return self.query.get_aggs()


class OpenedIssues(GitHubIssuesMetrics):
    """Class for computing opened issues metrics.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "opened"
        self.name = "Opened tickets"
        self.desc = "Number of opened tickets"
        self.query.get_cardinality("id").by_period()


class ClosedIssues(GitHubIssuesMetrics):
    """Class for computing closed issues metrics.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "closed"
        self.name = "Closed tickets"
        self.desc = "Number of closed tickets"
        self.query.is_closed()\
                  .since(self.start, field="closed_at")\
                  .until(self.end, field="closed_at")
        self.query.get_cardinality("id").by_period(field="closed_at")


class DaysToCloseMedian(GitHubIssuesMetrics):
    """Class for computing the metrics related to median values
    for the number of days to close a github issue.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "days_to_close_ticket_median"
        self.name = "Days to close tickets (median)"
        self.desc = "Number of days needed to close a ticket (median)"
        self.query.is_closed()
        self.query.get_percentiles("time_to_close_days")

    def aggregations(self):
        """Get the single valued aggregations for current query
        with respect to the previous time interval."""

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


class DaysToCloseAverage(GitHubIssuesMetrics):
    """Class for computing the metrics related to average values
    for the number of days to close a github issue.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "days_to_close_ticket_average"
        self.name = "Days to close tickets (average)"
        self.desc = "Number of days needed to close a ticket (average)"
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


class BMI():
    """The Backlog Management Index measures efficiency dealing with tickets.

    This is based on the book "Metrics and Models in Software Quality
    Engineering. Chapter 4.3.1. By Stephen H. Kan.
    BMI is calculated as the number of closed tickets out of the opened
    tickets in a given interval. This metric aims at having an overview of
    how the community deals with tickets. Continuous values under 1
    (or 100 if this is calculated as a percentage) shows low peformance
    given that the community leaves a lot of opened tickets. Continuous
    values close to 1 or over 1 shows a better performance. This would
    indicate that most of the tickets are being closed.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    DS_NAME = "github_issues"

    def __init__(self, index, start, end):
        self.start = start
        self.end = end
        self.id = "bmi_tickets"
        self.name = "Backlog Management Index"
        self.desc = "Number of tickets closed out of the opened ones in a given interval"
        self.closed = ClosedIssues(index, start, end)
        self.opened = OpenedIssues(index, start, end)

    def aggregations(self):
        """Get the aggregation value for BMI with respect to the previous
        time interval."""

        prev_month_start = get_prev_month(self.end,
                                          self.closed.query.interval_)
        self.closed.query.since(prev_month_start,
                                field="closed_at")
        closed_agg = self.closed.aggregations()
        self.opened.query.since(prev_month_start)
        opened_agg = self.opened.aggregations()
        if opened_agg == 0:
            bmi = 1.0  # if no submitted issues/prs, bmi is at 100%
        else:
            bmi = closed_agg / opened_agg
        return bmi

    def timeseries(self, dataframe=False):
        """Get BMI as a time series."""

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
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "activity_metrics": [OpenedIssues(index, start, end),
                             ClosedIssues(index, start, end)],
        "author_metrics": [],
        "bmi_metrics": [BMI(index, start, end)],
        "time_to_close_metrics": [DaysToCloseMedian(index, start, end)],
        "projects_metrics": []
    }

    return results


def project_activity(index, start, end):
    """Compute the metrics for the project activity section of the enriched
    github issues index.

    Returns a dictionary containing a "metric" key. This key contains the
    metrics for this section.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "metrics": [OpenedIssues(index, start, end),
                    ClosedIssues(index, start, end)]
    }

    return results


def project_community(index, start, end):
    """Compute the metrics for the project community section of the enriched
    github issues index.

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
        "bmi_metrics": [BMI(index, start, end)],
        "time_to_close_metrics": [DaysToCloseAverage(index, start, end),
                                  DaysToCloseMedian(index, start, end)],
        "time_to_close_review_metrics": [],
        "patchsets_metrics": []
    }

    return results
