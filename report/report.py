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
# git.Authors:
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

import configparser
import logging
import os

import matplotlib as mpl
# This avoids the use of the $DISPLAY value for the charts
mpl.use('Agg')
import matplotlib.pyplot as plt
import prettyplotlib as ppl
import numpy as np

from datetime import date, timedelta, timezone
from collections import OrderedDict

from dateutil import parser, relativedelta

from .metrics import git
from .metrics import github
from .metrics import mls
from .metrics import its
from .metrics import gerrit

from .metrics.metrics import Metrics

class Report():
    GIT_INDEX = 'git_enrich'
    GITHUB_INDEX = 'github_issues_enrich'
    ITS_INDEX = 'github_issues_enrich'
    EMAIL_INDEX = 'mbox_enrich'
    GERRIT_INDEX = 'gerrit'
    GLOBAL_PROJECT = 'general'
    TOP_MAX = 20

    ds2index = {
        gerrit.Gerrit: GERRIT_INDEX,
        git.Git: GIT_INDEX,
        github.GitHub: GITHUB_INDEX,
        mls.MLS: EMAIL_INDEX,
        its.ITS: ITS_INDEX
    }

    def __init__(self, es_url, start, end, data_dir=None, filters=None,
                 interval="month", offset=None, config_file=None):
        self.es_url = es_url
        self.start = start
        self.end = end
        self.data_dir = data_dir
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
        self.config = self.__get_config(config_file)

    def __get_config(self, config_file):
        config = {}
        if config_file:
            parser = configparser.ConfigParser()
            parser.read(config_file)
            sec = parser.sections()
            for s in sec:
                config[s] = {}
                opti = parser.options(s)
                for o in opti:
                    if "_metrics" in o:
                        metrics = parser.get(s,o).split(",")
                        # We need to convert the metric class names to the classes
                        metrics_class = [eval(klass) for klass in metrics]
                        config[s][o] = metrics_class
                    else:
                        config[s][o] = parser.get(s,o)
        else:
            RuntimeError("Config file needed to create the report")

        return config

    def __convert_none_to_zero(self, ts):
        # Matplotlib and import prettyplotlib as ppl don't handle None.
        # Convert None to 0 which is an ugly hack

        if not ts: return ts

        ts_clean = [val if val else 0 for val in ts ]

        return ts_clean

    def bar3_chart(self, title, labels, data1, file_name, data2, data3, legend=["", ""]):

        colors = ["orange", "grey"]

        data1 = self.__convert_none_to_zero(data1)
        data2 = self.__convert_none_to_zero(data2)
        data3 = self.__convert_none_to_zero(data3)

        fig, ax = plt.subplots(1)
        xpos = np.arange(len(data1))
        width = 0.28

        plt.title(title)
        y_pos = np.arange(len(data1))

        ppl.bar(xpos+width+width, data3, color="orange", width=0.28, annotate=True)
        ppl.bar(xpos+width, data1, color='grey', width=0.28, annotate=True)
        ppl.bar(xpos, data2, grid='y', width = 0.28, annotate=True)
        plt.xticks(xpos+width, labels)
        plt.legend(legend, loc=2)


        plt.savefig(file_name)
        plt.close()

    def bar_chart(self, title, labels, data1, file_name, data2 = None, legend=["", ""]):

        colors = ["orange", "grey"]

        data1 = self.__convert_none_to_zero(data1)
        data2 = self.__convert_none_to_zero(data2)

        fig, ax = plt.subplots(1)
        xpos = np.arange(len(data1))
        width = 0.35

        plt.title(title)
        y_pos = np.arange(len(data1))

        if data2 is not None:
            ppl.bar(xpos+width, data1, color="orange", width=0.35, annotate=True)
            ppl.bar(xpos, data2, grid='y', width = 0.35, annotate=True)
            plt.xticks(xpos+width, labels)
            plt.legend(legend, loc=2)

        else:
            ppl.bar(xpos, data1, grid='y', annotate=True)
            plt.xticks(xpos+width, labels)

        plt.savefig(file_name)
        plt.close()

    def get_metric_index(self, metric_cls):
        return self.ds2index[metric_cls.ds]

    def sec_overview(self):
        # Overview: Activity and git.Authors

        """
        Activity during the last 90 days and its evolution

        description: for the specified data source, we need the main activity
        metrics. This is the comparison of the last interval of
        analysis with the previous one. Net values
        are the total numbers, while the change is the percentage of such
        number if compared to the previous interval of analysis.
        commits, closed tickets, sent tickets, closed pull requests,
        open pull requests, sent emails
        """

        metrics = self.config['overview']['activity_metrics']
        file_name = self.config['overview']['activity_file_csv']

        file_name = os.path.join(self.data_dir, file_name)

        csv = 'metricsnames,netvalues,relativevalues,datasource\n'
        for metric in metrics:
            # comparing current metric month count with previous month
            es_index = self.get_metric_index(metric)
            ds = metric.ds.name
            m = metric(self.es_url, es_index, start=self.start, end=self.end)
            (last, percentage) = m.get_trend()
            csv += "%s,%i,%i,%s" % (metric.name, last, percentage, ds)
            csv += "\n"
        with open(file_name, "w") as f:
            f.write(csv)

        """
        Git Authors:

        description: average number of developers per month by quarters
        (so we have the average number of developers per month during
        those three months). If the approach is to work at the level of month,
        then just the number of developers per month.
        """

        author = self.config['overview']['author_metrics'][0]
        csv_labels = 'labels,'+author.id
        file_label = author.ds.name + "_" + author.id
        title_label = author.name + " per "+ self.interval
        self.__create_csv_eps(author, None, csv_labels, file_label, title_label)

        """
        Process
        github.Closed changesets out of opened changesets (REI), closed ticket out
        of opened tickets (BMI) and median time to merge in Gerrit (TTM)
        (Potential title: Project Efficiency)
        description: github.Closed PRs / Open PRs, github.Closed Issues / Open Issues,
        median time to close a PR, median time to close an Issue
        """

        bmi = []
        ttc = [] # time to close

        csv_labels = ''
        for m in self.config['overview']['bmi_metrics']:
            metric = m(self.es_url, self.get_metric_index(m),
                       start=self.end_prev_month, end=self.end)
            csv_labels += m.id +","
            bmi.append(metric.get_agg())

        for m in self.config['overview']['time_to_close_metrics']:
            metric = m(self.es_url, self.get_metric_index(m),
                       start=self.end_prev_month, end=self.end)
            csv_labels += m.id +","
            ttc.append(metric.get_agg())

        csv = csv_labels[:-1]+"\n"  # remove last comma
        csv = csv.replace("_","")
        for val in bmi:
            csv += "%s," % (self.str_val(val))
        for val in ttc:
            csv += "%s," % (self.str_val(val))
        if csv[-1] == ',': csv = csv [:-1]
        file_name = os.path.join(self.data_dir, 'efficiency.csv')
        with open(file_name, "w") as f:
            f.write(csv)

    def sec_com_channels(self):
        """
        Emails:
            description: number of emails sent per period of analysis
        Email Senders:
            description: number of people sending emails per period of analysis
        """

        for metric in self.config['com_channels']['activity_metrics'] + \
                      self.config['com_channels']['author_metrics']:
            csv_labels = 'labels,'+metric.id
            file_label = metric.ds.name + "_" + metric.id
            title_label = metric.name + " per "+ self.interval
            self.__create_csv_eps(metric, None, csv_labels, file_label, title_label)

    @classmethod
    def str_val(cls, val):
        """ Format the value of a metric value to a string """
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
        esfilters = None
        csv_labels = csv_labels.replace("_","")  # LaTeX not supports _
        if project and project != self.GLOBAL_PROJECT:
            esfilters={"project": project}
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
            date_str = parser.parse(m1_ts['date'][i]).strftime("%y-%m")
            csv += date_str
            csv += "," + self.str_val(m1_ts['value'][i])
            if metric2:
                csv += "," + self.str_val(m2_ts['value'][i])
            csv += "\n"

        if project:
            file_name = os.path.join(self.data_dir, file_label+"_"+project+".csv")
        else:
            file_name = os.path.join(self.data_dir, file_label+".csv")
        with open(file_name, "w") as f:
            f.write(csv)

        if project:
            file_name = os.path.join(self.data_dir, file_label+"_"+project+".eps")
            title = title_label+": "+ project
        else:
            file_name = os.path.join(self.data_dir, file_label+".eps")
            title = title_label
        x_val = [parser.parse(val).strftime("%y-%m") for val in m1_ts['date']]
        if metric2:
            self.bar_chart(title, x_val, m1_ts['value'],
                           file_name, m2_ts['value'],
                           legend=[m1.name, m2.name])
        else:
            self.bar_chart(title, x_val, m1_ts['value'], file_name,
                           legend=[m1.name])

    def sec_project_activity(self, project=None):
        """
        Activity
        """

        def create_data(metrics, project):
            csv_labels = "labels" + ',' + metrics[0].id + ","+metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels,
                                  file_label, title_label, project)

        logging.info("Activity data for: %s", project)

        """
        Commits and Pull Requests:
        description: number of commits and pull requests per project
        """

        metrics = self.config['project_activity']['ds1_metrics']
        create_data(metrics, project)


        """
        github.Opened and github.Closed Pull Requests:
        description: number of opened and closed pull requests per project
        """

        metrics = self.config['project_activity']['ds2_metrics']
        create_data(metrics, project)

        """
        github.Opened and github.Closed Issues:
        description: number of opened and closed issues per project
        """

        if 'ds3_metrics' in self.config['project_activity']:
            metrics = self.config['project_activity']['ds3_metrics']
            create_data(metrics, project)


    def sec_project_community(self, project=None):

        def create_csv(metric1, csv_labels, file_label):
            esfilters = None
            csv_labels = csv_labels.replace("_","")  # LaTeX not supports "_"
            if project != self.GLOBAL_PROJECT:
                esfilters={"project": project}

            m1 = metric1(self.es_url, self.get_metric_index(metric1),
                         esfilters=esfilters, start=self.end_prev_month, end=self.end)
            top = m1.get_list()
            csv = csv_labels + '\n'
            for i in range(0, len(top['value'])):
                if i > self.TOP_MAX:
                    break
                csv += top[metric1.FIELD_NAME][i] + "," + self.str_val(top['value'][i])
                csv += "\n"

            file_name = os.path.join(self.data_dir, file_label+"_"+project+".csv")

            with open(file_name, "w") as f:
                f.write(csv)


        logging.info("Community data for: %s", project)

        """
        Developers

        description: number of people that participate with a commit
        """
        author = self.config['project_community']['author_metrics'][0]
        csv_labels = 'labels,'+author.id
        file_label = author.ds.name + "_" + author.id
        title_label = author.name + " per "+ self.interval
        self.__create_csv_eps(author, None, csv_labels, file_label, title_label,
                              project)

        """
        Main developers

        """

        metric = self.config['project_community']['people_top_metrics'][0]
        # TODO: Commits must be extracted from metric
        csv_labels = author.id+",commits"
        file_label = author.ds.name+"_top_"+ author.id
        create_csv(metric, csv_labels, file_label)

        """
        Main organizations

        """
        orgs = self.config['project_community']['orgs_top_metrics'][0]
        # TODO: Commits must be extracted from metric
        csv_labels = orgs.id+",commits"
        file_label = orgs.ds.name+"_top_"+ orgs.id
        create_csv(orgs, csv_labels, file_label)

    def sec_project_process(self, project=None):

        logging.info("Process data for: %s", project)

        """
        BMI Pull Requests

        description: closed PRs out of open PRs in a period of time
        """
        metric = self.config['project_process']['bmi_metrics'][0]
        csv_labels = "labels"+","+metric.id
        file_label = metric.ds.name + "_" + metric.id
        title_label = metric.name
        self.__create_csv_eps(metric, None, csv_labels, file_label, title_label,
                              project)

        """
        BMI Issues

        description: closed issues out of open issues in a period of time
        """
        if len(self.config['project_process']['bmi_metrics']) > 1:
            metric = self.config['project_process']['bmi_metrics'][1]
            csv_labels = "labels"+","+metric.id
            file_label = metric.ds.name + "_" + metric.id
            title_label = metric.name
            self.__create_csv_eps(metric, None, csv_labels, file_label, title_label,
                                  project)

        """
        Time to close Issues

        description: median and mean time to close issues
        """

        if 'time_to_close_metrics' in self.config['project_process']:
            metrics = self.config['project_process']['time_to_close_metrics']
            csv_labels = "labels" + ',' + metrics[0].id + ","+metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            # title_label = metrics[0].name + ", " + metrics[1].name + " per "+ self.interval
            title_label = self.config['project_process']['time_to_close_title']
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels, file_label,
                                  title_label, project)

        """
        Time to close PRs

        description: median and mean time to close prs
        """

        metrics = self.config['project_process']['time_to_close_review_metrics']
        csv_labels = "labels" + ',' + metrics[0].id + ","+metrics[1].id
        file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
        file_label += metrics[1].ds.name + "_" + metrics[1].id
        # title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
        title_label = self.config['project_process']['time_to_close_review_title']
        self.__create_csv_eps(metrics[0], metrics[1], csv_labels, file_label,
                              title_label, project)

        """
        Patchsets per review

        description: median and average of the number of patchsets per review
        """
        if 'patchsets_metrics' in self.config['project_process']:
            metrics = self.config['project_process']['patchsets_metrics']
            csv_labels = "labels" + ',' + metrics[0].id + ","+metrics[1].id
            file_label = metrics[0].ds.name + "_" + metrics[0].id + "_"
            file_label += metrics[1].ds.name + "_" + metrics[1].id
            # title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
            title_label = self.config['project_process']['patchsets_title']
            self.__create_csv_eps(metrics[0], metrics[1], csv_labels, file_label,
                                  title_label, project)

    def sec_projects(self):
        """
        This activity is displayed at the general level, aggregating all
        of the projects, with the name 'general' and per project using
        the name of each project. This activity is divided into three main
        layers: activity, community and process.
        """

        # First the 'general' project
        self.sec_project_activity(self.GLOBAL_PROJECT)
        self.sec_project_community(self.GLOBAL_PROJECT)
        self.sec_project_process(self.GLOBAL_PROJECT)

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
            self.sec_project_activity(project)
            self.sec_project_community(project)
            self.sec_project_process(project)

    def sections(self):
        secs = OrderedDict()
        secs['Overview'] = self.sec_overview
        secs['Communication Channels'] = self.sec_com_channels
        secs['Detailed Activity by Project'] = self.sec_projects

        return secs

    def create(self):
        logging.info("Generating the report data from %s to %s",
                     self.start, self.end)

        for section in self.sections():
            logging.info("Generating %s", section)
            self.sections()[section]()

        logging.info("Done")

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
