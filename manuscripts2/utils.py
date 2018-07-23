#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Script for producing Reports from data in ElasticSearch
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
# Author:
#   Pranjal Aswani <aswani.pranjal@gmail.com>
#

from dateutil import relativedelta


def get_prev_month(end_date, interval):

    if interval not in ['month', 'quarter', 'year']:
        raise RuntimeError("Interval not supported ", interval)
    if interval == 'month':
        end_prev_month = end_date - relativedelta.relativedelta(months=1)
    elif interval == 'quarter':
        end_prev_month = end_date - relativedelta.relativedelta(months=3)
    elif interval == 'year':
        end_prev_month = end_date - relativedelta.relativedelta(months=12)

    return end_prev_month


def str_val(val):
    """
    Format the value of a metric value to a string

    :param val: number to be formatted
    :return: a string with the formatted value
    """
    str_val = val
    if val is None:
        str_val = "NA"
    elif type(val) == float:
        str_val = '%0.2f' % val
    else:
        str_val = str(val)
    return str_val
