from fastapi import FastAPI, Query, Path, Body, HTTPException
import pymysql
from dGraph_conn import dGraph_conn
import logging, csv, urllib
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


app = FastAPI()
graph_conn = None
rel_db_name = 'AutographaMT_Staging'
logging.basicConfig(filename='example.log',level=logging.DEBUG)
base_URL = 'http://localhost:9000'

book_num_map = { 'mat':40, 'mrk' : 41, 'luk': 42, 'jhn': 43}

num_book_map = {}
for key in book_num_map:
	num_book_map[book_num_map[key]] = key

class BibleBook(str, Enum):
	mat = 'mat'
	mrk = 'mrk'
	luk = 'luk'
	jhn = 'jhn'

class Reference(BaseModel):
	book : BibleBook
	chapter: int
	verse: int

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

@app.get('/bibles', status_code=200)
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

@app.put('/bibles/{bible_name}', status_code=200)
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


@app.post('/bibles', status_code = 200)
def add_bible(bible_name: str = Body("Hindi IRV4 bible"), language: str = Body("Hindi"), version: str = Body('IRV4'), tablename: str = Body('Hin_IRV4_BibleWord'), bookcode: BibleBook = Body('mat')):
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
		bib_node = { 'bible': bible_name,
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
			cursor.execute("Select LID, Position, Word, Map.Book, Chapter, Verse,lookup.Book, Strongs, Morph, Pronunciation, TW from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID = %s order by LID, Position",(book_num_map[bookcode.value]))
		else:
			cursor.execute("Select LID, Position, Word, Map.Book, Chapter, Verse,lookup.Book from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID=%s order by LID, Position",(book_num_map[bookcode.value]))
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
				'verse' : Verse,
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
	add_verseTextToBible(bib_node_uid, tablename.replace('BibleWord','Text'), bookcode.value)	
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



@app.post('/alignment')
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

@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}')
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


@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}')
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
@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}/words/{position}')
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