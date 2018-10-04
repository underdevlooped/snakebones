# -*- coding: utf-8 -*-
"""
Created on Thu May  3 21:24:09 2018

@author: Andre Kern

Funcoes de suporte para a criacao da skeleton tree
"""
import subprocess, pdb
from time import sleep
from scapy.all import *
from easysnmp import Session
from easysnmp.exceptions import (
    EasySNMPTimeoutError, EasySNMPConnectionError,
    EasySNMPUnknownObjectIDError)
from ipaddress import IPv4Interface  # , IPv4Network
from netaddr import EUI
from netaddr.strategy.eui48 import mac_cisco, mac_unix_expanded
# from scapy.sendrecv import srp
# from scapy.layers.l2 import Ether, ARP
# from scapy.config import conf
from typing import Union, Tuple, List, Dict, Optional

# Tuple, List, Callable, Any
# from snakebones import InternalNode, Node, LeafNode

ArpTable = List[Tuple[IPv4Interface, EUI]]

# =============================================================================
# from netaddr.strategy.eui48 import (mac_eui48, mac_unix, mac_unix_expanded,
#        mac_cisco, mac_bare, mac_pgsql, valid_str as valid_mac)
#
# from typing import Dict, Tuple, List
#
# ConnectionOptions = Dict[str, str]
# Address = Tuple[str, int]
# Server = Tuple[Address, ConnectionOptions]
# =============================================================================


# =============================================================================
# from netaddr import *
# from scapy.sendrecv import send,srp,sr1,sr
# from scapy.layers.inet import IP,ICMP
# from scapy.layers.l2 import Ether,ARP
# from scapy.config import conf
# =============================================================================


# %% Constantes
YES = ON = START = True
NO = OFF = STOP = False


# %% SNMP_DATA
def auto_snmp_data(complete_aft=True) -> dict:
    """Retorna dicionario com os dados snmp (sem probe) dos internal nodes
    no formato {'ip/masc':{'atributo1': 'valor1', 'atributo2': 'valor2', ...}

    :return: dict
    """
    snmp_data = \
        {'10.0.0.1/24': {'sys_name': 'v1',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('2', 'Gi0/1'),
                             ('3', 'Gi0/2'),
                             ('5', 'Gi1/0'),
                             ('6', 'Gi1/1'),
                             ('7', 'Gi1/2'),
                             ('8', 'Gi1/3'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             #b"\x00\x0c);'\x1e",  # 10.0.*.111/24 000c.293b.271e
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c',  # 10.0.10.1/24 0050.7966.680c
                             b'\xc4\x01\x08\x83\x00\x01',
                             b'\xc4\x01\x08\x83\x00\x10',
                             b'\xc4\x01\x08\x83\x00 ',
                             b'\xc4\x01\x08\x83\x000'
                         ],
                         'dot1d_tp_fdb_port': [
                             '1',
                             '3',
                             '3',
                             '3',
                             '3',
                             '2',
                             '2',
                             '16',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '2',
                             '15',
                             '5',
                             '6',
                             '7',
                             '8'
                         ]
                         },
         '10.0.0.2/24': {'sys_name': 'v2',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('2', 'Gi0/1'),
                             ('3', 'Gi0/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\n'  # 10.0.10.4/24 0050.7966.680a
                         ],
                         'dot1d_tp_fdb_port': [
                             '1',
                             '3',
                             '2',
                             '3',
                             '2',
                             '2',
                             '16',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3'
                         ]
                        },
         '10.0.0.3/24': {'sys_name': 'v3',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('2', 'Gi0/1'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\n'  # 10.0.10.4/24 0050.7966.680a
                         ],
                         'dot1d_tp_fdb_port': ['1', '2', '16', '2', '2', '2', '2', '2']},
         '10.0.0.4/24': {'sys_name': 'v4',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                         ],
                         'dot1d_tp_fdb_port': ['1', '15', '16']
                        },
         '10.0.0.5/24': {'sys_name': 'v5',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\n'  # 10.0.10.4/24 0050.7966.680a
                         ],
                         'dot1d_tp_fdb_port': ['1', '15', '16']},
         '10.0.0.6/24': {'sys_name': 'v6',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             b'\x00\x0c)\\Bq',  # 10.0.*.111/24 000c.295c.4271
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x0b'  # 10.0.30.2/24 0050.7966.680b
                         ],
                         'dot1d_tp_fdb_port': ['1', '15', '16']
                        }
         }

    snmp_data_full = \
        {'10.0.0.1/24': {'sys_name': 'v1',
                         'port_activelist': [
                             # ('1', 'Gi0/0'),  # NMS
                             ('2', 'Gi0/1'),
                             ('3', 'Gi0/2'),
                             ('5', 'Gi1/0'),
                             ('6', 'Gi1/1'),
                             ('7', 'Gi1/2'),
                             ('8', 'Gi1/3'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c',  # 10.0.10.1/24 0050.7966.680c
                             b'\xc4\x01\x08\x83\x00\x01',
                             b'\xc4\x01\x08\x83\x00\x10',
                             b'\xc4\x01\x08\x83\x00 ',
                             b'\xc4\x01\x08\x83\x000'
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '3',
                             '3',
                             '3',
                             '3',
                             '2',
                             '2',
                             '16',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '3',
                             '2',
                             '15',
                             '5',
                             '6',
                             '7',
                             '8'
                         ]
                         },
         '10.0.0.2/24': {'sys_name': 'v2',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('2', 'Gi0/1'),
                             ('3', 'Gi0/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x01\x80\x01',  # 10.0.0.1/24 003e.5c01.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c'  # 10.0.10.1/24 0050.7966.680c
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '1',
                             '3',
                             '2',
                             '3',
                             '1',
                             '3',
                             '3',
                             '1',
                             '1',
                             '2',
                             '2',
                             '16',
                             '3',
                             '3',
                             '3',
                             '3',
                             '1',
                             '1'
                         ]
                        },
         '10.0.0.3/24': {'sys_name': 'v3',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('2', 'Gi0/1'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x01\x80\x01',  # 10.0.0.1/24 003e.5c01.8001
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c'  # 10.0.10.1/24 0050.7966.680c
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '1',
                             '1',
                             '1',
                             '2',
                             '1',
                             '2',
                             '2',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '16',
                             '2',
                             '2',
                             '2',
                             '1',
                             '1'
                         ]},
         '10.0.0.4/24': {'sys_name': 'v4',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')
                         ],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x01\x80\x01',  # 10.0.0.1/24 003e.5c01.8001
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c'  # 10.0.10.1/24 0050.7966.680c
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '15',
                             '16',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1'
                         ]
                        },
         '10.0.0.5/24': {'sys_name': 'v5',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x01\x80\x01',  # 10.0.0.1/24 003e.5c01.8001
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x06\x80\x01',  # 10.0.0.6/24 003e.5c06.8001
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c'  # 10.0.10.1/24 0050.7966.680c
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '16',
                             '15',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1'
                         ]},
         '10.0.0.6/24': {'sys_name': 'v6',
                         'port_activelist': [
                             ('1', 'Gi0/0'),
                             ('15', 'Gi3/2'),
                             ('16', 'Gi3/3')],
                         'dot1d_base_num_ports': '16',
                         'dot1_base_type': '2',
                         'dot1d_tp_fdb_address': [
                             # b'\x00\x0c)\\Bq',  # NMS 10.0.*.111/24 000c.295c.4271
                             b'\x00>\\\x01\x80\x01',  # 10.0.0.1/24 003e.5c01.8001
                             b'\x00>\\\x02\x80\x01',  # 10.0.0.2/24 003e.5c02.8001
                             b'\x00>\\\x03\x80\x01',  # 10.0.0.3/24 003e.5c03.8001
                             b'\x00>\\\x04\x80\x01',  # 10.0.0.4/24 003e.5c04.8001
                             b'\x00>\\\x05\x80\x01',  # 10.0.0.5/24 003e.5c05.8001
                             b'\x00Pyfh\n',  # 10.0.10.4/24 0050.7966.680a
                             b'\x00Pyfh\t',  # 10.0.10.3/24 0050.7966.6809
                             b'\x00Pyfh\x00',  # 10.0.30.1/24 0050.7966.6800
                             b'\x00Pyfh\x01',  # 10.0.30.3/24 0050.7966.6801
                             b'\x00Pyfh\x02',  # 10.0.20.1/24 0050.7966.6802
                             b'\x00Pyfh\x03',  # 10.0.20.2/24 0050.7966.6803
                             b'\x00Pyfh\x04',  # 10.0.20.3/24 0050.7966.6804
                             b'\x00Pyfh\x05',  # 10.0.10.2/24 0050.7966.6805
                             b'\x00Pyfh\x06',  # 10.0.20.4/24 0050.7966.6806
                             b'\x00Pyfh\x07',  # 10.0.10.6/24 0050.7966.6807
                             b'\x00Pyfh\x08',  # 10.0.10.5/24 0050.7966.6808
                             b'\x00Pyfh\x0b',  # 10.0.30.2/24 0050.7966.680b
                             b'\x00Pyfh\x0c'  # 10.0.10.1/24 0050.7966.680c
                         ],
                         'dot1d_tp_fdb_port': [
                             # '1',  # NMS
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '15',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '1',
                             '16',
                             '1'
                         ]
                        }
         }

    if complete_aft:
        return snmp_data_full

    return snmp_data


# %% ARP_TABLE_DATA
def auto_arp_table_data() -> dict:
    """
    Retorna dicionario com interface IP do elemento e sua tabela arp
    lista de objetos (IPv4Inteface, EUI)
    :rtype: dict
    """
    arp_table_data = \
        {'10.0.0.0/24':[
            # (IPv4Interface('10.0.0.111/24'), EUI('000c.295c.4271')),
            (IPv4Interface('10.0.0.1/24'), EUI('003e.5c01.8001')),
            (IPv4Interface('10.0.0.2/24'), EUI('003e.5c02.8001')),
            (IPv4Interface('10.0.0.3/24'), EUI('003e.5c03.8001')),
            (IPv4Interface('10.0.0.4/24'), EUI('003e.5c04.8001')),
            (IPv4Interface('10.0.0.5/24'), EUI('003e.5c05.8001')),
            (IPv4Interface('10.0.0.6/24'), EUI('003e.5c06.8001'))
            ],
         '10.0.10.0/24':
             [
              # (IPv4Interface('10.0.10.111/24'), EUI('000c.295c.4271')),
              (IPv4Interface('10.0.10.1/24'), EUI('0050.7966.680c')),
              (IPv4Interface('10.0.10.2/24'), EUI('0050.7966.6805')),
              (IPv4Interface('10.0.10.3/24'), EUI('0050.7966.6809')),
              (IPv4Interface('10.0.10.4/24'), EUI('0050.7966.680a')),
              (IPv4Interface('10.0.10.5/24'), EUI('0050.7966.6808')),
              (IPv4Interface('10.0.10.6/24'), EUI('0050.7966.6807'))],
         '10.0.20.0/24':
             [
              # (IPv4Interface('10.0.20.111/24'), EUI('000c.295c.4271')),
              (IPv4Interface('10.0.20.1/24'), EUI('0050.7966.6802')),
              (IPv4Interface('10.0.20.2/24'), EUI('0050.7966.6803')),
              (IPv4Interface('10.0.20.3/24'), EUI('0050.7966.6804')),
              (IPv4Interface('10.0.20.4/24'), EUI('0050.7966.6806'))],
         '10.0.30.0/24':
             [
              # (IPv4Interface('10.0.30.111/24'), EUI('000c.295c.4271')),
              (IPv4Interface('10.0.30.1/24'), EUI('0050.7966.6800')),
              (IPv4Interface('10.0.30.2/24'), EUI('0050.7966.680b')),
              (IPv4Interface('10.0.30.3/24'), EUI('0050.7966.6801'))]}
    for key, value in arp_table_data.items():
        for ip_addres, mac_address in value:
            mac_address.dialect = mac_cisco
    return arp_table_data


ARP_TABLE_DATA = auto_arp_table_data()


# %% funcao update_arp_table
def set_arp_table(subnet: str,
                  probes: int = 1,
                  auto_fill: Optional[bool] = None,
                  manual_fill: Optional[List[Tuple[str,str]]] = None,
                  post: Optional[bool] = None,
                  include_me: Optional[bool] = None)\
        -> List[Tuple[IPv4Interface, EUI]]:
    """
    Envia pacotes ARP em broadcast p/ atualizar a tabela MAC dos elementos
    Retorna tupla para cada rede fornecida contendo lista de IPs, de MACs e
    total de elementos
        - Usa Rede fornecida [subnet.address] como destino de quadros L2.
    auto_fill:
        Usado para atribuir automaticamente arp_table
    manual_fill:
        Entrada manual de falores sem coleta SNMP no formato (IP, MAC):
            >>> [(IPv4Interface('10.0.0.1'), EUI('003e.5c01.8001')), ...]
    post:
        False
            não apresenta detalhes na tela
        True
            apresenta detalhes na tela

    Exemplo:
    ____
        >>> rede1 = SubNet('10.0.0.0/24')
        >>> rede1.update_arp_table()
        >>> rede1.update_arp_table(manual_fill=
                              [('10.0.0.1', '003e.5c01.8001'),
                               ('10.0.0.2', '003e.5c02.8001'),
                               ('10.0.0.3', '003e.5c03.8001'),
                               ('10.0.0.4', '003e.5c04.8001'),
                               ('10.0.0.5', '003e.5c05.8001'),
                               ('10.0.0.6', '003e.5c06.8001')])
    :param subnet: Rede a ter elementos rastreados
    :param probes: quantidade de quadros para cada elemento destino
    :param auto_fill: atribuido automaticamente da constante ARP_TABLE_DATA
    :param manual_fill: tuplas de (ip: str, mac: str)
    :param post: imprime etapas na tela
    :param include_me: True para incluir o NMS na arp table
    :return: Lista com tupla (IPv4Interface, EUI) dos elementos identificados
    :rtype: List[Tupla[IPv4Interface, EUI]]
    """
    if manual_fill:
        print('Valores da Tabela ARP atribuidos manualmente')
        return ip_mac_to_arp_table(manual_fill, subnet.prefixlen)
    if auto_fill:
        print('Valores da Tabela ARP atribuidos automaticamente')
        return ARP_TABLE_DATA.get(subnet.compressed)
    if post:
        print()
        print(f'===> Iniciando descoberta da rede {subnet.with_prefixlen}')
    for _ in range(probes):
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") /
                     ARP(pdst=subnet.address),
                     timeout=4)

        ip_list, mac_list = [], []
        # TODO função set_arp_table: testar
        if include_me:
            for ip in get_myip():
                if ip in subnet:
                    ip_list.append(ip)
            mac_list.append(get_mymac())
            mac_list[-1].dialect = mac_cisco

        for _, recebe in ans:
            ip_list.append(
                    IPv4Interface(recebe[0][1].summary().split()[5]
                                  + '/'
                                  + str(subnet.prefixlen))
            )
            mac_list.append(
                    EUI(
                            recebe[0][1].summary().split()[3].replace(':', '')
                    )
            )
            mac_list[-1].dialect = mac_cisco
        if post:
            print(f'Tabela ARP para a rede {subnet.address!r}:')
            for node in range(len(ip_list)):
                print(f'IP: {ip_list[node]}, MAC: {mac_list[node]}')

        arp_table_list = sorted(list(zip(ip_list, mac_list)))
        if not arp_table_list:
            return f'Tabela ARP nao definida para rede {subnet.address!r}'
        else:
            if post:
                print(f'Tabela ARP definida para rede {subnet.address!r}; '
                      f'Total de nodes: {str(len(arp_table_list))!r}')
            return arp_table_list


# %% funcao get_mymac
def get_mymac(interface: str = 'ens33', vendor: str = 'unix') -> EUI:
    """
    Retorna objeto EUI com endereco MAC da estacao onde a funcao e chamada

    :param interface: string com o nome da interface do computador NMS
    :param vendor:  cisco ou unix
    :return: EUI
    """
    vendor_list = {'cisco': mac_cisco, 'unix': mac_unix_expanded}
    ls_net = subprocess.run('ls -l /sys/class/net/'.split(),
                            stdout=subprocess.PIPE,
                            universal_newlines=True).stdout
    if interface not in ls_net:
        while True:
            interface = input(ls_net + '\nEntre nome da inteface: ')
            if interface not in ls_net:
                print('\n## Interface nao identificada ##\nConsulte lista: ')
            else:
                break

    mymac = subprocess.run(
            ('cat /sys/class/net/' + interface + '/address').split(),
            stdout=subprocess.PIPE,
            universal_newlines=True)
    mymac = EUI(mymac.stdout.strip('\n'))
    mymac.dialect = vendor_list.get(str.lower(vendor))
    return mymac


# %% funcao get_myip
def get_myip() -> List[IPv4Interface]:
    """
    Retorna lista com objetos IPv4Interface dos enderecos IPs da estacao onde
    a funcao e chamada

    :return: List[IPv4Interface]
    """
    output = subprocess.run(
            "ifconfig".split(),
            stdout=subprocess.PIPE,
            universal_newlines=True)
    output = output.stdout.split('\n')
    my_ips = []
    for line in output:
        if 'inet ' in line and "127.0.0." not in line:
            line = line.strip().split()
            my_ips.append((line[1], line[3]))
    return [IPv4Interface(ip + '/' + mask) for ip, mask in my_ips]


# %% ping icmp
def ping_ip(ip_address: str,
            repete: int = 3,
            espera: int = 1,
            tamanho: int = 1) -> str:
    """
    Executa um comando de PING para teste de conectividade ICMP.

    Imprime resultado na tela e Retorna str com estatistica.

    ip_address = Endereco IP de destino no formato '0.0.0.0':
    ----
    Usa o IP fornecido como destino para o ICMP-request

    Exemplos:
    ----
    >>> ping_ip('10.0.0.1')

    >>> ping_ip('10.0.0.1', repete=2, espera=2, tamanho=2)
    """
    print(f'===> Iniciando ping ICMP para IP {ip_address}')
    comando = ['ping', '-s', str(tamanho),
               '-c', str(repete),
               '-W', str(espera),
               ip_address]
    pong = subprocess.run(comando,
                          stdout=subprocess.PIPE,
                          universal_newlines=True)
    if not pong.stdout:
        return f'Falha ao iniciar PING para {ip_address!r}'
    else:
        print(pong.stdout)
        resultado = pong.stdout.split(sep='\n')[-3]
    return f"PING para {ip_address!r}: {resultado}"


# %% funcao ip_mac_to_arp_table
def ip_mac_to_arp_table(ip_mac_list: List[Tuple[str, str]],
                        net_prefix: Union[str, int]) -> ArpTable:
    """
    Converte lista de pares (IP, MAC) em (IPv4Interface, EUI)

    :param ip_mac_list:
        lista de ip e mac com prefixo de mascara de rede
    :param net_prefix:
        lista
    :return:
        lista com objetos IPv4Interface, EUI
    Exemplo
    ----
    >>> ip_mac_to_arp_table([
            ('10.0.0.1', '003e5c018001'),
            ('10.0.0.2', '003e5c018002')
            ],
            24)
    """
    ip_list, mac_list = [], []
    for ip, mac in ip_mac_list:
        ip_list.append(IPv4Interface(ip + '/' + str(net_prefix)))
        mac.replace('.', '').replace(':', '').replace('-', '')
        mac_list.append(EUI(mac))
        mac_list[-1].dialect = mac_cisco
    return sorted(list(zip(ip_list, mac_list)))


# %% map function
def map_func_list(funcao, lista):
    """
    Retorna a lista de entrada com funcao aplicada para cada elemento

    :param funcao:
    :param lista:
    :return: List
    """
    return [funcao(elemento) for elemento in lista]


def map_func_dict(funcao, dicionario):
    """
    Retorna o dicionario de entrada com funcao aplicada para cada valor
    :param funcao:
    :param dicionario:
    :return: Dict
    """
    return {key: funcao(valor) for key, valor in dicionario.itens()}


# %% to bytes
def to_bytes(x: Union[int, bytes, str]) -> bytes:
    """
    Converte argumento de entrada em bytes

    Exemplo:
    ----
        >>> to_bytes(10)
        ... b'10'

        >>> to_bytes('exemplo')
        ... b'exemplo'

        >>> type(to_bytes('exemplo'))
        ... bytes

        >>> to_bytes(b'em bytes')
        ... b'em bytes'
    """
    if type(x) is bytes:
        return x
    if type(x) is str:
        return bytes([ord(i) for i in x])
    return to_bytes(str(x))


# %% mac functions
def macstr_tobytes(mac: Union[bytes, str]) -> bytes:
    """
    Converte string de endereco MAC para bytes
    :param mac:
    :return:
    """
    if type(mac) is bytes:
        return mac
    if type(mac) is str:
        return int(mac, 16).to_bytes(6, 'big')
    return macstr_tobytes(str(mac))


# %% subprocess nms_config
def nms_config(mode: bool = START) -> None:
    """
    Define IP, mascara de cada interface do terminal para atuar como NMS


    mode = True (1):
    ----
    Configura NMS com IP e mascara
        ens33:0 10.0.0.111 netmask 255.255.255.0

        ens33:10 10.0.10.111 netmask 255.255.255.0

        ens33:20 10.0.20.111 netmask 255.255.255.0

        ens33:30 10.0.30.111 netmask 255.255.255.0

    mode = outro:
    ----
    desconfigura NMS, removendo IP, rota default, desativa e ativa novamente a
    interface

    Exemplo:
    ----
        - inicia configuracao do NMS:
        >>> nms_config()
        >>> nms_config(True)

        - para NMS e remove configuracao:
        >>> nms_config(False)
        >>> nms_config(STOP)
    """
    if mode:
        print('Iniciando configuracao das Interfaces do NMS...')
        ifconfig = subprocess.run(['ifconfig'],
                                  stdout=subprocess.PIPE,
                                  universal_newlines=True)
        route_table = subprocess.run('route -n'.split(),
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)
        print('Configurando inteface ens33:0...')
        sleep(1.5)
        while 'inet 10.0.0.111' not in ifconfig.stdout \
                and '10.0.0.0' not in route_table.stdout:
            subprocess.run('sudo ifconfig ens33:0 10.0.0.111 \
                           netmask 255.255.255.0'.split(),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
            ifconfig = subprocess.run(['ifconfig'],
                                      stdout=subprocess.PIPE,
                                      universal_newlines=True)
            route_table = subprocess.run('route -n'.split(),
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True)
            conf.route.resync()
        print('Configurando inteface ens33:10...')
        sleep(1.5)
        while 'inet 10.0.10.111' not in ifconfig.stdout \
                and '10.0.10.0' not in route_table.stdout:
            subprocess.run('sudo ifconfig ens33:10 10.0.10.111 \
                           netmask 255.255.255.0'.split(),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
            ifconfig = subprocess.run(['ifconfig'],
                                      stdout=subprocess.PIPE,
                                      universal_newlines=True)
            route_table = subprocess.run('route -n'.split(),
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True)
            conf.route.resync()
        print('Configurando inteface ens33:20...')
        sleep(1.5)
        while 'inet 10.0.20.111' not in ifconfig.stdout \
                and '10.0.20.0' not in route_table.stdout:
            subprocess.run('sudo ifconfig ens33:20 10.0.20.111 \
                           netmask 255.255.255.0'.split(),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
            ifconfig = subprocess.run(['ifconfig'],
                                      stdout=subprocess.PIPE,
                                      universal_newlines=True)
            route_table = subprocess.run('route -n'.split(),
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True)
            conf.route.resync()
        print('Configurando inteface ens33:30...')
        sleep(1.5)
        while 'inet 10.0.30.111' not in ifconfig.stdout \
                and '10.0.30.0' not in route_table.stdout:
            subprocess.run('sudo ifconfig ens33:30 10.0.30.111 \
                           netmask 255.255.255.0'.split(),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
            ifconfig = subprocess.run(['ifconfig'],
                                      stdout=subprocess.PIPE,
                                      universal_newlines=True)
            route_table = subprocess.run('route -n'.split(),
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True)
            conf.route.resync()
        return print('Configuracao do NMS concluida.')

    else:
        print('Desconfigurando inteface ens33...')
        subprocess.run('sudo ifconfig ens33 0'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Desativando inteface ens33:0...')
        subprocess.run('sudo ifconfig ens33:0 down'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Desativando inteface ens33:10...')
        subprocess.run('sudo ifconfig ens33:10 down'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Desativando inteface ens33:20...')
        subprocess.run('sudo ifconfig ens33:20 down'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Desativando inteface ens33:30...')
        subprocess.run('sudo ifconfig ens33:30 down'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Desativando inteface ens33...')
        subprocess.run('sudo ifconfig ens33 down'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        print('Configuracao da inteface ens33 foi removida.')
        print('Reativando inteface ens33...')
        subprocess.run('sudo ifconfig ens33 up'.split(),
                       stdout=subprocess.PIPE,
                       universal_newlines=True)
        conf.route.resync()
        print('Pronto.')


# %% test_snmp
# =============================================================================
# By sending appropriate SNMP queries to each detected element,
# the NMS infers the element type and if it has additional
# addresses (e.g., switches or routers).
# =============================================================================

def is_internal_node(node: str) -> bool:
    """
    Enviando as solicitacoes apropriadas para node verificando se eh
    switch ou bridge (internal node) com gerenciamento SNMP
    """
    snmp = Session(hostname=node,
                   version=2,
                   community='public')
    try:
        snmp.get_next('1.3.6.1.2.1.17')
    except (EasySNMPTimeoutError, EasySNMPUnknownObjectIDError) as err:
        print(f'Node {node} SNMP bridge error, {err}')
        return False
    else:
        print('SNMP bridge: OK.')
        return True


def is_leaf_node(node: str) -> bool:
    """
    Enviando as solicitacoes apropriadas para node verificando se NAO eh
    switch ou bridge (leaf node) sem gerenciamento SNMP
    """
    return not is_internal_node(node)

# %% snmp gets draft
# def get_snmp(node):
#    snmp = Session(hostname=node.ip.compressed,
#                   version=2,
#                   community='public')
#    print(repr(snmp))
#
#            sysname = snmp.get('sysName.0').value
#            ifnumber = snmp.get('ifNumber.0').value
#            ifindex = []
#            ifdescr = []
#            ifphysaddess = []
#            ifadminstatus = []
#            ifoperstatus = []
#
#            for index in range(1, int(ifnumber) + 1):
#                snmp.get('ifIndex.' + str(index)).value
#                ifindex.append(index)
#                ifdescr.append(snmp.get('ifDescr.' + str(index)).value)
#                ifphysaddess.append(
#                        to_bytes(snmp.get('ifPhysAddress.' + str(index)).value).hex()
#                        )
#                ifadminstatus.append(snmp.get('ifAdminStatus.' + str(index)).value)
#                ifoperstatus.append(snmp.get('ifOperStatus.' + str(index)).value)
#
#            atIfIndex = 'mib-2.3.1.1.1'  # Obsoleto
#            next_oid = snmp.get_next(atIfIndex).oid
#            atifindex = {}
#            while atIfIndex in next_oid:
#                interface = next_oid.split(sep='.', maxsplit=7)[5]
#                ip_naint = []
#                while atIfIndex+'.'+interface in next_oid:
#                    ip_naint.append(next_oid.split(sep='.', maxsplit=7)[-1])
#                    #         if_e_ip = next_oid.split(sep=atIfIndex)[-1]
#                    #         interface = if_e_ip.rsplit(sep='.')[0]
#                    #         ip_naint = if_e_ip.split(sep='.', maxsplit=2)[-1]
#                    atifindex[int(interface)] = ip_naint
#                    next_oid = snmp.get_next(next_oid).oid
#                print(f'Interface index: {interface}, IP: {ip_naint}')
#            print()
#
#            dot1dBaseNumPorts = 'mib-2.17.1.2'
#            dot1dbasenumports = snmp.get_next(dot1dBaseNumPorts).value
#
#            dot1BaseType = 'mib-2.17.1.3'
#            dot1basetype = snmp.get_next(dot1BaseType).value
#
#        #    dot1dStpPort = 'mib-2.17.2.15.1.1'
#        #    dot1dstpport = snmp.get_next(dot1dStpPort).value
#        #    next_oid = snmp.get_next(dot1dStpPort).oid
#        #    while dot1dStpPort in next_oid:
#        #        stp_porta_ativa = next_oid.rsplit(sep='.', maxsplit=1)[-1]
#        #        #         if_e_ip = next_oid.split(sep=atIfIndex)[-1]
#        #        #         interface = if_e_ip.rsplit(sep='.')[0]
#        #        #         ip_naint = if_e_ip.split(sep='.', maxsplit=2)[-1]
#        #        print(f'STP Interface index: {stp_porta_ativa}')
#        #        next_oid = snmp.get_next(next_oid).oid
#
#            dot1dStpPort = 'mib-2.17.2.15.1.1'
#            resposta_snmp = snmp.get_next(dot1dStpPort)
#            while dot1dStpPort in resposta_snmp.oid:
#                stp_porta_ativa = resposta_snmp.oid.rsplit(sep='.', maxsplit=1)[-1]
#        #        if_e_ip = next_oid.split(sep=atIfIndex)[-1]
#        #        interface = if_e_ip.rsplit(sep='.')[0]
#        #        ip_naint = if_e_ip.split(sep='.', maxsplit=2)[-1]
#                print(f'STP Interface index: {stp_porta_ativa}')
#                resposta_snmp = snmp.get_next(resposta_snmp.oid)
#            print()
#
#            dot1dTpFdbAddress = 'mib-2.17.4.3.1.1'
#            mac_list = []
#            dot1d_tp_fdb_address = mac_list
#            resposta_snmp = snmp.get_next(dot1dTpFdbAddress)
#            while dot1dTpFdbAddress in resposta_snmp.oid:
#                mac_list.append(to_bytes(resposta_snmp.value))
#                print(f'MACs: {dot1d_tp_fdb_address[-1].hex()}')
#                resposta_snmp = snmp.get_next(resposta_snmp.oid)
#            print()
#
#            dot1dTpFdbPort = 'mib-2.17.4.3.1.2'
#            dot1d_tp_fdb_port = []
#        #    <SNMPVariable value='1' (oid='mib-2.17.4.3.1.2.0.12.41.59.39.30',
#        #                             oid_index='',
#        #                             snmp_type='INTEGER')>
#            resposta_snmp = snmp.get_next(dot1dTpFdbPort)
#            while dot1dTpFdbPort in resposta_snmp.oid:
#                dot1d_tp_fdb_port.append(resposta_snmp.value)
#                print(f'Porta: {resposta_snmp.value}')
#                resposta_snmp = snmp.get_next(resposta_snmp.oid)
#            print()
#
#            ifName = 'ifName'  # 'mib-2.31.1.1.1.1'
#            if_name = []
#        #    <SNMPVariable value='Gi0/0' (oid='ifName',
#        #                                 oid_index='1',
#        #                                 snmp_type='OCTETSTR')>
#            resposta_snmp = snmp.get_next(ifName)
#            while ifName in resposta_snmp.oid+'.'+resposta_snmp.oid_index:
#                if_name.append(resposta_snmp.value)
#                print(f'Nome da porta: {resposta_snmp.value}')
#                resposta_snmp = snmp.get_next(resposta_snmp.oid
#                                              + '.'
#                                              + resposta_snmp.oid_index)
#            print()
#
#            ifAlias = 'ifAlias'  # 'mib-2.31.1.1.1.18'
#            if_alias = []
#        #    <SNMPVariable value='v6 | Gi0/0' (oid='ifAlias',
#        #                                      oid_index='2',
#        #                                      snmp_type='OCTETSTR')>
#            resposta_snmp = snmp.get_next(ifAlias)
#            while ifAlias in resposta_snmp.oid+'.'+resposta_snmp.oid_index:
#                if_alias.append(resposta_snmp.value)
#                print(f'Description da porta: {resposta_snmp.value}')
#                resposta_snmp = snmp.get_next(resposta_snmp.oid
#                                              + '.'
#                                              + resposta_snmp.oid_index)
#            print()
#
#            print(f'Hostname: {sysname}')
#            print(f'Num de interfaces: {ifnumber}')
#            print(f'Interface Index: {ifindex}')
#            print(f'Interface Nomes: {ifdescr}')
#            print(f'Interface PhyAdd: {ifphysaddess}')
#            print(f'Interface Admin Status: {ifadminstatus}')
#            print(f'Interface Oper Status: {ifoperstatus}')
#            print(f'Total de interfaces em bridge: {dot1dbasenumports}')
#            print(f'Tipo de bridge (2 = apenas \'transparente\'): {dot1basetype}')


# %% scapy functions
#    executar como super-user (sudo) para gerar pacotes
# https://phaethon.github.io/scapy/api/usage.html
# sr1              : Send packets at layer 3 and return only the first answer
# srp1             : Send and rcv pkt layer 2 and return only the 1st answer
# sniff            : Sniff packets
# arping           : Send ARP who-has requests to determine which hosts are up

# >>> conf.route
# Network Netmask Gateway Iface
# 127.0.0.0 255.0.0.0 0.0.0.0 lo
# 192.168.8.0 255.255.255.0 0.0.0.0 eth0
# 0.0.0.0 0.0.0.0 192.168.8.1 eth0
# >>> conf.route.delt(net="0.0.0.0/0",gw="192.168.8.1")
# >>> conf.route.add(net="0.0.0.0/0",gw="192.168.8.254")
# >>> conf.route.add(host="192.168.1.1",gw="192.168.8.1")
# >>> conf.route
# Network Netmask Gateway Iface
# 127.0.0.0 255.0.0.0 0.0.0.0 lo
# 192.168.8.0 255.255.255.0 0.0.0.0 eth0
# 0.0.0.0 0.0.0.0 192.168.8.254 eth0
# 192.168.1.1 255.255.255.255 192.168.8.1 eth0
# >>> conf.route.resync()
# >>> conf.route
# Network Netmask Gateway Iface
# 127.0.0.0 255.0.0.0 0.0.0.0 lo
# 192.168.8.0 255.255.255.0 0.0.0.0 eth0
# 0.0.0.0 0.0.0.0 192.168.8.1 eth0


# %% ARP Ping scapy
# The fastest way to discover hosts on a -local- ethernet network is to use the ARP Ping method:
# >>> ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst="10.0.0.0/24"),timeout=4)

# def update_arp_table(*redes: str) -> List[Tuple[List[str], List[str], int]]:
#    """
#    Envia pacotes ARP em broadcast para atualizar a tabela MAC dos elementos
#    Retorna tupla para cada rede fornecida contendo lista de IPs, de MACs e
#    total de elementos
#
#    redes = Endereco IP da rede de destino no formato '0.0.0.0/0':
#    ----
#    Usa o IP de rede fornecido como destino para o envio de quadros L2.
#
#    Exemplo:
#    ________
#    >>> update_arp_table('10.0.0.0/24')
#
#    >>> update_arp_table('10.0.0.0/24', '10.0.10.0/24')
#
#    >>> update_arp_table(*redes) #redes = ['10.0.0.0/24','10.0.10.0/24','10.0.20.0/24']
#    """
#    resposta_redes = []#    srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=rede),timeout=1)
#    for rede in redes:
#        print()
#        print(f'===> Iniciando descoberta da rede {rede}')
#        ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff") /
#                         ARP(pdst=rede),
#                         timeout=4)
#        ip, mac = [], []
#        num_nodes_ativos = 0
#        for envia, recebe in ans:
#            ip.append(recebe[0][1].summary().split()[5])
#            mac.append(recebe[0][1].summary().split()[3])
#        print(f'Tabela ARP para a rede {rede!r}:')
#        for node in range(len(ip)):
#            print(f'    IP: {ip[node]}, MAC: {mac[node]}')
#            num_nodes_ativos += 1
#        resposta_redes.append((ip, mac, num_nodes_ativos))
#        print(f'Rede: {rede!r}; '
#                f'Total de nodes: {str(num_nodes_ativos)!r}')
#    return resposta_redes


# %%
# redes = ['10.0.0.0/24', '10.0.10.0/24','10.0.20.0/24', '10.0.30.0/24']

# Answers can be reviewed with the following command:
# >>> ans.summary(lambda s,r: r.sprintf("%Ether.src% %ARP.psrc%"))
# Scapy also includes a built-in arping() function which performs similar to the above two commands:

# >>> arping("192.168.1.*")
# conf.route.resync()


# %% scapy icmp
# icmp_net = IP(dst='10.0.10.0/24')/ICMP()
# icmp_host = IP(dst='10.0.10.1')/ICMP()
# send(icmp_net)
# send(icmp_host)
# scapy.layers.l2.Ether


# %% posts function
# def posts(title, **kwargs): #kwargs = dict
#    print(title)
#    for post_title, post in kwargs.items():
#        print(post_title, post)
#
# my_title = "Titulo"
#
# posts(my_title,
#      arg1='Argumento1',
#      arg2='Argumento2',
#      arg3='Argumento3'
#      """ outputs:__
#        Titulo
#        Argumento1
#        Argumento2
#        Argumento3
#      """
#      )


# %% map funcao e retora lista de resultados
# def my_map(func, arg_list):
#    result = []
#    for i in arg_list:
#        result.append(func(i))
#    return result

# %%
# class A(object):
#     num = 0
#     grupo = set()
#
#     def __new__(cls, *args, **kargs):
#         cls.num += 1
#         return super().__new__(cls)
#
#     def __init__(self, texto):
#         A.grupo.add(self)
#         self.texto = texto
#
#     def __repr__(self):
#         return self.__class__.__name__ + '(' + self.texto + ')'
#
#     def __del__(self):
#         A.num -= 1
#         A.grupo.remove(self)
#
# teste1 = A('andre')
#
# A.grupo
# Out[3]: {A(andre)}
#
# A.num
# Out[4]: 1
#
# teste2 = A('kern')
#
# A.num
# Out[6]: 2
#
# teste1.grupo
# Out[8]: {A(andre), A(kern)}
#
# del teste2
#
# teste1.grupo
# Out[10]: {A(andre), A(kern)}
#
# teste1.num
# Out[11]: 2
