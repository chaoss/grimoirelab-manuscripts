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
#     Santiago Dueñas <sduenas@bitergia.com>
#

import os
import sys
import json
import logging
import unittest

from elasticsearch import Elasticsearch, helpers

ES_URL = "http://127.0.0.1:9200"

names = ["git_commit", "github_issues", "github_prs"]

# The names of the enrich indices that are to be set up in ES
enrich_indices = ["git_enrich", "github_issues_enrich", "github_prs_enrich"]


def setUpModule():
    """
    Set up the common fixtures for all the tests in the module.
    """

    es = Elasticsearch([ES_URL], timeout=3600, max_retries=50, retry_on_timeout=True)

    for name, enrich_index in zip(names, enrich_indices):

        with open(os.path.join("data/mappings", name + "_mappings.json")) as f:
            mappings = json.load(f)

        with open(os.path.join("data/indices", name + ".json")) as f:
            docs = []
            for line in f.readlines():
                doc = json.loads(line)
                docs.append(doc)

        if es.indices.exists(index=enrich_index):
            es.indices.delete(index=enrich_index)

        es.indices.create(index=enrich_index, body=mappings)

        for doc in docs:
            doc['_index'] = enrich_index
            es.indices.refresh(index=enrich_index)
            helpers.bulk(es, [doc], raise_on_error=True)

        es.indices.refresh(index=enrich_index)


def tearDownModule():
    """
    Destroy the test fixtures.
    """

    es = Elasticsearch([ES_URL], timeout=3600, max_retries=50, retry_on_timeout=True)
    for enrich_index in enrich_indices:
        es.indices.delete(index=enrich_index)


if __name__ == '__main__':
    setUpModule()
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_suite = unittest.TestLoader().discover('.', pattern='test*.py')
    result = unittest.TextTestRunner(buffer=True).run(test_suite)
    tearDownModule()
    sys.exit(not result.wasSuccessful())
