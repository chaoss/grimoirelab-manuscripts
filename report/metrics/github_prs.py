## Copyright (C) 2014 Bitergia
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## This file is a part of GrimoireLib
##  (an Python library for the MetricsGrimoire and vizGrimoire systems)
##
##
## Authors:
##   Alvaro del Castillo <acs@bitergia.com>
##   Daniel Izquierdo <dizquierdo@bitergia.com>

from .metrics import Metrics

class GitHubPRs():
    name = "github_prs"

    @classmethod
    def get_section_metrics(cls):
        # Those metrics are only for Pull Requests
        # github issues is covered as ITS
        return {
            "overview" : {
                "activity_metrics": [ClosedPR, SubmittedPR],
                "author_metrics": [],
                "bmi_metrics": [BMIPR],
                "time_to_close_metrics": [DaysToClosePRMedian],
                "projects_metrics": [Projects]
            },
            "com_channels": {
                "activity_metrics": [],
                "author_metrics": []
            },
            "project_activity": {
                "metrics": [SubmittedPR, ClosedPR]
            },
            "project_community": {
                "author_metrics": [],
                "people_top_metrics": [],
                "orgs_top_metrics": [],
            },
            "project_process": {
                "bmi_metrics": [BMIPR],
                "time_to_close_metrics": [],
                "time_to_close_title": "Days to close (median and average)",
                "time_to_close_review_metrics": [DaysToClosePRAverage, DaysToClosePRMedian],
                "time_to_close_review_title": "Days to close review (median and average)",
                "patchsets_metrics": []
            }
        }



class GitHubPRsMetrics(Metrics):
    ds = GitHubPRs


class SubmittedPR(GitHubPRsMetrics):
    id = "submitted"
    name = "Submitted reviews"
    desc = "Number of submitted code review processes"
    FIELD_NAME = 'id'
    FIELD_COUNT = 'id'
    filters = {"pull_request":"true"}


class ClosedPR(GitHubPRsMetrics):
    id = "closed"
    name = "Closed reviews"
    desc = "Number of closed review processes (merged or abandoned)"
    FIELD_NAME = 'id'
    FIELD_COUNT = 'id'
    filters = {"pull_request":"true", "state":"closed"}


class DaysToClosePRMedian(GitHubPRsMetrics):
    id = "days_to_close_pr_median"
    name = "Days to close reviews (median)"
    desc = "Number of days needed to close a review (median)"
    FIELD_COUNT = 'time_to_close_days'
    AGG_TYPE = 'median'
    filters = {"pull_request":"true", "state":"closed"}

    def get_agg(self):
        agg = super(type(self), self).get_agg()
        if agg == None:
            agg = 0  # None is because NaN in ES. Let's convert to 0
        return agg

class DaysToClosePRAverage(GitHubPRsMetrics):
    id = "days_to_close_pr_avg"
    name = "Days to close reviews (avg)"
    desc = "Number of days needed to close a review (average)"
    FIELD_COUNT = 'time_to_close_days'
    AGG_TYPE = 'average'
    filters = {"pull_request":"true", "state":"closed"}


class Projects(GitHubPRsMetrics):
    """ Projects in the review code management system """

    id = "projects"
    name = "Projects"
    desc = "Projects in the review code management system"
    FIELD_NAME = 'project' # field used to list projects


class BMIPR(GitHubPRsMetrics):
    """This class calculates the efficiency closing reviews

    It is calculated as the number of closed issues out of the total number
    of opened ones in a period.
    """

    id = "bmipr"
    name = "BMI Pull Requests"
    desc = "Efficiency reviewing: (closed prs)/(submitted prs)"

    def __get_metrics(self):
        """ Each metric must have its own filters copy to modify it freely"""
        esfilters_close = None
        esfilters_submit = None
        if self.esfilters:
            esfilters_close = self.esfilters.copy()
            esfilters_submit = self.esfilters.copy()

        closed = ClosedPR(self.es_url, self.es_index,
                          start=self.start, end=self.end,
                          esfilters=esfilters_close, interval=self.interval)
        # For BMI we need when the ticket was closed
        closed.DATE_FIELD = 'updated_at'
        submitted = SubmittedPR(self.es_url, self.es_index,
                                start=self.start, end=self.end,
                                esfilters=esfilters_submit,
                                interval=self.interval)

        return (closed, submitted)

    def get_agg(self):
        (closed, submitted) = self.__get_metrics()
        closed_agg = closed.get_agg()
        submitted_agg = submitted.get_agg()

        if submitted_agg == 0:
            bmi = 1  # if no submitted prs, bmi is at 100%
        else:
            bmi = closed_agg/submitted_agg

        return bmi


    def get_ts(self):
        bmi = {}
        (closed, submitted) = self.__get_metrics()
        closed_ts = closed.get_ts()
        submitted_ts = submitted.get_ts()

        bmi['date'] = closed_ts['date']
        bmi['unixtime'] = closed_ts['unixtime']
        bmi['value'] = []
        for i in range(0, len(submitted_ts['value'])):
            if submitted_ts['value'][i] == 0:
                bmi['value'].append(0)
            else:
                bmi['value'].append(closed_ts['value'][i] / submitted_ts['value'][i])

        return bmi


class Reviewers(GitHubPRsMetrics):
    """ People assigned to pull requests """
    id = "reviewers"
    name = "Reviewers"
    desc = "Number of persons reviewing code review activities"


class Closers(GitHubPRsMetrics):
    id = "closers"
    name = "Closers"
    desc = "Number of persons closing code review activities"


# Pretty similar to ITS openers
class Submitters(GitHubPRsMetrics):
    id = "submitters"
    name = "Submitters"
    desc = "Number of persons submitting code review processes"
