#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from pdb import set_trace as breakpoint
from esqueleto import (to_bytes, ip_mac_to_arp_table, nms_config, ping_ip,
                       auto_arp_table_data, auto_snmp_data, is_internal_node,
                       is_leaf_node, set_arp_table, get_mymac, get_myip, )
from ipaddress import IPv4Interface, IPv4Network  # ,IPv4Address
from itertools import permutations
from collections import Counter, defaultdict
from netaddr import EUI
from netaddr.strategy.eui48 import mac_cisco
from pprint import pprint
from typing import List, Union, Dict  # Tuple, Callable, Any, Union
from easysnmp import Session

# from easysnmp.exceptions import EasySNMPTimeoutError, EasySNMPConnectionError
# WARNING: No route found for IPv6 destination :: (no default route?).
# This affects only IPv6
# from scapy.all import *
# from scapy.sendrecv import srp
# from scapy.layers.l2 import Ether, ARP

# %% Constantes
YES = ON = START = True
NO = OFF = STOP = False

# %% Configuracao
AUTOFILL_MODE = ON
POST_MODE = ON
mymac = None


# %% definicao de dados
def config(internal_nodes: List[Union[str, None]] = None,
           autofill: bool = AUTOFILL_MODE) -> None:
    """
    Configura atribuicao de dados SNMP e tabela ARP
    :rtype: None
    :type internal_nodes: Lista com string de IPs dos nodes internos (switch)
    :type autofill: bool
    """
    global SNMP_DATA, ARP_TABLE_DATA
    if AUTOFILL_MODE:
        SNMP_DATA = auto_snmp_data()
        ARP_TABLE_DATA = auto_arp_table_data()
    else:
        nms_config(True)
        SNMP_DATA = get_snmp_data(*internal_nodes)
        ARP_TABLE_DATA = dict()


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
    _allsubnets_set = set()

    def __new__(cls, *args, **kargs):
        """Cria objeto SubNet e incrementa contador"""
        if cls not in SubNet._allsubnets_set:
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
        if auto_fill:
            self._arp_table = ARP_TABLE_DATA.get(self.compressed)
        else:
            self._arp_table = None
        self._internal_nodes = []
        self._leaf_nodes = []
        self._nodes = []
        if self not in SubNet._allsubnets_set:
            SubNet._allsubnets_set.add(self)

    # FIXME nao removendo do set ao deletar instancia
    # def __del__(self):
    #     print(self)
    #     SubNet.remove_subnet(self)
    #     # SubNet._num_of_nets -= 1

    @classmethod
    def remove_subnet(cls, subnet):
        """
        Remove SubNet do set de redes criadas (allsubnets_set)
        Decrementa contador de redes

        :param subnet:
        """
        cls._allsubnets_set.remove(subnet)
        cls._num_of_nets -= 1

    @property
    def num_of_nets(self):
        """Retorna Numore de redes SubNet criadas"""
        return self._num_of_nets

    @property
    def allsubnets_set(self):
        """Retorna lista com instancias SubNet criadas"""
        return self._allsubnets_set

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

    def update_arp_table(self,
                         probes=1,
                         auto_fill=AUTOFILL_MODE,
                         manual_fill=None,
                         post=POST_MODE):
        """Define atributo 'arp_table' da SubNet. Caso nao seja atribuido
        auto_fill, atualiza tabela ARP do elemento.
        """
        self._arp_table = set_arp_table(
                self, probes, auto_fill, manual_fill, post)

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
                self._internal_nodes[-1]._snmp_data = \
                    get_snmp_data(self._internal_nodes[-1])
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

    def __init__(self):
        """Inicia objeto Hub"""
        self._labeled = False
        self._port_list = None

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
        if hasattr(self, 'snmp_data'):
            return self.snmp_data.get('dot1d_tp_fdb_port')
        else:
            return self._port_list


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
    value_in_set:
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
    _all_nodes_set = set()

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

        if isinstance(mac_address, EUI):
            self._mac = mac_address
        elif isinstance(mac_address, str):
            self._mac = EUI(mac_address)
        else:
            raise Exception('Entrada MAC nao perminida')

        self._mac.dialect = mac_cisco
        self._mac_address = str(self.mac)
        self._labeled = True
        if self.network in SubNet._allsubnets_set:
            for subnet in SubNet._allsubnets_set:
                if self.network == subnet:
                    self.associated_subnets = {subnet}
        else:
            self.associated_subnets = {SubNet(self.compressed)}
            SubNet._allsubnets_set.update(self.associated_subnets)
        self._value_in_set = None  # valor do no para a lista L

    def __repr__(self):
        return self.__class__.__name__ + '(' + repr(self.with_prefixlen) \
               + ', ' + "'" + str(self._mac_address) + "')"

    @property
    def all_nodes_set(self):
        return self._all_nodes_set

    @property
    def mac(self):
        """ Retorna mac addres do node """
        return self._mac

    @property
    def mac_address(self):
        """ Retorna mac addres do node """
        return self._mac_address

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
    def value_in_set(self):
        """ Retorna valor do no para a lista L """
        return self._value_in_set

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
    _all_leaves_set = set()

    def __init__(self, ip_address, mac_address, is_root=NO):
        super().__init__(ip_address, mac_address)
        self.is_root = is_root
        LeafNode._all_leaves_set.add(self)
        Node._all_nodes_set.add(self)

    @property
    def is_root(self):
        """Indica se no folha eh root da arvore nao direcionada"""
        return self._is_root

    @property
    def all_leaves_set(self) -> set:
        """
        Conjunto com instancias LeafNode criadas

        :rtype: set
        :return: nodes do tipo folha/leave
        """
        return self._all_leaves_set

    @is_root.setter
    def is_root(self, value: bool):
        if isinstance(value, bool):
            self._is_root = value


# %% classe InternalNode
# propriedades das folhas Bv, basic property 1
#    if node in nodes:
#        assert node.leaves_size != 0
# funcoes dos nos
#    #numero nv do no para classificar em L
#    set_value()
#        if node == root
#            node.value = len(subnet.nodes) + 1/2
#        elif node in nodes and node.type
#            node.value = leaves_size - 1/2
#        else
#            node.value = leaves_size

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
        if auto_fill and SNMP_DATA.get(self.compressed):
            self._snmp_data = SNMP_DATA.get(self.compressed)
        else:
            self._snmp_data = get_snmp_data(self)

        # v(r) = porta que leva ao root
        self._port_root = None
        # DNv - v(r) = portas que levam as folhas
        self._port_leaves = None
        # Bv = lista de folhas do node na sub-rede
        self.leaves = dict()
        # |Bv| = numero de folhas Bv do node
        self._leaves_size = None
        InternalNode._allinodes_set.add(self)
        Node._all_nodes_set.add(self)

    def __del__(self):
        InternalNode._num_of_inodes -= 1

    @property
    def name(self):
        """
        Nome atribuido ao node pelo administrador da rede, coletado por snmp

        :rtype: str
        :return: sys_name snmp
        """
        return self.snmp_data.get('sys_name')

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
            print(f'Valor {value} foi atribuido pq nao e string.')

    @property
    def allinodes_set(self) -> set:
        """
        Conjunto com instancias InternalNode criadas

        :rtype: set
        :return: nodes internos
        """
        return self._allinodes_set

    # @property
    # def port_activeset(self, subnet=None):
    #     """
    #     Retorna lista de portas ativas do node
    #     # Dv = potas ativas
    #     """
    #     return {port for port, _ in self.snmp_data.get('port_activelist')}

    @property
    def port_activeset(self):
        """
        Retorna conjunto de portas ativas do node
        # Dv = potas ativas do node
        # DNv = potas ativas do node na subrede N

        Exemblo:
        ----
        >>> self.port_activeset['all']  # Dv
        ... {'3', '15', '16', '2'}
        >>> self.port_activeset['10.0.10.0/24']  # DNv
        ... {'3', '15'}

        """
        subnet_ports = defaultdict(set)
        allports = set()
        for subnet in self.associated_subnets:
            if subnet == self.network:
                continue
            for mac in subnet.mac_set:
                # breakpoint()
                for port, mac_set in self.aft_atports.items():
                    if mac in mac_set:
                        subnet_ports[subnet.address].add(port)
                        allports.add(port)
        subnet_ports['all'] = allports
        return subnet_ports

    @property
    def port_activelist(self) -> List:
        """
        Retorna lista de portas ativas do node
        # Dv = potas ativas no formato de lista
        """
        # return self._port_activelist
        return self.snmp_data.get('port_activelist')

    # FIXME InternalNode: port_root continuar
    @property
    def port_root(self):
        """
        Retorna a porta que leva ao root
        #v(r) = porta que leva ao root
        """
        subnet_ports = defaultdict(set)
        allports = set()
        for subnet in self.associated_subnets:
            if subnet == self.network:
                continue
            root = get_root(subnet)
            for mac in subnet.mac_set:
                # breakpoint()
                for port, mac_set in self.aft_atports.items():
                    if mac in mac_set:
                        subnet_ports[subnet.address].add(port)
                        allports.add(port)

        return self._port_root

    @property
    def port_leaves(self):
        """
        Retorna portas que levam aos nos folhas
        leaf ports = active - root
        #DNv - v(r) = portas que levam as folhas
        """
        return self._port_leaves

    @property
    def leaves(self):
        """
        Retorna lista de nos folhas (leaf nodes)
        #Bv = lista de folhas do no na sub-rede
        #leaves = active - root
        """
        return self._leaves

    @leaves.setter
    def leaves(self, value):
        self._leaves = value

    @property
    def leaves_size(self):
        """
        Retorna quantidade de nos folhas
        #|Bv| = numero de folhas do no
        """
        return self._leaves_size

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
        return self.snmp_data.get('dot1d_tp_fdb_address')

    @property
    def aft(self):
        """Tabela de emcaminhamento (MAC, PORTA)"""
        return list(zip(self.mac_list, self.port_list))

    @property
    def aft_atports(self) -> defaultdict:
        """Dicionario com tabela AFT de emcaminhamento para determinada porta
        Fv,k

        Exemplo:

        >>> self.aft_atports['2']
        ... {b'\x00>\\\x04\x80\x01', b'\x00Pyfh\x02', b'\x00Pyfh\x03'}
        :rtype: defaultdict
        :return: AFT em cada porta
        """
        atports = defaultdict(set)
        for mac, port in self.aft:
            atports[port].add(mac)
        return atports

    def subnet_aft_atports(self, subnet: str) -> defaultdict:
        """
        Retorna para enderecos MAC em porta especifica de uma subrede FNv,k

        :rtype: defaultdict
        :param subnet: Endereco da subrede
        :return: Dicionario portas como chaves e MACs da subrede como valor

        Exemplo:
        ----
        >>> self.subnet_aft_atports('10.0.10.0/24')
        ... defaultdict(<class 'set'>, {
        ...     '1': {b'\x00Pyfh\x05',
        ...           b'\x00Pyfh\x07',
        ...           b'\x00Pyfh\x0c',
        ...           b'\x00Pyfh\x08'},
        ...     '16': {b'\x00Pyfh\n'},
        ...     '15': {b'\x00Pyfh\t'}})
        >>> self.subnet_aft_atports('10.0.10.0/24')['15']
        ... {b'\x00Pyfh\t'}
        """
        atports = defaultdict(set)
        for rede in self.associated_subnets:
            if rede.address == subnet:
                for port, macs in self.aft_atports.items():
                    if rede.mac_set.intersection(macs):
                        atports[port].update(rede.mac_set.intersection(macs))
            else:
                continue
        return atports
    # def subnet_port_activeset(self, subnet=None):
    #     """
    #     Retorna conjunto de portas ativas do node
    #     # DNv = potas ativas na subrede N
    #     """
    #     subnet_ports = set()
    #     if isinstance(subnet,str):
    #         for rede in SubNet._allsubnets_set:
    #             if rede.address == subnet:
    #                 for mac in rede.mac_set:
    #                     # breakpoint()
    #                     for port, mac_set in self.aft_atports.items():
    #                         if mac in mac_set:
    #                             subnet_ports.add(port)
    #     return subnet_ports

    def set_associated_subnets(self):
        """
        Define redes associadas ao internal node 'v' dentre redes criadas,
        atribuindo a associated_subnets caso necessario
        v pertence a Vn
        """
        self.ports_onsubnet = defaultdict(set)
        for subnet in SubNet._allsubnets_set:
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

    # TODO: metodo set: set_port_root (get_root primeiro)
    def set_port_root(self, subnet: SubNet):
        """Define porta que liga ao root: port_root"""
        pass

    # TODO: metodo set: set_port_leaves
    def set_port_leaves(self):
        """Define lista de portas que ligam aos leave nodes: port_leaves"""
        pass

    # TODO: metodo set: set_leaves (get_root primeiro)
    # TODO: testar set_leaves
    def set_leaves(self, subnet: SubNet):
        """Define lista de folhas do node na sub-rede: leaves"""
        root = get_root(subnet)
        if not root:
            return f'{subnet!r} nao possui leaf nodes'
        self.leaves[subnet.address] = []
        for node in subnet.leaf_nodes:
            if node != root:
                self.leaves[subnet.address].append(node)

    # TODO: metodo set: set_leaves_size (set_leaves primeiro)
    def set_leaves_size(self):
        """Define quantidades de folhas: leaves_size"""
        pass


# %% classe Tree Tn(Vn, En)
class Tree(object):
    """
    Classe destinada as arvores nao direcionadas.

    - Cada 'SubNet' determina uma 'Tree' Tn(Vn, En).
    - Cada 'Tree' implementa uma 'SkeletonTree'.
    Represent sub-arvore do spanning-tree (UniTree) com os nodes da 'SubNet'.
    Resultado da uniao de todos os caminhos {Ps,t} entre cada par de nodes da
    'SubNet'.

    Contem switches de juncao (junction nodes) com grau 3 ou maior e switches
    de transito (transit nodes) com grau 2

    nodes e links para designar elementos de rede e suas interconexoes.

    Atributos:
    ----
    path:
        caminho P(s,t) de um node *s* para node *t* na mesma sub-rede
    nodes:
        lista de nodes pertencentes a Tree da sub-rede
    root:
        elemento definido como root (raiz)
    """
    _num_of_trees = 0

    def __new__(cls, *args, **kargs):
        """Cria objeto Tree e incrementa contador"""
        cls._num_of_trees += 1
        return super().__new__(cls)

    # TODO estruturacao construtor da classe Tree (continuar)
    def __init__(self, subnet: SubNet):
        self.subnet = subnet
        self.nodes = subnet.nodes

    def __del__(self):
        Tree._num_of_trees -= 1

    def __repr__(self):
        return self.__class__.__name__ + '(' + repr(self.subnet) + ')'

    @property
    def num_of_trees(self):
        """Retorna numero de instancias Tree criadas"""
        return self._num_of_trees

    @property
    def subnet(self):
        """Retorna endereco de rede referente a Tree"""
        return self._subnet

    @subnet.setter
    def subnet(self, value: SubNet):
        self._subnet = value

    @property
    def nodes(self):
        """Retorna lista Vn de nodes pertencentes a Tree da sub-rede"""
        return self._nodes

    @nodes.setter
    def nodes(self, value: Union[LeafNode, InternalNode, Node]):
        self._nodes = value

    @property
    def root(self):
        """Retorna elemento definido como root (raiz)"""
        return self._root

    @root.setter
    def root(self, value: LeafNode):
        self._root = value


# %% classe UniTree G(V,E)
class UniTree(object):
    """
    Classe destinada ao Spanning Tree nao direcionado explored network).
    Corresponde a uniao de todas as arvores Tree. Switches sao internal nodes,
    hosts e routers sao leaf nodes.

    G(V,E)
    ----
    - G:
        UniTree

    - V:
        node em V representa 1 elemento de rede (labeled and unlabeled nodes)

        - Labeled node:
            - tem MAC e fornece AFT por meio de solicitacoes SNMP
            - switchs com snmp e hosts
            - cada labeled node eh associado a uma ou mais sub-redes
        - Unlabeled node:
            - sem suporte a SNMP (hub ou switch).
    - E:
        cada edge em E representa uma conexao fisica entre 2 portas do
        elemento ativo

    Atributos:
    ----
    path:
        caminho P(s,t) de um node *s* para node *t* na mesma sub-rede
    subnets:
        sub-redes de G (spanning-tree), cada sub-rede definida pelo conjunto de
        seus elementos.
            - *N* = [N1, N2, ..., Nx]; N1 = [Node1, Node2, ..., Nodex]
    """

    # TODO estruturacao construtor da classe UniTree (em andamento)
    def __init__(self, trees: List[Tree]):
        self._nodes = None
        self._root = None


# %% Funcao get_port
# TODO função para identificar porta que leva a node específico v(u)
def get_port(from_node: Union[str, LeafNode, InternalNode],
             to_node: Union[str, LeafNode, InternalNode]) -> str:
    """
    Porta que leva a u. v(u)

    :rtype: str
    :type to_node: str, LeafNode, InternalNode
    :return: String com identificacao da porta
    :param to_node: Destino a ser identificado porta associada
    """
    # pass
    # FIXME: funcao get_port
    if isinstance(from_node, str):
        from_address = from_node
    elif isinstance(from_node, LeafNode, InternalNode):
        from_address = from_node.mac_address
    else:
        return None
    if isinstance(to_node, str):
        to_address = to_node
    elif isinstance(to_node, (LeafNode, InternalNode)):
        to_address = to_node.mac_address
    else:
        return None
    for mac, port in self.aft:
        if to_address == mac:
            return port


# %% Funcao get_root(subnet: SubNet) -> bool
def get_root(subnet: SubNet) -> Union[LeafNode, None]:
    """
    Identifica o LeafNode definido como root de uma SubNet

    :param subnet:
        SubNet a ser pesquisada pelo root node
    :return:
        Objeto LeafNode definido como root
    """
    if subnet.leaf_nodes:
        for node in subnet.leaf_nodes:
            if node.is_root:
                return node
        subnet.leaf_nodes[0].is_root = True
        return subnet.leaf_nodes[0]
    return None
    # print(f'Root nao definido para {subnet}')


# %% Funcao get_snmp_data
def get_snmp_data(*internal_nodes, net_bits=24) -> dict:
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
    for node in inodes:
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
        snmp_data[host_key]['sys_name'] = snmp.get('sysName.0').value

        dot1dstpport = 'mib-2.17.2.15.1.1'
        resposta_snmp = snmp.get_next(dot1dstpport)
        stp_port_indexes = []
        while dot1dstpport in resposta_snmp.oid:
            stp_port_indexes.append(
                    resposta_snmp.oid.rsplit(sep='.', maxsplit=1)[-1])
            resposta_snmp = snmp.get_next(resposta_snmp.oid)

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


#    #ligacoes fisicas entre 2 elementos
#    ports
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
        leaf_nodes - lista N - internal nodes de nos exclusivos da sub-rede
        nodes - lista VN dos elementos da sub-rede, leaf_nodes + internalnodes
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
    """
    # atributos da skeleton
    #    root_node
    #    leaf_nodes
    #    nodes
    #    sorted_nodes
    #    mac_table
    #    vertex
    #        nodes
    #    vertexes
    #    arcs
    #        ports
    #        leaf_nodes
    #    frontier_arcs
    """
    passo 1 - coleta dados
        - encontra porta root dos nos
        - calcula folhas dos nos
        - calcula valores dos nos para lista L sorted_nodes
    passo 2 - inicializa skeleton-tree
        - compila lista L sorted_nodes em ordem decrescente
        - inicializa skeleton-tree com primeiro vertex.nodes = root_node
          e set_node_value(root_node)
        - inicializa o grupo frontier_arcs com numero de port_activelist
          do root
        - cada arco arc de frontier_arcs eh associado ao grupo de folhas
          abaixo dele (macs na porta)
    passo 3 - modifica skeleton-tree
        - extrai primeiro no de L sorted_nodes
        - identifica arco frontier_arcs que sera conectado ao no extraido

    """

    # TODO SkeletonTree: inicialicazao da classe
    def __init__(self, subnet: SubNet):
        """
        Inicializa a skeleton-tree

        :param subnet: Objeto SubNet que induz a topologia
        """
        self.subnet = subnet
        self.nodes = subnet.nodes
        self.root = get_root(subnet)


#    #1
#    set_root_ports(nodes)
#    set_leaves(nodes)
#    set_values(nodes)
#    #2
#    set_sorted_nodes()
#    start()
#    set_frontiers()
#    #3
#    set_vertexes()
#        set_sorted()
#    #4

""" After the initialization stage, the algorithm iteratively extracts """


# %% main
def main():
    """
        Executa funcoes para criacao da skeleton tree [em desenvolvimento]
        ----
    """
    global mymac, SNMP_DATA, ARP_TABLE_DATA, AUTOFILL_MODE
    AUTOFILL_MODE = True

    config(['10.0.0.1',
            '10.0.0.2',
            '10.0.0.3',
            '10.0.0.4',
            '10.0.0.5',
            '10.0.0.6'])
    redes = (SubNet('10.0.0.0/24', auto_fill=AUTOFILL_MODE, has_switches=True),
             SubNet('10.0.10.0/24', auto_fill=AUTOFILL_MODE),
             SubNet('10.0.20.0/24', auto_fill=AUTOFILL_MODE),
             SubNet('10.0.30.0/24', auto_fill=AUTOFILL_MODE))

    # mymac = get_mymac(interface='ens33')
    # mymac = get_mymac(interface='enp0s17')
    if not AUTOFILL_MODE:
        for rede in redes:
            rede.update_arp_table(auto_fill=False, post=True)
            ARP_TABLE_DATA[rede.compressed] = rede.arp_table
            pprint(f'Rede {rede} ARP table {rede.arp_table}')
    pprint(f'Tabela ARP dos elementos: {ARP_TABLE_DATA }')
    print()
    pprint(f'Dados SNMP dos elementos: {SNMP_DATA}')
    print()

    for rede in redes:
        rede.set_all_nodes()
        print(f'Nodes da rede {rede!r}:')
        pprint(rede.nodes)
        print()
    for inode in redes[0].internal_nodes:
        inode.set_associated_subnets()
        print(f'Node switch {inode!r} de nome {inode.name}:')
        print(f'Intrefaces para redes: {inode.ports_onsubnet}')
        print(f'SubNet associadas: '
              f'{inode.associated_subnets.difference({inode.network})}')
        print(f'D{inode.name}:')
        pprint(inode.port_activeset['all'])
        print(f'DN{inode.name} N=10.0.10.0:')
        print(inode.port_activeset['10.0.10.0/24'])

        print(f'F{inode.name},k: {inode.aft_atports}')
        for port in inode.aft_atports.keys():
            pprint(f'F{inode.name},{port}:')
            pprint(inode.aft_atports[port])
        print()
        print(f'FN{inode.name},k N=10.0.10.0:')
        print(inode.subnet_aft_atports('10.0.10.0/24'))
        for port, macs in inode.subnet_aft_atports('10.0.10.0/24').items():
            pprint(f'FN{inode.name},{port}:')
            pprint(macs)


        print()

    # lista Vn de nodes associados com a subrede N
    for rede in redes:
        print(f'Nodes da rede {rede!r}:')
        pprint(rede.nodes)
        pprint(rede.nodes_set)
        pprint(f'Root: {get_root(rede)}')
        if not get_root(rede):
            print()
            continue
        print('Vn - r: ')
        pprint(rede.nodes_set - {get_root(rede)})
        print()
        # for inode in redes[0].internal_nodes:
        #     print(f'Porta {inode.name}(r) para root: {inode.get_port(get_root(rede))}')
        # print()
    pprint(Node._all_nodes_set)

# %% executa main()
if __name__ == '__main__':
    main()
