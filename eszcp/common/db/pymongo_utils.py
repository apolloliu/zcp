#    Copyright  2017 EasyStack, Inc
#    Author : Branty(jun.wang@easystack.cn)
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Pymongo Utilities and helper functions."""

import six
from six.moves.urllib import parse


def quote_key(key, reverse=False):
    """Prepare key for storage data in MongoDB.

    :param key: key that should be quoted
    :param reverse: boolean, True --- if we need a reverse order of the keys
                    parts
    :return: iter of quoted part of the key
    """
    r = -1 if reverse else 1

    for k in key.split('.')[::r]:
        if k.startswith('$'):
            k = parse.quote(k)
        yield k


def improve_keys(data, metaquery=False):
    """Improves keys in dict if they contained '.' or started with '$'.

    :param data: is a dictionary where keys need to be checked and improved
    :param metaquery: boolean, if True dots are not escaped from the keys
    :return: improved dictionary if keys contained dots or started with '$':
            {'a.b': 'v'} -> {'a': {'b': 'v'}}
            {'$ab': 'v'} -> {'%24ab': 'v'}
    """
    if not isinstance(data, dict):
        return data

    if metaquery:
        for key in six.iterkeys(data):
            if '.$' in key:
                key_list = []
                for k in quote_key(key):
                    key_list.append(k)
                new_key = '.'.join(key_list)
                data[new_key] = data.pop(key)
    else:
        for key, value in data.items():
            if isinstance(value, dict):
                improve_keys(value)
            if '.' in key:
                new_dict = {}
                for k in quote_key(key, reverse=True):
                    new = {}
                    new[k] = new_dict if new_dict else data.pop(key)
                    new_dict = new
                data.update(new_dict)
            else:
                if key.startswith('$'):
                    new_key = parse.quote(key)
                    data[new_key] = data.pop(key)
    return data


def unquote_keys(data):
    """Restores initial view of 'quoted' keys in dictionary data

    :param data: is a dictionary
    :return: data with restored keys if they were 'quoted'.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                unquote_keys(value)
            if key.startswith('%24'):
                k = parse.unquote(key)
                data[k] = data.pop(key)
    return data


def make_timestamp_range(start, end,
                         start_timestamp_op=None, end_timestamp_op=None):

    """Create the query document to find timestamps within that range.

    This is done by given two possible datetimes and their operations.
    By default, using $gte for the lower bound and $lt for the upper bound.
    """
    ts_range = {}

    if start:
        if start_timestamp_op == 'gt':
            start_timestamp_op = '$gt'
        else:
            start_timestamp_op = '$gte'
        ts_range[start_timestamp_op] = start

    if end:
        if end_timestamp_op == 'le':
            end_timestamp_op = '$lte'
        else:
            end_timestamp_op = '$lt'
        ts_range[end_timestamp_op] = end
    return ts_range


def make_query_from_filter(sample_filter, require_meter=True):
    """Return a query dictionary based on the settings in the filter.

    :param sample_filter: SampleFilter instance
    :param require_meter: If true and the filter does not have a meter,
                          raise an error.
    """
    q = {}

    """If the length of query counter is more than 1
    then return like '$in': ['counter1', 'counter1']
    """
    if sample_filter.get('meter'):
        counter_names = sample_filter.get('meter').split(',')
        if len(counter_names) > 1:
            q_counter_name = {}
            q_counter_name['$in'] = counter_names
            q['counter_name'] = sample_filter.get('meter')
        else:
            q['counter_name'] = sample_filter.get('meter')
    elif require_meter:
        raise RuntimeError('Missing required meter specifier')

    ts_range = make_timestamp_range(sample_filter.get('start_timestamp'),
                                    sample_filter.get('end_timestamp'),
                                    sample_filter.get('start_timestamp_op'),
                                    sample_filter.get('end_timestamp_op'))

    if ts_range:
        q['timestamp'] = ts_range

    if sample_filter.get('resource'):
        q['resource_id'] = sample_filter.get('resource')
