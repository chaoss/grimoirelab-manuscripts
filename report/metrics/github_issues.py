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

from . import its

class GitHubIssues(its.ITS):
    name = "github_issues"

    @classmethod
    def get_section_metrics(cls):
        return {
            "overview" : {
                "activity_metrics": [Closed, Opened],
                "author_metrics": [],
                "bmi_metrics": [BMI],
                "time_to_close_metrics": [DaysToCloseMedian],
                "projects_metrics": [Projects]
            },
            "com_channels": {
                "activity_metrics": [],
                "author_metrics": []
            },
            "project_activity": {
                "metrics": [Opened, Closed]
            },
            "project_community": {
                "author_metrics": [],
                "people_top_metrics": [],
                "orgs_top_metrics": [],
            },
            "project_process": {
                "bmi_metrics": [BMI],
                "time_to_close_metrics": [DaysToCloseAverage, DaysToCloseMedian],
                "time_to_close_title": "Days to close (median and average)",
                "time_to_close_review_metrics": [],
                "time_to_close_review_title": "",
                "patchsets_metrics": []
            }
        }


class GitHubIssuesMetrics(its.ITS):
    # TODO: All GitHubIssuesMetrics metrics should inherit from this class
    # but they are doing it from ITSMetrics directly. Change the design.
    ds = GitHubIssues

class Opened(its.Opened):
    ds = GitHubIssues
    filters = {"pull_request":"false"}

class Openers(its.Openers):
    ds = GitHubIssues
    filters = {"pull_request":"false"}

class Closed(its.Closed):
    ds = GitHubIssues
    filters = {"state":"closed", "pull_request":"false"}

class DaysToCloseMedian(its.DaysToCloseMedian):
    ds = GitHubIssues
    filters = {"state":"closed", "pull_request":"false"}

class DaysToCloseAverage(its.DaysToCloseAverage):
    ds = GitHubIssues
    filters = {"state":"closed", "pull_request":"false"}

class Closers(its.Closers):
    ds = GitHubIssues
    filters = {"state":"closed", "pull_request":"false"}

class BMI(its.BMI):
    ds = GitHubIssues
    filters = {"pull_request":"false"}

class Projects(its.Projects):
    ds = GitHubIssues
    filters = {"pull_request":"false"}
