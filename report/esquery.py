#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Helper classes for doing queries to ElasticSearch
#
# Copyright (C) 2016 Bitergia
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
#   Alvaro del Castillo San Felix <acs@bitergia.com>
#

import json

from datetime import timezone

from elasticsearch_dsl import A, Search, Q

USE_ELASTIC_DSL = True

class ElasticQuery():
    """ Helper class for building Elastic queries """

    AGGREGATION_ID = 1  # min aggregation identifier
    AGG_SIZE = 100  # Default max number of buckets
    ES_PRECISION = 3000

    @classmethod
    def __get_query_filters(cls, filters=None, inverse=False):
        """ {"name1":"value1", "name2":"value2"} """

        query_filters = ''

        if not filters:
            return query_filters

        for name in filters:
            if name[0] == '*' and not inverse:
                # An inverse filter and not inverse mode
                continue
            if name[0] != '*' and inverse:
                # A direct filter and inverse mode
                continue
            field_name = name[1:] if name[0] == '*' else name
            query_filters += """
                {
                  "match": {
                    "%s": {
                      "query": "%s",
                      "type": "phrase"
                    }
                  }
                }
            """ % (field_name, filters[name])
            query_filters += ","

        query_filters = query_filters[:-1]  # Remove the last comma

        return query_filters

    @classmethod
    def __get_query_range(cls, date_field, start=None, end=None):

        if not start and not end:
            return ''

        start_end = ''
        if start:
            start_end = '"gte": "%s",' % start.isoformat()
        if end:
            start_end += '"lte": "%s",' % end.isoformat()
        start_end = start_end[:-1]  # remove last comma

        query_range = """
        {
          "range": {
            "%s": {
              %s
            }
          }
        }
        """ % (date_field, start_end)

        return query_range

    @classmethod
    def __get_query_basic(cls, date_field=None, start=None, end=None,
                          filters=None):
        if not date_field:
            query_range = ''
        else:
            query_range = cls.__get_query_range(date_field, start, end)
            if query_range:
                query_range = ", " +  query_range

        query_filters = cls.__get_query_filters(filters)
        if query_filters:
            query_filters = ", " +  query_filters

        query_filters_inverse = cls.__get_query_filters(filters, inverse=True)

        if query_filters_inverse:
            query_filters_inverse = ', "must_not": [%s]' % query_filters_inverse

        query_basic = """
          "query": {
            "bool": {
              "must": [
                {
                  "query_string": {
                    "analyze_wildcard": true,
                    "query": "*"
                  }
                }
                %s %s
              ] %s
            }
          }
        """ % (query_range, query_filters, query_filters_inverse)

        return query_basic

    @classmethod
    def __get_query_agg_terms(cls, field):
        query_agg = """
          "aggs": {
            "%i": {
              "terms": {
                "field": "%s",
                "size": %i,
                "order": {
                    "_count": "desc"
                }
              }
            }
          }
        """ % (cls.AGGREGATION_ID, field, cls.AGG_SIZE)
        return query_agg

    @classmethod
    def __get_query_agg_max(cls, field):
        query_agg = """
          "aggs": {
            "%i": {
              "max": {
                "field": "%s"
              }
            }
          }
        """ % (cls.AGGREGATION_ID, field)

        return query_agg

    @classmethod
    def __get_query_agg_percentiles(cls, field, agg_id=None):
        if not agg_id:
            agg_id=cls.AGGREGATION_ID
        query_agg = """
          "aggs": {
            "%i": {
              "percentiles": {
                "field": "%s"
              }
            }
          }
        """ % (agg_id, field)

        return query_agg

    @classmethod
    def __get_query_agg_avg(cls, field, agg_id=None):
        if not agg_id:
            agg_id=cls.AGGREGATION_ID
        query_agg = """
          "aggs": {
            "%i": {
              "avg": {
                "field": "%s"
              }
            }
          }
        """ % (agg_id, field)

        return query_agg


    @classmethod
    def __get_query_agg_cardinality(cls, field, agg_id=None):
        if not agg_id:
            agg_id=cls.AGGREGATION_ID
        query_agg = """
          "aggs": {
            "%i": {
              "cardinality": {
                "field": "%s",
                "precision_threshold": %i
              }
            }
          }
        """ % (agg_id, field, cls.ES_PRECISION)

        return query_agg

    @classmethod
    def __get_bounds(cls, start=None, end=None):
        """ Return a dict with the bounds for a date_historgram agg """

        bounds = ''
        if start or end:
            # Extend bounds so we have data until start and end
            start_ts = None
            end_ts = None
            if start:
                start_ts = start.replace(tzinfo=timezone.utc).timestamp()
                start_ts_ms = start_ts * 1000  # ES uses ms
            if end:
                end_ts = end.replace(tzinfo=timezone.utc).timestamp()
                end_ts_ms = end_ts * 1000  # ES uses ms
            bounds_data = ''
            if start:
                bounds_data = '"min": %i,' % start_ts_ms
            if end:
                bounds_data += '"max": %i,' % end_ts_ms

            bounds_data = bounds_data[:-1] # remove last comma

            bounds = """{
                "extended_bounds": {
                    %s
                }
            } """ % (bounds_data)
            bounds = json.loads(bounds)

        return bounds

    @classmethod
    def __get_query_agg_ts(cls, field, time_field, interval=None,
                           time_zone=None, start=None, end=None,
                           agg_type='count', offset=None):
        """ Time series for an aggregation metric """
        if not interval:
            interval = '1M'
        if not time_zone:
            time_zone = 'UTC'

        if not field:
            field_agg = ''
        else:
            if agg_type == "cardinality":
                field_agg = cls.__get_query_agg_cardinality(field, agg_id=cls.AGGREGATION_ID+1)
            elif agg_type == "avg":
                field_agg = cls.__get_query_agg_avg(field, agg_id=cls.AGGREGATION_ID+1)
            elif agg_type == "percentiles":
                field_agg = cls.__get_query_agg_percentiles(field, agg_id=cls.AGGREGATION_ID+1)
            else:
                raise RuntimeError("Aggregation of %s in ts not supported" % agg_type)
            field_agg = ", " + field_agg

        bounds = None
        if start or end:
            if not offset:
                # With offset and quarter interval bogus buckets are added
                # to the start and to the end if extended_bounds is used
                # https://github.com/elastic/elasticsearch/issues/23776
                bounds_dict = cls.__get_bounds(start, end)
                bounds = json.dumps(bounds_dict)[1:-1]  # Remove {} from json
                bounds = "," + bounds # it is the last element

        query_agg = """
             "aggs": {
                "%i": {
                  "date_histogram": {
                    "field": "%s",
                    "interval": "%s",
                    "time_zone": "%s",
                    "min_doc_count": 0
                    %s
                  }
                  %s
                }
            }
        """ % (cls.AGGREGATION_ID, time_field, interval, time_zone, bounds,
               field_agg)

        return query_agg


    @classmethod
    def get_count(cls, date_field=None, start=None, end=None, filters=None):
        """ Total number of items """
        query_basic = cls.__get_query_basic(date_field=date_field,
                                            start=start, end=end,
                                            filters=filters)
        query = """
            {
              "size": 0,
              %s
              }
        """ % (query_basic)


        return query


    @classmethod
    def get_agg(cls, field=None, date_field=None, start=None, end=None,
                filters=None, agg_type="terms", offset=None, interval=None):
        """ if field and date_field the date_histogram of the agg is collected """

        query_basic = cls.__get_query_basic(date_field=date_field,
                                            start=start, end=end,
                                            filters=filters)

        if agg_type == "count":
            agg_type = 'cardinality'
        elif agg_type == "median":
            agg_type = 'percentiles'
        elif agg_type == "average":
            agg_type = 'avg'

        # Get only the aggs not the hits
        s = Search()[0:0]

        for f in filters:
            param = {f: filters[f]}
            if f[0:1] == "*":
                param = {f[1:]: filters[f]}
                s = s.query(~Q("match", **param))
            else:
                s = s.query(Q("match", **param))

        date_filter = cls.__get_query_range(date_field, start, end)

        s = s.query(json.loads(date_filter))

        if not interval:
            if agg_type == "terms":
                query_agg = ElasticQuery.__get_query_agg_terms(field)
            elif agg_type == "max":
                query_agg = ElasticQuery.__get_query_agg_max(field)
            elif agg_type == "cardinality":
                query_agg = ElasticQuery.__get_query_agg_cardinality(field)
            elif agg_type == "percentiles":
                query_agg = ElasticQuery.__get_query_agg_percentiles(field)
            elif agg_type == "avg":
                query_agg = ElasticQuery.__get_query_agg_avg(field)
            else:
                raise RuntimeError("Aggregation of %s not supported" % agg_type)
        else:
            query_agg = ElasticQuery.__get_query_agg_ts(field, date_field,
                                                        start=start, end=end,
                                                        interval=interval,
                                                        agg_type=agg_type,
                                                        offset=offset)

        if agg_type not in ['percentiles', 'terms', 'avg']:
            field_agg = A(agg_type, field=field,
                          precision_threshold=cls.ES_PRECISION)
        else:
            field_agg = A(agg_type, field=field)

        agg_id = cls.AGGREGATION_ID

        if interval:
            # Two aggs, date histogram and the field+agg_type
            bounds = ElasticQuery.__get_bounds(start, end)
            if offset:
                # With offset and quarter interval bogus buckets are added
                # to the start and to the end if extended_bounds is used
                # https://github.com/elastic/elasticsearch/issues/23776
                bounds = {"offset": offset}
            ts_agg = A('date_histogram', field=date_field, interval=interval,
                       time_zone="UTC", min_doc_count=0, **bounds)
            s.aggs.bucket(agg_id, ts_agg).metric(agg_id+1, field_agg)
        else:
            s.aggs.bucket(agg_id, field_agg)


        query = """
            {
              "size": 0,
              %s,
              %s
              }
        """ % (query_agg, query_basic)

        if USE_ELASTIC_DSL:
            return json.dumps(s.to_dict())
        else:
            return query
