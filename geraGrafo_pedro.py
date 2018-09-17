from __future__ import print_function #usado soh para printar o grafo

#Classe de cada no/vertice contendo os dados do mesmo e sua lista de conexoes
class vertice():
	def __init__(self,ID,ip,mac):
		self.ip = ip
		self.mac = mac
		self.filhos = [] #conjunto de vertices filhos
		self.ID = ID #inteiro usado para encontrar o vertice no algoritmo de grafo
	def addFilho(self,vertice):
		self.filhos.append(vertice)



#Funcao usada dentro do geraGrafo para criar o grafo
def processaGrafo(listaDeVertices,Grafo,atual):
	if atual < len(listaDeVertices):
		v = listaDeVertices[atual]
		IDnetos = set()
		IDfilhos = set()
		IDfilhosReais = []
		#achando os falsos filhos
		for filho in v.filhos:
			#preenchendo o conjunto de filhos com os IDs dos filhos
			IDfilhos.add(filho.ID)
			#preenchendo o conjunto de netos com os IDs dos netos
			for neto in filho.filhos:
				IDnetos.add(neto.ID)
		#removendo os falsos filhos
		IDfilhosReais = list(IDfilhos-IDnetos) ##FAZER MEMORIZACAO AQUI
		#registrando no grafo
		for i in IDfilhosReais:
			Grafo[atual][i] = 1
			Grafo[i][atual] = 1
		#proximo vertice
		processaGrafo(listaDeVertices,Grafo,atual+1)
		

#Funcao que gera o grafo
def geraGrafo(listaDeVertices):
	#listaDeVertices -> lista de vertices
	nVertices = len(listaDeVertices)

	#construindo o esqueleto do grafo
	Grafo = [[0 for x in range(nVertices)] for y in range(nVertices)]
	processaGrafo(listaDeVertices,Grafo,0)
	return Grafo






#------programa teste-----------------------------------------------------------

#tabela temporaria para testes
#a tabela contem todos os vertices e cada vertice contem sua lista de filhos
tabelaVertices = []
for i in xrange(0,6):
	tabelaVertices.append(vertice(i,"10.2.13."+str(i),"100.2.3.4."+str(i)))#preenchendo com vertices teste

#preenchendo os filhos para o teste
tabelaVertices[0].addFilho(tabelaVertices[1])
tabelaVertices[0].addFilho(tabelaVertices[2])
tabelaVertices[0].addFilho(tabelaVertices[3])
tabelaVertices[0].addFilho(tabelaVertices[4])
tabelaVertices[0].addFilho(tabelaVertices[5])

tabelaVertices[1].addFilho(tabelaVertices[4])
tabelaVertices[1].addFilho(tabelaVertices[3])
tabelaVertices[1].addFilho(tabelaVertices[5])


tabelaVertices[4].addFilho(tabelaVertices[5])

#Exemplo da entrada acima
'''
V1 com filhos [2,3,4,5,6]
V2 com filhos [5,4,6]
V3 com filhos []
V4 com filhos []
V5 com filhos [6]

'''
#Grafo

'''
(3)-(1)
	 |
	 (2)-(4)
	 |
	 (5)
	 |
	 (6)
'''



#Essa tabela mostra as arestas pelo seu i,j ,ou seja, g[1][2] = 1 significa que 1 e 2 possuem uma aresta entre eles
g = geraGrafo(tabelaVertices)
for i in xrange(0,len(tabelaVertices)):
	for j in xrange(0,len(tabelaVertices)):
		print(g[i][j], end=' ')
	print()