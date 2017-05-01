========================
Zabbix-Ceilometer Proxy
========================
.. image:: https://img.shields.io/pypi/v/zcp.svg
    :target: https://pypi.python.org/pypi/zcp/1.0.1

Objective
=========
This project started as a way to integrate monitoring information collected in a Cloud environment,
namely by OpenStack's Ceilometer, integrating it with an already existing monitoring solution using Zabbix.

Features
========
* Integration of OpenStack's available monitoring information (e.g. using Ceilometer) with already existing
  Monitoring systems (e.g. Zabbix);
* Automatically gather information about the existing Cloud Infrastructure being considered (tenants, instances);
* Seamlessly handle changes in the Cloud Infrastructure (creation and deletion of tenants and/or instances);
* Periodically retrieve resources/meters details from OpenStack;
* Allow to have one common monitoring system (e.g Zabbix) for several OpenStack-based Cloud Data Centres;
* Support keystone v3 to allow multiple domains using multiple proxies;
* Support rabbitmq clusters to consume messages from topics of keystone and nova;
* Provide default template(Template ZCP) to import through zabbix web interface;
* Provide mongo driver to retrive metrics from Ceilometer mongodb directly.

Requirements
============
The Zabbix-Ceilometer Proxy was written using _Python_ version 2.7.5 but can be easily ported to version 3.
It uses the Pika library for support of AMQP protocol, used by OpenStack.

For installing Pika, if you already have _Python_ and the _pip_ packet manager configured, you need only to
use a terminal/console and simply run following command under the project directory::

        sudo pip install -r requirement.txt

If the previous command fails, download and manually install the library on the host where you intend to
run the ZCP.

.. note::

    Since the purpose of this project is to be integrated with OpenStack and Zabbix it is assumed
    that apart from a running installation of these two, some knowledge of OpenStack has already
    been acquired.

Usage
=====
Assuming that all the above requirements are met, the ZCP can be run with 3 simple steps:

1. On your OpenStack installation point to your Keystone configuration file (keystone.conf) and
   update `notification_driver` to messaging(only support this driver for now)::

    notification_driver = messaging

2. Remember to modify ceilometer `event_pipline.yaml`. When the setup of notification_driver is done,
   a number of events of `identity.authenticate` will be put into ceilometer queue(notification.sample).
   There is no sense if record those events. The sample configuration in `/etc/ceilometer/event_pipeline.yaml`
   follows::

     | sources:
     |    - name: event_source
     |      events:
     |          - "*"
     |          - "!identity.authenticate"
     |      sinks:
     |          - event_sink
     | sinks:
     |    - name: event_sink
     |      transformers:
     |      triggers:
     |      publishers:
     |          - notifier://

2. Create directory for ZCP's log file and configuration file::

    $ sudo mkdir /var/log/zcp/
    $ sudo mkdir /etc/zcp/

3. Copy `proxy.conf` to `/etc/zcp/` and edit the `proxy.conf` configuration file to reflect your own system,
   including the IP addresses and ports of Zabbix and of the used OpenStack modules (RabbitMQ, Ceilometer
   Keystone and Nova). You can also tweak some ZCP internal configurations such as the polling interval and
   proxy name (used in Zabbix)::

    $ sudo cp etc/proxy.conf /etc/zcp/proxy.conf

4. Install zcp source code::

    $ python setup.py install

5. Add template name(Use `Template ZCP` as default) under 'zcp_configs' and import the template to Zabbix
   through Zabbix Web Interface. You can see `Template ZCP` in Zabbix `Templates` if import success.

6. Finally, run the Zabbix-Ceilometer Proxy in your console::

    $ eszcp-polling

If all goes well the information retrieved from OpenStack's Ceilometer will be pushed in your Zabbix
monitoring system.

.. note::

    You can check out a demo_ from a premilinary version of ZCP running with OpenStack Havana and Zabbix.

.. _demo: https://www.youtube.com/watch?v=DXz-W9fgvRk

Source
======
If not doing so already, you can check out the latest version of ZCP_.

.. _ZCP: https://github.com/apolloliu/zcp

Copyright
=========
Copyright (c) 2014 OneSource Consultoria Informatica, Lda.

Copyright (c) 2017 EasyStack Inc.

Thanks Cláudio Marques, David Palma and Luis Cordeiro for the original idea.

This project has been developed for the demand of Industrial Bank Co., Ltd by Branty and Hanxi Liu.
