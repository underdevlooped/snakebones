#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding=utf-8
"""
Created on Tue Nov 20 21:08:21 2018

terca, 203‎ de novembro de ‎2018, 21:08:21
.
@author: Andre Kern

Integrar cURL a API GNS3 com python

Initially, we generated a random tree of switches that defines
the switches’ connectivity. Then, we randomly connect the
required number of hubs to free switch ports and we uniformly
attached hosts to the switches and the hubs of the constructed
tree. In the following, we arbitrarily associated each host with
a single subnet-id and we connected the constructed tree to a
router with a dedicated port for each subnet.

Simulation results of networks with 10 switches (with 8 ports), 10 dumbhubs
(with 8 ports) and 100 hosts.  3:7 subnets, 0:5 uncooperative switchs
"""
from ast import literal_eval
from pdb import set_trace as breakpoint
from pprint import pprint
from subprocess import run, PIPE


class Gns3(object):
    """
    classe para gerenciar comunicacao com servidores GNS3 por meio da
    integracao entre cURP e API GNS3, lendo e escrevendo dados

    """

    def __init__(self, server='localhost', port=3080, project_id=None, user=None, pword=None):
        self.server = server
        self.port = str(port)
        self.version = curl_get(server=server, port=port, cmd='version')
        self.computes = curl_get(server=server, port=port, cmd='computes')
        self.projects = curl_get(server=server, port=port, cmd='projects')

    def __repr__(self):
        return f"Gns3({self.server!r}, {self.port})"

    # HINT Gns3: metodo nodes para criar e listar nodes
    def nodes(self, project_id=None, new=None):
        if new:
            node = curl_post(server=self.server,
                             port=self.port,
                             project_id=project_id,
                             cmd='nodes',
                             data=new)
            return node
        nodes = curl_get(server=self.server,
                         port=self.port,
                         project_id=project_id,
                         cmd='nodes')
        return nodes

# criar node
# curl -X POST
# 192.168.139.1:3080/v2/projects/389dde3d-08ac-447b-8d54-b053a3f6ed19/nodes -d '{"name": "VPCS 1", "node_type": "vpcs", "compute_id": "vm"}'
# HINT curl_get: funcao envia comandos para o servidor GNS3 e captura resposta
# HINT curl_get: atributos nomeados
def curl_get(server=None, port=None, project_id=None, cmd=None):
    """
    Envia comando cURL para servidor GNS3, captura resposta em string, formata e
    retorca conversao em objeto apropriado.
    dict, list, tuple, True, False, None, str.

    Exemplo:
    >>> curl_get('192.168.139.128', 3080, 'computes')
    curl 192.168.139.128:3080/v2/computes

    :param server: IP do servidor http alvo
    :param port: porta TCP do servidor alvo
    :param cmd: parametro final do comando
    :return: resposta em objto convertido
    """
    cmd_prefix = "".join(('curl ', server, ':', str(port), '/v2'))
    if project_id:
        cmd_prefix = "".join((cmd_prefix, '/projects/', project_id))
    if cmd:
        cmd_prefix = "".join((cmd_prefix, '/', cmd))
    cmd_send = cmd_prefix.split()
    cmd_ans = run(cmd_send, stdout=PIPE, universal_newlines=True).stdout
    strdict = ''.join(cmd_ans.replace(" ", "").split('\n'))
    strdict = strdict.replace('false',
                              'False').replace('true',
                                               'True').replace(':null',
                                                               ':None')
    str.replace(strdict, 'false', 'False')
    return literal_eval(strdict)


def curl_post(server=None, port=None, project_id=None, cmd=None, data=None):
    """
    Envia comando cURL para servidor GNS3, captura resposta em string, formata e
    retorca conversao em objeto apropriado.
    dict, list, tuple, True, False, None, str.

    Exemplo:
    >>> curl_put('192.168.139.128', 3080, 'computes')
    curl 192.168.139.128:3080/v2/computes

    :param server: IP do servidor http alvo
    :param port: porta TCP do servidor alvo
    :param cmd: parametro final do comando
    :return: resposta em objto convertido
    """
    cmd_prefix = "".join(('curl -X POST ', server, ':', str(port),
                          '/v2/projects/', project_id, '/', cmd, ' -d '))
    data_str = repr(data).replace('False',
                                  'false').replace('True',
                                                   'true').replace(':None',
                                                                   ':null')
    data_str = '\'' + data_str.replace('\'', '"') + '\''

    cmd_send = cmd_prefix + data_str
    cmd_ans = run(cmd_send, stdout=PIPE, universal_newlines=True, shell=True).stdout
    strdict = ''.join(cmd_ans.replace(" ", "").split('\n'))
    strdict = strdict.replace('false',
                              'False').replace('true',
                                               'True').replace(':null',
                                                               ':None')
    # str.replace(strdict, 'false', 'False')
    return literal_eval(strdict)

# HINT set_node: gerador de script modelo para nodes
def set_node(ip=None, prefix='24', gateway=None):
    if gateway:
        starturp_script = "set pcname -" + ip + "-\n" + \
                          " ".join(("ip", ip, gateway, prefix, "\n"))
    else:
        starturp_script = "set pcname -" + ip + "-\n" + \
                          " ".join(("ip", ip, prefix, "\n"))

    null = False
    node_cfg = \
    {
        "compute_id": "vm",
        # "console": 5001,
        "console_type": "telnet",
        # "first_port_name": null,
        # "height": 59,
        # "label": {
        #     "rotation": 0,
        #     # "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
        #     "text": ip,
        #     # "x": 19,
        #     # "y": -25
        # },
        "name": ip[ip.find('.',3)+1:],
        # "node_id": "1c867306-7db3-4368-bc26-a76ec61451fe",
        "node_type": "vpcs",
        "port_name_format": "Ethernet{0}",
        "port_segment_size": 0,
        "properties": {
            "startup_script": starturp_script,
            "startup_script_path": "startup.vpc"
        },
        "symbol": ":/symbols/vpcs_guest.svg"
        # "width": 65,
        # "x": -257,
        # "y": -254,
        # "z": 1
    }
    return node_cfg


# HINT set_hub: gerador de script modelo para hubs
def set_hub():
    hub_cfg = \
        {
            "compute_id": "vm",
            # "console": null,
            # "console_type": null,
            # "first_port_name": null,
            # "height": 32,
            # "label": {
            #     "rotation": 0,
            #     "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
            #     "text": "SW-HUB",
            #     "x": 14,
            #     "y": -24
            # },
            "name": "SW-HUB",
            # "node_id": "3c59e645-08af-4d77-90b9-1c212f67929f",
            "node_type": "ethernet_switch",
            "port_name_format": "Ethernet{0}",
            "port_segment_size": 0,
            # "properties": {
            #     "ports_mapping": [
            #         {
            #             "name": "Ethernet0",
            #             "port_number": 0,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet1",
            #             "port_number": 1,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet2",
            #             "port_number": 2,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet3",
            #             "port_number": 3,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet4",
            #             "port_number": 4,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet5",
            #             "port_number": 5,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet6",
            #             "port_number": 6,
            #             "type": "access",
            #             "vlan": 1
            #         },
            #         {
            #             "name": "Ethernet7",
            #             "port_number": 7,
            #             "type": "access",
            #             "vlan": 1
            #         }
            #     ]
            # },
            "symbol": ":/symbols/ethernet_switch.svg",
            # "width": 72,
            # "x": 114,
            # "y": 134,
            # "z": 1
        }
    return hub_cfg


# Server version
# Check the server version with a simple curl command:
#
# # curl "http://localhost:3080/v2/version"
# {
#     "local": false,
#     "version": "2.1.4"
# }
# List computes
# List all the compute servers:
#
# # curl "http://localhost:3080/v2/computes"
# [
#     {
#         "compute_id": "local",
#         "connected": true,
#         "host": "127.0.0.1",
#         "name": "local",
#         "port": 3080,
#         "protocol": "http",
#         "user": "admin"
#     }
# ]
# There is only one compute server where nodes can be run in this example. This
# compute as a special id: local, this is the local server which is embedded in
# the GNS3 controller.
#
# Create a project
# The next step is to create a project:
#
# # curl -X POST "http://localhost:3080/v2/projects" -d '{"name": "test"}'
# {
#     "name": "test",
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
# }
# Create nodes
# Using the project id, it is now possible to create two VPCS nodes:
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes" -d '{"name": "VPCS 1", "node_type": "vpcs", "compute_id": "local"}'
# {
#     "compute_id": "local",
#     "console": 5000,
#     "console_host": "127.0.0.1",
#     "console_type": "telnet",
#     "name": "VPCS 1",
#     "node_id": "f124dec0-830a-451e-a314-be50bbd58a00",
#     "node_type": "vpcs",
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
#     "status": "stopped"
# }
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes" -d '{"name": "VPCS 2", "node_type": "vpcs", "compute_id": "local"}'
# {
#     "compute_id": "local",
#     "console": 5001,
#     "console_host": "127.0.0.1",
#     "console_type": "telnet",
#     "name": "VPCS 2",
#     "node_id": "83892a4d-aea0-4350-8b3e-d0af3713da74",
#     "node_type": "vpcs",
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
#     "properties": {},
#     "status": "stopped"
# }
# Link nodes
# The two VPCS nodes can be linked together using their port number 0 (VPCS has only one network adapter with one port):
#
# # curl -X POST  "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/links" -d '{"nodes": [{"adapter_number": 0, "node_id": "f124dec0-830a-451e-a314-be50bbd58a00", "port_number": 0}, {"adapter_number": 0, "node_id": "83892a4d-aea0-4350-8b3e-d0af3713da74", "port_number": 0}]}'
# {
#     "capture_file_name": null,
#     "capture_file_path": null,
#     "capturing": false,
#     "link_id": "007f2177-6790-4e1b-ac28-41fa226b2a06",
#     "nodes": [
#         {
#             "adapter_number": 0,
#             "node_id": "f124dec0-830a-451e-a314-be50bbd58a00",
#             "port_number": 0
#         },
#         {
#             "adapter_number": 0,
#             "node_id": "83892a4d-aea0-4350-8b3e-d0af3713da74",
#             "port_number": 0
#         }
#     ],
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f"
# }
# Start nodes
# Start the two nodes:
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/f124dec0-830a-451e-a314-be50bbd58a00/start" -d "{}"
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/83892a4d-aea0-4350-8b3e-d0af3713da74/start" -d "{}"
# Connect to nodes
# Use a Telnet client to connect to the nodes once they have been started. The port number can be found in the output when the nodes have been created above.
#
# # telnet 127.0.0.1 5000
# Trying 127.0.0.1...
# Connected to localhost.
# Escape character is '^]'.
#
# Welcome to Virtual PC Simulator, version 0.6
# Dedicated to Daling.
# Build time: Dec 29 2014 12:51:46
# Copyright (c) 2007-2014, Paul Meng (mirnshi@gmail.com)
# All rights reserved.
#
# VPCS is free software, distributed under the terms of the "BSD" licence.
# Source code and license can be found at vpcs.sf.net.
# For more information, please visit wiki.freecode.com.cn.
#
# Press '?' to get help.
#
# VPCS> ip 192.168.1.1
# Checking for duplicate address...
# PC1 : 192.168.1.1 255.255.255.0
#
# VPCS> disconnect
#
# Good-bye
# Connection closed by foreign host.
#
# # telnet 127.0.0.1 5001
# Trying 127.0.0.1...
# Connected to localhost.
# Escape character is '^]'.
#
# Welcome to Virtual PC Simulator, version 0.6
# Dedicated to Daling.
# Build time: Dec 29 2014 12:51:46
# Copyright (c) 2007-2014, Paul Meng (mirnshi@gmail.com)
# All rights reserved.
#
# VPCS is free software, distributed under the terms of the "BSD" licence.
# Source code and license can be found at vpcs.sf.net.
# For more information, please visit wiki.freecode.com.cn.
#
# Press '?' to get help.
#
# VPCS> ip 192.168.1.2
# Checking for duplicate address...
# PC1 : 192.168.1.2 255.255.255.0
#
# VPCS> ping 192.168.1.1
# 84 bytes from 192.168.1.1 icmp_seq=1 ttl=64 time=0.179 ms
# 84 bytes from 192.168.1.1 icmp_seq=2 ttl=64 time=0.218 ms
# 84 bytes from 192.168.1.1 icmp_seq=3 ttl=64 time=0.190 ms
# 84 bytes from 192.168.1.1 icmp_seq=4 ttl=64 time=0.198 ms
# 84 bytes from 192.168.1.1 icmp_seq=5 ttl=64 time=0.185 ms
#
# VPCS> disconnect
# Good-bye
# Connection closed by foreign host.
# Stop nodes
# Stop the two nodes:
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/f124dec0-830a-451e-a314-be50bbd58a00/stop" -d "{}"
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/83892a4d-aea0-4350-8b3e-d0af3713da74/stop" -d "{}"
# Add visual elements
# Visual elements like rectangle, ellipses or images in the form of raw SVG can be added to a project.
#
# This will display a red square in the middle of your canvas:
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/drawings" -d '{"x":0, "y": 12, "svg": "<svg width=\"50\" height=\"50\"><rect width=\"50\" height=\"50\" style=\"fill: #ff0000\"></rect></svg>"}'
# Tip: embed PNG, JPEG etc. images using base64 encoding in the SVG.
#
# Add a packet filter
# Packet filters allow to filter packet on a given link. Here to drop a packet every 5 packets:
#
# Node creation
# There are two ways to add nodes.
#
# Manually by passing all the information required to create a new node.
# Using an appliance template stored on your server.
# Using an appliance template
# List all the available appliance templates:
#
# # curl "http://localhost:3080/v2/appliances"
#
# [
#     {
#         "appliance_id": "5fa8a8ca-0f80-4ac4-8104-2b32c7755443",
#         "category": "guest",
#         "compute_id": "vm",
#         "default_name_format": "{name}-{0}",
#         "name": "MicroCore",
#         "node_type": "qemu",
#         "symbol": ":/symbols/qemu_guest.svg"
#     },
#     {
#         "appliance_id": "9cd59d5a-c70f-4454-8313-6a9e81a8278f",
#         "category": "guest",
#         "compute_id": "vm",
#         "default_name_format": "{name}-{0}",
#         "name": "Chromium",
#         "node_type": "docker",
#         "symbol": ":/symbols/docker_guest.svg"
#     }
# ]
# Use the appliance template and add coordinates to select where the node will be put on the canvas:
#
# # curl -X POST http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/appliances/9cd59d5a-c70f-4454-8313-6a9e81a8278f -d '{"x": 12, "y": 42}'
# Manual creation of a Qemu node
# # curl -X POST http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes -d '{"node_type": "qemu", "compute_id": "local", "name": "Microcore1", "properties": {"hda_disk_image": "linux-microcore-6.4.img", "ram": 256, "qemu_path": "qemu-system-x86_64"}}'
#
# {
#     "command_line": "",
#     "compute_id": "local",
#     "console": 5001,
#     "console_host": "127.0.0.1",
#     "console_type": "telnet",
#     "first_port_name": null,
#     "height": 59,
#     "label": {
#         "rotation": 0,
#         "style": "font-family: TypeWriter;font-size: 10;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
#         "text": "Microcore1",
#         "x": null,
#         "y": -40
#     },
#     "name": "Microcore1",
#     "node_directory": "/Users/noplay/GNS3/projects/untitled/project-files/qemu/9e4eb45b-22f5-450d-8277-2934fbd0aa20",
#     "node_id": "9e4eb45b-22f5-450d-8277-2934fbd0aa20",
#     "node_type": "qemu",
#     "port_name_format": "Ethernet{0}",
#     "port_segment_size": 0,
#     "ports": [
#         {
#             "adapter_number": 0,
#             "data_link_types": {
#                 "Ethernet": "DLT_EN10MB"
#             },
#             "link_type": "ethernet",
#             "name": "Ethernet0",
#             "port_number": 0,
#             "short_name": "e0/0"
#         }
#     ],
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
#     "properties": {
#         "acpi_shutdown": false,
#         "adapter_type": "e1000",
#         "adapters": 1,
#         "boot_priority": "c",
#         "cdrom_image": "",
#         "cdrom_image_md5sum": null,
#         "cpu_throttling": 0,
#         "cpus": 1,
#         "hda_disk_image": "linux-microcore-6.4.img",
#         "hda_disk_image_md5sum": "877419f975c4891c019947ceead5c696",
#         "hda_disk_interface": "ide",
#         "hdb_disk_image": "",
#         "hdb_disk_image_md5sum": null,
#         "hdb_disk_interface": "ide",
#         "hdc_disk_image": "",
#         "hdc_disk_image_md5sum": null,
#         "hdc_disk_interface": "ide",
#         "hdd_disk_image": "",
#         "hdd_disk_image_md5sum": null,
#         "hdd_disk_interface": "ide",
#         "initrd": "",
#         "initrd_md5sum": null,
#         "kernel_command_line": "",
#         "kernel_image": "",
#         "kernel_image_md5sum": null,
#         "legacy_networking": false,
#         "mac_address": "00:af:69:aa:20:00",
#         "options": "",
#         "platform": "x86_64",
#         "process_priority": "low",
#         "qemu_path": "/usr/local/bin/qemu-system-x86_64",
#         "ram": 256,
#         "usage": ""
#     },
#     "status": "stopped",
#     "symbol": ":/symbols/computer.svg",
#     "width": 65,
#     "x": 0,
#     "y": 0,
#     "z": 0
# }
# Manual creation of a Dynamips node
# # curl http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes -d '{"symbol": ":/symbols/router.svg", "name": "R1", "properties": {"platform": "c7200", "nvram": 512, "image": "c7200-adventerprisek9-mz.124-24.T8.image", "ram": 512, "slot3": "PA-GE", "system_id": "FTX0945W0MY", "slot0": "C7200-IO-FE", "slot2": "PA-GE", "slot1": "PA-GE",  "idlepc": "0x606e0538", "startup_config_content": "hostname %h\n"}, "compute_id": "local", "node_type": "dynamips"}'
#
# {
#     "command_line": null,
#     "compute_id": "local",
#     "console": 5002,
#     "console_host": "127.0.0.1",
#     "console_type": "telnet",
#     "first_port_name": null,
#     "height": 45,
#     "label": {
#         "rotation": 0,
#         "style": "font-family: TypeWriter;font-size: 10;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
#         "text": "R1",
#         "x": null,
#         "y": -32
#     },
#     "name": "R1",
#     "node_directory": "/Users/noplay/GNS3/projects/untitled/project-files/dynamips",
#     "node_id": "f7367e7e-804e-48be-9037-284d4d9b059e",
#     "node_type": "dynamips",
#     "port_name_format": "Ethernet{0}",
#     "port_segment_size": 0,
#     "ports": [
#         {
#             "adapter_number": 0,
#             "data_link_types": {
#                 "Ethernet": "DLT_EN10MB"
#             },
#             "link_type": "ethernet",
#             "name": "FastEthernet0/0",
#             "port_number": 0,
#             "short_name": "f0/0"
#         },
#         {
#             "adapter_number": 1,
#             "data_link_types": {
#                 "Ethernet": "DLT_EN10MB"
#             },
#             "link_type": "ethernet",
#             "name": "GigabitEthernet0/0",
#             "port_number": 0,
#             "short_name": "g0/0"
#         },
#         {
#             "adapter_number": 2,
#             "data_link_types": {
#                 "Ethernet": "DLT_EN10MB"
#             },
#             "link_type": "ethernet",
#             "name": "GigabitEthernet1/0",
#             "port_number": 0,
#             "short_name": "g1/0"
#         },
#         {
#             "adapter_number": 3,
#             "data_link_types": {
#                 "Ethernet": "DLT_EN10MB"
#             },
#             "link_type": "ethernet",
#             "name": "GigabitEthernet2/0",
#             "port_number": 0,
#             "short_name": "g2/0"
#         }
#     ],
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
#     "properties": {
#         "auto_delete_disks": false,
#         "aux": null,
#         "clock_divisor": 4,
#         "disk0": 64,
#         "disk1": 0,
#         "dynamips_id": 2,
#         "exec_area": 64,
#         "idlemax": 500,
#         "idlepc": "0x606e0538",
#         "idlesleep": 30,
#         "image": "c7200-adventerprisek9-mz.124-24.T8.image",
#         "image_md5sum": "b89d30823cbbda460364991ed18449c7",
#         "mac_addr": "ca02.dcbb.0000",
#         "midplane": "vxr",
#         "mmap": true,
#         "npe": "npe-400",
#         "nvram": 512,
#         "platform": "c7200",
#         "power_supplies": [
#             1,
#             1
#         ],
#         "private_config": "",
#         "private_config_content": "",
#         "ram": 512,
#         "sensors": [
#             22,
#             22,
#             22,
#             22
#         ],
#         "slot0": "C7200-IO-FE",
#         "slot1": "PA-GE",
#         "slot2": "PA-GE",
#         "slot3": "PA-GE",
#         "slot4": null,
#         "slot5": null,
#         "slot6": null,
#         "sparsemem": true,
#         "startup_config": "configs/i2_startup-config.cfg",
#         "startup_config_content": "!\nhostname R1\n",
#         "system_id": "FTX0945W0MY"
#     },
#     "status": "stopped",
#     "symbol": ":/symbols/router.svg",
#     "width": 66,
#     "x": 0,
#     "y": 0,
#     "z": 0
# }
# Notifications
# Notifications can be seen by connection to the notification feed:
#
# # curl "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/notifications"
# {"action": "ping", "event": {"compute_id": "local", "cpu_usage_percent": 35.7, "memory_usage_percent": 80.7}}
# {"action": "node.updated", "event": {"command_line": "/usr/local/bin/vpcs -p 5001 -m 1 -i 1 -F -R -s 10001 -c 10000 -t 127.0.0.1", "compute_id": "local", "console": 5001, "console_host": "127.0.0.1", "console_type": "telnet", "name": "VPCS 2", "node_id": "83892a4d-aea0-4350-8b3e-d0af3713da74", "node_type": "vpcs", "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f", "properties": {"startup_script": null, "startup_script_path": null}, "status": "started"}}
# A Websocket notification stream is also available on http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/notifications/ws
#
# Read Notifications for more information.
#
# Where to find the endpoints?
# A list of all endpoints is available: Endpoints
#
# Tip: requests made by a client and by a controller to the computes nodes can been seen if the server is started with the –debug parameter.

type(None)

# Controller endpoints
# The controller manages everything, it is the central decision point and has a complete view of your network topologies, what nodes run on which compute server, the links between them etc.
#
# This is the high level API which can be used by users to manually control the GNS3 backend. The controller will call the compute endpoints when needed.
#
# A standard GNS3 setup is to have one controller and one or many computes.
#
# Appliance
# /v2/appliances
# /v2/appliances/templates
# /v2/projects/{project_id}/appliances/{appliance_id}
# Compute
# /v2/computes
# /v2/computes/endpoint/{compute_id}/{emulator}/{action:.+}
# /v2/computes/{compute_id}
# /v2/computes/{compute_id}/auto_idlepc
# /v2/computes/{compute_id}/{emulator}/{action:.+}
# /v2/computes/{compute_id}/{emulator}/images
# Drawing
# /v2/projects/{project_id}/drawings
# /v2/projects/{project_id}/drawings/{drawing_id}
# Gns3 vm
# /v2/gns3vm
# /v2/gns3vm/engines
# /v2/gns3vm/engines/{engine}/vms
# Link
# /v2/projects/{project_id}/links
# /v2/projects/{project_id}/links/{link_id}
# /v2/projects/{project_id}/links/{link_id}/available_filters
# /v2/projects/{project_id}/links/{link_id}/pcap
# /v2/projects/{project_id}/links/{link_id}/start_capture
# /v2/projects/{project_id}/links/{link_id}/stop_capture
# Node
# /v2/projects/{project_id}/nodes
# /v2/projects/{project_id}/nodes/{node_id}
# /v2/projects/{project_id}/nodes/{node_id}/duplicate
# /v2/projects/{project_id}/nodes/{node_id}/dynamips/auto_idlepc
# /v2/projects/{project_id}/nodes/{node_id}/dynamips/idlepc_proposals
# /v2/projects/{project_id}/nodes/{node_id}/files/{path:.+}
# /v2/projects/{project_id}/nodes/{node_id}/links
# /v2/projects/{project_id}/nodes/{node_id}/reload
# /v2/projects/{project_id}/nodes/{node_id}/start
# /v2/projects/{project_id}/nodes/{node_id}/stop
# /v2/projects/{project_id}/nodes/{node_id}/suspend
# /v2/projects/{project_id}/nodes/reload
# /v2/projects/{project_id}/nodes/start
# /v2/projects/{project_id}/nodes/stop
# /v2/projects/{project_id}/nodes/suspend
# Project
# /v2/projects
# /v2/projects/load
# /v2/projects/{project_id}
# /v2/projects/{project_id}/close
# /v2/projects/{project_id}/duplicate
# /v2/projects/{project_id}/export
# /v2/projects/{project_id}/files/{path:.+}
# /v2/projects/{project_id}/import
# /v2/projects/{project_id}/notifications
# /v2/projects/{project_id}/notifications/ws
# /v2/projects/{project_id}/open
# Server
# /v2/debug
# /v2/settings
# /v2/shutdown
# /v2/version
# Snapshot
# /v2/projects/{project_id}/snapshots
# /v2/projects/{project_id}/snapshots/{snapshot_id}
# /v2/projects/{project_id}/snapshots/{snapshot_id}/restore
# Symbol
# /v2/symbols
# /v2/symbols/{symbol_id:.+}/raw
# Compute Endpoints
# A compute is the GNS3 process running on a host. It controls emulators in order to run nodes (e.g. VMware VMs with VMware Workstation, IOS routers with Dynamips etc.)
#
# Warning These endpoints should be considered low level and private. They should only be used by the controller or for debugging purposes.
#     Atm switch
# /v2/compute/projects/{project_id}/atm_relay_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/atm_switch/nodes
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/atm_switch/nodes/{node_id}/suspend
# Capabilities
# /v2/compute/capabilities
# Cloud
# /v2/compute/projects/{project_id}/cloud/nodes
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/cloud/nodes/{node_id}/suspend
# Docker
# /v2/compute/docker/images
# /v2/compute/projects/{project_id}/docker/nodes
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/pause
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/suspend
# /v2/compute/projects/{project_id}/docker/nodes/{node_id}/unpause
# Dynamips vm
# /v2/compute/dynamips/images
# /v2/compute/dynamips/images/{filename:.+}
# /v2/compute/projects/{project_id}/dynamips/nodes
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/auto_idlepc
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/idlepc_proposals
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/resume
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/dynamips/nodes/{node_id}/suspend
# Ethernet hub
# /v2/compute/projects/{project_id}/ethernet_hub/nodes
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/ethernet_hub/nodes/{node_id}/suspend
# Ethernet switch
# /v2/compute/projects/{project_id}/ethernet_switch/nodes
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/ethernet_switch/nodes/{node_id}/suspend
# Frame relay switch
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/frame_relay_switch/nodes/{node_id}/suspend
# Iou
# /v2/compute/iou/images
# /v2/compute/iou/images/{filename:.+}
# /v2/compute/projects/{project_id}/iou/nodes
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/iou/nodes/{node_id}/suspend
# Nat
# /v2/compute/projects/{project_id}/nat/nodes
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/nat/nodes/{node_id}/suspend
# Network
# /v2/compute/network/interfaces
# /v2/compute/projects/{project_id}/ports/udp
# Notification
# /v2/compute/notifications/ws
# Project
# /v2/compute/projects
# /v2/compute/projects/{project_id}
# /v2/compute/projects/{project_id}/close
# /v2/compute/projects/{project_id}/export
# /v2/compute/projects/{project_id}/files
# /v2/compute/projects/{project_id}/files/{path:.+}
# /v2/compute/projects/{project_id}/import
# /v2/compute/projects/{project_id}/notifications
# /v2/compute/projects/{project_id}/stream/{path:.+}
# Qemu
# /v2/compute/projects/{project_id}/qemu/nodes
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/resume
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/qemu/nodes/{node_id}/suspend
# /v2/compute/qemu/binaries
# /v2/compute/qemu/capabilities
# /v2/compute/qemu/images
# /v2/compute/qemu/images/{filename:.+}
# /v2/compute/qemu/img
# /v2/compute/qemu/img-binaries
# Server
# /v2/compute/debug
# /v2/compute/version
# Traceng
# /v2/compute/projects/{project_id}/traceng/nodes
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/traceng/nodes/{node_id}/suspend
# Virtualbox
# /v2/compute/projects/{project_id}/virtualbox/nodes
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/resume
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/virtualbox/nodes/{node_id}/suspend
# /v2/compute/virtualbox/vms
# Vmware
# /v2/compute/projects/{project_id}/vmware/nodes
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/interfaces/vmnet
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/resume
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/vmware/nodes/{node_id}/suspend
# /v2/compute/vmware/vms
# Vpcs
# /v2/compute/projects/{project_id}/vpcs/nodes
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/nio
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/start_capture
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/adapters/{adapter_number:d+}/ports/{port_number:d+}/stop_capture
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/duplicate
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/reload
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/start
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/stop
# /v2/compute/projects/{project_id}/vpcs/nodes/{node_id}/suspend

type(None)


def main():

    project_id = '389dde3d-08ac-447b-8d54-b053a3f6ed19'  # scritp-test.gns3
    # curl "http://192.168.139.128:3080/v2/computes"
    vm = Gns3('192.168.139.128')
    print("\nGNS3 VM: ")
    # print(vm)
    # pprint(vm.version)
    # pprint(vm.computes)
    # pprint(vm.projects)

    pc = Gns3('192.168.139.1')
    # print("\nGNS3 PC: ")
    # print(pc)
    # pprint(pc.version)
    # pprint(pc.computes)
    # pprint(pc.projects)
    nodes = ('10.0.10.1', '10.0.10.2', '10.0.10.3')
    new_hub = set_hub()
    # breakpoint()
    pprint(pc.nodes(project_id=project_id, new=new_hub))
    # for nodeip in nodes:
    #     new_node = set_node(nodeip, '24')
    #     pprint(pc.nodes(project_id=project_id, new=new_node))

# curl -X POST 192.168.139.1:3080/v2/projects/389dde3d-08ac-447b-8d54-b053a3f6ed19/nodes -d '{"name": "VPCS 1", "node_type": "vpcs", "compute_id": "vm"}'

if __name__ == '__main__':
    main()

"""
host model
    {
        "compute_id": "vm",
        "console": 5001,
        "console_type": "telnet",
        "first_port_name": null,
        "height": 59,
        "label": {
            "rotation": 0,
            "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
            "text": "[x]",
            "x": 19,
            "y": -25
        },
        "name": "[x]",
        "node_id": "1c867306-7db3-4368-bc26-a76ec61451fe",
        "node_type": "vpcs",
        "port_name_format": "Ethernet{0}",
        "port_segment_size": 0,
        "properties": {
            "startup_script": "set pcname \\[x\\]\nip 10.0.30.1 10.0.30.100 24\n",
            "startup_script_path": "startup.vpc"
        },
        "symbol": ":/symbols/vpcs_guest.svg",
        "width": 65,
        "x": -257,
        "y": -254,
        "z": 1
    },
    

HUB model
{
    "compute_id": "vm",
    "console": null,
    "console_type": null,
    "first_port_name": null,
    "height": 32,
    "label": {
        "rotation": 0,
        "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
        "text": "SW-HUB",
        "x": 14,
        "y": -24
    },
    "name": "SW-HUB",
    "node_id": "3c59e645-08af-4d77-90b9-1c212f67929f",
    "node_type": "ethernet_switch",
    "port_name_format": "Ethernet{0}",
    "port_segment_size": 0,
    "properties": {
        "ports_mapping": [
            {
                "name": "Ethernet0",
                "port_number": 0,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet1",
                "port_number": 1,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet2",
                "port_number": 2,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet3",
                "port_number": 3,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet4",
                "port_number": 4,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet5",
                "port_number": 5,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet6",
                "port_number": 6,
                "type": "access",
                "vlan": 1
            },
            {
                "name": "Ethernet7",
                "port_number": 7,
                "type": "access",
                "vlan": 1
            }
        ]
    },
    "symbol": ":/symbols/ethernet_switch.svg",
    "width": 72,
    "x": 114,
    "y": 134,
    "z": 1
},
"""
