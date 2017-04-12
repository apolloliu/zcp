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
Class for Handling Nova events in OpenStack's RabbitMQ

Uses the pika library for handling the AMQP protocol, implementing the

necessary callbacks for Nova events
"""

import json

from eszcp.common import log


LOG = log.logger(__name__)


class NovaEvents:
    def __init__(self, zabbix_handler, connection):

        """
        :param zabbix_handler: zabbix api handler
        :param connection: rabbitmq connection instance
        """
        self.zabbix_handler = zabbix_handler
        self.mqconnc = connection

    def nova_amq(self):
        """
        Method used to listen to nova events

        """
        try:
            LOG.info("Start consuming nova messages from rabbitmq ...")
            channel = self.mqconnc.connection.channel()
            channel.exchange_declare(exchange='nova', type='topic')
            channel.queue_declare(queue="zcp-nova", exclusive=True)
            channel.queue_bind(exchange='nova', queue="zcp-nova",
                               routing_key='notifications.#')
            channel.queue_bind(exchange='nova', queue="zcp-nova",
                               routing_key='compute.#')
            channel.basic_consume(self.nova_callback,
                                  queue="zcp-nova",
                                  no_ack=True)
            channel.start_consuming()
        except Exception as e:
            LOG.error("Fail to consume messages from nova: %s" % e)
            # Make sure consume messages normally
            self.mqconnc()

    def nova_callback(self, ch, method, properties, body):
        """
        Method used by method nova_amq() to filter messages by type of message.

        :param ch: refers to the head of the protocol
        :param method: refers to the method used in callback
        :param properties: refers to the proprieties of the message
        :param body: refers to the message transmitted
        """
        payload = json.loads(body)

        try:
            project_name = payload.get('_context_project_name')
            project_id = payload.get('_context_project_id')
            if not (project_id or project_name):
                LOG.debug("Drop a notification message,"
                          "project_name or project_id is not found.")
                return
            type_of_message = payload['event_type']

            if type_of_message == 'compute.instance.create.end':
                instance_id = payload['payload']['instance_id']
                instance_name = payload['payload']['hostname']
                self.zabbix_handler.create_host(instance_name,
                                                instance_id,
                                                project_name,
                                                project_id)
                LOG.info("Creating a host: %s(%s) in Zabbix Server"
                         % (instance_id, instance_name))
            elif type_of_message == 'compute.instance.delete.end':
                host = payload['payload']['instance_id']
                host_id = self.zabbix_handler.find_host_id(host)
                self.zabbix_handler.delete_host(host_id)
                LOG.info("Deleting a host: %s in Zabbix Server"
                         % host_id)
            else:
                # TO DO
                # Maybe more event types will be supported
                pass
        except Exception as ex:
            LOG.error('Failed to handler nova event: %(event_type)s '
                      'error message: %(msg)s.'
                      % {'event_type': payload['event_type'], 'msg': ex})
