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
#     Pranjal Aswani <aswani.pranjal@gmail.com>

import os
import sys
import json
import unittest

from datetime import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import A

from grimoire_elk.elk import feed_backend, enrich_backend

# Hack to make sure that tests import the right packages
# due to setuptools behaviour
sys.path.insert(0, '..')

from manuscripts2.elasticsearch import Query, Index

# We are going to insert perceval's data into elasticsearch
# So that we can test the the functions
ES_URL = "http://127.0.0.1:9200"
REPOSITORY = "https://github.com/chaoss/grimoirelab-perceval"
GIT_ENRICH_INDEX = "perceval_git_test"
GIT_RAW_INDEX = "perceval_git_test_raw"
BACKEND = "git"
BACKEND_PARAMS = [REPOSITORY]

# Some aggregation results as seen on 10th July 2018
NUM_COMMITS = 1209
NUM_AUTHORS = 19
NUM_COMMITTERS = 10
SUM_LINES_CHANGED = 196209
AVERAGE_LINES_ADDED = 125.2
# This was tested over 50 values and 10 was the most stable one
PERCENTILE_LINES_ADDED = 10
MIN_GRIMOIRE_CREATION_DATE = 1439914107000
MAX_COMMIT_DATE = 1531248096000

# These commits have "grimoire_creation_date" greater than 10/07/2016
# And "commit_date" less than 10/07/2017 to test double range
NUM_COMMITS2 = 389

FETCH_AGGREGATION_RESULTS_DATA1 = "data/num_hash_by_authors.json"
FETCH_SOURCE_RESULTS_DATA1 = "data/authors.json"
TERMS_AGGREGATION_DATA = "data/terms_aggregation_authors.json"
SUM_LINES_ADDED_BY_AUTHORS = "data/sum_lines_added_by_authors.json"
NUM_HASHES_BY_QUARTER = "data/num_hashes_by_quarter.json"


def load_json_file(filename, mode="r"):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        json_content = json.load(f)
    return json_content


class TestElasticsearch(unittest.TestCase):
    """Base class to test new_functions.py"""

    maxDiff = None

    @classmethod
    def setUpClass(cls):

        cls.es = Elasticsearch(hosts=ES_URL)

        feed_backend(ES_URL, clean=True, fetch_archive=False, backend_name=BACKEND,
                     backend_params=BACKEND_PARAMS, es_index=GIT_RAW_INDEX,
                     es_index_enrich=GIT_ENRICH_INDEX, project=None, arthur=False)

        enrich_backend(ES_URL, clean=True, backend_name=BACKEND,
                       backend_params=BACKEND_PARAMS,
                       ocean_index=GIT_RAW_INDEX,
                       ocean_index_enrich=GIT_ENRICH_INDEX,
                       unaffiliated_group=None)

    def setUp(self):
        """Set up the necessary functions to run unittests"""

        self.es = Elasticsearch(ES_URL)
        self.github_index = Index(index_name=GIT_ENRICH_INDEX,
                                  es=self.es)

        self.Query_test_object = Query(self.github_index)

        self.field1 = "hash"
        self.field2 = "author_name"
        self.field3 = "lines_added"
        self.field4 = "lines_changed"
        self.date_field1 = "grimoire_creation_date"
        self.date_field2 = "commit_date"

        # Using sample filters not related to the GIT_INDEX
        self.filters = [{"item_type": "pull_request"}, {"item_type": "issue"}]
        self.offset = 2
        self.interval = "month"
        self.timezone = "UTC"

        # Make sure to change the CONSTANTS defined above if you change
        # the end date here before testing because tests might fail otherwise
        self.start = datetime(2015, 1, 1)  # from date
        self.end = datetime(2018, 7, 10)  # to date
        self.size = 10000
        self.precision_threshold = 3000

    def test_initialization(self):
        """
        Test if we can create an Query object without parameters
        """

        with self.assertRaises(TypeError):
            github_obj = Query()

        query = Query(self.github_index)

    def test_add_query(self):
        """
        Test if we can add a normal query into the search variable of Query object
        """

        # Add the query
        self.Query_test_object.add_query(self.filters[0])
        # check whether the query was inserted into the Search object or not
        self.assertDictEqual(self.Query_test_object.search.query.to_dict()['match'],
                             {'item_type': 'pull_request'})

    def test_add_inverse_query(self):
        """
        Test if we can add a inverse query into the search variable of Query object
        """

        self.Query_test_object.add_inverse_query(self.filters[1])
        # check whether the query was inserted into the Search object or not
        self.assertDictEqual(self.Query_test_object.search.query.to_dict()['bool']['must_not'][0],
                             {'match': {'item_type': 'issue'}})

    def test_get_sum(self):
        """
        Test the sum aggregation
        """

        field = self.field4
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_sum()

        # with field param
        self.Query_test_object.get_sum(field=field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        self.assertEqual(int(self.Query_test_object.get_aggs()), SUM_LINES_CHANGED)

    def test_get_average(self):
        """
        Test the average aggregation
        """

        field = self.field3
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_average()

        # with field param
        self.Query_test_object.get_average(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        avg_lines_changed = "%.1f" % self.Query_test_object.get_aggs()
        avg_lines_changed = float(avg_lines_changed)
        self.assertEqual(avg_lines_changed, AVERAGE_LINES_ADDED)

    def test_get_percentiles(self):
        """
        Test the percentiles aggregation
        """

        field = self.field3
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_percentiles()

        # with field param
        self.Query_test_object.get_percentiles(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        percentiles = int(self.Query_test_object.get_aggs())
        self.assertEqual(percentiles, PERCENTILE_LINES_ADDED)

    def test_get_terms(self):
        """
        Test the terms aggregation
        """

        field = self.field2
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_terms()

        # with field param
        self.Query_test_object.get_terms(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        response = self.Query_test_object.fetch_aggregation_results()['aggregations']
        buckets = {"buckets": response['0']['buckets']}
        authors = load_json_file(TERMS_AGGREGATION_DATA)
        self.assertEqual(authors, buckets)

    def test_get_min(self):
        """
        Test the min aggregation
        """

        field = self.date_field1
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_min()

        # with field param
        self.Query_test_object.get_min(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        self.assertEqual(self.Query_test_object.get_aggs(), MIN_GRIMOIRE_CREATION_DATE)

    def test_get_max(self):
        """
        Test the max aggregation
        """

        field = self.date_field2
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_max()

        # with field param
        self.Query_test_object.get_max(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        self.assertEqual(self.Query_test_object.get_aggs(), MAX_COMMIT_DATE)

    def test_get_cardinality(self):
        """
        Test the cardniality(count) aggregation
        """

        field = "committer_name"
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_cardinality()

        # with field param
        self.Query_test_object.get_cardinality(field)\
                              .since(start=self.start)\
                              .until(end=self.end)
        self.assertEqual(self.Query_test_object.get_aggs(), NUM_COMMITTERS)

    def test_get_extended_stats(self):
        """
        Test the extended statistics aggregation
        """

        field = self.field1
        # without field param
        with self.assertRaises(AttributeError):
            self.Query_test_object.get_extended_stats()

        # with field param
        self.Query_test_object.get_extended_stats(field)
        test_agg = A("extended_stats", field=field)
        agg_name, agg = self.Query_test_object.aggregations.popitem()
        self.assertEqual('extended_stats_' + field, agg_name)
        self.assertEqual(agg, test_agg)

    def test_since(self):
        """
        Test the start date in range for a field
        """

        field = self.date_field1

        test_date = None
        self.Query_test_object.since(start=self.start, field=field)
        filtrs = self.Query_test_object.search.to_dict()['query']['bool']['filter']
        for filtr in filtrs:
            if 'range' in filtr:
                if field in filtr['range']:
                    test_date = filtr['range'][field]['gte']
                    break
        self.assertEqual(test_date, self.start.isoformat())

    def test_until(self):
        """
        Test the end date in range for a field
        """

        field = self.date_field2

        test_date = None
        self.Query_test_object.until(end=self.end, field=field)
        filtrs = self.Query_test_object.search.to_dict()['query']['bool']['filter']
        for filtr in filtrs:
            if 'range' in filtr:
                if field in filtr['range']:
                    test_date = filtr['range'][field]['lte']
                    break
        self.assertEqual(test_date, self.end.isoformat())

    def test_since_until(self):
        """
        Test since and until simultaneously on 2 different fields
        """

        self.Query_test_object.get_cardinality(self.field1)\
                              .since(start=datetime(2016, 7, 10), field=self.date_field1)\
                              .until(end=datetime(2017, 7, 10), field=self.date_field2)
        self.assertEqual(self.Query_test_object.get_aggs(), NUM_COMMITS2)

    def test_by_authors(self):
        """
        Test nested aggregation wrt authors
        """

        self.Query_test_object.get_sum(self.field3)\
                              .by_authors(self.field2)\
                              .since(start=self.start)\
                              .until(end=self.end)

        response = self.Query_test_object.fetch_aggregation_results()['aggregations']
        buckets = {"buckets": response['0']['buckets']}

        sum_lines_added = load_json_file(SUM_LINES_ADDED_BY_AUTHORS)
        self.assertEqual(sum_lines_added, buckets)

    def test_by_organizations(self):
        """
        Test nested aggregation wrt author organizations
        Just checking if the aggregation exists in the dict, for now
        Because there is no org field in 'git' data source
        """

        test_agg = A("terms", field="author_domain", missing="others", size=self.size)
        test_agg.metric(0, "cardinality", field=self.field1, precision_threshold=self.precision_threshold)

        self.Query_test_object.get_cardinality(self.field1)\
                              .by_organizations("author_domain")
        agg_name, agg = self.Query_test_object.aggregations.popitem()

        self.assertEqual(agg, test_agg, msg='\n{0}\n{1}'.format(agg, test_agg))

    def test_by_period_without_args(self):
        """
        Test the date histogram aggregation with no parameters
        """

        test_agg = A("date_histogram", field=self.date_field1,
                     interval=self.interval, time_zone=self.timezone,
                     min_doc_count=0, **{})
        test_agg.metric(0, "cardinality", field=self.field1, precision_threshold=self.precision_threshold)

        self.Query_test_object.get_cardinality(self.field1)\
                              .by_period()
        agg_name, agg = self.Query_test_object.aggregations.popitem()

        self.assertEqual(agg, test_agg, msg='\n{0}\n{1}'.format(agg, test_agg))

    def test_by_period_with_params(self):
        """
        Test the date_histogram aggregation with all the parameters
        """

        self.Query_test_object.since(start=self.start)\
                              .until(end=self.end)\
                              .get_cardinality(self.field1)\
                              .by_period(field=self.date_field2,
                                         period="quarter",
                                         timezone=self.timezone)

        response = self.Query_test_object.fetch_aggregation_results()['aggregations']
        hash_by_period = load_json_file(NUM_HASHES_BY_QUARTER)
        buckets = {"buckets": response['0']['buckets']}

        self.assertEqual(hash_by_period, buckets)

    def test_multiple_aggregations(self):
        """
        Test if multiple aggregations can be added
        Choosing any 3 aggregations, randomly
        """

        self.Query_test_object.get_cardinality(self.field1)\
                              .get_sum(self.field3)\
                              .get_terms(self.field2)

        aggregations = [A("cardinality", field=self.field1,
                          precision_threshold=self.precision_threshold),
                        A("sum", field=self.field3),
                        A("terms", field=self.field2, order={'_count': 'desc'},
                          size=self.size)]

        for test_agg in aggregations[::-1]:
            agg_name, agg = self.Query_test_object.aggregations.popitem()
            self.assertEqual(agg, test_agg)

    def test_nested_aggregations(self):
        """
        Tested 3 level nested aggregation
        """

        self.Query_test_object.get_cardinality(self.field1)\
                              .by_authors()\
                              .by_period(period="quarter")

        period_agg = A("date_histogram", field=self.date_field1,
                       interval="quarter", time_zone=self.timezone,
                       min_doc_count=0, **{})

        author_agg = A("terms", field="author_uuid", missing="others", size=self.size)

        author_agg.metric(0, "cardinality",
                          field=self.field1,
                          precision_threshold=self.precision_threshold)
        period_agg.metric(0, author_agg)

        agg_name, agg = self.Query_test_object.aggregations.popitem()
        self.assertEqual(agg, period_agg)

    def test_fetch_aggregation_results(self):
        """
        Test the fetched aggregation data
        """

        self.Query_test_object.until(end=self.end)\
                              .get_cardinality(self.field1)\
                              .by_authors(field=self.field2)
        response = self.Query_test_object.fetch_aggregation_results()
        aggregations = {"aggregations": response['aggregations']}
        actual_response = load_json_file(FETCH_AGGREGATION_RESULTS_DATA1)

        self.assertDictEqual(aggregations, actual_response)

    def test_fetch_results_from_source(self):
        """
        Testing if specific fields can be fetched from index
        """

        self.Query_test_object.until(end=self.end)
        response = self.Query_test_object.fetch_results_from_source(self.field2)
        actual_response = load_json_file(FETCH_SOURCE_RESULTS_DATA1)
        self.assertEqual(response, actual_response['hits'])

    def test_get_aggs(self):
        """
        Testing single valued aggregations
        """

        self.Query_test_object.until(end=self.end)
        self.Query_test_object.get_cardinality(self.field1)
        num_commits = self.Query_test_object.get_aggs()
        self.assertEqual(NUM_COMMITS, num_commits)

        self.Query_test_object.until(end=self.end)
        self.Query_test_object.get_cardinality(self.field2)
        num_authors = self.Query_test_object.get_aggs()
        self.assertEqual(NUM_AUTHORS, num_authors)

    @classmethod
    def tearDownClass(cls):
        """
        Deleting the indices that were created for the tests
        """

        cls.es.indices.delete(index=GIT_ENRICH_INDEX)
        cls.es.indices.delete(index=GIT_RAW_INDEX)
