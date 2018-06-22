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

from datetime import timezone

from elasticsearch import Elasticsearch
from elasticsearch_dsl import A, Search, Q
# elasticsearch_dsl is referred to as es_dsl in the comments, henceforth


class ElasticQuery():
    """ Helper class for building Elastic queries """

    AGGREGATION_ID = 1  # min aggregation identifier
    AGG_SIZE = 100  # Default max number of buckets
    ES_PRECISION = 3000  # This is the default value for percision_threshold

    @classmethod
    def __get_query_filters(cls, filters={}, inverse=False):
        """
        Convert a dict with the filters to be applied ({"name1":"value1", "name2":"value2"})
        to a list of query objects which can be used together in a query using boolean
        combination logic.

        :param filters: dict with the filters to be applied
        :param inverse: if True include all the inverse filters (the one starting with *)
        :return: a list of es_dsl 'MatchPhrase' Query objects
                 Ex: [MatchPhrase(name1="value1"), MatchPhrase(name2="value2"), ..]
                 Dict representation of the object: {'match_phrase': {'field': 'home'}}
        """
        query_filters = []

        for name in filters:
            if name[0] == '*' and not inverse:
                # An inverse filter and not inverse mode
                continue
            if name[0] != '*' and inverse:
                # A direct filter and inverse mode
                continue
            field_name = name[1:] if name[0] == '*' else name

            params = {field_name: filters[name]}
            # trying to use es_dsl only and not creating hard coded queries
            query_filters.append(Q('match_phrase', **params))

        return query_filters

    @classmethod
    def __get_query_range(cls, date_field, start=None, end=None):
        """
        Create a filter dict with date_field from start to end dates.

        :param date_field: field with the date value
        :param start: date with the from value. Should be a datetime.datetime object
                      of the form: datetime.datetime(2018, 5, 25, 15, 17, 39)
        :param end: date with the to value. Should be a datetime.datetime object
                      of the form: datetime.datetime(2018, 5, 25, 15, 17, 39)
        :return: a dict containing a range filter which can be used later in an
                 es_dsl Search object using the `filter` method.
        """
        if not start and not end:
            return ''

        start_end = {}
        if start:
            start_end["gte"] = "%s" % start.isoformat()
        if end:
            start_end["lte"] = "%s" % end.isoformat()

        query_range = {date_field: start_end}
        return query_range

    @classmethod
    def __get_query_basic(cls, date_field=None, start=None, end=None,
                          filters={}):
        """
        Create a es_dsl query object with the date range and filters.

        :param date_field: field with the date value
        :param start: date with the from value, should be a datetime.datetime object
        :param end: date with the to value, should be a datetime.datetime object
        :param filters: dict with the filters to be applied
        :return: a DSL query containing the required parameters
                 Ex: {'query': {'bool': {'filter': [{'range': {'DATE_FIELD':
                                                        {'gte': '2015-05-19T00:00:00',
                                                         'lte': '2018-05-18T00:00:00'}}}],
                    'must': [{'match_phrase': {'first_name': 'Jhon'}},
                             {'match_phrase': {'last_name': 'Doe'}},
                             {'match_phrase': {'Phone': 2222222}}
                             ]}}}
        """
        query_basic = Search()

        query_filters = cls.__get_query_filters(filters)
        for f in query_filters:
            query_basic = query_basic.query(f)

        query_filters_inverse = cls.__get_query_filters(filters, inverse=True)
        # Here, don't forget the '~'. That is what makes this an inverse filter.
        for f in query_filters_inverse:
            query_basic = query_basic.query(~f)

        if not date_field:
            query_range = {}
        else:
            query_range = cls.__get_query_range(date_field, start, end)

        # Applying the range filter
        query_basic = query_basic.filter('range', **query_range)

        return query_basic

    @classmethod
    def __get_query_agg_terms(cls, field, agg_id=None):
        """
        Create a es_dsl aggregation object based on a term.

        :param field: field to be used to aggregate
        :return: a tuple with the aggregation id and es_dsl aggregation object. Ex:
                {
                    "terms": {
                        "field": <field>,
                        "size:": <size>,
                        "order":{
                            "_count":"desc"
                    }
                }
        Which will then be used as Search.aggs.bucket(agg_id, query_agg) method
        to add aggregations to the es_dsl Search object
        """
        if not agg_id:
            agg_id = cls.AGGREGATION_ID
        query_agg = A("terms", field=field, size=cls.AGG_SIZE, order={"_count": "desc"})
        return (agg_id, query_agg)

    @classmethod
    def __get_query_agg_max(cls, field, agg_id=None):
        """
        Create an es_dsl aggregation object for getting the max value of a field.

        :param field: field from which the get the max value
        :return: a tuple with the aggregation id and es_dsl aggregation object. Ex:
                {
                    "max": {
                        "field": <field>
                }
        """
        if not agg_id:
            agg_id = cls.AGGREGATION_ID
        query_agg = A("max", field=field)
        return (agg_id, query_agg)

    @classmethod
    def __get_query_agg_percentiles(cls, field, agg_id=None):
        """
        Create an es_dsl aggregation object for getting the percentiles value of a field.
        In general this is used to get the median (0.5) percentile.

        :param field: field from which the get the percentiles values
        :return: a tuple with the aggregation id and es_dsl aggregation object. Ex:
                {
                    "percentile": {
                        "field": <field>
                }
        """
        if not agg_id:
            agg_id = cls.AGGREGATION_ID
        query_agg = A("percentiles", field=field)
        return (agg_id, query_agg)

    @classmethod
    def __get_query_agg_avg(cls, field, agg_id=None):
        """
        Create an es_dsl aggregation object for getting the average value of a field.

        :param field: field from which the get the average value
        :return: a tuple with the aggregation id and es_dsl aggregation object. Ex:
                {
                    "avg": {
                        "field": <field>
                }
        """
        if not agg_id:
            agg_id = cls.AGGREGATION_ID
        query_agg = A("avg", field=field)
        return (agg_id, query_agg)

    @classmethod
    def __get_query_agg_cardinality(cls, field, agg_id=None):
        """
        Create an es_dsl aggregation object for getting the approximate count of distinct values of a field.

        :param field: field from which the get count of distinct values
        :return: a tuple with the aggregation id and es_dsl aggregation object. Ex:
                {
                    "cardinality": {
                        "field": <field>,
                        "precision_threshold": 3000
                }
        """
        if not agg_id:
            agg_id = cls.AGGREGATION_ID
        query_agg = A("cardinality", field=field, precision_threshold=cls.ES_PRECISION)
        return (agg_id, query_agg)

    @classmethod
    def __get_bounds(cls, start=None, end=None):
        """
        Return a dict with the bounds for a date_histogram agg.

        :param start: date from for the date_histogram agg, should be a datetime.datetime object
        :param end: date to for the date_histogram agg, should be a datetime.datetime object
        :return: a dict with the DSL bounds for a date_histogram aggregation
        """
        bounds = {}
        if start or end:
            # Extend bounds so we have data until start and end
            start_ts = None
            end_ts = None
            if start:
                # elasticsearch is unable to convert date with microseconds into long
                # format for processing, hence we convert microseconds to zero
                start = start.replace(microsecond=0)
                start_ts = start.replace(tzinfo=timezone.utc).timestamp()
                start_ts_ms = start_ts * 1000  # ES uses ms
            if end:
                end = end.replace(microsecond=0)
                end_ts = end.replace(tzinfo=timezone.utc).timestamp()
                end_ts_ms = end_ts * 1000  # ES uses ms

            bounds_data = {}
            if start:
                bounds_data["min"] = start_ts_ms
            if end:
                bounds_data["max"] = end_ts_ms

            bounds["extended_bounds"] = bounds_data
        return bounds

    @classmethod
    def __get_query_agg_ts(cls, field, time_field, interval=None,
                           time_zone=None, start=None, end=None,
                           agg_type='count', offset=None):
        """
        Create an es_dsl aggregation object for getting the time series values for a field.

        :param field: field to get the time series values
        :param time_field: field with the date
        :param interval: interval to be used to generate the time series values, such as:(year(y),
                         quarter(q), month(M), week(w), day(d), hour(h), minute(m), second(s))
        :param time_zone: time zone for the time_field
        :param start: date from for the time series, should be a datetime.datetime object
        :param end: date to for the time series, should be a datetime.datetime object
        :param agg_type: kind of aggregation for the field (cardinality, avg, percentiles)
        :param offset: offset to be added to the time_field in days
        :return: a aggregation object to calculate timeseries values of a field
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
                agg_id, field_agg = cls.__get_query_agg_cardinality(field, agg_id=cls.AGGREGATION_ID + 1)
            elif agg_type == "avg":
                agg_id, field_agg = cls.__get_query_agg_avg(field, agg_id=cls.AGGREGATION_ID + 1)
            elif agg_type == "percentiles":
                agg_id, field_agg = cls.__get_query_agg_percentiles(field, agg_id=cls.AGGREGATION_ID + 1)
            else:
                raise RuntimeError("Aggregation of %s in ts not supported" % agg_type)

        bounds = {}
        if start or end:
            if not offset:
                # With offset and quarter interval bogus buckets are added
                # to the start and to the end if extended_bounds is used
                # https://github.com/elastic/elasticsearch/issues/23776
                bounds = cls.__get_bounds(start, end)
            else:
                bounds = {'offset': offset}

        query_agg = A("date_histogram", field=time_field, interval=interval,
                      time_zone=time_zone, min_doc_count=0, **bounds)

        agg_dict = field_agg.to_dict()[field_agg.name]
        query_agg.bucket(agg_id, field_agg.name, **agg_dict)

        return (cls.AGGREGATION_ID, query_agg)

    @classmethod
    def get_count(cls, date_field=None, start=None, end=None, filters={}):
        """
        Build the DSL query for counting the number of items.

        :param date_field: field with the date
        :param start: date from which to start counting, should be a datetime.datetime object
        :param end: date until which to count items, should be a datetime.datetime object
        :param filters: dict with the filters to be applied
        :return: a DSL query with size parameter
        """
        """ Total number of items """
        query_basic = cls.__get_query_basic(date_field=date_field,
                                            start=start, end=end,
                                            filters=filters)
        # size=0 gives only the count and not the hits
        query = query_basic.extra(size=0)
        return query

    @classmethod
    def get_agg(cls, field=None, date_field=None, start=None, end=None,
                filters={}, agg_type="terms", offset=None, interval=None):
        """
        Compute the aggregated value for a field.
        :param field: field to get the time series values
        :param date_field: field with the date
        :param interval: interval to be used to generate the time series values, such as:(year(y),
                         quarter(q), month(M), week(w), day(d), hour(h), minute(m), second(s))
        :param start: date from for the time series, should be a datetime.datetime object
        :param end: date to for the time series, should be a datetime.datetime object
        :param agg_type: kind of aggregation for the field (cardinality, avg, percentiles)
        :param offset: offset to be added to the time_field in days
        :return: a query containing the aggregation, filters and range for the specified term
        """
        # This gives us the basic structure of the query, including:
        # Normal and inverse filters and range.
        s = cls.__get_query_basic(date_field=date_field, start=start, end=end, filters=filters)

        # Get only the aggs not the hits
        # Default count starts from 0
        s = s.extra(size=0)

        if agg_type == "count":
            agg_type = 'cardinality'
        elif agg_type == "median":
            agg_type = 'percentiles'
        elif agg_type == "average":
            agg_type = 'avg'

        if not interval:
            if agg_type == "terms":
                agg_id, query_agg = ElasticQuery.__get_query_agg_terms(field)
            elif agg_type == "max":
                agg_id, query_agg = ElasticQuery.__get_query_agg_max(field)
            elif agg_type == "cardinality":
                agg_id, query_agg = ElasticQuery.__get_query_agg_cardinality(field)
            elif agg_type == "percentiles":
                agg_id, query_agg = ElasticQuery.__get_query_agg_percentiles(field)
            elif agg_type == "avg":
                agg_id, query_agg = ElasticQuery.__get_query_agg_avg(field)
            else:
                raise RuntimeError("Aggregation of %s not supported" % agg_type)
        else:
            agg_id, query_agg = ElasticQuery.__get_query_agg_ts(field, date_field,
                                                                start=start, end=end,
                                                                interval=interval,
                                                                agg_type=agg_type,
                                                                offset=offset)
        s.aggs.bucket(agg_id, query_agg)

        return s.to_dict()


def get_first_date_of_index(elastic_url, index):
    """Get the first/min date present in the index"""
    es = Elasticsearch(elastic_url)
    search = Search(using=es, index=index)
    agg = A("min", field="grimoire_creation_date")
    search.aggs.bucket("1", agg)
    search = search.extra(size=0)
    response = search.execute()
    start_date = response.to_dict()['aggregations']['1']['value_as_string'][:10]
    return start_date
