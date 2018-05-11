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
        """
        Convert a dict with the filters to be applied ({"name1":"value1", "name2":"value2"})
        to a DSL string representing these filters.

        :param filters: dict with the filters to be applied
        :param inverse: if True include all the inverse filters (the one starting with *)
        :return: a string with the DSL value for these filters
        """
        """  """

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
        """
        Create a string with range DSL query for the date in date_field from start to end dates.

        :param date_field: field with the date value
        :param start: date with the from value
        :param end: date with the to value
        :return: a string including the range date DSL query
        """

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
        """
        Create a string with the date range and filters DSL query.

        :param date_field: field with the date value
        :param start: date with the from value
        :param end: date with the to value
        :param filters: dict with the filters to be applied
        :return: a string including the DSL query
        """
        if not date_field:
            query_range = ''
        else:
            query_range = cls.__get_query_range(date_field, start, end)
            if query_range:
                query_range = ", " + query_range

        query_filters = cls.__get_query_filters(filters)
        if query_filters:
            query_filters = ", " + query_filters

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
        """
        Create a string with an aggregated DSL query based on a term.

        :param field: field to be used to aggregate
        :return: a string including the DSL query
        """

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
        """
        Create a string with an aggregated DSL query for getting the max value of a field.

        :param field: field from which the get the max value
        :return: a string including the DSL query
        """

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
        """
        Create a string with an aggregated DSL query for getting the percentiles value of a field.
        In general this is used to get the median (0.5) percentil.

        :param field: field from which the get the percentiles values
        :return: a string including the DSL query
        """

        if not agg_id:
            agg_id = cls.AGGREGATION_ID
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
        """
        Create a string with an aggregated DSL query for getting the average value of a field.

        :param field: field from which the get the average value
        :return: a string including the DSL query
        """

        if not agg_id:
            agg_id = cls.AGGREGATION_ID
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
        """
        Create a string with an aggregated DSL query for getting the approximate count of distinct values of a field.

        :param field: field from which the get count of distinct values
        :return: a string including the DSL query
        """

        if not agg_id:
            agg_id = cls.AGGREGATION_ID
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
        """
        Return a dict with the DSL bounds for a date_histogram agg.

        :param start: date from for the date_histogram agg
        :param end: date to for the date_histogram agg
        :return: a dict with the DSL bounds for a date_histogram agg
        """

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

            bounds_data = bounds_data[:-1]  # remove last comma

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
        """
        Create a string with an aggregation DSL query for getting the time series
        values for field.

        :param field: field to get the time series values
        :param time_field: field with the date
        :param interval: interval to be used to generate the time series values
        :param time_zone: time zone for the time_field
        :param start: date from for the time series
        :param end: date to for the time series
        :param agg_type: kind of aggregation for the field (cardinality, avg, percentiles)
        :param offset: offset to be added to the time_field in days
        :return: a string with the DSL query
        """
        """ Time series for an aggregation metric """
        if not interval:
            interval = '1M'
        if not time_zone:
            time_zone = 'UTC'

        if not field:
            field_agg = ''
        else:
            if agg_type == "cardinality":
                field_agg = cls.__get_query_agg_cardinality(field, agg_id=cls.AGGREGATION_ID + 1)
            elif agg_type == "avg":
                field_agg = cls.__get_query_agg_avg(field, agg_id=cls.AGGREGATION_ID + 1)
            elif agg_type == "percentiles":
                field_agg = cls.__get_query_agg_percentiles(field, agg_id=cls.AGGREGATION_ID + 1)
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
                bounds = "," + bounds  # it is the last element

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
        """
        Build the DSL query for counting the number of items.

        :param date_field: field with the date
        :param start: date from which to start counting
        :param end: date until which to count items
        :param filters: dict with the filters to be applied
        :return: a string with the DSL query
        """
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
        """
        Compute the aggregated value for a field.
        If USE_ELASTIC_DSL is True it uses the elastic_dsl library. If not, esquery (this) module is
        used to build the query.

        :param field: field to get the time series values
        :param date_field: field with the date
        :param interval: interval to be used to generate the time series values
        :param start: date from for the time series
        :param end: date to for the time series
        :param agg_type: kind of aggregation for the field (cardinality, avg, percentiles)
        :param offset: offset to be added to the time_field in days
        :return: a string with the DSL query
        """

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
            s.aggs.bucket(agg_id, ts_agg).metric(agg_id + 1, field_agg)
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
