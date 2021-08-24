from fastapi import FastAPI, Query, Path, Body, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import subprocess
import unicodedata
import pymysql
from dGraph_conn import dGraph_conn
import logging, csv, urllib, json, itertools, re
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

import networkx as nx
import matplotlib.pyplot as plt

from Resources.BibleNames.ubs_xlm_parser import get_nt_ot_names_from_ubs

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
graph_conn = None
rel_db_name = 'AutographaMT_Staging'
logging.basicConfig(filename='example.log',level=logging.DEBUG)
base_URL = 'http://localhost:7000'

non_letters = [',', '"', '!', '.', '\n', '\\','“','”','“','*','।','?',';',"'","’","(",")","‘","—"]
non_letter_pattern = re.compile(r'['+''.join(non_letters)+']')

book_num_map = { "mat": 40 ,"mrk": 41 ,"luk": 42 ,"jhn": 43 ,"act": 44 ,"rom": 45 ,"1co": 46 ,"2co": 47 ,"gal": 48 ,"eph": 49 ,"php": 50 ,"col": 51 ,"1th": 52 ,"2th": 53 ,"1ti": 54 ,"2ti": 55 ,"tit": 56 ,"phm": 57 ,"heb": 58 ,"jas": 59 ,"1pe": 60 ,"2pe": 61 ,"1jn": 62 ,"2jn": 63 ,"3jn": 64 ,"jud": 65 ,"rev": 66, "Genesis": 1, "GEN": 1, "Exodus": 2, "EXO": 2, "Leviticus": 3, "LEV": 3, "Numbers": 4, "NUM": 4, "Deuteronomy": 5, "DEU": 5, "Joshua": 6, "JOS": 6, "Judges": 7, "JDG": 7, "Ruth": 8, "RUT": 8, "1 Samuel": 9, "1SA": 9, "2 Samuel": 10, "2SA": 10, "1 Kings": 11, "1KI": 11, "2 Kings": 12, "2KI": 12, "1 Chronicles": 13, "1CH": 13, "2 Chronicles": 14, "2CH": 14, "Ezra": 15, "EZR": 15, "Nehemiah": 16, "NEH": 16, "Esther": 17, "EST": 17, "Job": 18, "JOB": 18, "Psalms": 19, "PSA": 19, "Proverbs": 20, "PRO": 20, "Ecclesiastes": 21, "ECC": 21, "Song of Solomon": 22, "SNG": 22, "Isaiah": 23, "ISA": 23, "Jeremiah": 24, "JER": 24, "Lamentations": 25, "LAM": 25, "Ezekiel": 26, "EZK": 26, "Daniel": 27, "DAN": 27, "Hosea": 28, "HOS": 28, "Joel": 29, "JOL": 29, "Amos": 30, "AMO": 30, "Obadiah": 31, "OBA": 31, "Jonah": 32, "JON": 32, "Micah": 33, "MIC": 33, "Nahum": 34, "NAM": 34, "Habakkuk": 35, "HAB": 35, "Zephaniah": 36, "ZEP": 36, "Haggai": 37, "HAG": 37, "Zechariah": 38, "ZEC": 38, "Malachi": 39, "MAL": 39, "Matthew": 40, "MAT": 40, "Mark": 41, "MRK": 41, "Luke": 42, "LUK": 42, "John": 43, "JHN": 43, "Acts": 44, "ACT": 44, "Romans": 45, "ROM": 45, "1 Corinthians": 46, "1CO": 46, "2 Corinthians": 47, "2CO": 47, "Galatians": 48, "GAL": 48, "Ephesians": 49, "EPH": 49, "Philippians": 50, "PHP": 50, "Colossians": 51, "COL": 51, "1 Thessalonians": 52, "1TH": 52, "2 Thessalonians": 53, "2TH": 53, "1 Timothy": 54, "1TI": 54, "2 Timothy": 55, "2TI": 55, "Titus": 56, "TIT": 56, "Philemon": 57, "PHM": 57, "Hebrews": 58, "HEB": 58, "James": 59, "JAS": 59, "1 Peter": 60, "1PE": 60, "2 Peter": 61, "2PE": 61, "1 John": 62, "1JN": 62, "2 John": 63, "2JN": 63, "3 John": 64, "3JN": 64, "Jude": 65, "JUD": 65, "Revelation": 66, "REV": 66, "Psalm": 19, "PSA": 19,
"GEN": 1,	"EXO": 2,	"LEV": 3,	"NUM": 4,	"DEU": 5,	"JOS": 6,	"JDG": 7,	"RUT": 8,	"1SA": 9,	"2SA": 10,	"1KI": 11,	"2KI": 12,	"1CH": 13,	"2CH": 14,	"EZR": 15,	"NEH": 16,	"EST": 17,	"JOB": 18,	"PSA": 19,	"PRO": 20,	"ECC": 21,	"SNG": 22,	"ISA": 23,	"JER": 24,	"LAM": 25,	"EZK": 26,	"DAN": 27,	"HOS": 28,	"JOL": 29,	"AMO": 30,	"OBA": 31,	"JON": 32,	"MIC": 33,	"NAM": 34,	"HAB": 35,	"ZEP": 36,	"HAG": 37,	"ZEC": 38,	"MAL": 39}

num_book_map = {}
for key in book_num_map:
	num_book_map[book_num_map[key]] = key

class BibleBook(str, Enum):
	mat = "mat"
	mrk = "mrk"
	luk = "luk"
	jhn = "jhn"
	act = "act"
	rom = "rom"
	co1 = "1co"
	co2 = "2co"
	gal = "gal"
	eph = "eph"
	php = "php"
	col = "col"
	th1 = "1th"
	th2 = "2th"
	ti1 = "1ti"
	ti2 = "2ti"
	tit = "tit"
	phm = "phm"
	heb = "heb"
	jas = "jas"
	pe1 = "1pe"
	pe2 = "2pe"
	jn1 = "1jn"
	jn2 = "2jn"
	jn3 = "3jn"
	jud = "jud"
	rev = "rev"

class Reference(BaseModel):
	book : BibleBook
	chapter: int
	verse: int

@app.get("/", status_code=200)
def test():
	return {'msg': "server up and running"}


############### Graph #####################

@app.get("/graph", status_code = 200, tags=["READ", "Graph"])
def connect_Graph():
	''' connects to the dgraph server'''
	global graph_conn
	try:
		graph_conn = dGraph_conn()
	except Exception as e:
		logging.error('At connecting to graph DB')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Not connected to Graph. "+ str(e))
	return {'msg': 'Connected to graph'}

@app.delete("/graph", status_code=200, tags=["Graph", "WRITE"])
def delete():
	''' delete the entire graph'''
	global graph_conn
	try:
		res = graph_conn.drop_all()
	except Exception as e:
		logging.error('At deleting graph DB')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	return {'msg': 'Deleted the entire graph'}

############### Strongs Numbers ###########################

strong_dict_query = '''
		query dict($dummy: string){
		dict(func: eq(dictionary, "Greek Strongs")){
			uid
		} }
'''

all_strongs_query = '''
		query strongs($dummy: string){
		strongs(func: has(StrongsNumber)){
			uid,
			StrongsNumber,
			pronunciation,
			lexeme,
			transliteration,
			definition,
			strongsNumberExtended,
			englishWord
		} }
'''


strongs_link_query = '''
		query strongs( $strongs: string){
		strongs(func: eq(StrongsNumber, $strongs)) {
			StrongsNumber,
			pronunciation,
			lexeme,
			transliteration,
			definition,
			strongsNumberExtended,
			englishWord,
			occurances:~strongsLink @normalize{
				~alignsTo{
				position:position,
				word:word,
				belongsTo{
					verse: verse,
					belongsTo{
						chapter:chapter,
						belongsTo{
						  book:bookNumber,
						  belongsTo {
						   bible:bible 
	}	}	}	}	}	} } }
'''

strongs_in_verse_query = '''
	query strongs($book: string, $chap:int, $ver: int){
	strongs (func: has(bible)) @cascade  @normalize{
		~belongsTo @filter (eq(bookNumber,$book)) {
			~belongsTo @filter( eq(chapter, $chap)) {
				~belongsTo @filter (eq(verse, $ver)) {
					~belongsTo{
						position: position,
						word:word,
						strongsLink {
							StrongsNumber:StrongsNumber
	}	}	}	}	}	} }
'''

strong_node_query  = """
				query strongs($strongs: int){
				  u as var(func: eq(strongsNumber, $strongs))
				}"""

class StrongsProperty(str, Enum):
	pronunciation = 'pronunciation'
	lexeme = 'lexeme'
	transliteration = 'transliteration'
	definition = 'definition'
	strongsNumberExtended = 'strongsNumberExtended'
	englishWord = 'englishWord'

class StrongsPropertyValue(BaseModel):
	property: StrongsProperty
	value: str

@app.get("/strongs", status_code=200, tags=["READ", "Strongs Number"])
def get_strongs(strongs_number: Optional[int] = None, bbbcccvvv: Optional[str] = Query(None, regex='^\w\w\w\d\d\d\d\d\d'), skip: Optional[int] =None, limit: Optional[int]=None):
	''' Get the list of strongs nodes and their property values.
	If strongs_number is sepcified, its properties and occurances are returned.
	If strongs_number is not present and bbbcccvvv(bbb- 3 letter bookcode, ccc- chapter number in 3 digits, vvv- verse number in 3 digits)
	is provided, lists all strongs in that verse, with their property values and positions(as per Gree bible).
	If neither of the first two query params are provided, it lists all the strongs numbers in Greek.
	Number of items returned can be set using the skip and limit parameters.'''
	result = {}
	try:
		if not strongs_number and not bbbcccvvv:
			query_res = graph_conn.query_data(all_strongs_query,{'$dummy':''})
		elif strongs_number:
			query_res = graph_conn.query_data(strongs_link_query,{'$strongs':str(strongs_number)})
			logging.info('query_res: %s' % query_res)
		else:
			variables = {
						'$book': str(book_num_map[bbbcccvvv[:3].lower()]),
						'$chap':bbbcccvvv[3:6],
						'$ver': bbbcccvvv[-3:]
						}
			logging.info('variables: %s' % variables)
			query_res = graph_conn.query_data(strongs_in_verse_query, variables)
			logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching strongs numbers')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	logging.info('skip: %s, limit %s' % (skip, limit))
	if not skip:
		skip = -1
	if not limit:
		limit = len(query_res['strongs'])
	result['strongs'] = query_res['strongs'][skip+1:limit]
	for i, strong in enumerate(result['strongs']):
		if 'occurances' in strong:
			occurs = []
			for occur in strong['occurances']:
				logging.info(occur)
				logging.info(num_book_map)
				verse_link = '%s/bibles/%s/books/%s/chapters/%s/verses/%s/words/%s'%(base_URL, occur['bible'], num_book_map[occur['book']], occur['chapter'], occur['verse'], occur['position'])
				occurs.append(urllib.parse.quote(verse_link, safe='/:-'))
			result['strongs'][i]['occurances'] = occurs
		if 'StrongsNumber' in strong:
			strong_link = '%s/strongs?strongs_number=%s'%(base_URL, strong['StrongsNumber'])
			result['strongs'][i]['strongsLink'] = urllib.parse.quote(strong_link, safe='/:?=')
	return result

@app.put("/strongs/{strongs_number}", status_code = 200, tags=["Strongs Number", "WRITE"])
def edit_strongs(strongs_number: int, key_values: List[StrongsPropertyValue] = Body(...)):
	''' Update a property value of selected strongs number node'''
	logging.info("input args strongs_number: %s, key_values: %s" % (strongs_number, key_values))
	nquad = ''
	for prop in key_values:
		nquad +=	'uid(u) <%s> "%s" .\n' %(prop.property.value, prop.value)
	logging.info('nquad: %s' %nquad)
	try:
		graph_conn.upsert(query=strong_node_query, nquad=nquad, variables={'$strongs': str(strongs_number)})
	except Exception as e:
		logging.error('At editing strongs numbers')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	raise HTTPException(status_code=503, detail="Not implemented properly. ")


@app.post("/strongs", status_code=201, tags=["WRITE", "Strongs Number"])
def add_strongs():
	'''creates a strongs dictionary.
	 Collects strongs data from mysql DB and add to graph 
	 '''
	try:
		db = pymysql.connect(host="localhost",database=rel_db_name, user="root", password="password", charset='utf8mb4')
		cursor = db.cursor(pymysql.cursors.SSCursor)
	except Exception as e:
		logging.error("At MySql DB connection")
		logging.error(e)
		raise HTTPException(status_code=502, detail="MySQL side error. "+str(e))

	tablename = 'Greek_Strongs_Lexicon'
	nodename = 'Greek Strongs'

	# create a dictionary nodename
	dict_node = { 'dictionary': nodename,
				   'dgraph.type': "DictionaryNode"
			}
	try:
		dict_node_uid = graph_conn.create_data(dict_node)
	except Exception as e:
		logging.error("At dict node creation")
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	logging.info('dict_node_uid: %s' %dict_node_uid)

	cursor.execute("Select ID, Pronunciation, Lexeme, Transliteration, Definition, StrongsNumber, EnglishWord from "+tablename+" order by ID")

	count_for_test = 0
	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break
		# if count_for_test>50:
		# 	break
		count_for_test += 1
		strongID = next_row[0]
		Pronunciation = next_row[1]
		Lexeme = next_row[2]
		Transliteration = next_row[3]
		Definition = next_row[4]
		StrongsNumberExtended = next_row[5]
		EnglishWord = next_row[6]

		strong_node = {
			'dgraph.type': "StrongsNode",
			'StrongsNumber':strongID,
			'pronunciation': Pronunciation,
			'lexeme': Lexeme,
			'transliteration': Transliteration,
			'definition': Definition,
			'strongsNumberExtended': StrongsNumberExtended,
			'englishWord': EnglishWord,
			'belongsTo':{
				'uid': dict_node_uid
				}		
			}
		try:
			strong_node_uid = graph_conn.create_data(strong_node)
		except Exception as e:
			logging.error("At strong node creation")
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		logging.info('strong_node_uid: %s' %strong_node_uid)

	cursor.close()
	db.close()
	return {'msg': 'Added to graph'} # created


##################### Translation Words ######################

all_tw_query = '''
	query tw($dummy: string){
	tw(func: has(translationWord)){
		translationWord,
		slNo,
		twType,
		description,
	}
	}
'''

tw_link_query = '''
	query tw($tw: string){
	tw(func: eq(translationWord, $tw)){
		translationWord,
		slNo,
		twType,
		description,
		occurances: ~twLink @normalize {
			~alignsTo {
			position:position,
			word:word,
			belongsTo{
				verse: verse,
				belongsTo{
					chapter:chapter,
					belongsTo{
					  book:bookNumber,
					  belongsTo {
					   bible:bible 
	}	}	}	}	} }	} }
'''

tw_in_verse_query = '''
	query tw($book: string, $chap:int, $ver: int){
	tw (func: has(bible)) @cascade  @normalize{
		~belongsTo @filter (eq(bookNumber,$book)) {
			~belongsTo @filter( eq(chapter, $chap)) {
				~belongsTo @filter (eq(verse, $ver)) {
					~belongsTo{
						position: position,
						word:word,
						twLink {
							translationWord:translationWord,
	}	}	}	}	}	} }
'''

tw_node_query  = """
				query tw($tw: str){
				  u as var(func: eq(translationWord, $tw))
				}"""


class TwProperty(str, Enum):
	slNo= 'slNo'
	twType= 'twType'
	description= 'description'
	wordForms = 'wordForms'

class TwPropertyValue(BaseModel):
	property: TwProperty
	value: str


@app.get("/translationwords", status_code=200, tags=["READ", "Translation Words"])
def get_translationwords(translation_word: Optional[str] = None, bbbcccvvv: Optional[str] = Query(None, regex='^\w\w\w\d\d\d\d\d\d'), skip: Optional[int] =None, limit: Optional[int]=None):
	''' Get the list of Translation word nodes and their property values.
	If Translation word is sepcified, its properties and occurances are returned.
	If Translation word is not present and bbbcccvvv(bbb- 3 letter bookcode, ccc- chapter number in 3 digits, vvv- verse number in 3 digits)
	is provided, lists all Translation words in that verse, with their property values and positions(as per Gree bible).
	If neither of the first two query params are provided, it lists all the Translation words.
	Number of items returned can be set using the skip and limit parameters.'''
	result = {}
	try:
		if not translation_word and not bbbcccvvv:
			query_res = graph_conn.query_data(all_tw_query,{'$dummy':''})
		elif translation_word:
			query_res = graph_conn.query_data(tw_link_query,{'$tw':translation_word})
			logging.info('query_res: %s' % query_res)
		else:
			variables = {
						'$book': str(book_num_map[bbbcccvvv[:3].lower()]),
						'$chap':bbbcccvvv[3:6],
						'$ver': bbbcccvvv[-3:]
						}
			logging.info('variables: %s' % variables)
			query_res = graph_conn.query_data(tw_in_verse_query, variables)
			logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching translation words')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	logging.info('skip: %s, limit %s' % (skip, limit))
	if not skip:
		skip = -1
	if not limit:
		limit = len(query_res['tw'])
	result['translationWords'] = query_res['tw'][skip+1:limit]
	for i, tw in enumerate(result['translationWords']):
		if 'occurances' in tw:
			occurs = []
			for occur in tw['occurances']:
				verse_link = '%s/bibles/%s/books/%s/chapters/%s/verses/%s/words/%s'%(base_URL, occur['bible'], num_book_map[occur['book']], occur['chapter'], occur['verse'], occur['position'])
				occurs.append(urllib.parse.quote(verse_link, safe='/:-'))
			result['translationWords'][i]['occurances'] = occurs
		if 'translationWord' in tw:
			link = '%s/translationwords?translation_word=%s'%(base_URL, tw['translationWord'])
			result['translationWords'][i]['translationWordLink'] = urllib.parse.quote(link, safe='/:?=')
	return result


@app.put("/translationwords/{translation_word}", status_code = 200, tags=["WRITE", "Translation Words"])
def edit_translationwords(translation_word: str, key_values: List[TwPropertyValue] = Body(...)):
	''' Update a property value of selected Translation word'''
	logging.info("input args translation_word: %s, key_values: %s" % (translation_word, key_values))
	nquad = ''
	for prop in key_values:
		nquad +=	'uid(u) <%s> "%s" .\n' %(prop.property.value, prop.value)
	logging.info('nquad: %s' %nquad)
	try:
		graph_conn.upsert(query=tw_node_query, nquad=nquad, variables={'$tw': translation_word})
	except Exception as e:
		logging.error('At editing translation word')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	raise HTTPException(status_code=503, detail="Not implemented properly. ")


@app.post("/translationwords", status_code=201, tags=["WRITE", "Translation Words"])
def add_translationwords():
	'''creates a translation word dictionary.
	 Collects tw data from CSV file and adds to graph 
	 '''
	tw_path = 'Resources/translationWords/tws.csv'
	nodename = 'translation words'

	# create a dictionary nodename
	dict_node = { 'dictionary': nodename,
				  'dgraph.type': "DictionaryNode"
			}
	try:
		dict_node_uid = graph_conn.create_data(dict_node)
	except Exception as e:
		logging.error("At dict node creation")
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	logging.info('dict_node_uid:%s' %dict_node_uid)

	count_for_test = 0
	with open(tw_path) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='\t')
		for row in csv_reader:
			# if count_for_test>50:
			# 	break
			count_for_test += 1

			sl_no = row[0]
			tw = row[1]
			Type = row[2]
			word_forms = row[3].split(',')
			description = row[4]
			tw_node = {
				'dgraph.type': "TWNode",
				'translationWord':tw,
				'slNo': sl_no,
				'twType': Type,
				'description':description,
				'belongsTo':{
				'uid': dict_node_uid
				}		
			}
			if len(word_forms)>0:
				tw_node['wordForms'] = word_forms
			try:
				tw_node_uid = graph_conn.create_data(tw_node)
			except Exception as e:
				logging.error("At tw node creation")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
			logging.info('tw_node_uid:%s' %tw_node_uid)
	return {'msg': 'Added to graph'}



########################### Bible Names ###########################













##################### Bible ##########################

all_bibles_query = '''
	query bibles($dummy: string){
	bibles(func: has(bible)){
		bible,
		language,
		books : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
		}
	}
	}

'''

bible_name_query = '''
	query bibles($bib: string){
	bibles(func: eq(bible, $bib)){
		bible,
		language,
		books : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
		}
	}
	}

'''

bible_lang_query = '''
	query bibles($lang: string){
	bibles(func: has(bible)) @filter(eq(language, $lang)){
		bible,
		language,
		version,
		books : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
		}
	}
	}

'''

bible_node_query  = """
				query bible($bib: string){
				  u as var(func: eq(bible, $bib))
				}"""

bible_uid_query = '''
	query bible($bib: string){
	bible(func: eq(bible, $bib)){
		uid
	}
	}
'''

bookNode_query = '''
		query book($bib: string, $book: string){
		book(func: uid($bib))
		@normalize {
				~belongsTo @filter (eq(book,$book)){
				uid : uid
				}
		}
		}
	'''
chapNode_query = '''
		query book($chap: int, $book: string){
		chapter(func: uid($book))
		@normalize {
				~belongsTo @filter (eq(chapter,$chap)){
				uid : uid
				}
		}
		}
	'''
verseNode_query = '''
		query book($chapter: string, $verse: int){
		verse(func: uid($chapter))
		@normalize {
				~belongsTo @filter (eq(verse,$verse)){
				uid : uid
				}
		}
		}
	'''
strongNode_query = '''
	query strongs($strongnum: int){
	strongs(func: eq(StrongsNumber,$strongnum)){
		uid
	}
	}
'''
twNode_query = '''
	query tw($word: string){
	tw(func: eq(translationWord, $word) ){
		uid
	}
	}
	'''

class BibleProperty(str, Enum):
	language= 'language'
	version= 'version'

class BiblePropertyValue(BaseModel):
	property: BibleProperty
	value: str

@app.get('/bibles', status_code=200, tags=["READ", "Bible Contents"])
def get_bibles(bible_name : Optional[str] = None, language: Optional[str] = None, skip: Optional[int] = None, limit: Optional[int] = None):
	''' fetches bibles nodes, properties and available books. 
	If no query params are given, all bibles in graph are fetched.
	If bible_name is specified, only that node is returned.
	If only language if given, all bible nodes, and details vavailable in that language is returned
	Number of items returned can be set using the skip and limit parameters.
	'''
	result = {}
	try:
		if not bible_name and not language:
			query_res = graph_conn.query_data(all_bibles_query,{'$dummy':''})
		elif bible_name:
			query_res = graph_conn.query_data(bible_name_query,{'$bib':bible_name})
			logging.info('query_res: %s' % query_res)
		else:
			query_res = graph_conn.query_data(bible_lang_query,{'$lang':language})
			logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching Bibles')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	logging.info('skip: %s, limit %s' % (skip, limit))
	if not skip:
		skip = -1
	if not limit:
		limit = len(query_res['bibles'])
	result['bibles'] = query_res['bibles'][skip+1:limit]
	return result

@app.put('/bibles/{bible_name}', status_code=200, tags=["WRITE", "Bible Contents"])
def edit_bible(bible_name: str, key_values: List[BiblePropertyValue]):
	''' Update a property value of selected bible node'''
	logging.info("input args bible_name: %s, key_values: %s" % (bible_name, key_values))
	nquad = ''
	for prop in key_values:
		nquad +=	'uid(u) <%s> "%s" .\n' %(prop.property.value, prop.value)
	logging.info('nquad: %s' %nquad)
	try:
		graph_conn.upsert(query=bible_node_query, nquad=nquad, variables={'$bib': bible_name})
	except Exception as e:
		logging.error('At editing Bible ')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	raise HTTPException(status_code=503, detail="Not implemented properly. ")

def normalize_unicode(text, form="NFKC"):
    '''to normalize text contents before adding them to DB'''
    return unicodedata.normalize(form, text)

def parse_usfm(usfm_string):
    '''converts an uploaded usfm text to a JSON using usfm-grammar'''
    if isinstance(usfm_string, bytes):
    	usfm_string = usfm_string.decode('UTF-8')
    file= open("temp.usfm", "w")
    file.write(usfm_string)
    file.close()
    process = subprocess.Popen(['/usr/bin/usfm-grammar temp.usfm --level=relaxed --filter=scripture'],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)
    stdout, stderr = process.communicate()
    if stderr:
        raise Exception(stderr.decode('utf-8'))
    usfm_json = json.loads(stdout.decode('utf-8'))
    return usfm_json

punct_pattern = re.compile('['+"".join([',', '"', '!', '.', ':', ';', '\n', '\\','“','”',
        '“','*','।','?',';',"'","’","(",")","‘","—"])+']')

@app.post('/bibles/usfm', status_code = 200, tags=["WRITE", "Bible Contents"])
def add_bible_usfm(bible_name: str = Body("Hindi IRV4 bible"), language: str = Body("Hindi"), version: str = Body('IRV4'), usfm_file: UploadFile = File(...)):
	'''Processes the usfm and adds contents to corresponding bible(creates new bible if not present already)'''
	usfm = usfm_file.file.read()
	# print(usfm)
	connect_Graph()
	try:
		bibNode_query_res = graph_conn.query_data(bible_uid_query,{'$bib':bible_name})
	except Exception as e:
		logging.error('At fetching Bible uid')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))

	if len(bibNode_query_res['bible']) == 0:
		# create a bible nodename
		bib_node = { 
			'dgraph.type': "BibleNode",
			'bible': bible_name,
			'language' : language,
			'version': str(version)
				}
		try:
			bib_node_uid = graph_conn.create_data(bib_node)
			logging.info('bib_node_uid: %s' %bib_node_uid)
		except Exception as e:
			logging.error('At creating Bible node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	elif len(bibNode_query_res['bible']) > 1:
		logging.error('At fetching Bible uid')
		logging.error( 'matched multiple bible nodes')
		raise HTTPException(status_code=500, detail="Graph side error. "+' matched multiple bible nodes')
	else:
		bib_node_uid = bibNode_query_res['bible'][0]['uid']	

	book_json = parse_usfm(usfm)
	book_code = book_json['book']['bookCode'].upper()
	book_num = book_num_map[book_code.upper()]

	# to find/create book node
	variables = {
		'$bib': bib_node_uid,
		'$book': book_code
	}
	try:
		bookNode_query_res = graph_conn.query_data(bookNode_query,variables)
	except Exception as e:
		logging.error('At fetching book node')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	if len(bookNode_query_res['book']) == 0:
		bookNode = {
			'dgraph.type': "BookNode",
			'book' : book_code,
			'bookNumber': book_num,
			'belongsTo' : {
				'uid': bib_node_uid 
			}
		}
		try:
			bookNode_uid = graph_conn.create_data(bookNode)
		except Exception as e:
			logging.error('At creating book node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	elif len(bookNode_query_res['book']) > 1:
		logging.error('At fetching book node')
		logging.error("Matched multiple book nodes")
		raise HTTPException(status_code=500, detail="Graph side error. Matched multiple book nodes")
	else:
		bookNode_uid = bookNode_query_res['book'][0]['uid']

	for chapter in book_json['chapters']:
		chapter_num = chapter['chapterNumber']
		# to find/create chapter node
		variables = {
			'$book': bookNode_uid,
			'$chap': str(chapter_num)
		}
		try:
			chapNode_query_res = graph_conn.query_data(chapNode_query,variables)
		except Exception as e:
			logging.error('At fetching chapter node')
			logging.error(e)
			raise HTTPException(status_code=500, detail="Graph side error. "+ str(e))

		if len(chapNode_query_res['chapter']) == 0:
			chapNode = {
				'dgraph.type': "ChapterNode",
				'chapter' : chapter_num,
				'belongsTo' : {
					'uid': bookNode_uid 
				}
			}
			try:
				chapNode_uid = graph_conn.create_data(chapNode)
			except Exception as e:
				logging.error('At creating chapter node')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		elif len(chapNode_query_res['chapter']) > 1:
			logging.error('At fetching chapter node')
			logging.error("Matched multiple chapter nodes")
			raise HTTPException(status_code=500, detail="Graph side error. Matched multiple chapter nodes")
		else:
			chapNode_uid = chapNode_query_res['chapter'][0]['uid']

		for content in chapter['contents']:
			if "verseNumber" in content:
				verse_num = content['verseNumber']
				verse_text = content['verseText']
				ref_string = book_code+" "+ str(chapter_num)+":"+str(verse_num)
				# to find/create verse node
				variables = {
					'$chapter': chapNode_uid,
					'$verse': str(verse_num)
				}
				try:
					verseNode_query_res = graph_conn.query_data(verseNode_query,variables)
				except Exception as e:
					logging.error('At fetching verse node')
					logging.error(e)
					raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
				if len(verseNode_query_res['verse']) == 0:
					verseNode = {
						'dgraph.type': "VerseNode",
						'verse' : verse_num,
						'refString': ref_string,
						'verseText': verse_text,
						'belongsTo' : {
							'uid': chapNode_uid 
						}
					}
					try:
						verseNode_uid = graph_conn.create_data(verseNode)
					except Exception as e:
						logging.error('At creating verse node')
						logging.error(e)
						raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
				elif len(verseNode_query_res['verse']) > 1:
						logging.error('At creating chapter node')
						logging.error("Matched multiple verse nodes")
						raise HTTPException(status_code=500, detail="Graph side error. Matched multiple verse nodes")
				else:
					verseNode_uid = verseNode_query_res['verse'][0]['uid']				
				clean_text = re.sub(punct_pattern, ' ',verse_text)
				words = re.split(r'\s+', clean_text)
				for i, word in enumerate(words):
					# to create a word node
					wordNode = {
							'dgraph.type': "WordNode",
							'word' : word,
							'belongsTo' : {
								'uid': verseNode_uid 
							},
							'position': i,
						}
					try:
						wordNode_uid = graph_conn.create_data(wordNode)
					except Exception as e:
						logging.error('At creating word node')
						logging.error(e)
						raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
					logging.info('wordNode_uid:%s'%wordNode_uid)
	return {"message":"usfm added"}

@app.post('/bibles', status_code = 200, tags=["WRITE", "Bible Contents"])
def add_bible(bible_name: str = Body("Hindi IRV4 bible"), language: str = Body("Hindi"), version: str = Body('IRV4'), tablename: str = Body('Hin_IRV4_BibleWord'), bookcode: BibleBook = Body(BibleBook.mat)):
	''' create a bible node, fetches contents from specified table in MySQL DB and adds to Graph.
	Currently the API is implemented to add only one book at a time. 
	This is due to the amount of time required.'''
	try:
		bibNode_query_res = graph_conn.query_data(bible_uid_query,{'$bib':bible_name})
	except Exception as e:
		logging.error('At fetching Bible uid')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))

	if len(bibNode_query_res['bible']) == 0:
		# create a bible nodename
		bib_node = { 
			'dgraph.type': "BibleNode",
			'bible': bible_name,
			'language' : language,
			'version': str(version)
				}
		try:
			bib_node_uid = graph_conn.create_data(bib_node)
			logging.info('bib_node_uid: %s' %bib_node_uid)
		except Exception as e:
			logging.error('At creating Bible node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	elif len(bibNode_query_res['bible']) > 1:
		logging.error('At fetching Bible uid')
		logging.error( 'matched multiple bible nodes')
		raise HTTPException(status_code=500, detail="Graph side error. "+' matched multiple bible nodes')
	else:
		bib_node_uid = bibNode_query_res['bible'][0]['uid']

	try:
		db = pymysql.connect(host="localhost",database=rel_db_name, user="root", password="password", charset='utf8mb4')
		cursor = db.cursor(pymysql.cursors.SSCursor)
	except Exception as e:
		logging.error('At connecting to MYSQL')
		logging.error( e)
		raise HTTPException(status_code=502, detail="MySQL side error. "+str(e))
	try:
		if bible_name == 'Grk UGNT4 bible':
			Morph_sequence = ['Role','Type','Mood','Tense','Voice','Person','Case','Gender','Number','Degree']
			cursor.execute("Select LID, Position, Word, Map.Book, Chapter, Verse,lookup.Book, Strongs, Morph, Pronunciation, TW, lookup.Code from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID = %s order by LID, Position",(book_num_map[bookcode.value]))
		else:
			cursor.execute("Select LID, Position, Word, Map.Book, Chapter, Verse,lookup.Book, lookup.Code from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID=%s order by LID, Position",(book_num_map[bookcode.value]))
	except Exception as e:
		logging.error('At fetching data from MYSQL')
		logging.error( e)
		raise HTTPException(status_code=502, detail="MySQL side error. "+str(e))
	count_for_test = 0
	chapNode=None
	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break
		# if count_for_test>100:
		# 	break
		count_for_test += 1


		LID = next_row[0]
		Position = next_row[1]
		Word = next_row[2]
		BookNum = next_row[3]
		Chapter = next_row[4]
		Verse = next_row[5]
		BookName = next_row[6]
		book_code = next_row[-1]
		if bible_name == "Grk UGNT4 bible":			
			Strongs = next_row[7]
			Morph = next_row[8].split(',')
			Pronunciation = next_row[9]	
			TW_fullString = next_row[10]
		logging.info('Book,Chapter,Verse:'+str(BookNum)+","+str(Chapter)+","+str(Verse))

		# to find/create book node
		variables = {
			'$bib': bib_node_uid,
			'$book': BookName
		}
		try:
			bookNode_query_res = graph_conn.query_data(bookNode_query,variables)
		except Exception as e:
			logging.error('At fetching book node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		if len(bookNode_query_res['book']) == 0:
			bookNode = {
				'dgraph.type': "BookNode",
				'book' : BookName,
				'bookNumber': BookNum,
				'belongsTo' : {
					'uid': bib_node_uid 
				}
			}
			try:
				bookNode_uid = graph_conn.create_data(bookNode)
			except Exception as e:
				logging.error('At creating book node')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		elif len(bookNode_query_res['book']) > 1:
			logging.error('At fetching book node')
			logging.error("Matched multiple book nodes")
			raise HTTPException(status_code=500, detail="Graph side error. Matched multiple book nodes")
		else:
			bookNode_uid = bookNode_query_res['book'][0]['uid']

		# to find/create chapter node
		variables = {
			'$book': bookNode_uid,
			'$chap': str(Chapter)
		}
		try:
			chapNode_query_res = graph_conn.query_data(chapNode_query,variables)
		except Exception as e:
			logging.error('At fetching chapter node')
			logging.error(e)
			raise HTTPException(status_code=500, detail="Graph side error. "+ str(e))

		if len(chapNode_query_res['chapter']) == 0:
			chapNode = {
				'dgraph.type': "ChapterNode",
				'chapter' : Chapter,
				'belongsTo' : {
					'uid': bookNode_uid 
				}
			}
			try:
				chapNode_uid = graph_conn.create_data(chapNode)
			except Exception as e:
				logging.error('At creating chapter node')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		elif len(chapNode_query_res['chapter']) > 1:
			logging.error('At fetching chapter node')
			logging.error("Matched multiple chapter nodes")
			raise HTTPException(status_code=500, detail="Graph side error. Matched multiple chapter nodes")
		else:
			chapNode_uid = chapNode_query_res['chapter'][0]['uid']

		# to find/create verse node
		variables = {
			'$chapter': chapNode_uid,
			'$verse': str(Verse)
		}
		try:
			verseNode_query_res = graph_conn.query_data(verseNode_query,variables)
		except Exception as e:
			logging.error('At fetching verse node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		if len(verseNode_query_res['verse']) == 0:
			verseNode = {
				'dgraph.type': "VerseNode",
				'verse' : Verse,
				'refString': book_code+" "+str(Chapter)+":"+str(Verse),
				'belongsTo' : {
					'uid': chapNode_uid 
				},
				'lid':LID
			}
			try:
				verseNode_uid = graph_conn.create_data(verseNode)
			except Exception as e:
				logging.error('At creating verse node')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		elif len(verseNode_query_res['verse']) > 1:
				logging.error('At creating chapter node')
				logging.error("Matched multiple verse nodes")
				raise HTTPException(status_code=500, detail="Graph side error. Matched multiple verse nodes")
		else:
			verseNode_uid = verseNode_query_res['verse'][0]['uid']

		# to create a word node
		wordNode = {
				'dgraph.type': "WordNode",
				'word' : Word,
				'belongsTo' : {
					'uid': verseNode_uid 
				},
				'position': Position,
			}
		if bible_name == 'Grk UGNT4 bible':
			wordNode['pronunciation'] = Pronunciation

			for key,value in zip(Morph_sequence,Morph):
				if(value!=''):
					wordNode[key] = value
			variables = {
				'$strongnum': str(Strongs)
			}
			try:
				strongNode_query_res = graph_conn.query_data(strongNode_query,variables)
			except Exception as e:
				logging.error('At fetching strong node')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
			logging.info('strongNode_query_res:',strongNode_query_res)
			if len(strongNode_query_res['strongs'])>0:
				strongNode_uid = strongNode_query_res['strongs'][0]['uid']
				wordNode['strongsLink'] = { 'uid': strongNode_uid }
			if TW_fullString != "-":
				Type, word = TW_fullString.split('/')[-2:]
				variables = {
					'$word' : word
				}
				try:
					twNode_query_res = graph_conn.query_data(twNode_query,variables)
				except Exception as e:
					logging.error('At fetching tw node')
					logging.error(e)
					raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
				if len(twNode_query_res['tw']) > 0:
					twNode_uid = twNode_query_res['tw'][0]['uid']
					wordNode['twLink'] = { 'uid': twNode_uid }
		try:
			wordNode_uid = graph_conn.create_data(wordNode)
		except Exception as e:
			logging.error('At creating word node')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		logging.info('wordNode_uid:%s'%wordNode_uid)

	cursor.close()
	db.close()
	text_tablename = tablename.replace('BibleWord','Text')
	if text_tablename == 'Grk_UGNT4_Text':
		text_tablename = 'Grk_UGNT_Text'
	add_verseTextToBible(bib_node_uid, text_tablename, bookcode.value)	
	return {'msg': "Added %s in %s" %(bookcode, bible_name)}

verseNode_withLID_query = '''
		query verse($bib: string, $lid: int){
		verse(func: uid($bib))
		@normalize {
				~belongsTo {
					~belongsTo{
						~belongsTo @filter(eq(lid,$lid)){
						  uid: uid
		}	}	}	}	}
	'''

def add_verseTextToBible(bib_node_uid,table_name, bookcode):
	global graph_conn
	try:
		db = pymysql.connect(host="localhost",database=rel_db_name, user="root", password="password", charset='utf8mb4')
		cursor = db.cursor(pymysql.cursors.SSCursor)
		###### to add text from the text tables in the mysql DB ###############
		cursor.execute("SELECT LID, main.Verse from "+table_name+" as main JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID=%s order by LID",(book_num_map[bookcode]))
	except Exception as e:
		logging.error('At fetching verse from mysql DB')
		logging.error(e)
		raise HTTPException(status_code=502, detail="MySQL side error. "+str(e))

	next_row = cursor.fetchone()
	logging.info("Adding text to the bible verse")
	while next_row:
		# print(next_row)
		LID = next_row[0]
		verse = next_row[1]
		variables = {
			'$bib': bib_node_uid,
			'$lid': str(LID)
		}
		verseNode_query_res = graph_conn.query_data(verseNode_withLID_query,variables)
		if len(verseNode_query_res['verse']) == 0:
			logging.warn('Couldn\'t find the verse with lid')
		elif len(verseNode_query_res['verse']) > 1:
			logging.error('At fetching verse node')
			logging.error('Matched multiple verse nodes')
			raise HTTPException(status_code=500, detail="Graph side error. Matched multiple verse nodes.")
		else:
			verseNode_uid = verseNode_query_res['verse'][0]['uid']
			verseText = {
				'uid': verseNode_uid,
				'verseText': verse 
			}
			try:
				graph_conn.create_data(verseText)
			except Exception as e:
				logging.error('At adding text to verse')
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
			logging.info('text added for:',LID )
		next_row = cursor.fetchone()
		# break
	cursor.close()
	db.close()
	return 

######################### Alignment ##############################
bible_word_query = '''
	query bib_word($bib:string, $book:int, $chapter:int, $verse:int, $pos:int){
	bib_word(func: uid($bib)) @normalize {
		~belongsTo @filter(eq(bookNumber,$book)){
			~belongsTo @filter(eq(chapter,$chapter)){
				~belongsTo @filter(eq(verse,$verse)){
					~belongsTo @filter(eq(position,$pos)){
						uid : uid
						
					}
				}
			}
		}
	}
	}
'''

bible_query = '''
	query bible($name: string){
	bible (func: has(bible)) @filter(eq(bible,$name)){
	uid
	}
	}
'''



@app.post('/alignment', status_code=201, tags=["WRITE", "Bible Contents"])
def add_alignment(source_bible: str = Body('Hin IRV4 bible'), alignment_table: str = Body('Hin_4_Grk_UGNT4_Alignment'), bookcode: BibleBook = Body('mat')):
	global graph_conn

	target_bible = 'Grk UGNT4 bible'

	try:
		db = pymysql.connect(host="localhost",database=rel_db_name, user="root", password="password", charset='utf8mb4')
		cursor = db.cursor(pymysql.cursors.SSCursor)
		cursor.execute("Select Book, Chapter, Verse, PositionSrc, PositionTrg, UserId, Stage, Type, UpdatedOn, LidSrc, LidTrg from "+alignment_table+" as a JOIN Bcv_LidMap as Map ON LidSrc=Map.ID where Map.Book = %s order by LidSrc, PositionSrc",(book_num_map[bookcode]))
	except Exception as e:
		logging.error('At fetching alignment')
		logging.error(e)
		raise HTTPException(status_code=502, detail="MySQL side error. "+str(e))

	alignment_name = source_bible.replace('bible','')+'-'+target_bible.replace('bible','')+'Alignment'

	try:
		variables = {
		'$name' : source_bible
		}
		src_bib_node_query_res = graph_conn.query_data(bible_query,variables)
		logging.info('src_bib_node_query_res:%s' %src_bib_node_query_res)
		src_bibNode_uid = src_bib_node_query_res['bible'][0]['uid']
		variables = {
		'$name' : target_bible
		}
		trg_bib_node_query_res = graph_conn.query_data(bible_query,variables)
		trg_bibNode_uid = trg_bib_node_query_res['bible'][0]['uid']
	except Exception as e:
		logging.error('At finding bible nodes')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))

	count_for_test = 0
	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break
		# if count_for_test >10:
		# 	break
		count_for_test += 1

		BookNum = str(next_row[0])
		Chapter = str(next_row[1])
		Verse = str(next_row[2])
		PositionSrc = str(next_row[3])
		PositionTrg = str(next_row[4])
		UserId = str(next_row[5])
		Stage = str(next_row[6])
		Type = str(next_row[7])
		UpdatedOn = next_row[8]
		LidSrc = str(next_row[9])
		LidTrg = str(next_row[10])
		logging.info('BCV:%s %s %s'%(BookNum,Chapter,Verse))

		if PositionTrg == '255' or PositionSrc == '255':
			continue

		if (LidSrc != LidTrg):
			logging.info("Across verse alignment cannot be handled by this python script.")
			logging.info("Found at:%s %s %s"%(BookNum,Chapter,Verse))
			raise HTTPException(status_code=503, detail="Across verse alignment cannot be handled. "+str(e))

		try:
			src_wordNode_uid = None
			variables = {
				'$bib' : src_bibNode_uid,
				'$book' : str(BookNum),
				'$chapter' : str(Chapter),
				'$verse' : str(Verse),
				'$pos' : str(PositionSrc)
			}
			src_wordNode_query_res = graph_conn.query_data(bible_word_query,variables)
			src_wordNode_uid = src_wordNode_query_res['bib_word'][0]['uid']

			trg_wordNode_uid = None

			variables2 = {
				'$bib' : trg_bibNode_uid,
				'$book' : str(BookNum),
				'$chapter' : str(Chapter),
				'$verse' : str(Verse),
				'$pos' : str(PositionTrg)
			}
			trg_wordNode_query_res = graph_conn.query_data(bible_word_query,variables2)
			trg_wordNode_uid = trg_wordNode_query_res['bib_word'][0]['uid']
		except Exception as e:
			logging.error('At finding word nodes')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
		logging.info('src_wordNode_uid:%s'%src_wordNode_uid)
		logging.info('trg_wordNode_uid:%s'%trg_wordNode_uid)

		set_alignment_mutation = { 'uid': src_wordNode_uid,
									'alignsTo': {
										'uid': trg_wordNode_uid
									}
								}
		try:
			res = graph_conn.create_data(set_alignment_mutation)
		except Exception as e:
			logging.error('At creating alignmnet link')
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	cursor.close()
	db.close()
	return {'msg': "Alignment added for %s and %s in %s"% (source_bible, target_bible, bookcode)}











##################### Bible Content retrival ######################
whole_chapter_query = '''
	query chapter($bib: string, $book: int, $chapter: int){
	chapter(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapter
		verses: ~belongsTo {
			verse: verse,
			verseText: verseText,
			words: ~belongsTo @normalize{
				word:word,
				position: position,
				twLink: twLink {
					translationWord: translationWord,
				},
				strongsLink {
					strongsNumber: StrongsNumber,
					englishWord: englishWord
				}
				alignsTo: alignsTo {
					twLink: twLink {
						translationWord: translationWord,
					}
					strongsLink {
						strongsNumber: StrongsNumber,
						englishWord: englishWord
					}
				}
			}
		}
		}
		}
	}
	}
'''

@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}', status_code=200, tags=["READ", "Bible Contents"])
def get_whole_chapter(bible_name: str, bookcode: BibleBook, chapter: int):
	''' fetches all verses of the chapter 
	including their strong number, tw and bible name connections
	'''
	result = {}
	try:
		variables = {'$bib': bible_name,
					'$book': str(book_num_map[bookcode]),
					'$chapter': str(chapter)}
		query_res = graph_conn.query_data(whole_chapter_query,variables)
		logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching chapter contents')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	try:
		result = query_res['chapter'][0]['~belongsTo'][0]['~belongsTo'][0]
		for j,ver in enumerate(result['verses']):
			for i,wrd in enumerate(ver['words']):
				if 'translationWord' in wrd:
					link = '%s/translationwords?translation_word=%s'%(base_URL, wrd['translationWord'])
					result['verses'][j]['words'][i]['translationWordLink'] = urllib.parse.quote(link, safe='/:?=')
				if 'strongsNumber' in wrd:
					link = '%s/strongs?strongs_number=%s'%(base_URL, wrd['strongsNumber'])
					result['verses'][j]['words'][i]['strongsLink'] = urllib.parse.quote(link, safe='/:?=')
	except Exception as e:
		logging.error('At parsing chapter contents')
		logging.error(e)
		raise HTTPException(status_code=404, detail="Requested content not Available. ")
	return result

one_verse_query = '''
	query verse($bib: string, $book: int, $chapter: int, $verse: int){
	verse(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapter
		~belongsTo @filter(eq(verse, $verse)){
			verse: verse,
			verseText: verseText,
			words: ~belongsTo @normalize{
				word:word,
				uid,
				position: position,
				twLink: twLink {
					translationWord: translationWord,
				},
				strongsLink {
					strongsNumber: StrongsNumber,
					englishWord: englishWord
				}
				alignsTo: alignsTo {
					twLink: twLink {
						translationWord: translationWord,
					}
					strongsLink {
						strongsNumber: StrongsNumber,
						englishWord: englishWord
					}
				}

			}
		}
		}
		}
	}
	}
'''


@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}', status_code=200, tags=["READ", "Bible Contents"])
def get_one_verse(bible_name: str, bookcode: BibleBook, chapter: int, verse: int):
	''' fetches all verses of the chapter 
	including their strong number, tw and bible name connections
	'''
	result = {}
	try:
		variables = {'$bib': bible_name,
					'$book': str(book_num_map[bookcode]),
					'$chapter': str(chapter),
					'$verse': str(verse)}
		query_res = graph_conn.query_data(one_verse_query,variables)
		logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching chapter contents')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	try:
		result = query_res['verse'][0]['~belongsTo'][0]['~belongsTo'][0]['~belongsTo'][0]
		for i,wrd in enumerate(result['words']):
			if 'translationWord' in wrd:
				link = '%s/translationwords?translation_word=%s'%(base_URL, wrd['translationWord'])
				result['words'][i]['translationWordLink'] = urllib.parse.quote(link, safe='/:?=')
			if 'strongsNumber' in wrd:
				link = '%s/strongs?strongs_number=%s'%(base_URL, wrd['strongsNumber'])
				result['words'][i]['strongsLink'] = urllib.parse.quote(link, safe='/:?=')
	except Exception as e:
		logging.error('At parsing verse contents')
		logging.error(e)
		raise HTTPException(status_code=404, detail="Requested content not Available. ")
	return result

word_query = '''
	query word($bib: string, $book: int, $chapter: int, $verse: int, $pos: int){
	word(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapter
		~belongsTo @filter(eq(verse, $verse)){
			verse: verse,
			verseText: verseText,
			words: ~belongsTo @filter(eq(position, $pos)) @normalize{
				word:word,
				position: position,
				twLink: twLink {
					translationWord: translationWord,
				},
				strongsLink {
					strongsNumber: StrongsNumber,
					englishWord: englishWord
				}
				alignsTo: alignsTo {
					twLink: twLink {
						translationWord: translationWord,
					}
					strongsLink {
						strongsNumber: StrongsNumber,
						englishWord: englishWord
					}
				}

			}
		}
		}
		}
	}
	}
'''
@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}/words/{position}', status_code=200, tags=["READ", "Bible Contents"])
def get_verse_word(bible_name: str, bookcode: BibleBook, chapter: int, verse: int, position: int):
	''' fetches all verses of the chapter 
	including their strong number, tw and bible name connections
	'''
	result = {}
	try:
		variables = {'$bib': bible_name,
					'$book': str(book_num_map[bookcode]),
					'$chapter': str(chapter),
					'$verse': str(verse),
					'$pos': str(position)}
		query_res = graph_conn.query_data(word_query,variables)
		logging.info('query_res: %s' % query_res)
	except Exception as e:
		logging.error('At fetching chapter contents')
		logging.error(e)
		raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	try:
		result = query_res['word'][0]['~belongsTo'][0]['~belongsTo'][0]['~belongsTo'][0]
		for i,wrd in enumerate(result['words']):
			if 'translationWord' in wrd:
				link = '%s/translationwords?translation_word=%s'%(base_URL, wrd['translationWord'])
				result['words'][i]['translationWordLink'] = urllib.parse.quote(link, safe='/:?=')
			if 'strongsNumber' in wrd:
				link = '%s/strongs?strongs_number=%s'%(base_URL, wrd['strongsNumber'])
				result['words'][i]['strongsLink'] = urllib.parse.quote(link, safe='/:?=')
	except Exception as e:
		logging.error('At parsing verse contents')
		logging.error(e)
		raise HTTPException(status_code=404, detail="Requested content not Available. ")
	return result



	############### Bible Names ##################

dict_node_query  = """
				query dict($dict: string){
				  dict(func: eq(dictionary, $dict)){
					uid
				} }"""

name_X_uid_query = """
			query name($xuid: string){
			name(func: eq(externalUid, $xuid)){
				uid,
				name
			} }
"""

all_names_query = """
			query names($skip: int, $limit: int){
			names(func: has(externalUid), offset: $skip, first: $limit) {
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						otherExternalUid: externalUid
					}
			} }
"""

one_name_xuid_query = """
			query names($skip: int, $limit: int, $xuid: string){
			names(func: eq(externalUid, $xuid), offset: $skip, first: $limit){
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						otherExternalUid: externalUid
					}
			} } 
"""

name_match_query = """
			query names($skip: int, $limit: int, $name: string){
			names(func: eq(name, $name), offset: $skip, first: $limit) {
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						otherExternalUid: externalUid
					}
			} } 
"""

family_tree_query = '''
	query relations($xuid: string){
	relations(func: eq(externalUid,$xuid)){
		name,
		externalUid,
		father{
			name,
			externalUid,
			sibling: ~father{
				name,
				externalUid	} },
		mother{
			name,
			externalUid,
			sibling: ~mother{
				name,
				externalUid	} },
		spouse{
			name,
			externalUid	},
		children1:~father{
			name,
			externalUid },
		children2:~mother{
			name,
			externalUid },
		sameAs{
			name,
			externalUid,
			father{
				name,
				externalUid,
				sibling: ~father{
					name,
					externalUid	} },
			mother{
				name,
				externalUid,
				sibling: ~mother{
					name,
					externalUid	} },
			spouse{
				name,
				externalUid	},
			children1:~father{
				name,
				externalUid },
			children2:~mother{
				name,
				externalUid } }
	} }
'''

names_link_query = '''
	query occurences($xuid: string, $skip:int, $limit:int){
	occurences(func: eq(externalUid, $xuid)){
	~nameLink(offset: $skip, first: $limit) @normalize{
		word: word,
		belongsTo{
			verse:verse,
			verseText: verseText,
			belongsTo{
				chapter:chapter,
				belongsTo{
					book: book,
					bookNumber: bookNumber}	} } }
	sameAs{
		~nameLink(offset: $skip, first: $limit) @normalize{
			word: word,
			belongsTo{
				verse:verse,
				verseText: verseText,
				belongsTo{
					chapter:chapter,
					belongsTo{
						book: book,
						bookNumber: bookNumber}	} } }
	}
	}	}
'''

@app.post("/names", status_code=201, tags=["WRITE", "Bible Names"])
def add_names():
	'''creates a Bible names dictionary.
	* Pass I: Collect names from factgrid, ubs and wiki files and add to dictionary.
	* Pass II: Connect the names to each other based on known relations
	* Pass III: Connects names to each other using "sameAs" relation 
	* Pass IV: Connects names to bible Words in English ULB bible
	 '''
	nodename = 'Bible Names'

	variables = {"$dict": nodename}

	dict_node_query_result = graph_conn.query_data(dict_node_query, variables)
	if len(dict_node_query_result['dict']) == 0:
		# create a dictionary nodename
		dict_node = { 
				'dgraph.type': "DictionaryNode",
				'dictionary': nodename
				}
		try:
			dict_node_uid = graph_conn.create_data(dict_node)
		except Exception as e:
			logging.error("At dict node creation")
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+str(e))
	elif len(dict_node_query_result['dict']) == 1 :
		dict_node_uid = dict_node_query_result['dict'][0]['uid']
	else:
		logging.error("At dict node fetch")
		logging.error("More than one node matched")
		raise HTTPException(status_code=502, detail="Graph side error. More than one node matched")
	logging.info('dict_node_uid: %s' %dict_node_uid)

	factgrid_file = open('Resources/BibleNames/factgrid_person_query.json','r').read()
	factgrid_names = json.loads(factgrid_file)
	wiki_file = open('Resources/BibleNames/wiki_person_query.json','r').read()
	wiki_names = json.loads(wiki_file)
	ubs_names = get_nt_ot_names_from_ubs()

	# logging.info("factgrid_names: [%s,...]"%factgrid_names[0])
	# logging.info("ubs_names: [%s,...]"%ubs_names[0])
	# logging.info("wiki_names: [%s,...]"%wiki_names[0])

	###Pass I #####
	logging.info("Pass I: Adding names to dictionary")

	for name in factgrid_names:
		external_uid = name['Person']
		label = name['PersonLabel']
		desc = ""
		if "," in label:
			label1, label2 = label.split(",", 1)
			label = label1
			desc = label2 + ". "

		name_node = {
		 "dgraph.type": "NameNode",
		 "externalUid": external_uid,
		 "name": label,
		 "belongsTo": {
			"uid": dict_node_uid
		 }
		}
		if "PersonDescription" in name:
			desc += name['PersonDescription']
		if desc != "":
			name_node['description'] = desc.strip()

		if "GenderLabel" in name:
			name_node['gender'] = name['GenderLabel']

		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query, {"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) > 0:
				logging.warn("Skipping name node creation")
				logging.warn("Name already exists\nNew name node: %s\nExisting node: %s"%(name_node, name_X_uid_query_res['name'][0]))
			else:
				name_node_uid = graph_conn.create_data(name_node)
				logging.info('name: %s, name_node_uid: %s' %(label, name_node_uid))
		except Exception as e:
			logging.error("At name node creation")
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

	for name in ubs_names:
		external_uid = "ubs_name/"+name['id']
		label = name['name']

		name_node = {
		 "externalUid": external_uid,
		 "name": label,
		 "belongsTo": {
			"uid": dict_node_uid
		 }
		}
		if "description" in name:
			name_node['description'] = name['description'].strip()


		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query, {"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) > 0:
				logging.warn("Skipping name node creation")
				logging.warn("Name already exists\nNew name node: %s\nExisting node: %s"%(name_node, name_X_uid_query_res['name'][0]))
			else:
				name_node_uid = graph_conn.create_data(name_node)
				logging.info('name: %s, name_node_uid: %s' %(label, name_node_uid))
		except Exception as e:
			logging.error("At name node creation")
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

	for name in wiki_names:
		external_uid = name['item']
		label = name['itemLabel']

		name_node = {
		 "externalUid": external_uid,
		 "name": label,
		 "belongsTo": {
			"uid": dict_node_uid
		 }
		}
		if "itemDescription" in name:
			name_node['description'] = name['itemDescription'].strip()
		if "gender" in name:
			name_node['gender'] = name['gender'].strip()
		if "birthdate" in name:
			name_node['birthdate'] = name['birthdate'].strip()
		if "deathdate" in name:
			name_node['deathdate'] = name['deathdate'].strip()
		if "birthPlaceLabel" in name:
			name_node['birthPlace'] = name['birthPlaceLabel'].strip()
		if "deathPlaceLabel" in name:
			name_node['deathPlace'] = name['deathPlaceLabel'].strip()


		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query, {"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) > 0:
				logging.warn("Skipping name node creation")
				logging.warn("Name already exists\nNew name node: %s\nExisting node: %s"%(name_node, name_X_uid_query_res['name'][0]))
			else:
				name_node_uid = graph_conn.create_data(name_node)
				logging.info('name: %s, name_node_uid: %s' %(label, name_node_uid))
		except Exception as e:
			logging.error("At name node creation")
			logging.error(e)
			raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

	####Pass II ####
	logging.info("Pass II: connecting names via known relations")

	for name in factgrid_names:
		external_uid = name['Person']
		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) == 1:
				name_node_uid = name_X_uid_query_res['name'][0]['uid']
			else:
				logging.error("At name node fetching")
				logging.error("Name node not found: %s"%external_uid)
				raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
		except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		name_node = {'uid': name_node_uid}

		if 'Father' in name:
			father_external_uid = name['Father']
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": father_external_uid})
				if len(name_X_uid_query_res['name']) == 1:
					father_node_uid = name_X_uid_query_res['name'][0]['uid']
					name_node['father'] = {'uid': father_node_uid}
				else:
					logging.warn("At name node fetching")
					logging.warn("Name node not found: %s"%father_external_uid)
					# raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
			except Exception as e:
					logging.error("At name node fetching")
					logging.error(e)
					raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		if 'Mother' in name:
			mother_external_uid = name['Mother']
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": mother_external_uid})
				if len(name_X_uid_query_res['name']) == 1:
					mother_node_uid = name_X_uid_query_res['name'][0]['uid']
					name_node['mother'] = {'uid': mother_node_uid}	
				else:
					logging.warn("At name node fetching")
					logging.warn("Name node not found: %s"%mother_external_uid)
					# raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
			except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		if "father" in name_node or "mother" in name_node:
			try:
				graph_conn.create_data(name_node)
			except Exception as e:
				logging.error("At name connecting")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

	for name in wiki_names:
		external_uid = name['item']
		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) == 1:
				name_node_uid = name_X_uid_query_res['name'][0]['uid']
			else:
				logging.error("At name node fetching")
				logging.error("Name node not found: %s"%external_uid)
				raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
		except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		name_node = {'uid': name_node_uid}

		if 'father' in name:
			father_external_uid = name['father']
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": father_external_uid})
				if len(name_X_uid_query_res['name']) == 1:
					father_node_uid = name_X_uid_query_res['name'][0]['uid']
					name_node['father'] = {'uid': father_node_uid}
				else:
					logging.warn("At name node fetching")
					logging.warn("Name node not found: %s"%father_external_uid)
					# raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
			except Exception as e:
					logging.error("At name node fetching")
					logging.error(e)
					raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		if 'mother' in name:
			mother_external_uid = name['mother']
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": mother_external_uid})
				if len(name_X_uid_query_res['name']) == 1:
					mother_node_uid = name_X_uid_query_res['name'][0]['uid']
					name_node['mother'] = {'uid': mother_node_uid}	
				else:
					logging.warn("At name node fetching")
					logging.warn("Name node not found: %s"%mother_external_uid)
					# raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
			except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		if 'spouse' in name:
			spouse_external_uid = name['spouse']
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": spouse_external_uid})
				if len(name_X_uid_query_res['name']) == 1:
					spouse_node_uid = name_X_uid_query_res['name'][0]['uid']
					name_node['spouse'] = {'uid': spouse_node_uid}	
				else:
					logging.warn("At name node fetching")
					logging.warn("Name node not found: %s"%spouse_external_uid)
					# raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
			except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))


		if "father" in name_node or "mother" in name_node or "spouse" in name_node:
			try:
				graph_conn.create_data(name_node)
			except Exception as e:
				logging.error("At name connecting")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

	##### Pass III ######

	logging.info("Pass III: Connecting names via sameAs relations based on manually connected data")

	connection_file = open('Resources/BibleNames/connected_ne.json').read()
	connections = json.loads(connection_file)

	factgrid_id_pattern = "https://database.factgrid.de/entity/"
	wiki_id_pattern = 'http://www.wikidata.org/entity/'
	ubs_id_pattern = 'ubs_name/'

	for conn in connections:
		if conn['linked'] != "manual":
			continue
		ids = []
		if 'factgrid' in conn:
			f_ids = set(conn['factgrid'])
			ids += [factgrid_id_pattern+id for id in f_ids]
		if 'ubs' in conn:
			u_ids = set(conn['ubs'])
			ids += [ubs_id_pattern+id for id in u_ids]
		if 'wiki' in conn:
			w_ids = set(conn['wiki'])
			ids += [wiki_id_pattern+id for id in w_ids]

		for a, b in itertools.product(ids,ids):
			if a == b:
				continue
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query, {'$xuid': a.strip()})
				if (len(name_X_uid_query_res['name']) == 1):
					a_node_uid = name_X_uid_query_res['name'][0]['uid']
				else:
					logging.warn("At fetching name nodes")
					logging.warn("cannot find one node for a_node: %s"%a)
					logging.warn("got query result: %s"%name_X_uid_query_res)
					continue
			except Exception as e:
				logging.error("At fetching name nodes")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))
			try:
				name_X_uid_query_res = graph_conn.query_data(name_X_uid_query, {'$xuid': b.strip()})
				if (len(name_X_uid_query_res['name']) == 1):
					b_node_uid = name_X_uid_query_res['name'][0]['uid']
				else:
					logging.warn("At fetching name nodes")
					logging.warn("cannot find one node for b_node: %s"%b)
					logging.warn("got query result: %s"%name_X_uid_query_res)
					continue
			except Exception as e:
				logging.error("At fetching name nodes")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

			sameAs_connection = {
				"uid": a_node_uid,
				"sameAs": { 
					"uid": b_node_uid
				}
			}

			try:
				graph_conn.create_data(sameAs_connection)
			except Exception as e:
				logging.error("At name connecting via sameAs")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))
	
	##### Pass IV ######

	logging.info("Pass IV: Connecting names to Bible words")

	for name in factgrid_names:
		external_uid = name['Person']
		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) == 1:
				name_node_uid = name_X_uid_query_res['name'][0]['uid']
				search_names = [name_X_uid_query_res['name'][0]['name']]
				if "sameAs" in name_X_uid_query_res['name'][0]:
					search_names += [same['name'] for same in name_X_uid_query_res['name'][0]['sameAs']]
			else:
				logging.error("At name node fetching")
				logging.error("Name node not found: %s"%external_uid)
				raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
		except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		ref_pattern = re.compile('(\d* ?\w+) (\d+):?(\d+)?')
		if "notedLabel" in name:
			ref = name['notedLabel']
			inconsistant_values = ["Superscript of Psalm 7", "The General Epistle of Jude", "New Testament", "Pilate stone"]
			try:
				ref_obj = re.match(ref_pattern, ref)
				book = ref_obj.group(1)
				chapter= ref_obj.group(2)
				verse = ref_obj.group(3)
			except Exception as e:
				if ref in inconsistant_values:
					continue
				logging.error("At Parsing Reference:%s"%ref)
				logging.error(e)
				raise HTTPException(status_code=502, detail="Regex error. "+ str(e))
			if verse == None:
				verse = 0
			variables = {
				'$bib': "Eng ULB bible",
				'$book' : str(book_num_map[book]),
				'$chapter': str(chapter),
				'$verse': str(verse)
			}
			try:
				one_verse_query_res = graph_conn.query_data(one_verse_query, variables)
			except Exception as e:
				logging.error("At fetching words in verse:%s"%variables)
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

			found_verse = False
			found_word = False
			search_names_cleaned = [name.split(" ", 1)[0].replace(",","").lower() for name in search_names]
			search_names = set(search_names_cleaned)
			if len(one_verse_query_res['verse'][0]) > 0 :
				if "~belongsTo" in one_verse_query_res['verse'][0] and len(one_verse_query_res['verse'][0]['~belongsTo']) > 0:
					if "~belongsTo" in one_verse_query_res['verse'][0]["~belongsTo"][0] and len(one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo']) > 0:
						if "~belongsTo" in one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo'][0] and len(one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo'][0]["~belongsTo"]) > 0:
							words = one_verse_query_res['verse'][0]['~belongsTo'][0]['~belongsTo'][0]['~belongsTo'][0]['words']
							for wrd in words:
								if re.sub(non_letter_pattern, "", wrd['word'].lower().replace("'s","")) in search_names:
									name_connection = {
										"uid": wrd['uid'],
										'nameLink' : { "uid": name_node_uid}
									}
									try:
										logging.info("linking %s to %s"%(name["PersonLabel"], wrd['word']))
										graph_conn.create_data(name_connection)
										pass
									except Exception as e:
										logging.error("At creating nameLink")
										logging.error(e)
										raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))
									found_word = True
							found_verse = True
			if not found_verse:
				logging.warn("verse %s not found"%variables)
				# pass
			elif not found_word:
				text = ' '.join([wrd['word'] for wrd in words])
				logging.warn("Matching word not found in the searched verse\n %s >>> %s"%(name['PersonLabel'], text))

	verse_not_found_count = 0
	for name in ubs_names:
		external_uid = "ubs_name/"+name['id']
		try:
			name_X_uid_query_res = graph_conn.query_data(name_X_uid_query,{"$xuid": external_uid})
			if len(name_X_uid_query_res['name']) == 1:
				name_node_uid = name_X_uid_query_res['name'][0]['uid']
				search_names = [name_X_uid_query_res['name'][0]['name']]
				if "sameAs" in name_X_uid_query_res['name'][0]:
					search_names += [same['name'] for same in name_X_uid_query_res['name'][0]['sameAs']]
			else:
				logging.error("At name node fetching")
				logging.error("Name node not found: %s"%external_uid)
				raise HTTPException(status_code=502, detail="Graph side error. Name node not found.")
		except Exception as e:
				logging.error("At name node fetching")
				logging.error(e)
				raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

		search_names_cleaned = [name.split(" ", 1)[0].replace(";","").lower() for name in search_names]
		search_names = set(search_names_cleaned)
		if "occurances" in name:
			refs = name['occurances']
			for ref in refs:
				book, chapter, verse, pos = ref	
				variables = {
					'$bib': "Eng ULB bible",
					'$book' : str(book),
					'$chapter': str(chapter),
					'$verse': str(verse)
				}
				try:
					one_verse_query_res = graph_conn.query_data(one_verse_query, variables)
				except Exception as e:
					logging.error("At fetching words in verse:%s"%variables)
					logging.error(e)
					raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))

				found_verse = False
				found_word = False
				if len(one_verse_query_res['verse'][0]) > 0 :
					if "~belongsTo" in one_verse_query_res['verse'][0] and len(one_verse_query_res['verse'][0]['~belongsTo']) > 0:
						if "~belongsTo" in one_verse_query_res['verse'][0]["~belongsTo"][0] and len(one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo']) > 0:
							if "~belongsTo" in one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo'][0] and len(one_verse_query_res['verse'][0]["~belongsTo"][0]['~belongsTo'][0]["~belongsTo"]) > 0:
								words = one_verse_query_res['verse'][0]['~belongsTo'][0]['~belongsTo'][0]['~belongsTo'][0]['words']
								for wrd in words:
									if re.sub(non_letter_pattern, "", wrd['word'].lower().replace("'s","")) in search_names:
										name_connection = {
											"uid": wrd['uid'],
											'nameLink' : { "uid": name_node_uid}
										}
										try:
											logging.info("linking %s to %s"%(name["name"], wrd['word']))
											graph_conn.create_data(name_connection)
											pass
										except Exception as e:
											logging.error("At creating nameLink")
											logging.error(e)
											raise HTTPException(status_code=502, detail="Graph side error. "+ str(e))
										found_word = True
								found_verse = True
				if not found_verse:
					logging.warn("verse %s not found"%variables)
					verse_not_found_count += 1
					# pass
				elif not found_word:
					text = ' '.join([wrd['word'] for wrd in words])
					logging.warn("Matching word not found in the searched verse\n %s >>> %s"%(name['name'], text))

	return {'msg': "Added names"}


@app.get("/names", status_code=200, tags=["READ","Bible Names"])
def get_names(name: str = None, externalUid: str = None, occurences: bool = False, skip:int = 0, limit: int = 10):
	variables = {
		"$skip": str(skip),
		"$limit": str(limit)
		}
	result = []
	try:
		if not name and not externalUid:
			names_query_res = graph_conn.query_data(all_names_query, variables)
		elif externalUid:
			variables['$xuid'] = externalUid
			names_query_res = graph_conn.query_data(one_name_xuid_query, variables)
		elif name:
			variables['$name'] = name
			names_query_res = graph_conn.query_data(name_match_query, variables)
	except Exception as e:
		logging.error('At fetching names')
		logging.error(e)
		raise HTTPException(status_code=503, detail="Graph side error. "+str(e))

	if len(names_query_res['names']) == 0:
		logging.error('At fetching names')
		logging.error("Requested content not Available. ")
		raise HTTPException(status_code=404, detail="Requested content not Available. ")
	result = names_query_res['names']

	for i,person in enumerate(result):
		result[i]['link'] = '%s/names?externalUid=%s;occurences=True'%(base_URL,urllib.parse.quote(person['externalUid']))
		result[i]['relations'] = '%s/names/relations?externalUid=%s'%(base_URL, urllib.parse.quote(person['externalUid']))
		if "sameAs" in person:
			for j,otherName in enumerate(person['sameAs']):
				result[i]['sameAs'][j]['link'] = '%s/names?externalUid=%s;occurences=True'%(base_URL, urllib.parse.quote(otherName['otherExternalUid']))
	if occurences:
		for i, person in enumerate(result):
			result[i]['occurences'] = []
			try:
				occurences_query_res = graph_conn.query_data(names_link_query,{'$xuid': person['externalUid'], "$skip": str(skip), "$limit": str(limit)})
			except Exception as e:
				logging.error('At fetching names occurences of %s'%person['name'])
				logging.error(e)
				raise HTTPException(status_code=503, detail="Graph side error. "+str(e))
			if len(occurences_query_res['occurences']) == 0:
				logging.warn('At fetching names occurences of %s'%person['name'])
				logging.warn("Requested contents not available")
			else:
				if '~nameLink' in occurences_query_res['occurences'][0]:
					result[i]['occurences'] = occurences_query_res['occurences'][0]['~nameLink']
				if 'sameAs' in occurences_query_res['occurences'][0]:
					for otherName_occurences in occurences_query_res['occurences'][0]['sameAs']:
						result[i]['occurences'] += otherName_occurences['~nameLink']

	return result


@app.get("/names/relations", status_code=200, tags=["READ","Bible Names"])
def get_person_relations(externalUid: str):
	result = {}
	try:
		relations_query_result = graph_conn.query_data(family_tree_query,{'$xuid': externalUid})
	except Exception as e:
		logging.error('At fetching family relations of %s'%extrenalUid)
		logging.error(e)
		raise HTTPException(status_code=503, detail="Graph side error. "+str(e))
	if len(relations_query_result['relations']) == 0:
		logging.error('At fetching family relations of %s'%person['name'])
		logging.error("Requested contents not available")
		raise HTTPException(status_code=404, detail="Requested content not available")

	result['person'] = {"name": relations_query_result['relations'][0]['name'],
						"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['externalUid']))}
	result['siblings'] = []
	if "father" in relations_query_result['relations'][0]:
		result['father'] = {"name": relations_query_result['relations'][0]['father'][0]['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['father'][0]['externalUid'])) 
							}
		if 'sibling' in relations_query_result['relations'][0]['father'][0]:
			for sibling in relations_query_result['relations'][0]['father'][0]['sibling']:
				if sibling['externalUid'] != externalUid:
					result['siblings'].append({"name": sibling['name'],
												"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
												})
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'father' in otherName:
				if 'father' not in result:
					result['father'] = {"name": otherName['father'][0]['name'],
										"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(otherName['father'][0]['externalUid']))}
				if 'sibling' in otherName['father'][0]:
					for sibling in otherName['father'][0]['sibling']:
						result['siblings'].append({"name": sibling['name'],
													"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
													})
				break
	if "mother" in relations_query_result['relations'][0]:
		result['mother'] = {"name": relations_query_result['relations'][0]['mother'][0]['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['mother'][0]['externalUid'])) 
							}
		if 'sibling' in relations_query_result['relations'][0]['mother'][0]:
			for sibling in relations_query_result['relations'][0]['mother'][0]['sibling']:
				sib = {"name": sibling['name'],
						"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
						}
				if sibling['externalUid'] != externalUid and sib not in result['siblings']:
					result['siblings'].append()
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'mother' in otherName:
				if 'mother' not in result:
					result['mother'] = {"name": otherName['mother'][0]['name'],
										"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(otherName['mother'][0]['externalUid']))}
				if 'sibling' in otherName['mother'][0]:
					for sibling in otherName['mother'][0]['sibling']:
						sib = {"name": sibling['name'],
								"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
								}
						if sibling['externalUid'] != externalUid and sib not in result['siblings']:
							result['siblings'].append({"name": sibling['name'],
														"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
														})
				break
	result['spouses'] = []
	if "spouse" in relations_query_result['relations'][0]:
		for spouse in relations_query_result['relations'][0]['spouse']:
			sps = {"name": spouse['name'],
				"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(spouse['externalUid']))}
			if sps not in result['spouses']:
				result['spouses'].append(sps)
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if "spouse" in otherName:
				for spouse in otherName['spouse']:
					sps = {"name": spouse['name'],
						"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(spouse['externalUid']))}
					if sps not in result['spouses']:
						result['spouses'].append(sps)
						
	result['children'] = []
	if "children1" in relations_query_result['relations'][0]:
		for child in relations_query_result['relations'][0]['children1']:
			ch = {"name": child['name'],
					"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
			if ch not in result['children']:
				result['children'].append(ch)	
	elif "children2" in relations_query_result['relations'][0]:
		for child in relations_query_result['relations'][0]['children2']:
			ch = {"name": child['name'],
					"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
			if ch not in result['children']:
				result['children'].append(ch)	
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'children1' in otherName:
				for child in otherName['children1']:
					ch = {"name": child['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
					if ch not in result['children']:
						result['children'].append(ch)	
			elif 'children2' in otherName:
				for child in otherName['children2']:
					ch = {"name": child['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
					if ch not in result['children']:
						result['children'].append(ch)	
	if len(result['spouses']) == 0:
		del result['spouses']
	if len(result['siblings']) == 0:
		del result['siblings']
	if len(result['children']) == 0:
		del result['children']

	fig = plt.figure(figsize=(12,12))
	ax = plt.subplot(111)
	ax.set_title('Graph - Shapes', fontsize=10)
	G = nx.DiGraph()

	G.add_node(result['person']['name'], level=3)
	colour_list = ["blue"]

	if 'father' in result:
		G.add_node(result['father']['name'], level=4)
		G.add_edge(result['person']['name'], result['father']['name'], label='father')
		colour_list.append("green")

	if 'mother' in result:
		G.add_node(result['mother']['name'], level=4 )
		G.add_edge(result['person']['name'], result['mother']['name'], label='mother')
		colour_list.append("green")

	if 'siblings' in result:
		for sib in result['siblings']:
			G.add_node(sib['name'], level=2)
			G.add_edge(result['person']['name'], sib['name'], label='sibling')
			colour_list.append("purple")

	if 'spouses' in result:
		for sps in result['spouses']:
			G.add_node(sps['name'], level=2)
			G.add_edge(result['person']['name'], sps['name'], label='spouse')
			colour_list.append("pink")

	if 'children' in result:
		for child in result['children']:
			G.add_node(child['name'], level=1)
			G.add_edge(result['person']['name'], child['name'], label='child')
			colour_list.append("orange")

	pos = nx.multipartite_layout(G, subset_key='level', align='horizontal')
	nx.draw(G, pos, node_size=5000, node_color=colour_list, font_size=20, font_weight='bold')
	nx.draw_networkx_labels(G, pos)
	nx.draw_networkx_edge_labels(G, pos)
	plt.tight_layout()
	plt.savefig("static/Family-tree.png")

	rels_html = ""
	for key in result:
		if key in ['person', 'mother', 'father']:
			rels_html += '%s:<a href="%s">%s</a><br>'%(key.upper(), result[key]['link'], result[key]['name'])
		else:
			items = ", ".join(['<a href="%s">%s</a>'%(it['link'], it['name']) for it in result[key]])
			# items = ['<a href="%s">%s</a>'%(it['link'], it['name']) for it in result[key]]
			rels_html += '%s:%s <br>'%(key.upper(), str(items))

	html_file = open("Family-tree.html", "w")
	html_content = '''
	<html>
	<body>
	<div style="float:left" width="25%%">
	%s
	</div>
	<div style="float:left" width="75%%">
	<img src="/static/Family-tree.png" height="750px">
	</div>
	</body>
	</html>
	'''%rels_html

	html_file.write(html_content)
	html_file.close()
	return FileResponse("Family-tree.html")



#################### VERSIFICATION #########################

@app.post("/versification/original", status_code=201, tags=["WRITE", "Versification"])
def add_versification_orig(versification: dict):
	'''Create the entire versification structure with the original versification format'''
	nodename = "original"
	root_node = {
		'dgraph.tyep': "VersificationNode",
		"versification": nodename}
	root_node_uid = graph_conn.create_data(root_node)
	for book in versification['maxVerses']:
		book_node = {
			"dgraphType": "VersificationBookNode",
			"bookcode": book, 
			"belongsTo":{"uid":root_node_uid}}
		book_node_uid = graph_conn.create_data(book_node)
		for i,chap_max in enumerate(versification['maxVerses'][book]):
			chapter_node = {
				"dgraph.type": "VersificationChapterNode",
				"chapter":i+1, 
				"belongsTo":{"uid":book_node_uid}}
			chapter_node_uid = graph_conn.create_data(chapter_node)
			for verse in range(int(chap_max)):
				verse_node = {
					"dgraph.tyep": "VersificationVerseNode",
					"verseNumber":verse+1, 
					"belongsTo":{"uid":chapter_node_uid}}
				verse_node_uid = graph_conn.create_data(verse_node)


versi_verse_node_query = '''query verse($book: string, $chapter:int, $verse:int){
	verse(func: eq(versification, "original")) @normalize{
		versification,
		~belongsTo @filter(eq(bookcode, $book)){
			bookcode,
			~belongsTo @filter(eq(chapter, $chapter)){
				chapter,
				~belongsTo @filter(eq(verseNumber, $verse)){
					uid:uid
				}
			}
		}
	}	
}
'''

bible_verse_node_query = '''query verse($bib_uid: string, $book: int, $chapter:int, $verse:int){
	verse(func: uid($bib_uid)) @normalize{
		bible,
		~belongsTo @filter(eq(bookNumber, $book)){
			book,
			~belongsTo @filter(eq(chapter, $chapter)){
				chapter,
				~belongsTo @filter(eq(verse, $verse)){
					uid:uid
				}
			}
		}
	}	
}

'''

# partial verses are not matched by these patterns as the code processing mappedVerses also cannot handle them
# single_verse_pattern = re.compile(r'([\w\d]\w\w) (\d+):(\d+\w*)$')
verse_range_pattern = re.compile(r'([\w\d]\w\w) (\d+):(\d+\w*)\-?(\d+\w*)?$')

def versi_map_nodes(var1, var2):
	if re.match(r'[\w\d]\w\w', var1['$book']):
		var1['$book'] = str(book_num_map[var1['$book']])
	source_node = graph_conn.query_data(bible_verse_node_query, var1)
	if len(source_node['verse']) < 1:
		raise Exception("Cant find node:%s", var1)
	versi_node = graph_conn.query_data(versi_verse_node_query, var2)
	if len(versi_node['verse']) < 1:
		raise Exception("Cant find versification node: %s", var2)
	mapping = {"uid": source_node['verse'][0]['uid'],
				"verseMapping": {"uid":versi_node['verse'][-1]['uid']}}
	print(mapping)
	graph_conn.create_data(mapping)
	return True
	
def to_int(num):
	match_obj = re.match(r'\d+', num)
	return int(match_obj.group(0))

def process_ref_string(ref_str):
	# print(ref_str,"-->")
	verse_list = []
	match_obj = re.match(verse_range_pattern, ref_str)
	if match_obj:
		book = match_obj.group(1)
		chapter = match_obj.group(2)
		verse_s = match_obj.group(3)
		verse_e = match_obj.group(4)
		if verse_e is None or verse_e == "":
			verse_list = [{"$book":book, "$chapter":chapter, "$verse":str(to_int(verse_s))}]
		else:
			for v in range(to_int(verse_s), to_int(verse_e)+1):
				var = {"$book":book, "$chapter":chapter, "$verse":str(v)}
				verse_list.append(var)
	else:
		raise Exception("Reference, %s, cannot be parsed"% ref_str)
	# print(verse_list)
	return verse_list

@app.post("/versification/map", status_code=201, tags=["WRITE", "Versification"])
def add_versification_map(versification:dict, bible_name:str):
	'''Add maps from verses of selected bible to the original versification structure as per the map'''
	connect_Graph()
	bib_res = graph_conn.query_data(bible_uid_query, {"$bib":bible_name})
	if len(bib_res['bible']) < 1:
		raise HTTPException("Bible not found:%s", bible_name)
	bib_uid = bib_res['bible'][0]['uid']
	for source_verse in versification['verseMappings']:
		versi_verse = versification['verseMappings'][source_verse]
		src_vars = process_ref_string(source_verse)
		versi_vars = process_ref_string(versi_verse)
		for item in src_vars:
			item["$bib_uid"] = str(bib_uid)
		# if two refs have same number of verses, maps one-to-one
		# if different number of verses, then all extra verses in the longer range is mapped to the last verse of shorter one
		i = 0
		for var1 in src_vars:
			var2 = versi_vars[i]
			if i < len(versi_vars)-1:
				i = i+1
			versi_map_nodes(var1, var2)
		var1 = src_vars[-1]
		while i < len(versi_vars)-1:
			var2 = versi_vars[i]
			versi_map_nodes(var1, var2)
			i += 1

	for verse in versification['excludedVerses']:
		verse_vars = process_ref_string(verse)
		for var in verse_vars:
			versi_node = graph_conn.query_data(versi_verse_node_query, var)
			if len(versi_node['verse']) < 1:
				raise Exception("Cant find versification node: %s", var)
			mapping = {"uid": str(bib_uid),
						"excludedVerse": {"uid":versi_node['verse'][0]['uid']}}
			print(mapping)
			graph_conn.create_data(mapping)

	for verse in versification["partialVerses"]:
		'''if component verses are coming as muiltiple verse nodes in Graph, 
		add a "partialVerse" relation from root verse to components'''
		pass

exluded_verses_query = '''query verses($bib_uid: string){
	verse(func: uid($bib_uid)) @normalize{
		bible,
		excludedVerse{
			verse: verseNumber,
			belongsTo{
				chapter: chapter,
				belongsTo{
					book: bookcode
				}
			}
		}
	}	
}

'''

verse_mappings_query = '''
query verses($bib_uid: string){
	verse(func: uid($bib_uid)) @cascade @normalize{
		bible,
		~belongsTo{
			srcBook:bookNumber,
			~belongsTo{
				srcChapter:chapter,
				~belongsTo{
					srcVerse: verse,
					verseMapping{
						trgVerse: verseNumber,
						belongsTo{
							trgChapter: chapter,
							belongsTo{
								trgBook: bookcode
							}
						}
					}
				}
			}
		}

	}	
}
'''

maxVerse_query = '''query struct($bib_uid: string){
	struct(func: uid($bib_uid)) {
		bible,
		~belongsTo{
			bookNumber,
			~belongsTo (orderasc: chapter) @normalize{
				chapter: chapter,
	    		~belongsTo{
					verseNum as verse
  				}
  				maxVerse: max(val(verseNum))
			}
		}
	}	
}
'''

@app.get("/versification/map", status_code=200, tags=["READ", "Versification"])
def get_versification_map(bible_name:str):
	'''Gets a text output as given by versification sniffer, if mapping is added for the bible'''
	versification = {}
	versification["maxVerses"] = {}
	versification["partialVerses"] = {}
	versification["verseMappings"] = {}
	versification["excludedVerses"] = []
	versification["unexcludedVerses"] = {}
	connect_Graph()
	bib_res = graph_conn.query_data(bible_uid_query, {"$bib":bible_name})
	if len(bib_res['bible']) < 1:
		raise HTTPException("Bible not found:%s", bible_name)
	bib_uid = bib_res['bible'][0]['uid']

	## exlcudedVerses
	verses = graph_conn.query_data(exluded_verses_query, {"$bib_uid": str(bib_uid)})
	for ver in verses['verse']:
		ref = '%s %s:%s'%(ver['book'], ver['chapter'], ver['verse'])
		versification["excludedVerses"].append(ref)
	print(versification["excludedVerses"])

	# verseMappings
	mapped_verses = graph_conn.query_data(verse_mappings_query, {"$bib_uid": str(bib_uid)})

	for ver in mapped_verses['verse']:
		key = "%s %s:%s"%(num_book_map[ver["srcBook"]], ver["srcChapter"], ver["srcVerse"])
		val = "%s %s:%s"%(ver["trgBook"], ver["trgChapter"], ver["trgVerse"])
		if key in versification['verseMappings']:
			match_obj = re.match(verse_range_pattern, versification['verseMappings'][key])
			book = match_obj.group(1)
			chapter = match_obj.group(2)
			verse_s = match_obj.group(3)
			verse_e = match_obj.group(4)
			if book == ver["trgBook"] and chapter == ver["trgChapter"]:
				if verse_e is None:
					range_ = sorted([int(verse_s), ver["trgVerse"]])
				else:
					range_ = sorted([int(verse_s), int(verse_e), ver["trgVerse"]])
				sorted_range = str(range_[0])+"-"+str(range_[-1])
				val = "%s %s:%s"%(ver["trgBook"], ver["trgChapter"], sorted_range)
			else:
				val = versification['verseMappings'][key] +", "+ val
		versification['verseMappings'][key] = val
	print(versification['verseMappings'])

	# maxVerses
	book_chapters = graph_conn.query_data(maxVerse_query, {"$bib_uid": str(bib_uid)})
	for book in book_chapters['struct'][0]['~belongsTo']:
		# print(book)
		book_code = num_book_map[book['bookNumber']]
		book_entry = []
		for chap in book['~belongsTo']:
			book_entry.append(chap["maxVerse"])
		versification['maxVerses'][book_code] = book_entry
	print(versification['maxVerses'])

	# partialVerses: to be implemented
	# unExcludedVerses: to be implemented
	return versification

parallel_versi_verses_query = '''query verse($book: string, $chapter:int, $verse:int){
	verse(func: eq(versification, "original")) @cascade @normalize{
		versification,
		~belongsTo @filter(eq(bookcode, $book)){
			bookcode,
			~belongsTo @filter(eq(chapter, $chapter)){
				chapter,
				~belongsTo @filter(eq(verseNumber, $verse)){
					uid
					~verseMapping{
						verse: verseText,
						verseNum: verse,
						belongsTo{
							chapter: chapter,
							belongsTo{
								book:book,
								bookNumber: bookNumber,
								belongsTo{
									bible:bible
								}
							}
						}
					}
				}
			}
		}
	}	
}
'''

simple_parallel_verses_query = '''query verse($book: string, $chapter:int, $verse:int){
	verse(func: has(bible)) @normalize @cascade{
		bible:bible,
		~belongsTo @filter(eq(bookNumber, $book)){
			book:book,
			bookNumber:bookNumber,
			~belongsTo @filter(eq(chapter, $chapter)){
				chapter:chapter,
				~belongsTo @filter(eq(verse, $verse)){
					verseNumber:verse,
					verseText:verseText
				}
			}
		}
	}	
}
'''

@app.get("/versification/verse", status_code=200, tags=["READ", "Versification"])
def get_verse_map(bookcode: BibleBook, chapter:int, verse:int):
	'''Gets all verses mapped to the original verse given by bcv.'''
	connect_Graph()
	var = {"$book": bookcode.upper(), "$chapter":str(chapter), "$verse":str(verse)}
	mapped_verses = graph_conn.query_data(parallel_versi_verses_query, var)['verse']
	# print(mapped_verses)
	res = mapped_verses
	mapped_bibles = set([item['bible'] for item in mapped_verses])

	var['$book'] = str(book_num_map[bookcode])
	parallelverses = graph_conn.query_data(simple_parallel_verses_query, var)['verse']
	for ver in parallelverses:
		if ver['bible'] not in mapped_bibles:
			res.append(ver)

	return res

