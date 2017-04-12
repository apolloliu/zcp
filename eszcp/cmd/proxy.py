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

"""
Proxy for integration of resources between OpenStack's Ceilometer and Zabbix

This proxy periodically checks for changes in Ceilometer's resources reporting
them to Zabbix. It is also integrated

OpenStack's Nova and RabbitMQ for reflecting changes in
Projects/Tenants and Instances
"""

import multiprocessing

from eszcp.common import log
from eszcp.common import conf
from eszcp.task.polling.base_handler import HandlerAdapter
from eszcp.task import nova_handler
from eszcp.task import keystone_handler
from eszcp.keystone_client import Client
from eszcp.nova_client import Client as nova_Client
from eszcp import messaging
from eszcp import zabbix_handler

log.initlog()
LOG = log.logger(__name__)
conf_file = conf.Conf()


def init_zcp(processes):
    """
        Method used to initialize the Zabbix-Ceilometer Proxy
    """

    # Creation of the Auth keystone-dedicated authentication class
    # Responsible for managing domain and project related requests
    ks_client = Client(conf_file)
    nv_client = nova_Client(conf_file)
    # Creation of the Zabbix Handler class
    # Responsible for the communication with Zabbix
    zabbix_hdl = zabbix_handler.ZabbixHandler(conf_file.read_option(
                                                    'zabbix_configs',
                                                    'zabbix_admin_user'),
                                              conf_file.read_option(
                                                    'zabbix_configs',
                                                    'zabbix_admin_pass'),
                                              conf_file.read_option(
                                                    'zabbix_configs',
                                                    'zabbix_host'),
                                              conf_file.read_option(
                                                    'zabbix_configs',
                                                    'zabbix_port'),
                                              conf_file.read_option(
                                                    'zcp_configs',
                                                    'template_name'),
                                              ks_client,
                                              nv_client)

    # Creation of the Polling Handler class
    # Responsible for the communication with OpenStack's Ceilometer or Mongo,
    # polling for changes every N seconds
    polling_hdl = HandlerAdapter.get_handler(conf_file, ks_client,
                                             nv_client, zabbix_hdl)

    # First run of the Zabbix handler for retrieving the necessary information
    zabbix_hdl.first_run()

    # Creation of the Nova Handler class
    # Responsible for detecting the creation of new instances in OpenStack,
    # translated then to Hosts in Zabbix
    nova_hdl = nova_handler.NovaEvents(zabbix_hdl, messaging.MQConnection())

    # Creation of the Project Handler class
    # Responsible for detecting the creation of new tenants in OpenStack,
    # translated then to HostGroups in Zabbix
    keystone_hdl = keystone_handler.KeystoneEvents(zabbix_hdl,
                                                   messaging.MQConnection(),
                                                   ks_client)

    # Create and append processes to process list
    LOG.INFO('**************** Keystone listener started ****************')
    p1 = multiprocessing.Process(target=keystone_hdl.keystone_amq)
    p1.daemon = True
    processes.append(p1)

    LOG.INFO('**************** Nova listener started ****************')
    p2 = multiprocessing.Process(target=nova_hdl.nova_amq)
    p2.daemon = True
    processes.append(p2)

    p3 = multiprocessing.Process(target=polling_hdl.interval_run)
    p3.daemon = True
    processes.append(p3)

    # start all the processes
    [ps.start() for ps in processes]


def main():
    processes = []
    LOG.info("-------------- Starting Zabbix Ceilometer Proxy --------------")
    init_zcp(processes)
    # wait for all processes to complete
    [ps.join() for ps in processes]
    LOG.info("************* Runnig Zabbix Ceilometer Proxy  ****************")
    print "ZCP terminated"
    LOG.info('************* Terninate Zabbix Ceilometer Proxy ***************')
