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
import logging
import functools

from ceilometerclient.v2 import client as clm_clientv20

from zcp.common import conf

CONF = conf.Conf()
LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, ex:
            msg = getattr(ex, 'message', None) or \
                  getattr(ex, 'msg', '')
            LOG.error(msg)
            raise
    return with_logging


class Client(object):
    def __init__(self):
        v3_kwargs = {
                "username": CONF.read_option('keystone_authtoken',
                                             'username'),
                "password": CONF.read_option('keystone_authtoken',
                                             'password'),
                "project_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'project_name'),
                "user_domain_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'user_domain_name'),
                "project_domain_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'project_domain_name'),
                "auth_url": CONF.read_option('keystone_authtoken',
                                             'auth_url'),
                "region_name": CONF.read_option(
                                             'keystone_authtoken',
                                             'region_name'),
        }
        self.clm_client = clm_clientv20.Client('', **v3_kwargs)

    @logged
    def list_resources(self, q=None, links=None, limit=None):
        if not isinstance(q, list):
            # TO DO
            # add something warning
            raise
        return self.clm_client.resources.list(q=q,
                                              links=links,
                                              limit=limit)

    @logged
    def statistics(self, meter_name, q=None, limit=None):
        if not isinstance(q, list):
            LOG.error("Invalid query param q: %s,q must be a list" % q)
            raise
        return self.clm_client.statistics.list(meter_name,
                                               q=q,
                                               limit=limit
                                               )
