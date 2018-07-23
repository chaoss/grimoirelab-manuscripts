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


class GitMetrics():
    """Root of all metric classes based on queries to a git enriched index.

    This class is not intended to be instantiated, but to be
    extened by child classes that will populate self.query with real
    queries.

    :param index: index object
    """

    def __init__(self, index, start, end):

        self.query = Query(index)
        self.start = start
        self.end = end
        self.query.since(self.start).until(self.end)

    def timeseries(self):
        """Obtain a time series from the current query"""

        return self.query.get_timeseries(dataframe=True)

    def aggregations(self):
        """Obtain a single valued aggregation from the current query"""

        return self.query.get_aggs()


class Commits(GitMetrics):
    """Class for computing the "commits" metric.

    :param index: index object
    """

    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "commits"
        self.name = "Commits"
        self.desc = "Changes to the source code"
        self.query = self.query.get_cardinality("hash").by_period()


class Authors(GitMetrics):
    """
    class for computing the "Authors" metric

    :param:
    """
    def __init__(self, index, start, end):
        super().__init__(index, start, end)
        self.id = "authors"
        self.name = "Authors"
        self.desc = "People authoring commits (changes to source code)"
        self.query = self.query.get_cardinality("author_uuid").by_period()


def overview(index, start, end):
    """Compute metrics in the overview section for enriched git indexes.

    Returns a dictionary. Each key in the dictionary is the name of
    a metric, the value is the value of that metric. Value can be
    a complex object (eg, a time series).

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
