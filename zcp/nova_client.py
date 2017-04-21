#    Copyright  2017 EasyStack, Inc
#    Authors: Claudio Marques,
#             David Palma,
#             Luis Cordeiro,
#             Branty <jun.wang@easystack.cn>
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

from novaclient import client as nova_client
from novaclient import exceptions


LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.Unauthorized, e:
            msg = "Error... \nToken refused! " \
                  "The request you have made requires authentication."
            LOG.error(msg)
            raise
        except exceptions.NotFound, e:
            LOG.error("Not Found Nova Resource")
            raise
        except Exception, ex:
            msg = getattr(ex, 'message', None) or \
                  getattr(ex, 'msg', '')
            LOG.error(msg)
            raise
    return with_logging


class Client(object):
    def __init__(self, conf):
        # novaclient only support keystone v3
        auth_url = conf.read_option('keystone_authtoken',
                                    'auth_url')
        if auth_url.endswith('/v3'):
            auth_url = auth_url.replace('/v3', '/v2.0')
        self.nv_client = nova_client.Client(2,
                                            conf.read_option(
                                                'keystone_authtoken',
                                                'username'),
                                            conf.read_option(
                                                'keystone_authtoken',
                                                'password'),
                                            conf.read_option(
                                                'keystone_authtoken',
                                                'project_name'),
                                            auth_url,
                                            region_name=conf.read_option(
                                                'keystone_authtoken',
                                                'region_name')
                                            )

    @logged
    def instance_get_all(self, since=None):
        """Returns list of all instances.

        If since is supplied, it will return the instances changes since that
        datetime. since should be in ISO Format '%Y-%m-%dT%H:%M:%SZ'
        """
        search_opts = {'all_tenants': True}
        if since:
            search_opts['changes-since'] = since
        return self.nv_client.servers.list(
            detailed=True,
            search_opts=search_opts)
