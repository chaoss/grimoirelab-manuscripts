#!/usr/bin/python3
## Copyright (C) 2016 Bitergia
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## This file is a part of GrimoireLib
##  (an Python library for the MetricsGrimoire and vizGrimoire systems)
##
##
## Authors:
##   Daniel Izquierdo-Cortazar <dizquierdo@bitergia.com>
##   Alvaro del Castillo <acs@bitergia.com>

import logging

import pytz

import requests

from datetime import datetime, timedelta

from ..esquery import ElasticQuery


logger = logging.getLogger(__name__)


class Metrics(object):
    """Root of hierarchy of Entities (Metrics)

    This is the root hierarchy of the of the metric classes
    defined for each of the data sources.

    When instantiated Metrics, we can obtain specific representations
    of such entity. Timeseries of datasets (get_ts method), aggregated
    data (get_agg method) or lists of elements (get_list method).

    """

    id = None
    name = None
    desc = None
    AGG_TYPE = 'count'  # agg type for the metric
    FIELD_NAME = None  # Field used for metric lists
    FIELD_COUNT = None  # Field used for metric count
    FIELD_DATE = 'grimoire_creation_date'
    DEFAULT_INTERVAL = '1M'
    filters = None  # fixed filters for the metric
    filters_core = None  # Core filters to be used in all metrics
    interval = '1M'  # interval to be used in all metrics
    offset = None  # offset to be used in date histogram in all metrics

    def __init__(self, es_url, es_index, start=None, end=None, esfilters={},
                 interval=None, offset=None):
        """es connection and filter to be used"""
        self.es_url = es_url
        self.es_index = es_index
        self.start = start
        self.end = end
        self.esfilters = esfilters if esfilters else {}
        if self.filters:
            # If there are metric class filters use them also
            self.esfilters.update(self.filters)
        if self.filters_core:
            # If there are core filters for all metrics use them also
            self.esfilters.update(self.filters_core)
        if interval:
            self.interval = interval
        if offset:
            self.offset = offset

    def get_definition(self):
        def_ = {
               "id":self.id,
               "name":self.name,
               "desc":self.desc
        }
        return def_

    def get_query(self, evolutionary=False):
        """
        Private method that returns a valid ElasticSearch query for
        computing the metric.

        :evolutionary: boolean
            If True, an evolutionary analysis is provided
            If False, an aggregated analysis is provided
        """

        if not evolutionary:
            interval = None
            offset = None
        else:
            interval = self.interval
            offset = self.offset
            if not interval:
                raise RuntimeError("Evolutionary query without an interval.")

        query = ElasticQuery.get_agg(field=self.FIELD_COUNT,
                                     date_field=self.FIELD_DATE,
                                     start=self.start, end=self.end,
                                     filters=self.esfilters,
                                     agg_type=self.AGG_TYPE,
                                     interval=interval,
                                     offset=offset)

        logger.debug("Metric: '%s' (%s); Query: %s",
                     self.name, self.id, query)
        return query


    def get_list(self):
        field = self.FIELD_NAME
        query = ElasticQuery.get_agg(field=field,
                                     date_field=self.FIELD_DATE,
                                     start=self.start, end=self.end,
                                     filters=self.esfilters)
        logger.debug("Metric: '%s' (%s); Query: %s",
                     self.name, self.id, query)
        res = self.get_metrics_data(query)
        l = {field:[],"value":[]}
        for bucket in res['aggregations'][str(ElasticQuery.AGGREGATION_ID)]['buckets']:
            l[field].append(bucket['key'])
            l['value'].append(bucket['doc_count'])
        return l

    def get_metrics_data(self, query):
        """ Get the metrics data from ES """
        url = self.es_url+'/' + self.es_index + '/_search'
        r = requests.post(url, query)
        r.raise_for_status()
        return r.json()

    def get_ts(self):
        """Returns a time series of a specific class

        A timeseries consists of a unixtime date, labels, some other
        fields and the data of the specific instantiated class per
        interval. This is built on a hash table.

        """
        query = self.get_query(True)
        res = self.get_metrics_data(query)
        # Time to convert it to our grimoire timeseries format
        ts = {"date":[],"value":[],"unixtime":[]}
        agg_id = ElasticQuery.AGGREGATION_ID
        if 'buckets' not in res['aggregations'][str(agg_id)]:
            raise RuntimeError("Aggregation results have no buckets in time series results.")
        for bucket in res['aggregations'][str(agg_id)]['buckets']:
            ts['date'].append(bucket['key_as_string'])
            if str(agg_id+1) in bucket:
                # We have a subaggregation with the value
                # If it is percentiles we get the median
                if 'values' in bucket[str(agg_id+1)]:
                    val = bucket[str(agg_id+1)]['values']['50.0']
                    if val == 'NaN':
                        # ES returns NaN. Convert to None for matplotlib graph
                        val = None
                    ts['value'].append(val)
                else:
                    ts['value'].append(bucket[str(agg_id+1)]['value'])
            else:
                ts['value'].append(bucket['doc_count'])
            # unixtime comes in ms from ElasticSearch
            ts['unixtime'].append(bucket['key']/1000)
        return ts

    def get_agg(self):
        """ Returns an aggregated value """
        query = self.get_query(False)
        res = self.get_metrics_data(query)
        # We need to extract the data from the JSON res
        # If we have agg data use it
        agg_id = str(ElasticQuery.AGGREGATION_ID)
        if 'aggregations' in res and 'values' in res['aggregations'][agg_id]:
            if self.AGG_TYPE=='median':
                agg = res['aggregations'][agg_id]['values']["50.0"]
                if agg == 'NaN':
                    # ES returns NaN. Convert to None for matplotlib graph
                    agg = None
            else:
                raise RuntimeError("Multivalue aggregation result not supported")
        elif 'aggregations' in res and 'value' in res['aggregations'][agg_id]:
            agg = res['aggregations'][agg_id]['value']
        else:
            agg = res['hits']['total']

        return agg


    def get_trend(self):
        """ Get the trends for the interval defined in the metric """

        # TODO: We just need the last two periods, not the full ts
        ts = self.get_ts()
        last = ts['value'][len(ts['value'])-1]
        prev = ts['value'][len(ts['value'])-2]

        trend = last - prev
        trend_percentage = None
        if last == 0:
            if prev > 0:
                trend_percentage = -100
            else:
                trend_percentage = 0
        else:
            trend_percentage = int((trend/last)*100)

        return (last, trend_percentage)
