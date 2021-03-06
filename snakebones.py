#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding=utf-8
"""
Created on Sun Dec 3 ‏‎18:20:24 2017

domingo, ‎3‎ de ‎dezembro‎ de ‎2017, ‏‎18:20:24
.
@author: Andre Kern

Descobrindo a topologia fisica do spanning tree, G(V, E) , incorporado na LAN
Ethernet explorada
"""
# TODO https://www.geeksforgeeks.org/greedy-algorithms-set-7-dijkstras-algorithm-for-adjacency-list-representation/

# import subprocess
import sys

sys.path.append(
    '/mnt/hgfs/Projeto Final Dissertacao/snakebones'
)
sys.path.append(
    '/media/sf_Projeto_Final_Dissertacao/snakebones'
)

import logging
import networkx as nx  # para trabalhar com grafos
import matplotlib.pyplot as plt
from pdb import set_trace as breakpoint
from esqueleto import (to_bytes, ip_mac_to_arp_table, nms_config, ping_ip,
                       auto_arp_table_data, auto_snmp_data, is_internal_node,
                       is_leaf_node, set_arp_table, get_mymac, get_myip,
                       aft_fdb, config_nms, arp_table)
from ipaddress import IPv4Interface, IPv4Network  # ,IPv4Address
from itertools import combinations
from collections import Counter, defaultdict
from netaddr import EUI
from netaddr.strategy.eui48 import mac_cisco
from pprint import pprint
from typing import List, Union, Dict, Optional, \
    Set, Iterable, Tuple  # , Callable, Any, Union
from easysnmp import Session

# from easysnmp.exceptions import EasySNMPTimeoutError, EasySNMPConnectionError
# WARNING: No route found for IPv6 destination :: (no default route?).
# This affects only IPv6
# from scapy.all import *
# from scapy.sendrecv import srp
# from scapy.layers.l2 import Ether, ARP

logger = logging.getLogger(__name__)

# %% Constantes
YES = ON = START = True
NO = OFF = STOP = False

# %% Configuracao
AUTOFILL_MODE = False
POST_MODE = ON
mymac = None


# %% definicao de dados
def config(internal_nodes: List[Union[str, None]] = None,
           complete_aft=True) -> None:
    """
    Configura atribuicao de dados SNMP e tabela ARP
    :param complete_aft:
        True -> ARP completa para todos os nodes
        False -> ARP incompleta equivalente a formada a partir no NMS
    :type complete_aft: bool
    :type internal_nodes: Lista com string de IPs dos nodes internos (switch)
    :rtype: None
    """
    global SNMP_DATA, ARP_TABLE_DATA
    if AUTOFILL_MODE:
        SNMP_DATA = auto_snmp_data(complete_aft)
        ARP_TABLE_DATA = auto_arp_table_data()
    else:
        nms_config(True)
        SNMP_DATA = get_snmp_data(*internal_nodes)
        ARP_TABLE_DATA = dict()


class LoggingContext(object):
    def __init__(self, logger, level=None, handler=None, close=True):
        self.logger = logger
        self.level = level
        self.handler = handler
        self.close = close

    def __enter__(self):
        if self.level is not None:
            self.old_level = self.logger.level
            self.logger.setLevel(self.level)
        if self.handler:
            self.logger.addHandler(self.handler)

    def __exit__(self, et, ev, tb):
        if self.level is not None:
            self.logger.setLevel(self.old_level)
        if self.handler:
            self.logger.removeHandler(self.handler)
        if self.handler and self.close:
            self.handler.close()
        # implicit return of None => don't swallow exceptions


# %% classe SubNet
# propriedades basicas
class SubNet(IPv4Network):
    """
    Define rede 'N' a ser analisada. Representa conjunto de nodes
    'labeled' em uma determinada sub-rede. Cada objeto 'SubNet' determina um
    objeto 'Tree'.
    The set V is comprised of both labeled and unlabeled nodes.
    Labeled nodes, basically, represent elements that have a unique identifying
     MAC address and can provide AFT
    information through SNMP queries

    Atributos:
    ----
        address:
            id sub-rede = endereco e mascara
        arp_table:
            lista de IPs e macs relacionados
        internal_nodes:
            switches envolvidos na sub-rede (nodes - leaf_nodes)
        leaf_nodes:
            N = lista dos nodes (labeled) de uma sub-rede (para hosts) ou de
            varias sub-redes (para switches)
        nodes:
            Vn = lista dos elementos envolvidos na sub-rede (assume sem hubs).
            V representa hubs e switches envolvidos em todas as sub-redes.
        num_of_nets:
            numero total de objetos SubNet criados
    Metodos
        update_arp_table():
            Define atributo 'arp_table' da SubNet. [snmp] ou manual
        set_all_nodes():
            Define lista de nodes, internal_nodes e leaf_nodes da SubNet.
    """

    _num_of_nets = 0
    _all = set()

    def __new__(cls, *args, **kargs):
        """Cria objeto SubNet e incrementa contador"""
        if cls not in SubNet._all:
            cls._num_of_nets += 1
        return super().__new__(cls)

    def __init__(self, network_address,
                 strict=NO,
                 has_switches=NO,
                 auto_fill=AUTOFILL_MODE):
        """
        network_address:
            endereco IP da rede.
        strict:
            - True (YES)
                NAO aceita bits na parte de host.
            - False (NO)
                aceita bits na parte de host.
        has_swithes:
            - True (YES)
                Define rede atribuida para switches (internal nodes)
            - False (NO)

        Exemplo:
            >>> rede = SubNet('10.0.0.1/24')
            >>> rede.network_address
            ... IPv4Network('10.0.0.0/24')

            >>> rede = SubNet('10.0.0.0/24')
            >>> rede.network_address
            ... IPv4Network('10.0.0.0/24')
        """
        super().__init__(network_address, strict)
        self._has_switches = has_switches
        self._arp_table = None
        self._internal_nodes = []
        self._leaf_nodes = []
        self._nodes = []
        if self not in SubNet._all:
            SubNet._all.add(self)

    # FIXMEdepois nao removendo do set ao deletar instancia
    # def __del__(self):
    #     print(self)
    #     SubNet.remove_subnet(self)
    #     # SubNet._num_of_nets -= 1

    @classmethod
    def remove_subnet(cls, subnet):
        """
        Remove SubNet do set de redes criadas (all)
        Decrementa contador de redes

        :param subnet:
        """
        cls._all.remove(subnet)
        cls._num_of_nets -= 1

    @property
    def num_of_nets(self):
        """Retorna Numore de redes SubNet criadas"""
        return self._num_of_nets

    @property
    def all(self):
        """Retorna lista com instancias SubNet criadas"""
        return self._all

    @property
    def address(self):
        """Retorna endereco da rede SubNet com mascara"""
        return self.compressed

    @property
    def mac_set(self):
        """Retorna conjunto de enderecos MAC (em bytes) da SubNet"""
        return {mac.packed for _, mac in self.arp_table}

    @property
    def eui_set(self):
        """Retorna conjunto de objetos EUI (MAC) da SubNet"""
        return {eui for _, eui in self.arp_table}

    @property
    def nodes(self):
        """Retorna lista de nos (nodes Vn) da SubNet"""
        return self._nodes

    @property
    def nodes_set(self):
        """Retorna conjunto de nos (nodes Vn) da SubNet"""
        return set(self._nodes)

    @property
    def leaf_nodes(self):
        """Retorna lista de nos folhas (leaf nodes) da SubNet"""
        return self._leaf_nodes

    @property
    def internal_nodes(self):
        """Retorna lista de nos internos (internal nodes) da SubNet"""
        return self._internal_nodes

    @property
    def arp_table(self):
        """Retorna tabela arp da SubNet"""
        return self._arp_table

    @arp_table.setter
    def arp_table(self, value):
        self._arp_table = value

    def update_arp_table(self,
                         probes=1,
                         auto_fill=AUTOFILL_MODE,
                         manual_fill=None,
                         post=POST_MODE):
        """Define atributo 'arp_table' da SubNet. Caso nao seja atribuido
        auto_fill, atualiza tabela ARP do elemento.
        """
        self._arp_table = set_arp_table(
            self, probes, auto_fill, manual_fill)

    def set_all_nodes(self, auto_fill=AUTOFILL_MODE):
        """
        Define lista de nodes, internal_nodes e leaf_nodes da SubNet.
        Executa coleta automatica de SNMP na deficao de nodes da SubNet em 
        atributo snmp_data.

        Retorta listas com os devidos nodes da SubNet
        """
        if not self._arp_table:
            self.update_arp_table()
        for interface, mac in self._arp_table:
            if not get_node(interface.compressed):
                if auto_fill:
                    if self._has_switches:
                        # if self._has_switches and mac != get_mymac():
                        self._internal_nodes.append(
                            InternalNode(interface.compressed, str(mac))
                        )
                        self._internal_nodes[-1]._snmp_data = \
                            SNMP_DATA[interface.compressed]
                        self._nodes.append(self._internal_nodes[-1])
                    else:
                        self._leaf_nodes.append(
                            LeafNode(interface.compressed, str(mac))
                        )
                        self._nodes.append(self._leaf_nodes[-1])

                elif is_internal_node(interface.ip.compressed):
                    self._internal_nodes.append(
                        InternalNode(interface.compressed, str(mac))
                    )
                    # self._internal_nodes[-1]._snmp_data = \
                    #     get_snmp_data(self._internal_nodes[-1])
                    self._nodes.append(self._internal_nodes[-1])
                else:
                    self._leaf_nodes.append(
                        LeafNode(interface.compressed, str(mac))
                    )
                    self._nodes.append(self._leaf_nodes[-1])


# %% classe  Hub
class Hub(object):
    """
    Classe elementar para nodes [sem IP/MAC]
    ____
    #atributos
        - labeled: tipo do node
            - False = unlabeled -> hub (ou switches sem snmp)
            - True = labeled -> nodes, leafnodes, internalnodes (ip e mac unico)
        - port_list: postas de conexao com os elementos.
            - Apenas um item caso seja host.
    """
    _all_hubs = set()

    def __init__(self):
        """Inicia objeto Hub"""
        self._labeled = False
        if isinstance(self, Hub):
            Hub._all_hubs.add(self)
        self.name = f"hub_{len(Hub._all_hubs)}"

    def __repr__(self):
        return self.__class__.__name__ + '()'

    @property
    def labeled(self):
        """Retorna tipo de node
        ---
            switches e elementos que respondem snmp: 'labeled'

            elementos sem mac unico: 'unlabeled'
        """
        return self._labeled

    @property
    def port_list(self):
        """Retorna lista de portas"""
        return ['1']

    @property
    def port_set(self):
        """Retorna conjunto de portas"""
        return set(self.port_list)


# %% classe Node
class Node(IPv4Interface, Hub):
    """
    Classe para nodes com IP e MAC

    Atributos
    ----
    ip_address:
        endereco IP do node
    labeled: tipo do node
        False = unlabeled -> hub (ou switches sem snmp)
        True = labeled -> nodes, leafnodes, internalnodes (ip e mac unico)
    mac ou mac_address:
        endereco MAC do node
    num_of_nodes:
        numero total de nodes criados
    port_list:
        postas de conexao com o elemento.
    value_nv:
        numero nv do no para classificar em L
            - se node eh root, valor = quantidade de nodes +1/2
            - se node eh interno, valor = quantidade de nodes -1/2
            - se node eh folha, valor = quantidade de nodes
    mac_address:
        mac addres do node
    associated_subnets:
        Lista de redes relacionadas ao node.
        Cada node (labeled) na UniTree (G) esta associado com uma ou mais
        SubNet (N)

    Metodos:
    ----
    in_subnet(subnet):
        verifica se node pertence a SubNet fornecida
    """
    _num_of_nodes = 0
    _all = set()

    def __new__(cls, *args, **kargs):
        """Cria objeto Node e incrementa contador"""
        cls._num_of_nodes += 1
        return super().__new__(cls)

    def __del__(self):
        Node._num_of_nodes -= 1

    def __init__(self, ip_address: Union[IPv4Interface, str],
                 mac_address: Union[EUI, str]):
        """
        ip_address:
            Endereco IP para gerar objeto IPv4Interface
        mac_address:
            Endereco MAC para gerar objeto EUI
        """
        if isinstance(ip_address, IPv4Interface):
            super().__init__(ip_address.compressed)
            self._ip_address = self.ip.compressed
        elif isinstance(ip_address, str):
            super().__init__(ip_address)
            self._ip_address = self.ip.compressed
        else:
            raise Exception('Entrada IP nao perminida')

        self._mac = EUI(mac_address)

        self._mac.dialect = mac_cisco
        self._labeled = True
        if self.network in SubNet._all:
            for subnet in SubNet._all:
                if self.network == subnet:
                    self.associated_subnets = {subnet}
        else:
            self.associated_subnets = {SubNet(self.compressed)}
            SubNet._all.update(self.associated_subnets)
        self._value_nv = None  # valor do no para a lista L

    def __repr__(self):
        return self.__class__.__name__ + '(' + repr(self.with_prefixlen) \
               + ', ' + "'" + str(self.mac_address) + "')"

    @property
    def all(self) -> set:
        """
        Retorna conjunto V de todos os nodes criados da arvore G(V, E)

        :return: Conjunto de nodes
        :rtype: set
        """
        return self._all

    @property
    def mac(self):
        """ Retorna mac addres do node """
        return self._mac

    @property
    def mac_address(self):
        """ Retorna mac addres do node """
        return str(self.mac)

    @property
    def ip_address(self):
        """ Retorna IP addres do node """
        return self._ip_address

    @property
    def associated_subnets(self):
        """
        Retrona lista de redes associadas ao node, representando a colecao de
        subredes (*N*v) incluidas na sua arvore de conectvidade. A AFT de um
        determinado node contem informacoes de acessibilidade para nodes nas
        redes Nv. Cada node 'labeled' esta associado a uma ou mais redes.
        """
        return self._associated_subnets

    @associated_subnets.setter
    def associated_subnets(self, value):
        if not hasattr(self, 'associated_subnets'):
            if isinstance(value, SubNet):
                self._associated_subnets = set(value)
            elif isinstance(value, set):
                self._associated_subnets = set()
                for subnet in value:
                    if isinstance(subnet, SubNet):
                        self._associated_subnets.add(subnet)

        if isinstance(value, SubNet):
            self._associated_subnets.add(value)
        elif isinstance(value, set):
            for subnet in value:
                if isinstance(subnet, SubNet):
                    self._associated_subnets.add(subnet)

    @property
    def value_nv(self):
        """ Retorna valor do no para a lista L """
        return self._value_nv

    @property
    def value_n(self):
        """ Retorna valor do no para a lista L """
        return self._value_nv

    @property
    def num_of_nodes(self):
        """Retorna numero total de nodes criados"""
        return self._num_of_nodes

    def in_subnet(self, subnet: SubNet) -> bool:
        """
        :param subnet: verifica se node pertence a subnet fornecida
        :type subnet: SubNet
        :rtype: bool
        """
        return self in subnet


# %% classe LeafNode
class LeafNode(Node):
    """Classe destinada a leaf nodes (hosts)
    """
    _all_leaves = set()

    def __init__(self, ip_address, mac_address, is_root=False):
        super().__init__(ip_address, mac_address)
        self.is_root = is_root
        LeafNode._all_leaves.add(self)
        Node._all.add(self)
        self._name = f"leaf_{len(LeafNode._all_leaves)}"

    @property
    def name(self) -> str:
        """Nome criado para o node, indicando quando for root

        :return: Nome do node
        :rtype: str
        """
        if self.is_root:
            return self._name + "*root*"
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def is_root(self):
        """Indica se no folha eh root da arvore nao direcionada"""
        return self._is_root

    @property
    def all_leaves(self) -> set:
        """
        Conjunto com instancias LeafNode criadas

        :rtype: set
        :return: nodes do tipo folha/leave
        """
        return self._all_leaves

    @is_root.setter
    def is_root(self, value: bool):
        if isinstance(value, bool):
            self._is_root = value

    def aft_atports(self,
                    porta: str,
                    subnet: Union[str, IPv4Network, SubNet, None] = None) \
            -> Optional[Set]:
        """Retorna tabela AFT de emcaminhamento para porta. LeafNode difinido
        com apenas porta '1', retornando None se solicitado porta diferente ou
        outra subnet diferente da sua. Mac do LeafNode (self) nao incluido no
        retorno

        Fv,k e FNv,k

        Exemplo:
        ----
        >>> self.aft_atports('1')  # Fv,k
        ... {b'\\x00Pyfh\\x04',
        ...  b'\\x00Pyfh\\x06',
        ...  b'\\x00Pyfh\\x03'}

        >>> self.aft_atports('1','10.0.20.0/24')  # FNv,k N==self.network
        ... {b'\\x00Pyfh\\x04',
        ...  b'\\x00Pyfh\\x06',
        ...  b'\\x00Pyfh\\x03'}

        >>> self.aft_atports('1','10.0.10.0/24')  # FNv,k N!=self.network
        ... None

        :param porta: indice da porta a analisar
        :param subnet:  rede a ser retornado aft
        :return: AFT em cada porta
        :rtype: set
        """
        subnet = get_subnet(subnet)
        node_port = port_activeset(self)
        if not subnet and node_port == {porta}:
            return get_subnet(self.network.compressed).mac_set - {
                self.mac.packed}
        elif subnet and node_port == {porta}:
            if subnet.compressed == self.network.compressed:
                return subnet.mac_set - {self.mac.packed}
            else:
                return None


# %% classe InternalNode
class InternalNode(Node):
    """
    Classe define switches envolvidos na sub-rede (nodes - leaf_nodes)
    ____
    Atributos
        mac_list
            Lista com MACs aprendidos
        port_list
            Lista portas contendo MAC para encaminhamento
        aft
            Tabela de emcaminhamento no formato (MAC, PORTA)
        port_activelist
            Lista ordenada de portas com STP ativo
        port_root
        port_leaves
        leaves
        leaves_size

    """
    _num_of_inodes = 0
    _allinodes_set = set()

    def __new__(cls, *args, **kargs):
        """Cria objeto InternalNode e incrementa contador"""
        cls._num_of_inodes += 1
        return super().__new__(cls)

    def __init__(self, ip_address, mac_address, auto_fill=AUTOFILL_MODE):
        super().__init__(ip_address, mac_address)
        self.ports_onsubnet = defaultdict(set)
        if auto_fill and SNMP_DATA.get(self.compressed):
            self._snmp_data = SNMP_DATA.get(self.compressed)
        else:
            self._snmp_data = get_snmp_data(self).get(self.compressed)

        InternalNode._allinodes_set.add(self)
        Node._all.add(self)

    def __del__(self):
        InternalNode._num_of_inodes -= 1

    @property
    def port_list(self) -> Optional[List[str]]:
        """Retorna lista de portas na ordem coletada pelo snmp

        :return: Lista de portas
        :rtype: None, list
        """
        if hasattr(self, 'snmp_data'):
            return self._snmp_data.get('dot1d_tp_fdb_port')
        return None

    @property
    def name(self):
        """
        Nome atribuido ao node pelo administrador da rede, coletado por snmp

        :rtype: str
        :return: sys_name snmp
        """
        return self._snmp_data.get('sys_name')

    @name.setter
    def name(self, value: str) -> None:
        """
        Define nome ao node

        :rtype: None
        :param value: Nome a ser atribuido
        """
        if isinstance(value, str):
            self.snmp_data['sys_name'] = value
        else:
            print(f'Valor {value} nao foi atribuido pq nao e string.')

    @property
    def allinodes_set(self) -> set:
        """
        Conjunto com instancias InternalNode criadas

        :rtype: set
        :return: nodes internos
        """
        return self._allinodes_set

    @property
    def port_activelist_named(self) -> List:
        """
        Retorna lista de portas ativas do node com respectivos nomes
        """
        # return self._port_activelist
        return self._snmp_data.get('port_activelist')

    @property
    def port_name(self) -> dict:
        """
        Retorna dicionario de portas ativas do node com respectivos nomes

        Exemplo:
        ----
        >>> self.port_name['1']
        ... 'Gi0/0'
        :return: Dicionario {'porta': 'nome'}
        :rtype: dict
        """
        name_dict = defaultdict(str)
        for port, name in self._snmp_data.get('port_activelist'):
            name_dict[port] = name
        return name_dict

    def port_root(self, subnet: Union[str, IPv4Network, SubNet]) -> str:
        """
        Retorna dicionario com portas que levam ao root para rede especificada
        como chave
        #v(r) = porta que leva ao root

        Exemplo:
        ----
        >>> self.port_root('10.0.10.0/24')  # rede existente
        ... '1'

        >>> self.port_root('10.0.99.0/24')  # rede inexistente
        ... None

        :param subnet: rede a ser retornado root port
        :return:  Porta ao root
        :rtype: str
        """
        return get_port(self, get_root(get_subnet(subnet)))

    def port_leaves(self, subnet: Union[str, IPv4Network, SubNet]) -> set:
        """
        Retorna portas que levam aos nos folhas
        leaf ports = active - root
        #DNv - v(r) = portas que levam as folhas

        Exemplo:
        ----
        >>> self.port_leaves('10.0.20.0/24')
        ... {'3', '16'}

        :param subnet: rede a ser retornado portas folhas
        :return: Portas para folhas
        :rtype: set
        """
        subnet = get_subnet(subnet)
        port_root = {self.port_root(subnet)}
        return port_activeset(self, subnet) - port_root

    def leaves(self, subnet: Union[str, IPv4Network, SubNet]) -> set:
        """
        Retorna conjunto de nos folhas em relacao ao root para subrede fornecida
        #leaves = nodes - root
        #Bv = N - root
        #Bv = lista de folhas do no na sub-rede

        Exemplo:
        ----
        >>> self.leaves('10.0.20.0/24')
        ... {LeafNode('10.0.20.3/24', '0050.7966.6804'),
        ...  LeafNode('10.0.20.4/24', '0050.7966.6806')}

        :param subnet: rede a ser retornado LeafNodes
        :return: Conjunto de folhas
        :rtype: set
        """
        subnet = get_subnet(subnet)
        leaves = set()
        for port in self.port_leaves(subnet):
            for mac in self.aft_atports(port, subnet):
                leaves.add(get_node(mac))
        return leaves

    def leaves_size(self, subnet) -> int:
        """
        Retorna quantidade de nodes folhas para rede informada
        #|Bv| = numero de folhas do node

        Exemplo:
        ----
        >>> self.leaves_size('10.0.10.0/24')
        ... 5

        :param subnet: rede a ser retornado quantidade de folhas
        :return: Quantidade de folhas
        :rtype: int
        """
        return len(self.leaves(get_subnet(subnet)))

    @property
    def num_of_inodes(self):
        """Retorna numero total de internal nodes criados"""
        return self._num_of_inodes

    @property
    def snmp_data(self):
        """Dados da coleta SNMP"""
        return self._snmp_data

    @property
    def mac_list(self):
        """Lista com MACs aprendidos"""
        return self._snmp_data.get('dot1d_tp_fdb_address')

    @property
    def aft(self):
        """Tabela de emcaminhamento (MAC, PORTA)"""
        return list(zip(self.mac_list, self.port_list))

    def aft_atports(self,
                    porta: str,
                    subnet: Union[str, IPv4Network, SubNet, None] = None) \
            -> set:
        """Retorna tabela AFT de emcaminhamento para determinada porta, podendo
        filtrar rede especifica

        Fv,k e FNv,k

        Exemplo:
        ----
        >>> self.aft_atports('1')  # Fv,k
        ... {b'\x00>\\\x01\x80\x01',
        ...  b'\x00>\\\x06\x80\x01',
        ...  b'\x00Pyfh\x00',
        ...  b'\x00Pyfh\x01',
        ...  b'\x00Pyfh\x0b',
        ...  b'\x00Pyfh\x0c'}

        >>> self.aft_atports('1','10.0.10.0/24')  # FNv,k
        ... {b'\x00Pyfh\x0c'}

        :param porta: indice da porta a analisar
        :param subnet:  rede a ser retornado aft
        :return: AFT em cada porta
        :rtype: set
        """
        if not subnet:
            return {mac for mac, port in zip(self.mac_list, self.port_list)
                    if port == porta}
        else:
            subnet = get_subnet(subnet)
            return {mac for mac in subnet.mac_set
                    if mac in self.aft_atports(porta)}

    def set_aft(self, porta: str, *new_macs):
        """Acrescenta new_macs a tabela AFT de emcaminhamento para determinada porta

        Atualiza Fv,k

        :param porta:
        :param new_macs:
        """
        ports = self._snmp_data['dot1d_tp_fdb_port']
        mac_data = self._snmp_data['dot1d_tp_fdb_address']
        while ports.count(porta):
            mac_data.pop(ports.index(porta))
            ports.remove(porta)

        for mac in new_macs:
            if mac in mac_data:
                ports.pop(mac_data.index(mac))
                mac_data.remove(mac)
            mac_data.append(mac)
            ports.append(porta)

    def set_associated_subnets(self):
        """
        Define redes associadas ao internal node 'v' dentre redes criadas,
        atribuindo a associated_subnets caso necessario
        v pertence a Vn
        """
        for subnet in SubNet._all:
            # for self in InternalNode._allinodes_set:
            if subnet == self.network:
                continue
            else:
                arp_set = set()
                for ip_arp, mac_arp in subnet.arp_table:
                    if mac_arp.packed in self.mac_list:
                        arp_set.add(mac_arp.packed)
                    for mac_aft, port_aft in self.aft:
                        if mac_aft == mac_arp.packed:
                            self.ports_onsubnet[subnet.address].add(port_aft)
            if len(self.ports_onsubnet[subnet.address]) >= 2 \
                    or (subnet.mac_set
                        and arp_set
                        and (arp_set < subnet.mac_set)):
                self.associated_subnets.add(subnet)
                subnet._nodes.append(self)


NodeL3 = Union[LeafNode, InternalNode]


# %% Funcao get_node
def get_node(node: Union[bytes, str, LeafNode, InternalNode]) \
        -> Union[None, LeafNode, InternalNode]:
    """Localiza e retorna node com base no endereco fornecido

    :param node:
        Enderedeo em bytes ou string do IP ou MAC do node a ser pesquisado
    :return: Objeto que representa o node
    :rtype: LeafNode,InternalNode
    """
    if isinstance(node, bytes):
        address = int.from_bytes(node, 'big')
        if len(node) > 4:
            try:
                EUI(address)
            except:
                return None
        else:
            try:
                IPv4Interface(address)
            except:
                return None
        for net_node in Node._all:
            if net_node.ip.packed == node \
                    or net_node.mac.packed == node:
                return net_node

    elif isinstance(node, str):
        try:
            node_obj = IPv4Interface(node)
        except:
            try:
                node_obj = EUI(node)
            except:
                return None
            else:
                for net_node in Node._all:
                    if net_node.mac == node_obj:
                        return net_node
        else:
            for net_node in Node._all:
                if net_node.ip == node_obj.ip:
                    return net_node
    elif isinstance(node, EUI):
        for net_node in Node._all:
            if net_node.mac.packed == node.packed:
                return net_node
    else:
        for net_node in Node._all:
            if net_node == node:
                return net_node


# %% Funcao set_root(node)
def set_root(node: Union[bytes, str, LeafNode, InternalNode] = None,
             subnet: Union[str, IPv4Network, SubNet, None] = None) \
        -> None:
    """
    Pode ser escolhido com basse no node fornecido OU na subnet.
    Caso node, tenta definir LeafNode fornecido como root de sua SubNet.
    Caso subnet, atribui o NMS conectada a subnet como root

    atributo is_root do LeafNode: LeafNode.is_root = True

    :param node: node a ser pesquisado definido como root node
    :param subnet: rede a ser definido root para o NMS
    :return: define atributo LeafNode.is_root = True
    :rtype: None
    """
    if node:
        root_node = get_node(node)
        if not root_node:
            logger.warning(f"Root node nao definido para {node}")
            return None
        found_net = get_subnet(root_node.network.compressed)
        if not found_net:
            logger.warning(f"Rede nao definida para {root_node}")
            return None
        if found_net.leaf_nodes:
            for node in found_net.leaf_nodes:
                if node == root_node:
                    root_node.is_root = True
                    logger.debug(f'Root definido: {root_node}')
                else:
                    node.is_root = False
            if not root_node.is_root:
                logger.warning("Root Nao localizado")
                return None
        else:
            logger.warning(f"Rede {found_net} nao possui leaf_nodes definidos")
            return None
    elif subnet:
        found_net = get_subnet(subnet)
        if found_net:
            if found_net.leaf_nodes:
                for node in found_net.leaf_nodes:
                    if node.is_root:
                        node.is_root = False
                for ip in get_myip():
                    if ip in found_net:
                        root = get_node(ip)
                        root.is_root = True
                        logger.debug(f'Root definido para {found_net}: '
                                     f'{root}')
                return None
            else:
                logger.warning(f"Rede {found_net} "
                               f"nao possui leaf_nodes definidos")
                return None
        else:
            logger.warning(f"Rede {subnet} nao localizada")


# %% Funcao get_root(subnet: SubNet) -> bool
def get_root(subnet: Union[str, IPv4Network, SubNet]) -> Optional[LeafNode]:
    """
    Identifica o LeafNode definido como root de uma SubNet

    :param subnet:
        Rede a ser pesquisada pelo root node
    :return:
        Objeto LeafNode definido como root
    """
    subnet = get_subnet(subnet)
    if subnet:
        if subnet.leaf_nodes:
            for node in subnet.leaf_nodes:
                if node.is_root:
                    return node
    return None
    # print(f'Root nao definido para {subnet}')


# %% Funcao get_port
def get_port(from_node: Union[str, LeafNode, InternalNode],
             to_node: Union[str, LeafNode, InternalNode]) -> Optional[str]:
    """
    Retorna porta do node interno v que leva a u. v(u)

    Exemplo:
    ----
    >>> get_port('10.0.20.1/24', '10.0.0.2/24')
    ... '1'

    :param from_node: Node de origem que fornecera dado da porta de saida
    :param to_node: Destino a ser identificado porta de saida associada
    :type to_node: str, LeafNode, InternalNode
    :return: String com identificacao da porta
    :rtype: str
    """
    # pass
    source = get_node(from_node)
    if not source:
        return None
    elif isinstance(source, LeafNode):
        return '1'
    destination = get_node(to_node)
    if not destination:
        return None
    for mac, port in source.aft:
        if destination.mac.packed == mac:
            return port


# %% Funcao get_subnet
def get_subnet(subnet: Union[str, IPv4Network, SubNet]) -> Optional[SubNet]:
    """Retorna se endereco de rede fornecido existe entre os objetos SubNet
    criados.

    Exemplo:
    ----
    >>> get_subnet('10.0.10.0/24')
    ... SubNet('10.0.10.0/24')

    >>> get_subnet('10.0.10.0/255.255.255.0')
    ... SubNet('10.0.10.0/24')

    >>> get_subnet('10.0.10.0/0.0.0.255')
    ... SubNet('10.0.10.0/24')

    >>> get_subnet(IPv4Network('10.0.10.0/24'))
    ... SubNet('10.0.10.0/24')

    >>> get_subnet(SubNet('10.0.10.0/24'))
    ... SubNet('10.0.10.0/24')

    :param subnet: Rede a ser localizada
    :return: Objeto SubNet, se foi localizado
    :rtype: SubNet
    """
    if isinstance(subnet, str):
        try:
            net_obj = IPv4Network(subnet, strict=False)
        except:
            return None
    elif isinstance(subnet, (SubNet, IPv4Network)):
        net_obj = subnet
    else:
        return None
    for net in SubNet._all:
        if net == net_obj:
            return net
    return None


# %% Funcao port_activeset
def port_activeset(node: NodeL3,
                   subnet: Optional[str] = None) -> set:
    """
    Retorna conjunto de portas ativas do node. Para objetos LeafNode retorna
    sempre {'1'}

    # Dv = potas ativas do node
    # DNv = potas ativas do node na subrede N (parametro subnet)

    Exemplo:
    ----
    >>> # para nodes '10.0.10.X/24'
    >>> port_activeset(LeafNode('10.0.10.1/24', '0050.7966.680c'))# Dv
    ... {'1'}
    >>> port_activeset(InternalNode('10.0.0.1/24', '003e.5c01.8001'))  # Dv
    ... {'3', '16', '1', '2'}

    >>> port_activeset(LeafNode('10.0.10.1/24', '0050.7966.680c'),
    ...                '10.0.10.0/24')  # DNv existente
    ... {'1'}
    >>> port_activeset(LeafNode('10.0.10.1/24', '0050.7966.680c'),
    ...                '10.0.20.0/24')  # DNv inexistene
    ... set()

    >>> port_activeset(InternalNode('10.0.0.1/24', '003e.5c01.8001'),
    ...                '10.0.20.0/24')  # DNv existente
    ... {'3', '16', '2'}
    >>> port_activeset(InternalNode('10.0.0.1/24', '003e.5c01.8001'),
    ...                '10.0.30.0/24')  # DNv inexistene
    ... set()

    :return: Conjunto de portas ativas
    :param node: LeafNode ou InternalNode
    :param subnet: subrede no formato 'ip/mascara'
    :return: Conjunto de portas ativas
    :rtype: set

    """
    if isinstance(node, LeafNode):
        if not subnet:
            return {'1'}
        else:
            subnet = get_subnet(subnet)
            for rede in node.associated_subnets:
                if rede.compressed == subnet.compressed:
                    return {'1'}
            return set()

    elif isinstance(node, InternalNode):
        if not subnet:
            return node.port_set
        else:
            subnet = get_subnet(subnet)
            subnet_ports = set()
            for mac in subnet.mac_set:
                for port in node.port_set:
                    if mac in node.aft_atports(port):
                        subnet_ports.add(port)
            return subnet_ports


# %% Funcao get_active_ports
def get_active_ports(node: Union[bytes, str, LeafNode, InternalNode],
                     *netnodes: Optional[Tuple[NodeL3, NodeL3]]) \
        -> set:
    """
    Retorna conjunto de portas ativas do node. Para objetos LeafNode retorna
    sempre {'1'}

    # Dv = potas ativas do node
    # DNv = potas ativas do node para conjunto  de nodes N (parametro netnodes)

    Exemplo:
    ----
    >>> # para nodes '10.0.10.X/24'
    >>> get_active_ports(LeafNode('10.0.10.111/24', '000c.295c.4271'))# Dv
    ... {'1'}
    >>> get_active_ports(InternalNode('10.0.0.2/24', '003e.5c02.8001'))  # Dv
    ... {'3', '16', '1', '2'}

    >>> get_active_ports(LeafNode('10.0.10.111/24', '000c.295c.4271'),
    ...                     (LeafNode('10.0.10.6/24', '0050.7966.6807'),
    ...                      LeafNode('10.0.10.5/24', '0050.7966.6808')
    ...                     ))  # DNv existente
    ... {'1'}

    >>> get_active_ports(LeafNode('10.0.10.5/24', '0050.7966.6808'),
    ...                     (LeafNode('10.0.20.4/24', '0050.7966.6806'),
    ...                      LeafNode('10.0.20.3/24', '0050.7966.6804')
    ...                      ))  # DNv inexistene
    ... set()

    :param node: LeafNode ou InternalNode
    :param netnodes: subrede no formato 'ip/mascara'
    :type netnodes: Iterable
    :return: Conjunto de portas ativas
    :rtype: set

    """
    node = get_node(node)

    if isinstance(node, LeafNode):
        if not netnodes:  # Dv
            return {'1'}
        else:  # DNv
            for netnode in netnodes:
                if node in netnode.network:
                    return {'1'}
            return set()

    elif isinstance(node, InternalNode):
        if not netnodes:
            return node.port_set
        else:
            netnodes_ports = set()
            for netnode in netnodes:
                for port in node.port_set:
                    if netnode.mac.packed in node.aft_atports(port):
                        netnodes_ports.add(port)
            return netnodes_ports


# %% Funcao get_snmp_data
def get_snmp_data(*internal_nodes, net_bits: int = 24) -> dict:
    """
    Executa coleta SNMP dos dados:
        sysname:
            hostname do elemento
        ifnumber:
            quantidade de interfaces (fisicas + virtuais + null)
        ifindex:
            lista de indices numerico das interfaces ifnumber
        ifdescr:
            lista de nome das interfaces ifnumber
        ifphysaddess:
            lista de MAC das interfaces ifnumber
        ifadminstatus:
            estado configurado das interfaces ifnumber (1 = desbloqueada)
        ifoperstatus:
            estado de atividade das interfaces ifnumber (1 = em atividade)
        dot1dbasenumports:
            quantidade de interfaces em bridge
        dot1basetype:
            tipo de bridge (2 = apenas 'transparente')
        dot1dstpport:
            indice das interfaces com STP ativo.
        dot1d_tp_fdb_address
            MAC conhecidos pela bridge (forwarding)
        dot1d_tp_fdb_port
            index da porta com MAC

        exemplo 10.0.0.1:
            Vlan    Mac Address       Type        Ports
            ----    -----------       --------    -----
               1    000c.293b.271e    DYNAMIC     Gi0/0
               1    003e.5c02.8001    DYNAMIC     Gi0/2
               1    003e.5c03.8001    DYNAMIC     Gi0/2
               1    003e.5c04.8001    DYNAMIC     Gi0/2
               1    003e.5c05.8001    DYNAMIC     Gi0/2
               1    003e.5c06.8001    DYNAMIC     Gi0/1
               1    0050.7966.6800    DYNAMIC     Gi0/1
               1    0050.7966.6801    DYNAMIC     Gi3/3
               1    0050.7966.6802    DYNAMIC     Gi0/2
               1    0050.7966.6803    DYNAMIC     Gi0/2
               1    0050.7966.6804    DYNAMIC     Gi0/2
               1    0050.7966.6805    DYNAMIC     Gi0/2
               1    0050.7966.6806    DYNAMIC     Gi0/2
               1    0050.7966.6807    DYNAMIC     Gi0/2
               1    0050.7966.6808    DYNAMIC     Gi0/2
               1    0050.7966.6809    DYNAMIC     Gi0/2
               1    0050.7966.680a    DYNAMIC     Gi0/2
               1    0050.7966.680b    DYNAMIC     Gi0/1
               1    0050.7966.680c    DYNAMIC     Gi3/2
               1    c401.0883.0001    DYNAMIC     Gi1/0
               1    c401.0883.0010    DYNAMIC     Gi1/1
               1    c401.0883.0020    DYNAMIC     Gi1/2
               1    c401.0883.0030    DYNAMIC     Gi1/3
            Total Mac Addresses for this criterion: 23


    """
    if not internal_nodes:
        inodes = \
            ['10.0.0.1',
             '10.0.0.2',
             '10.0.0.3',
             '10.0.0.4',
             '10.0.0.5',
             '10.0.0.6']
    else:
        inodes = internal_nodes

    snmp_data = dict()
    # HINT get_snmp_data: bloqueado propagacao de log para modulos importados
    logging.getLogger('easysnmp').propagate = False
    for node in inodes:
        # logger.info(f'Coletando SNMP em {node}...')
        if isinstance(node, (Node, InternalNode, LeafNode)):
            host_key = node.compressed
            node_ip = node.ip.compressed
        else:
            host_key = node + '/' + str(net_bits)
            node_ip = node
        snmp_data[host_key] = dict()
        snmp = Session(hostname=node_ip,
                       version=2,
                       community='public')
        # logger.info(f'Coletando SNMP sys_name em {node}...')
        snmp_data[host_key]['sys_name'] = snmp.get('sysName.0').value

        dot1dstpport = 'mib-2.17.2.15.1.1'
        # logger.info(f'Coletando SNMP portas dot1dstpport em {node}...')
        resposta_snmp = snmp.get_next(dot1dstpport)
        stp_port_indexes = []
        while dot1dstpport in resposta_snmp.oid:
            stp_port_indexes.append(
                resposta_snmp.oid.rsplit(sep='.', maxsplit=1)[-1])
            resposta_snmp = snmp.get_next(resposta_snmp.oid)
        # logger.debug(f'SNMP portas dot1dstpport em {node}: {stp_port_indexes}')

        ifname = 'mib-2.31.1.1.1.1'  # 'iFname'
        # resposta_snmp = snmp.get(ifname)
        if_name = []
        for index in stp_port_indexes:
            resposta_snmp = snmp.get(ifname + '.' + index)
            if_name.append(resposta_snmp.value)
        snmp_data[host_key]['port_activelist'] \
            = list(zip(stp_port_indexes, if_name))

        dot1dbasenumports = 'mib-2.17.1.2'
        snmp_data[host_key]['dot1d_base_num_ports'] \
            = snmp.get_next(dot1dbasenumports).value

        dot1basetype = 'mib-2.17.1.3'
        snmp_data[host_key]['dot1_base_type'] \
            = snmp.get_next(dot1basetype).value

        dot1dtpfdbaddress = 'mib-2.17.4.3.1.1'
        mac_list = []
        #            dot1d_tp_fdb_address = mac_list
        resposta_snmp = snmp.get_next(dot1dtpfdbaddress)
        while dot1dtpfdbaddress in resposta_snmp.oid:
            mac_list.append(to_bytes(resposta_snmp.value))
            resposta_snmp = snmp.get_next(resposta_snmp.oid)
        snmp_data[host_key]['dot1d_tp_fdb_address'] = mac_list

        dot1dtpfdbport = 'mib-2.17.4.3.1.2'
        dot1d_tp_fdb_port = []
        #    <SNMPVariable value='1' (oid='mib-2.17.4.3.1.2.0.12.41.59.39.30',
        #                             oid_index='',
        #                             snmp_type='INTEGER')>
        resposta_snmp = snmp.get_next(dot1dtpfdbport)
        while dot1dtpfdbport in resposta_snmp.oid:
            dot1d_tp_fdb_port.append(resposta_snmp.value)
            resposta_snmp = snmp.get_next(resposta_snmp.oid)
        snmp_data[host_key]['dot1d_tp_fdb_port'] = dot1d_tp_fdb_port

    return snmp_data


# %% classe Edges
class Edges(object):
    """
    Define grupo de enlaces (edges). Representa cada conexão física entre 2
    portas ativas de elementos da rede
    """
    pass


# %% classe Vertex
class Vertex(object):
    """Representa o vertice na skeleton-tree. Cada vertice contem um conjunto
    associado de um ou mais nodes em Vn

    """
    _all = set()  # set Y de H(Y, A)
    _verbose_name = False

    def __init__(self, *nodes):
        self._nodes_set = set()
        for node in nodes:
            self._nodes_set.add(node)
            if isinstance(node, (LeafNode, InternalNode)):
                self._value_ny = node.value_nv
            else:
                self._value_ny = None
        Vertex._all.add(self)  # y U Y

    def __repr__(self):
        if not self._nodes_set:
            return f"{self.__class__.__name__}()"
        elif Vertex._verbose_name:
            return f"{self.__class__.__name__}({self._nodes_set})"
        nodes = {node.name for node in self._nodes_set}
        return f"{self.__class__.__name__}({nodes})"

    def __lt__(self, other):
        if not isinstance(other, Vertex):
            return NotImplemented
        try:
            return self._value_ny < other._value_ny
        except AttributeError:
            return NotImplemented

    @property
    def nodes_set(self):
        """
        Retorna conjunto de labeled nodes que compoem o vertice. Se for Hub
        retorna set()

        :return: Conjunto de nodes
        """
        for node in self._nodes_set:
            if isinstance(node, (LeafNode, InternalNode)):
                return self._nodes_set
        return set()

    @nodes_set.setter
    def nodes_set(self, value):
        self._nodes_set = value

    @property
    def value_n(self) -> float:
        """Retorna valor do no para a lista L

        :return: valor nv
        :rtype: float
        """
        return self._value_ny

    @value_n.setter
    def value_n(self, value):
        self._value_ny = value


# %% classe Arch
class Arch(object):
    """
    Define arco que interliga 2 vertices em uma SkeletonTree
    """
    _all = set()  # conjunto de todos os arcos criados

    def __init__(self,
                 endpoint_a: Vertex,
                 port_a: Optional[str] = None,
                 endpoint_b: Optional[Vertex] = None,
                 port_b: Optional[str] = None,
                 netnodes=None) -> None:
        self._endpoint_a = endpoint_a
        self._endpoint_b = endpoint_b
        self._port_a = port_a
        self._port_b = port_b
        self.netnodes = netnodes
        # Ba
        node_a = list(endpoint_a._nodes_set)[0]
        if node_a and isinstance(node_a, (LeafNode, InternalNode)):
            self._reachable_nodes_set = \
                {get_node(mac)
                 for mac in get_aft(node_a, port_a, *self.netnodes)}
        else:
            self._reachable_nodes_set = None
        Arch._all.add(self)  # a U A

    def __repr__(self):
        return f"{self.__class__.__name__}" \
               f"({self._endpoint_a!r}, {self._port_a!r}, {self._endpoint_b}, " \
               f"{self._port_b!r})"

    @property
    def reachable_mac(self) -> Set[EUI]:
        """
        Retorna conjunto de objetos EUI com mac dos nodes acessados pelo arco

        :return: Conjunto de EUI (MAC)
        :rtype: set
        """
        return {node.mac for node in self._reachable_nodes_set}

    @reachable_mac.setter
    def reachable_mac(self, value):
        self._reachable_nodes_set = {get_node(node) for node in value}


# %% classe SkeletonTree
class SkeletonTree(object):
    """
    Define skeleton tree composta de vertices e arcos H(Y,A)

     cada LeafNode ou junctio node e representado exclusivamente por um vertice
     simples e a sequencia de transit nodes e identificado por um ou mais
     vertices

    vertices e arcs para designar elementos da the skeleton-tree e suas
    interconexoes

    #atributos da skeleton
        root_node - identifica o no raiz da skeleton-tree
        netnodes - lista N - internal nodes de nos exclusivos da sub-rede
        nodes - lista Vn dos elementos da sub-rede, leaf_nodes + internalnodes
        sem HUBs
        sorted_nodes - lista L decrescente dos nos
        mac_table - tabela de enderecos mac das interfaces
        vertex - vertice da skeleton-tree
        vertex_nodes - lista de nodes inclusos no vertice
        vertexes - grupo Y de vertices y
        arcs - grupo A de arcos a
            ports
            #Ba
            leaf_nodes
        frontier_arcs - grupo Z de arcos com 1 end-point

    passo 1 - coleta dados
        - encontra porta root dos nos
        - calcula folhas dos nos
        - calcula valores dos nos para lista L sorted_nodes
    passo 2 - inicializa skeleton-tree
        - compila lista L sorted_l em ordem decrescente
        - inicializa skeleton-tree com primeiro vertex.nodes = root_node
        - inicializa o grupo frontier_set com numero de port_activelist
          do root
        - cada arco arc de frontier_set eh associado ao grupo de folhas
          abaixo dele (macs na porta)
    passo 3 - modifica skeleton-tree
        - extrai primeiro no de L sorted_l
        - identifica arco frontier_arcs que sera conectado ao no extraido

    """
    _all = set()  # conjunto de totos skeletons criadas

    # SKELETONTREE(N, VN , root, AFTs)
    def __init__(self,
                 netnodes: Union[Set[LeafNode], List[LeafNode]],  # N
                 nodes: Set[NodeL3],  # Vn
                 root: NodeL3,  # root
                 subnet: Optional[Union[str, IPv4Network, SubNet]] = None,
                 remove: List[
                     Union[bytes, str, LeafNode, InternalNode]] = None) \
            -> None:
        """
        Inicializa a skeleton-tree
        SKELETONTREE(N, VN , root, AFTs)

        :param netnodes: LeafNodes N que compoem a SkeletonTree
        :param nodes: todos os nodes V relacionados a N
        :param root: root node referenciado para calculo da SkeletonTree
        :param subnet: subrede que induz a topologia
        :rtype: None
        """
        if subnet:
            self.subnet = get_subnet(subnet)
            self.name = f"({self.subnet.compressed!r})"
        else:
            self.name = f"('bone_{len(SkeletonTree._all)+1}')"
        logger.info(f'Iniciando skeleton {self.name }')

        if remove:
            remove_set = {get_node(node) for node in remove if get_node(node)}
            logger.debug(f'Removendo {remove_set}')
            self.nodes = set(nodes) - remove_set  # Vn
            self.netnodes = set(netnodes) - remove_set  # N
        else:
            self.nodes = set(nodes)  # Vn
            self.netnodes = set(netnodes)  # N
        self.root = root  # r
        self.root._value_nv = len(netnodes) + 0.5  # |N| + 1/2
        self.frontier_set = set()  # Z para arcos fronteira
        self.vertices = set()  # set Y de H(Y, A)
        self.arches: Set[Arch] = set()  # set A de H(Y, A)
        logger.debug(f'Root {self.root} value_n {self.root._value_nv}')

        # definindo |Bv| de N para cada node com root em v
        logger.info(
            f'Definindo |Bv| de N para cada node com root em {self.root}')
        for node in self.nodes - {self.root}:
            if isinstance(node, InternalNode):
                node.bv_set = set()  # Bv
                # Dv - {v(r)}
                leaves_ports = \
                    port_activeset(node) - {get_port(node, self.root)}
                for port in leaves_ports:
                    node.bv_set |= {aftnode.mac for aftnode in
                                    get_aft(node, port, *self.netnodes)}
                if not node.bv_set:
                    self.nodes.remove(node)
                    logger.debug(f'Removendo node {node}. Bv nao definido')
                else:
                    logger.debug(f'Bv para node {node} ({len(node.bv_set)}): '
                                 f'{node.bv_set}')

            else:
                node.bv_set = {node.mac}
                logger.debug(f'Bv para node {node}: {node.bv_set}')
            # v ∈ N or |DNv| != 2
            if node in self.netnodes \
                    or len(get_active_ports(node, *self.netnodes)) != 2:
                node._value_nv = len(node.bv_set) - 0.5  # nv = |Bv| - 1/2
            else:
                node._value_nv = len(node.bv_set)  # nv = |Bv|
            logger.debug(f'Value_nv para node {node}: {node._value_nv}')

        node_values = [(node.value_nv, node) for node in self.nodes]
        # L =  sorted Vn - {r}
        self.sorted_l = [node for (value, node)
                         in sorted(node_values, reverse=True)]
        vertex = Vertex(self.sorted_l.pop(0))  # new vertex y with Cy = {r}
        self.vertices.add(vertex)
        self.root_vertex = vertex
        for port in get_active_ports(self.root, *self.netnodes):  # k ∈ DNr
            arch_out = Arch(vertex, port, netnodes=self.netnodes)
            self.arches.add(arch_out)
            self.frontier_set.add(arch_out)

        # main loop
        while self.sorted_l:
            node = self.sorted_l.pop(0)  # v'
            arch_a = self.find_arch(node.bv_set)  # acha a de Bv'
            if not arch_a:
                logger.error(f'Arco nao encontrado para {node}')
                logger.debug(f"lista 'L' {self.sorted_l}")
                logger.debug(f"Node' {node} Bv: {node.bv_set}")
                # breakpoint()
                continue
            vertex = arch_a._endpoint_a  # y = start a in Y
            if vertex.value_n == node.value_nv:
                vertex._nodes_set.add(node)  # Cy U {v'}
            else:
                self.frontier_set.remove(arch_a)  # Z - {a}
                next_vertex = Vertex(node)  # new y'
                self.vertices.add(next_vertex)
                # pprint(f" v: {vertex}")
                # pprint(f" v': {next_vertex}")
                ports = get_active_ports(node, *self.netnodes)
                port_leaves = ports - {get_port(node, self.root)}
                for port in port_leaves:  # port_leaves = DNv' - {v(r)}
                    arch_out = Arch(next_vertex,
                                    port,
                                    endpoint_b=None,
                                    port_b=None,
                                    netnodes=self.netnodes)
                    self.arches.add(arch_out)
                    self.frontier_set.add(arch_out)  # a'

                if arch_a.reachable_mac == node.bv_set:  # Ba = Bv'
                    arch_a._endpoint_b = next_vertex  # y' connect to a
                elif not vertex.nodes_set:  # Cy = 0
                    new_arch = Arch(vertex,
                                    port_a=None,
                                    endpoint_b=None,
                                    port_b=None,
                                    netnodes=self.netnodes)  # â
                    self.arches.add(new_arch)
                    new_arch.reachable_mac \
                        = arch_a.reachable_mac - node.bv_set
                    self.frontier_set.add(new_arch)  # Z U â
                    arch_a._endpoint_b = next_vertex  # y' connect to a
                    arch_a.reachable_mac = node.bv_set
                else:
                    vertex_x = Vertex(Hub())  # create HUB x with Cx = 0
                    self.vertices.add(vertex_x)
                    num_nodes = len(arch_a.reachable_mac)  # |Ba|
                    vertex_x._value_ny = num_nodes - 0.5  # nx=|Ba|-1/2
                    arch_a1 = Arch(vertex_x)
                    self.arches.add(arch_a1)
                    arch_a1.reachable_mac \
                        = arch_a.reachable_mac  # Ba1 = Bv'
                    arch_a2 = Arch(vertex_x)
                    self.arches.add(arch_a2)
                    arch_a2.reachable_mac \
                        = arch_a.reachable_mac - node.bv_set  # Ba2
                    self.frontier_set.add(arch_a2)
                    arch_a._endpoint_b = vertex_x  # x connect to a
                    arch_a1._endpoint_b = next_vertex  # y' to a1
        SkeletonTree._all.add(self)
        logger.info(f"Criada Skeleton Tree H(Y, A): {self}")

        sorted_l = sorted([(node.value_nv, node)
                           for node in self.nodes], reverse=True)
        logger.debug(f"Nodes em 'L': {sorted_l}")

        logger.info(f">>> Vertices 'Y': ({len(self.vertices)})")
        logger.debug(self.vertices)

        logger.info(f">>> Arcos 'A': ({len(self.arches)})")
        logger.debug(self.arches)

    def __repr__(self):
        if hasattr(self, 'subnet'):
            return self.__class__.__name__ + f"({self.subnet.compressed!r})"
        elif hasattr(self, 'name'):
            return self.__class__.__name__ + self.name
        return self.__class__.__name__ + f"('__init__')"

    @property
    def macs(self) -> Set[EUI]:
        """Retorna conjunto VN com objetos EUI de MACs dos nodes

        :return: conjunto VN com EUIs
        :rtype: set
        """
        return {node.mac for node in self.nodes}

    @property
    def netmacs(self) -> Set[EUI]:
        """Retorna conjunto N de objetos EUI com MACs dos nodes

        :return: conjunto N com EUIs
        :rtype: set
        """
        return {node.mac for node in self.netnodes}

    @property
    def leaves(self) -> set:
        """
        Conjunto de folhas da skeleton-tree (sem o root node)
        # N - r

        :return: Folhas da skeleton-tree
        :rtype: set
        """
        return self.netnodes - {self.root}

    def find_arch(self, reachable_leaves):
        """
        Retorna arco que acessa folhas dadas

        :param reachable_leaves: conjunto de folhas destido do arco
        :return: Arco localizado
        :rtype: Arch
        """
        total_leaves = len(reachable_leaves)
        for arch in self.frontier_set:
            if arch._reachable_nodes_set >= reachable_leaves \
                    or arch.reachable_mac >= reachable_leaves:
                return arch
            elif len(arch._reachable_nodes_set) >= total_leaves - 3 \
                or len(arch.reachable_mac) >= total_leaves - 3:
                logger.warning(f'Arco {arch} proximo.')
                logger.debug(f'node_set {arch._reachable_nodes_set}')
                logger.debug(f'mac_set {arch.reachable_mac}')

        logger.warning(f'Arco nao encontrado para {reachable_leaves}')
        logger.debug(f'arcos fronteira: {self.frontier_set}')

    def get_children(self, vertex: Vertex) -> List[Vertex]:
        """
        Retorna lista de vertex filhos tendo como referencia vertex dado

        :param vertex: Vertex de referencia
        :return: Vertex filhos
        :rtype: list
        """
        ordered = sorted(self.vertices, key=lambda vertex: vertex._value_ny,
                         reverse=True)
        return ordered[ordered.index(vertex) + 1:]

    @property
    def anchors(self) -> Set[NodeL3]:
        """
        Retorna conjunto de vertices que sao anchoras de uma skeleton-tree dada
        :return: Conjunto de Ancoras
        :rtype: set
        """
        anchors = set()
        for vertice in self.vertices:
            if len(vertice.nodes_set) == 1:
                for node in vertice.nodes_set:
                    anchors.add(node)
        return anchors
        # return {vertice._nodes_set for vertice in self.vertices
        #         if len(vertice.nodes_set) == 1}


# %% Funcao ext_aft para aft estendida
def ext_aft(y_vertex: Vertex, x_anchors: Set[NodeL3], skeleton: SkeletonTree) \
        -> Set[NodeL3]:
    """
    Expande a tabela AFT com base em vertice raiz e ancoras de entrada para
    SkeletonTree especificada. Atualiza recursivamente a base da tabela AFT
    conforme necessario.

    :param y_vertex: vertex raiz da SkeletonTree
    :param x_anchors: conjunto de ancoras iniciais
    :param skeleton: SkeletonTree de referencia
    :return: Conjunto de nodes ancoras
    :rtype: set
    """
    x_child = dict()  # Xyi
    children = skeleton.get_children(y_vertex)
    from_node = list(y_vertex._nodes_set)[0]
    for child in children:  # for child yj
        to_node = list(child._nodes_set)[0]
        if isinstance(to_node, (LeafNode, Hub)):
            continue
            # return {child}
        else:
            # if isinstance(from_node, Hub) or isinstance(to_node, Hub)
            index = get_port(from_node, to_node)
            # Xyj = ExtendedAFTs(yj,X H(Y,A))
            x_child[index] = ext_aft(child, x_anchors, skeleton)

    x_child_union = set()
    for value in x_child.values():
        x_child_union.union(value)  # (U Xyj)

    # Xy = (U Xyj) U (X ∩ Cy)
    xy = x_child_union | (x_anchors & y_vertex.nodes_set)
    for node in y_vertex.nodes_set:  # node v ∈ Cy
        if isinstance(node, InternalNode) and node != skeleton.root:
            port_root = get_port(node, skeleton.root)  # v(r)

            aft = set(node.aft_atports(port_root))  # Fv,v(r)
            aft.union(x_anchors - xy)  # Fv,v(r) U (X - Xy)
            node.set_aft(port_root, aft)  # Fv,v(r) = Fv,v(r) U (X - Xy)

            for port in x_child.keys():  # v,kj
                aft_child = set(node.aft_atports(port))  # Fv,kj
                aft_child.union(x_child[port])
                node.set_aft(port, aft_child)
        else:
            continue

    return xy


# %% Funcao get_aft retorna aft em porta especifica do node
def get_aft(node: Union[bytes, str, LeafNode, InternalNode],
            port: str,
            *netnodes) -> Set[NodeL3]:
    """Retorna conjunto de nodes acessados pela porta fornecida. Opcional definir
    filtro de nodes destino como referencia.

    :param node: node origem
    :param port: interface do node para coletar informacao
    :param netnodes: (opcional) filtra somente os nodes fornecidos
    :return: nodes acessados pela porta
    :rtype: set
    """
    source_node = get_node(node)
    aft_atport = source_node.aft_atports(port)
    if not aft_atport:
        return {source_node}
    aft = {get_node(mac) for mac in aft_atport}
    if netnodes:
        return {aft_node for aft_node in aft
                for node in netnodes
                if aft_node == node}
    else:
        return {get_node(aft_node) for aft_node in aft}


def boneprint(skeleton: SkeletonTree, verbose: bool = True) -> None:
    """
    Imprime dados da SkeletonTree informada.
    Vertices, Arcos e Lista hierarquica de nodes.

    :param skeleton: SkeletonTree para imprimir
    :param verbose: modo detalhado de dados
    :type skeleton: SkeletonTree
    :type verbose: bool
    :rtype: None
    """
    if verbose:
        print("\n" + f"Skeleton Tree H(Y, A): {skeleton}")

        print(">>> Lista 'L' de Nodes ordenados por value_n:")
        pprint(sorted([(node.value_nv, node)
                       for node in skeleton.nodes], reverse=True))

        print(f">>> Vertices 'Y': ({len(skeleton.vertices)})")
        pprint(skeleton.vertices)

        print(f">>> Arcos 'A': ({len(skeleton.arches)})")
        pprint(skeleton.arches)
    else:
        print("\n" + f"Skeleton Tree H(Y, A): {skeleton}")

        print(f">>> Lista 'L' de Nodes descobertos ordenados: "
              f"({len(skeleton.nodes)})")
        lista_l = sorted([(node.value_nv, node)
                          for node in skeleton.nodes], reverse=True)
        for value, node in lista_l:
            print(f"({value}, {node.name})")

        node_list = []
        for vertice in skeleton.vertices:
            for node in vertice._nodes_set:
                if isinstance(node, (LeafNode, InternalNode)):
                    node_list.append([node.name, node.ip.compressed])
                else:
                    node_list.append([node.name, None])

        print(f">>> Vertices 'Y': ({len(node_list)})")
        for node_name, node_ip in sorted(node_list):
            print(f"{node_name}, {node_ip}")

        print(f">>> Arcos 'A': ({len(skeleton.arches)})")
        arco_simples = []
        for arco in skeleton.arches:
            for node in arco._endpoint_a._nodes_set:
                endpoint_a = node.name
            for node in arco._endpoint_b._nodes_set:
                endpoint_b = node.name
            arco_simples.append(sorted([endpoint_a, endpoint_b]))
        for node_a, node_b in sorted(arco_simples):
            print(f"{{{node_a}, {node_b}}}")


def subnet_creator(sw_subnet: Union[str, IPv4Network, SubNet],
                   *subnets: Union[str, IPv4Network, SubNet]) \
        -> Set[SubNet]:
    """
    Verifica se redes existem e retorna objetos Subnets para cada uma
    fornecida. Cria objetos SubNet conforme necessario. Primeira rede referente
     a que contem switches gerenciaveis (respondem SNMP).

    :param sw_subnet: rede dos switches gerenciaveis
    :param subnets: redes a serem criadas
    :return: conjunto de redes
    :rtype: set
    """
    # logger.info('Criando SubNets...')
    found_subnet = get_subnet(sw_subnet)
    if found_subnet:
        found_subnet._has_switches = True
        nets = {found_subnet}
    else:
        nets = {SubNet(sw_subnet, has_switches=True)}
    for subnet in subnets:
        found_subnet = get_subnet(subnet)
        if found_subnet:
            nets.update({found_subnet})
        else:
            nets.add(SubNet(subnet))
    logger.info(f'SubNets criadas: {len(nets)}')
    return nets


def subnet_ips(subnets=3, prefix=None, mask=None):
    """
    Retorna gerador com IP de subnets.
    prefixo de 2 octedos em decimal: '10.0' (padrao), '192.168'

    :param subnets:
    :param prefix:
    :return:
    """
    if not prefix:
        prefix = '10.0'
    if not mask:
        mask = 24
    return (f'{prefix}.{subnet+1}.0/{mask}'
            for subnet in range(subnets))


# %% main
def main():
    """
        Executa funcoes para criacao da skeleton tree [em desenvolvimento]
        ----
    """
    global mymac, SNMP_DATA, ARP_TABLE_DATA, AUTOFILL_MODE
    AUTOFILL_MODE = False

    # 1) OBTENDO DADOS

    sw_subnet = '10.0.0.0/24'  # subnet que contem switches gerenciaveis (snmp)
    redes = subnet_creator(
        sw_subnet, '10.0.10.0/24', '10.0.20.0/24', '10.0.30.0/24')
    sw_subnet = get_subnet(sw_subnet)
    internal_nodes = \
        ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5', '10.0.0.6']
    if AUTOFILL_MODE:
        SNMP_DATA = auto_snmp_data(complete_aft=False)
        ARP_TABLE_DATA = auto_arp_table_data()
        for rede in redes:
            rede.arp_table = ARP_TABLE_DATA.get(rede.compressed)
    else:
        nms_config(True)
        ARP_TABLE_DATA = dict()
        for rede in redes:
            rede.arp_table = \
                set_arp_table(rede,
                              probes=1,
                              timeout=3,
                              include_me=True,
                              mode='arp')
            ARP_TABLE_DATA[rede.compressed] = rede.arp_table
        # breakpoint()
        SNMP_DATA = get_snmp_data(*internal_nodes)

    # mymac = get_mymac(interface='ens33')
    # mymac = get_mymac(interface='enp0s17')

    for rede in redes:
        rede.set_all_nodes()
    for inode in sw_subnet.internal_nodes:
        inode.set_associated_subnets()

    if AUTOFILL_MODE:
        my_ips = ['10.0.0.111', '10.0.10.111', '10.0.20.111', '10.0.30.111']
    else:
        my_ips = get_myip()
    for my_ip in my_ips:
        set_root(my_ip)

    print("\n" + f"Nodes descobertos: ({len(Node._all)})")
    pprint(Node._all)

    print("\n" + f"Inodes: ({len(InternalNode._allinodes_set)})")
    pprint(InternalNode._allinodes_set)
    # procedimento atualiza aft parcial conforme topologia de referencia
    # for inode in InternalNode._allinodes_set:
    #     inode: InternalNode
    #     print(f"{inode} antes: ")
    #     pprint(inode.aft)
    #     for port, mac in aft_fdb[inode.compressed].items():
    #         inode.set_aft(port, *mac)
    #     inode.set_associated_subnets
    #     print('depois:')
    #     pprint(inode.aft)
    #     print()

    # 2) INFERINDO TOPOLOGIA
    skeletons: List[SkeletonTree] = list()
    for subnet in SubNet._all:  # subnet Ni ∈ 'N'
        if subnet._has_switches:
            continue
        # SkeletonTree(Ni,Vni,ri,AFTs)
        if not AUTOFILL_MODE:
            set_root(subnet=subnet)
        skeletons.append(SkeletonTree(subnet.leaf_nodes,  # Ni
                                      subnet.nodes_set,  # Vni
                                      get_root(subnet),  # ri
                                      subnet))

        bone: SkeletonTree = skeletons[-1]  # Hi(Yi,Ai)
        # ExtendedAFTs(yj,X H(Y,A))
        ext_aft(bone.root_vertex,  # yj
                bone.anchors,  # X
                bone)  # H(Y,A)
        boneprint(bone)

    # for skeleton in skeletons:
    #     boneprint(skeleton)

    while len(skeletons) >= 2 and skeletons[0].anchors & skeletons[1].anchors:
        first, second = skeletons[0], skeletons[1]  # Hi and Hj
        new_netnodes = first.netnodes | second.netnodes  # Nk = Ni U Nj
        anchors_inter = first.anchors & second.anchors
        new_root = anchors_inter.pop()  # rk = any node in Xi ∩ Xj
        new_nodes = first.nodes | second.nodes  # VNk = VNi U VNj
        new_skeleton = SkeletonTree(new_netnodes,
                                    new_nodes,
                                    new_root,
                                    remove=['10.0.10.111',
                                            '10.0.20.111',
                                            '10.0.30.111'])
        ext_aft(new_skeleton.root_vertex,
                new_skeleton.anchors,
                new_skeleton)
        skeletons.remove(first)
        skeletons.remove(second)
        skeletons.append(new_skeleton)
    united_skeleton = skeletons.pop()
    boneprint(united_skeleton)
    boneprint(united_skeleton, verbose=False)

    # Gerando grafos
    print('\nGerando grafos')
    grafo = nx.Graph([(arco._endpoint_a, arco._endpoint_b)
                      for arco in united_skeleton.arches])
    # for arco in united_skeleton.arches:
    #     grafo.add_edge(arco._endpoint_a, arco._endpoint_b)
    # grafo.add_edges_from([(arco._endpoint_a, arco._endpoint_b)
    #                       for arco in united_skeleton.arches])
    pprint(sorted(list(grafo.nodes), reverse=True))
    pprint(list(zip(nx.convert_node_labels_to_integers(grafo, 1),
                    sorted(list(grafo.nodes), reverse=True))))
    pprint(f"Grau {sorted(list(grafo.nodes), reverse=True)[0]}: "
           f"{grafo.degree(sorted(list(grafo.nodes), reverse=True)[0])}")
    # pprint(grafo.degree(sorted(list(grafo.nodes), reverse=True)[0]))
    dict(nx.all_pairs_shortest_path(grafo))

    options = {
        'node_color': 'lightblue',
        # 'node_size': 500,
        'width': 2,
        'with_labels': True
        # 'font_weight': 'bold'
    }
    # plt.subplot()
    nx.draw(grafo, **options)
    plt.show()


# %% executa main()
if __name__ == '__main__':
    main()

# 2018-11-06
# autofil on, incomplete AFT
#
# Nodes descobertos: (22)
# {InternalNode('10.0.0.1/24', '003e.5c01.8001'),
#  InternalNode('10.0.0.2/24', '003e.5c02.8001'),
#  InternalNode('10.0.0.3/24', '003e.5c03.8001'),
#  InternalNode('10.0.0.4/24', '003e.5c04.8001'),
#  InternalNode('10.0.0.5/24', '003e.5c05.8001'),
#  InternalNode('10.0.0.6/24', '003e.5c06.8001'),
#  LeafNode('10.0.10.1/24', '0050.7966.680c'),
#  LeafNode('10.0.10.2/24', '0050.7966.6805'),
#  LeafNode('10.0.10.3/24', '0050.7966.6809'),
#  LeafNode('10.0.10.4/24', '0050.7966.680a'),
#  LeafNode('10.0.10.5/24', '0050.7966.6808'),
#  LeafNode('10.0.10.6/24', '0050.7966.6807'),
#  LeafNode('10.0.10.111/24', '000c.295c.4271'),
#  LeafNode('10.0.20.1/24', '0050.7966.6802'),
#  LeafNode('10.0.20.2/24', '0050.7966.6803'),
#  LeafNode('10.0.20.3/24', '0050.7966.6804'),
#  LeafNode('10.0.20.4/24', '0050.7966.6806'),
#  LeafNode('10.0.20.111/24', '000c.295c.4271'),
#  LeafNode('10.0.30.1/24', '0050.7966.6800'),
#  LeafNode('10.0.30.2/24', '0050.7966.680b'),
#  LeafNode('10.0.30.3/24', '0050.7966.6801'),
#  LeafNode('10.0.30.111/24', '000c.295c.4271')}
#
# Inodes: (6)
# {InternalNode('10.0.0.1/24', '003e.5c01.8001'),
#  InternalNode('10.0.0.2/24', '003e.5c02.8001'),
#  InternalNode('10.0.0.3/24', '003e.5c03.8001'),
#  InternalNode('10.0.0.4/24', '003e.5c04.8001'),
#  InternalNode('10.0.0.5/24', '003e.5c05.8001'),
#  InternalNode('10.0.0.6/24', '003e.5c06.8001')}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.10.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(7.5, LeafNode('10.0.10.111/24', '000c.295c.4271')),
#  (5.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (4.5, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (1.5, InternalNode('10.0.0.5/24', '003e.5c05.8001')),
#  (0.5, LeafNode('10.0.10.6/24', '0050.7966.6807')),
#  (0.5, LeafNode('10.0.10.5/24', '0050.7966.6808')),
#  (0.5, LeafNode('10.0.10.4/24', '0050.7966.680a')),
#  (0.5, LeafNode('10.0.10.3/24', '0050.7966.6809')),
#  (0.5, LeafNode('10.0.10.2/24', '0050.7966.6805')),
#  (0.5, LeafNode('10.0.10.1/24', '0050.7966.680c'))]
# >>> Vertices 'Y': (12)
# {Vertex({'leaf_1*root*'}),
#  Vertex({'v1'}),
#  Vertex({'v5'}),
#  Vertex({'v2'}),
#  Vertex({'v3'}),
#  Vertex({'hub_1'}),
#  Vertex({'leaf_7'}),
#  Vertex({'leaf_4'}),
#  Vertex({'leaf_6'}),
#  Vertex({'leaf_5'}),
#  Vertex({'leaf_3'}),
#  Vertex({'leaf_2'})}
# >>> Arcos 'A': (11)
# {Arch(Vertex({'leaf_1*root*'}), '1', Vertex({'v1'}), None),
#  Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v1'}), '15', Vertex({'leaf_2'}), None),
#  Arch(Vertex({'v3'}), '16', Vertex({'leaf_3'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'hub_1'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v5'}), '16', Vertex({'leaf_5'}), None),
#  Arch(Vertex({'v5'}), '15', Vertex({'leaf_4'}), None),
#  Arch(Vertex({'hub_1'}), None, Vertex({'v5'}), None),
#  Arch(Vertex({'hub_1'}), None, Vertex({'leaf_7'}), None),
#  Arch(Vertex({'hub_1'}), None, Vertex({'leaf_6'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.20.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(5.5, LeafNode('10.0.20.111/24', '000c.295c.4271')),
#  (4, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (3.5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (1.5, InternalNode('10.0.0.4/24', '003e.5c04.8001')),
#  (1, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (0.5, LeafNode('10.0.20.4/24', '0050.7966.6806')),
#  (0.5, LeafNode('10.0.20.3/24', '0050.7966.6804')),
#  (0.5, LeafNode('10.0.20.2/24', '0050.7966.6803')),
#  (0.5, LeafNode('10.0.20.1/24', '0050.7966.6802'))]
# >>> Vertices 'Y': (9)
# {Vertex({'leaf_8*root*'}),
#  Vertex({'v2'}),
#  Vertex({'leaf_11'}),
#  Vertex({'v1'}),
#  Vertex({'v4'}),
#  Vertex({'v3'}),
#  Vertex({'leaf_12'}),
#  Vertex({'leaf_10'}),
#  Vertex({'leaf_9'})}
# >>> Arcos 'A': (8)
# {Arch(Vertex({'v2'}), '16', Vertex({'leaf_11'}), None),
#  Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v2'}), '2', Vertex({'v4'}), None),
#  Arch(Vertex({'leaf_8*root*'}), '1', Vertex({'v1'}), None),
#  Arch(Vertex({'v4'}), '15', Vertex({'leaf_9'}), None),
#  Arch(Vertex({'v4'}), '16', Vertex({'leaf_10'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'leaf_12'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.30.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(4.5, LeafNode('10.0.30.111/24', '000c.295c.4271')),
#  (2.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (1.5, InternalNode('10.0.0.6/24', '003e.5c06.8001')),
#  (0.5, LeafNode('10.0.30.3/24', '0050.7966.6801')),
#  (0.5, LeafNode('10.0.30.2/24', '0050.7966.680b')),
#  (0.5, LeafNode('10.0.30.1/24', '0050.7966.6800'))]
# >>> Vertices 'Y': (6)
# {Vertex({'v1'}),
#  Vertex({'leaf_13*root*'}),
#  Vertex({'leaf_16'}),
#  Vertex({'leaf_14'}),
#  Vertex({'leaf_15'}),
#  Vertex({'v6'})}
# >>> Arcos 'A': (5)
# {Arch(Vertex({'v1'}), '2', Vertex({'v6'}), None),
#  Arch(Vertex({'v6'}), '15', Vertex({'leaf_14'}), None),
#  Arch(Vertex({'leaf_13*root*'}), '1', Vertex({'v1'}), None),
#  Arch(Vertex({'v6'}), '16', Vertex({'leaf_15'}), None),
#  Arch(Vertex({'v1'}), '16', Vertex({'leaf_16'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('bone_5')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(14.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (8.5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (6, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (2, InternalNode('10.0.0.6/24', '003e.5c06.8001')),
#  (2, InternalNode('10.0.0.5/24', '003e.5c05.8001')),
#  (2, InternalNode('10.0.0.4/24', '003e.5c04.8001')),
#  (0.5, LeafNode('10.0.30.3/24', '0050.7966.6801')),
#  (0.5, LeafNode('10.0.30.2/24', '0050.7966.680b')),
#  (0.5, LeafNode('10.0.30.1/24', '0050.7966.6800')),
#  (0.5, LeafNode('10.0.20.4/24', '0050.7966.6806')),
#  (0.5, LeafNode('10.0.20.3/24', '0050.7966.6804')),
#  (0.5, LeafNode('10.0.20.2/24', '0050.7966.6803')),
#  (0.5, LeafNode('10.0.20.1/24', '0050.7966.6802')),
#  (0.5, LeafNode('10.0.10.6/24', '0050.7966.6807')),
#  (0.5, LeafNode('10.0.10.5/24', '0050.7966.6808')),
#  (0.5, LeafNode('10.0.10.4/24', '0050.7966.680a')),
#  (0.5, LeafNode('10.0.10.3/24', '0050.7966.6809')),
#  (0.5, LeafNode('10.0.10.2/24', '0050.7966.6805')),
#  (0.5, LeafNode('10.0.10.1/24', '0050.7966.680c'))]
# >>> Vertices 'Y': (20)
# {Vertex({'v1'}),
#  Vertex({'v2'}),
#  Vertex({'v3'}),
#  Vertex({'v6'}),
#  Vertex({'v5'}),
#  Vertex({'hub_3'}),
#  Vertex({'v4'}),
#  Vertex({'leaf_16'}),
#  Vertex({'leaf_15'}),
#  Vertex({'leaf_14'}),
#  Vertex({'leaf_12'}),
#  Vertex({'leaf_11'}),
#  Vertex({'leaf_10'}),
#  Vertex({'leaf_9'}),
#  Vertex({'leaf_7'}),
#  Vertex({'leaf_6'}),
#  Vertex({'leaf_5'}),
#  Vertex({'leaf_4'}),
#  Vertex({'leaf_3'}),
#  Vertex({'leaf_2'})}
# >>> Arcos 'A': (19)
# {Arch(Vertex({'v1'}), '2', Vertex({'v6'}), None),
#  Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v1'}), '16', Vertex({'leaf_16'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v1'}), '15', Vertex({'leaf_2'}), None),
#  Arch(Vertex({'v2'}), '2', Vertex({'v4'}), None),
#  Arch(Vertex({'v2'}), '16', Vertex({'leaf_11'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'hub_3'}), None),
#  Arch(Vertex({'v3'}), '16', Vertex({'leaf_3'}), None),
#  Arch(Vertex({'v6'}), '16', Vertex({'leaf_15'}), None),
#  Arch(Vertex({'v6'}), '15', Vertex({'leaf_14'}), None),
#  Arch(Vertex({'v5'}), '16', Vertex({'leaf_5'}), None),
#  Arch(Vertex({'v5'}), '15', Vertex({'leaf_4'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'v5'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_12'}), None),
#  Arch(Vertex({'v4'}), '16', Vertex({'leaf_10'}), None),
#  Arch(Vertex({'v4'}), '15', Vertex({'leaf_9'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_7'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_6'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('bone_5')
# >>> Lista 'L' de Nodes descobertos ordenados: (19)
# (14.5, v1)
# (8.5, v2)
# (6, v3)
# (2, v6)
# (2, v5)
# (2, v4)
# (0.5, leaf_16)
# (0.5, leaf_15)
# (0.5, leaf_14)
# (0.5, leaf_12)
# (0.5, leaf_11)
# (0.5, leaf_10)
# (0.5, leaf_9)
# (0.5, leaf_7)
# (0.5, leaf_6)
# (0.5, leaf_5)
# (0.5, leaf_4)
# (0.5, leaf_3)
# (0.5, leaf_2)
# >>> Vertices 'Y': (20)
# hub_3, None
# leaf_10, 10.0.20.2
# leaf_11, 10.0.20.3
# leaf_12, 10.0.20.4
# leaf_14, 10.0.30.1
# leaf_15, 10.0.30.2
# leaf_16, 10.0.30.3
# leaf_2, 10.0.10.1
# leaf_3, 10.0.10.2
# leaf_4, 10.0.10.3
# leaf_5, 10.0.10.4
# leaf_6, 10.0.10.5
# leaf_7, 10.0.10.6
# leaf_9, 10.0.20.1
# v1, 10.0.0.1
# v2, 10.0.0.2
# v3, 10.0.0.3
# v4, 10.0.0.4
# v5, 10.0.0.5
# v6, 10.0.0.6
# >>> Arcos 'A': (19)
# {hub_3, leaf_12}
# {hub_3, leaf_6}
# {hub_3, leaf_7}
# {hub_3, v3}
# {hub_3, v5}
# {leaf_10, v4}
# {leaf_11, v2}
# {leaf_14, v6}
# {leaf_15, v6}
# {leaf_16, v1}
# {leaf_2, v1}
# {leaf_3, v3}
# {leaf_4, v5}
# {leaf_5, v5}
# {leaf_9, v4}
# {v1, v2}
# {v1, v6}
# {v2, v3}
# {v2, v4}
#
######################################################################
# autofill off, aft incomplete
#
# Nodes descobertos: (23)
# {InternalNode('10.0.0.1/24', '003e.5c01.8001'),
#  InternalNode('10.0.0.2/24', '003e.5c02.8001'),
#  InternalNode('10.0.0.3/24', '003e.5c03.8001'),
#  InternalNode('10.0.0.4/24', '003e.5c04.8001'),
#  InternalNode('10.0.0.5/24', '003e.5c05.8001'),
#  InternalNode('10.0.0.6/24', '003e.5c06.8001'),
#  LeafNode('10.0.0.111/24', '000c.295c.4271'),
#  LeafNode('10.0.10.1/24', '0050.7966.6801'),
#  LeafNode('10.0.10.2/24', '0050.7966.6809'),
#  LeafNode('10.0.10.3/24', '0050.7966.680b'),
#  LeafNode('10.0.10.4/24', '0050.7966.6805'),
#  LeafNode('10.0.10.5/24', '0050.7966.6803'),
#  LeafNode('10.0.10.6/24', '0050.7966.6802'),
#  LeafNode('10.0.10.111/24', '000c.295c.4271'),
#  LeafNode('10.0.20.1/24', '0050.7966.6800'),
#  LeafNode('10.0.20.2/24', '0050.7966.680a'),
#  LeafNode('10.0.20.3/24', '0050.7966.680c'),
#  LeafNode('10.0.20.4/24', '0050.7966.6808'),
#  LeafNode('10.0.20.111/24', '000c.295c.4271'),
#  LeafNode('10.0.30.1/24', '0050.7966.6804'),
#  LeafNode('10.0.30.2/24', '0050.7966.6806'),
#  LeafNode('10.0.30.3/24', '0050.7966.6807'),
#  LeafNode('10.0.30.111/24', '000c.295c.4271')}
#
# Inodes: (6)
# {InternalNode('10.0.0.1/24', '003e.5c01.8001'),
#  InternalNode('10.0.0.2/24', '003e.5c02.8001'),
#  InternalNode('10.0.0.3/24', '003e.5c03.8001'),
#  InternalNode('10.0.0.4/24', '003e.5c04.8001'),
#  InternalNode('10.0.0.5/24', '003e.5c05.8001'),
#  InternalNode('10.0.0.6/24', '003e.5c06.8001')}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.10.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(7.5, LeafNode('10.0.10.111/24', '000c.295c.4271')),
#  (5.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (4.5, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (1.5, InternalNode('10.0.0.5/24', '003e.5c05.8001')),
#  (0.5, LeafNode('10.0.10.6/24', '0050.7966.6802')),
#  (0.5, LeafNode('10.0.10.5/24', '0050.7966.6803')),
#  (0.5, LeafNode('10.0.10.4/24', '0050.7966.6805')),
#  (0.5, LeafNode('10.0.10.3/24', '0050.7966.680b')),
#  (0.5, LeafNode('10.0.10.2/24', '0050.7966.6809')),
#  (0.5, LeafNode('10.0.10.1/24', '0050.7966.6801'))]
# >>> Vertices 'Y': (12)
# {Vertex({'leaf_5'}),
#  Vertex({'leaf_6'}),
#  Vertex({'leaf_3'}),
#  Vertex({'leaf_2'}),
#  Vertex({'leaf_4'}),
#  Vertex({'leaf_8*root*'}),
#  Vertex({'leaf_7'}),
#  Vertex({'hub_1'}),
#  Vertex({'v2'}),
#  Vertex({'v5'}),
#  Vertex({'v1'}),
#  Vertex({'v3'})}
# >>> Arcos 'A': (11)
# {Arch(Vertex({'hub_1'}), None, Vertex({'leaf_6'}), None),
#  Arch(Vertex({'hub_1'}), None, Vertex({'leaf_7'}), None),
#  Arch(Vertex({'hub_1'}), None, Vertex({'v5'}), None),
#  Arch(Vertex({'v5'}), '15', Vertex({'leaf_4'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'hub_1'}), None),
#  Arch(Vertex({'v3'}), '16', Vertex({'leaf_3'}), None),
#  Arch(Vertex({'v1'}), '15', Vertex({'leaf_2'}), None),
#  Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v5'}), '16', Vertex({'leaf_5'}), None),
#  Arch(Vertex({'leaf_8*root*'}), '1', Vertex({'v1'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.20.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(5.5, LeafNode('10.0.20.111/24', '000c.295c.4271')),
#  (4, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (3.5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (1.5, InternalNode('10.0.0.4/24', '003e.5c04.8001')),
#  (1, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (0.5, LeafNode('10.0.20.4/24', '0050.7966.6808')),
#  (0.5, LeafNode('10.0.20.3/24', '0050.7966.680c')),
#  (0.5, LeafNode('10.0.20.2/24', '0050.7966.680a')),
#  (0.5, LeafNode('10.0.20.1/24', '0050.7966.6800'))]
# >>> Vertices 'Y': (9)
# {Vertex({'v2'}),
#  Vertex({'v1'}),
#  Vertex({'v4'}),
#  Vertex({'leaf_11'}),
#  Vertex({'v3'}),
#  Vertex({'leaf_12'}),
#  Vertex({'leaf_10'}),
#  Vertex({'leaf_9'}),
#  Vertex({'leaf_13*root*'})}
# >>> Arcos 'A': (8)
# {Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v2'}), '16', Vertex({'leaf_11'}), None),
#  Arch(Vertex({'v2'}), '2', Vertex({'v4'}), None),
#  Arch(Vertex({'v4'}), '15', Vertex({'leaf_9'}), None),
#  Arch(Vertex({'v4'}), '16', Vertex({'leaf_10'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'leaf_12'}), None),
#  Arch(Vertex({'leaf_13*root*'}), '1', Vertex({'v1'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('10.0.30.0/24')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(4.5, LeafNode('10.0.30.111/24', '000c.295c.4271')),
#  (2.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (1.5, InternalNode('10.0.0.6/24', '003e.5c06.8001')),
#  (0.5, LeafNode('10.0.30.3/24', '0050.7966.6807')),
#  (0.5, LeafNode('10.0.30.2/24', '0050.7966.6806')),
#  (0.5, LeafNode('10.0.30.1/24', '0050.7966.6804'))]
# >>> Vertices 'Y': (6)
# {Vertex({'leaf_16'}),
#  Vertex({'leaf_17*root*'}),
#  Vertex({'v1'}),
#  Vertex({'leaf_14'}),
#  Vertex({'leaf_15'}),
#  Vertex({'v6'})}
# >>> Arcos 'A': (5)
# {Arch(Vertex({'v1'}), '2', Vertex({'v6'}), None),
#  Arch(Vertex({'v6'}), '15', Vertex({'leaf_14'}), None),
#  Arch(Vertex({'leaf_17*root*'}), '1', Vertex({'v1'}), None),
#  Arch(Vertex({'v1'}), '16', Vertex({'leaf_16'}), None),
#  Arch(Vertex({'v6'}), '16', Vertex({'leaf_15'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('bone_5')
# >>> Lista 'L' de Nodes ordenados por value_n:
# [(14.5, InternalNode('10.0.0.1/24', '003e.5c01.8001')),
#  (8.5, InternalNode('10.0.0.2/24', '003e.5c02.8001')),
#  (6, InternalNode('10.0.0.3/24', '003e.5c03.8001')),
#  (2, InternalNode('10.0.0.6/24', '003e.5c06.8001')),
#  (2, InternalNode('10.0.0.5/24', '003e.5c05.8001')),
#  (2, InternalNode('10.0.0.4/24', '003e.5c04.8001')),
#  (0.5, LeafNode('10.0.30.3/24', '0050.7966.6807')),
#  (0.5, LeafNode('10.0.30.2/24', '0050.7966.6806')),
#  (0.5, LeafNode('10.0.30.1/24', '0050.7966.6804')),
#  (0.5, LeafNode('10.0.20.4/24', '0050.7966.6808')),
#  (0.5, LeafNode('10.0.20.3/24', '0050.7966.680c')),
#  (0.5, LeafNode('10.0.20.2/24', '0050.7966.680a')),
#  (0.5, LeafNode('10.0.20.1/24', '0050.7966.6800')),
#  (0.5, LeafNode('10.0.10.6/24', '0050.7966.6802')),
#  (0.5, LeafNode('10.0.10.5/24', '0050.7966.6803')),
#  (0.5, LeafNode('10.0.10.4/24', '0050.7966.6805')),
#  (0.5, LeafNode('10.0.10.3/24', '0050.7966.680b')),
#  (0.5, LeafNode('10.0.10.2/24', '0050.7966.6809')),
#  (0.5, LeafNode('10.0.10.1/24', '0050.7966.6801'))]
# >>> Vertices 'Y': (20)
# {Vertex({'v1'}),
#  Vertex({'v2'}),
#  Vertex({'v3'}),
#  Vertex({'v6'}),
#  Vertex({'v5'}),
#  Vertex({'hub_3'}),
#  Vertex({'v4'}),
#  Vertex({'leaf_16'}),
#  Vertex({'leaf_15'}),
#  Vertex({'leaf_14'}),
#  Vertex({'leaf_12'}),
#  Vertex({'leaf_11'}),
#  Vertex({'leaf_10'}),
#  Vertex({'leaf_9'}),
#  Vertex({'leaf_7'}),
#  Vertex({'leaf_6'}),
#  Vertex({'leaf_5'}),
#  Vertex({'leaf_4'}),
#  Vertex({'leaf_3'}),
#  Vertex({'leaf_2'})}
# >>> Arcos 'A': (19)
# {Arch(Vertex({'v1'}), '15', Vertex({'leaf_2'}), None),
#  Arch(Vertex({'v1'}), '2', Vertex({'v6'}), None),
#  Arch(Vertex({'v1'}), '16', Vertex({'leaf_16'}), None),
#  Arch(Vertex({'v1'}), '3', Vertex({'v2'}), None),
#  Arch(Vertex({'v2'}), '2', Vertex({'v4'}), None),
#  Arch(Vertex({'v2'}), '16', Vertex({'leaf_11'}), None),
#  Arch(Vertex({'v2'}), '3', Vertex({'v3'}), None),
#  Arch(Vertex({'v3'}), '2', Vertex({'hub_3'}), None),
#  Arch(Vertex({'v3'}), '16', Vertex({'leaf_3'}), None),
#  Arch(Vertex({'v6'}), '15', Vertex({'leaf_14'}), None),
#  Arch(Vertex({'v6'}), '16', Vertex({'leaf_15'}), None),
#  Arch(Vertex({'v5'}), '15', Vertex({'leaf_4'}), None),
#  Arch(Vertex({'v5'}), '16', Vertex({'leaf_5'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'v5'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_12'}), None),
#  Arch(Vertex({'v4'}), '15', Vertex({'leaf_9'}), None),
#  Arch(Vertex({'v4'}), '16', Vertex({'leaf_10'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_7'}), None),
#  Arch(Vertex({'hub_3'}), None, Vertex({'leaf_6'}), None)}
#
# Skeleton Tree H(Y, A): SkeletonTree('bone_5')
# >>> Lista 'L' de Nodes descobertos ordenados: (19)
# (14.5, v1)
# (8.5, v2)
# (6, v3)
# (2, v6)
# (2, v5)
# (2, v4)
# (0.5, leaf_16)
# (0.5, leaf_15)
# (0.5, leaf_14)
# (0.5, leaf_12)
# (0.5, leaf_11)
# (0.5, leaf_10)
# (0.5, leaf_9)
# (0.5, leaf_7)
# (0.5, leaf_6)
# (0.5, leaf_5)
# (0.5, leaf_4)
# (0.5, leaf_3)
# (0.5, leaf_2)
# >>> Vertices 'Y': (20)
# hub_3, None
# leaf_10, 10.0.20.2
# leaf_11, 10.0.20.3
# leaf_12, 10.0.20.4
# leaf_14, 10.0.30.1
# leaf_15, 10.0.30.2
# leaf_16, 10.0.30.3
# leaf_2, 10.0.10.1
# leaf_3, 10.0.10.2
# leaf_4, 10.0.10.3
# leaf_5, 10.0.10.4
# leaf_6, 10.0.10.5
# leaf_7, 10.0.10.6
# leaf_9, 10.0.20.1
# v1, 10.0.0.1
# v2, 10.0.0.2
# v3, 10.0.0.3
# v4, 10.0.0.4
# v5, 10.0.0.5
# v6, 10.0.0.6
# >>> Arcos 'A': (19)
# {hub_3, leaf_12}
# {hub_3, leaf_6}
# {hub_3, leaf_7}
# {hub_3, v3}
# {hub_3, v5}
# {leaf_10, v4}
# {leaf_11, v2}
# {leaf_14, v6}
# {leaf_15, v6}
# {leaf_16, v1}
# {leaf_2, v1}
# {leaf_3, v3}
# {leaf_4, v5}
# {leaf_5, v5}
# {leaf_9, v4}
# {v1, v2}
# {v1, v6}
# {v2, v3}
# {v2, v4}


# '\u2208'
# Out[2]: '∈'
# '\u2229'
# Out[24]: '∩'
