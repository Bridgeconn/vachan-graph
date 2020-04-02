from dGraph_conn import dGraph_conn
from flask import Flask, render_template, request
import re, json, requests
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn

graph_conn = None
app = Flask(__name__)

stopWords = set(stopwords.words('english'))
word_pattern = re.compile(r"\w+")

syn_based_query = ''' query syn_verses($syn: string){
	syn_verses(func: eq(synonym_set,$syn)) @normalize{
 		~synset{
	    wordLinkCount:count(~wordnet_link),
			~wordnet_link {
    		matchWord:word,
    		belongsTo{
					verseNum:verse,
					verseText:verseText,
					belongsTo{
						chapter:chapter,
						belongsTo{
							book:book,
							belongsTo{
							 bible
}	}	}	}	}	}	}	}

'''

lemma_based_query = ''' query lemma_verses($lemma: string){
	syn_verses(func: eq(wn_lemma,$lemma)) @normalize{
		~root{
 		~synset{
	    wordLinkCount:count(~wordnet_link),
			~wordnet_link {
    		matchWord:word,
    		belongsTo{
					verseNum:verse,
					verseText:verseText,
					belongsTo{
						chapter:chapter,
						belongsTo{
							book:book,
							belongsTo{
							 bible
}	}	}	}	}	}	}	}	}

'''


def concept_based_StoryQuery2(term_array):
	qry_template = '''
	query cn_term($term: string){
	verses(func:eq(cn_term,%s)){
		concept:cn_term,
		~titleEmbeddings{infoText:summary, matchText: title, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
		~summaryEmbeddings{infoText:summary, matchText: summary, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
	    a as count(~verseEmbeddings),
	    b as count(~titleEmbeddings),
	    c as count(~questionEmbeddings),
	    d as count(~answerEmbeddings),
	    e as count(~summaryEmbeddings),
	    conceptLinkCount: math(a+b+c+d+e),

	}
		}
	''' % term_array
	return qry_template


concept_based_StoryQuery = '''
	query cn_term($term: string_array){
	verses(func:eq(cn_term,$term)){
		concept:cn_term,
		~titleEmbeddings{infoText:summary, matchText: title, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
		~summaryEmbeddings{infoText:summary, matchText: summary, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
	    a as count(~verseEmbeddings),
	    b as count(~titleEmbeddings),
	    c as count(~questionEmbeddings),
	    d as count(~answerEmbeddings),
	    e as count(~summaryEmbeddings),
	    conceptLinkCount: math(a+b+c+d+e),

}
	}
'''

concept_based_QAquery = '''
	query cn_term($term: [string]){
	verses(func:eq(cn_term,"widow")){
		concept:cn_term,
		~questionEmbeddings{infoText:answer, matchText:question, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
		~answerEmbeddings{infoText:answer, matchText:answer, referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } },
		study_qes: ~questionEmbeddings{infoText:answer,matchText:question,  ~studyQuestion{ referenceVerse {  verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } } },
		study_ans: ~answerEmbeddings{infoText:answer, matchText:answer, ~studyQuestion{  	referenceVerse { verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} } } },
	    a as count(~verseEmbeddings),
	    b as count(~titleEmbeddings),
	    c as count(~questionEmbeddings),
	    d as count(~answerEmbeddings),
	    e as count(~summaryEmbeddings),
	    conceptLinkCount: math(a+b+c+d+e),

}
	}
'''


concept_based_verseQuery = '''
	query cn_term($term: [string]){
	verses(func:eq(cn_term,"widow")){
		concept:cn_term,
		~verseEmbeddings{verseText:verseText, verse:verse, belongsTo{ chapter:chapter, belongsTo {book:book}} },
	    a as count(~verseEmbeddings),
	    b as count(~titleEmbeddings),
	    c as count(~questionEmbeddings),
	    d as count(~answerEmbeddings),
	    e as count(~summaryEmbeddings),
	    conceptLinkCount: math(a+b+c+d+e),

}
	}
'''


def extend_queryword(word):
	synonyms = []
	hyper_hypo_nyms = []
	mero_holo_nyms = []

	syns = wn.synsets(word)
	for syn in syns:
		if syn.name() not in synonyms:
			synonyms.append(syn.name())
		
		hypernyms = syn.hypernyms()
		for hyp in hypernyms:
				if hyp.name() not in hyper_hypo_nyms:
					hyper_hypo_nyms.append(hyp.name())
		hyponyms = syn.hyponyms()
		for hyp in hyponyms:
				if hyp.name() not in hyper_hypo_nyms:
					hyper_hypo_nyms.append(hyp.name())

		part_holonyms = syn.part_holonyms()
		for hyp in part_holonyms:
				if hyp.name() not in hyper_hypo_nyms:
					mero_holo_nyms.append(hyp.name())
		part_meronyms = syn.part_meronyms()
		for hyp in part_meronyms:
				if hyp.name() not in hyper_hypo_nyms:
					mero_holo_nyms.append(hyp.name())
	return synonyms, hyper_hypo_nyms, mero_holo_nyms

def extend_queryword2(word):
	synonyms = []
	related_words = []
	# print("word:",word)
	syns = wn.synsets(word)
	for syn in syns:
		# print("\tsyn:",syn.name())
		for lemma in syn.lemmas():
			# print("\t\tlemma:",lemma.name())
			if lemma.name() not in synonyms:
				synonyms.append(lemma.name())
			for form in lemma.derivationally_related_forms():
				# print("\t\t\tform:",form.name())
				if form.name() not in synonyms:
					synonyms.append(form.name())

		related_syns = syn.hypernyms() + syn.hyponyms() + syn.part_holonyms() + syn.part_meronyms()
		for syn in related_syns:
			# print("\tsyn:",syn.name())
			for lemma in syn.lemmas():
				# print("\t\tlemma:",lemma.name())
				if lemma.name() not in related_words:
					related_words.append(lemma.name())
				for form in lemma.derivationally_related_forms():
					# print("\t\t\tform:",form.name())
					if form.name() not in related_words:
						related_words.append(form.name())
	return synonyms, related_words

@app.route('/dgraph/search/<user_query>',methods=["GET"])
def process_query(user_query):
	global graph_conn

	result_verses = {}

	# QUERY ENHANCING BY SYNONYM ADDTION
	qry_words = re.findall(word_pattern,user_query)
	twoWord_combos = ["_".join(qry_words[i:i+2]) for i in range(len(qry_words)-1)]
	threeWord_combos = ["_".join(qry_words[i:i+3]) for i in range(len(qry_words)-2)]

	synonyms = []
	related_words = []
	for word in qry_words+twoWord_combos+threeWord_combos:
		if word in stopWords:
			print("ignoring:",word)
			continue
		# s_set, h_set, m_set = extend_queryword(word)
		s_set, more_set = extend_queryword2(word)
		for w in s_set:
			if w not in synonyms:
				synonyms.append(w)
		# for w in h_set+m_set:
		for w in more_set:
			if w not in related_words:
				related_words.append(w)
	print('synonyms:',synonyms)
	print('related_words:',related_words)


	# WORDNET BASED VERSE FETCH
	for val in synonyms:
		# syn_based_query_res = graph_conn.query_data(syn_based_query,{"$syn":val})
		syn_based_query_res = graph_conn.query_data(lemma_based_query,{"$lemma":val})
		for verse in syn_based_query_res['syn_verses']:
			ref = verse['book']+" "+ str(verse['chapter'])+ ":"+ str(verse['verseNum'])
			weight = 1/verse['wordLinkCount']
			if ref in result_verses:
				text = result_verses[ref]['text'].replace(verse['matchWord'],"<b>"+verse['matchWord']+"</b>")
				text = text.replace('<b><b>','<b>')
				text = text.replace('</b></b>','</b>')
				result_verses[ref]['text'] = text
				result_verses[ref]['weight'] += weight
			else:
				text = verse['verseText'].replace(verse['matchWord'],"<b>"+verse['matchWord']+"</b>")
				result_verses[ref] = {'text': text, 'weight': weight}
	# for val in related_words:
	# 	# syn_based_query_res = graph_conn.query_data(syn_based_query,{"$syn":val})
	# 	syn_based_query_res = graph_conn.query_data(lemma_based_query,{"$lemma":val})
	# 	for verse in syn_based_query_res['syn_verses']:
	# 		ref = verse['book']+" "+ str(verse['chapter'])+ ":"+ str(verse['verseNum'])
	# 		weight = 0.5/verse['wordLinkCount']
	# 		if ref in result_verses:
	# 			text = result_verses[ref]['text'].replace(verse['matchWord'],"<b>"+verse['matchWord']+"</b>")
	# 			text = text.replace('<b><b>','<b>')
	# 			text = text.replace('</b></b>','</b>')
	# 			result_verses[ref]['text'] = text
	# 			result_verses[ref]['weight'] += weight
	# 		else:
	# 			text = verse['verseText'].replace(verse['matchWord'],"<b>"+verse['matchWord']+"</b>")
	# 			result_verses[ref] = {'text': text, 'weight': weight}

	

	# # CONCEPTNET BASED VERSE FETCH
	# # Try stroies
	# print("synonyms:",synonyms)
	# concept_based_query_res = graph_conn.query_data(concept_based_StoryQuery2(json.dumps(synonyms)),{"$term":str(synonyms)})
	# verse_list = []
	# topWeight = 0
	# story = ''
	# print(concept_based_query_res)
	# for res in concept_based_query_res['verses']:
	# 		print(res)
	# 		matchWord = res['concept'] 
	# 		conceptCount = res['conceptLinkCount']
	# 		if "~titleEmbeddings" in res:
	# 			for reflist in res["~titleEmbeddings"]:
	# 				matchText = reflist['matchText']
	# 				infoText = reflist['infoText']
	# 				weight = 1/(conceptCount*len(matchText))
	# 				if weight>topWeight:
	# 					story = matchText
	# 					verse_list = []
	# 					topWeight = weight
	# 					for ver in reflist['referenceVerse']:
	# 						verse_list.append((ver,weight, infoText))
	# 		if "~summaryEmbeddings" in res:
	# 			for reflist in res["~summaryEmbeddings"]:
	# 				matchText = reflist['matchText']
	# 				infoText = reflist['infoText']
	# 				weight = 1/(conceptCount*len(matchText))
	# 				if weight>topWeight:
	# 					verse_list = []
	# 					topWeight = weight
	# 					story = matchText
	# 					for ver in reflist['referenceVerse']:
	# 						verse_list.append((ver,weight, infoText))
	# print("user_query:",user_query)
	# print("weight:", topWeight)
	# print("matched story:",story)
			


			# if "~verseEmbeddings" in res:
			# 	for ver in res["~verseEmbeddings"]:
			# 		matchText = ver['matchText']
			# 		weight = 1/(conceptCount*len(matchText))
			# 		verse_list.append((ver,weight,matchText))
			# if "~questionEmbeddings" in res:
			# 	for reflist in res["~questionEmbeddings"]:
			# 		matchText = reflist['matchText']
			# 		weight = 1/(conceptCount*len(matchText))
			# 		if 'referenceVerse' not in reflist:
			# 			break
			# 		for ver in reflist['referenceVerse']:
			# 			verse_list.append((ver,weight,matchText))
			# if "~answerEmbeddings" in res:
			# 	for reflist in res["~answerEmbeddings"]:
			# 		matchText = reflist['matchText']
			# 		weight = 1/(conceptCount*len(matchText))
			# 		if 'referenceVerse' not in reflist:
			# 			break
			# 		for ver in reflist['referenceVerse']:
			# 			verse_list.append((ver,weight,matchText))
	# for v in verse_list:
	# 			ver = v[0]
	# 			weight = v[1]
	# 			info = v[2]
	# 			ref = ver["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(ver["belongsTo"][0]["chapter"])+":"+str(ver["verse"])
	# 			if ref in result_verses:
	# 				text = re.sub(matchWord,"<b>"+matchWord+"</b>", result_verses[ref]['text'])
	# 				# text = result_verses[ref]['text'].replace(matchWord,"<b>"+matchWord+"</b>")
	# 				text = text.replace('<b><b>','<b>')
	# 				text = text.replace('</b></b>','</b>')
	# 				result_verses[ref]['text'] = text
	# 				result_verses[ref]["weight"] += weight
	# 			else:
	# 				text = re.sub(matchWord,"<b>"+matchWord+"</b>", ver["verseText"])
	# 				# text = ver["verseText"].replace(matchWord,'<b>'+matchWord+'</b>')
	# 				result_verses[ref] = {"weight":weight,"text":text}


	# RANKING BASED ON CONCEPTBORROWED FROM PAGERANK
	sorted_result = {}
	for k,v in sorted(result_verses.items(), key = lambda x: x[1]['weight']*x[1]['text'].count("</b>"), reverse=True):
		sorted_result[k] = v['text']
	return json.dumps(sorted_result)





if __name__ == '__main__':
	graph_conn = dGraph_conn()
	app.run(host='0.0.0.0', port=5000, debug=True)

	# synset, hyper_hypo_set, mero_holo_set = extend_queryword("drown_in")
	# print(" synset:",synset,"\n hyper_hypo_set:",hyper_hypo_set,"\n mero_holo_set:",mero_holo_set)

	# process_query("Hello and welcome to get up")

	# main_words, related_words = extend_queryword2('test')
	# print("main_words:",main_words, "\nrelated_words:",related_words)