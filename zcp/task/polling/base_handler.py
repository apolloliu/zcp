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
import time

from zcp.common import conf
from zcp import exceptions

LOG = logging.getLogger(__name__)

SUPPORTED_HANDLERS = {
    'ceilometer': 'zcp.task.polling.ceilometer_handler',
    'mongodb': 'zcp.task.polling.mongodb_handler'
    }


class Handler(object):
    """Base class for polling handler.
    """

    def __init__(self, conf, zabbix_hdl):
        self.conf = conf
        self.zabbix_hdl = zabbix_hdl

    def interval_run(self, func=None):
        """
        :param func: loop execute function
        """
        LOG.info("********* Polling Ceilometer Metrics Into Zabbix **********")
        while True:
            self.run()
            time.sleep(self.polling_interval)

    def run(self):
        hosts, hosts_map = self.zabbix_hdl.get_hosts(filter_no_proxy=True)
        # Refresh zabbix hostgroups and proxies if needed
        self.zabbix_hdl.check_host_groups()
        self.zabbix_hdl.check_proxies()
        self.polling_metrics(hosts, hosts_map)

    def polling_metrics(self, instance_id, proxy_name):
        """
        :param instance_id: nova instance uuid
        :param proxy_name: zabbix proxy_name
        """
        raise exceptions.NotImplementedError


class HandlerAdapter(object):
    """
    Handler factory
    """
    @staticmethod
    def get_handler(conf, *args):
        """
        :params args: handler requiremnets params
         The following parameters must be specified in 'args' by order:
         param 1: zcp configs
         param 2: a keystone client instance
         param 3: a nova client instance
         param 4: a zabbix handler instance
        """
        cfg = conf if conf else conf.Conf()
        polling_handler = cfg.read_option('zcp_configs',
                                          'polling_handler',
                                          'mongodb')
        if polling_handler not in SUPPORTED_HANDLERS:
            LOG.error('%s not in supported handlers %s'
                      % (polling_handler, SUPPORTED_HANDLERS.keys()))
            raise exceptions.NotImplementedError
        try:
            module = __import__(SUPPORTED_HANDLERS.get(polling_handler),
                                fromlist=['zcp'])
            return module.get_handler(conf, *args)
        except ImportError or ValueError as e:
            LOG.error('Module %s not found in  Python package %s'
                      % (SUPPORTED_HANDLERS.get('polling_handler'),
                         'zcp'))
            raise
        except AttributeError or TypeError as e:
            msg = getattr(e, 'msg', '') or getattr(e, 'message', '')
            LOG.error(msg)
            raise
        except Exception as e:
            raise
