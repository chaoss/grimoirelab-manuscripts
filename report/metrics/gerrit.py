## Copyright (C) 2016 Bitergia
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
##
## Authors:
##   Alvaro del Castillo <acs@bitergia.com>
##   Daniel Izquierdo <dizquierdo@bitergia.com>

""" Metrics for Gerrit review system """

import logging

from .metrics import Metrics

class Gerrit():
    name = "gerrit"

    @classmethod
    def get_section_metrics(cls):
        return {
            "overview" : {
                "activity_metrics": [Closed, Submitted],
                "author_metrics": None,
                "bmi_metrics": [BMI],
                "time_to_close_metrics": [DaysToMergeMedian],
                "projects_metrics": [Projects],
            },
            "com_channels": {
                "activity_metrics": [],
                "author_metrics": []
            },
            "project_activity": {
                "metrics": [Submitted, Closed]
            },
            "project_community": {
                "author_metrics": [],
                "people_top_metrics": [],
                "orgs_top_metrics": [],
            },
            "project_process": {
                "bmi_metrics": [BMI],
                "time_to_close_metrics": [],
                "time_to_close_title": "",
                "time_to_close_review_metrics": [DaysToMergeAverage, DaysToMergeMedian],
                "time_to_close_review_title": "Days to close review (median and average)",
                "patchsets_metrics": [PatchsetsMedian, PatchsetsAverage],
                "patchsets_title": "Number of patchsets per review (median and average)"
            }
        }


class GerritMetrics(Metrics):
    ds = Gerrit


class Submitted(GerritMetrics):
    id = "submitted"
    name = "Submitted reviews"
    desc = "Number of submitted code review processes"
    FIELD_NAME = 'url'
    FIELD_COUNT = 'url'


class Merged(GerritMetrics):
    id = "merged"
    name = "Merged reviews"
    desc = "Number of merged review processes"
    FIELD_NAME = 'url'
    FIELD_COUNT = 'url'
    filters = {"status": "MERGED"}

class Abandoned(GerritMetrics):
    id = "abandoned"
    name = "Abandoned reviews"
    desc = "Number of abandoned review processes"
    FIELD_NAME = 'url'
    FIELD_COUNT = 'url'
    filters = {"status": "ABANDONED"}

class Closed(GerritMetrics):
    id = "closed"
    name = "Closed reviews"
    desc = "Number of closed review processes (merged or abandoned)"

    def __get_metrics(self):
        """ Each metric must have its own filters copy to modify it freely"""
        esfilters_merge = None
        esfilters_abandon = None
        if self.esfilters:
            esfilters_merge = self.esfilters.copy()
            esfilters_abandon = self.esfilters.copy()

        merged = Merged(self.es_url, self.es_index,
                              start=self.start, end=self.end,
                              esfilters=esfilters_merge, interval=self.interval)

        abandoned = Abandoned(self.es_url, self.es_index,
                                    start=self.start, end=self.end,
                                    esfilters=esfilters_abandon, interval=self.interval)
        return (merged, abandoned)

    def get_agg(self):
        (merged, abandoned) = self.__get_metrics()
        merged_agg = merged.get_agg()
        abandoned_agg = abandoned.get_agg()
        agg = merged_agg + abandoned_agg
        return agg

    def get_ts(self):
        closed = {}
        (merged, abandoned) = self.__get_metrics()
        merged_ts = merged.get_ts()
        abandoned_ts = abandoned.get_ts()

        closed['date'] = merged_ts['date']
        closed['unixtime'] = merged_ts['unixtime']
        closed['value'] = []
        for i in range(0, len(merged_ts['value'])):
            closed['value'].append(merged_ts['value'][i] + abandoned_ts['value'][i])
        return closed


class BMI(GerritMetrics):
    """This class calculates the efficiency closing reviews

    This class is based on the Backlog Management Index that in issues, it is
    calculated as the number of merged issues out of the total number of opened
    ones in a period. (The other way around also provides an interesting view).

    In terms of the code review system, this values is measured as the number
    of merged+abandoned reviews out of the total number of submitted ones.
    """

    id = "bmi_reviews"
    name = "BMI Gerrit"
    desc = "Efficiency reviewing: (merged+abandoned reviews)/(submitted reviews)"

    def __get_metrics(self):
        """ Each metric must have its own filters copy to modify it freely"""
        esfilters_merge = None
        esfilters_abandon = None
        esfilters_submit = None
        if self.esfilters:
            esfilters_merge = self.esfilters.copy()
            esfilters_abandon = self.esfilters.copy()
            esfilters_submit = self.esfilters.copy()

        merged = Merged(self.es_url, self.es_index,
                              start=self.start, end=self.end,
                              esfilters=esfilters_merge, interval=self.interval)
        # For BMI we need when the ticket was closed
        merged.DATE_FIELD = 'closed'

        abandoned = Abandoned(self.es_url, self.es_index,
                                    start=self.start, end=self.end,
                                    esfilters=esfilters_abandon, interval=self.interval)
        # For BMI we need when the ticket was closed
        abandoned.DATE_FIELD = 'closed'

        submitted = Submitted(self.es_url, self.es_index,
                                    start=self.start, end=self.end,
                                    esfilters=esfilters_submit,
                                    interval=self.interval)

        return (merged, abandoned, submitted)

    def get_agg(self):
        (merged, abandoned, submitted) = self.__get_metrics()
        merged_agg = merged.get_agg()
        abandoned_agg = abandoned.get_agg()
        closed_agg = merged_agg + abandoned_agg
        submitted_agg = submitted.get_agg()

        if submitted_agg == 0:
            bmi = 1  # if no submitted reviews, bmi is at 100%
        else:
            bmi = closed_agg/submitted_agg

        return bmi


    def get_ts(self):
        bmi = {}
        (merged, abandoned, submitted) = self.__get_metrics()
        merged_ts = merged.get_ts()
        abandoned_ts = abandoned.get_ts()
        submitted_ts = submitted.get_ts()

        bmi['date'] = merged_ts['date']
        bmi['unixtime'] = merged_ts['unixtime']
        bmi['value'] = []
        for i in range(0, len(submitted_ts['value'])):
            if submitted_ts['value'][i] == 0:
                bmi['value'].append(0)
            else:
                closed = merged_ts['value'][i] + abandoned_ts['value'][i]
                bmi['value'].append(closed / submitted_ts['value'][i])
        return bmi


class Organizations(GerritMetrics):
    id = "organizations"
    name = "Organizations"
    desc = "Number of organizations (organizations, etc.) with persons active in code review"
    FIELD_NAME = 'author_org_name'


class Projects(GerritMetrics):
    id = "projects"
    name = "Projects"
    desc = "Number of projects in code review"
    FIELD_NAME = 'project' # field used to list projects


class Submitters(GerritMetrics):
    id = "submitters"
    name = "Submitters"
    desc = "Number of persons submitting code review processes"
    FIELD_COUNT = 'author_uuid' # field used to count Authors
    FIELD_NAME = 'author_name' # field used to list Authors


class DaysToMergeMedian(GerritMetrics):
    id = "days_to_merge_review_median"
    name = "Days to merge reviews (median)"
    desc = "Number of days needed to merge a review (median)"
    FIELD_COUNT = 'timeopen'
    AGG_TYPE = 'median'
    filters = {"status": "MERGED"}

    def get_agg(self):
        agg = super(type(self), self).get_agg()
        if agg == None:
            agg = 0  # None is because NaN in ES. Let's convert to 0
        return agg

class DaysToMergeAverage(GerritMetrics):
    id = "days_to_merge_review_avg"
    name = "Days to merge reviews (average)"
    desc = "Number of days needed to merge a review (average)"
    FIELD_COUNT = 'timeopen'
    AGG_TYPE = 'average'
    filters = {"status": "MERGED"}

class PatchsetsMedian(GerritMetrics):
    id = "review_patchsets_median"
    name = "Patchsets per review (median)"
    desc = "Number of patchsets per review (median)"
    FIELD_COUNT = 'patchsets'
    AGG_TYPE = 'median'

    def get_agg(self):
        agg = super(type(self), self).get_agg()
        if agg == None:
            agg = 0  # None is because NaN in ES. Let's convert to 0
        return agg

class PatchsetsAverage(GerritMetrics):
    id = "review_patchsets_avg"
    name = "Patchsets per review (average)"
    desc = "Number of patchsets per review (average)"
    FIELD_COUNT = 'patchsets'
    AGG_TYPE = 'average'
