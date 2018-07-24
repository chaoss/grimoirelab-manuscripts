#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
#     Valerio Cosentino <valcos@bitergia.com>
#     Pranjal Aswani <aswani.pranjal@gmail.com>

import os
import sys
import json
import requests
import configparser
from datetime import datetime

sys.path.insert(0, '..')

from grimoire_elk.elk import load_identities
from grimoire_elk.utils import get_connectors, get_elastic


ES_URL = "http://localhost:9200"
USER = "root"
PASSWORD = ""
DB_SORTINGHAT = "test_sh"
CONFIG_FILE = "tests.conf"


DATA_SOURCES = {
    "git": ["test_git_raw", "test_git"],
    "github_issues": ["test_github_issues_raw", "test_github_issues"],
    "github_prs": ["test_github_prs_raw", "test_github_prs"]
}


def data2es(items, ocean):
    def ocean_item(item):
        # Hack until we decide the final id to use
        if 'uuid' in item:
            item['ocean-unique-id'] = item['uuid']
        else:
            # twitter comes from logstash and uses id
            item['uuid'] = item['id']
            item['ocean-unique-id'] = item['id']

        # Hack until we decide when to drop this field
        if 'updated_on' in item:
            updated = datetime.fromtimestamp(item['updated_on'])
            item['metadata__updated_on'] = updated.isoformat()
        if 'timestamp' in item:
            ts = datetime.fromtimestamp(item['timestamp'])
            item['metadata__timestamp'] = ts.isoformat()

        # the _fix_item does not apply to the test data for Twitter
        try:
            ocean._fix_item(item)
        except KeyError:
            pass

        return item

    items_pack = []  # to feed item in packs

    for item in items:
        item = ocean_item(item)
        if len(items_pack) >= ocean.elastic.max_items_bulk:
            ocean._items_to_es(items_pack)
            items_pack = []
        items_pack.append(item)
    inserted = ocean._items_to_es(items_pack)

    return inserted


def setup_data_source(data_source, raw_index, enrich_index):

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    es_con = dict(config.items('Elasticsearch'))['url']
    connectors = get_connectors()

    maxDiff = None
    db_user = ''
    db_password = ''

    if 'Database' in config:
        if 'user' in config['Database']:
            db_user = config['Database']['user']
        if 'password' in config['Database']:
            db_password = config['Database']['password']

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", data_source + ".json")) as f:
        items = json.load(f)

    if data_source in ['github_issues', 'github_prs']:
        data_source = "github"
    # populate raw index
    perceval_backend = None
    clean = True
    ocean_backend = connectors[data_source][1](perceval_backend)
    elastic_ocean = get_elastic(es_con, raw_index, clean, ocean_backend)
    ocean_backend.set_elastic(elastic_ocean)
    data2es(items, ocean_backend)

    enrich_backend = connectors[data_source][2](db_sortinghat=DB_SORTINGHAT,
                                                db_user=db_user,
                                                db_password=db_password)
    elastic_enrich = get_elastic(es_con, enrich_index, clean, enrich_backend)
    enrich_backend.set_elastic(elastic_enrich)

    # Load SH identities
    load_identities(ocean_backend, enrich_backend)

    enrich_count = enrich_backend.enrich_items(ocean_backend)

    print("{} items enriched".format(enrich_count))


def teardown_data_source(raw_index, enrich_index):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    es_con = dict(config.items('Elasticsearch'))['url']

    delete_raw = es_con + "/" + raw_index
    requests.delete(delete_raw, verify=False)

    delete_enrich = es_con + "/" + enrich_index
    requests.delete(delete_enrich, verify=False)
