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

import matplotlib as mpl
# This avoids the use of the $DISPLAY value for the charts
mpl.use('Agg')
import matplotlib.pyplot as plt
import prettyplotlib as ppl
import numpy as np

from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from distutils.dir_util import copy_tree

from dateutil import parser, relativedelta

from .metrics import git
from .metrics import its
from .metrics import jira
from .metrics import github_issues
from .metrics import github_prs
from .metrics import mls
from .metrics import gerrit
from .metrics import stackexchange

from .metrics.metrics import Metrics

logger = logging.getLogger(__name__)

class Report():
    GIT_INDEX = 'git_enrich'
    GITHUB_ISSUES_INDEX = 'github_issues'
    GITHUB_PRS_INDEX = 'github_issues'
    JIRA_INDEX = 'jira'
    EMAIL_INDEX = 'mbox_enrich'
    GERRIT_INDEX = 'gerrit'
    STACHEXCHANGE_INDEX = 'stackoverflow'
    GLOBAL_PROJECT = 'general'
    TOP_MAX = 20

    ds2index = {
        gerrit.Gerrit: GERRIT_INDEX,
        git.Git: GIT_INDEX,
        github_issues.GitHubIssues: GITHUB_ISSUES_INDEX,
        github_prs.GitHubPRs: GITHUB_PRS_INDEX,
        jira.Jira: JIRA_INDEX,
        mls.MLS: EMAIL_INDEX,
        stackexchange.Stackexchange: STACHEXCHANGE_INDEX
    }

    ds2class = {
        "gerrit": gerrit.Gerrit,
        "git": git.Git,
        "github_issues": github_issues.GitHubIssues,
        "github_prs": github_prs.GitHubPRs,
        "jira": jira.Jira,
        "mailinglist": mls.MLS,
        "stackexchange": stackexchange.Stackexchange
    }

    supported_data_sources = ['git', 'github', 'gerrit', 'mls']
    supported_data_sources += ['github_issues', 'github_prs']
    supported_data_sources += ['jira']
    supported_data_sources += ['stackexchange']

    def __init__(self, es_url, start, end, data_dir=None, filters=None,
                 interval="month", offset=None, data_sources=None,
                 report_name=None, projects=False):
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
        # Just include the supported data sources
        self.data_sources = list(set(data_sources) & set(self.supported_data_sources))
        # Temporal hack
        for mls_ds in ['mbox', 'pipermail']:
            if mls_ds in data_sources:
                self.data_sources.append('mailinglist')
        if 'github' in data_sources:
            # In mordred github issues and prs are managed together
            self.data_sources.remove('github')
            self.data_sources += ['github_issues', 'github_prs']
        self.data_sources = list(set(self.data_sources))
        # End temporal hack
        self.config = self.__get_config(self.data_sources)
        self.report_name = report_name
        self.projects = projects

    def __get_config(self, data_sources=None):
        """
            The config is get from each data source and then it is combined.

            It defines the metrics to be included in each section of the report
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
                            if metric_section not in new_config[section] or \
                                new_config[section][metric_section] is None:
                                new_config[section][metric_section] = ds_config[section][metric_section]
                            else:
                                new_config[section][metric_section] += ds_config[section][metric_section]

        # fields that are not linked to a data source
        new_config['overview']['activity_file_csv'] = "data_source_evolution.csv"
        new_config['overview']['efficiency_file_csv'] = "efficiency.csv"
        new_config['project_process']['time_to_close_title'] = "Days to close (median and average)"
        new_config['project_process']['time_to_close_review_title'] = "Days to close review (median and average)"

        for i in range(0, len(data_sources)):
            ds = data_sources[i]
            ds_config = self.ds2class[ds].get_section_metrics()
            activity_metrics = ds_config['project_activity']['metrics']
            new_config['project_activity']['ds' + str(i+1)+"_metrics"] = activity_metrics

        # from pprint import pprint
        # pprint(new_config)
        # raise
        return new_config

    def __convert_none_to_zero(self, ts):
        # Matplotlib and import prettyplotlib as ppl don't handle None.
        # Convert None to 0 which is an ugly hack

        if not ts:
            return ts

        ts_clean = [val if val else 0 for val in ts]

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
        """ Data sources overview: table with metric summaries"""

        metrics = self.config['overview']['activity_metrics']
        file_name = self.config['overview']['activity_file_csv']

        file_name = os.path.join(self.data_dir, file_name)

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
        csv_labels = 'labels,'+author.id
        file_label = author.ds.name + "_" + author.id
        title_label = author.name + " per "+ self.interval
        self.__create_csv_eps(author, None, csv_labels, file_label, title_label)

        logger.debug("CSV file %s generation in progress", file_name)

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

        logger.debug("CSV file: %s was generated", file_name)

    def sec_com_channels(self):

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

        logger.debug("CSV file %s generation in progress", file_label)

        esfilters = None
        csv_labels = csv_labels.replace("_","")  # LaTeX not supports

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

        logger.debug("CSV file %s was generated", file_label)

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

        logger.info("Activity data for: %s", project)

        for activity_ds in self.config['project_activity']:
            if activity_ds == 'metrics':
                continue  # all metrics included
            metrics = self.config['project_activity'][activity_ds]
            create_data(metrics, project)


    def sec_project_community(self, project=None):

        def create_csv(metric1, csv_labels, file_label):
            esfilters = None
            csv_labels = csv_labels.replace("_","")  # LaTeX not supports "_"
            if project != self.GLOBAL_PROJECT:
                esfilters={"project": project}

            file_name = os.path.join(self.data_dir, file_label+"_"+project+".csv")

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

        logger.info("Process data for: %s", project)

        """
        BMI Pull Requests, BMI Issues

        description: closed PRs/issues out of open PRs/issues in a period of time
        """
        for i in range(0, len(self.config['project_process']['bmi_metrics'])):
            metric = self.config['project_process']['bmi_metrics'][i]
            csv_labels = "labels"+","+metric.id
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
            csv_labels = "labels" + ',' + metrics[0].id + ","+metrics[1].id
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
                csv_labels = "labels" + ',' + metrics[i].id + ","+metrics[i+1].id
                file_label = metrics[i].ds.name + "_" + metrics[i].id + "_"
                file_label += metrics[i+1].ds.name + "_" + metrics[i+1].id
                # title_label = metrics[0].name+", "+ metrics[1].name + " per "+ self.interval
                title_label = self.config['project_process']['time_to_close_review_title']
                self.__create_csv_eps(metrics[i], metrics[i+1], csv_labels, file_label,
                                      title_label, project)
                i = i + 2

        """
        Patchsets per review

        description: median and average of the number of patchsets per review
        """
        if self.config['project_process']['patchsets_metrics']:
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
        secs = OrderedDict()
        secs['Overview'] = self.sec_overview
        secs['Communication Channels'] = self.sec_com_channels
        secs['Detailed Activity by Project'] = self.sec_projects

        return secs

    def create_data_figs(self):
        """ Generate the data and figs files for the report """
        logger.info("Generating the report data and figs from %s to %s",
                     self.start, self.end)

        for section in self.sections():
            logger.info("Generating %s", section)
            self.sections()[section]()

        logger.info("Data and figs done")

    @classmethod
    def period_name(cls, pdate, interval='quarter', offset=None):
        # Just supporting quarters right now
        name = pdate.strftime('%Y-%m-%d') + ' ' + interval

        if interval == 'quarter':
            if offset:
                # +31d offset format
                offset_days = int(offset[1:-1])
                pdate = pdate - timedelta(days=offset_days)
            name = pdate.strftime('%Y')
            # The month is the next month 2017-04-01 to the current quarter
            month = int(pdate.strftime('%m')) - 1
            quarter = int(round(int(month)/3, 0))
            name += "-Q" + str(quarter)

        return name

    def create_pdf(self):
        logger.info("Generating PDF report")

        # First step is to create the report dir from the template
        report_path = self.data_dir
        templates_path = os.path.join(os.path.dirname(__file__),
                                        "latex_template")
        copy_tree(templates_path, report_path)
        # Copy the data generated to be used in LaTeX template
        copy_tree(self.data_dir, os.path.join(report_path, "data"))
        copy_tree(self.data_dir, os.path.join(report_path, "figs"))
        # Change the project global name
        project_replace = self.report_name.replace(' ', r'\ ')
        cmd = ['grep -rl PROJECT-NAME . | xargs sed -i s/PROJECT-NAME/' + project_replace + '/g']
        subprocess.call(cmd, shell=True, cwd=report_path)
        # Change the quarter subtitle
        period_name = self.period_name(self.end, self.interval, self.offset)
        period_replace = period_name.replace(' ', r'\ ')
        cmd = ['grep -rl 2016-QUARTER . | xargs sed -i s/2016-QUARTER/' + period_replace +  '/g']
        # cmd = ['sed -i s/2016-QUARTER/' + self.end.strftime('%Y-%m-%d') + \
        #       r'\ ' + self.interval + '/g *.tex']
        subprocess.call(cmd, shell=True, cwd=report_path)
        # Report date frame
        quarter_start = self.end - relativedelta.relativedelta(months=3)
        quarter_start += relativedelta.relativedelta(days=1)
        dateframe = (quarter_start.strftime('%Y-%m-%d')+" to "+self.end.strftime('%Y-%m-%d')).replace(' ', r'\ ')
        cmd = ['grep -rl DATEFRAME . | xargs sed -i s/DATEFRAME/' + dateframe +  '/g']
        subprocess.call(cmd, shell=True, cwd=report_path)
        # Change the date Copyright
        cmd = [r'sed -i s/\(cc\)\ 2016/\(cc\)\ ' + datetime.now().strftime('%Y') + '/g *.tex']
        subprocess.call(cmd, shell=True, cwd=report_path)
        # Fix LaTeX special chars
        cmd = [r'sed -i "s/\&/\\\&/g" data/git_top_organizations_*']
        res = subprocess.call(cmd, shell=True, cwd=report_path)
        cmd = [r'sed -i "s/^#//g" data/git_top_organizations_*']
        subprocess.call(cmd, shell=True, cwd=report_path)


        # Activity section
        activity = ''
        for activity_ds in ['git', 'github', 'gerrit', 'mls']:
            if activity_ds in self.data_sources:
                activity += r"\input{activity/" +  activity_ds + ".tex}"

        with open(os.path.join(report_path, "activity.tex"), "w") as flatex:
            flatex.write(activity)

        # Community section
        community = ''
        for community_ds in ['git', 'mls']:
            if community_ds in self.data_sources:
                community += r"\input{community/" +  community_ds + ".tex}"

        with open(os.path.join(report_path, "community.tex"), "w") as flatex:
            flatex.write(community)

        # Overview section
        overview = r'\input{overview/summary.tex}'
        for overview_ds in ['github', 'gerrit']:
            if overview_ds in self.data_sources:
                overview += r"\input{overview/efficiency-" +  overview_ds + ".tex}"

        with open(os.path.join(report_path, "overview.tex"), "w") as flatex:
            flatex.write(overview)

        # Process section
        process = ''
        for process_ds in ['github_prs', 'gerrit']:
            if process_ds in self.data_sources:
                process += r"\input{process/" +  process_ds + ".tex}"

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
