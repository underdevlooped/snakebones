#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding=utf-8
"""
Created on Sun Dec 8 ‏‎11:50:24 2018

domingo, 8‎ de ‎dezembro‎ de ‎2018, ‏‎11:50:24
.
@author: Andre Kern

Execucao da descoberta de topologia fisica da LAN Ethernet explorada  por meio
da SkeletonTree
"""

from esqueleto import ping_nmap
from scapy.all import *
from pdb import set_trace as breakpoint
from pprint import pprint
from time import sleep
from typing import List

import gnsbinder as gb
import snakebones as sk


def main():
    global mymac, SNMP_DATA, ARP_TABLE_DATA, AUTOFILL_MODE
    AUTOFILL_MODE = False

    # GERANDO TOPOLOGIAS
    total_switches = 10
    total_hubs = 10
    total_hosts = 100
    total_nodes = total_switches + total_hubs + total_hosts
    total_graphs = 10
    total_subnets = 3
    resultados = list()

    graph_path = '/mnt/hgfs/Projeto Final Dissertacao/snakebones/grafos_rand/'
    file_name = \
        f'randomgraph_sw{total_switches:02}_hub{total_hubs:02}_host{total_hosts:03}_'

    # ler grafos aleatorios
    graph_list = list()
    for i in range(total_graphs):
        graph_loaded = gb.nx.Graph(
            gb.nx.nx_pydot.read_dot(f'{graph_path}{file_name}{i+1:002}.txt')
        )
        graph_list.append(graph_loaded)

    project_id = '389dde3d-08ac-447b-8d54-b053a3f6ed19'  # scritp-test.gns3
    nms_id = 'a296b0ec-209a-47a5-ae11-fe13f25e7b73'  # NMS (lubuntu-MESTRADO)

    pc = gb.Gns3('192.168.139.1', project_id=project_id)

    #
    sw_subnet = '10.0.0.0/24'  # subnet que contem switches gerenciaveis (snmp)
    leaf_subnet = [leaf for leaf in sk.subnet_ips(total_subnets)]
    redes = sk.subnet_creator(sw_subnet, *leaf_subnet)
    sw_subnet = sk.get_subnet(sw_subnet)
    internal_nodes = \
        [h.compressed for h in sw_subnet.hosts()][:total_switches]

    sk.config_nms(redes=redes)

    # breakpoint()

    # Cria nodes e links no GNS3 a partir dos grafos
    for graph in graph_list:
        pc.clear_links(keep=(nms_id,))
        # breakpoint()
        pc.nodes_from_graph(graph, subnets=total_subnets, steps={'host': 75})
        pc.links_from_graph(graph)
        pc.start_nodes()
        hosts_ips = list(
            gb.subnet_host_ips(subnets=total_subnets, ips=total_hosts))
        sleep(120)

        # 1) OBTENDO DADOS
        ARP_TABLE_DATA = dict()
        for rede in redes:
            if rede == sw_subnet:
                ipmax = total_switches
            else:
                div, mod = divmod(total_hosts, total_subnets)
                ipmax = div + mod
            rede.arp_table = \
                sk.arp_table(rede,
                             probes=2,
                             timeout=4,
                             include_me=True,
                             mode='multping',
                             ipmax=ipmax)
            ARP_TABLE_DATA[rede.compressed] = rede.arp_table
        SNMP_DATA = dict()
        for internal_node in internal_nodes:
            # breakpoint()
            ping_nmap(hosts_ips)
            for attempt in range(3):
                try:
                    SNMP_DATA.update(sk.get_snmp_data(internal_node))
                except Exception as err:
                    print(f'Erro {err} coleta snmp. tentativa {attempt+1}/3...')
                    sk.ping_ip(internal_node.ip_address)
                    sleep(1)
                else:
                    break
            else:
                print(f'Erro coleta snmp. {attempt+1} tentativas sem sucesso.')
                raise TimeoutError('Erro tentando coletar snmp')

        for rede in redes:
            rede.set_all_nodes()
        for inode in sw_subnet.internal_nodes:
            inode.set_associated_subnets()
        for my_ip in sk.get_myip():
            sk.set_root(my_ip)

        print("\n" + f"Nodes descobertos: ({len(sk.Node._all)})")
        pprint(sk.Node._all)

        print("\n" + f"Inodes: ({len(sk.InternalNode._allinodes_set)})")
        pprint(sk.InternalNode._allinodes_set)

        # 2) INFERINDO TOPOLOGIA
        skeletons: List[sk.SkeletonTree] = list()
        for subnet in sk.SubNet._all:  # subnet Ni ∈ 'N'
            if subnet._has_switches:
                continue
            # SkeletonTree(Ni,Vni,ri,AFTs)
            if not AUTOFILL_MODE:
                sk.set_root(subnet=subnet)
            skeletons.append(sk.SkeletonTree(subnet.leaf_nodes,  # Ni
                                             subnet.nodes_set,  # Vni
                                             sk.get_root(subnet),  # ri
                                             subnet))

            bone: sk.SkeletonTree = skeletons[-1]  # Hi(Yi,Ai)
            # ExtendedAFTs(yj,X H(Y,A))
            sk.ext_aft(bone.root_vertex,  # yj
                       bone.anchors,  # X
                       bone)  # H(Y,A)
            sk.boneprint(bone)

        while len(skeletons) >= 2 and skeletons[0].anchors & skeletons[1].anchors:
            first, second = skeletons[0], skeletons[1]  # Hi and Hj
            new_netnodes = first.netnodes | second.netnodes  # Nk = Ni U Nj
            anchors_inter = first.anchors & second.anchors
            new_root = anchors_inter.pop()  # rk = any node in Xi ∩ Xj
            new_nodes = first.nodes | second.nodes  # VNk = VNi U VNj
            remove = [interface.ip.compressed for interface in sk.get_myip()][1:]
            # FIXME erro ao criar SkeletonTree
            # breakpoint()
            new_skeleton = sk.SkeletonTree(new_netnodes,
                                           new_nodes,
                                           new_root,
                                           remove=remove[1:])
            sk.ext_aft(new_skeleton.root_vertex,
                       new_skeleton.anchors,
                       new_skeleton)
            skeletons.remove(first)
            skeletons.remove(second)
            skeletons.append(new_skeleton)
        united_skeleton = skeletons.pop()
        united_len = len(united_skeleton.vertices)
        if united_len == total_nodes:
            # sk.boneprint(united_skeleton)
            # sk.boneprint(united_skeleton, verbose=False)
            aferido = True
            print(f'Rede aferida do graph ({graph_list.index(graph)}) '
                  f'{graph}.')
        else:
            aferido = False
            print(f'Rede nao aferida do graph ({graph_list.index(graph)}). '
                  f'Total:{total_nodes} Aferido:{united_len}')
        resultados.append((graph_list.index(graph),
                           graph,
                           total_nodes,
                           len(united_skeleton.vertices),
                           aferido))
    breakpoint()


if __name__ == '__main__':
    main()
