#    Copyright  2017 EasyStack, Inc
#    Author: Branty(jun.wang@easystack.cn)
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

import logging
from logging.config import fileConfig
import os

from eszcp.exceptions import LogConfigurationNotFound
from eszcp.common import conf

cfg_file = conf.Conf()
log_dir = cfg_file.read_option('log', 'log_dir')
log_file = cfg_file.read_option('log', 'log_file')


def init_log():
    log_path = os.path.join(log_dir, log_file)
    try:
        fileConfig(log_path)
    except Exception:
        msg = "Please configure correctly and be sure file log path exists!"
        raise LogConfigurationNotFound(msg)
    else:
        logger = logging.getLogger()
        logger.debug('Start initializing ZCP log...')
