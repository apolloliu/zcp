#    Copyright  2017 EasyStack, Inc
#    Authors: Claudio Marques,
#             David Palma,
#             Luis Cordeiro,
#             Branty <jun.wang@easystack.cn>
#             Hanxi Liu<apolloliuhx@gmail.com>
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
Class for Handling KeystoneEvents in OpenStack's RabbitMQ

Uses the pika library for handling the AMQP protocol,

implementing the necessary callbacks for Keystone events
"""

import json

from eszcp.common import log


LOG = log.logger(__name__)


class KeystoneEvents:

    def __init__(self, zabbix_handler, connection, ks_client):
        """
        :param zabbix_handler: zabbix api handler
        :param connection: rabbitmq connection instance
        :param ks_client: keystone client
        """
        self.zabbix_handler = zabbix_handler
        self.ks_client = ks_client
        self.mqconnc = connection

    def keystone_amq(self):
        """
        Method used to listen to keystone events
        """
        try:
            LOG.info("Start consuming keystone messages from rabbitmq ...")
            channel = self.mqconnc.connection.channel()
            channel.exchange_declare(exchange='keystone', type='topic')
            channel.queue_declare(queue="zcp-keystone", exclusive=True)
            channel.queue_bind(exchange='keystone',
                               queue="zcp-keystone",
                               routing_key='notifications.#')
            channel.basic_consume(self.keystone_callback,
                                  queue="zcp-keystone",
                                  no_ack=True)
            channel.start_consuming()
        except Exception as e:
            LOG.error("Fail to consume messages from keystone: %s" % e)
            # Make sure consume messages normally
            self.mqconnc()

    def _handler_events(self, payload):
        if payload['event_type'] == 'identity.project.created':
            tenant_id = payload['payload']['resource_info']
            project = self.ks_client.get_project(tenant_id)
            LOG.info("Creating a hostgroup: %s(%s) in Zabbix Server"
                     % (tenant_id, project.name))
            self.zabbix_handler.create_host_group(project.name)
            self.zabbix_handler.group_list.append([project.name,
                                                   tenant_id,
                                                   project.domain_id])

        elif payload['event_type'] == 'identity.project.deleted':
            tenant_id = payload['payload']['resource_info']
            LOG.info("Deleting a hostgroup: %s in Zabbix Server"
                     % tenant_id)
            self.zabbix_handler.project_delete(tenant_id)
        elif payload['event_type'] == 'identity.domain.created':
            domain_id = payload['payload']['resource_info']
            domain_ref = self.ks_client.show_domain(domain_id)
            domain_name = domain_ref['name'] if isinstance(
                          domain_ref, dict) else domain_ref.name
            LOG.info("Creating a zabbix proxy: %s(%s) in Zabbix Server"
                     % (domain_name, domain_id))
            self.zabbix_handler.create_proxy(domain_name, domain_id)
        elif payload['event_type'] == 'identity.domain.deleted':
            domain_id = payload['payload']['resource_info']
            LOG.info("Deleting a zabbix proxy: %s in Zabbix Server"
                     % domain_id)
            self.zabbix_handler.delete_proxy(domain_id)
        else:
            # TO DO
            # Maybe more event types will be supported
            pass

    def keystone_callback(self, ch, method, properties, body):
        """
        Method used by method keystone_amq() to filter messages
        by type of message.

        :param ch: refers to the head of the protocol
        :param method: refers to the method used in callback
        :param properties: refers to the proprieties of the message
        :param body: refers to the message transmitted
        """
        payload = json.loads(body)
        try:
            self._handler_events(payload)
        except Exception as ex:
            LOG.error(ex)
