# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     Alvaro del Castillo <acs@bitergia.com>
#


import os
import sys
import shutil
import tempfile
import unittest
import subprocess

from dateutil import parser

# Hack to make sure that tests import the right packages
# due to setuptools behaviour
sys.path.insert(0, '..')

from manuscripts.report import Report

CONF_FILE = 'test.cfg'


class TestReport(unittest.TestCase):
    """Basic tests for the Report class """

    def setUp(self):
        self.es_url = 'http://localhost:9200'
        self.start = parser.parse('1900-01-01')
        self.end = parser.parse('2100-01-01')
        self.data_sources = ['git']

        self.report = Report(self.es_url, self.start, self.end, data_sources=self.data_sources)

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

    def test_replace_text_dir(self):
        """Test whether we can replace one string with another
        string in all the files containing the first string"""

        # -----Setting up variables to test the function-----
        # create a temp directory
        temp_path = tempfile.mkdtemp(prefix='manuscripts_')

        current_dir = os.path.dirname(os.path.abspath(__file__))
        # path to where the original report.tar.gz file is stored
        report_path = os.path.join(current_dir, 'data/test_report.tar.gz')

        # extract the file into the temp directory
        subprocess.check_call(['tar', '-xzf', report_path, '-C', temp_path])
        temp_report_path = os.path.join(temp_path, 'test_report')

        report_file1 = os.path.join(temp_report_path, 'report_file1.tex')
        report_file2 = os.path.join(temp_report_path, 'report_file2.tex')
        report_file3 = os.path.join(temp_report_path, 'report_file3.tex')
        data_file1 = os.path.join(temp_report_path, 'data/data_file1.tex')
        data_file2 = os.path.join(temp_report_path, 'data/data_file2.tex')

        # files that will be changed when replace_text_dir function is called
        tex_files_to_change = [report_file1, report_file2, data_file1]

        # files that should not change when replace_text_dir function is called
        tex_files_not_to_change = [report_file3, data_file2]

        # -----Test the function-----

        self.report.replace_text_dir(temp_report_path, "Open Source is Awesome!", "REPLACED-TEXT")
        self.report.replace_text_dir(temp_report_path, "Open Source is Awesome!", "REPLACED-TEXT", "data/*.tex")

        for file in tex_files_to_change:
            with open(file, 'r') as f:
                self.assertIn("REPLACED-TEXT", f.read())

        for file in tex_files_not_to_change:
            with open(file, 'r') as f:
                self.assertNotIn("REPLACED-TEXT", f.read())

        # -----Cleaning up-----
        shutil.rmtree(temp_path)

    def test_period_name(self):
        """
        Test whether the period name for a date is build correctly
        :return:
        """

        period_name = "18-Q1"

        # The data is the next period date
        period_date = parser.parse('2018-04-01')
        self.assertEqual(Report.build_period_name(period_date), period_name)

        # The data is the start of a period
        period_date = parser.parse('2018-01-01')
        self.assertEqual(Report.build_period_name(period_date, start_date=True), period_name)

        # The period is not a quarter
        with self.assertRaises(RuntimeError):
            Report.build_period_name(period_date, interval="day")

    def tearDown(self):
        pass


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    unittest.main(buffer=True, warnings='ignore')
