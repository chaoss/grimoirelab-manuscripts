#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Script for producing Reports from data in ElasticSearch
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
# Author:
#   Pranjal Aswani <aswani.pranjal@gmail.com>

import os
import json


def load_json_file(filename, mode="r"):
    """
    Load a json file and return the data.

    :param filename: the name of the json file to be loaded
    :param mode: the mode to open the file in. Default: 'r'
    :returns: content of the json file as a python dict
    """

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        json_content = json.load(f)
    return json_content
