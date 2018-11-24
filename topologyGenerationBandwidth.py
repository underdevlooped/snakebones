import networkx as nx
import copy
#import numpy

#Requires packages
#apt-get install python-networkx

class TopologyGenerator():

	def __init__(self):
		pass
		
	def generateNetwork(self,name):
		self.network = nx.Graph()
		self.nrDCLocations = 0
		if (name == "test"):
			return self.__generateTest()
		elif (name == "rnp"):
			return self.__generateRNP()
		elif (name == "rnpCampNatal"):
			self.__generateRNP()
			self.network.add_edge("campinaGrande", "natal", weight=177, bandwidth=10000)
			return self.network , self.nrDCLocations
		elif (name == "rnpCurFlo"):
			self.__generateRNP()
			self.network.add_edge("curitiba", "florianopolis", weight=251, bandwidth=10000)
			return self.network , self.nrDCLocations
		elif (name == "rnpFiveLess"):
			self.__generateRNP()
			#self.network.add_edge("campinaGrande", "natal", weight=177, bandwidth=10000)
			#self.network.add_edge("curitiba", "florianopolis", weight=251, bandwidth=10000)
			#self.network.add_edge("beloHorizonte", "vitoria", weight=381, bandwidth=10000)
			#self.network.add_edge("beloHorizonte", "rioDeJaneiro", weight=340, bandwidth=10000)
			#self.network.add_edge("recife", "joaoPessoa", weight=103, bandwidth=10000)
			#Falso
			self.network.add_edge("beloHorizonte", "goiania", weight=500, bandwidth=10000)
			self.network.add_edge("salvador", "belem", weight=500, bandwidth=10000)
			return self.network , self.nrDCLocations
		elif (name == "rnpFiveMore"):
			self.__generateRNP()
			self.network.add_edge("campinaGrande", "natal", weight=177, bandwidth=10000)
			self.network.add_edge("campinaGrande", "maceio", weight=270, bandwidth=10000)
			#self.network.add_edge("campinaGrande", "fortaleza", weight=489, bandwidth=10000)
			#self.network.add_edge("recife", "joaoPessoa", weight=103, bandwidth=10000)
			#self.network.add_edge("recife", "natal", weight=255, bandwidth=10000)
			#Falso
			#self.network.add_edge("fortaleza", "maceio", weight=500, bandwidth=10000)
			return self.network , self.nrDCLocations
		elif (name == "rnpMod"):
			self.__generateRNP()
			for edge in self.network.edges():
				self.network[edge[0]][edge[1]]['bandwidth'] = 100000
			return self.network , self.nrDCLocations	
		elif (name == "rnpModTrans"):
			self.__generateRNP()
			for edge in self.network.edges():
				self.network[edge[0]][edge[1]]['bandwidth'] = 100000
			#Add more links
			#self.network.add_edge("fortaleza", "campinaGrande", weight=489, bandwidth=100000)
			self.network.add_edge("campinaGrande", "natal", weight=177, bandwidth=100000)
			#self.network.add_edge("campinaGrande", "maceio", weight=270, bandwidth=100000)
			#self.network.add_edge("beloHorizonte", "vitoria", weight=381, bandwidth=100000)
			self.network.add_edge("beloHorizonte", "rioDeJaneiro", weight=340, bandwidth=100000)
			self.network.add_edge("curitiba", "florianopolis", weight=251, bandwidth=100000)
			self.network.add_edge("recife", "natal", weight=255, bandwidth=10000)
			return self.network , self.nrDCLocations	
		elif (name == "renater"):
			return self.__generateRENATER()
		elif (name == "geantMod"):
			self.__generateGEANT()
			for edge in self.network.edges():
				self.network[edge[0]][edge[1]]['bandwidth'] = 100000
			return self.network , self.nrDCLocations
		elif (name == "geant"):
			return self.__generateGEANT()
		else:
			return False , False
		
	def __generateTest(self):
		self.network.add_node("s0",type="gateway")
		self.network.add_node("s1",type="gateway")
		self.network.add_node("s2",type="gateway")
		self.network.add_node("s3",type="gateway")
		self.network.add_node("s4",type="gateway")
		self.network.add_node("dc0",type="dcLocation")
		self.network.add_edge("dc0", "s0", weight=0 )
		self.network.add_node("dc1",type="dcLocation")
		self.network.add_edge("dc1", "s1", weight=0 )
		self.network.add_node("dc2",type="dcLocation")
		self.network.add_edge("dc2", "s2", weight=0 )
		self.network.add_node("dc3",type="dcLocation")
		self.network.add_edge("dc3", "s3", weight=0 )
		self.network.add_edge("dc0", "dc1", weight=200, bandwidth=10000 )
		self.network.add_edge("dc0", "dc2", weight=100, bandwidth=10000 )
		self.network.add_edge("dc0", "dc3", weight=300, bandwidth=10000 )
		self.network.add_edge("dc1", "dc2", weight=150, bandwidth=10000 )
		self.network.add_edge("dc2", "dc3", weight=50, bandwidth=10000 )
		self.nrDCLocations = 4
		return self.network , self.nrDCLocations
			

	def __generateRNP(self):
		#Add nodes
		self.network.add_node("rioBranco",type="dcLocation")
		self.network.add_node("portoVelho",type="dcLocation")
		self.network.add_node("cuiaba",type="dcLocation")
		self.network.add_node("campoGrande",type="dcLocation")
		self.network.add_node("curitiba",type="dcLocation")
		self.network.add_node("curitibaGW",type="gateway")
		self.network.add_node("portoAlegre",type="dcLocation")
		self.network.add_node("portoAlegreGW",type="gateway")
		self.network.add_node("florianopolis",type="dcLocation")
		self.network.add_node("florianopolisGW",type="gateway")
		self.network.add_node("saoPaulo",type="dcLocation")
		self.network.add_node("saoPauloGW1",type="gateway")
		self.network.add_node("saoPauloGW2",type="gateway")
		self.network.add_node("saoPauloGW3",type="gateway")
		self.network.add_node("saoPauloGW4",type="gateway")
		self.network.add_node("saoPauloGW5",type="gateway")
		self.network.add_node("rioDeJaneiro",type="dcLocation")
		self.network.add_node("rioDeJaneiroGW1",type="gateway")
		self.network.add_node("rioDeJaneiroGW2",type="gateway")
		self.network.add_node("vitoria",type="dcLocation")
		self.network.add_node("vitoriaGW",type="gateway")
		self.network.add_node("beloHorizonte",type="dcLocation")
		self.network.add_node("beloHorizonteGW",type="gateway")
		self.network.add_node("brasilia",type="dcLocation")
		self.network.add_node("brasiliaGW1",type="gateway")
		self.network.add_node("brasiliaGW2",type="gateway")
		self.network.add_node("goiania",type="dcLocation")
		self.network.add_node("palmas",type="dcLocation")
		self.network.add_node("manaus",type="dcLocation")
		self.network.add_node("boaVista",type="dcLocation")
		self.network.add_node("macapa",type="dcLocation")
		self.network.add_node("belem",type="dcLocation")
		self.network.add_node("belemGW",type="gateway")
		self.network.add_node("saoLuis",type="dcLocation")
		self.network.add_node("fortaleza",type="dcLocation")
		self.network.add_node("fortalezaGW",type="gateway")
		self.network.add_node("teresina",type="dcLocation")
		self.network.add_node("natal",type="dcLocation")
		self.network.add_node("natalGW",type="gateway")
		self.network.add_node("campinaGrande",type="dcLocation")
		self.network.add_node("recife",type="dcLocation")
		self.network.add_node("recifeGW",type="gateway")
		self.network.add_node("maceio",type="dcLocation")
		self.network.add_node("aracaju",type="dcLocation")
		self.network.add_node("salvador",type="dcLocation")
		self.network.add_node("salvadorGW",type="gateway")
		self.network.add_node("joaoPessoa",type="dcLocation")

		self.nrDCLocations = 27

		#Add links to gateways
		self.network.add_edge("curitiba", "curitibaGW", weight=0 )
		self.network.add_edge("portoAlegre", "portoAlegreGW", weight=0 )	
		self.network.add_edge("florianopolis", "florianopolisGW", weight=0 )
		self.network.add_edge("saoPaulo", "saoPauloGW1", weight=0 )
		self.network.add_edge("saoPaulo", "saoPauloGW2", weight=0 )
		self.network.add_edge("saoPaulo", "saoPauloGW3", weight=0 )
		self.network.add_edge("saoPaulo", "saoPauloGW4", weight=0 )
		self.network.add_edge("saoPaulo", "saoPauloGW5", weight=0 )	
		self.network.add_edge("rioDeJaneiro", "rioDeJaneiroGW1", weight=0 )
		self.network.add_edge("rioDeJaneiro", "rioDeJaneiroGW2", weight=0 )
		self.network.add_edge("vitoria", "vitoriaGW", weight=0 )
		self.network.add_edge("beloHorizonte", "beloHorizonteGW", weight=0 )
		self.network.add_edge("brasilia", "brasiliaGW1", weight=0 )
		self.network.add_edge("brasilia", "brasiliaGW2", weight=0 )
		self.network.add_edge("belem", "belemGW", weight=0 )
		self.network.add_edge("fortaleza", "fortalezaGW", weight=0 )
		self.network.add_edge("natal", "natalGW", weight=0 )
		self.network.add_edge("recife", "recifeGW", weight=0 )
		self.network.add_edge("salvador", "salvadorGW", weight=0 )

		#Add links between pops (38)
		self.network.add_edge("teresina", "recife", weight=931, bandwidth=3000  )
		self.network.add_edge("saoPaulo", "curitiba", weight=334, bandwidth=10000 )
		self.network.add_edge("goiania", "cuiaba", weight=740, bandwidth=10000  )
		self.network.add_edge("goiania", "palmas", weight=727, bandwidth=3000  )
		self.network.add_edge("brasilia", "goiania", weight=175, bandwidth=20000  )
		self.network.add_edge("fortaleza", "beloHorizonte", weight=1884, bandwidth=10000  )
		self.network.add_edge("belem", "teresina", weight=750, bandwidth=3000  )
		self.network.add_edge("belem", "macapa", weight=329, bandwidth=220  )
		self.network.add_edge("saoLuis", "belem", weight=482, bandwidth=10000  )
		self.network.add_edge("fortaleza", "saoLuis", weight=654, bandwidth=10000  )
		self.network.add_edge("natal", "fortaleza", weight=433, bandwidth=10000  )
		#Removed link in relation to the version of May 2013
		#self.network.add_edge("campinaGrande", "natal", weight=175, bandwidth=10000  )
		self.network.add_edge("recife", "campinaGrande", weight=141, bandwidth=10000  )
		self.network.add_edge("maceio", "recife", weight=202, bandwidth=10000  )
		self.network.add_edge("aracaju", "maceio", weight=202, bandwidth=10000  )
		self.network.add_edge("salvador", "aracaju", weight=277, bandwidth=10000  )
		self.network.add_edge("brasilia", "beloHorizonte", weight=628, bandwidth=10000  )
		self.network.add_edge("rioDeJaneiro", "brasilia", weight=932, bandwidth=10000  )
		self.network.add_edge("beloHorizonte", "salvador", weight=961, bandwidth=10000  )
		self.network.add_edge("vitoria", "salvador", weight=832, bandwidth=10000  )
		self.network.add_edge("rioDeJaneiro", "vitoria", weight=413, bandwidth=10000  )
		self.network.add_edge("saoPaulo", "rioDeJaneiro", weight=360, bandwidth=20000  )
		self.network.add_edge("saoPaulo", "beloHorizonte", weight=490, bandwidth=10000  )
		self.network.add_edge("florianopolis", "saoPaulo", weight=487, bandwidth=10000  )
		self.network.add_edge("portoAlegre", "florianopolis", weight=375, bandwidth=10000  )
		self.network.add_edge("curitiba", "portoAlegre", weight=543, bandwidth=10000  )
		self.network.add_edge("campoGrande", "curitiba", weight=779, bandwidth=10000  )
		self.network.add_edge("cuiaba", "campoGrande", weight=558, bandwidth=10000  ) 
		self.network.add_edge("portoVelho", "cuiaba", weight=1139, bandwidth=3000  )
		self.network.add_edge("rioBranco", "portoVelho", weight=444, bandwidth=3000  )
		self.network.add_edge("manaus", "brasilia", weight=1930, bandwidth=1000  )
		self.network.add_edge("boaVista", "manaus", weight=653, bandwidth=220  )
		self.network.add_edge("boaVista", "fortaleza", weight=2567, bandwidth=40  )
		#New links in relation to the version of May 2013
		self.network.add_edge("campinaGrande", "joaoPessoa", weight=115, bandwidth=10000  )
		self.network.add_edge("joaoPessoa", "natal", weight=154, bandwidth=10000  )
		self.network.add_edge("fortaleza", "recife", weight=629, bandwidth=10000  )
		self.network.add_edge("fortaleza", "rioDeJaneiro", weight=2191, bandwidth=10000  )
		self.network.add_edge("brasilia", "fortaleza", weight=1680, bandwidth=10000  )
		self.network.add_edge("brasilia", "belem", weight=1590, bandwidth=1000  )

		return self.network , self.nrDCLocations

	def __generateRENATER(self):

		#Add nodes
		self.network.add_node("brest1",type="dcLocation")
		self.network.add_node("brest2",type="dcLocation")
		self.network.add_node("quimper",type="dcLocation")
		self.network.add_node("roscoff",type="dcLocation")
		self.network.add_node("lannion",type="dcLocation")
		self.network.add_node("saint_brieuc",type="dcLocation")
		self.network.add_node("rennes",type="dcLocation")
		self.network.add_node("vannes",type="dcLocation")
		self.network.add_node("lorient",type="dcLocation")
		self.network.add_node("nantes",type="dcLocation")
		self.network.add_node("angers",type="dcLocation")
		self.network.add_node("lemans",type="dcLocation")
		self.network.add_node("tours",type="dcLocation")
		self.network.add_node("orleans",type="dcLocation")
		self.network.add_node("poitiers",type="dcLocation")
		self.network.add_node("nancay",type="dcLocation")
		self.network.add_node("bordeaux",type="dcLocation")
		self.network.add_node("pau",type="dcLocation")
		self.network.add_node("toulouse",type="dcLocation")
		self.network.add_node("limoges",type="dcLocation")
		self.network.add_node("clermont",type="dcLocation")
		self.network.add_node("lyon1",type="dcLocation")
		self.network.add_node("lyon2",type="dcLocation")
		self.network.add_node("marseille1",type="dcLocation")
		self.network.add_node("marseille2",type="dcLocation")
		self.network.add_node("marseilleGW1",type="gateway")
		self.network.add_node("marseilleGW2",type="gateway")
		self.network.add_node("montpellier",type="dcLocation")
		self.network.add_node("avignon",type="dcLocation")
		self.network.add_node("cardarache",type="dcLocation")
		self.network.add_node("toulon",type="dcLocation")
		self.network.add_node("sophia",type="dcLocation")
		self.network.add_node("corte",type="dcLocation")
		self.network.add_node("nice",type="dcLocation")
		self.network.add_node("grenoble",type="dcLocation")
		self.network.add_node("geneve",type="dcLocation")
		self.network.add_node("geneveGW",type="gateway")
		self.network.add_node("dijon",type="dcLocation")
		self.network.add_node("besancon",type="dcLocation")
		self.network.add_node("strasbourg",type="dcLocation")
		self.network.add_node("nancy",type="dcLocation")
		self.network.add_node("nancyGW",type="gateway")
		self.network.add_node("reims",type="dcLocation")
		self.network.add_node("paris1",type="dcLocation")
		self.network.add_node("paris2",type="dcLocation")
		self.network.add_node("parisGW1",type="gateway")
		self.network.add_node("parisGW2",type="gateway")
		self.network.add_node("parisGW3",type="gateway")
		self.network.add_node("parisGW4",type="gateway")
		self.network.add_node("parisGW5",type="gateway")
		self.network.add_node("caen",type="dcLocation")
		self.network.add_node("rouen",type="dcLocation")
		self.network.add_node("compiegne",type="dcLocation")
		self.network.add_node("lille",type="dcLocation")
		#new sites in October 2014
		self.network.add_node("laRochelle",type="dcLocation")
		self.network.add_node("niort",type="dcLocation")
		self.network.add_node("angouleme",type="dcLocation")



		self.nrDCLocations = 48

		#Add links to gateways
		self.network.add_edge("paris1", "parisGW1", weight=0 )
		self.network.add_edge("paris1", "parisGW2", weight=0 )
		self.network.add_edge("paris1", "parisGW3", weight=0 )
		self.network.add_edge("paris2", "parisGW4", weight=0 )
		self.network.add_edge("paris2", "parisGW5", weight=0 )
		self.network.add_edge("marseille1", "marseilleGW1", weight=0 )
		self.network.add_edge("marseille2", "marseilleGW2", weight=0 )
		self.network.add_edge("geneve", "geneveGW", weight=0 )
		self.network.add_edge("nancy", "nancyGW", weight=0 )

		#Add links between pops (63)
		self.network.add_edge("rennes", "caen", weight=153, bandwidth=10000)
		self.network.add_edge("brest1", "roscoff", weight=53, bandwidth=10000)
		self.network.add_edge("brest1", "quimper", weight=53, bandwidth=20000)
		self.network.add_edge("roscoff", "lannion", weight=39, bandwidth=10000 )
		self.network.add_edge("quimper", "lorient", weight=62, bandwidth=20000 )
		self.network.add_edge("lannion", "saint_brieuc", weight=57, bandwidth=20000 )
		self.network.add_edge("lorient", "vannes", weight=46, bandwidth=20000)
		self.network.add_edge("saint_brieuc", "rennes", weight=92, bandwidth=20000 )
		self.network.add_edge("vannes", "nantes", weight=103, bandwidth=20000 )
		self.network.add_edge("rennes", "nantes", weight=100, bandwidth=10000 )		
		self.network.add_edge("nantes", "bordeaux", weight=275, bandwidth=10000 )
		self.network.add_edge("bordeaux", "pau", weight=173, bandwidth=2500 )
		self.network.add_edge("pau", "toulouse", weight=151, bandwidth=2500 )
		self.network.add_edge("bordeaux", "toulouse", weight=212, bandwidth=10000 )
		self.network.add_edge("bordeaux", "clermont", weight=306, bandwidth=10000 )
		self.network.add_edge("bordeaux", "poitiers", weight=207, bandwidth=10000 )
		self.network.add_edge("poitiers", "limoges", weight=109, bandwidth=2500 )
		self.network.add_edge("limoges", "clermont", weight=142, bandwidth=2500 )
		self.network.add_edge("poitiers", "orleans", weight=189, bandwidth=10000 )
		self.network.add_edge("angers", "lemans", weight=82, bandwidth=10000 )			
		self.network.add_edge("lemans", "tours", weight=77, bandwidth=1000 )
		self.network.add_edge("tours", "orleans", weight=108, bandwidth=1000 )
		self.network.add_edge("orleans", "paris2", weight=111, bandwidth=10000 )
		self.network.add_edge("caen", "rouen", weight=111, bandwidth=10000 )
		self.network.add_edge("rouen", "paris1", weight=112, bandwidth=10000 )
		self.network.add_edge("paris1", "lille", weight=204, bandwidth=10000 )
		self.network.add_edge("lille", "compiegne", weight=136, bandwidth=10000 )
		self.network.add_edge("compiegne", "paris2", weight=68, bandwidth=10000 )
		self.network.add_edge("paris2", "reims", weight=131, bandwidth=10000 )
		self.network.add_edge("paris1", "nancy", weight=282, bandwidth=10000 )		
		self.network.add_edge("reims", "nancy", weight=169, bandwidth=10000 )
		self.network.add_edge("nancy", "strasbourg", weight=116, bandwidth=10000 )
		self.network.add_edge("strasbourg", "besancon", weight=197, bandwidth=10000 )
		self.network.add_edge("besancon", "dijon", weight=75, bandwidth=10000 )
		self.network.add_edge("dijon", "lyon1", weight=174, bandwidth=10000 )
		self.network.add_edge("lyon1", "paris1", weight=392, bandwidth=30000 )
		self.network.add_edge("lyon2", "paris2", weight=392, bandwidth=30000 )
		self.network.add_edge("paris1", "nancay", weight=170, bandwidth=10000 )
		self.network.add_edge("clermont", "lyon1", weight=136, bandwidth=20000 )
		self.network.add_edge("lyon2", "geneve", weight=112, bandwidth=20000 )
		self.network.add_edge("geneve", "grenoble", weight=116, bandwidth=10000 )	
		self.network.add_edge("lyon2", "grenoble", weight=95, bandwidth=10000 )
		self.network.add_edge("grenoble", "cardarache", weight=148, bandwidth=10000 )
		self.network.add_edge("lyon1", "marseille1", weight=278, bandwidth=20000 )
		self.network.add_edge("lyon2", "marseille2", weight=278, bandwidth=20000 )
		self.network.add_edge("marseille2", "avignon", weight=86, bandwidth=10000 )
		self.network.add_edge("marseille1", "cardarache", weight=94, bandwidth=10000 )
		self.network.add_edge("cardarache", "nice", weight=203, bandwidth=10000 )
		self.network.add_edge("nice", "sophia", weight=19, bandwidth=10000 )
		self.network.add_edge("sophia", "marseille1", weight=141, bandwidth=10000 )
		self.network.add_edge("sophia", "toulon", weight=106, bandwidth=10000 )
		self.network.add_edge("toulon", "marseille2", weight=49, bandwidth=10000 )	
		self.network.add_edge("marseille1", "montpellier", weight=126, bandwidth=10000 )
		self.network.add_edge("montpellier", "toulouse", weight=196, bandwidth=10000 )
		self.network.add_edge("brest1", "lannion", weight=85, bandwidth=20000 )
		self.network.add_edge("marseille2", "corte", weight=328, bandwidth=1000 )
		self.network.add_edge("nantes", "angers", weight=80, bandwidth=10000 )
		#New links in October 2014
		self.network.add_edge("poitiers","angouleme", weight=105, bandwidth=1000 )
		self.network.add_edge("angouleme","laRochelle", weight=116, bandwidth=1000 )
		self.network.add_edge("laRochelle","niort", weight=56, bandwidth=1000 )
		self.network.add_edge("niort","nantes", weight=129, bandwidth=1000 )
		self.network.add_edge("caen","paris1", weight=202, bandwidth=10000 )
		self.network.add_edge("avignon","cardarache", weight=9, bandwidth=10000 )

		
		#Add links between pops in the same city (4)
		self.network.add_edge("brest1", "brest2", weight=0, bandwidth=10000 )
		self.network.add_edge("lyon1", "lyon2", weight=0, bandwidth=20000 )
		self.network.add_edge("paris1", "paris2", weight=0, bandwidth=30000 )
		self.network.add_edge("marseille1", "marseille2", weight=0, bandwidth=20000 )

		return self.network , self.nrDCLocations

	def __generateGEANT(self):

		#Add nodes
		self.network.add_node("AT",type="dcLocation")
		self.network.add_node("AT_gw",type="gateway")
		self.network.add_node("BE",type="dcLocation")
		self.network.add_node("BG",type="dcLocation")
		self.network.add_node("BG_gw1",type="gateway")
		self.network.add_node("BG_gw2",type="gateway")
		self.network.add_node("CH",type="dcLocation")
		self.network.add_node("CY",type="dcLocation")
		self.network.add_node("CZ",type="dcLocation")
		self.network.add_node("DE_frankfurt",type="dcLocation")
		self.network.add_node("DE_frankfurt_gw1",type="gateway")
		self.network.add_node("DE_frankfurt_gw2",type="gateway")
		self.network.add_node("DE_frankfurt_gw3",type="gateway")
		self.network.add_node("DE_frankfurt_gw4",type="gateway")
		self.network.add_node("DE_berlim",type="dcLocation")
		self.network.add_node("DK",type="dcLocation")
		self.network.add_node("EE",type="dcLocation")
		self.network.add_node("ES",type="dcLocation")
		self.network.add_node("ES_gw1",type="gateway")
		self.network.add_node("ES_gw2",type="gateway")
		self.network.add_node("FI",type="dcLocation")
		self.network.add_node("FR_paris",type="dcLocation")
		self.network.add_node("FR_paris_gw1",type="gateway")
		self.network.add_node("FR_paris_gw2",type="gateway")
		self.network.add_node("FR_borderGeneve",type="dcLocation")
		self.network.add_node("GR",type="dcLocation")
		self.network.add_node("HR",type="dcLocation")
		self.network.add_node("HU",type="dcLocation")
		self.network.add_node("IE",type="dcLocation")
		self.network.add_node("IL",type="dcLocation")
		self.network.add_node("IS",type="dcLocation")
		self.network.add_node("IT",type="dcLocation")
		self.network.add_node("IT_gw",type="gateway")
		self.network.add_node("LT",type="dcLocation")
		self.network.add_node("LU",type="dcLocation")
		self.network.add_node("LV",type="dcLocation")
		self.network.add_node("ME",type="dcLocation")
		self.network.add_node("MK",type="dcLocation")
		self.network.add_node("MT",type="dcLocation")
		self.network.add_node("NL",type="dcLocation")
		self.network.add_node("NL_gw1",type="gateway")
		self.network.add_node("NL_gw2",type="gateway")
		self.network.add_node("NL_gw3",type="gateway")
		self.network.add_node("NL_gw4",type="gateway")
		self.network.add_node("NL_gw5",type="gateway")
		self.network.add_node("NO",type="dcLocation")
		self.network.add_node("PL",type="dcLocation")
		self.network.add_node("PT",type="dcLocation")
		self.network.add_node("RO",type="dcLocation")
		self.network.add_node("RS",type="dcLocation")
		self.network.add_node("BY",type="dcLocation")
		#Does not exist in October 2014 topology
		#self.network.add_node("RU",type="dcLocation")
		self.network.add_node("SE",type="dcLocation")
		self.network.add_node("SI",type="dcLocation")
		self.network.add_node("MD",type="dcLocation")
		self.network.add_node("SK",type="dcLocation")
		self.network.add_node("TR",type="dcLocation")
		self.network.add_node("UK",type="dcLocation")
		self.network.add_node("UK_gw1",type="gateway")
		self.network.add_node("UK_gw2",type="gateway")
		self.network.add_node("UK_gw3",type="gateway")
		self.network.add_node("UA",type="dcLocation")

		self.nrDCLocations = 41

		#Add links to gateways
		self.network.add_edge("IT", "IT_gw", weight=0 )
		self.network.add_edge("AT", "AT_gw", weight=0 )
		self.network.add_edge("NL", "NL_gw1", weight=0 )
		self.network.add_edge("NL", "NL_gw2", weight=0 )
		self.network.add_edge("NL", "NL_gw3", weight=0 )
		self.network.add_edge("NL", "NL_gw4", weight=0 )
		self.network.add_edge("NL", "NL_gw5", weight=0 )
		self.network.add_edge("FR_paris", "FR_paris_gw1", weight=0 )
		self.network.add_edge("FR_paris", "FR_paris_gw2", weight=0 )
		self.network.add_edge("UK", "UK_gw1", weight=0 )
		self.network.add_edge("UK", "UK_gw2", weight=0 )
		self.network.add_edge("UK", "UK_gw3", weight=0 )
		self.network.add_edge("BG", "BG_gw1", weight=0 )
		self.network.add_edge("BG", "BG_gw2", weight=0 )
		self.network.add_edge("DE_frankfurt", "DE_frankfurt_gw1", weight=0 )
		self.network.add_edge("DE_frankfurt", "DE_frankfurt_gw2", weight=0 )
		self.network.add_edge("DE_frankfurt", "DE_frankfurt_gw3", weight=0 )
		self.network.add_edge("DE_frankfurt", "DE_frankfurt_gw4", weight=0 )
		self.network.add_edge("ES", "ES_gw1", weight=0 )
		self.network.add_edge("ES", "ES_gw2", weight=0 )

		#Add links between pops (58 links)
		#On the map of October 2014 the capacity Some of the links are indicated in the maps in the limits between 1 and 10
		#To estimate the capacity for these links we have used capacity values indicated on the map of 2013
		#We have considered 100G for link indicated with more than 100G
		#Except some cases explicit mentioned on the GEANT map, we use as cities the capitol of each country
		self.network.add_edge("IS", "DK", weight=1242, bandwidth=10000 )
		self.network.add_edge("IS", "UK", weight=1887, bandwidth=2500 )
		self.network.add_edge("IE", "UK", weight=465, bandwidth=120000 )
		#self.network.add_edge("UK", "NL", weight=358, bandwidth= )
		self.network.add_edge("UK", "BE", weight=322, bandwidth=100000 )
		#self.network.add_edge("UK", "IL", weight=3614, bandwidth= )
		self.network.add_edge("UK", "CY", weight=3224, bandwidth=1000 )
		self.network.add_edge("UK", "FR_paris", weight=350, bandwidth=100000 )
		self.network.add_edge("UK", "PT", weight=1584, bandwidth=10000 )
		self.network.add_edge("FR_borderGeneve", "CH", weight=132, bandwidth=100000 )
		self.network.add_edge("FR_borderGeneve", "ES", weight=1022, bandwidth=100000 )
		self.network.add_edge("FR_borderGeneve", "IT", weight=246, bandwidth=100000 )
		self.network.add_edge("FR_paris", "ES", weight=1054, bandwidth=30000 )
		#self.network.add_edge("FR_paris", "LU", weight=287, bandwidth= )
		self.network.add_edge("FR_paris", "CH", weight=435, bandwidth=100000 )
		self.network.add_edge("PT", "ES", weight=501, bandwidth=10000 )
		#self.network.add_edge("ES", "CH", weight=1154, bandwidth= )
		#self.network.add_edge("ES", "IT", weight=1188, bandwidth= )
		self.network.add_edge("DE_berlim", "DK", weight=363, bandwidth=100000 )
		self.network.add_edge("DE_frankfurt", "CH", weight=352, bandwidth=100000 )
		self.network.add_edge("DE_frankfurt", "LU", weight=188, bandwidth=10000 )
		self.network.add_edge("DE_frankfurt", "IL", weight=2990, bandwidth=10000 )
		#self.network.add_edge("DE_frankfurt", "AT", weight=596, bandwidth= )
		self.network.add_edge("DE_frankfurt", "CY", weight=2591, bandwidth=1000 )
		self.network.add_edge("DE_frankfurt", "CZ", weight=412, bandwidth=100000 )
		self.network.add_edge("DE_frankfurt", "PL", weight=897, bandwidth=30000 )
		#self.network.add_edge("DE_frankfurt", "RU", weight=2032, bandwidth= )
		self.network.add_edge("DE_frankfurt", "DK", weight=685, bandwidth=100000 )
		self.network.add_edge("DE_frankfurt", "NL", weight=371, bandwidth=100000)
		self.network.add_edge("NL", "BE", weight=173, bandwidth=100000 )
		self.network.add_edge("NL", "DK", weight=615, bandwidth=100000 )
		self.network.add_edge("DK", "NO", weight=479, bandwidth=100000 )
		#self.network.add_edge("DK", "RU", weight=1565, bandwidth= )
		self.network.add_edge("DK", "SE", weight=524, bandwidth=100000 )
		self.network.add_edge("DK", "EE", weight=836, bandwidth=10000 )
		self.network.add_edge("NO", "SE", weight=412, bandwidth=100000 )
		self.network.add_edge("SE", "FI", weight=396, bandwidth=100000 )
		self.network.add_edge("EE", "LV", weight=286, bandwidth=10000 )
		self.network.add_edge("LV", "LT", weight=271, bandwidth=10000 )
		self.network.add_edge("LT", "PL", weight=383, bandwidth=10000 )
		self.network.add_edge("PL", "CZ", weight=519, bandwidth=10000 )
		self.network.add_edge("PL", "BY", weight=471, bandwidth=1000 )
		self.network.add_edge("PL", "UA", weight=689, bandwidth=1000 )
		self.network.add_edge("CZ", "SK", weight=287, bandwidth=100000 )
		self.network.add_edge("SK", "AT", weight=55, bandwidth=100000 )
		self.network.add_edge("SK", "HU", weight=162, bandwidth=100000 )
		self.network.add_edge("CH", "IT", weight=212, bandwidth=100000 )
		self.network.add_edge("AT", "IT", weight=625, bandwidth=100000 )
		self.network.add_edge("IT", "MT", weight=1153, bandwidth=2500 )
		self.network.add_edge("IT", "GR", weight=1466, bandwidth=20000 )	
		self.network.add_edge("AT", "GR", weight=1282, bandwidth=20000 )
		#self.network.add_edge("GR", "BG", weight=523, bandwidth= )
		self.network.add_edge("BG", "AT", weight=814, bandwidth=10000 )
		self.network.add_edge("BG", "MK", weight=174, bandwidth=1000 )
		#self.network.add_edge("BG", "TR", weight=850, bandwidth= )
		#self.network.add_edge("BG", "RO", weight=294, bandwidth= )
		self.network.add_edge("BG", "HU", weight=632, bandwidth=10000 )	
		#self.network.add_edge("RO", "TR", weight=750, bandwidth= )
		self.network.add_edge("RO", "MD", weight=359, bandwidth=1000 )
		self.network.add_edge("RO", "HU", weight=645, bandwidth=10000 )
		self.network.add_edge("RO", "AT", weight=858, bandwidth=10000 )	
		self.network.add_edge("AT", "SI", weight=290, bandwidth=100000 )
		self.network.add_edge("SI", "HR", weight=115, bandwidth=100000 )
		#self.network.add_edge("AT", "HR", weight=270, bandwidth= )	
		#self.network.add_edge("SI", "HU", weight=387, bandwidth= )
		self.network.add_edge("HR", "HU", weight=302, bandwidth=100000 )
		self.network.add_edge("RS", "HU", weight=319, bandwidth=10000 )	
		self.network.add_edge("ME", "HU", weight=560, bandwidth=10000 )
		self.network.add_edge("NL","DE_berlim", weight=581, bandwidth=100000 )
		self.network.add_edge("NL", "LU", weight=298, bandwidth=10000 )
		self.network.add_edge("DE_frankfurt", "TR", weight=2194, bandwidth=10000 )
		self.network.add_edge("TR", "HU", weight=1395, bandwidth=20000 )

		return self.network , self.nrDCLocations

class SRGgenerator():
		def __init__(self,network,srgType,parameters=""):
			self.network = network
			self.srgType = srgType
			self.parameters = parameters	

		def generateSRG(self):
			if (self.srgType == "oneFailure"):
				return self.__generateOneFailureSRG()
			elif (self.srgType == "allkFailures"):
				try:
					k = self.parameters["k"]
				except:
					print "Invalid Parameter for SRG allkFailures"
					return False
				return self.__generateAllkFailures(k)
			else:
				print "Invalid SRG"
				return False

		#This SRG model consider failure in each DC location and on each link (between dc locations and between GW and DC location)
		def __generateOneFailureSRG(self):
			srgSet = []
			#Add all the dc locations to the srg set
			for node in self.network:
				if (self.network.node[node]["type"] == "dcLocation"):
					srgSet.append({"nodes":[node],"links":[]})
			#Add all the links to the srg set
			allEdges = self.network.edges()
			for edge in allEdges:
				srgSet.append({"nodes":[],"links":[edge]})

			return list(srgSet)

		#This SRG model consider every combination of two DC location and link (between dc locations and between GW and DC location)
		def __generateAllkFailures(self,k):
			import itertools
			srgSet = []
			#Get all DC locations
			allDcLocations = []
			for node in self.network:
				if (self.network.node[node]["type"] == "dcLocation"):
					allDcLocations.append(node)
			#Add all the links to the srg set
			allEdges = self.network.edges()

			#List with all elements (edges and nodes)
			allElements = allDcLocations + allEdges

			#Generate combinations of all k failures
			allCombinations = list(itertools.combinations(allElements,k))

			#Write the SRGs
			for comb in allCombinations:
				#For each combination check if it is a node or a link
				nodes = []
				links = []
				for element in comb:
					if (element in allEdges):
						links.append(element)
					else:
						nodes.append(element)
				#Write the SGR
				srgSet.append({"nodes":list(nodes),"links":list(links)})

			return list(srgSet)
			
