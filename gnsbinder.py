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
the switches connectivity. Then, we randomly connect the
required number of hubs to free switch ports and we uniformly
attached hosts to the switches and the hubs of the constructed
tree. In the following, we arbitrarily associated each host with
a single subnet-id and we connected the constructed tree to a
router with a dedicated port for each subnet.

Simulation results of networks with 10 switches (with 8 ports), 10 dumbhubs
(with 8 ports) and 100 hosts.  3:7 subnets, 0:5 uncooperative switchs
"""

import networkx as nx  # para trabalhar com grafos
import matplotlib.pyplot as plt

from ast import literal_eval
from itertools import count, takewhile, repeat
from json import dumps, loads
from networkx.generators.trees import random_tree
from networkx.algorithms.tree.recognition import is_tree, is_arborescence
from pdb import set_trace as breakpoint
from pprint import pprint
from random import randint, randrange, sample, choice, shuffle
from string import ascii_lowercase
from subprocess import run, PIPE
from time import sleep


class Gns3(object):
    """
    classe para gerenciar comunicacao com servidores GNS3 por meio da
    integracao entre cURP e API GNS3, lendo e escrevendo dados

    """

    def __init__(self, server='localhost', port=3080, project_id=None):
        self.server = server
        self.port = str(port)
        self.project_id = project_id

    def __repr__(self):
        return f"Gns3({self.server!r}, {self.port})"

    def nodes(self, project_id=None, new=None):
        if not project_id:
            project_id = self.project_id
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

    def nodes_amouts(self,
                     project_id=None,
                     sw_str='qemu',
                     hub_str='ethernet_switch',
                     host_str='vpcs'):
        """
        Retorna quantidade de switches hubs e host no projeto em um dicionario
        {'host': 0, 'hub': 0, 'sw': 0}

        :param project_id: id do projeto no servidor GNS3
        :param sw_str: string que identifica switchs nos nodes GNS3
        :param hub_str: string que identifica hubs nos nodes GNS3
        :param host_str: string que identifica hosts nos nodes GNS3
        :return: quantidades de switches hubs e hosts
        """
        if not project_id:
            project_id = self.project_id
        nodes = curl_get(server=self.server,
                         port=self.port,
                         project_id=project_id,
                         cmd='nodes')
        sw_count = count()
        hub_count = count()
        host_count = count()
        for node in nodes:
            node_type = node.get('node_type')
            if node_type == sw_str:
                next(sw_count)
            elif node_type == hub_str:
                next(hub_count)
            elif node_type == host_str:
                next(host_count)
        sw, hub, host = map(next, [sw_count, hub_count, host_count])
        return {'sw': sw, 'hub': hub, 'host': host}

    def links(self, project_id=None, new=None):
        if not project_id:
            project_id = self.project_id
        if new:
            a_id, b_id = new[0], new[1]
            node_a = curl_get(server=self.server,
                              port=self.port,
                              project_id=project_id,
                              cmd=f'nodes/{a_id}')
            node_b = curl_get(server=self.server,
                              port=self.port,
                              project_id=project_id,
                              cmd=f'nodes/{b_id}')

            try:
                free_a = self.freeports(project_id=project_id, node_id=a_id)[0]
                free_b = self.freeports(project_id=project_id, node_id=b_id)[0]
            except IndexError as err:
                return f'Sem porta livre para criar link'
            if node_a.get('node_type') == 'qemu':
                end_a = {'node_id': a_id,
                         'adapter_number': free_a,
                         'port_number': 0}
            else:
                end_a = {'node_id': a_id,
                         'adapter_number': 0,
                         'port_number': free_a}
            if node_b.get('node_type') == 'qemu':
                end_b = {'node_id': b_id,
                         'adapter_number': free_b,
                         'port_number': 0}
            else:
                end_b = {'node_id': b_id,
                         'adapter_number': 0,
                         'port_number': free_b}

            link_cfg = {'nodes': [end_a, end_b]}

            link = curl_post(server=self.server,
                             port=self.port,
                             project_id=project_id,
                             cmd='links',
                             data=link_cfg)
            return link
        links = curl_get(server=self.server,
                         port=self.port,
                         project_id=project_id,
                         cmd='links')
        return links

    def clear_links(self, project_id=None):
        if not project_id:
            project_id = self.project_id
        links = curl_get(server=self.server,
                         port=self.port,
                         project_id=project_id,
                         cmd='links')
        for link in links:
            curl_delete(server=self.server,
                        port=self.port,
                        project_id=project_id,
                        cmd=f'links/{link.get("link_id")}')

    def freeports(self, project_id=None, node_id=None):
        if not project_id:
            project_id = self.project_id
        node = curl_get(server=self.server,
                        port=self.port,
                        project_id=project_id,
                        cmd=f'nodes/{node_id}')
        if node.get('properties').get('adapters'):
            ports = [port for port in range(node['properties']['adapters'])]
            for link in self.links(project_id):
                for node in link['nodes']:
                    if node['node_id'] == node_id:
                        ports.remove(node['adapter_number'])
        else:
            ports = [port for port in range(len(node['ports']))]
            for link in self.links(project_id):
                for node in link['nodes']:
                    if node['node_id'] == node_id:
                        ports.remove(node['port_number'])
        return ports

    def nodes_from_graph(self, graph=None, subnets=1, host_ips=None):
        """
        Cria nodes GNS3 a partir de um grafo

        :param graph:
        :param host_ips:
        """
        sw_graph_amout, hub_graph_amout, host_graph_amout = \
            graph_nodes_amouts(graph).values()
        host_ips = list(subnet_host_ips(subnets=subnets, ips=host_graph_amout))
        sw_gns_amout, hub_gns_amout, host_gns_amout = \
            self.nodes_amouts().values()
        sw_tocreate = sw_graph_amout - sw_gns_amout
        hub_tocreate = hub_graph_amout - hub_gns_amout
        host_tocreate = host_graph_amout - host_gns_amout

        # Cria switches
        for i in range(sw_tocreate):
            new_switch = set_switch(name_index=sw_gns_amout + 1 + i,
                                    xyrange=(-635, 640, -841, -300))
            self.nodes(new=new_switch)

        # Cria hubs
        for i in range(hub_tocreate):
            new_hub = set_hub(name_index=hub_gns_amout + 1 + i,
                              xyrange=(-635, 640, -300, 100))
            self.nodes(new=new_hub)

        # Cria hosts
        for i in range(host_tocreate):
            new_host = set_host(host_ips[host_gns_amout + i],
                                xyrange=(-635, 640, 100, 810))
            self.nodes(new=new_host)

    # HINT links_from_graph: bug links nao aleatorios para hosts
    def links_from_graph(self, graph):
        """
        Cria links GNS3 partindo de um grafo

        :param graph:
        """
        nodes_pairs = dict(zip(graph.nodes,
                               (node['node_id'] for node in self.nodes())))
        for edge in graph.edges:
            node_a = nodes_pairs[edge[0]]
            node_b = nodes_pairs[edge[1]]
            self.links(new=(node_a, node_b))

    @property
    def version(self):
        return curl_get(server=self.server, port=self.port, cmd='version')

    @property
    def computes(self):
        return curl_get(server=self.server, port=self.port, cmd='computes')

    @property
    def projects(self):
        return curl_get(server=self.server, port=self.port, cmd='projects')


# criar node
# curl -X POST 192.168.139.1:3080/v2/projects/389dde3d-08ac-447b-8d54-b053a3f6ed19/nodes -d '{"name": "VPCS 1", "node_type": "vpcs", "compute_id": "vm"}'
# curl -X POST 192.168.139.1:3080/v2/projects/389dde3d-08ac-447b-8d54-b053a3f6ed19/nodes -d '{"compute_id": "vm", "console_type": "telnet", "name": "v1", "node_type": "qemu", "properties": {"qemu_path": "/usr/bin/qemu-system-x86_64", "ram": 768}, "symbol": ":/symbols/multilayer_switch.svg"}'
def curl_get(server=None, port=None, project_id=None, cmd=None) -> dict:
    """
    Envia comando cURL para servidor GNS3, captura resposta em string, formata e
    retorca conversao em objeto apropriado.
    dict, list, tuple, True, False, None, str.

    Exemplo:
    >>> curl_get('192.168.139.128', 3080, 'computes')
    curl 192.168.139.128:3080/v2/computes

    :param server: IP do servidor http alvo
    :param port: porta TCP do servidor alvo
    :param cmd:
    parametro final do comando
        - 'version': retorna versao do servidor e local de execucao
        - 'computes': lista todos os servidores com seus detalhes de conexao
    :return: resposta em objto convertido
    """
    cmd_prefix = f"curl http://{server}:{port}/v2"
    if project_id:
        cmd_prefix = f"{cmd_prefix}/projects/{project_id}"
    if cmd:
        cmd_prefix = f"{cmd_prefix}/{cmd}"
    cmd_send = cmd_prefix.split()
    cmd_ans = run(cmd_send, stdout=PIPE, universal_newlines=True).stdout
    return loads(cmd_ans)  # convertido de json


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
    cmd_prefix = \
        f"curl -X POST http://{server}:{port}/v2/projects/{project_id}/{cmd} -d "

    cmd_send = f"{cmd_prefix} '{dumps(data)}'"
    cmd_ans = \
        run(cmd_send, stdout=PIPE, universal_newlines=True, shell=True).stdout
    return loads(cmd_ans)  # convertido de json


# curl -i -X DELETE 'http://localhost:3080/v2/projects/project_id/links/10456b36-5917-4992-a1c0-d2e07a56f2a2'
def curl_delete(server=None, port=None, project_id=None, cmd=None):
    cmd_send = \
        f"curl -X DELETE http://{server}:{port}/v2/projects/{project_id}/{cmd}"
    cmd_ans = \
        run(cmd_send, stdout=PIPE, universal_newlines=True, shell=True).stdout
    if cmd_ans:
        return loads(cmd_ans)  # convertido de json
    return None


def rand_pos(xstart=None, xstop=None, ystart=None, ystop=None, step=None):
    """
    Retorna coodenada aleatoria para criar node na area visivel da topologia com
    base na grid padrao.

    :param xstart:
    :param xstop:
    :param ystart:
    :param ystop:
    :param step:
    :return:
    """
    if not xstart:
        xstart = -635
    if not xstop:
        xstop = 640
    if not ystart:
        ystart = -841
    if not ystop:
        ystop = 810
    if not step:
        step = 150
    x_pos = choice(range(xstart, xstop, step))
    y_pos = choice(range(ystart, ystop, step))
    return {'x': x_pos, 'y': y_pos}


# HINT set_switch: corrigido carregamento do sistema operacional simulado
def set_switch(name_index=1, pos=None, xyrange=None):
    """
    Opcao de posicao para nodes definicao ou aleatoria

    :param name_index:
    :param pos:
    :param xyrange:
    :return:
    """
    name = f"v{name_index}"
    hda_disk_image = "vios_l2-adventerprisek9-m.vmdk.SSA.152-4.0.55.E"
    hda_disk_image_md5sum = "1a3a21f5697cae64bb930895b986d71e"
    hda_disk_interface = "virtio"
    linked_clone = True
    options = "-nographic"
    process_priority = "normal"
    usage = "There is no default password and enable password. " \
            "There is no default configuration present."

    if not pos:
        if xyrange:
            pos = rand_pos(*xyrange)
        else:
            pos = rand_pos()
    else:
        pos['x'], pos['y'] = pos
    false, null, true = False, None, True
    # if gateway:
    #     starturp_script = "set pcname -" + ip + "-\n" + \
    #                       " ".join(("ip", ip, gateway, prefix, "\n"))
    # else:
    #     starturp_script = "set pcname -" + ip + "-\n" + \
    #                       " ".join(("ip", ip, prefix, "\n"))
    #
    switch_cfg = \
        {
            "compute_id": "vm",
            # "console": 5032,
            "console_type": "telnet",
            # "first_port_name": "",
            # "height": 48,
            # "label": {
            #     "rotation": 0,
            #     "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
            #     "text": "v1",
            #     "x": -24,
            #     "y": -20
            # },
            "name": name,
            # "node_id": "ebca888d-828d-4a52-b900-f7301c0e3ce3",
            "node_type": "qemu",
            "port_name_format": "Gi{1}/{0}",
            "port_segment_size": 4,
            "properties": {
                # "acpi_shutdown": false,
                # "adapter_type": "e1000",
                "adapters": 16,
                # "bios_image": "",
                # "bios_image_md5sum": null,
                # "boot_priority": "c",
                # "cdrom_image": "",
                # "cdrom_image_md5sum": null,
                # "cpu_throttling": 0,
                # "cpus": 1,
                "hda_disk_image": hda_disk_image,
                "hda_disk_image_md5sum": hda_disk_image_md5sum,
                "hda_disk_interface": hda_disk_interface,
                # "hdb_disk_image": "",
                # "hdb_disk_image_md5sum": null,
                # "hdb_disk_interface": "ide",
                # "hdc_disk_image": "",
                # "hdc_disk_image_md5sum": null,
                # "hdc_disk_interface": "ide",
                # "hdd_disk_image": "",
                # "hdd_disk_image_md5sum": null,
                # "hdd_disk_interface": "ide",
                # "initrd": "",
                # "initrd_md5sum": null,
                # "kernel_command_line": "",
                # "kernel_image": "",
                # "kernel_image_md5sum": null,
                # "legacy_networking": false,
                "linked_clone": linked_clone,
                # # "mac_address": "00:3e:5c:01:00:00",
                "options": options,
                # "platform": "x86_64",
                "process_priority": process_priority,
                "qemu_path": "/usr/bin/qemu-system-x86_64",
                "ram": 768,
                "usage": usage
            },
            "symbol": ":/symbols/multilayer_switch.svg",
            # "width": 51,
            "x": pos["x"],
            "y": pos["y"]
            # "z": 1
        }
    return switch_cfg


def set_hub(name_index=1, pos=None, xyrange=None):
    false, null, true = False, None, True
    name = f"HUB{name_index}"
    if not pos:
        if xyrange:
            pos = rand_pos(*xyrange)
        else:
            pos = rand_pos()
    else:
        pos['x'], pos['y'] = pos
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
            #     "text": "HUB",
            #     "x": 14,
            #     "y": -24
            # },
            "name": name,
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
            "x": pos["x"],
            "y": pos["y"]
            # "z": 1
        }
    return hub_cfg


def set_host(ip=None, prefix='24', gateway=None, pos=None, xyrange=None):
    false, null, true = False, None, True
    if gateway:
        starturp_script = f"set pcname -{ip}-\nip {ip} {gateway} {prefix}\n"
    else:
        starturp_script = f"set pcname -{ip}-\nip {ip} {prefix}\n"
    if not pos:
        if xyrange:
            pos = rand_pos(*xyrange)
        else:
            pos = rand_pos()
    else:
        pos['x'], pos['y'] = pos
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
            "name": ip[ip.find('.', 3) + 1:],
            # "node_id": "1c867306-7db3-4368-bc26-a76ec61451fe",
            "node_type": "vpcs",
            "port_name_format": "Ethernet{0}",
            "port_segment_size": 0,
            "properties": {
                "startup_script": starturp_script,
                "startup_script_path": "startup.vpc"
            },
            "symbol": ":/symbols/vpcs_guest.svg",
            # "width": 65,
            "x": pos["x"],
            "y": pos["y"]
            # "z": 1
        }
    return node_cfg


def set_link(a_id, a_adapter, b_id, b_adapter):
    # teste = {"properties": {"adapters": 16}}
    link_cfg = \
        {'nodes': [{'node_id': a_id,
                    'adapter_number': a_adapter,
                    'port_number': 0},
                   {'node_id': b_id,
                    'adapter_number': b_adapter,
                    'port_number': 0}
                   ]}
    return link_cfg


def chunks(iterable, n):
    """
    Dividir em partes de n por vez.

    :param iterable:
    :param n:
    """
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]


def split(iterable, n):
    """
    Dividir uniformemente em n partes

    :param iterable:
    :param n:
    :return:
    """
    div, mod = divmod(len(iterable), n)
    return (iterable[i * div + min(i, mod):(i + 1) * div + min(i + 1, mod)]
            for i in range(n))


# HINT random_graph: corrigido bug hosts nao aleatorios no grafo
def random_graph(sw_nodes, hub_nodes, host_nodes, plot=None):
    """
    Criacao e plot (opcional) de arvore aleatoria para alimentar GNS3.
    Retorna grafo, posicoes e opcoes

    :param sw_nodes:
    :param hub_nodes:
    :param host_nodes:
    :param plot:
    :return:
    """
    randtree = random_tree(sw_nodes)
    switches = (''.join(['v', str(i)]) for i in range(1, sw_nodes + 1))
    hubs = (''.join(['HUB', str(i)]) for i in range(1, hub_nodes + 1))
    hosts = (''.join(['h', str(i)]) for i in range(1, host_nodes + 1))
    mapping = dict(list(zip(randtree.nodes, switches)))
    randtree = nx.relabel.relabel_nodes(randtree, mapping)
    # for node in randtree.nodes:
    #     randtree.nodes[node]['type'] = 'switch'
    attribs = {node: {'type': 'switch', 'color': 'orange'}
               for node in randtree.nodes}
    nx.set_node_attributes(randtree, attribs)
    # nx.set_node_attributes(randtree, 'switch', 'type')
    tree_nodes = list(randtree.nodes)
    for hub in hubs:
        randtree.add_edge(sample(tree_nodes, 1).pop(), hub)
    for node in randtree.nodes:
        if not randtree.nodes[node].get('type'):
            randtree.nodes[node]['type'] = 'hub'
            randtree.nodes[node]['color'] = 'pink'

    tree_nodes = list(randtree.nodes)
    to_split = list(hosts)
    randtree.add_nodes_from(to_split)
    shuffle(to_split)
    host_chunks = split(to_split, len(tree_nodes))
    for host_chunk, node in zip(host_chunks, tree_nodes):
        for host in host_chunk:
            randtree.add_edge(host, node)
    for node in randtree.nodes:
        if not randtree.nodes[node].get('type'):
            randtree.nodes[node]['type'] = 'host'
            randtree.nodes[node]['color'] = 'lightblue'

    cores_nodes = [randtree.nodes[node]['color'] for node in randtree.nodes]

    options = {
        # 'pos':(dictionary, optional),
        'with_labels': True,
        'font_weight': 'bold',
        'node_size': 800,
        # 'node_size':array,
        # 'node_color': 'r',
        'node_color': cores_nodes,
        'node_shape': 'o',
        # s - square
        # o - circle
        # ^>v< - triangles
        # d - diamond
        # p - pentagon
        # h - hexagon
        # 8 - 8 sides
        'alpha': 1.0,
        'linewidths': 1.0,
        # ([None | scalar | sequence])
        'width': 1.7,
        # 'edgecolors': 'black',
        'edge_color': 'darkblue'
        # 'edge_color':array,
    }
    places = nx.spring_layout(randtree,
                              # k=1.5/(len(randtree.nodes))*(1/2),
                              # k=1/sqrt(len(randtree.nodes)),
                              iterations=50)
    if plot:
        options.update(plot)
        # nx.draw_networkx(randtree, **options)
        nx.draw(randtree, pos=places, **options)
        plt.show()
    return randtree, places, options


def random_graphs(sw_nodes, hub_nodes, host_nodes, many=1):
    """
    Gerador de grafos em lote

    :param sw_nodes:
    :param hub_nodes:
    :param host_nodes:
    :param many:
    """
    for i in range(many):
        yield random_graph(sw_nodes, hub_nodes, host_nodes)
    # pass


def plot_graph(graph, pos=None, options=None):
    """
    Plot simplificado do grafo com cores diferenciadas por tipo de node

    :param graph:
    :param pos:
    :param options:
    """
    if options:
        nx.draw(graph, pos=pos, **options)
    else:
        cores_nodes = [graph.nodes[node]['color'] for node in graph.nodes]
        nx.draw(graph, pos=pos, node_color=cores_nodes, with_labels=True)
    plt.show()


def graph_nodes_amouts(graph):
    """
    Retorna quantidade de switches hubs e host do grafo

    :param graph: grafo gerado pela funcao random_graph
    :return: quantidades de switches hubs e hosts
    """
    # for node in graph.nodes:
    #     if graph.nodes['type'] ==
    sw_count = count()
    hub_count = count()
    host_count = count()
    for node in graph.nodes:
        if graph.nodes[node]['type'] == 'switch':
            next(sw_count)
        elif graph.nodes[node]['type'] == 'hub':
            next(hub_count)
        elif graph.nodes[node]['type'] == 'host':
            next(host_count)
    sw, hub, host = map(next, [sw_count, hub_count, host_count])
    return {'sw': sw, 'hub': hub, 'host': host}


def subnet_host_ips(subnets=1, ips=30, prefix=None):
    """
    Retorna gerador com total de IPs distribuido uniformemente por subnet.
    prefixo de 2 octedos em decima: '10.0' (padrao), '192.168'

    :param subnets:
    :param ips:
    :param prefix:
    :return:
    """
    if not prefix:
        prefix = '10.0'
    blocks, extra = divmod(ips, subnets)
    block_ips = [list(range(blocks)) for _ in range(subnets)]
    for i in range(extra):
        block_ips[i].append(len(block_ips[i]))
    sub_ip = list(zip(range(subnets), block_ips * subnets))
    return (f'{prefix}.{subnet+1}.{ip+1}'
            for subnet, ips in sub_ip for ip in ips)


# Create a project
# The next step is to create a project:
#
# # curl -X POST "http://localhost:3080/v2/projects" -d '{"name": "test"}'
# {
#     "name": "test",
#     "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f",
# }

""""""
# Start nodes
# Start the two nodes:
#
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/f124dec0-830a-451e-a314-be50bbd58a00/start" -d "{}"
#
# Connect to nodes
# Use a Telnet client to connect to the nodes once they have been started. The port number can be found in the output when the nodes have been created above.
#
# # telnet 127.0.0.1 5000
# Trying 127.0.0.1...
# Connected to localhost.
#
# VPCS> ip 192.168.1.1
# Checking for duplicate address...
# PC1 : 192.168.1.1 255.255.255.0
# VPCS> disconnect
#
#  Stop nodes:
# # curl -X POST "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes/f124dec0-830a-451e-a314-be50bbd58a00/stop" -d "{}"
#
# Node creation
#  Manual creation of a Qemu node
# # curl -X POST http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/nodes -d '{"node_type": "qemu", "compute_id": "local", "name": "Microcore1", "properties": {"hda_disk_image": "linux-microcore-6.4.img", "ram": 256, "qemu_path": "qemu-system-x86_64"}}'
#
# Notifications
# Notifications can be seen by connection to the notification feed:
# # curl "http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/notifications"
# {"action": "ping", "event": {"compute_id": "local", "cpu_usage_percent": 35.7, "memory_usage_percent": 80.7}}
# {"action": "node.updated", "event": {"command_line": "/usr/local/bin/vpcs -p 5001 -m 1 -i 1 -F -R -s 10001 -c 10000 -t 127.0.0.1", "compute_id": "local", "console": 5001, "console_host": "127.0.0.1", "console_type": "telnet", "name": "VPCS 2", "node_id": "83892a4d-aea0-4350-8b3e-d0af3713da74", "node_type": "vpcs", "project_id": "b8c070f7-f34c-4b7b-ba6f-be3d26ed073f", "properties": {"startup_script": null, "startup_script_path": null}, "status": "started"}}
# A Websocket notification stream is also available on http://localhost:3080/v2/projects/b8c070f7-f34c-4b7b-ba6f-be3d26ed073f/notifications/ws
#
#
# Tip: requests made by a client and by a controller to the computes nodes can been seen if the server is started with the –debug parameter.

""""""

# Controller endpoints
# The controller manages everything, it is the central decision point and has a complete view of your network topologies, what nodes run on which compute server, the links between them etc.
#
# This is the high level API which can be used by users to manually control the GNS3 backend. The controller will call the compute endpoints when needed.
#
# A standard GNS3 setup is to have one controller and one or many computes.
#
# Compute
# /v2/computes
# Node
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
# /v2/projects/{project_id}/open
# Server
# /v2/debug
# /v2/settings
# /v2/shutdown
# /v2/version

""""""


def main():
    plot_options = {
        # 'node_color': 'lightblue',
        # 'node_size': 800,
        # 'width': 1.7,
        'with_labels': True
        # 'font_weight': 'bold'
    }
    new_switches = 10
    new_hubs = 10
    new_hosts = 100
    new_graphs = 10
    # randtree, randtree_pos, randtree_opt = random_graph(new_switches,
    #                                                     new_hubs,
    #                                                     new_hosts)
    # type_dict = nx.get_node_attributes(randtree, 'type')
    # pprint(list(randtree.nodes))

    graph_path = '/home/akern/Documents/grafos/'
    graph_path = '/mnt/hgfs/Projeto Final Dissertacao/snakebones/grafos_rand/'
    file_name = \
        f'randomgraph_sw{new_switches:02}_hub{new_hubs:02}_host{new_hosts:03}_'
    # # gerar e salvar grafos
    # graph_gen = \
    #     random_graphs(new_switches, new_hubs, new_hosts, many=new_graphs)
    # for i, (graph, places, options) in enumerate(graph_gen):
    #     nx.nx_pydot.write_dot(graph, f'{graph_path}{file_name}{i+1:002}.txt')

    # ler e fazer plot dos grafos
    graph_list = list()
    for i in range(new_graphs):
        graph_loaded = nx.Graph(
            nx.nx_pydot.read_dot(f'{graph_path}{file_name}{i+1:002}.txt')
        )
        graph_list.append(graph_loaded)
        # plot_graph(graph_loaded, randtree_pos, randtree_opt)

    breakpoint()

    project_id = '389dde3d-08ac-447b-8d54-b053a3f6ed19'  # scritp-test.gns3
    # curl "http://192.168.139.128:3080/v2/computes"
    # vm = Gns3('192.168.139.128')

    pc = Gns3('192.168.139.1', project_id=project_id)
    print("\nGNS3 PC: ")
    print(pc)
    # pprint(pc.version)
    # pprint(pc.computes)
    # pprint(pc.projects)
    # pprint(pc.nodes())
    # pprint(pc.nodes_amouts())

    # Cria nodes e links no GNS3
    for graph in graph_list[:2]:
        pc.nodes_from_graph(graph, subnets=3)
        pc.clear_links()
        pc.links_from_graph(graph)
        breakpoint()
        sleep(2)

    pc.clear_links()


# node_a = "82f33431-5c66-418e-a45a-a8eb542ac13a"  # v1
# node_b = "a90255bb-f7ad-4c46-86c0-e2c6ca3c0ed3"  # HUB1
# free_a = pc.freeports(project_id=project_id, node_id=node_a)[0]
# free_b = pc.freeports(project_id=project_id, node_id=node_b)[0]
# new_link = set_link(node_a, free_a, node_b, free_b)
# print('\n\n\n')
# pprint(pc.links(project_id=project_id, new=new_link))
#
# node_a = "8847f3bb-0eae-40c4-bd20-078ab55fb771"  # vpc 10.2
# node_b = "a90255bb-f7ad-4c46-86c0-e2c6ca3c0ed3"  # HUB1
# free_a = pc.freeports(project_id=project_id, node_id=node_a)[0]
# free_b = pc.freeports(project_id=project_id, node_id=node_b)[0]
# new_link = set_link(node_a, free_a, node_b, free_b)
# print('\n\n\n')
# pprint(pc.links(project_id=project_id, new=new_link))
#

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
        "text": "HUB",
        "x": 14,
        "y": -24
    },
    "name": "HUB",
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
}


switch model
{
    "compute_id": "vm",
    "console": 5032,
    "console_type": "telnet",
    "first_port_name": "",
    "height": 48,
    "label": {
        "rotation": 0,
        "style": "font-family: TypeWriter;font-size: 10.0;font-weight: bold;fill: #000000;fill-opacity: 1.0;",
        "text": "v1",
        "x": -24,
        "y": -20
    },
    "name": "v1",
    "node_id": "ebca888d-828d-4a52-b900-f7301c0e3ce3",
    "node_type": "qemu",
    "port_name_format": "Gi{1}/{0}",
    "port_segment_size": 4,
    "properties": {
        "acpi_shutdown": false,
        "adapter_type": "e1000",
        "adapters": 16,
        "bios_image": "",
        "bios_image_md5sum": null,
        "boot_priority": "c",
        "cdrom_image": "",
        "cdrom_image_md5sum": null,
        "cpu_throttling": 0,
        "cpus": 1,
        "hda_disk_image": "vios_l2-adventerprisek9-m.vmdk.SSA.152-4.0.55.E",
        "hda_disk_image_md5sum": "1a3a21f5697cae64bb930895b986d71e",
        "hda_disk_interface": "virtio",
        "hdb_disk_image": "",
        "hdb_disk_image_md5sum": null,
        "hdb_disk_interface": "ide",
        "hdc_disk_image": "",
        "hdc_disk_image_md5sum": null,
        "hdc_disk_interface": "ide",
        "hdd_disk_image": "",
        "hdd_disk_image_md5sum": null,
        "hdd_disk_interface": "ide",
        "initrd": "",
        "initrd_md5sum": null,
        "kernel_command_line": "",
        "kernel_image": "",
        "kernel_image_md5sum": null,
        "legacy_networking": false,
        "linked_clone": true,
        "mac_address": "00:3e:5c:01:00:00",
        "options": "-nographic",
        "platform": "x86_64",
        "process_priority": "normal",
        "qemu_path": "/usr/bin/qemu-system-x86_64",
        "ram": 768,
        "usage": "There is no default password and enable password. There is no default configuration present."
    },
    "symbol": ":/symbols/multilayer_switch.svg",
    "width": 51,
    "x": 53,
    "y": -247,
    "z": 1
}
"""
