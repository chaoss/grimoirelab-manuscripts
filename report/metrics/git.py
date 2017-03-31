#!/usr/bin/python3
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
##   Daniel Izquierdo-Cortazar <dizquierdo@bitergia.com>
##   Alvaro del Castillo  <acs@bitergia.com>
##

from .metrics import Metrics

class Git():
    name = "git"

    @classmethod
    def get_section_metrics(cls):
        return {
            "overview" : {
                "activity_metrics": [Commits],
                "author_metrics": [Authors],
                "bmi_metrics": [],
                "time_to_close_metrics": [],
                "projects_metrics": [Projects]
            },
            "com_channels": {
                "activity_metrics": [],
                "author_metrics": []
            },
            "project_activity": {
                # TODO: Authors is not activity but we need two metrics here
                "metrics": [Commits, Authors]
            },
            "project_community": {
                "author_metrics": [Authors],
                "people_top_metrics": [Authors],
                "orgs_top_metrics": [Organizations],
            },
            "project_process": {
                "bmi_metrics": [],
                "time_to_close_metrics": [],
                "time_to_close_title": "",
                "time_to_close_review_metrics": [],
                "time_to_close_review_title": "",
                "patchsets_metrics": []
            }
        }


class GitMetrics(Metrics):
    ds = Git


class Commits(GitMetrics):
    """ Commits metric class for source code management systems """

    id = "commits"
    name = "Commits"
    desc = "Changes to the source code"
    FIELD_COUNT = 'hash' # field used to count commits
    FIELD_NAME = 'hash' # field used to list commits


class Authors(GitMetrics):
    """ Authors metric class for source code management systems """

    id = "authors"
    name = "Authors"
    desc = "People authoring commits (changes to source code)"
    FIELD_COUNT = 'author_uuid' # field used to count Authors
    FIELD_NAME = 'author_name' # field used to list Authors


class Organizations(GitMetrics):
    """ Projects in the source code management system """

    id = "organizations"
    name = "Organizations"
    desc = "Organizations in the source code management system"
    FIELD_NAME = 'author_org_name' # field used to list projects

class Committers(GitMetrics):
    """ Committers metric class for source code management systems """

    id = "committers"
    name = "Committers"
    desc = "Number of developers committing (merging changes to source code)"
    FIELD_COUNT = 'Commit_uuid'
    FIELD_NAME = 'Commit_name'


class Projects(GitMetrics):
    """ Projects in the source code management system """

    id = "projects"
    name = "Projects"
    desc = "Projects in the source code management system"
    FIELD_NAME = 'project' # field used to list projects
