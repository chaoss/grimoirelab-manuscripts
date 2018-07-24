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

    def setUp(self):
        self.es = Elasticsearch([ES_URL], timeout=3600, max_retries=50, retry_on_timeout=True)

        with open(os.path.join("data", self.name + "_mappings.json")) as f:
            mappings = json.load(f)

        with open(os.path.join("data", self.name + ".json")) as f:
            docs = []
            for line in f.readlines():
                doc = json.loads(line)
                docs.append(doc)

        if self.es.indices.exists(index=self.enrich_index):
            self.es.indices.delete(index=self.enrich_index)

        self.es.indices.create(index=self.enrich_index, body=mappings)

        for doc in docs:
            doc['_index'] = self.enrich_index
            self.es.indices.refresh(index=self.enrich_index)
            helpers.bulk(self.es, [doc], raise_on_error=True)

        self.es.indices.refresh(index=self.enrich_index)

    def tearDown(self):
        self.es.indices.delete(index=self.enrich_index)
