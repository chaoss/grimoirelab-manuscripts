# Copyright (C) 2014 Bitergia
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
# This file is a part of GrimoireLib
#  (an Python library for the MetricsGrimoire and vizGrimoire systems)
#
#
# Authors:
#   Daniel Izquierdo-Cortazar <dizquierdo@bitergia.com>
#   Alvaro del Castillo <acs@bitergia.com>
#

from .metrics import Metrics


class MLS():
    name = "mailing lists"

    @classmethod
    def get_section_metrics(cls):
        return {
            "overview": {
                "activity_metrics": [EmailsSent],
                "author_metrics": [],
                "bmi_metrics": [],
                "time_to_close_metrics": [],
                "projects_metrics": [Projects]
            },
            "com_channels": {
                "activity_metrics": [EmailsSent],
                "author_metrics": [EmailsSenders]
            },
            "project_activity": {
                # TODO: EmailsSenders is not activity but we need two metrics here
                "metrics": [EmailsSent, EmailsSenders]
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


class MLSMetrics(Metrics):
    ds = MLS


class EmailsSent(MLSMetrics):
    """ Emails metric class for mailing lists analysis """

    id = "emails_sent"
    name = "Sent Emails"
    desc = "Emails sent to mailing lists"
    FIELD_COUNT = "Message-ID"
    FIELD_NAME = "Message-ID"


class EmailsSenders(MLSMetrics):
    """ Emails Senders class for mailing list analysis """

    id = "emails_senders"
    name = "Email Senders"
    desc = "People sending emails"

    FIELD_COUNT = 'author_uuid'  # field used to count Authors
    FIELD_NAME = 'author_name'  # field used to count Authors


class Projects(MLSMetrics):
    """ Projects in the mailing lists """

    id = "projects"
    name = "Projects"
    desc = "Projects in the mailing lists"
    FIELD_NAME = 'project'  # field used to list projects
