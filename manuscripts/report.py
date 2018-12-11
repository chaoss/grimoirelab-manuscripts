#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Script for producing Reports from data in ElasticSearch
#
# Copyright (C) 2016 Bitergia
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
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

import logging
import os
import subprocess
import sys
import glob

import matplotlib as mpl
# This avoids the use of the $DISPLAY value for the charts
mpl.use('Agg')
import matplotlib.pyplot as plt
import prettyplotlib as ppl
import numpy as np

from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file

from dateutil import parser, relativedelta

from .metrics import git
from .metrics import jira
from .metrics import github_issues
from .metrics import github_prs
from .metrics import mls
from .metrics import gerrit
from .metrics import stackexchange

from .metrics.metrics import Metrics

logger = logging.getLogger(__name__)


class Report():
    """ Class which represents a Manuscripts report """

    # Elasticsearch index names in which metrics data is stored
    GIT_INDEX = 'git'
    GITHUB_ISSUES_INDEX = 'github_issues'
    GITHUB_PRS_INDEX = 'github_issues'
    JIRA_INDEX = 'jira'
    EMAIL_INDEX = 'mbox_enrich'
    GERRIT_INDEX = 'gerrit'
    STACHEXCHANGE_INDEX = 'stackoverflow'
    GLOBAL_PROJECT = 'general'
    TOP_MAX = 20

    # Helper dict to map a data source class with its Elasticsearch index
    ds2index = {
        gerrit.Gerrit: GERRIT_INDEX,
        git.Git: GIT_INDEX,
        github_issues.GitHubIssues: GITHUB_ISSUES_INDEX,
        github_prs.GitHubPRs: GITHUB_PRS_INDEX,
        jira.Jira: JIRA_INDEX,
        mls.MLS: EMAIL_INDEX,
        stackexchange.Stackexchange: STACHEXCHANGE_INDEX
    }

    # Helper dict to map a data source name with its python class
    ds2class = {
        "gerrit": gerrit.Gerrit,
        "git": git.Git,
        "github_issues": github_issues.GitHubIssues,
        "github_prs": github_prs.GitHubPRs,
        "jira": jira.Jira,
        "mailinglist": mls.MLS,
        "stackexchange": stackexchange.Stackexchange
    }

    # A reverse dictionary to get the data sources for the corresponding classes
    class2ds = {val: key for key, val in ds2class.items()}

    # GrimoireLab data sources supported by Manuscripts
    supported_data_sources = ['git', 'github', 'gerrit', 'mls']
    supported_data_sources += ['github_issues', 'github_prs']
    supported_data_sources += ['jira']
    supported_data_sources += ['stackexchange']

    def __init__(self, es_url, start, end, data_dir=None, filters=None,
                 interval="month", offset=None, data_sources=None,
                 report_name=None, projects=False, indices=[], logo=None):
        """
        Report init method called when creating a new Report object

        :param es_url: Elasticsearch URL in which metrics data is stored
        :param start: start (from) date from which to compute the metrics
        :param end: end (to) date form which to compute the metrics
        :param data_dir: directory in which to store the data results for the report
        :param filters: additional filters to be added to all metrics queries
        :param interval: time interval used in Elasticsearch to aggregate the metrics data
        :param offset: time offset in days to be added to the intervals
        :param data_sources: list of data sources to be included in the report
        :param report_name: name of the report (used in the title for example)
        :param projects: generate a specific report for each project
        :param indices: list of data source indices in Elasticsearch to be used to get the metrics values
        :param logo: logo to be used in the report (in the title and headers of the pages)
        """

        if not (es_url and start and end and data_sources):
            logger.error('''Missing needed params for Report:
                            elastic_url, end_date, start_date and data_sources''')
            sys.exit(1)

        self.es_url = es_url
        self.start = start
        self.end = end
        self.data_dir = data_dir
        self.logo = logo
        self.filters = filters  # Report filters for all metrics in the report
        if self.filters:
            # Use the filters as core filters for all the metrics in the report
            Metrics.filters_core = self.filters
        self.offset = offset
        if self.offset:
            # Offset to be used in all the metrics in the report
            Metrics.offset = self.offset
        self.interval = interval
        if self.interval:
            # Interval to be used in all the metrics in the report
            Metrics.interval = self.interval
        if self.interval not in ['year', 'quarter', 'month']:
            raise RuntimeError("Interval not supported ", interval)
        if self.interval == 'month':
            self.end_prev_month = end - relativedelta.relativedelta(months=1)
        elif self.interval == 'quarter':
            self.end_prev_month = end - relativedelta.relativedelta(months=3)
        elif self.interval == 'year':
            self.end_prev_month = end - relativedelta.relativedelta(months=12)

        # Create a dict of indices which, for each data_source, will give the
        # name of the elasticsearch index that has to be used.
        self.index_dict = defaultdict(lambda: None)
        for pos, index in enumerate(indices):
            self.index_dict[data_sources[pos]] = index

        # Just include the supported data sources
        self.data_sources = list(set(data_sources) & set(self.supported_data_sources))

        # Temporal hack
        mls_index = None
        for mls_ds in ['mbox', 'pipermail']:
            if mls_ds in data_sources:
                # Get the custom index name for mailing lists if provided
                mls_index = mls_index or self.index_dict[mls_ds]
                self.data_sources.append('mailinglist')
                if mls_ds in self.index_dict.keys():
                    del self.index_dict[mls_ds]
        # Set custom index for mailing lists if exists
        if mls_index:
            self.index_dict['mailinglist'] = mls_index

        if 'github' in data_sources:
            # Get the custom index name for github
            github_index = self.index_dict['github']
            # In mordred github issues and prs are managed together
            self.data_sources.remove('github')
            self.data_sources += ['github_issues', 'github_prs']
            # Set the indices of issues and prs as the same custom index provided
            self.index_dict['github_issues'] = github_index
            self.index_dict['github_prs'] = github_index
            del self.index_dict['github']

        self.data_sources = list(set(self.data_sources))
        # End temporal hack
        self.config = self.__get_config(self.data_sources)
        self.report_name = report_name
        self.projects = projects

    def __get_config(self, data_sources=None):
        """
        Build a dictionary with the Report configuration with the data sources and metrics to be included
        in each section of the report
        :param data_sources: list of data sources to be included in the report
        :return: a dict with the data sources and metrics to be included in the report
        """

        if not data_sources:
            # For testing
            data_sources = ["gerrit", "git", "github_issues", "mls"]

        # In new_config a dict with all the metrics for all data sources is created
        new_config = {}
        for ds in data_sources:
            ds_config = self.ds2class[ds].get_section_metrics()
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

        # Fields that are not linked to a data source
        new_config['overview']['activity_file_csv'] = "data_source_evolution.csv"
        new_config['overview']['efficiency_file_csv'] = "efficiency.csv"
        new_config['project_process']['time_to_close_title'] = "Days to close (median and average)"
        new_config['project_process']['time_to_close_review_title'] = "Days to close review (median and average)"

        for i in range(0, len(data_sources)):
            ds = data_sources[i]
            ds_config = self.ds2class[ds].get_section_metrics()
            activity_metrics = ds_config['project_activity']['metrics']
            new_config['project_activity']['ds' + str(i + 1) + "_metrics"] = activity_metrics

        return new_config

    def __convert_none_to_zero(self, ts):
        """
        Convert None values to 0 so the data works with Matplotlib
        :param ts:
        :return: a list with 0s where Nones existed
        """

        if not ts:
            return ts

        ts_clean = [val if val else 0 for val in ts]

        return ts_clean

    def bar3_chart(self, title, labels, data1, file_name, data2, data3, legend=["", ""]):
        """
        Generate a bar plot with three columns in each x position and save it to file_name

        :param title: title to be used in the chart
        :param labels: list of labels for the x axis
        :param data1: values for the first columns
        :param file_name: name of the file in which to save the chart
        :param data2: values for the second columns
        :param data3: values for the third columns
        :param legend: legend to be shown in the chart
        :return:
        """

        colors = ["orange", "grey"]

        data1 = self.__convert_none_to_zero(data1)
        data2 = self.__convert_none_to_zero(data2)
        data3 = self.__convert_none_to_zero(data3)

        fig, ax = plt.subplots(1)
        xpos = np.arange(len(data1))
        width = 0.28

        plt.title(title)
        y_pos = np.arange(len(data1))

        ppl.bar(xpos + width + width, data3, color="orange", width=0.28, annotate=True)
        ppl.bar(xpos + width, data1, color='grey', width=0.28, annotate=True)
        ppl.bar(xpos, data2, grid='y', width=0.28, annotate=True)
        plt.xticks(xpos + width, labels)
        plt.legend(legend, loc=2)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        plt.savefig(file_name)
        plt.close()

    def bar_chart(self, title, labels, data1, file_name, data2=None, legend=["", ""]):
        """
        Generate a bar plot with one or two columns in each x position and save it to file_name

        :param title: title to be used in the chart
        :param labels: list of labels for the x axis
        :param data1: values for the first columns
        :param file_name: name of the file in which to save the chart
        :param data2: values for the second columns. If None only one column per x position is shown.
        :param legend: legend to be shown in the chart
        :return:
        """

        colors = ["orange", "grey"]

        data1 = self.__convert_none_to_zero(data1)
        data2 = self.__convert_none_to_zero(data2)

        fig, ax = plt.subplots(1)
        xpos = np.arange(len(data1))
        width = 0.35

        plt.title(title)
        y_pos = np.arange(len(data1))

        if data2 is not None:
            ppl.bar(xpos + width, data1, color="orange", width=0.35, annotate=True)
            ppl.bar(xpos, data2, grid='y', width=0.35, annotate=True)
            plt.xticks(xpos + width, labels)
            plt.legend(legend, loc=2)

        else:
            ppl.bar(xpos, data1, grid='y', annotate=True)
            plt.xticks(xpos + width, labels)

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        plt.savefig(file_name)
        plt.close()

    def get_metric_index(self, metric_cls):
        """
        Get the index name with the data for a metric class
        :param metric_cls: a metric class
        :return: the name of the index with the data for the metric
        """
        ds = self.class2ds[metric_cls.ds]
        if self.index_dict[ds]:
            index_name = self.index_dict[ds]
        else:
            index_name = self.ds2index[metric_cls.ds]
        return index_name

    def sec_overview(self):
        """
        Generate the data for the Overview section in the report
        :return:
        """

        """ Data sources overview: table with metric summaries"""
        metrics = self.config['overview']['activity_metrics']
        file_name = self.config['overview']['activity_file_csv']

        data_path = os.path.join(self.data_dir, "data")
        file_name = os.path.join(data_path, file_name)

        logger.debug("CSV file %s generation in progress", file_name)

        csv = 'metricsnames,netvalues,relativevalues,datasource\n'
        for metric in metrics:
            # comparing current metric month count with previous month
            es_index = self.get_metric_index(metric)
            ds = metric.ds.name
            m = metric(self.es_url, es_index, start=self.start, end=self.end)
            (last, percentage) = m.get_trend()
            csv += "%s,%i,%i,%s" % (metric.name, last, percentage, ds)
            csv += "\n"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "w") as f:
            # Hack, we need to fix LaTeX escaping in a central place
            csv = csv.replace("_", r"\_")
            f.write(csv)

        logger.debug("CSV file: %s was generated", file_name)

        """
        Git Authors:

        description: average number of developers per month by quarters
        (so we have the average number of developers per month during
        those three months). If the approach is to work at the level of month,
        then just the number of developers per month.
        """

        author = self.config['overview']['author_metrics'][0]
        csv_labels = 'labels,' + author.id
        file_label = author.ds.name + "_" + author.id
        title_label = author.name + " per " + self.interval
        self.__create_csv_eps(author, None, csv_labels, file_label, title_label)

        logger.debug("CSV file %s generation in progress", file_name)

        bmi = []
        ttc = []  # time to close

        csv_labels = ''
        for m in self.config['overview']['bmi_metrics']:
            metric = m(self.es_url, self.get_metric_index(m),
                       start=self.end_prev_month, end=self.end)
            csv_labels += m.id + ","
            bmi.append(metric.get_agg())

        for m in self.config['overview']['time_to_close_metrics']:
            metric = m(self.es_url, self.get_metric_index(m),
                       start=self.end_prev_month, end=self.end)
            csv_labels += m.id + ","
            ttc.append(metric.get_agg())

        csv = csv_labels[:-1] + "\n"  # remove last comma
        csv = csv.replace("_", "")
        for val in bmi:
            csv += "%s," % (self.str_val(val))
        for val in ttc:
            csv += "%s," % (self.str_val(val))
        if csv[-1] == ',':
            csv = csv[:-1]

        data_path = os.path.join(self.data_dir, "data")
        file_name = os.path.join(data_path, 'efficiency.csv')
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "w") as f:
            f.write(csv)

        logger.debug("CSV file: %s was generated", file_name)

    def sec_com_channels(self):
        """
        Generate the data for the Communication Channels section in the report
        :return:
        """

        metrics = self.config['com_channels']['activity_metrics']
        metrics += self.config['com_channels']['author_metrics']
        for metric in metrics:
            csv_labels = 'labels,' + metric.id
            file_label = metric.ds.name + "_" + metric.id
            title_label = metric.name + " per " + self.interval
            self.__create_csv_eps(metric, None, csv_labels, file_label, title_label)

    @classmethod
    def str_val(cls, val):
        """
        Format the value of a metric value to a string

        :param val: number to be formatted
        :return: a string with the formatted value
        """

        str_val = val
        if val is None:
            str_val = "NA"
        elif type(val) == float:
            str_val = '%0.2f' % val
        else:
            str_val = str(val)
        return str_val

    def __create_csv_eps(self, metric1, metric2, csv_labels, file_label,
                         title_label, project=None):
        """
        Generate the CSV data and EPS figs files for two metrics
        :param metric1: first metric class
        :param metric2: second metric class
        :param csv_labels: labels to be used in the CSV file
        :param file_label: shared filename token to be included in csv and eps files
        :param title_label: title for the EPS figures
        :param project: name of the project for which to generate the data
        :return:
        """

        logger.debug("CSV file %s generation in progress", file_label)

        esfilters = None
        csv_labels = csv_labels.replace("_", "")  # LaTeX not supports

        if project and project != self.GLOBAL_PROJECT:
            esfilters = {"project": project}
        m1 = metric1(self.es_url, self.get_metric_index(metric1),
                     esfilters=esfilters,
                     start=self.start, end=self.end)
        m1_ts = m1.get_ts()

        if metric2:
            m2 = metric2(self.es_url, self.get_metric_index(metric2),
                         esfilters=esfilters,
                         start=self.start, end=self.end)
            m2_ts = m2.get_ts()

        csv = csv_labels + '\n'
        for i in range(0, len(m1_ts['date'])):
            if self.interval == 'quarter':
                date_str = self.build_period_name(parser.parse(m1_ts['date'][i]), start_date=True)
            else:
                date_str = parser.parse(m1_ts['date'][i]).strftime("%y-%m")
            csv += date_str
            csv += "," + self.str_val(m1_ts['value'][i])
            if metric2:
                csv += "," + self.str_val(m2_ts['value'][i])
            csv += "\n"

        data_path = os.path.join(self.data_dir, "data")

        if project:
            file_name = os.path.join(data_path, file_label + "_" + project + ".csv")
        else:
            file_name = os.path.join(data_path, file_label + ".csv")

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, "w") as f:
            f.write(csv)

        logger.debug("CSV file %s was generated", file_label)

        fig_path = os.path.join(self.data_dir, "figs")

        if project:
            file_name = os.path.join(fig_path, file_label + "_" + project + ".eps")
            title = title_label + ": " + project
        else:
            file_name = os.path.join(fig_path, file_label + ".eps")
            title = title_label

        if self.interval != 'quarter':
            x_val = [parser.parse(val).strftime("%y-%m") for val in m1_ts['date']]
        else:
            x_val = []
            for val in m1_ts['date']:
                period = self.build_period_name(parser.parse(val), start_date=True)
                x_val.append(period)
        if metric2:
            self.bar_chart(title, x_val, m1_ts['value'],
                           file_name, m2_ts['value'],
                           legend=[m1.name, m2.name])
        else:
            self.bar_chart(title, x_val, m1_ts['value'], file_name,
                           legend=[m1.name])

    def sec_project_activity(self, project=None):
        """
        Generate the data for the Activity section in the report
        :return:
        """

        def create_data(metrics, project):
            csv_labels = "labels" + ',' + metrics[0].id + "," + metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            title_label = metrics[0].name + ", " + metrics[1].name + " per " + self.interval
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels,
                                  file_label, title_label, project)

        logger.info("Activity data for: %s", project)

        for activity_ds in self.config['project_activity']:
            if activity_ds == 'metrics':
                continue  # all metrics included
            metrics = self.config['project_activity'][activity_ds]
            create_data(metrics, project)

    def sec_project_community(self, project=None):
        """
        Generate the data for the Communication section in a Project report
        :return:
        """

        def create_csv(metric1, csv_labels, file_label):
            esfilters = None
            csv_labels = csv_labels.replace("_", "")  # LaTeX not supports "_"
            if project != self.GLOBAL_PROJECT:
                esfilters = {"project": project}

            data_path = os.path.join(self.data_dir, "data")

            file_name = os.path.join(data_path, file_label + "_" + project + ".csv")

            logger.debug("CSV file %s generation in progress", file_name)

            m1 = metric1(self.es_url, self.get_metric_index(metric1),
                         esfilters=esfilters, start=self.end_prev_month, end=self.end)
            top = m1.get_list()
            csv = csv_labels + '\n'
            for i in range(0, len(top['value'])):
                if i > self.TOP_MAX:
                    break
                csv += top[metric1.FIELD_NAME][i] + "," + self.str_val(top['value'][i])
                csv += "\n"

            with open(file_name, "w") as f:
                f.write(csv)

            logger.debug("CSV file %s was generated", file_name)

        logger.info("Community data for: %s", project)

        author = self.config['project_community']['author_metrics'][0]
        csv_labels = 'labels,' + author.id
        file_label = author.ds.name + "_" + author.id
        title_label = author.name + " per " + self.interval
        self.__create_csv_eps(author, None, csv_labels, file_label, title_label,
                              project)

        """
        Main developers

        """
        metric = self.config['project_community']['people_top_metrics'][0]
        # TODO: Commits must be extracted from metric
        csv_labels = author.id + ",commits"
        file_label = author.ds.name + "_top_" + author.id
        create_csv(metric, csv_labels, file_label)

        """
        Main organizations

        """
        orgs = self.config['project_community']['orgs_top_metrics'][0]
        # TODO: Commits must be extracted from metric
        csv_labels = orgs.id + ",commits"
        file_label = orgs.ds.name + "_top_" + orgs.id
        create_csv(orgs, csv_labels, file_label)

    def sec_project_process(self, project=None):
        """
        Generate the data for the Process section in a Project report
        :return:
        """

        logger.info("Process data for: %s", project)

        """
        BMI Pull Requests, BMI Issues

        description: closed PRs/issues out of open PRs/issues in a period of time
        """
        for i in range(0, len(self.config['project_process']['bmi_metrics'])):
            metric = self.config['project_process']['bmi_metrics'][i]
            csv_labels = "labels" + "," + metric.id
            file_label = metric.ds.name + "_" + metric.id
            title_label = metric.name
            self.__create_csv_eps(metric, None, csv_labels, file_label, title_label,
                                  project)

        """
        Time to close Issues

        description: median and mean time to close issues
        """

        if len(self.config['project_process']['time_to_close_metrics']) > 0:
            metrics = self.config['project_process']['time_to_close_metrics']
            csv_labels = "labels" + ',' + metrics[0].id + "," + metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            # title_label = metrics[0].name + ", " + metrics[1].name + " per "+ self.interval
            title_label = self.config['project_process']['time_to_close_title']
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels, file_label,
                                  title_label, project)

        """
        Time to close PRs and gerrit reviews

        description: median and mean time to close prs and gerrit reviews
        """
        if len(self.config['project_process']['time_to_close_review_metrics']) > 0:
            metrics = self.config['project_process']['time_to_close_review_metrics']
            i = 0
            while i < len(metrics):
                # Generate the metrics in data source pairs.
                # TODO: convert to tuples metrics
                csv_labels = "labels" + ',' + metrics[i].id + "," + metrics[i + 1].id
                file_label = metrics[i].ds.name + "_" + metrics[i].id + "_"
                file_label += metrics[i + 1].ds.name + "_" + metrics[i + 1].id
                # title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
                title_label = self.config['project_process']['time_to_close_review_title']
                self.__create_csv_eps(metrics[i], metrics[i + 1], csv_labels, file_label,
                                      title_label, project)
                i = i + 2

        """
        Patchsets per review

        description: median and average of the number of patchsets per review
        """
        if self.config['project_process']['patchsets_metrics']:
            metrics = self.config['project_process']['patchsets_metrics']
            csv_labels = "labels" + ',' + metrics[0].id + "," + metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            # title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
            title_label = self.config['project_process']['patchsets_title']
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels, file_label,
                                  title_label, project)

    def sec_projects(self):
        """
        Generate the report projects related sections: the general project is included always and add
        to the global report, and an specific report for each project is generated if configured.
        :return:
        """

        """
        This activity is displayed at the general level, aggregating all
        of the projects, with the name 'general' and per project using
        the name of each project. This activity is divided into three main
        sections: activity, community and process.
        """

        # First the 'general' project
        self.sec_project_activity(self.GLOBAL_PROJECT)
        self.sec_project_community(self.GLOBAL_PROJECT)
        self.sec_project_process(self.GLOBAL_PROJECT)

        if not self.projects:
            # Don't generate per project data
            return

        # Just one level projects supported yet

        # First we need to get the list of projects per data source and
        # join all lists in the overall projects list

        projects_lists = self.config['overview']['projects_metrics']

        projects = []
        for p in projects_lists:
            p_list = p(self.es_url, self.get_metric_index(p),
                       start=self.start).get_list()['project']
            projects += p_list

        projects = list(set(projects))

        project_str = "\n".join(projects)

        with open(os.path.join(self.data_dir, "projects.txt"), "w") as f:
            f.write(project_str)

        for project in projects:
            # The name of the project is used to create files
            project = project.replace("/", "_")
            self.sec_project_activity(project)
            self.sec_project_community(project)
            self.sec_project_process(project)

    def sections(self):
        """
        Get the sections of the report and howto build them.

        :return: a dict with the method to be called to fill each section of the report
        """
        secs = OrderedDict()
        secs['Overview'] = self.sec_overview
        secs['Communication Channels'] = self.sec_com_channels
        secs['Detailed Activity by Project'] = self.sec_projects

        return secs

    def create_data_figs(self):
        """
        Generate the data and figs files for the report

        :return:
        """

        logger.info("Generating the report data and figs from %s to %s",
                    self.start, self.end)

        for section in self.sections():
            logger.info("Generating %s", section)
            self.sections()[section]()

        logger.info("Data and figs done")

    @classmethod
    def build_period_name(cls, pdate, interval='quarter', offset=None, start_date=False):
        """
        Build the period name for humans (eg, 18-Q2) to be used in the reports.
        Just supporting quarters right now.
        The name is built using the last month for the quarter.

        :param pdate: the date (datetime) which defines the period
        :param interval: the time interval (string)  used in the report
        :param start_date: if False, pdate is the end of the period date
        :return: the period name for humans (eg, 18-Q2)
        """

        if interval not in ['quarter']:
            raise RuntimeError("Interval not support in build_period_name", interval)

        name = pdate.strftime('%Y-%m-%d') + ' ' + interval
        months_in_quarter = 3
        end_quarter_month = None

        if interval == 'quarter':
            if offset:
                # +31d offset format
                offset_days = int(offset[1:-1])
                pdate = pdate - timedelta(days=offset_days)
            if not start_date:
                # pdate param is the first day of the next quarter
                # Remove one day to have a date in the end_quarter_month
                pdate = pdate.replace(day=1) - timedelta(days=1)
                year = pdate.strftime('%y')
                end_quarter_month = int(pdate.strftime('%m'))
            else:
                # pdate param is the first day of the period
                # add months_in_quarter to have the last month of the quarter
                year = pdate.strftime('%y')
                end_quarter_month = int(pdate.strftime('%m')) + months_in_quarter - 1

            quarter = int(round(int(end_quarter_month) / months_in_quarter, 0))
            name = year + "-Q" + str(quarter)

        return name

    @staticmethod
    def replace_text(filepath, to_replace, replacement):
        """
        Replaces a string in a given file with another string

        :param file: the file in which the string has to be replaced
        :param to_replace: the string to be replaced in the file
        :param replacement: the string which replaces 'to_replace' in the file
        """
        with open(filepath) as file:
            s = file.read()
        s = s.replace(to_replace, replacement)
        with open(filepath, 'w') as file:
            file.write(s)

    def replace_text_dir(self, directory, to_replace, replacement, file_type=None):
        """
        Replaces a string with its replacement in all the files in the directory

        :param directory: the directory in which the files have to be modified
        :param to_replace: the string to be replaced in the files
        :param replacement: the string which replaces 'to_replace' in the files
        :param file_type: file pattern to match the files in which the string has to be replaced
        """
        if not file_type:
            file_type = "*.tex"
        for file in glob.iglob(os.path.join(directory, file_type)):
            self.replace_text(file, to_replace, replacement)

    def create_pdf(self):
        """
        Create the report pdf file filling the LaTeX templates with the figs and data for the report

        :return:
        """

        logger.info("Generating PDF report")

        # First step is to create the report dir from the template
        report_path = self.data_dir
        templates_path = os.path.join(os.path.dirname(__file__),
                                      "latex_template")

        # Copy the data generated to be used in LaTeX template
        copy_tree(templates_path, report_path)

        # if user specified a logo then replace it with default logo
        if self.logo:
            os.remove(os.path.join(report_path, "logo.eps"))
            os.remove(os.path.join(report_path, "logo-eps-converted-to.pdf"))
            print(copy_file(self.logo, os.path.join(report_path, "logo." + self.logo.split('/')[-1].split('.')[-1])))

        # Change the project global name
        project_replace = self.report_name.replace(' ', r'\ ')
        self.replace_text_dir(report_path, 'PROJECT-NAME', project_replace)
        self.replace_text_dir(os.path.join(report_path, 'overview'), 'PROJECT-NAME', project_replace)

        # Change the quarter subtitle
        if self.interval == "quarter":
            build_period_name = self.build_period_name(self.end, self.interval, self.offset)
        else:
            build_period_name = self.start.strftime("%y-%m") + "-" + self.end.strftime("%y-%m")
        period_replace = build_period_name.replace(' ', r'\ ')
        self.replace_text_dir(report_path, '2016-QUARTER', period_replace)
        self.replace_text_dir(os.path.join(report_path, 'overview'), '2016-QUARTER', period_replace)

        # Report date frame
        quarter_start = self.end - relativedelta.relativedelta(months=3)
        quarter_start += relativedelta.relativedelta(days=1)
        dateframe = (quarter_start.strftime('%Y-%m-%d') + " to " + self.end.strftime('%Y-%m-%d')).replace(' ', r'\ ')
        self.replace_text_dir(os.path.join(report_path, 'overview'), 'DATEFRAME', dateframe)

        # Change the date Copyright
        self.replace_text_dir(report_path, '(cc) 2016', '(cc) ' + datetime.now().strftime('%Y'))

        # Fix LaTeX special chars
        self.replace_text_dir(report_path, '&', '\&', 'data/git_top_organizations_*')
        self.replace_text_dir(report_path, '^#', '', 'data/git_top_organizations_*')

        # Activity section
        activity = ''
        for activity_ds in ['git', 'github', 'gerrit', 'mls']:
            if activity_ds in self.data_sources:
                activity += r"\input{activity/" + activity_ds + ".tex}"

        with open(os.path.join(report_path, "activity.tex"), "w") as flatex:
            flatex.write(activity)

        # Community section
        community = ''
        for community_ds in ['git', 'mls']:
            if community_ds in self.data_sources:
                community += r"\input{community/" + community_ds + ".tex}"

        with open(os.path.join(report_path, "community.tex"), "w") as flatex:
            flatex.write(community)

        # Overview section
        overview = r'\input{overview/summary.tex}'
        for overview_ds in ['github', 'gerrit']:
            if overview_ds in self.data_sources:
                overview += r"\input{overview/efficiency-" + overview_ds + ".tex}"

        with open(os.path.join(report_path, "overview.tex"), "w") as flatex:
            flatex.write(overview)

        # Process section
        process = ''
        for process_ds in ['github_prs', 'gerrit']:
            if process_ds in self.data_sources:
                process += r"\input{process/" + process_ds + ".tex}"

        if not process:
            process = "Unfortunately, this section is empty because there are no supported sources available to perform this kind of analysis."

        with open(os.path.join(report_path, "process.tex"), "w") as flatex:
            flatex.write(process)

        # Time to generate the pdf report
        res = subprocess.call("pdflatex report.tex", shell=True, cwd=report_path)
        if res > 0:
            logger.error("Error generating PDF")
            return
        # A second time so the TOC is generated
        subprocess.call("pdflatex report.tex", shell=True, cwd=report_path)

        logger.info("PDF report done %s", report_path + "/report.pdf")

    def create(self):
        """
        Generate the data and figs for the report and fill the LaTeX templates with them
        to generate a PDF file with the report.

        :return:
        """
        logger.info("Generating the report from %s to %s", self.start, self.end)

        self.create_data_figs()
        self.create_pdf()

        logger.info("Report completed")

    @classmethod
    def get_core_filters(cls, filters):
        core_filters = {}
        if not filters:
            return core_filters
        for f in filters:
            name = f.split(":")[0]
            value = f.split(":")[1]
            core_filters[name] = value
        return core_filters
