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
import snakebones as sk
import gnsbinder as gb
from pdb import set_trace as breakpoint


def main():
    global mymac, SNMP_DATA, ARP_TABLE_DATA, AUTOFILL_MODE
    AUTOFILL_MODE = False

    # GERANDO TOPOLOGIAS
    new_switches = 10
    new_hubs = 10
    new_hosts = 100
    new_graphs = 10
    new_subnets = 3

    graph_path = '/mnt/hgfs/Projeto Final Dissertacao/snakebones/grafos_rand/'
    file_name = \
        f'randomgraph_sw{new_switches:02}_hub{new_hubs:02}_host{new_hosts:03}_'

    # ler grafos aleatorios
    graph_list = list()
    for i in range(new_graphs):
        graph_loaded = gb.nx.Graph(
            gb.nx.nx_pydot.read_dot(f'{graph_path}{file_name}{i+1:002}.txt')
        )
        graph_list.append(graph_loaded)

    project_id = '389dde3d-08ac-447b-8d54-b053a3f6ed19'  # scritp-test.gns3
    nms_id = 'a296b0ec-209a-47a5-ae11-fe13f25e7b73'  # NMS (lubuntu-MESTRADO)

    pc = gb.Gns3('192.168.139.1', project_id=project_id)
    breakpoint()

    # Cria nodes e links no GNS3
    for graph in graph_list[0]:
        pc.clear_links(keep=(nms_id,))
        pc.nodes_from_graph(graph, subnets=3)
        pc.links_from_graph(graph)
        breakpoint()

    # pc.clear_links(keep=(nms_id,))

    # 1) OBTENDO DADOS
    sw_subnet = '10.0.0.0/24'  # subnet que contem switches gerenciaveis (snmp)
    redes = sk.subnet_creator(
        sw_subnet)  # , '10.0.10.0/24', '10.0.20.0/24', '10.0.30.0/24')
    for rede in sk.subnet_ips(new_subnets):
        redes.update(sk.subnet_creator(rede))
    breakpoint()
    sw_subnet = sk.get_subnet(sw_subnet)
    internal_nodes = \
        ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.5', '10.0.0.6']

    sk.nms_config(True)
    ARP_TABLE_DATA = dict()
    for rede in redes:
        rede.arp_table = \
            sk.set_arp_table(rede,
                             probes=1,
                             timeout=3,
                             include_me=True,
                             mode='arp')
        ARP_TABLE_DATA[rede.compressed] = rede.arp_table
    # breakpoint()
    SNMP_DATA = sk.get_snmp_data(*internal_nodes)


if __name__ == '__main__':
    main()
