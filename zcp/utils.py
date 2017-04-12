#    Copyright  2017 EasyStack, Inc
#    Author : Branty(jun.wang@easystack.cn)
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utilities and helper functions."""

import datetime
import json
from oslo_utils import timeutils
import re


AVALIABLE_STATUS = [
    'SHUTOFF',
    'ACTIVE'
    ]


class Singleton(object):

    def __init__(self, clz):
        """Return the last handler which cloud be required more than once."""
        self.clz = clz
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.clz(*args, **kwargs)
        return self.instance


def isUseable_instance(status):
    """
    :param status: nova instance status
    """
    return status in AVALIABLE_STATUS


def is_active(instance):
    """
    :param instance: a nova instance,normally is a dict
    """
    if isinstance(instance, dict):
        return instance['server']['status'] == 'ACTIVE' \
               if "server" in instance.keys() \
               else instance['status'] == "ACTIVE"
    else:
        return False


def endswith_words(source):
    """
    Determine whether a string ends with the pattern of vd[a-z]
    example:
        string = 'aa0d0c92-31a8-44a2-vsfd' =>>> return False
        string = 'aa0d0a-4733-944bfe7-vda' =>>> return True
    :param source: str

    """
    match = False
    if isinstance(source, str):
        match = re.search(".*-vd[a-z]$", source)
    elif isinstance(source, unicode):
        match = re.search(".*-vd[a-z]$", str(source))
    else:
        return False
    return match


def date2str(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")


def str2date(string):
    return datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")


def ms2str(date):
    return date.strftime("%Y-%m-%d %H:%M:%S.%f")


def utcnow():
    """Returns a datetime for the current utc time."""
    return timeutils.utcnow()


def mapping_json_to_dict(mapping_file):
    """
    Parsing the JSON file according to configuration
    The configuration is supported as follows:
    {
     "period_colls":[60,300,3600]
     "60":{
           "meter_type":["cpu_util",
                         "disk.read.bytes.rate",
                         "..."]
            "mult_topology":[1,5,15,120,1440]
            "point_topology":[100,300,100,100,200]
          },
     "300":{
          },
     "3600":{
            "meter_type":["instance",
                          "volume",
                          "account"
                          ...
                        ]
            "mult_topology":[1,6,24]
            "point_topology":[100,200,200]
          }
    }
    """

    def _parse_json_file(j_file):
        with open(j_file) as f:
            return json.load(f)
    try:
        map_dict = _parse_json_file(mapping_file)
        if 'period_colls' in map_dict and \
                isinstance(map_dict['period_colls'], list):
            for i in map_dict['period_colls']:
                if str(i) not in map_dict.keys():
                    raise Exception("Parsing mapping.json error, "
                                    "because of not key %d in "
                                    "the mapping file" % i)
        else:
            raise Exception("Parsing mapping.json error,"
                            "Maybe not key period_colls "
                            "in the mapping file or "
                            "the value of period_colls is not list")
        return map_dict
    except ValueError:
        raise
    except Exception:
        raise


def get_metric_BASE_T(map_dict, metric=None):
    """
    :param map_dict: Parsed mapping.json as a dict

    """
    if not isinstance(map_dict, dict):
        raise
    if metric is None:
        return
    for period in map_dict['period_colls']:
        metrics = map_dict.get(str(period))
        if not metrics:
            continue
        elif metric in metrics['meter_type']:
            return int(period)
    return
