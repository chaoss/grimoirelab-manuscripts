#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 Bitergia
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
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Alvaro del Castillo <acs@bitergia.com>


import sys
import unittest

from dateutil import parser

# Hack to make sure that tests import the right packages
# due to setuptools behaviour
sys.path.insert(0, '..')

from report.report import Report

CONF_FILE = 'test.cfg'

class TestReport(unittest.TestCase):
    """Basic tests for the Report class """

    def setUp(self):
        pass

    def test_initialization(self):
        """Test whether attributes are initializated"""

        es_url = None
        start = None
        end = None


        with self.assertRaises(TypeError):
            report = Report()

        with self.assertRaises(SystemExit):
            report = Report(es_url, start, end)

        es_url = 'http://localhost:9200'
        start = parser.parse('1900-01-01')
        end = parser.parse('2100-01-01')
        data_sources = ['git']

        report = Report(es_url, start, end, data_sources=data_sources)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    unittest.main(buffer=True, warnings='ignore')
