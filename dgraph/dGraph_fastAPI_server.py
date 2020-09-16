from fastapi import FastAPI, Query, Path, Body, HTTPException
import pymysql
from dGraph_conn import dGraph_conn
import logging, csv
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


app = FastAPI()
graph_conn = None
rel_db_name = 'AutographaMT_Staging'
logging.basicConfig(filename='example.log',level=logging.DEBUG)

book_num_map = {'mat': 40, "matthew": 40}


@app.get("/", status_code=200)
def test():
	return {'msg': "server up and running"}


############### Graph #####################

@app.get("/graph", status_code = 200)
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

@app.delete("/graph", status_code=200)
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
			occurance:~lemma @normalize{
				position:position,
				word:word,
				belongsTo{
					verse: verse,
					belongsTo{
						chapter:chapter,
						belongsTo{
						  book:book,
						  belongsTo {
						   bible:bible 
	}	}	}	}	}	} }
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
						lemma {
							StrongsNumber:StrongsNumber,
							pronunciation:pronunciation,
							lexeme:lexeme,
							transliteration:transliteration,
							definition:definition,
							strongsNumberExtended:strongsNumberExtended,
							englishWord:englishWord
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

@app.get("/strongs", status_code=200)
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
	return result

@app.put("/strongs/{strongs_number}", status_code = 200)
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


@app.post("/strongs", status_code=201)
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
	dict_node = { 'dictionary': nodename
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
		# if not next_row:
		# 	break
		if count_for_test>50:
			break
		count_for_test += 1
		strongID = next_row[0]
		Pronunciation = next_row[1]
		Lexeme = next_row[2]
		Transliteration = next_row[3]
		Definition = next_row[4]
		StrongsNumberExtended = next_row[5]
		EnglishWord = next_row[6]

		strong_node = {
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
		occurances: ~tw @normalize {
	        position:position,
	        word:word,
			belongsTo{
				verse: verse,
		        belongsTo{
		            chapter:chapter,
		            belongsTo{
		              book:book,
		              belongsTo {
		               bible:bible 
	}	}	}	}	} }	}
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
						tw {
							translationWord:translationWord,
							slNo:slNo,
							twType:twType,
							description:description,
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


@app.get("/translationwords", status_code=200)
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
	return result


@app.put("/translationwords/{translation_word}", status_code = 200)
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


@app.post("/translationwords", status_code=201)
def add_translationwords():
	'''creates a translation word dictionary.
	 Collects tw data from CSV file and adds to graph 
	 '''
	tw_path = 'Resources/translationWords/tws.csv'
	nodename = 'translation words'

	# create a dictionary nodename
	dict_node = { 'dictionary': nodename
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
