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
import logging
import snakebones as sk


def main():
    global mymac, SNMP_DATA, ARP_TABLE_DATA, AUTOFILL_MODE
    AUTOFILL_MODE = False

    # GERANDO TOPOLOGIAS
    total_switches = 10
    total_hubs = 10
    total_hosts = 100
    total_nodes = total_switches + total_hubs + total_hosts
    total_graphs = 5
    total_subnets = 3
    resultados = list()

    graph_path = '/mnt/hgfs/Projeto Final Dissertacao/snakebones/grafos_rand'
    file_name = \
        f'randomgraph_sw{total_switches:02}_hub{total_hubs:02}_' \
        f'host{total_hosts:03}'

    logging.basicConfig(filename=f'{graph_path}/Logs/{file_name}_'
                                 f'{total_graphs}.log',
                        format='%(asctime)s : %(module)-10s : %(levelname)-7s : '
                               '%(lineno)-4d : %(funcName)s : %(message)s',
                        # datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    formatter = logging.Formatter('%(name)-10s: %(levelname)-7s : %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('console').addHandler(console)

    logger = logging.getLogger(__name__)

    logger.info('Inicio.')
    logger.debug(f'Totais: sw:{total_switches} hub:{total_hubs} '
                  f'host:{total_hosts} subnets:{total_subnets} '
                  f'grafos:{total_graphs}')

    # ler grafos aleatorios
    graph_list = list()
    for i in range(total_graphs):
        graph_loaded = gb.nx.Graph(
            gb.nx.nx_pydot.read_dot(f'{graph_path}/{file_name}_{i+1:002}.txt')
        )
        graph_list.append(graph_loaded)
    logger.info(f'{len(graph_list)} grafos lidos')

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

    logger.info(f'configurando interfaces do NMS...')
    sk.config_nms(redes=redes)
    logger.info(f'Interfaces do NMS configuradas para {len(redes)} redes')

    # Cria nodes e links no GNS3 a partir dos grafos
    for num_g, graph in enumerate(graph_list, 1):
        logger.info(f'Criando topologia {num_g} no GNS3...')
        pc.clear_links(keep=(nms_id,))
        pc.nodes_from_graph(graph, subnets=total_subnets, steps={'host': 75})
        pc.links_from_graph(graph)
        logger.info(f'Iniciando nodes da topologia {num_g} no GNS3...')
        pc.start_nodes()
        hosts_ips = list(
            gb.subnet_host_ips(subnets=total_subnets, ips=total_hosts))
        logger.info(f'Topologia {num_g} criada no GNS3 com {total_hosts} hosts '
                    f'em {total_subnets} redes')
        sleep(120)

        # 1) OBTENDO DADOS
        ARP_TABLE_DATA = dict()
        for rede in redes:
            logger.info(f'Criando tabela ARP topo {num_g} '
                        f'rede {rede.compressed}...')
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
            logger.info(f'Tabela ARP criada rede {rede.compressed}. '
                        f'Total: {len(rede.arp_table)}.')
            logger.debug(rede.arp_table)

        SNMP_DATA = dict()
        for internal_node in internal_nodes:
            logger.info(f'Atualizando tabela ARP para coleta SNMP '
                        f'{internal_node} ...')

            ping_nmap(hosts_ips)
            logger.info(f'Iniciando coleta SNMP {internal_node}...')
            for attempt in range(3):
                logger.debug(f'Tentativa {attempt+1}/3 de '
                             f'coletar {internal_node}')
                try:
                    SNMP_DATA.update(sk.get_snmp_data(internal_node))
                except Exception as err:
                    logger.warning(f'Erro {err} coleta snmp. '
                                   f'Tentativa {attempt+1}/3...')
                    sk.ping_ip(internal_node)
                    sleep(1)
                else:
                    logger.info(f'SNMP {internal_node} coletado com sucesso')
                    logger.debug(SNMP_DATA[internal_node + '/24'])
                    break
            else:
                logger.error(f'Erro coleta snmp. {attempt+1} tentativas '
                             f'sem sucesso.')
                raise TimeoutError('Erro tentando coletar snmp')

        logger.info(f'Definindo nodes das redes...')
        for rede in redes:
            logger.debug(f'Definindo nodes para rede {rede}...')
            rede.set_all_nodes()
            logger.debug(f'Nodes definidos para rede {rede}. '
                         f'Total: {len(rede.nodes)}')
        logger.info(f'Nodes definidos para {len(redes)}.')
        logger.info(f'Definindo redes associadas...')
        for inode in sw_subnet.internal_nodes:
            logger.debug(f'Definindo redes associadas a {inode}...')
            inode.set_associated_subnets()
            logger.debug(f'Redes associadas {inode}. '
                         f'Total: {len(inode.associated_subnets)}')
        for my_ip in sk.get_myip():
            sk.set_root(my_ip)

        logger.info(f"total GNS3 Nodes: ({len(sk.Node._all)}). "
                    f"Inodes: {len(sk.InternalNode._allinodes_set)}. "
                    f"Leafs: {len(sk.LeafNode._all_leaves)}")
        graph_nodes_labeled = total_hosts + total_switches + total_subnets + 1
        num_allnodes = len(sk.Node._all)
        if num_allnodes < (graph_nodes_labeled):
            logging.error(f'Quantidade de nodes ({num_allnodes}) '
                          f'inferior ao esperado ({graph_nodes_labeled})')
        # print("\n" + f"Nodes descobertos: ({num_allnodes})")
        # pprint(sk.Node._all)
        logger.info(f"Nodes descobertos: ({num_allnodes})")
        logger.debug(sk.Node._all)

        logger.info(f"Inodes: ({len(sk.InternalNode._allinodes_set)})")
        logger.debug(sk.InternalNode._allinodes_set)

        # 2) INFERINDO TOPOLOGIA
        skeletons: List[sk.SkeletonTree] = list()
        for subnet in sk.SubNet._all:  # subnet Ni ∈ 'N'
            if subnet._has_switches:
                continue
            # SkeletonTree(Ni,Vni,ri,AFTs)
            if not AUTOFILL_MODE:
                sk.set_root(subnet=subnet)
            logger.info(f'Criando Skeleton para {subnet}...')
            root = sk.get_root(subnet)
            logger.debug(subnet.leaf_nodes)
            logger.debug(subnet.nodes_set)
            logger.debug(root)
            skeletons.append(sk.SkeletonTree(subnet.leaf_nodes,  # Ni
                                             subnet.nodes_set,  # Vni
                                             sk.get_root(subnet),  # ri
                                             subnet))
            logger.info(f'Skeleton {skeletons[-1]} criada para {subnet}.')

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
