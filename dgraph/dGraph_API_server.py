from flask import Flask, render_template, request
from flask_restful import Api, Resourceimport pymysql
from dGraph_conn import dGraph_conn



rel_db_name = 'AutographaMT_Staging'

graph_conn = None
app = Flask(__name__)
api = Api(app)

##### Graph #####

class Graph(Resource):
    def get(self):
		# intialize a connection and add schema
        pass

    def delete(self):
		# delete the entire graph
        pass
api.add_resource(UserAPI, '/graph', endpoint = 'user')

#################



### strong numbers #########
class Strongs(Resource):
    def get(self):
		# get the whole list of strongs nodes and their property values
        pass

    def get(self, strongs_number):
		# get the specified strong number's property values with all incoming and outgoing links
		# the links would give its occurances in bible(links to bible-words)
        pass

    def get(self, strongs_number, bible_name):
		# get the specified strong number's property values with all incoming and outgoing links
		# the links would give its occurances in bible(links to bible-words)
        pass

    def get(self, strongs_number, bible_name, bbbcccvvv):
    	# input: bbbcccvvv. bbb for 3 letter book code and ccc and vvv chapter and verse number. vvv and bbb are optional
		# get the specified strong number's property values with all incoming and outgoing links
		# the links would give its occurances in bible(links to bible-words)
        pass

    def put(self, strongs_number):
		# either update/add a property value or add a link to the selected strongs number node
        pass

     def post(self):
		# creates a strongs dictionary node if not already present
		# add a list of strongs numbers and their property values to graph and link to strongs dictionary node
     	pass

    def delete(self):
		# deletes the dictionary node and also all strong number nodes
        pass

    def  delete(self, strongs_number):
		# deletes the selected strongs node
    	pass

api.add_resource(Strongs, '/strongs', endpoint = 'strongs')
api.add_resource(Strongs, '/strongs/<text:strongs_number>', endpoint = 'strongs')
api.add_resource(Strongs, '/strongs/<text:strongs_number>/<text:bible_name>', endpoint = 'strongs')
api.add_resource(Strongs, '/strongs/<text:strongs_number>/<text:bible_name>/<text:bbbcccvvv>', endpoint = 'strongs')

##############################


### translation words #########

class TranslationWord(Resource):
    def get(self):
		# get the whole list of translation-word nodes and their property values
        pass

    def get(self, translation_word):
		# get the specified tw's property values with all incoming and outgoing links
    	pass

    def get(self, translation_word, bible_name):
		# get the specified tw's property values with all incoming and outgoing links
    	pass

    def get(self, translation_word, bible_name, bbbcccvvv):
    	# input: bbbcccvvv. bbb for 3 letter book code and ccc and vvv chapter and verse number. vvv and bbb are optional
		# get the specified tw's property values with all incoming and outgoing links
    	pass

    def put(self, translation_word):
		# either update/add a property value or add a link to the selected translation-word number node
        pass

    def post(self):
		# creates a translation-word dictionary node if not already present
		# add a list of translation-words  and their property values to graph and link to translation-word dictionary node
    	pass

    def delete(self):
		# deletes the dictionary node and also all strong number nodes
        pass

    def delete(self, translation_word):
		# deletes the selected node
        pass

api.add_resource(TranslationWord, '/translationword', endpoint = 'translationword')
api.add_resource(TranslationWord, '/translationword/<text:translation_word>', endpoint = 'translationword')
api.add_resource(TranslationWord, '/translationword/<text:translation_word>/<text:bible_name>', endpoint = 'translationword')
api.add_resource(TranslationWord, '/translationword/<text:translation_word>/<text:bible_name>/<text:bbbcccvvv>', endpoint = 'translationword')

#############################


### bible names #########
class BibleName(Resource):
    def get(self):
		# get the whole list of bible-name nodes and their property values
        pass

    def get(self, name):
		# get the specified name's property values with all incoming and outgoing links
    	pass

    def get(self, name, bible_name):
		# get the specified name's property values with all incoming and outgoing links
    	pass

    def get(self, name, bible_name, bbbcccvvv):
    	# input: bbbcccvvv. bbb for 3 letter book code and ccc and vvv chapter and verse number. vvv and bbb are optional
		# get the specified name's property values with all incoming and outgoing links
    	pass


    def put(self, name):
		# either update/add a property value or add a link to the selected bible-name number node
        pass

    def post(self):
		# creates a bible-name dictionary node if not already present
		# add a list of bible-names  and their property values to graph and link to bible-name dictionary node
    	pass

    def delete(self):
		# deletes the dictionary node and also all strong number nodes
	    pass

	def delete(self, name):
		# deletes the selected node
		pass		

api.add_resource(BibleName, '/biblename', endpoint = 'biblename')
api.add_resource(BibleName, '/biblename/<text:name>', endpoint = 'biblename')
api.add_resource(BibleName, '/biblename/<text:name>/<text:bible_name>', endpoint = 'biblename')
api.add_resource(BibleName, '/biblename/<text:name>/<text:bible_name>/<text:bbbcccvvv>', endpoint = 'biblename')

#############################



##### Bible #######
class Bible(Resource):
    def get(self):
    	# fetches all the bible nodes and their property values
        pass

    def get(self, bible_name):
		# bible_name would be a unique identifier with version name, version number(if present) and language code
		# fetches the property values of the seleted bible and all incoming and outgoing links    	
		pass

    def put(self, bible_name):
    	# update/add a property value or add a link to the specified bible node
        pass

    def post(self):
		# creates a list of bible nodes with specified properties
		# { 'bible name': "mal_IRV4_bible/eng_ESV_bible/grk_UGNT_bible",
		#    'language': "mal" }
    	pass

    def delete(self, bible_name):
    	# delete the selected bible node and all connections to/from it, also deleting its contents books, chapters, verses and words
        pass

api.add_resource(Bible, '/bible', endpoint = 'bible')
api.add_resource(Bible, '/users/<text:bible_name>', endpoint = 'bible')

#####################


######## bible-book #######
class BibleBook(Resource):
    def get(self, bible_name):
		# fetches all available books in selected bible
        pass

    def get(self, bible_name, book_code):
    	# fetches all properties and connections(available chapters) of selected book 
    	pass

    def put(self, bible_name, book_code):
		# add/change property values and also add new links 
        pass

    def post(self, bible_name):
		# Create a list of book nodes under the selected bible node
		pass    	

    def delete(self, bible_name, book_code):
		# delete the selected book node and all connections to/from it, also deleting its contents chapters, verses and words
        pass

api.add_resource(BibleBook, '/bible/book/<text:bible_name>', endpoint = 'bible/book')
api.add_resource(BibleBook, '/bible/book/<text:bible_name>/<text:book_code>', endpoint = 'bible/book')

############################


######## bible-book-chapter #######
class BibleBookChapter(Resource):
    def get(self, bible_name, book_code):
		# fetches all available chapters in selected bible book
        pass

    def get(self, bible_name, book_code, chapter_number):
		# fetches all properties and connections(available verses) of selected chapter 
        pass

    def put(self, bible_name, book_code, chapter_number):
		# add/change property values and also add new links 
        pass

    def post(self, bible_name, book_code):
    	# Create a list of chapter nodes under the selected book node
    	pass

    def delete(self, bible_name, book_code, chapter_number):
		# delete the selected chapter node and all connections to/from it, also deleting its contents verses and words
		pass

api.add_resource(BibleBookChapter, '/bible/book/chapter/<text:bible_name>/<text:book_code>', endpoint = 'bible/book/chapter')
api.add_resource(BibleBookChapter, '/bible/book/chapter/<text:bible_name>/<text:book_code>/<int:chapter_number>', endpoint = 'bible/book/chapter')

############################

######## bible-book-chapter-verse #######
class BibleBookChapterVerse(Resource):
    def get(self, bible_name, book_code, chapter_number):
		# fetches all available verses in selected chapter
        pass

    def get(self, bible_name, book_code, chapter_number, verse_number):
		# fetches all properties and connections(available words) of selected verse 
        pass

    def put(self, bible_name, book_code, chapter_number, verse_number):
		# add/change property values and also add new links 
        pass

    def post(self, bible_name, book_code, chapter_number):
		# Create a list of verse nodes under the selected chapter node. 
		# Also create the word nodes under each of these verses
    	pass

    def delete(self, bible_name, book_code, chapter_number, verse_number):
		# delete the selected chapter node and all connections to/from it, also deleting its  word nodes
        pass

api.add_resource(BibleBookChapterVerse, '/bible/book/chapter/verse/<text:bible_name>/<text:book_code>/<int:chapter_number>', endpoint = 'bible/book/chapter/verse')
api.add_resource(BibleBookChapterVerse, '/bible/book/chapter/verse/<text:bible_name>/<text:book_code>/<int:chapter_number>/<text:verse_number>', endpoint = 'bible/book/chapter/verse')

#########################################


######## bible-word #######
class BibleWord(Resource):
    def get(self, bible_name, word):
		# fetches all available occurances of the specified word in that language's bible
		# returns [ { word:"", bible:"", book: "", chapter: "", verse :""}, {}, ... ]
        pass

    def get(self, bible_name, bbbcccvvv, word):
    	# fetches all properties and connections(available links to dictionaries etc) of all occurances of the word in the selected verse
		# returns [ {"word":"", position:"", property1:"", ... }, {}, ... ]
        pass

    def get(self, bible_name, bbbcccvvv, position):
    	# not sure if this would work as themethod above has a similar parameter list
        pass

    def put(self, bible_name, bbbcccvvv, position):
		# add/change property values and also add new links 
        pass


api.add_resource(BibleWord, '/bible/word/<text:bible_name>/<text:word>', endpoint = 'bible/word')
api.add_resource(BibleWord, '/bible/word/<text:bible_name>/<text:bbbcccvvv>/<text:word>', endpoint = 'bible/word')
api.add_resource(BibleWord, '/bible/word/<text:bible_name>/<text:bbbcccvvv>/<int:position>', endpoint = 'bible/word')

#########################################


##### alignment ######
class Alignment(Resource):
    def get(self, bible_name1, bible_name2, bbbcccvvv):
		# input: in bbbcccvvv , bbb if 3 letter book_code, ccc is chapter number and vvv is verse number
		# biblenames could be any bible present in DB, they are not restricted to greek
		# if none of them is greek then alignment is derived via the alignmnents to greek
		# Alignmnet across verses not handled now as the data also doesnt have it yet
		# returns the word alignmnets for the selected verse pairs. 
        pass

    def post(self, bible_name1, bible_name2):
		# using a list of alignments exported from mysql DB, add links bettween bible-word nodes of each bible
		# Alignmnet across verses not handled now as the data also doesnt have it yet
		# As we only have alignmnets to greek bible, bible_name2 is restricted to the greek bible in graph DB
        pass

    def delete(self, bible_name1, bible_name2):
		# delete all alignment links bettween bible-word nodes of the selected bibles
        pass

api.add_resource(Alignment, '/alignment/<Text:bible_name1>/<text:bible_name2>/<text:bbbcccvvv>', endpoint = 'alignment')
api.add_resource(Alignment, '/alignment/<Text:bible_name1>/<text:bible_name2>', endpoint = 'alignment')

#####################################


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, debug=True)


