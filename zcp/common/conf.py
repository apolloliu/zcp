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
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""
Class for reading the configuration file

Uses the ConfigParser lib to return the values present in the config file
"""

import ConfigParser
from ConfigParser import NoOptionError
from ConfigParser import NoSectionError
import os
import sys


FIND_DIRS = [
            os.path.abspath(os.path.join(
                            os.path.dirname(__file__),
                            "..", "etc/proxy.conf")
                            ),
            "/etc/zcp/proxy.conf",
            ]

"""
The basic singleton pattern

Use __new__ when you need to control the creation of a new instance.

Use __init__ when you need to control initialization of a new instance.

How to use them,view  the following link:
https://mail.python.org/pipermail/tutor/2008-April/061426.html

When cls._instance is None, the class of Singleton is not  instantiated,
instantiate this class and return.

When cls._instance in not None, return the instance directly.

Talk  is too cheap,show you the codes:

    class Singleton(object):
        def __new__(cls, *args,**kwargs):
            if not hasattr(cls,'_instance'):
               cls._instance = super(Singleton,cls).__new__(cls,
                                                            *args,
                                                            **kwargs)
            return  cls._instance

    class Myclass(Singleton):
        a = 1
    one = Myclass()
    two = Myclass()
    # we can compare one with two, id(), == ,is
    two.a = 3
    print one.a  # output is : 3
    print id(one) == id(two) # outout is : True

"""


def singleton(cls, *args, **kwags):
    instance = {}

    def _singleton():
        if cls not in instance:
            instance[cls] = cls(*args, **kwags)
        return instance[cls]
    return _singleton


@singleton
class Conf:
    """
    parse ZabbixCeilometer Proxy conf , singleton partten

    The way of  decorator for singleton pattern is more pythonic

    """

    config = None

    def __init__(self, conf_file=None):

        """
        Method to read from conf file specific options

        :param file: the zcp configuration file
        """
        zcp_conf = None
        if conf_file and os.path.exists(conf_file):
            zcp_conf = conf_file
        if not zcp_conf:
            for f in FIND_DIRS:
                if os.path.exists(f):
                    zcp_conf = f
                    break
        if not zcp_conf:
            print "Can't find zabbixceilometer-proxy configurate file"
            sys.exit(1)
        self.config = ConfigParser.SafeConfigParser()
        self.config.readfp(open(zcp_conf))

    def read_option(self, group, name, default=None, raw=False):
        """
        :return:
        """
        value = None
        try:
            value = self.config.get(group, name, raw=raw)
        except NoOptionError or NoSectionError:
            if default is not None:
                return default
            else:
                raise
        except Exception:
            raise
        return value
