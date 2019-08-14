import pymysql
import csv
import pickle

import sys

import py2neo
from py2neo import Graph, NodeMatcher
from py2neo.data import Node, Relationship

db_name = 'AutographaMT_Staging'
# # db = pymysql.connect(host="localhost",database="test_new_tables", user="root", password="11111111", charset='utf8mb4')

graph = Graph(password="password")



def add_UGNT_bible_2neo(buk):
	db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
	cursor = db.cursor(pymysql.cursors.SSCursor)
	cur = db.cursor()

	tablename = 'Grk_UGNT4_BibleWord'
	biblename = 'UGNT4'
	# bible = Node("BIBLE", name=biblename, version="4.0", expandedName="Unfoldingword Greek New Testament")
	bibleNode = Node("BIBLE", name=biblename)
	bibleNode['version'] = 4.0
	bibleNode['expandedName'] = "Unfoldingword Greek New Testament"

	tx = graph.begin()
	tx.merge(bibleNode,'BIBLE','name')
	tx.commit()
	
	Morph_sequence = ['Role','Type','Mood','Tense','Voice','Person','Case','Gender','Number','Degree']

	cursor.execute("Select LID, Position, Word, Strongs, Morph, Pronunciation, Map.Book, Chapter, Verse,lookup.Book, TW from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID = %s order by LID, Position",(buk))

	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break

		LID = str(next_row[0])
		Position = str(next_row[1])
		Word = next_row[2]
		Strongs = next_row[3]
		Morph = next_row[4].split(',')
		Pronunciation = next_row[5]	
		BookNum = str(next_row[6])
		Chapter = str(next_row[7])
		Verse = str(next_row[8])
		BookName = next_row[9]
		TW_fullString = next_row[10]



		# print('LID:'+str(LID))
		# print('Position:'+str(Position))
		# print('Book,Chapter,Verse:'+str(BookNum)+","+str(Chapter)+","+str(Verse))
		# print('BookName:'+str(BookName))

		tx = graph.begin()
	
		bookNode = Node("BOOK",name=BookName,number=BookNum)
		found = False
		for rel in graph.match((None,bibleNode), r_type="BELONGS_TO"):
			if rel.start_node["name"]==BookName:
				bookNode = rel.start_node
				found =True 
		if not found:
			bookRel = Relationship(bookNode,"BELONGS_TO",bibleNode)
			bookRel['atIndex'] = BookNum
			tx.create(bookRel)
			print("creating new book-->bible relation")



		chapterNode = Node("CHAPTER",number=Chapter)
		found = False
		for rel in graph.match((None,bookNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Chapter:
				chapterNode = rel.start_node
				found =True 
		if not found:
			chapRel = Relationship(chapterNode,"BELONGS_TO",bookNode)
			chapRel['atIndex'] = Chapter
			tx.create(chapRel)
			print("creating new chapter-->book relation")



		verseNode = Node("VERSE",number=Verse)
		verseNode['lid'] = LID
		found = False
		for rel in graph.match((None,chapterNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Verse:
				verseNode = rel.start_node
				found =True 
		if not found:
			verseRel = Relationship(verseNode,"BELONGS_TO",chapterNode)
			verseRel['atIndex'] = Verse
			tx.create(verseRel)
			print("creating new verse-->chapter relation")
			print('Book,Chapter,Verse:'+str(BookNum)+","+str(Chapter)+","+str(Verse))

		

		wordNode = Node("WORD",literalform=Word)
		wordNode['position'] = Position
		for key,value in zip(Morph_sequence,Morph):
			if(value!=''):
				wordNode[key] = value
		wordRel = Relationship(wordNode,"BELONGS_TO",verseNode)
		wordRel['atIndex'] = Position
		tx.create(wordRel)
		print("creating new word")

		matcher = NodeMatcher(graph)
		try:
			strongNode = matcher.match("STRONG_NUM", id=Strongs).first()
			# print('strongNode:',strongNode['id'])
			strongRel = Relationship(wordNode,"HAS_LEMMA",strongNode)
			tx.create(strongRel)
		except Exception as e:
			print('wordNode:',wordNode)
			print('sttongNode:',strongNode)
			# if (BookNum,Chapter,Verse) in [(43,8,6)]:
			if strongNode == None:
				# invalid strong number 99237
				pass
			else:
				raise e

		if TW_fullString != "-":
			Type, word = TW_fullString.split('/')[-2:]
			try:
				# twNode = matcher.match("TRANSLATION_WORD", type=Type, word=word).first()
				twNode = matcher.match("TRANSLATION_WORD", word=word).first()
				if twNode == None:
					twNode = matcher.match("TRANSLATION_WORD").where("'"+word+"' in _.forms").first()
				twRel = Relationship(wordNode,"IS_TW",twNode)
				tx.create(twRel)
				
			except Exception as e:
				print('wordNode:',wordNode)
				print('twNode:',twNode)
				if twNode == None:
					pass
				else:
				# elif (BookNum,Chapter,Verse) in [(42,21,36)]:
				# 	# strnegth not found, only strength
				# 	pass
				# else:
				# 	print('TW not found error:')
				# 	print('Type:',Type)
				# 	print('word:',word)
					raise e
		tx.commit()

		# break
	cursor.close()
	cur.close()
	db.close()

# def delete_ugnt_from_neo():
# 	graph.evalate('')


def add_strongs_dict():
	db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
	cursor = db.cursor(pymysql.cursors.SSCursor)
	cur = db.cursor()

	tablename = 'Greek_Strongs_Lexicon'
	dictname = 'Greek Strongs'
	dictNode = Node("DICTIONARY", name=dictname)
	
	print('Before dictNode:',dictNode)
	tx = graph.begin()
	tx.merge(dictNode,'DICTIONARY','name')
	print('After dictNode:',dictNode)

	cursor.execute("Select ID, Pronunciation, Lexeme, Transliteration, Definition, StrongsNumber, EnglishWord from "+tablename+" order by ID")

	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break
		strongID = next_row[0]
		Pronunciation = next_row[1]
		Lexeme = next_row[2]
		Transliteration = next_row[3]
		Definition = next_row[4]
		StrongsNumberExtended = next_row[5]
		EnglishWord = next_row[6]

		print("strongID:",strongID)
		print("EnglishWord:",EnglishWord)

		strongNode = Node("STRONG_NUM",id=strongID)
		strongNode['pronunciation'] = Pronunciation
		strongNode['lexeme'] = Lexeme
		strongNode['transliteration'] = Transliteration
		strongNode['definition'] = Definition
		strongNode['strongsNum'] = StrongsNumberExtended
		strongNode['english'] = EnglishWord
		strongRel = Relationship(strongNode,"BELONGS_TO",dictNode)
		strongRel['atIndex'] = strongID
		tx.create(strongRel)
		print("adding strong:",strongID)

		# break
	tx.commit()
	cursor.close()
	cur.close()
	db.close()
	

def add_tw_dictionary():
	db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
	cursor = db.cursor(pymysql.cursors.SSCursor)
	cur = db.cursor()

	tw_path = 'tws.csv'

	dictname = 'Translation Words'
	dictNode = Node("DICTIONARY", name=dictname)
	
	tx = graph.begin()
	tx.merge(dictNode,'DICTIONARY','name')
	print('dictNode:',dictNode)


	with open(tw_path) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='\t')
		for row in csv_reader:
			sl_no = row[0]
			tw = row[1]
			Type = row[2]
			word_forms = row[3].split(',')
			print('word_forms:',word_forms)

			twNode = Node("TRANSLATION_WORD",id=sl_no)
			twNode['word'] = tw
			twNode['type'] = Type
			if len(word_forms)>0:
				twNode['forms'] = word_forms

			twRel = Relationship(twNode,"BELONGS_TO",dictNode)
			twRel['atIndex'] = sl_no
			tx.create(twRel)
			print("adding tw:",sl_no)


			# break
	tx.commit()
	cursor.close()
	cur.close()
	db.close()


def add_GL_bible_2neo(tablename, biblename,lang,buk,expandedName="Indian Revised Version"):
	db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
	cursor = db.cursor(pymysql.cursors.SSCursor)
	cur = db.cursor()

	# tablename = 'Grk_UGNT4_BibleWord'
	# biblename = 'UGNT4'

	bibleNode = Node("BIBLE", name=biblename)
	bibleNode['version'] = 4.0
	bibleNode['expandedName'] = expandedName
	bibleNode['language'] = lang

	tx = graph.begin()
	tx.merge(bibleNode,'BIBLE','name')
	tx.commit()

	cursor.execute("Select LID, Position, Word, Map.Book, Chapter, Verse,lookup.Book from "+tablename+" JOIN Bcv_LidMap as Map ON LID=Map.ID JOIN Bible_Book_Lookup as lookup ON lookup.ID=Map.Book where lookup.ID=%s order by LID, Position",(buk))

	while(True):
		next_row = cursor.fetchone()
		if not next_row:
			break

		LID = str(next_row[0])
		Position = str(next_row[1])
		Word = next_row[2]
		BookNum = str(next_row[3])
		Chapter = str(next_row[4])
		Verse = str(next_row[5])
		BookName = next_row[6]
		
		# print('LID:'+str(LID))
		# print('Position:'+str(Position))
		print('Book,Chapter,Verse:'+str(BookNum)+","+str(Chapter)+","+str(Verse))
		# print('BookName:'+str(BookName))

		tx = graph.begin()
	
		bookNode = Node("BOOK",name=BookName,number=BookNum)
		found = False
		for rel in graph.match((None,bibleNode), r_type="BELONGS_TO"):
			if rel.start_node["name"]==BookName:
				bookNode = rel.start_node
				found =True 
		if not found:
			bookRel = Relationship(bookNode,"BELONGS_TO",bibleNode)
			bookRel['atIndex'] = BookNum
			tx.create(bookRel)
			print("creating new book-->bible relation")



		chapterNode = Node("CHAPTER",number=Chapter)
		found = False
		for rel in graph.match((None,bookNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Chapter:
				chapterNode = rel.start_node
				found =True 
		if not found:
			chapRel = Relationship(chapterNode,"BELONGS_TO",bookNode)
			chapRel['atIndex'] = Chapter
			tx.create(chapRel)
			print("creating new chapter-->book relation")



		verseNode = Node("VERSE",number=Verse)
		verseNode['lid'] = LID
		found = False
		for rel in graph.match((None,chapterNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Verse:
				verseNode = rel.start_node
				found =True 
		if not found:
			verseRel = Relationship(verseNode,"BELONGS_TO",chapterNode)
			verseRel['atIndex'] = Verse
			tx.create(verseRel)
			print("creating new verse-->chapter relation")

		

		wordNode = Node("WORD",literalform=Word)
		wordNode['position'] = Position
		wordRel = Relationship(wordNode,"BELONGS_TO",verseNode)
		wordRel['atIndex'] = Position
		tx.create(wordRel)
		print("creating new word")

		tx.commit()
	cursor.close()
	cur.close()
	db.close()



def add_alignment_2neo(src_bible,trg_bible,alignment_table,buk):
	db = pymysql.connect(host="localhost",database=db_name, user="root", password="password", charset='utf8mb4')
	cursor = db.cursor(pymysql.cursors.SSCursor)

	matcher = NodeMatcher(graph)
	
	src_bibleNode = None
	trg_bibleNode = None

	src_bibleNode = matcher.match("BIBLE",name=src_bible).first()
	trg_bibleNode = matcher.match("BIBLE",name=trg_bible).first()

	cursor.execute("Select Book, Chapter, Verse, PositionSrc, PositionTrg, UserId, Stage, Type, UpdatedOn, LidSrc, LidTrg from "+alignment_table+" JOIN Bcv_LidMap as Map ON LidSrc=Map.ID where Map.Book = %s order by LidSrc, PositionSrc",(buk))


	while(True):
		next_row = cursor.fetchone()
		# print(next_row)
		if not next_row:
			break

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
		print('BCV:',(BookNum,Chapter,Verse))

		if PositionTrg == '255' or PositionSrc == '255':
			continue

		if (LidSrc != LidTrg):
			print("Across verse alignment cannot be handled by this python script.")
			print("Found at:",(BookNum,Chapter,Verse))
			sys.exit(1)

		src_bookNode = None
		src_chapterNode = None
		src_verseNode = None
		src_wordNode = None


		trg_bookNode = None
		trg_chapterNode = None
		trg_verseNode = None
		trg_wordNode = None
		tx = graph.begin()

	
		for rel in graph.match((None,src_bibleNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==BookNum:
				src_bookNode = rel.start_node
		
		for rel in graph.match((None,trg_bibleNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==BookNum:
				trg_bookNode = rel.start_node
		
		for rel in graph.match((None,src_bookNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Chapter:
				src_chapterNode = rel.start_node
		
		for rel in graph.match((None,trg_bookNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Chapter:
				trg_chapterNode = rel.start_node
		
		for rel in graph.match((None,src_chapterNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Verse:
				src_verseNode = rel.start_node
		
		for rel in graph.match((None,trg_chapterNode), r_type="BELONGS_TO"):
			if rel.start_node["number"]==Verse:
				trg_verseNode = rel.start_node
		for rel in graph.match((None,src_verseNode), r_type="BELONGS_TO"):
				if rel.start_node["position"]==PositionSrc:
					src_wordNode = rel.start_node
		if not src_wordNode:
			print("Cannot find word node :",(BookNum,Chapter,Verse,PositionSrc))
			continue
			# raise e
		
		for rel in graph.match((None,trg_verseNode), r_type="BELONGS_TO"):
			if rel.start_node["position"]==PositionTrg:
				trg_wordNode = rel.start_node
		
		

		alignRel = Relationship(src_wordNode,"ALIGNS_TO",trg_wordNode)
		alignRel['user'] = UserId
		alignRel['type'] = Type
		alignRel['stage'] = Stage
		alignRel['updatedOn'] = UpdatedOn
		tx.create(alignRel)
		print("creating new link for:",(BookNum,Chapter,Verse,PositionSrc))

		tx.commit()
		# break
	cursor.close()
	db.close()




def add_english_wordnet():
	from nltk.corpus import wordnet as wn

	dictname = 'English Wordnet'
	dictNode = Node("DICTIONARY", name=dictname)
	
	print('Before dictNode:',dictNode)
	# tx = graph.begin()
	graph.merge(dictNode,'DICTIONARY','name')
	print('After dictNode:',dictNode)
	# tx.commit()

	matcher = NodeMatcher(graph)

	for i,word in enumerate(wn.words()):
		if i <= 10000:
			continue
		# if i>10000:
		# 	break
		try:
			# print(word)
			found_nodes = list(matcher.match('WORD',literalform=word))

			if len(found_nodes)==0:
				found_nodes = list(matcher.match('WORD',literalform=word.capitalize()))

			# print(found_nodes)
			if len(found_nodes)==0:
				continue

			wordNode = Node("WORDNET_WORD",form=word)
			graph.create(wordNode)

			word2dictRel = Relationship.type("BELONGS_TO")
			graph.create(word2dictRel(wordNode,dictNode))

			for syn in wn.synsets(word):
				synsetNode = Node("SYNSET",name=syn.name())
				synsetNode['definition'] = syn.definition()
				synsetNode['example'] = syn.examples()
				synsetNode.__primarylabel__ = "SYNSET"
				synsetNode.__primarykey__ = "name"
				graph.merge(synsetNode)

				hasSynsetRel = Relationship.type("HAS_SYNSET")
				graph.create(hasSynsetRel(wordNode,synsetNode))

				lemmas = syn.lemmas()
				for lma in lemmas:
					lemmaNode = Node("WORDNET_LEMMA",name=lma.name())
					lemmaNode.__primarylabel__ = "WORDNET_LEMMA"
					lemmaNode.__primarykey__ = "name"
					graph.merge(lemmaNode)

					hasLemmaREL = Relationship.type("HAS_LEMMA")
					graph.merge(hasLemmaREL(synsetNode,lemmaNode))

					antonyms = lma.antonyms()
					for anto in antonyms:
						antoNode = Node("WORDNET_LEMMA",name=anto.name())
						antoNode.__primarylabel__ = "WORDNET_LEMMA"
						antoNode.__primarykey__ = "name"
						graph.merge(antoNode)

						hasAntonymREL = Relationship.type("HAS_ANTONYM")
						graph.merge(hasAntonymREL(lemmaNode,antoNode))

				hypernyms = syn.hypernyms()
				for hyp in hypernyms:
					hyperNode = Node("SYNSET",name=hyp.name())
					hyperNode.__primarylabel__ = "SYNSET"
					hyperNode.__primarykey__ = "name"
					graph.merge(hyperNode)

					hashyperREL = Relationship.type("HAS_HYPERNYM")
					graph.merge(hashyperREL(synsetNode,hyperNode))

		except Exception as e:
			print('at word: ',word)
			# print('hypernyms:',hypernyms)
			raise e
		
		print("Added WORDNET_WORD: ",i,word)


	
def link_English_ULB_to_wordnet(book):
	# from nltk.corpus import stopwords
	# eng_stopwords = set(stopwords.words('english'))

	matcher = NodeMatcher(graph)

	bibleNode = matcher.match("BIBLE",name='English_ULB').first()

	for rel in graph.match((None,bibleNode), r_type="BELONGS_TO"):
		if rel.start_node["number"]==str(book):
			bookNode = rel.start_node

	chapters = [rel.start_node for rel in graph.match((None,bookNode), r_type="BELONGS_TO")]

	for chapterNode in chapters:
		verses = [rel.start_node for rel in graph.match((None,chapterNode), r_type="BELONGS_TO")]
		for verseNode in verses:
			# print(' in ',chapterNode['number'],':',verseNode['number'])
			words = [rel.start_node for rel in graph.match((None,verseNode), r_type="BELONGS_TO")]
			for wordNode in words:
				word_form = wordNode['literalform']
				word_form = word_form.lower()
				# if word_form in eng_stopwords:
				# 	continue
				wn_wordNode = matcher.match("WORDNET_WORD",form=word_form).first()
				if wn_wordNode:
					IS_WN_WORDRel = Relationship(wordNode,"IS_WN_WORD",wn_wordNode)
					graph.create(IS_WN_WORDRel)
					print('linked ',word_form)




def delete_full_graph():
	graph.delete_all()
	print('The full graph deleted!!!')



# add_strongs_dict()

# add_tw_dictionary()

# add_UGNT_bible_2neo(43)
# 41 error at 14:48
# 43 error at 8:6
# 44 error at 5:29
#
# for i in range(41,67):
# 	add_UGNT_bible_2neo(i)


# add_GL_bible_2neo('Hin_4_BibleWord',"Hindi_IRV4","Hindi",40)
# for i in range(41,67):
# 	add_GL_bible_2neo('Hin_4_BibleWord',"Hindi_IRV4","Hindi",i)

# add_GL_bible_2neo('Eng_ULB_BibleWord',"English_ULB","English",40,'Unfolding Literal Bible')
# for i in range(41,67):
# 	add_GL_bible_2neo('Eng_ULB_BibleWord',"English_ULB","English",i,'Unfolding Literal Bible')


# for i in range(41,67):
# 	add_alignment_2neo('Hindi_IRV4','UGNT4','Hin_4_Grk_UGNT4_Alignment',i)

for i in range(41,67):
	add_alignment_2neo('English_ULB','UGNT4','Eng_ULB_Grk_UGNT4_Alignment',i)



# add_english_wordnet()

# link_English_ULB_to_wordnet(40)

# delete_full_graph()

