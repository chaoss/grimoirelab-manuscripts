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

from manuscripts2.elasticsearch import Query
from manuscripts2.utils import get_prev_month


class GitMetrics():
    """Root of all metric classes based on queries to a git enriched index.

    This class is not intended to be instantiated, but to be
    extened by child classes that will populate self.query with real
    queries.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    DS_NAME = "git"

    def __init__(self, index, start, end):

        self.query = Query(index)
        self.start = start
        self.end = end
        self.query.since(self.start).until(self.end)

    def timeseries(self, dataframe=False):
        """Obtain a time series from the current query.

        :param dataframe: if true, return results as a pandas.DataFrame
        :return: return the date histogram aggregations
        """

        return self.query.get_timeseries(dataframe=dataframe)

    def aggregations(self):
        """Obtain a single valued aggregation from the current query."""

        return self.query.get_aggs()


class Commits(GitMetrics):
    """Class for computing the "commits" metric.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "commits"
        self.name = "Commits"
        self.desc = "Changes to the source code"
        self.query = self.query.get_cardinality("hash").by_period()


class Authors(GitMetrics):
    """Class for computing the "Authors" metric.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "authors"
        self.name = "Authors"
        self.desc = "People authoring commits (changes to source code)"

    def aggregations(self):
        """
        Override parent method. Obtain list of the terms and their corresponding
        values using "terms" aggregations for the previous time period.

        :returns: a data frame containing terms and their corresponding values
        """

        prev_month_start = get_prev_month(self.end, self.query.interval_)
        self.query.since(prev_month_start)
        self.query.get_terms("author_name")
        return self.query.get_list(dataframe=True)

    def timeseries(self, dataframe=False):
        """Get the date histogram aggregations.

        :param dataframe: if true, return a pandas.DataFrame object
        """

        self.query.get_cardinality("author_uuid").by_period()
        return super().timeseries(dataframe)


class Organizations(GitMetrics):
    """Projects in the source code management system

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "organizations"
        self.name = "Organizations"
        self.desc = "Organizations in the source code management system"

    def aggregations(self):
        """
        Override parent method. Obtain list of the terms and their corresponding
        values using "terms" aggregations for the previous time period.

        :returns: a data frame containing terms and their corresponding values
        """

        prev_month_start = get_prev_month(self.end, self.query.interval_)
        self.query.since(prev_month_start)
        self.query.get_terms("author_org_name")
        return self.query.get_list(dataframe=True)


def overview(index, start, end):
    """Compute metrics in the overview section for enriched git indexes.

    Returns a dictionary. Each key in the dictionary is the name of
    a metric, the value is the value of that metric. Value can be
    a complex object (eg, a time series).

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "activity_metrics": [Commits(index, start, end)],
        "author_metrics": [Authors(index, start, end)],
        "bmi_metrics": [],
        "time_to_close_metrics": [],
        "projects_metrics": []
    }

    return results


def project_activity(index, start, end):
    """Compute the metrics for the project activity section of the enriched
    git index.

    Returns a dictionary containing a "metric" key. This key contains the
    metrics for this section.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "metrics": [Commits(index, start, end),
                    Authors(index, start, end)]
    }

    return results


def project_community(index, start, end):
    """Compute the metrics for the project community section of the enriched
    git index.

    Returns a dictionary containing "author_metrics", "people_top_metrics"
    and "orgs_top_metrics" as the keys and the related Metrics as the values.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "author_metrics": [Authors(index, start, end)],
        "people_top_metrics": [Authors(index, start, end)],
        "orgs_top_metrics": [Organizations(index, start, end)],
    }

    return results


def project_process(index, start, end):
    """Compute the metrics for the project process section of the enriched
    git index.

    Returns a dictionary containing "bmi_metrics", "time_to_close_metrics",
    "time_to_close_review_metrics" and patchsets_metrics as the keys and
    the related Metrics as the values.

    :param index: index object
    :param start: start date to get the data from
    :param end: end date to get the data upto
    :return: dictionary with the value of the metrics
    """

    results = {
        "bmi_metrics": [],
        "time_to_close_metrics": [],
        "time_to_close_review_metrics": [],
        "patchsets_metrics": []
    }

    return results
