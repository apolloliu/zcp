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
from logging import handlers
import os

from eszcp.common.conf import Conf


cfg_file = Conf()
root_level = cfg_file.read_option('log', 'root_level')
console_level = cfg_file.read_option('log', 'consolo_level')
log_level = cfg_file.read_option('log', 'log_level')
log_dir = cfg_file.read_option('log', 'log_dir')
log_file = cfg_file.read_option('log', 'log_file')
maxbytes = cfg_file.read_option('log', 'maxbytes')
backupcount = cfg_file.read_option('log', 'backupcount')
log_default_format = cfg_file.read_option('log',
                                          'log_default_format',
                                          raw=True)


class ContextAdapt(object):
    def __init__(self, logger):
        self.logger = logger

    def debug(self, msg=None):
        if msg:
            self.logger.debug(msg)

    def DEBUG(self, msg=None):
        self.debug(msg)

    def info(self, msg=None):
        if msg:
            self.logger.info(msg)

    def INFO(self, msg=None):
        self.info(msg)

    def warning(self, msg=None):
        if msg:
            self.logger.warning(msg)

    def WARING(self, msg=None):
        self.warning(msg)

    def error(self, msg=None):
        if msg:
            self.logger.error(msg)

    def ERROR(self, msg=None):
        self.error(msg)

    def critical(self, msg=None):
        if msg:
            self.msg.critical(msg)

    def CRITICAL(self, msg=None):
        self.critical(msg)

_loggers = {}
VALID_LEVELS = [
    'CRITICAL', 'critical',
    'FATAL', 'fatal',
    'ERROR', 'error',
    'WARNING', 'warning',
    'WARN', 'warn',
    'INFO', 'info',
    'DEBUG', 'debug',
    'NOTSET', 'noset'
]


def logger(name=None):
    if name not in _loggers:
        _loggers[name] = ContextAdapt(logging.getLogger(name))
    return _loggers[name]


def prepare_init():
    if not os.path.exists(log_dir):
        msg = "No such directory: %s" % log_dir
        raise IOError(msg)
    if not root_level or root_level not in VALID_LEVELS:
        msg = "Invalid log level of root_level: %s" % root_level
        raise ValueError(msg)
    if not console_level or console_level not in VALID_LEVELS:
        msg = "Invalid log level of consolo_level: %s" \
                % console_level
        raise ValueError(msg)
    if not log_level or log_level not in VALID_LEVELS:
        msg = "Invalid log level of log_level: %s" % log_level
        raise ValueError(msg)


def initlog():
    prepare_init()
    logfile = log_dir + log_file \
        if log_dir.endswith("/") else \
        log_dir + '/' + log_file
    # set root logger
    rootlogger = logger().logger
    rootlogger.setLevel(root_level.upper())
    logfmt = logging.Formatter(log_default_format)
    loghdl = handlers.RotatingFileHandler(filename=logfile,
                                          maxBytes=int(maxbytes),
                                          mode='a',
                                          backupCount=int(backupcount))
    consolohdl = logging.StreamHandler()
    # set log_file logger
    loghdl.setFormatter(logfmt)
    loghdl.setLevel(log_level.upper())

    # set log_file IOStream logger
    consolohdl.setLevel(console_level.upper())
    consolohdl.setFormatter(logfmt)
    # record log message in log_file or print log message with standard output
    rootlogger.addHandler(loghdl)
    rootlogger.addHandler(consolohdl)
