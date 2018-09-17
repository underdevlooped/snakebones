class Node(object): #Classe para modelar os dados
    def __init__(self,ID, ip, mac):
        self.ip = ip
        self.mac = mac
        self.ID = ID

#Funcao do site que o Andre mandou para gerar as arestas.
def generate_edges(graph):
    edges = []
    for node in graph:
        for neighbour in graph[node]:
            edges.append((node, neighbour))
    return edges

#Funcao que encontrei para mostrar os caminhos do grafo.
def dfs_caminhos(grafo, inicio, fim):
    pilha = [(inicio, [inicio])]
    while pilha:
        vertice, caminho = pilha.pop()
        for proximo in set(grafo[vertice]) - set(caminho):
            if proximo == fim:
                yield caminho + [proximo]
            else:
                pilha.append((proximo, caminho + [proximo]))

def imprimirEdges(grafo):
    resultEdges = generate_edges(grafo)
    for i in resultEdges:
        print(i[0].ID, i[0].ip, i[0].mac, " , ", i[1].ID, i[1].ip, i[1].mac)
    print("\n")

def imprimirCaminhos(grafo, inicio, fim):
    caminhos = list(dfs_caminhos(grafo, inicio, fim))
    for i in caminhos:
        aux = len(i)
        for c in range(aux):
            print("[",i[c].ID,i[c].ip,i[c].mac,"]", end = ' ')
        print("\n")

# -------- Programa Principal ----------


#Lista de dados com endereços
listaNode = []
for info in range(5):
    listaNode.append(Node(info,"10.2.13."+str(info),"100.2.3.4."+str(info)))

#Imprimindo a tabela com as informações
for info in listaNode:
    print(info.ID, info.ip, info.mac)
print("\n")

'''
Exemplo do grafo do site que o Andre mandou
graph = { "a" : ["c"],
          "b" : ["c", "e"],
          "c" : ["a", "b", "d", "e"],
          "d" : ["c"],
          "e" : ["c", "b"],
          "f" : []
        }

 O grafo abaixo usa o molde do "graph", porém com as informações. 
 O uso dos nós como conteúdo do dicionario forma as arestas.
'''
grafo = {
    listaNode[0]: [listaNode[2]], #3
    listaNode[1]:[listaNode[2],listaNode[4]], #3,5
    listaNode[2]:[listaNode[0],listaNode[1],listaNode[3],listaNode[4]], #1,2,4,5
    listaNode[3]:[listaNode[2]], #3
    listaNode[4]:[listaNode[2], listaNode[1]]
}

imprimirEdges(grafo)
imprimirCaminhos(grafo,listaNode[0],listaNode[4])
