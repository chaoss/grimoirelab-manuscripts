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
#

import os
import logging

from collections import defaultdict

from elasticsearch import Elasticsearch

from .elasticsearch import (Query,
                            Index,
                            get_trend)

from .metrics import git
from .metrics import github_prs
from .metrics import github_issues

logger = logging.getLogger(__name__)


def create_csv(filename, csv_data, mode="w"):
    with open(filename, mode) as f:
        csv_data.replace("_", r"\_")
        f.write(csv_data)


class Report():

    # Elasticsearch index names in which metrics data is stored
    GIT_INDEX = 'git'
    GITHUB_ISSUES_INDEX = 'github_issues'
    GITHUB_PRS_INDEX = 'github_prs'

    # Helper dict to map a data source class with its Elasticsearch index
    class2index = {
        git.GitMetrics: GIT_INDEX,
        github_issues.IssuesMetrics: GITHUB_ISSUES_INDEX,
        github_prs.PullRequestsMetrics: GITHUB_PRS_INDEX,
    }

    # Helper dict to map a data source name with its python class
    ds2class = {
        "git": git.GitMetrics,
        "github_issues": github_issues.IssuesMetrics,
        "github_prs": github_prs.PullRequestsMetrics,
    }

    def __init__(self, es_url=None, start=None, end=None, data_dir=None, filters=None,
                 interval="month", offset=None, data_sources=None,
                 report_name=None, projects=False, indices=[], logo=None):

        Query.interval_ = interval

        self.es = "http://localhost:9200"
        self.es_client = Elasticsearch(self.es)
        # Set the client for all metrics
        Index.es = self.es_client

        self.data_dir = data_dir
        self.index_dict = defaultdict(lambda: None)
        for pos, index in enumerate(indices):
            self.index_dict[data_sources[pos]] = Index(index_name=index)

        self.config = self.__get_config(data_sources=data_sources)

    def get_metric_index(self, data_source):
        if data_source in self.index_dict:
            return self.index_dict[data_source]
        else:
            return Index(index_name=self.class2index[self.ds2class[data_source]])

    def __get_config(self, data_sources=None):

        if not data_sources:
            # For testing
            data_sources = ["git", "github_issues", "github_prs"]

        # In new_config a dict with all the metrics for all data sources is created
        new_config = {}
        for index, ds in enumerate(data_sources):
            metric_class = self.ds2class[ds]
            metric_index = self.get_metric_index(ds)
            ds_config = metric_class(metric_index).get_section_metrics()

            for section in ds_config:
                if section not in new_config:
                    # Just create the section with the data for the ds
                    new_config[section] = ds_config[section]
                else:
                    for metric_section in ds_config[section]:
                        if ds_config[section][metric_section] is not None:
                            if (metric_section not in new_config[section] or
                                new_config[section][metric_section] is None):
                                new_config[section][metric_section] = ds_config[section][metric_section]
                            else:
                                new_config[section][metric_section] += ds_config[section][metric_section]

            activity_metrics = ds_config['project_activity']['metrics']
            new_config['project_activity']['ds' + str(index + 1) + "_metrics"] = activity_metrics

        # Fields that are not linked to a data source
        new_config['overview']['activity_file_csv'] = "data_source_evolution.csv"
        new_config['overview']['efficiency_file_csv'] = "efficiency.csv"
        new_config['project_process']['time_to_close_title'] = "Days to close (median and average)"
        new_config['project_process']['time_to_close_review_title'] = "Days to close review (median and average)"

        return new_config

    def get_activity_metrics(self):

        metrics = self.config['overview']['activity_metrics']
        file_name = self.config['overview']['activity_file_csv']
        data_path = os.path.join(self.data_dir, "data")
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        file_name = os.path.join(data_path, file_name)

        logger.debug("CSV file %s generation in progress", file_name)

        csv = "metricsnames, netvalues, relativevalues, datasource\n"

        for metric in metrics:
            (last, percentage) = get_trend(metric.get_timeseries())
            csv += "{}, {}, {}, {}\n".format(metric.index.index_name, last,
                                             percentage, metric.index.index_name)

        create_csv(file_name, csv)
