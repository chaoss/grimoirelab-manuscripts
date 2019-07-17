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
#     Valerio Cosentino <valcos@bitergia.com>
#

import unittest
from elasticsearch import Elasticsearch


ES_URL = "http://127.0.0.1:9200"


class TestBaseElasticSearch(unittest.TestCase):
    """
    Test base class from which all the test classes inherit.
    All the variables common to the tests can be declared here.
    """

    es = Elasticsearch([ES_URL], timeout=3600, max_retries=50, retry_on_timeout=True)
