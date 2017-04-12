#    Copyright  2017 EasyStack, Inc
#    Authors:  Branty <jun.wang@easystack.cn>
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

INSTANCE_METRICS = [
    'cpu_util',
    'cpu.delta',
    'memory.usage',
    'disk.read.bytes.rate',
    'disk.read.requests.rate',
    'disk.write.bytes.rate',
    'disk.write.requests.rate'
    ]

NETWORK_METRICS = [
    'network.incoming.bytes.rate',
    'network.incoming.packets.rate',
    'network.outgoing.bytes.rate',
    'network.outgoing.packets.rate'
    ]

"""
 Cache instance metrics, the date structure is the following:
 {"instance_id":{
     "instance_id": INSTANCE_METRICS,
     "instance-xxx-{instance_id}-{tap_id}": NETWORK_METRICS,
     "instance-{disk_id}": DISK_METRICS,
     ...
    },
  ...
 }
"""
