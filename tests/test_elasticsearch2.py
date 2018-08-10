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
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Valerio Cosentino <valcos@bitergia.com>

from base import TestBaseElasticSearch

ENRICH_INDEX = "git_enrich"


class TestGit(TestBaseElasticSearch):
    """Base class to test new_functions.py"""

    def test_read_items(self):
        """Check that the items fetched from the data folder are correctly loaded"""

        page = self.es.search(
            index=ENRICH_INDEX,
            scroll="60m",
            size=200,
            body={"query": {"match_all": {}}}
        )

        sid = page['_scroll_id']
        scroll_size = page['hits']['total']

        if scroll_size == 0:
            return

        data = []
        while scroll_size > 0:

            for item in page['hits']['hits']:
                data.append(item['_source'])

            page = self.es.scroll(scroll_id=sid, scroll='60m')
            sid = page['_scroll_id']
            scroll_size = len(page['hits']['hits'])

        self.assertEqual(len(data), 1244)
