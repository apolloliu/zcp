#!/usr/bin/env python
from setuptools import find_packages
from setuptools import setup

setup(
    name="zcp",
    version="1.0.0",
    author="hanxi.liu",
    author_email="apolloliuhx@gmail.com",
    packages=find_packages(),
    scripts=['bin/eszcp-polling'],
    url="https://github.com/apolloliu/ZCP",
    description="A Timer task for polling ceilometer metrics into zabbix"
)
