## Copyright (C) 2017 Bitergia
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
##

from .metrics import Metrics

class Stackexchange():
    name = "stackexchange"

    @classmethod
    def get_section_metrics(cls):
        return {
            "overview" : {
                "activity_metrics": [QuestionsSent],
                "author_metrics": [],
                "bmi_metrics": [],
                "time_to_close_metrics": [],
                "projects_metrics": [Projects]
            },
            "com_channels": {
                "activity_metrics": [QuestionsSent],
                "author_metrics": [QuestionsSenders]
            },
            "project_activity": {
                # TODO: QuestionsSenders is not activity but we need two metrics here
                "metrics": [QuestionsSent, QuestionsSenders]
            },
            "project_community": {
                "author_metrics": [],
                "people_top_metrics": [],
                "orgs_top_metrics": [],
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


class StackexchangeMetrics(Metrics):
    ds = Stackexchange


class QuestionsSent(StackexchangeMetrics):
    """ Questions metric class for stackexchange analysis """

    id = "questions_sent"
    name = "Sent Questions"
    desc = "Questions sent to stackexchange site"
    FIELD_COUNT = "uuid"  # field used to count questions
    FIELD_NAME = "title"  # field used to list qyestions
    filters = {"is_stackexchange_question":"1"}


class QuestionsSenders(StackexchangeMetrics):
    """ Questions Senders class for stackexchange analysis """

    id = "questions_senders"
    name = "Questions Senders"
    desc = "People sending questions"

    FIELD_COUNT = 'author_uuid' # field used to count Authors
    FIELD_NAME = 'author_name' # field used to count Authors
    filters = {"is_stackexchange_question":"1"}


class Projects(StackexchangeMetrics):
    """ Projects in the stackexchange """

    id = "projects"
    name = "Projects"
    desc = "Projects in stackexchange"
    FIELD_NAME = 'project' # field used to list projects
