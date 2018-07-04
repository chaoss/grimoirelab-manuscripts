#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Derived classes to calculate Metrics from specific data sources
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
# Authors:
#   Pranjal Aswani <aswani.pranjal@gmail.com>

from .new_functions import Query


class PullRequests(Query):
    def __init__(self, index_obj, esfilters={}, interval=None, offset=None):
        super().__init__(index_obj, esfilters, interval, offset)
        super().add_query({"pull_request": "true"})


class Issues(Query):

    def __init__(self, index_obj, esfilters={}, interval=None, offset=None):
        super().__init__(index_obj, esfilters, interval, offset)
        super().add_query({"pull_request": "false"})
