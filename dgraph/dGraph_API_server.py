from flask import Flask, render_template, request
from flask_restplus import Api, Resource, reqparse, fields, marshal_with
import pymysql
from dGraph_conn import dGraph_conn
import logging, csv


rel_db_name = 'AutographaMT_Staging'
logging.basicConfig(filename='example.log',level=logging.DEBUG)

graph_conn = None
app = Flask(__name__)
api = Api(app)

book_num_map = {'mat': 40, "matthew": 40}
##### Graph #####

class Graph(Resource):
	def get(self):
		''' intialize a connection and add schema'''
		global graph_conn
		try:
			graph_conn = dGraph_conn()
		except Exception as e:
			logging.error('At connecting to graph DB')
			logging.error(e)
			return { 'message': 'Not connected', 'error':e}, 500
		return {'message': 'Connected to graph'}, 200

	def delete(self):
		''' delete the entire graph'''
		pass
api.add_resource(Graph, '/graph', endpoint = 'graph')

#################



### strong numbers #########
strongs_put_args = reqparse.RequestParser()
strongs_put_args.add_argument('StrongsNumber',type=str, required=True, help="example: 3704")
strongs_put_args.add_argument('pronunciation',type=str, help="example: hop'-oce")
strongs_put_args.add_argument('lexeme',type=str, help="the root word. example :ὅπως")
strongs_put_args.add_argument('transliteration',type=str, help="example: hópōs")
strongs_put_args.add_argument('definition',type=str, help="the definition")
strongs_put_args.add_argument('strongsNumberExtended',type=str, help="example: g3704")
strongs_put_args.add_argument('englishWord',type=str, help="example: that 45, how 4, to 4, so that 1, when 1, because 1")
strongs_put_args.add_argument('belongsTo',type=dict, help="belongsTo is a dictionary with uid of strongs dictionary node")



occurance_dict = {
  'bible' : fields.String,
  'book' : fields.String,
  'chapter': fields.Integer,
  'verse': fields.Integer,
  'position': fields.Integer,
  'word': fields.String
 }
strongs_resource = {
	'uid': fields.String,
	'StrongsNumber' : fields.String,
	'pronunciation' : fields.String,
	'lexeme' : fields.String,
	'transliteration' : fields.String,
	'definition' : fields.String,
	'strongsNumberExtended' : fields.String,
	'englishWord' : fields.String,
	'belongsTo' : fields.String,
	'word-occurances' : fields.List(fields.Nested(occurance_dict))
}

strongs_resource_list = {
	'strongs' :fields.List(fields.Nested(strongs_resource))
}

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
		strongs(func: eq(StrongsNumber, $strongs))  @cascade{
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


class Strongs(Resource):

	@marshal_with(strongs_resource_list)
	def get(self):
		''' get the whole list of strongs nodes and their property values'''
		result = []
		try:
			query_res = graph_conn.query_data(all_strongs_query,{'$dummy':''})
		except Exception as e:
			logging.error('At fetching strongs numbers')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':e}, 500
		result = query_res
		return result

	@api.expect(strongs_put_args)
	def put(self):
		''' either update a property value or add a link to the selected strongs number node'''
		args = strongs_put_args.parse_args()
		logging.info("input args %s" % args)
		
		return {'message': 'Not implemented yet'}, 201 # created

	def post(self):
		'''creates a strongs dictionary.
		 Collects strongs data from mysql DB and add to graph 
		 '''
		db = pymysql.connect(host="localhost",database=rel_db_name, user="root", password="password", charset='utf8mb4')
		cursor = db.cursor(pymysql.cursors.SSCursor)
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
			return { 'message': 'Aborting'}, 500
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
				return { 'message': 'Aborting'}, 500
			logging.info('strong_node_uid: %s' %strong_node_uid)


		cursor.close()
		db.close()
		return "success"
		return {'message': 'Added to graph'}, 201 # created


api.add_resource(Strongs, '/strongs', endpoint = 'strongs', methods=['GET', 'POST', 'PUT'])

class StrongsLink(Resource):
	@marshal_with(strongs_resource_list)
	def get(self, strongs_number):
		''' fetches the strongs number details and its occurances'''
		try:
			query_res = graph_conn.query_data(strongs_link_query,{'$strongs':strongs_number})
		except Exception as e:
			logging.error('At fetching strongs number links')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':str(e)}, 500
		result = query_res
		return result

api.add_resource(StrongsLink, '/strongslink/<string:strongs_number>', endpoint = 'strongslink', methods=['GET'])


class StrongsVerseLink(Resource):
	def get(self, bbbcccvvv):
		''' fetches all strongs numbers in verse'''
		variables = {
					'$book': str(book_num_map[bbbcccvvv[:3].lower()]),
					'$chap':bbbcccvvv[3:6],
					'$ver': bbbcccvvv[-3:]
					}
		logging.info(variables)
		try:
			query_res = graph_conn.query_data(strongs_in_verse_query, variables)
		except Exception as e:
			logging.error('At fetching strongs links in verse')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':str(e)}, 500
		result = query_res

		return result

api.add_resource(StrongsVerseLink, '/strongsverselink/<string:strongs_number>/<string:bbbcccvvv>', endpoint = 'strongsverselink', methods=['GET'])

##############################


### translation words #########
tw_put_args = reqparse.RequestParser()
tw_put_args.add_argument('translationWord',type=str, help="")
tw_put_args.add_argument('slNo',type=str, help="")
tw_put_args.add_argument('twType',type=str, help="")
tw_put_args.add_argument('description',type=str, help="")
tw_put_args.add_argument('belongsTo',type=dict, help="belongsTo is a dictionary with uid of translationword dictionary node")

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

class TranslationWord(Resource):
	def get(self):
		''' get the whole list of translationWord nodes and their property values'''
		result = []
		try:
			query_res = graph_conn.query_data(all_tw_query,{'$dummy':''})
		except Exception as e:
			logging.error('At fetching translationWords')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':str(e)}, 500
		result = query_res
		return result


	def put(self, translation_word):
		''' either update a property value or add a link to the selected translation-word node'''
		args = tw_put_args.parse_args()
		logging.info("input args %s" % args)
		return {'message': 'Not implemented yet'}, 201 # created

	def post(self):
		''' creates a translation-word dictionary. 
		 add a list of translation-words  and their property values to graph '''
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
			return { 'message': 'Aborting'}, 500
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
					return { 'message': 'Aborting'}, 500
				logging.info('tw_node_uid:%s' %tw_node_uid)
		return {'message': 'Added to graph'}, 201 # created


api.add_resource(TranslationWord, '/translationword', endpoint = 'translationword', methods=['GET', 'POST', 'PUT'])

class TranslationWordLinks(Resource):

	def get(self, translation_word):
		''' fetches the details of the TW, with its occurances'''
		try:
			query_res = graph_conn.query_data(tw_link_query,{'$tw':translation_word})
		except Exception as e:
			logging.error('At fetching tw links')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':str(e)}, 500
		result = query_res
		return result


api.add_resource(TranslationWordLinks, '/translationwordlinks/<string:translation_word>', endpoint = 'translationwordlinks')

class TranslationWordVerseLinks(Resource):
	def get(self, bbbcccvvv):
		''' fetches all TWs in verse'''
		variables = {
					'$book': str(book_num_map[bbbcccvvv[:3].lower()]),
					'$chap':bbbcccvvv[3:6],
					'$ver': bbbcccvvv[-3:]
					}
		logging.info(variables)
		try:
			query_res = graph_conn.query_data(tw_in_verse_query, variables)
		except Exception as e:
			logging.error('At fetching tw links in verse')
			logging.error(e)
			return { 'message': 'Graph side error', 'error':str(e)}, 500
		result = query_res
		return result

api.add_resource(TranslationWordVerseLinks, '/translationwordverselinks/<string:bbbcccvvv>', endpoint = 'translationwordverselinks')

# #############################


# ### bible names #########
# class BibleName(Resource):
# 	def get(self):
# 		# get the whole list of bible-name nodes and their property values
# 		pass

# 	def get(self, name):
# 		# get the specified name's property values with all incoming and outgoing links
# 		pass

# 	def get(self, name, bible_name):
# 		# get the specified name's property values with all incoming and outgoing links
# 		pass

# 	def get(self, name, bible_name, bbbcccvvv):
# 		# input: bbbcccvvv. bbb for 3 letter book code and ccc and vvv chapter and verse number. vvv and bbb are optional
# 		# get the specified name's property values with all incoming and outgoing links
# 		pass


# 	def put(self, name):
# 		# either update/add a property value or add a link to the selected bible-name number node
# 		pass

# 	def post(self):
# 		# creates a bible-name dictionary node if not already present
# 		# add a list of bible-names  and their property values to graph and link to bible-name dictionary node
# 		pass

# 	def delete(self):
# 		# deletes the dictionary node and also all strong number nodes
# 		pass

# 	def delete(self, name):
# 		# deletes the selected node
# 		pass		

# api.add_resource(BibleName, '/biblename', endpoint = 'biblename')
# api.add_resource(BibleName, '/biblename/<string:name>', endpoint = 'biblename/name')
# api.add_resource(BibleName, '/biblename/<string:name>/<string:bible_name>', endpoint = 'biblename/name/bible')
# api.add_resource(BibleName, '/biblename/<string:name>/<string:bible_name>/<string:bbbcccvvv>', endpoint = 'biblename/name/bible/bcv')

# #############################



# ##### Bible #######
# class Bible(Resource):
# 	def get(self):
# 		# fetches all the bible nodes and their property values
# 		pass

# 	def get(self, bible_name):
# 		# bible_name would be a unique identifier with version name, version number(if present) and language code
# 		# fetches the property values of the seleted bible and all incoming and outgoing links    	
# 		pass

# 	def put(self, bible_name):
# 		# update/add a property value or add a link to the specified bible node
# 		pass

# 	def post(self):
# 		# creates a list of bible nodes with specified properties
# 		# { 'bible name': "mal_IRV4_bible/eng_ESV_bible/grk_UGNT_bible",
# 		#    'language': "mal" }
# 		pass

# 	def delete(self, bible_name):
# 		# delete the selected bible node and all connections to/from it, also deleting its contents books, chapters, verses and words
# 		pass

# api.add_resource(Bible, '/bible', endpoint = 'bible')
# api.add_resource(Bible, '/users/<string:bible_name>', endpoint = 'bible/biblename')

# #####################


# ######## bible-book #######
# class BibleBook(Resource):
# 	def get(self, bible_name):
# 		# fetches all available books in selected bible
# 		pass

# 	def get(self, bible_name, book_code):
# 		# fetches all properties and connections(available chapters) of selected book 
# 		pass

# 	def put(self, bible_name, book_code):
# 		# add/change property values and also add new links 
# 		pass

# 	def post(self, bible_name):
# 		# Create a list of book nodes under the selected bible node
# 		pass    	

# 	def delete(self, bible_name, book_code):
# 		# delete the selected book node and all connections to/from it, also deleting its contents chapters, verses and words
# 		pass

# api.add_resource(BibleBook, '/bible/book/<string:bible_name>', endpoint = 'bible/book/biblename')
# api.add_resource(BibleBook, '/bible/book/<string:bible_name>/<string:book_code>', endpoint = 'bible/book/biblename/bookcode')

# ############################


# ######## bible-book-chapter #######
# class BibleBookChapter(Resource):
# 	def get(self, bible_name, book_code):
# 		# fetches all available chapters in selected bible book
# 		pass

# 	def get(self, bible_name, book_code, chapter_number):
# 		# fetches all properties and connections(available verses) of selected chapter 
# 		pass

# 	def put(self, bible_name, book_code, chapter_number):
# 		# add/change property values and also add new links 
# 		pass

# 	def post(self, bible_name, book_code):
# 		# Create a list of chapter nodes under the selected book node
# 		pass

# 	def delete(self, bible_name, book_code, chapter_number):
# 		# delete the selected chapter node and all connections to/from it, also deleting its contents verses and words
# 		pass

# api.add_resource(BibleBookChapter, '/bible/book/chapter/<string:bible_name>/<string:book_code>', endpoint = '/bible/book/chapter/biblename/bookcode')
# api.add_resource(BibleBookChapter, '/bible/book/chapter/<string:bible_name>/<string:book_code>/<int:chapter_number>', endpoint = '/bible/book/chapter/biblename/bookcode/chapter')

# ############################

# ######## bible-book-chapter-verse #######
# class BibleBookChapterVerse(Resource):
# 	def get(self, bible_name, book_code, chapter_number):
# 		# fetches all available verses in selected chapter
# 		pass

# 	def get(self, bible_name, book_code, chapter_number, verse_number):
# 		# fetches all properties and connections(available words) of selected verse 
# 		pass

# 	def put(self, bible_name, book_code, chapter_number, verse_number):
# 		# add/change property values and also add new links 
# 		pass

# 	def post(self, bible_name, book_code, chapter_number):
# 		# Create a list of verse nodes under the selected chapter node. 
# 		# Also create the word nodes under each of these verses
# 		pass

# 	def delete(self, bible_name, book_code, chapter_number, verse_number):
# 		# delete the selected chapter node and all connections to/from it, also deleting its  word nodes
# 		pass

# api.add_resource(BibleBookChapterVerse, '/bible/book/chapter/verse/<string:bible_name>/<string:book_code>/<int:chapter_number>', endpoint = '/bible/book/chapter/verse/bookcode/chapter')
# api.add_resource(BibleBookChapterVerse, '/bible/book/chapter/verse/<string:bible_name>/<string:book_code>/<int:chapter_number>/<string:verse_number>', endpoint = '/bible/book/chapter/verse/bookcode/chapter/verse')

# #########################################


# ######## bible-word #######
# class BibleWord(Resource):
# 	def get(self, bible_name, word):
# 		# fetches all available occurances of the specified word in that language's bible
# 		# returns [ { word:"", bible:"", book: "", chapter: "", verse :""}, {}, ... ]
# 		pass

# 	def get(self, bible_name, bbbcccvvv, word):
# 		# fetches all properties and connections(available links to dictionaries etc) of all occurances of the word in the selected verse
# 		# returns [ {"word":"", position:"", property1:"", ... }, {}, ... ]
# 		pass

# 	def get(self, bible_name, bbbcccvvv, position):
# 		# not sure if this would work as themethod above has a similar parameter list
# 		pass

# 	def put(self, bible_name, bbbcccvvv, position):
# 		# add/change property values and also add new links 
# 		pass


# api.add_resource(BibleWord, '/bible/word/<string:bible_name>/<string:word>', endpoint = '/bible/word/biblename/word')
# api.add_resource(BibleWord, '/bible/word/<string:bible_name>/<string:bbbcccvvv>/<string:word>', endpoint = '/bible/word/biblename/bcv/word')
# api.add_resource(BibleWord, '/bible/word/<string:bible_name>/<string:bbbcccvvv>/<int:position>', endpoint = '/bible/word/biblename/bcv/position')

# #########################################


# ##### alignment ######
# class Alignment(Resource):
# 	def get(self, bible_name1, bible_name2, bbbcccvvv):
# 		# input: in bbbcccvvv , bbb if 3 letter book_code, ccc is chapter number and vvv is verse number
# 		# biblenames could be any bible present in DB, they are not restricted to greek
# 		# if none of them is greek then alignment is derived via the alignmnents to greek
# 		# Alignmnet across verses not handled now as the data also doesnt have it yet
# 		# returns the word alignmnets for the selected verse pairs. 
# 		pass

# 	def post(self, bible_name1, bible_name2):
# 		# using a list of alignments exported from mysql DB, add links bettween bible-word nodes of each bible
# 		# Alignmnet across verses not handled now as the data also doesnt have it yet
# 		# As we only have alignmnets to greek bible, bible_name2 is restricted to the greek bible in graph DB
# 		pass

# 	def delete(self, bible_name1, bible_name2):
# 		# delete all alignment links bettween bible-word nodes of the selected bibles
# 		pass

# api.add_resource(Alignment, '/alignment/<string:bible_name1>/<string:bible_name2>/<string:bbbcccvvv>', endpoint = 'alignment/biblenames/bcv')
# api.add_resource(Alignment, '/alignment/<string:bible_name1>/<string:bible_name2>', endpoint = 'alignment/biblenames')

# #####################################


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, debug=True)


