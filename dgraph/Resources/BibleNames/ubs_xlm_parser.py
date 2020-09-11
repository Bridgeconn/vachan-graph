import xml.etree.ElementTree as ET 
import csv 

books_lookup = { 1: "gen", 2 : "exo",	3 : "lev",	4 : "num",	5 : "deu",	6 : "jos",	7 : "jdg",	8 : "rut",	9 : "1sa",	10 : "2sa",	11 : "1ki",	12 : "2ki",	13 : "1ch",	14 : "2ch",	15 : "ezr",	16 : "neh",	17 : "est",	18 : "job",	19 : "psa",	20 : "pro",	21 : "ecc",	22 : "sng",	23 : "isa",	24 : "jer",	25 : "lam",	26 : "ezk",	27 : "dan",	28 : "hos",	29 : "jol",	30 : "amo",	31 : "oba",	32 : "jon",	33 : "mic",	34 : "nam",	35 : "hab",	36 : "zep",	37 : "hag",	38 : "zec",	39 : "mal",	40 : "mat",	41 : "mrk",	42 : "luk",	43 : "jhn",	44 : "act",	45 : "rom",	46 : "1co",	47 : "2co",	48 : "gal",	49 : "eph",	50 : "php",	51 : "col",	52 : "1th",	53 : "2th",	54 : "1ti",	55 : "2ti",	56 : "tit",	57 : "phm",	58 : "heb",	59 : "jas",	60 : "1pe",	61 : "2pe",	62 : "1jn",	63 : "2jn",	64 : "3jn",	65 : "jud",	66 : "rev" }

def parseXML(xmlfile,flag): 
  
	# create element tree object 
	tree = ET.parse(xmlfile) 
	root = tree.getroot() 
	names_list = [] 
  
	# iterate name entries 
	for item in root.findall('./Entry'): 
		name = {} 

		name['id'] = item.find('ID').text + flag
		name['name'] = item.find('Subentry/Gloss-EN').text
		# name['language'] = item.find('Language').text
		# name['original-word'] = item.find('Word').text
		name['description'] = item.find('Subentry/Definition-EN').text
		# name['type'] = item.find('Subentry/Class').text
		name['occurances'] = {}
		for ref in item.find('Subentry/References'):
			bbbcccvvv__ = ref.text
			book = int(bbbcccvvv__[:3])
			book_name = books_lookup[book]
			# chapter = int(bbbcccvvv__[3:6])
			# verse = int(bbbcccvvv__[6:9])
			# pos = int(bbbcccvvv__[9:])
			# name['occurances'].append((book,chapter,verse,pos))
			if book_name not in name['occurances']:
				name['occurances'][book_name] = 1
			else:
				name['occurances'][book_name] += 1
		names_list.append(name) 
	  
	return names_list 

def get_nt_ot_names_from_ubs():  
	names = parseXML('2008-04-entity-database/ubs-names-ot.xml','ot')
	names += parseXML('2008-04-entity-database/ubs-names-nt.xml','nt')
	return names

# names = get_nt_ot_names_from_ubs()
# print(len(names))