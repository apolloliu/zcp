#!/usr/bin/env python
from setuptools import find_packages
from setuptools import setup

setup(
    version="1.0.1",
    author="hanxi.liu",
    author_email="apolloliuhx@gmail.com",
    packages=find_packages(),
    scripts=['bin/zcp-polling'],
    description="A Timer task for polling ceilometer metrics into zabbix"
)
