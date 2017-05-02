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
Zabbix Handler

Provides a class responsible for the communication with Zabbix,

including access to several API methods
"""

import functools
import json
import logging
import socket
import struct
import urllib2

from zcp import exceptions
from zcp import utils


LOG = logging.getLogger(__name__)


def logged(func):

    @functools.wraps(func)
    def with_logging(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, ex:
            LOG.error(ex)
            raise
    return with_logging


class Base_Handler(object):
    def __init__(self, zabbix_host, zabbix_port=10051):
        self.zabbix_host = zabbix_host
        self.zabbix_port = zabbix_port

    def set_proxy_header(self, data):
        """Method used to simplify constructing the protocol to
        communicate with Zabbix

        :param data: refers to the json message
        :rtype : returns the message ready to send to Zabbix server
        with the right header
        """
        # data_length = len(data)
        # data_header = struct.pack('i', data_length) + '\0\0\0\0'
        # HEADER = '''ZBXD\1%s%s'''
        # data_to_send = HEADER % (data_header, data)
        payload = json.dumps(data)
        return payload

    def connect_zabbix(self, payload):
        """
        Method used to send information to Zabbix
        :param payload: refers to the json message prepared to send to Zabbix
        :rtype : returns the response received by the Zabbix API
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.zabbix_host, int(self.zabbix_port)))
        s.send(payload)
        # read its response, the first five bytes are the header again
        response_header = s.recv(5, socket.MSG_WAITALL)
        if not response_header == 'ZBXD\1':
            raise ValueError('Got invalid response')

        # read the data header to get the length of the response
        response_data_header = s.recv(8, socket.MSG_WAITALL)
        response_data_header = response_data_header[:4]
        response_len = struct.unpack('i', response_data_header)[0]

        # read the whole rest of the response now that we know the length
        response_raw = s.recv(response_len, socket.MSG_WAITALL)
        s.close()
        LOG.info(response_raw)
        response = json.loads(response_raw)

        return response

    def send_data_zabbix(self, counter_volume, resource_id,
                         item_key, proxy_name):
        """Method used to prepare the body with data from Ceilometer and send
        it to Zabbix using connect_zabbix method

        :param counter_volume: the actual measurement
        :param resource_id:  refers to the resource ID
        :param item_key:    refers to the item key
        """
        tmp = json.dumps(counter_volume)
        data = {"request": "history data", "host": proxy_name,
                "data": [{"host": resource_id,
                          "key": item_key,
                          "value": tmp}]}

        payload = self.set_proxy_header(data)
        self.connect_zabbix(payload)


class ZabbixHandler(Base_Handler):
    def __init__(self, zabbix_admin_user, zabbix_admin_pass,
                 zabbix_host, zabbix_port,
                 template_name, ks_client, nv_client):
        """
        :param zabbix_user: zabbix admin user
        :param zabbix_pass: zabbix admin password
        :param zabbix_pass: zabbix host ip
        :param template_name:zabbix templete which binds nova instance
        :parms ks_client: Openstack identity service, keystone client
        :parms nv_client: Openstack compute service,nova client
        :parms zabbix_hdl:zabbix handler
        """
        super(ZabbixHandler, self).__init__(zabbix_host, zabbix_port)
        self.zabbix_admin_user = zabbix_admin_user
        self.zabbix_admin_pass = zabbix_admin_pass
        self.template_name = template_name
        self.ks_client = ks_client
        self.nv_client = nv_client
        self.group_list = []

    def first_run(self):

        self.api_auth = self.get_zabbix_auth()
        self.proxies = self.check_proxies()
        self.template_id = self.get_template_id()
        tenants = self.ks_client.get_projects()
        self.group_list = self.host_group_list(tenants)
        self.check_host_groups()
        self.check_instances()

    def get_zabbix_auth(self):
        """
        Method used to request a session ID form Zabbix API by sending
        Admin credentials (user, password)

        :return: returns an Id to use with zabbix api calls
        """
        payload = {"jsonrpc": "2.0",
                   "method": "user.login",
                   "params": {"user": self.zabbix_admin_user,
                              "password": self.zabbix_admin_pass},
                   "id": 2}
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            LOG.error('Incorrect user or password,please check it again')
            raise
        zabbix_auth = response['result']
        return zabbix_auth

    def check_proxies(self):
        """
        Method used to check if those proxies exist.
        Map keystone domain to zabbix proxy.

        :return: a control value and those proxies if exists
        """
        cache_proxy = {}
        payload = {
            "jsonrpc": "2.0",
            "method": "proxy.get",
            "params": {
                "output": "extend"
            },
            "auth": self.api_auth,
            "id": 1
        }
        # return all proxies in zabbix
        response = self.contact_zabbix_server(payload)
        proxies = [proxy['host'] for proxy in response['result']]
        for proxy in response['result']:
            cache_proxy[proxy['host']] = proxy['proxyid']
        # return all domains in keystone
        domains = [domain for domain in self.ks_client.get_domains()]
        # each item in current_proxies:[proxy_id,domain_id]
        current_proxies = []
        for domain in domains:
            if domain.name not in proxies:
                '''
                Check if proxy exists, if not create one
                '''
                # host: domain ID truncated by the first eight
                if domain.id[:8] in proxies:
                    current_proxies.append([cache_proxy[domain.id[:8]],
                                            domain.id])
                    continue
                LOG.info("%s is not in zabbix proxies, starting to create a "
                         "new proxy mapping to keystone domain" % domain.name)
                payload = {
                       "jsonrpc": "2.0",
                       "method": "proxy.create",
                       "params": {
                           "host": domain.name,
                           "status": "5"
                       },
                       "auth": self.api_auth,
                       "id": 1
                       }
                response = self.contact_zabbix_server(payload)
                # NOTE: when '@','#' or other No ASSIC char in name string,
                # raise 'Invalid Params' error.
                # Then Replace zabbix proxy name with domain ID
                # host: domain ID truncated by the first eight
                if 'error' in response:
                    payload['params']['host'] = domain.id[:8]
                    response = self.contact_zabbix_server(payload)
                proxy_id = response['result']['proxyids'][0]
                current_proxies.append([proxy_id, domain.id])
                LOG.info("%s is not in zabbix proxies, success to create a "
                         "new proxy mapping to keystone domain" % domain.name)
            else:
                current_proxies.append([[cache_proxy[domain.name]], domain.id])
        return current_proxies

    @logged
    def check_host_groups(self):
        """
        This method checks if some host group exists

        """
        payload = {
                "jsonrpc": "2.0",
                "method": "hostgroup.get",
                "params": {
                    "output": "extend"
                },
                "auth": self.api_auth,
                "id": 1
        }
        # Get all host groups
        response = self.contact_zabbix_server(payload)
        zabbix_hostgroups = [gp['name'] for gp in response['result']]
        for item in self.group_list:
            if item[0] not in zabbix_hostgroups:
                # Prevent naming collision
                if str(item[0] + item[1][:6]) in zabbix_hostgroups:
                    continue
                payload = {"jsonrpc": "2.0",
                           "method": "hostgroup.create",
                           "params": {"name": item[0]},
                           "auth": self.api_auth,
                           "id": 2}
                response = self.contact_zabbix_server(payload)
                if 'error' in response:
                    # NOTE:host name collision ,rename host_name =
                    # <tenant ID truncated by the first six> + <tenant_nam>
                    payload['params']['name'] = item[0] + item[1][:6]
                    response = self.contact_zabbix_server(payload)
                if response.get('result'):
                    LOG.info("Success to create a new hostgroup: %s, "
                             "zabbix hostgroup mapping to keystone project."
                             % payload['params']['name'])
                else:
                    LOG.info("Failed to create a new hostgroup: %s, "
                             "zabbix hostgroup mapping to keystone project."
                             % payload['params']['name'])
            else:
                LOG.info("Already exists a new hostgroup: %s, "
                         "zabbix hostgroup mapping to keystone project."
                         % item[0])

    @logged
    def check_instances(self):
        """
        Method used to verify existence of an instance / host

        """
        servers = [i.to_dict() for i in self.nv_client.instance_get_all()]
        for item in servers:
            if utils.isUseable_instance(item['status']):
                payload = {
                    "jsonrpc": "2.0",
                    "method": "host.get",
                    "params": {
                        "output": "extend",
                        "filter": {"host": item['id']}
                        },
                    "auth": self.api_auth,
                    "id": 1
                }
                response = self.contact_zabbix_server(payload)
                # the Nova instance has not been create in zabbix,
                # so the result in the return body in []
                if not response.get('result', []):
                    for row in self.group_list:
                        if row[1] == item['tenant_id']:
                            instance_name = item['name']
                            instance_id = item['id']
                            domain_id = row[2]
                            tenant_name = row[0]
                            self.create_host(
                                         instance_name,
                                         instance_id,
                                         tenant_name,
                                         item['tenant_id'],
                                         domain_id,
                                         )
                            LOG.info(
                                "Success to create a new host: %s, "
                                "The instances is to a keystone "
                                "project(%s),and now create a new zabbix host "
                                "added to the zabbix hostgroup. "
                                % (instance_name,
                                   tenant_name
                                   )
                            )
                else:
                    LOG.info("Zabbix host(%s) has already exists."
                             % item['id'])
            else:
                msg = "Drop to check or create instance ," \
                      "the status of %(instance_name)s(%(instance_id)s) " \
                      "is in %(status)s." \
                      % {"instance_name": item['name'],
                         "instance_id": item['id'],
                         "status": item['status']}
                LOG.warning(msg)

    def create_host(self, instance_name, instance_id,
                    tenant_name, tenant_id, domain_id=None):

        """
        Method used to create a host in Zabbix server

        :param instance_name: refers to the instance name
        :param instance_id:   refers to the instance id
        :param tenant_name:   refers to the tenant name
        :param domain_id:     refers to the domain id
        """
        group_id = self.find_group_id(tenant_name, tenant_id)
        if not domain_id:
            project = self.ks_client.get_project(tenant_id)
            domain_id = project.domain_id
        proxy_id = self.find_proxy_id(domain_id)
        hostname = instance_name
        if not (instance_id in instance_name):
            hostname = instance_name + '_' + instance_id[:8]

        payload = {"jsonrpc": "2.0",
                   "method": "host.create",
                   "params": {
                       "host": instance_id,
                       "name": hostname,
                       "proxy_hostid": proxy_id,
                       "interfaces": [
                           {
                               "type": 1,
                               "main": 1,
                               "useip": 1,
                               "ip": "127.0.0.1",
                               "dns": "",
                               "port": "10050"}
                       ],
                       "groups": [
                           {
                               "groupid": group_id
                           }
                       ],
                       "templates": [
                           {
                               "templateid": self.template_id
                           }
                       ],

                   },
                   "auth": self.api_auth,
                   "id": 1}
        response = self.contact_zabbix_server(payload)
        if response.get('result'):
            LOG.info("Success to create a new host: %s" % instance_name)
        else:
            LOG.warning("Failed to create a new host: %s" % instance_name)

    def find_group_id(self, tenant_name, tenant_id):
        """
        Method used to find the the group id of an host in Zabbix server

        :param tenant_name: refers to the tenant name
        :param tenant_id: refers to the tenant id
        :return: returns the group id that belongs to the host_group or tenant
        """
        group_id = None
        payload = {"jsonrpc": "2.0",
                   "method": "hostgroup.get",
                   "params": {
                       "output": "extend"
                   },
                   "auth": self.api_auth,
                   "id": 2
                   }
        response = self.contact_zabbix_server(payload)
        group_list = response['result']
        for line in group_list:
            if line['name'] == tenant_name:
                group_id = line['groupid']
                break
            elif line['name'] == tenant_name + tenant_id[:6]:
                group_id = line['groupid']
                break
        return group_id

    def find_proxy_id(self, domain_id):
        """
        Method used to find the the proxy id of an host in Zabbix server
        :param domain_name: refers to the domain name
        :param domain_id: refers to the domain id
        :return: returns the proxy id that belongs to the zabbix proxy
        """
        # When domain_id not found, raise exception
        # TO DO
        domain = self.ks_client.show_domain(domain_id)
        payload = {"jsonrpc": "2.0",
                   "method": "proxy.get",
                   "params": {
                       "output": "extend",
                       "filter": {
                            "host": domain.name
                           }
                   },
                   "auth": self.api_auth,
                   "id": 2
                   }
        response = self.contact_zabbix_server(payload)
        proxy = response['result']
        if proxy and len(proxy) > 0:
            return proxy[0]['proxyid']
        else:
            payload['params']['filter']['host'] = domain.id[:8]
            response = self.contact_zabbix_server(payload)
            proxy = response['result']
            if proxy and len(proxy) > 0:
                return proxy[0]['proxyid']
        # proxy not found
        raise

    def get_template_id(self):
        """
        Method used to check if the template already exists.
        If not, creates one

        :return: returns the template ID
        """
        global template_id
        template_id = None
        payload = {
            "jsonrpc": "2.0",
            "method": "template.get",
            "params": {
                "output": "extend",
                "filter": {
                    "host": [
                        self.template_name
                    ]
                }
            },
            "auth": self.api_auth,
            "id": 1
        }
        response = self.contact_zabbix_server(payload)

        if len(response['result']) > 0:
            for item in response['result']:
                template_id = item['templateid']
        else:
            message = ("Can't find default template in zabbix. "
                       "Please import the default template!")
            raise exceptions.TemplateNotFound(message)
        return template_id

    def find_host_id(self, host):
        """
        Method used to find a host Id in Zabbix server

        :param host: ref to nova instance_id
        :return: returns the host id
        """
        host_id = None
        payload = {"jsonrpc": "2.0",
                   "method": "host.get",
                   "params": {
                       "output": "extend",
                       "filter": {"host": host}
                   },
                   "auth": self.api_auth,
                   "id": 2
                   }
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            LOG.error("Falied to find host(%s):%s,maybe zabbix server "
                      "is down" % (host, response['error']['data']))
        elif len(response.get('result')):
            host_id = response['result'][0]['hostid']
        else:
            LOG.waring("Falied to find host: %s" % host)
        return host_id

    def delete_host(self, host_id):
        """
        Method used to delete a Host in Zabbix Server

        :param host_id: refers to the host id to delete
        """
        payload = {"jsonrpc": "2.0",
                   "method": "host.delete",
                   "params": [
                       host_id
                   ],
                   "auth": self.api_auth,
                   "id": 1
                   }
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            LOG.error("Falied to delete host:%s,maybe zabbix server "
                      "is down" % host_id)
        else:
            LOG.info("Success to delete host:%s" % host_id)

    def host_group_list(self, tenants):
        """
        Method to "fill" an array of hosts

        :param tenants: receive an array of tenants
        :return: parsed list of hosts [[tenant_name1, uuid1],
        [tenant_name2, uuid2], ..., [tenant_nameN, uuidN],]
        """
        host_group_list = []
        for item in tenants:
            if not item.name == 'services':
                host_group_list.append([item.name,
                                        item.id,
                                        item.domain_id
                                        ]
                                       )

        return host_group_list

    def project_delete(self, tenant_id):
        """
        Method used to delete a project

        :param tenant_id: receives a tenant id
        """

        for item in self.group_list:
            if item[1] == tenant_id:
                tenant_name = item[0]
                group_id = self.find_group_id(tenant_name, tenant_id)
                self.delete_host_group(group_id)
                self.group_list.remove(item)

    def delete_host_group(self, group_id):
        """
        This method deletes a host group
        :param group_id: receives the group id
        """
        payload = {"jsonrpc": "2.0",
                   "method": "hostgroup.delete",
                   "params": [group_id],
                   "auth": self.api_auth,
                   "id": 1
                   }
        self.contact_zabbix_server(payload)

    def create_host_group(self, tenant_name):
        """
        This method is used to create host_groups. Every tenant is a host group

        :param tenant_name: receives keystone tenant name
        """
        payload = {"jsonrpc": "2.0",
                   "method": "hostgroup.create",
                   "params": {"name": tenant_name},
                   "auth": self.api_auth,
                   "id": 2}
        self.contact_zabbix_server(payload)

    def create_proxy(self, domain_name, domain_id):
        """
        This method is used to create zabbix proxy. Every domain
        is a zabbix proxy

        :param domain_name: refs to keystone domain name
        :param domain_id:   refs to keystone domain id
        """
        payload = {
                       "jsonrpc": "2.0",
                       "method": "proxy.create",
                       "params": {
                           "host": domain_name,
                           "status": "5"
                       },
                       "auth": self.api_auth,
                       "id": 1
        }
        proxy_id = None
        response = self.contact_zabbix_server(payload)
        # NOTE: when '@','#' or other No ASSIC char in name string,
        # raise 'Invalid Params' error.
        # Then Replace zabbix proxy name with domain ID
        # host: domain ID truncated by the first eight
        if 'error' in response:
            payload['params']['host'] = domain_id[:8]
            response = self.contact_zabbix_server(payload)
            if 'error' not in response:
                proxy_id = response['result']['proxyids'][0]
                LOG.info("Success to create a new proxy: %s" % domain_id[:8])
                self.proxies.append([proxy_id, domain_id])
            else:
                LOG.warning("Failed to create a new proxy: %s,"
                            "error message: %s" % (domain_id[:8],
                                                   response['error']))
        elif response.get('result'):
            proxy_id = response['result']['proxyids'][0]
            LOG.info("Success to create a new proxy: %s" % domain_name)
            self.proxies.append([proxy_id, domain_id])

    def delete_proxy(self, domain_id):
        for item in self.proxies:
            if item[1] == domain_id:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "proxy.delete",
                    "params": [item[0]],
                    "auth": self.api_auth,
                    "id": 1
                }
                response = self.contact_zabbix_server(payload)
                if 'result' in response:
                    LOG.info("Success to delete a new proxy: %s"
                             % response['result']['proxyids'][0])
                    self.proxies.remove(item)
                else:
                    LOG.warning("Falied to delete a new proxy, error "
                                "message:%s" % response['error'])

    def get_items_by_template(self):
        """This method find all items in specified template
        :return : a list stored all metric items
        """
        template_id = self.get_template_id()
        payload = {"jsonrpc": "2.0",
                   "method": "item.get",
                   "params": {"output": "extend",
                              "templateids": [template_id]},
                   "auth": self.api_auth,
                   "id": 1
                   }
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            return []
        else:
            return [item['name'] for item in response['result']]

    def get_hosts_by_proxy(self, proxy_id=None):
        """This method find all hosts in specified proxy
        :return : a dict stored all hosts
        """
        hosts = {}
        # proxy_name is not None,find all hosts in the specified proxy
        if proxy_id:
            payload = {"jsonrpc": "2.0",
                       "method": "host.get",
                       "params": {"output": "extend",
                                  "proxyids": [proxy_id]},
                       "auth": self.api_auth,
                       "id": 1
                       }
            response = self.contact_zabbix_server(payload)
            if 'error' not in response:
                hosts = {proxy_id: response['result']}
        else:
            for i in self.proxies:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "host.get",
                    "params": {"output": "extend",
                               "proxyids": [i[0]]},
                    "auth": self.api_auth,
                    "id": 1
                   }
                response = self.contact_zabbix_server(payload)
                hosts[i[0]] = [(host['host'], host['hostid'], host['name'])
                               for host in response['result']]
        return hosts

    def get_hosts(self, filter_no_proxy=False):
        """Method used do query Zabbix API in order to fill an Array of hosts

        :params filter_no_proxy: get all hosts whose proxy_hostid is not '0'
        :return: returns a dict and a list ,record zabbix host information.
        hosts_cache, the date structure is the following:
         {"instance_id":["host_id","host_name","proxy_id"]
         }
        hosts: ['instance_id1','instance)id2',...]
        """
        hosts = []
        hosts_cache = {}
        payload = {
                    "jsonrpc": "2.0",
                    "method": "host.get",
                    "params": {"output": "extend"},
                    "auth": self.api_auth,
                    "id": 1
        }
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            LOG.warning("Falied to get all zabbix hosts, error "
                        "message:%s" % response['error'])
            return []
        # Get hosts monitoring the zabbix proxy
        if filter_no_proxy:
            for host in response['result']:
                if int(host['proxy_hostid']):
                    hosts.append(host['host'])
                    hosts_cache[host['host']] = [host['hostid'],
                                                 host['name'],
                                                 host['proxy_hostid']]
        else:
            for host in response['result']:
                hosts.append(host['host'])
                hosts_cache[host['host']] = [host['hostid'],
                                             host['name'],
                                             host['proxy_hostid']]
        return hosts, hosts_cache

    def get_by_proxyid(self, proxy_id):
        """
        :param proxy_id: refs to proxy id
        """
        payload = {
                    "jsonrpc": "2.0",
                    "method": "proxy.get",
                    "params": {"output": "extend",
                               "proxyids": proxy_id},
                    "auth": self.api_auth,
                    "id": 1
        }
        response = self.contact_zabbix_server(payload)
        if 'error' in response:
            LOG.error("Falied to find proxy : %s" % proxy_id)
        elif len(response['result']) == 0:
            LOG.warning("Can't find proxy : %s" % proxy_id)
        else:
            return response['result'][0]

    def contact_zabbix_server(self, payload):
        """
        Method used to contact the Zabbix server.

        :param payload: refers to the json message to send to Zabbix
        :return: returns the response from the Zabbix API
        """
        data = json.dumps(payload)
        req = urllib2.Request('http://' + self.zabbix_host +
                              '/zabbix/api_jsonrpc.php',
                              data,
                              {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = json.loads(f.read())
        f.close()
        return response