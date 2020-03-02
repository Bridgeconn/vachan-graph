from dGraph_conn import dGraph_conn
from flask import Flask, render_template, request
import pandas as pd
import re, json, requests
from sklearn.metrics.pairwise import cosine_similarity
from text_to_uri import standardized_uri
import itertools
import nltk
from nltk.stem import WordNetLemmatizer 
from nltk.corpus import stopwords

graph_conn = None
app = Flask(__name__)

conceptnetNumberBatchModel = './models/mini.h5'
cn_embeddings = pd.read_hdf(conceptnetNumberBatchModel, 'mat', encoding='utf-8')
lemmatizer = WordNetLemmatizer()
stopWords = set(stopwords.words('english'))

# search a particular concept available in the graph
# find all verses that concept is link to, either directly or 
# through linked stories, questions, answers etc
cnterm_query = '''
	query cn_term($term: string){
	verses(func:eq(cn_term,$term)){
		concept:cn_term,
		~verseEmbeddings{ verseText, verse, belongsTo{ chapter, belongsTo {book}} },
		~titleEmbeddings{ referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } },
		~questionEmbeddings{ referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } },
		~answerEmbeddings{ referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } },
		~summaryEmbeddings{ referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } },
		study_qes: ~questionEmbeddings{	~studyQuestion{ referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } } },
		study_ans: ~answerEmbeddings{ ~studyQuestion{  	referenceVerse{ verseText, verse, belongsTo{ chapter, belongsTo {book}} } } }
	}
	}
'''
tw_query ='''
	query tw($term: string){
	verses(func:eq(translationWord,$term)){
  concept:translationWord,
  ~tw{ word,belongsTo{verse,belongsTo{chapter,belongsTo{ book } } } }
}}
'''
verseText_query = '''
	query text($bible:string, $book:string, $chapter:int, $verse:int){
	text(func:eq(bible,$bible))@cascade @normalize{
		~belongsTo @filter(eq(book,$book)){
		 ~belongsTo @filter(eq(chapter,$chapter)){
		  ~belongsTo @filter(eq(verse,$verse)){
		  	verseText:verseText
		}}}	}
	}
'''

def concept_finder(text):
	text_words = re.findall(r'\w+',text)
	text_words = [word.lower() for word in text_words]

	# all one-word, two_word and three_word slices
	possible_concepts = []
	possible_concepts += [' '.join(text_words[i:i+3]) for i in range(len(text_words)-2)]
	possible_concepts += [' '.join(text_words[i:i+2]) for i in range(len(text_words)-1)]
	possible_concepts += text_words
	for word in text_words:
		lemma = lemmatizer.lemmatize(word)
		if lemma not in possible_concepts and lemma not in stopWords:
			possible_concepts.append(lemma)
	for sw in list(stopWords)+["jesus"]:
		if sw in possible_concepts:
			possible_concepts.remove(sw)

	# find the available conceptnet UIRs.
	# if a multi-word concept is available, its component words should be exculded 
	# unless it is present again, separately in the text 
	possible_uris = [standardized_uri('en',phrase) for phrase in possible_concepts]
	valid_concepts = []
	# print("possible_uris:",possible_uris)
	added = []
	for uri in possible_uris:
			if uri in added:
				continue
			try:
				vec = cn_embeddings.loc[uri]
				phrase = uri.replace('/c/en/','')
				valid_concepts.append(phrase)
				# to remove component concepts
				words = phrase.split("_")
				phrase_components = []
				phrase_components += ['_'.join(words[i+2]) for i in range(len(words)-1)]
				phrase_components += words
				for comp in phrase_components:
					if '/c/en/'+comp in possible_uris:
						added.append('/c/en/'+comp)
						# print("removing:",'/c/en/'+comp)
			except Exception as e:
				# print("misshit at conceptnet:",uri)
				pass
	# print("valid_concepts:",valid_concepts)
	return valid_concepts,possible_concepts

@app.route('/dgraph/search/<user_query>',methods=["GET"])
def process_query(user_query):
	global graph_conn
	query_concepts,all_possible_concepts = concept_finder(user_query)
	# print('query_concepts:',query_concepts)

	# find synonyms from conceptnet
	extended_query_concepts = []
	for con in query_concepts:
		obj = requests.get('http://api.conceptnet.io/c/en/'+con).json()
		for edge in obj['edges']:
			if edge['rel']['label'] in ['Synonym','IsA'] and edge['end']['language']=='en' and edge['start']['language']=='en':
				if edge['end']['term'].split('/')[-1] == con:
					extended_query_concepts.append(edge['start']['term'].split('/')[-1])
				else:
					extended_query_concepts.append(edge['end']['term'].split('/')[-1])
	for con in query_concepts:
		if con not in extended_query_concepts:
			extended_query_concepts.append(con)
	print('extended_query_concepts:',extended_query_concepts)

	all_res_verses = {}

	# search based on concept net links in DB
	for concept in extended_query_concepts:
		weight = 1
		for char in concept:
			if char == "_":
				weight +=1
		cnterm_query_res = graph_conn.query_data(cnterm_query,{"$term":concept})
		verse_list = []
		# print('extended query concept:',concept)
		for res in cnterm_query_res['verses']:
			if "~verseEmbeddings" in res:
				for ver in res["~verseEmbeddings"]:
					verse_list.append(ver)
			if "~titleEmbeddings" in res:
				for reflist in res["~titleEmbeddings"]:
					for ver in reflist['referenceVerse']:
						verse_list.append(ver)
			if "~summaryEmbeddings" in res:
				for reflist in res["~summaryEmbeddings"]:
					for ver in reflist['referenceVerse']:
						verse_list.append(ver)
			if "~questionEmbeddings" in res:
				for reflist in res["~questionEmbeddings"]:
					if 'referenceVerse' not in reflist:
						break
					for ver in reflist['referenceVerse']:
						verse_list.append(ver)
			if "~answerEmbeddings" in res:
				for reflist in res["~answerEmbeddings"]:
					if 'referenceVerse' not in reflist:
						break
					for ver in reflist['referenceVerse']:
						verse_list.append(ver)
			for ver in verse_list:
				ref = ver["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(ver["belongsTo"][0]["chapter"])+":"+str(ver["verse"])
				text = ver["verseText"]
				if ref in all_res_verses:
					all_res_verses[ref]["count"] += weight
				else:
					all_res_verses[ref] = {"count":weight,"text":text}

	# search based on translationWord links in Greek bible
	for concept in all_possible_concepts:
		weight = 1
		for char in concept:
			if char == " ":
				weight +=1
		con_in_twFormat = concept.lower().replace(" ","")
		tw_query_res = graph_conn.query_data(tw_query,{"$term":con_in_twFormat})
		for res in tw_query_res['verses']:
			if "~tw" in res:
				print("tw match:",res['concept'])
				for wrd_nod in res["~tw"]:
					ref = wrd_nod["belongsTo"][0]["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(wrd_nod["belongsTo"][0]["belongsTo"][0]["chapter"])+":"+str(wrd_nod["belongsTo"][0]["verse"])
					if ref in all_res_verses:
						all_res_verses[ref]["count"] += weight
					else:
						text = ""
						variables = {
							"$bible":"Eng ULB bible",
							"$book":wrd_nod["belongsTo"][0]["belongsTo"][0]["belongsTo"][0]["book"],
							"$chapter":str(wrd_nod["belongsTo"][0]["belongsTo"][0]["chapter"]),
							"$verse":str(wrd_nod["belongsTo"][0]["verse"])
						}
						verseText_query_res = graph_conn.query_data(verseText_query,variables)
						if len(verseText_query_res['text'])==1:
							text = verseText_query_res['text'][0]["verseText"]
						all_res_verses[ref] = {"count":weight,"text":text}

	sorted_verses = { k:v   for k,v in sorted(all_res_verses.items(), key=lambda x: x[1]["count"], reverse=True)}
	result = ''
	prev_count = 0
	for i,k in enumerate(sorted_verses):
		if i < 6:
			result += "<br>"+ k + "&nbsp;" + sorted_verses[k]['text']
		elif sorted_verses[k]['count'] == prev_count and i < 20:
			result += "<br>"+ k + "&nbsp;" + sorted_verses[k]['text']
		else:
			break
		prev_count = sorted_verses[k]['count']


	return json.dumps(result)

if __name__ == '__main__':
	# global graph_conn
	graph_conn = dGraph_conn()

	app.run(host='0.0.0.0', port=5000, debug=True)
	# app.run(debug=True)
	# process_query("Peter sinks")
