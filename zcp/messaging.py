#    Copyright  2017 EasyStack, Inc
#    Authors: Hanxi Liu<apolloliuhx@gmail.com>
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
import pika
import time

from eszcp.common import conf


LOG = logging.getLogger(__name__)
cfg = conf.Conf()

hosts = cfg.read_option('os_rabbitmq', 'rabbit_hosts')
user = cfg.read_option('os_rabbitmq', 'rabbit_user')
passwd = cfg.read_option('os_rabbitmq', 'rabbit_pass')
port = cfg.read_option('os_rabbitmq', 'rabbit_port')
vh = cfg.read_option('os_rabbitmq', 'rabbit_virtual_host')
max_retries = int(cfg.read_option('os_rabbitmq', 'max_retries', -1))
retry_interval = int(cfg.read_option('os_rabbitmq', 'retry_interval', 5))


def connection():
    connect = None
    connection_state = False
    attemps = 0
    MAX_RETRIES = max_retries * len(hosts.split(','))
    while True:
        if connection_state:
            break
        try:
            for host in hosts.split(','):
                LOG.info("Connecting to Rabbitmq server %s..." % host)
                connect = pika.BlockingConnection(pika.ConnectionParameters(
                    host=host,
                    port=int(port),
                    virtual_host=vh,
                    credentials=pika.PlainCredentials(user,
                                                      passwd)))
        except Exception as e:
            if max_retries < 0:
                LOG.error('Unable to connect to the Rabbitmq cluster: '
                          '%(msg)s.Trying again in %(retry_interval)d '
                          'seconds,Continuing to retry to connect '
                          % {'msg': e,
                             'retry_interval': retry_interval})
                time.sleep(retry_interval)
            elif max_retries > 0 and attemps <= MAX_RETRIES:
                LOG.error('Unable to connect to the Rabbitmq cluster: '
                          '%(msg)s.Trying again in %(retry_interval)d '
                          'seconds,max_retries time: %(max_retries)d,'
                          'retry times left:%(left)d'
                          % {'msg': e,
                             'retry_interval': retry_interval,
                             'max_retries': MAX_RETRIES,
                             'left': (MAX_RETRIES - attemps)})
                attemps += 1
                time.sleep(retry_interval)
            else:
                LOG.error('Unable to connect to the Rabbitmq cluster: '
                          '%(msg)s.' % {'msg': e})
                raise
        else:
            connection_state = True
    return connect


class MQConnection(object):
    """RabbitMQ connection class
    """
    def __init__(self):
        self.connection = connection()

    def __call__(self):
        self.connection = connection()
