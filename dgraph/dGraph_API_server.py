from flask import Flask, render_template, request
from dGraph_conn import dGraph_conn
import pymysql
import csv, json
import itertools
import pandas as pd
import re, math


rel_db_name = 'AutographaMT_Staging'

graph_conn = None
app = Flask(__name__)


@app.route('/')
def main():
	global graph_conn
	graph_conn = dGraph_conn()
	print(graph_conn)
	return render_template('admin.html')

### Graph ####

'/graph' # get
# intialize a connection and add schema
# show the dash board

'/graph' # delete
# delete the entire graph
# show the dash board

###############

### strong numbers #########

'/strongs' # get
# get the whole list of strongs nodes and their property values

'/strongs/<text:strongs_number>' #get
# get the specified strong number's property values with all incoming and outgoing links

'/strongs'	# post
# creates a strongs dictionary node if not already present
# add a list of strongs numbers and their property values to graph and link to strongs dictionary node

'/strongs/<text:strongs_number>' # put
# either update/add a property value or add a link to the selected strongs number node

'/strongs' #delete
# deletes the dictionary node and also all strong number nodes

'/strongs/<text:strongs_number>' #delete
# deletes the selected strongs node

#############################

### translation words #########

'/translation-word' # get
# get the whole list of translation-word nodes and their property values

'/translation-word/<text:translation_word>' #get
# get the specified tw's property values with all incoming and outgoing links

'/translation-word'	# post
# creates a translation-word dictionary node if not already present
# add a list of translation-words  and their property values to graph and link to translation-word dictionary node

'/translation-word/<text:translation_word>' # put
# either update/add a property value or add a link to the selected translation-word number node

'/translation-word' #delete
# deletes the dictionary node and also all strong number nodes

'/translation-word/<text:translation_word>' #delete
# deletes the selected node

#############################


### bible names #########


'/bible-name' # get
# get the whole list of bible-name nodes and their property values

'/bible-name/<text:bible_name>' #get
# get the specified name's property values with all incoming and outgoing links

'/bible-name'	# post
# creates a bible-name dictionary node if not already present
# add a list of bible-names  and their property values to graph and link to bible-name dictionary node


'/bible-name/<text:bible_name>' # put
# either update/add a property value or add a link to the selected bible-name number node

'/bible-name' #delete
# deletes the dictionary node and also all strong number nodes

'/bible-name/<text:translation_word>' #delete
# deletes the selected node

#############################



##### Bible #######

'/bible' # get
# fetches all the bible nodes and their property values

'/bible/<text: bible_name>' #get
# bible_name would be a unique identifier with version name, version number(if present) and language code
# fetches the property values of the seleted bible and all incoming and outgoing links

'/bible' # post
# creates a list of bible nodes with specified properties
# { 'bible name': "mal_IRV4_bible/eng_ESV_bible/grk_UGNT_bible",
#    'language': "mal" }


'/bible/<text: bible_name>' #put
# update/add a property value or add a link to the specified bible node

'/bible/<text:bible_name>' # delete
# delete the selected bible node and all connections to/from it, also deleting its contents books, chapters, verses and words

#####################


######## bible-book #######

'/bible-book/<text:bible>' # get
# fetches all available books in selected bible

'/bible-book/<text:bible>/<text:book_code>' # get
# fetches all properties and connections(available chapters) of selected book 

'/bible-book/<text:bible>' #post
# Create a list of book nodes under the selected bible node

'/bible-book/<text:bible>/<text:book_code>' #put
# add/change property values and also add new links 

'/bible-book/<text:bible>/<text:book_code>' # delete
# delete the selected book node and all connections to/from it, also deleting its contents chapters, verses and words

############################


######## bible-book-chapter #######

'/bible-book-chapter/<text:bible>/<text:book_code>' # get
# fetches all available chapters in selected bible book

'/bible-book-chapter/<text:bible>/<text:book_code>/<int:chapter_number>' # get
# fetches all properties and connections(available verses) of selected chapter 

'/bible-book-chapter/<text:bible>/<text:book_code>' #post
# Create a list of chapter nodes under the selected book node

'/bible-book-chapter/<text:bible>/<text:book_code>/<text:chapter_number>' #put
# add/change property values and also add new links 

'/bible-book-chapter/<text:bible>/<text:book_code>/<text:chapter>' # delete
# delete the selected chapter node and all connections to/from it, also deleting its contents verses and words

############################

######## bible-book-chapter-verse #######

'/bible-book-chapter-verse/<text:bible>/<text:book_code>/<int:chapter_number>' # get
# fetches all available verses in selected chapter

'/bible-book-chapter-verse/<text:bible>/<text:book_code>/<int:chapter_number>/<text:verse_number>' # get
# fetches all properties and connections(available words) of selected verse 

'/bible-book-chapter-verse/<text:bible>/<text:book_code>/<int:chapter_number>' #post
# Create a list of verse nodes under the selected chapter node. Also create the word nodes under each of these verses

'/bible-book-chapter-verse/<text:bible>/<text:book_code>/<int:chapter_number>/<text:verse_number>' #put
# add/change property values and also add new links 

'/bible-book-chapter-verse/<text:bible>/<text:book_code>/<int:chapter_number>/<text:verse_number>' # delete
# delete the selected chapter node and all connections to/from it, also deleting its  word nodes

#########################################


######## bible-word #######

'/bible-word/<text:language>/<text:word>' # get
# fetches all available occurances of the specified word in that language's bible
# returns [ { word:"", bible:"", book: "", chapter: "", verse :""}, {}, ... ]

'/bible-word/<text:bible>/<text:book_code>/<int:chapter_number>/<text:verse_number>/<text:word>' # get
# fetches all properties and connections(available links to dictionaries etc) of all occurances of the word in the selected verse
# returns [ {"word":"", position:"", property1:"", ... }, {}, ... ]

'/bible-word/<text:bible>/<text:book_code>/<int:chapter_number>/<text:verse_number>/<int:position>' #put
# add/change property values and also add new links 

#########################################


##### alignment ######

'/alignment/<Text:bible_name1>/<text:bible_name2>/<text:bbbcccvvv>' #get
# input: in bbbcccvvv , bbb if 3 letter book_code, ccc is chapter number and vvv is verse number
# biblenames could be any bible present in DB, they are not restricted to greek
# if none of them is greek then alignment is derived via the alignmnents to greek
# Alignmnet across verses not handled now as the data also doesnt have it yet
# returns the word alignmnets for the selected verse pairs. 

'/alignment/<Text:bible_name1>/<text:bible_name2>' #post
# using a list of alignments exported from mysql DB, add links bettween bible-word nodes of each bible
# Alignmnet across verses not handled now as the data also doesnt have it yet
# As we only have alignmnets to greek bible, bible_name2 is restricted to the greek bible in graph DB

'/alignment/<Text:bible_name1>/<text:bible_name2>' #delete
# delete all alignment links bettween bible-word nodes of the selected bibles

#####################################


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, debug=True)


