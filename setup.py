#!/usr/bin/env python
from setuptools import find_packages
from setuptools import setup

setup(
    name="eszcp",
    version="1.0.0",
    author=["Branty","Hanxi Liu"],
    author_email=["jun.wang@easystack.cn","hanxi.liu@easystack.cn"],
    packages=find_packages(),
    scripts=['bin/eszcp-polling'],
    url="www.easystack.cn",
    description="A Timer task for polling ceilometer metrics into zabbix"
)
