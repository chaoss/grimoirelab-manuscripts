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

import sys
import json
import unittest

from datetime import datetime

# Hack to make sure that tests import the right packages
# due to setuptools behaviour
sys.path.insert(0, '..')

from manuscripts.esquery import ElasticQuery


class TestEsquery(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        """Set up the necessary functions to run unittests"""
        self.es = ElasticQuery()

        self.field = "AGG_FIELD"  # field to aggregate
        self.date_field = "DATE_FIELD"  # field for range
        self.filters = {"name1": "value1", "name2": "value2", "*name3": "value3"}
        self.offset = 2
        self.interval = "1y"
        self.timezone = "UTC"
        self.start = datetime(2017, 5, 23)  # from date
        self.end = datetime(2018, 5, 23)  # to date

    def test_get_query_filters(self):
        """Test whether correct es_dsl query filters are generated"""

        # test with no filters
        self.assertEqual(self.es._ElasticQuery__get_query_filters(), [])

        # test for normal filters i.e non-inverse filters
        test_list_normal = [{"match_phrase": {"name1": "value1"}},
                            {"match_phrase": {"name2": "value2"}}]
        output_list_normal = self.es._ElasticQuery__get_query_filters(self.filters)
        for index, item in enumerate(output_list_normal):
            self.assertDictEqual(test_list_normal[index], item.to_dict())

        # test for inverse filters
        test_list_inverse = [{"match_phrase": {"name3": "value3"}}]
        output_list_inverse = self.es._ElasticQuery__get_query_filters(self.filters, inverse=True)
        for index, item in enumerate(output_list_inverse):
            self.assertDictEqual(test_list_inverse[index], item.to_dict())

    def test_get_query_range(self):
        """Test if appropriate range filter is created or not"""

        # test when no start or end date is given
        self.assertEqual(self.es._ElasticQuery__get_query_range(self.date_field), "")

        # test when all the params are given
        test_range_dict = {
            "DATE_FIELD": {
                "gte": "2017-05-23T00:00:00",
                "lte": "2018-05-23T00:00:00"
            }
        }
        self.assertDictEqual(self.es._ElasticQuery__get_query_range(date_field=self.date_field,
                             start=self.start, end=self.end), test_range_dict)

    def test_get_query_basic(self):
        """Test if basic queries can be formed or not"""

        # test without filters
        test_no_filters = {
            "query": {
                "bool": {
                    "filter": [
                        {
                            "range": {
                                "DATE_FIELD": {
                                    "gte": "2017-05-23T00:00:00",
                                    "lte": "2018-05-23T00:00:00"
                                }
                            }
                        }
                    ]
                }
            }
        }
        self.assertDictEqual(self.es._ElasticQuery__get_query_basic(self.date_field, self.start, self.end).to_dict(),
                             test_no_filters)

        # test with everything (range, normal and inverse filters)
        test_with_filters = {
            'query': {
                'bool': {
                    'filter': [
                        {
                            'range': {
                                'DATE_FIELD': {
                                    'gte': '2017-05-23T00:00:00',
                                    'lte': '2018-05-23T00:00:00'
                                }
                            }
                        }
                    ],
                    'must': [
                        {
                            'match_phrase': {
                                'name1': 'value1'
                            }
                        },
                        {
                            'match_phrase': {
                                'name2': 'value2'
                            }
                        }
                    ],
                    'must_not': [
                        {
                            'match_phrase': {
                                'name3': 'value3'
                            }
                        }
                    ]
                }
            }
        }
        self.assertDictEqual(self.es._ElasticQuery__get_query_basic(self.date_field, self.start, self.end,
                             self.filters).to_dict(), test_with_filters)

    def test_query_aggregations(self):
        """Test all the aggregation functions"""

        # ------ Terms aggregation ------
        test_terms_dict = {
            "terms": {
                "field": "AGG_FIELD",
                "size": 100,
                "order": {
                    "_count": "desc"
                }
            }
        }
        agg_id, terms_agg = self.es._ElasticQuery__get_query_agg_terms(self.field, 22)
        # check the output dict
        self.assertDictEqual(test_terms_dict, terms_agg.to_dict())
        # check the cutom agg id
        self.assertEqual(agg_id, 22)

        # ------ Max aggregation ------
        test_max_dict = {
            "max": {
                "field": "AGG_FIELD"
            }
        }
        _, max_agg = self.es._ElasticQuery__get_query_agg_max(self.field)
        # check the output dict
        self.assertDictEqual(test_max_dict, max_agg.to_dict())

        # ------ Avg aggregation ------
        test_avg_dict = {
            "avg": {
                "field": "AGG_FIELD"
            }
        }
        _, avg_agg = self.es._ElasticQuery__get_query_agg_avg(self.field)
        # check the output dict
        self.assertDictEqual(test_avg_dict, avg_agg.to_dict())

        # ------ Percentile aggregation ------
        test_percentiles_dict = {
            "percentiles": {
                "field": "AGG_FIELD"
            }
        }
        _, percentiles_agg = self.es._ElasticQuery__get_query_agg_percentiles(self.field)
        # check the output dict
        self.assertDictEqual(test_percentiles_dict, percentiles_agg.to_dict())

        # ------ Cardinality aggregation ------
        test_cardinality_dict = {
            "cardinality": {
                "field": "AGG_FIELD",
                "precision_threshold": self.es.ES_PRECISION
            }
        }
        _, cardinality_agg = self.es._ElasticQuery__get_query_agg_cardinality(self.field)
        # check the output dict
        self.assertDictEqual(test_cardinality_dict, cardinality_agg.to_dict())

    def test_get_bounds(self):
        """Test the get_bounds function"""

        # with empty parameters
        self.assertEquals(self.es._ElasticQuery__get_bounds(), {})

        test_bounds_dict = {
            "extended_bounds": {
                "min": 1495497600000.0,
                "max": 1527033600000.0
            }
        }
        self.assertDictEqual(self.es._ElasticQuery__get_bounds(self.start, self.end), test_bounds_dict)

    def test_get_query_agg_ts(self):
        """Test the date histogram functionality"""

        # with empty parameters (this TypeError is because of the empty bounds dict)
        with self.assertRaises(TypeError):
            self.es._ElasticQuery__get_query_agg_ts()

        # with incompatible aggregation type
        with self.assertRaises(RuntimeError):
            self.es._ElasticQuery__get_query_agg_ts(self.field, self.date_field, start=self.start,
                                                    end=self.end, agg_type='count', offset=None)

        # with no aggregation field
        with self.assertRaises(TypeError):
            self.es._ElasticQuery__get_query_agg_ts(date_field=self.date_field, start=self.start,
                                                    end=self.end, agg_type='avg', offset=None)

        # test with everything and offset==None
        test_cardinality_ts_dict = {
            "date_histogram": {
                "field": "DATE_FIELD",
                "interval": "1y",
                "time_zone": "UTC",
                "min_doc_count": 0,
                "extended_bounds": {
                    "min": 1495497600000.0,
                    "max": 1527033600000.0
                }
            },
            "aggs": {
                2: {
                    "cardinality": {
                        "field": "AGG_FIELD",
                        "precision_threshold": 3000
                    }
                }
            }
        }
        agg_id, test_ts_dict1 = self.es._ElasticQuery__get_query_agg_ts(self.field, self.date_field,
                                                                        interval=self.interval,
                                                                        time_zone=self.timezone,
                                                                        start=self.start, end=self.end,
                                                                        agg_type='cardinality', offset=None)
        self.assertDictEqual(test_ts_dict1.to_dict(), test_cardinality_ts_dict)
        self.assertEqual(agg_id, 1)

        # test with everything and offset==2(days)
        test_avg_ts_dict = {
            "date_histogram": {
                "field": "DATE_FIELD",
                "interval": "1M",
                "time_zone": "UTC",
                "min_doc_count": 0,
                "offset": 2
            },
            "aggs": {
                2: {
                    "avg": {
                        "field": "AGG_FIELD"
                    }
                }
            }
        }
        _, test_ts_dict2 = self.es._ElasticQuery__get_query_agg_ts(self.field, self.date_field,
                                                                   interval="1M", time_zone=self.timezone,
                                                                   start=self.start, end=self.end,
                                                                   agg_type='avg', offset=2)
        self.assertDictEqual(test_ts_dict2.to_dict(), test_avg_ts_dict)

    def test_get_agg(self):
        """Test the aggregation function"""
        self.maxDiff = None
        # check with everything and interval==None
        # aggregation names should be numeric here and not a string value,
        # they are string because get_agg() function converts the dict into string
        # using json.dumps and we are loading that string again using json.loads
        # this should be changed when get_aggs is changed to use only es_dsl
        test_agg_dict1 = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_phrase": {
                                "name1": "value1"
                            }
                        },
                        {
                            "match_phrase": {
                                "name2": "value2"
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "match_phrase": {
                                "name3": "value3"
                            }
                        }
                    ],
                    "filter": [
                        {
                            "range": {
                                "DATE_FIELD": {
                                    "gte": "2017-05-23T00:00:00",
                                    "lte": "2018-05-23T00:00:00"
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "1": {
                    "terms": {
                        "field": "AGG_FIELD",
                        "size": 100,
                        "order": {
                            "_count": "desc"
                        }
                    }
                }
            },
            "size": 0
        }
        self.assertDictEqual(json.loads(self.es.get_agg(field=self.field, date_field=self.date_field, start=self.start,
                                        end=self.end, filters=self.filters, agg_type="terms", offset=None,
                                        interval=None)), test_agg_dict1)

        # check with everything and interval==1year
        test_agg_dict2 = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match_phrase": {
                                "name1": "value1"
                            }
                        },
                        {
                            "match_phrase": {
                                "name2": "value2"
                            }
                        }
                    ],
                    "must_not": [
                        {
                            "match_phrase": {
                                "name3": "value3"
                            }
                        }
                    ],
                    "filter": [
                        {
                            "range": {
                                "DATE_FIELD": {
                                    "gte": "2017-05-23T00:00:00",
                                    "lte": "2018-05-23T00:00:00"
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                '1': {
                    "date_histogram": {
                        "field": "DATE_FIELD",
                        "interval": "1y",
                        "time_zone": "UTC",
                        "min_doc_count": 0,
                        "extended_bounds": {
                            "min": 1495497600000.0,
                            "max": 1527033600000.0
                        }
                    },
                    "aggs": {
                        '2': {
                            "cardinality": {
                                "field": "AGG_FIELD",
                                "precision_threshold": 3000
                            }
                        }
                    }
                }
            },
            "size": 0
        }
        self.assertDictEqual(json.loads(self.es.get_agg(field=self.field, date_field=self.date_field, start=self.start,
                                        end=self.end, filters=self.filters, agg_type="cardinality",
                                        offset=None, interval=self.interval)), test_agg_dict2)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    unittest.main(buffer=True, warnings='ignore')
