#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Classes for querying ElasticSearch and calculating the metrics
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
#   Pranjal Aswani <aswani.pranjal@gmail.com>

from dateutil import parser
from datetime import timezone
from collections import OrderedDict, defaultdict

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch_dsl import A, Q, Search


class Index():
    """
    Index class representing an elasticsearch index
    """

    def __init__(self, index_name, es=None):
        """
        :param index_name: name of the elasticsearch index that is to be queried (required)
        :param es: the client used to connect to elasticsearch (optional)
                   default connects to elasticsearch running at http://localhost:9200
        """

        self.index_name = index_name
        if not es:
            es = Elasticsearch()
        self.es = es


class Query():
    """
    Base query class used to query elasticsearch
    """

    filters = {}
    start_date = None
    end_date = None
    interval_ = "month"
    offset_ = None

    def __init__(self, index, esfilters={}, interval=None, offset=None):
        """
        :param index: An Index object containing the connection details
        :param esfilters: TODO: this is still to be implemented
        :param interval: interval to use for timeseries data
        :param offset: TODO: this is still to be implemented
        """
        self.index = index
        self.search = Search(using=self.index.es, index=self.index.index_name)

        self.parent_agg_counter = 0
        if esfilters:
            self.filters.update(esfilters)
        # an ordered aggregation dict so that the nested aggregations can be made chainable
        self.aggregations = OrderedDict()
        self.child_agg_counter_dict = defaultdict(int)  # to keep a track of nested child aggregations
        self.size = 10000  # temporary hack to get all the data
        self.precision_threshold = 3000  # accuracy that we want when counting the number of items
        if interval:
            self.interval_ = interval
        if offset:
            self.offset_ = offset

    def add_query(self, key_val={}):
        """
        Add an es_dsl query object to the es_dsl Search object

        :param key_val: a key-value pair(dict) containing the query to be added to the search object
        :returns: self, which allows the method to be chainable with the other methods
        """

        q = Q("match", **key_val)
        self.search = self.search.query(q)
        return self

    def add_inverse_query(self, key_val={}):
        """
        Add an es_dsl inverse query object to the es_dsl Search object

        :param key_val: a key-value pair(dict) containing the query to be added to the search object
        :returns: self, which allows the method to be chainable with the other methods
        """

        q = Q("match", **key_val)
        self.search = self.search.query(~q)
        return self

    def is_open(self):
        """
        Add the {'state':'open'} query to the Search object

        :returns: self, which allows the method to be chainable with the other methods
        """

        self.add_query({"state": "open"})
        return self

    def is_closed(self):
        """
        Add the {'state':'closed'} query to the Search object

        :returns: self, which allows the method to be chainable with the other methods
        """

        self.add_query({"state": "closed"})
        return self

    def get_sum(self, field=None):
        """
        Create a sum aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("sum", field=field)
        self.aggregations['sum_' + field] = agg
        return self

    def get_average(self, field=None):
        """
        Create an avg aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("avg", field=field)
        self.aggregations['avg_' + field] = agg
        return self

    def get_percentiles(self, field=None, percents=None):
        """
        Create a percentile aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :param percents: the specific percentiles to be calculated
                         default: [1.0, 5.0, 25.0, 50.0, 75.0, 95.0, 99.0]
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        if not percents:
            percents = [1.0, 5.0, 25.0, 50.0, 75.0, 95.0, 99.0]
        agg = A("percentiles", field=field, percents=percents)

        self.aggregations['percentiles_' + field] = agg
        return self

    def get_terms(self, field=None):
        """
        Create a terms aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("terms", field=field, size=self.size, order={"_count": "desc"})
        self.aggregations['terms_' + field] = agg
        return self

    def get_min(self, field=None):
        """
        Create a min aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("min", field=field)
        self.aggregations['min_' + field] = agg
        return self

    def get_max(self, field=None):
        """
        Create a max aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("max", field=field)
        self.aggregations['max_' + field] = agg
        return self

    def get_cardinality(self, field=None):
        """
        Create a cardinality aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("cardinality", field=field, precision_threshold=self.precision_threshold)
        self.aggregations['cardinality_' + field] = agg
        return self

    def get_extended_stats(self, field=None):
        """
        Create an extended_stats aggregation object and add it to the aggregation dict

        :param field: the field present in the index that is to be aggregated
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            raise AttributeError("Please provide field to apply aggregation to!")
        agg = A("extended_stats", field=field)
        self.aggregations['extended_stats_' + field] = agg
        return self

    def add_custom_aggregation(self, agg, name=None):
        """
        Takes in an es_dsl Aggregation object and adds it to the aggregation dict.
        Can be used to add custom aggregations such as moving averages

        :param agg: aggregation to be added to the es_dsl search object
        :param name: name of the aggregation object (optional)
        :returns: self, which allows the method to be chainable with the other methods
        """

        agg_name = name if name else 'custom_agg'
        self.aggregations[agg_name] = agg
        return self

    def since(self, start, field=None):
        """
        Add the start date to query data starting from that date
        sets the default start date for each query

        :param start: date to start looking at the fields (from date)
        :param field: specific field for the start date in range filter
                      for the Search object
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            field = "grimoire_creation_date"
        self.start_date = start

        date_dict = {field: {"gte": "{}".format(self.start_date.isoformat())}}
        self.search = self.search.filter("range", **date_dict)
        return self

    def until(self, end, field=None):
        """
        Add the end date to query data upto that date
        sets the default end date for each query

        :param end: date to stop looking at the fields (to date)
        :param field: specific field for the end date in range filter
                      for the Search object
        :returns: self, which allows the method to be chainable with the other methods
        """

        if not field:
            field = "grimoire_creation_date"
        self.end_date = end

        date_dict = {field: {"lte": "{}".format(self.end_date.isoformat())}}
        self.search = self.search.filter("range", **date_dict)
        return self

    def by_authors(self, field=None):
        """
        Used to seggregate the data with respect to the users. This method
        pops the latest aggregation from the self.aggregations dict and
        adds it as a nested aggregation under itself

        :param field: the field to create the parent agg (optional)
                      default: author_uuid
        :returns: self, which allows the method to be chainable with the other methods
        """

        # Parent aggregation
        agg_field = field if field else "author_uuid"
        agg_key = "terms_" + agg_field
        if agg_key in self.aggregations.keys():
            agg = self.aggregations[agg_key]
        else:
            agg = A("terms", field=agg_field, missing="others", size=self.size)

        child_agg_counter = self.child_agg_counter_dict[agg_key]  # 0 if not present because defaultdict
        child_name, child_agg = self.aggregations.popitem()

        # add child agg to parent agg
        agg.metric(child_agg_counter, child_agg)
        # insert this agg to the agg dict. This agg essentially replaces
        # the last agg that was in the agg dict
        self.aggregations[agg_key] = agg
        self.child_agg_counter_dict[agg_key] += 1
        return self

    def by_organizations(self, field=None):
        """
        Used to seggregate the data acording to organizations. This method
        pops the latest aggregation from the self.aggregations dict and
        adds it as a nested aggregation under itself

        :param field: the field to create the parent agg (optional)
                      default: author_org_name
        :returns: self, which allows the method to be chainable with the other methods
        """

        # this functions is currently only for issues and PRs
        agg_field = field if field else "author_org_name"
        agg_key = "terms_" + agg_field
        if agg_key in self.aggregations.keys():
            agg = self.aggregations[agg_key]
        else:
            agg = A("terms", field=agg_field, missing="others", size=self.size)

        child_agg_counter = self.child_agg_counter_dict[agg_key]  # 0 if not present because defaultdict
        child_name, child_agg = self.aggregations.popitem()

        agg.metric(child_agg_counter, child_agg)
        self.aggregations[agg_key] = agg
        self.child_agg_counter_dict[agg_key] += 1
        return self

    def by_period(self, field=None, period=None, timezone=None, start=None, end=None):
        """
        Create a date histogram aggregation using the last added aggregation for the
        current object. Add this date_histogram aggregation into self.aggregations

        :param field: the index field to create the histogram from
        :param period: the interval which elasticsearch supports, ex: "month", "week" and such
        :param timezone: custom timezone
        :param start: custom start date for the date histogram, default: start date under range
        :param end: custom end date for the date histogram, default: end date under range
        :returns: self, which allows the method to be chainable with the other methods
        """

        hist_period = period if period else self.interval_
        time_zone = timezone if timezone else "UTC"

        start_ = start if start else self.start_date
        end_ = end if end else self.end_date
        bounds = self.get_bounds(start_, end_)

        date_field = field if field else "grimoire_creation_date"
        agg_key = "date_histogram_" + date_field
        if agg_key in self.aggregations.keys():
            agg = self.aggregations[agg_key]
        else:
            agg = A("date_histogram", field=date_field, interval=hist_period,
                    time_zone=time_zone, min_doc_count=0, **bounds)

        child_agg_counter = self.child_agg_counter_dict[agg_key]
        child_name, child_agg = self.aggregations.popitem()

        agg.metric(child_agg_counter, child_agg)
        self.aggregations[agg_key] = agg
        self.child_agg_counter_dict[agg_key] += 1
        return self

    def get_bounds(self, start=None, end=None):
        """
        Get bounds for the date_histogram method

        :param start: start date to set the extended_bounds min field
        :param end: end date to set the extended_bounds max field
        :returns bounds: a dictionary containing the min and max fields
                         required to set the bounds in date_histogram aggregation
        """

        bounds = {}
        if start or end:
            # Extend bounds so we have data until start and end
            start_ts = None
            end_ts = None

            if start:
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

    def reset_aggregations(self):
        """
        Remove all aggregations added to the search object
        """

        temp_search = self.search.to_dict()
        if 'aggs' in temp_search.keys():
            del temp_search['aggs']
            self.search.from_dict(temp_search)
        self.parent_agg_counter = 0
        self.child_agg_counter = 0
        self.child_agg_counter_dict = defaultdict(int)

    def flush_aggregations(self):
        """
        Remove all the aggregations from the self.aggregations dict
        """

        self.aggregations = OrderedDict()

    def fetch_aggregation_results(self):
        """
        Loops though the self.aggregations dict and adds them to the Search object
        in order in which they were created. Queries elasticsearch and returns a dict
        containing the results

        :returns: a dictionary containing the response from elasticsearch
        """

        self.reset_aggregations()

        for key, val in self.aggregations.items():
            self.search.aggs.bucket(self.parent_agg_counter, val)
            self.parent_agg_counter += 1

        self.search = self.search.extra(size=0)
        response = self.search.execute()
        self.flush_aggregations()
        return response.to_dict()

    def fetch_results_from_source(self, *fields, dataframe=False):
        """
        Get values for specific fields in the elasticsearch index, from source

        :param fields: a list of fields that have to be retrieved from the index
        :param dataframe: if true, will return the data in the form of a pandas.DataFrame
        :returns: a list of dicts(key_val pairs) containing the values for the applied fields
                  if dataframe=True, will return the a dataframe containing the data in rows
                  and the fields representing column names
        """

        if not fields:
            raise AttributeError("Please provide the fields to get from elasticsearch!")

        self.reset_aggregations()

        self.search = self.search.extra(_source=fields)
        self.search = self.search.extra(size=self.size)
        response = self.search.execute()
        hits = response.to_dict()['hits']['hits']
        data = [item["_source"] for item in hits]

        if dataframe:
            df = pd.DataFrame.from_records(data)
            return df.fillna(0)
        return data

    def get_timeseries(self, child_agg_count=0, dataframe=False):
        """
        Get time series data for the specified fields and period of analysis

        :param query: a Query object with the necessary aggregations and filters
        :param child_agg_count: the child aggregation count to be used
                                default = 0
        :param dataframe: if dataframe=True, return a pandas.DataFrame object
        :returns: dictionary containing "date", "value" and "unixtime" keys
                  with lists as values containing data from each bucket in the
                  aggregation
        """

        res = self.fetch_aggregation_results()

        ts = {"date": [], "value": [], "unixtime": []}

        if 'buckets' not in res['aggregations'][str(self.parent_agg_counter - 1)]:
            raise RuntimeError("Aggregation results have no buckets in time series results.")

        for bucket in res['aggregations'][str(self.parent_agg_counter - 1)]['buckets']:
            ts['date'].append(parser.parse(bucket['key_as_string']).date())
            if str(child_agg_count) in bucket:
                # We have a subaggregation with the value
                # If it is percentiles we get the median
                if 'values' in bucket[str(child_agg_count)]:
                    val = bucket[str(child_agg_count)]['values']['50.0']
                    if val == 'NaN':
                        # ES returns NaN. Convert to None for matplotlib graph
                        val = None
                    ts['value'].append(val)
                else:
                    ts['value'].append(bucket[str(child_agg_count)]['value'])
            else:
                ts['value'].append(bucket['doc_count'])
            # unixtime comes in ms from ElasticSearch
            ts['unixtime'].append(bucket['key'] / 1000)

        if dataframe:
            df = pd.DataFrame.from_records(ts, index="date")
            return df.fillna(0)
        return ts

    def get_aggs(self):
        """
        Compute the values for single valued aggregations

        :param query: a Query object with the necessary aggregations and filters
        :returns: the single aggregation value
        """

        res = self.fetch_aggregation_results()
        if 'aggregations' in res and 'values' in res['aggregations'][str(self.parent_agg_counter - 1)]:
            try:
                agg = res['aggregations'][str(self.parent_agg_counter - 1)]['values']["50.0"]
                if agg == 'NaN':
                    # ES returns NaN. Convert to None for matplotlib graph
                    agg = None
            except Exception as e:
                raise RuntimeError("Multivalue aggregation result not supported")

        elif 'aggregations' in res and 'value' in res['aggregations'][str(self.parent_agg_counter - 1)]:
            agg = res['aggregations'][str(self.parent_agg_counter - 1)]['value']

        else:
            agg = res['hits']['total']

        return agg


class PullRequests(Query):
    def __init__(self, index_obj, esfilters={}, interval=None, offset=None):
        super().__init__(index_obj, esfilters, interval, offset)
        super().add_query({"pull_request": "true"})


class Issues(Query):

    def __init__(self, index_obj, esfilters={}, interval=None, offset=None):
        super().__init__(index_obj, esfilters, interval, offset)
        super().add_query({"pull_request": "false"})


def get_trend(timeseries):
    """
    Using the values returned by get_timeseries(), compare the current
    Metric value with it's previous period's value

    :param timeseries: data returned from the get_timeseries() method
    :returns: the last period value and relative change
    """

    last = timeseries['value'][len(timeseries['value']) - 1]
    prev = timeseries['value'][len(timeseries['value']) - 2]
    trend = last - prev
    trend_percentage = None

    if last == 0:
        if prev > 0:
            trend_percentage = -100
        else:
            trend_percentage = 0
    else:
        trend_percentage = int((trend / last) * 100)
    return (last, trend_percentage)


def calculate_bmi(closed, submitted):
    """
    BMI is the ratio of the number of closed items to the number of total items
    submitted in a particular period of analysis. The items can be issues, pull
    requests and such

    :param closed: data returned from get_timeseries() containing closed items
    :param submitted: data returned from get_timeseries() containing total items
    :returns: a dict containing "period" and "bmi" keys with values as lists
              bmi is the ratio of the number of items closed by the total
              number of items submitted in a "period" of analysis
    """

    if sorted(closed.keys()) != sorted(submitted.keys()):
        raise AttributeError("The buckets supplied are not congruent!")

    dates = closed['date']
    closed_values = closed['value']
    submitted_values = submitted['value']
    ratios = []
    for x, y in zip(closed_values, submitted_values):
        if y == 0:
            ratios.append(0)
        else:
            ratios.append(x / y)
    return {"period": dates, "bmi": ratios}


def buckets_to_df(buckets):
    """
    Takes in aggregation buckets and converts them into a pandas dataframe
    after cleaning the buckets. If a DateTime field is present(usually having the name:
    "key_as_string") parses it to datetime object and then it uses it as key

    :param buckets: elasticsearch aggregation buckets to be converted to a DataFrame obj
    :returns: a DataFrame object created by parsing the buckets
    """
    cleaned_buckets = []
    for item in buckets:
        if type(item) == str:
            return item

        temp = {}
        for key, val in item.items():
            try:
                temp[key] = val['value']
            except Exception as e:
                temp[key] = val

        cleaned_buckets.append(temp)

    if "key_as_string" in temp.keys():
        ret_df = pd.DataFrame.from_records(cleaned_buckets)
        ret_df = ret_df.rename(columns={"key": "date_in_seconds"})
        ret_df['key'] = pd.to_datetime(ret_df['key_as_string'])
        ret_df = ret_df.drop(["key_as_string", "doc_count"], axis=1)
        ret_df = ret_df.set_index("key")
    elif "key" in cleaned_buckets[0].keys():
        ret_df = pd.DataFrame.from_records(cleaned_buckets)  # index="key")
    else:
        ret_df = pd.DataFrame(cleaned_buckets)

    return ret_df.fillna(0)
