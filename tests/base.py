#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Bitergia
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
#     Valerio Cosentino <valcos@bitergia.com>
#

import json
import os
import unittest
from elasticsearch import Elasticsearch, helpers


ES_URL = "http://127.0.0.1:9200"


class TestBaseElasticSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.es = Elasticsearch([ES_URL], timeout=3600, max_retries=50, retry_on_timeout=True)

        with open(os.path.join("data", cls.name + "_mappings.json")) as f:
            mappings = json.load(f)

        with open(os.path.join("data", cls.name + ".json")) as f:
            docs = []
            for line in f.readlines():
                doc = json.loads(line)
                docs.append(doc)

        if cls.es.indices.exists(index=cls.enrich_index):
            cls.es.indices.delete(index=cls.enrich_index)

        cls.es.indices.create(index=cls.enrich_index, body=mappings)

        for doc in docs:
            doc['_index'] = cls.enrich_index
            cls.es.indices.refresh(index=cls.enrich_index)
            helpers.bulk(cls.es, [doc], raise_on_error=True)

        cls.es.indices.refresh(index=cls.enrich_index)

    @classmethod
    def tearDownClass(cls):
        cls.es.indices.delete(index=cls.enrich_index)
