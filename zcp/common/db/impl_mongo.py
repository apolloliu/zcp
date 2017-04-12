#    Copyright  2017 EasyStack, Inc
#    Authors: Branty <jun.wang@easystack.cn>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import datetime
import os
import pymongo
import six
import time

from eszcp import exceptions
from eszcp.common import conf
from eszcp.common import log
from eszcp.common.db import models
from eszcp.common.db import pymongo_utils
from eszcp import utils

LOG = log.logger(__name__)
CONF = conf.Conf()

MAX_RETRIES = CONF.read_option('mongodb', 'max_retries', 3)
RETRY_INTERVAL = CONF.read_option('mongodb', 'retry_interval', 2)
MONGO_URL = CONF.read_option('mongodb', 'connection')
MAPPING_FILE = CONF.read_option('mongodb', 'mapping_file',
                                '/etc/ceilometer/mapping.json')
CACHE_MAPPING_FILE = {}


def parse_metric_json():
    global CACHE_MAPPING_FILE
    mapping_file = MAPPING_FILE
    if not os.path.isabs(mapping_file):
        CACHE_MAPPING_FILE = '/etc/ceilometer/%s' % mapping_file
    elif os.path.exists(mapping_file):
        CACHE_MAPPING_FILE = utils.mapping_json_to_dict(mapping_file)
    if not CACHE_MAPPING_FILE:
        LOG.error("Can't find Metric mapping.json file, "
                  "Make sure the mapping_file exist "
                  "under section [collector] "
                  "which must be configured properly.")
        raise exceptions.MappingFileNotFound
    return CACHE_MAPPING_FILE


def safe_mongo_call(call):
    def closure(*args, **kwargs):
        max_retries = MAX_RETRIES
        retry_interval = RETRY_INTERVAL
        attempts = 0
        while True:
            try:
                return call(*args, **kwargs)
            except pymongo.errors.AutoReconnect as err:
                if 0 <= max_retries <= attempts:
                    LOG.error('Unable to reconnect to the primary mongodb '
                              'after %(retries)d retries. Giving up.' %
                              {'retries': max_retries})
                    raise
                LOG.warning('Unable to reconnect to the primary mongodb: '
                            '%(errmsg)s. Trying again in %(retry_interval)d '
                            'seconds.' %
                            {'errmsg': err, 'retry_interval': retry_interval})
                attempts += 1
                time.sleep(retry_interval)
    return closure


@utils.Singleton
class Connection(object):
    """MongoDB connection.
    """
    SORT_OPERATION_MAPPING = {'desc': pymongo.DESCENDING,
                              'asc': pymongo.ASCENDING}
    _GENESIS = datetime.datetime(year=datetime.MINYEAR, month=1, day=1)
    _APOCALYPSE = datetime.datetime(year=datetime.MAXYEAR, month=12, day=31,
                                    hour=23, minute=59, second=59)
    SAMPLE_T = 60

    def __init__(self):
        url = MONGO_URL
        max_retries = MAX_RETRIES
        retry_interval = RETRY_INTERVAL
        attempts = 0
        while True:
            try:
                self.client = pymongo.MongoClient(url)
                LOG.debug('mongo client: %s' % self.client)
                parse_metric_json()
            except pymongo.errors.ConnectionFailure as e:
                if max_retries >= 0 and attempts >= max_retries:
                    LOG.error('Unable to connect to the database after '
                              '%(retries)d retries. Giving up.' %
                              {'retries': max_retries})
                    raise
                LOG.warning('Unable to connect to the database server: '
                            '%(errmsg)s. Trying again in %(retry_interval)d '
                            'seconds.' %
                            {'errmsg': e, 'retry_interval': retry_interval})
                attempts += 1
                time.sleep(retry_interval)
            except Exception as e:
                LOG.warning('Unable to connect to the database server: '
                            '%(errmsg)s.' % {'errmsg': e})
                raise
            else:
                connection_options = pymongo.uri_parser.parse_uri(url)
                self.db = getattr(self.client, connection_options['database'])
                self.db.authenticate(connection_options['username'],
                                     connection_options['password'])
                break

    def get_resources(self, start_timestamp=None, start_timestamp_op=None,
                      end_timestamp=None, end_timestamp_op=None,
                      metaquery=None, resource=None, limit=None):
        """Return an iterable of models.Resource instances
        :param start_timestamp: Optional modified timestamp start range.
        :param start_timestamp_op: Optional start time operator, like gt, ge.
        :param end_timestamp: Optional modified timestamp end range.
        :param end_timestamp_op: Optional end time operator, like lt, le.
        :param metaquery: Optional dict with metadata to match on.
        :param resource: Optional resource filter.
        :param limit: Maximum number of results to return.
        """
        metaquery = pymongo_utils.improve_keys(metaquery, metaquery=True) or {}
        if start_timestamp or end_timestamp:
            # TO DO
            # ceilometet.storage.impl_mongo.ConnectionOrig._get_time_constrained_resources
            return []
        else:
            query = {}
            sort_instructions = []
            if resource is not None:
                query['_id'] = resource
            query.update(dict((k, v)
                         for (k, v) in six.iteritems(metaquery)))
            sort_key = 'last_sample_timestamp'
            sort_instructions.append((sort_key,
                                     self.SORT_OPERATION_MAPPING['desc']))
            if limit:
                results = self.db.resource.find(query, sort=sort_instructions,
                                                limit=limit)
            else:
                results = self.db.resource.find(query, sort=sort_instructions)

            return [models.Resource(
                        resource_id=r['_id'],
                        user_id=r['user_id'],
                        project_id=r['project_id'],
                        first_sample_timestamp=r.get('first_sample_timestamp',
                                                     self._GENESIS),
                        last_sample_timestamp=r.get('last_sample_timestamp',
                                                    self._APOCALYPSE),
                        source=r['source'],
                        metadata=pymongo_utils.unquote_keys(r['metadata']),
                        resource_name=pymongo_utils.unquote_keys(
                                   r['resource_name'])) for r in results]

    def get_meter_statistics(self, sample_filter, period=None, groupby=None,
                             aggregate=None, limit=None):
        """Return an iterable of models.Statistics instance containing meter
        statistics described by the query parameters.

        The filter must have a meter value set.

        """
        if groupby or aggregate:
            # TO DO
            # ceilometet.storage.impl_mongo.Connection.get_meter_statistics
            return []
        period = []
        aggregate = []
        if (groupby and
                set(groupby) - set(['user_id', 'project_id',
                                    'resource_id', 'source'])):
            raise NotImplementedError("Unable to group by these fields")
        q = pymongo_utils.make_query_from_filter(sample_filter)
        if period:
            T = period
        else:
            # Set the smallest base_period as default sample period
            # T = self.SAMPLE_T
            T = utils.get_metric_BASE_T(CACHE_MAPPING_FILE,
                                        sample_filter.get('meter')) \
                                        or self.SAMPLE_T
        coll = 'statistics%s' % T
        LOG.debug("get_statistics2 q = %s" % q)
        if limit:
            results = self.db[coll].find(q,
                                         sort=[('period_start', -1)],
                                         limit=limit)
        else:
            results = self.db[coll].find(q, sort=[('period_start', 1)])

        stats = [self._stats_result_to_model(r, groupby, aggregate)
                 for r in results]
        return stats

    def _stats_result_aggregates(self, result, aggregate):
        stats_args = {}
        for attr in ['count', 'min', 'max', 'sum', 'avg']:
            if attr in result:
                stats_args[attr] = result[attr]

        if aggregate:
            stats_args['aggregate'] = {}
            for a in aggregate:
                ak = '%s%s' % (a.func, '/%s' % a.param if a.param else '')
                if ak in result:
                    stats_args['aggregate'][ak] = result[ak]
                elif 'aggregate' in result:
                    stats_args['aggregate'][ak] = result['aggregate'].get(ak)
        return stats_args

    def _stats_result_to_model(self, result, groupby, aggregate,
                               period=None, first_timestamp=None):

        stats_args = self._stats_result_aggregates(result, aggregate)
        stats_args['unit'] = result['unit']
        stats_args['duration'] = result['T'] if 'T' in result \
            else result['duration']
        stats_args['duration_start'] = result['period_start']
        stats_args['duration_end'] = result['period_end']
        stats_args['period'] = result['T'] if 'T' in result \
            else result['period']
        stats_args['period_start'] = result['period_start']
        stats_args['period_end'] = result['period_end']
        stats_args['groupby'] = (dict(
            (g, result['groupby'][g]) for g in groupby) if groupby else None)
        return models.Statistics(**stats_args)
