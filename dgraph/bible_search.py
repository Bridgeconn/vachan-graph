from dGraph_conn import dGraph_conn
from flask import Flask, render_template, request
import pandas as pd
import re, json
from sklearn.metrics.pairwise import cosine_similarity
from text_to_uri import standardized_uri
import itertools

graph_conn = None
min_threshold = 0

app = Flask(__name__)

alltw_query = '''
	query tws($lang:string){
	tws(func:has(translationWord)){
	 translationWord
	}	}
'''

allquestions_query = '''
	query questions($lang:string){
	questions(func: has(question)){
  		question,
  		questionEmbeddings{
  		cn_term },
	    referenceVerse{
	      verse,
    	  belongsTo{
        	chapter,
        	belongsTo{
        	book } }  },
        ~studyQuestion{
   	    referenceVerse{
	      verse,
    	  belongsTo{
        	chapter,
        	belongsTo{
        	book } }  }
        }
  		}	}
'''

allanswers_query = '''
	query answers($lang:string){
	answers(func: has(answer)){
		answer,
		answerEmbeddings{
  		cn_term },
	    referenceVerse{
	      verse,
    	  belongsTo{
        	chapter,
        	belongsTo{
        	book } }  },
        ~studyQuestion{
	   	    referenceVerse{
		      verse,
	    	  belongsTo{
	        	chapter,
	        	belongsTo{
	        	book } }  }
        }

	}	}
'''

alltitles_query = '''
	query titles($lang:string){
	titles(func: has(title)){
		title,
		titleEmbeddings {
  		cn_term	},
	    referenceVerse{
	      verse,
    	  belongsTo{
        	chapter,
        	belongsTo{
        	book } }  }
	}	}
'''
bcv_query = '''
	query verse($book:string, $chapter:int, $verse:int){
	verse(func: eq(bible,"Eng ULB bible")) @normalize @cascade{
		~belongsTo @filter(eq(book,$book)){
		 ~belongsTo @filter(eq(chapter,$chapter)){
		 	~belongsTo @filter(eq(verse,$verse)){
		 		verseText: verseText
	}}}}}
'''




word_score = None
all_tws = None
all_titles = None
all_questions = None
all_answers = None

def initialize_search():
	global graph_conn
	global word_score
	global all_tws, all_titles, all_questions, all_answers
	graph_conn = dGraph_conn()

	# collect all text fields used for searching in the Graph DB
	# eq:translation words, story titles, questions, Answers etc
	# To start with only fetch English contents
	all_text_fields = []
	alltw_query_res  = graph_conn.query_data(alltw_query,{'$lang':"English"})
	all_tws = alltw_query_res['tws']
	all_text_fields += [item['translationWord'] for item in all_tws]
	alltitles_query_res  = graph_conn.query_data(alltitles_query,{'$lang':"English"})
	all_titles = alltitles_query_res['titles']
	all_text_fields += [item['title'] for item in all_titles]
	allquestions_query_res  = graph_conn.query_data(allquestions_query,{'$lang':"English"})
	all_questions = allquestions_query_res['questions']
	all_text_fields += [item['question'] for item in all_questions]
	allanswers_query_res  = graph_conn.query_data(allanswers_query,{'$lang':"English"})
	all_answers = allanswers_query_res['answers']
	all_text_fields += [item['answer'] for item in all_answers]

	all_text_fields = " ".join(all_text_fields)

	# calculate the score of each unique word in above contents
	# based on increasing order of frequency
	# ie. least frequent word will have highest score
	# this is to be used as weights in scoring the query results
	word_rank = {}
	all_text_words = re.findall(r'\w+',all_text_fields)
	for word in all_text_words:
		word = word.lower()
		if word in word_rank:
			word_rank[word] += 1
		else:
			word_rank[word] = 1
	sorted_words = sorted(word_rank.items(),key=lambda x :x[1],reverse=True)	
	word_score = {}
	score = 0
	prev_freq = 0
	for tup in sorted_words:
		if tup[1] != prev_freq:
			score += 1
			prev_freq = tup[1]
		word_score[tup[0]] = score
	# print(word_score)


conceptnetNumberBatchModel = './models/mini.h5'
cn_embeddings = pd.read_hdf(conceptnetNumberBatchModel, 'mat', encoding='utf-8')
def concept_finder(text):
	text_words = re.findall(r'\w+',text)
	text_words = [word.lower() for word in text_words]

	# all one-word, two_word and three_word slices
	possible_concepts = []
	possible_concepts += [' '.join(text_words[i:i+3]) for i in range(len(text_words)-2)]
	possible_concepts += [' '.join(text_words[i:i+2]) for i in range(len(text_words)-1)]
	possible_concepts += text_words

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
				valid_concepts.append((phrase,vec))
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
	return valid_concepts



def similary_distance(query_concepts,text_concepts):
	score = 0
	# print("\n\nNext text")
	cosine_sim_sum = 0
	for qry_concept,txt_concept in itertools.product(query_concepts,text_concepts):
		# normalized similary value between 0 and 1
		qry_vec = qry_concept[1]
		txt_vec = txt_concept[1]
		cos_sim = cosine_similarity([qry_vec],[txt_vec])
		# print(qry_concept[0],txt_concept[0],cos_sim)

		text_words = txt_concept[0].split("_")
		# calculate the weighted sum
		for wrd in text_words:
			if wrd in word_score:
				# print(wrd,":",word_score[wrd])
				cosine_sim_sum += cos_sim[0][0]*word_score[wrd]/100  
	# normalizing with length of the matched text(or number of concepts present in the matched text)
	if(len(text_concepts)>0):
		cosine_sim_sum = cosine_sim_sum/len(text_concepts)
	return cosine_sim_sum

def consolidate_result(list_of_verselists):
	# consolidate all the results lists
	# by choosing the most selected 10 verses
	# if we dont have enough common verses in the lists,
	# then do a bruteforce
	verse_vote = {}
	length = len(list_of_verselists)
	for i,verselist in enumerate(list_of_verselists):
		refs = verselist[2]
		# print(refs)
		for verse in refs:
			if verse in verse_vote:
				print(length-i)
				verse_vote[verse] += length-i
			else:
				print(length-i)
				verse_vote[verse] = length-i
	sorted_verseList = [(v,verse_vote[v])  for v in sorted(verse_vote, key=verse_vote.get, reverse=True)]
	# print(sorted_verseList[:10])
	return sorted_verseList[:10]





def process_query(user_query):
	global all_tws, all_titles, all_questions, all_answers

	# Obtain the vector similary of query with indicator texts in the DB
	# like titles, questions etc
	# find the list of verses they refer to
	query_concepts = concept_finder(user_query)

	# find synonyms from conceptnet
	extended_query_concepts = []
	query_concepts += extended_query_concepts

	selected_sim_scores = []

	# print(all_titles)
	sim_scores = []
	for item in all_titles:
		text_concepts = [(con['cn_term'],cn_embeddings.loc['/c/en/'+con['cn_term']]) for con in item['titleEmbeddings']]
		references = []
		for ref in item["referenceVerse"]:
			# print('ref:',ref)
			ref_text = ref['belongsTo'][0]["belongsTo"][0]['book']+ " " + str(ref['belongsTo'][0]["chapter"]) + ":"+ str(ref['verse'])
			references.append(ref_text)
		sim_scores.append((item['title'],similary_distance(query_concepts,text_concepts),references ))
	sorted_sim_scores = sorted(sim_scores, key=lambda x:x[1], reverse=True)
	selected_sim_scores = sorted_sim_scores[:3]
	# for tup in sim_scores:
	# 	print(tup)
	# sorted_sim_scores = []
	# top10_verses_trial1 = []

	sim_scores = []
	for item in all_questions:
			text_concepts = [(con['cn_term'],cn_embeddings.loc['/c/en/'+con['cn_term']]) for con in item['questionEmbeddings']]
			references = []
			if "referenceVerse" in item:
				ref_list = item["referenceVerse"]
			else:
				ref_list = item["~studyQuestion"][0]["referenceVerse"]
			for ref in ref_list:
				ref_text = ref['belongsTo'][0]["belongsTo"][0]['book']+ " " + str(ref['belongsTo'][0]["chapter"]) + ":"+ str(ref['verse'])
				references.append(ref_text)
			sim_scores.append((item['question'],similary_distance(query_concepts,text_concepts),references ))
	sorted_sim_scores = sorted(sim_scores, key=lambda x:x[1], reverse=True)
	selected_sim_scores += sorted_sim_scores[:10]
	# sorted_sim_scores = []
	# top10_verses_trial2 = []


	sim_scores = []
	for item in all_answers:
			text_concepts = [(con['cn_term'],cn_embeddings.loc['/c/en/'+con['cn_term']]) for con in item['answerEmbeddings']]
			references = []
			if "referenceVerse" in item:
				ref_list = item["referenceVerse"]
			else:
				ref_list = item["~studyQuestion"][0]["referenceVerse"]
			for ref in ref_list:
				ref_text = ref['belongsTo'][0]["belongsTo"][0]['book']+ " " + str(ref['belongsTo'][0]["chapter"]) + ":"+ str(ref['verse'])
				references.append(ref_text)
			sim_scores.append((item['answer'],similary_distance(query_concepts,text_concepts), references ))
	sorted_sim_scores = sorted(sim_scores, key=lambda x:x[1], reverse=True)
	selected_sim_scores += sorted_sim_scores[:10]
	# sorted_sim_scores = []
	# top10_verses_trial3 = []


	# sim_scores += [ (item['translationWord'],similary_distance(query_concepts,concept_finder(item['translationWord']))) for item in all_tws]
	# sorted_sim_scores = []
	# top10_verses_trial4 = []

	sorted_sim_scores = sorted(selected_sim_scores, key=lambda x:x[1])
	# print(sorted_sim_scores)
	result_str = ""
	# find the top 10 verses from all the different search schemes
	top10_verses = consolidate_result(sorted_sim_scores)
	for res in top10_verses:
		book = res[0].split(' ')[0]
		chapter_verse = res[0].split(' ')[1]
		chapter, verse = chapter_verse.split(":")
		variable = {'$book':book, "$chapter":chapter, "$verse":verse}
		bcv_query_res = graph_conn.query_data(bcv_query,variable)
		if len(bcv_query_res['verse'])==1:
			result_str += res[0] + ":&nbsp;"+bcv_query_res['verse'][0]['verseText']+"<br>"
		else:
			result_str += res[0] + ":&nbsp;"+"not in this db"+"<br>"

	return json.dumps(result_str)

@app.route('/dgraph/search/<query>',methods=["GET"])
def addBibleStories(query):
	res = process_query(query)
	return res


if __name__ == '__main__':
	initialize_search()
	app.run(host='0.0.0.0', port=5000, debug=True)

	# concepts1 = concept_finder("Mary and Martha's stroy was always a huge sensation.")
	# concepts2 = concept_finder("Jesus was crucified")
	# concepts3 = concept_finder("Jesus saved the sinners")
	# print(concepts)

	# print("1 and 2:",similary_distance(concepts1,concepts2))
	# print("1 and 3:",similary_distance(concepts1,concepts3))
	# print("2 and 3:",similary_distance(concepts2,concepts3))

	# process_query("The duty of a good servant")
	# process_query("The devil tests the Lord") # Satan tempts Jesus
	# process_query("Jesus comes back from the Dead")
	# process_query("John is born")	# The birth of John
	# process_query("solitude")
	# process_query("The miracle of feeding thousands of people") # Jesus Feeds Five Thousand People

	######### Checking sorting of results ###############
	# process_query("small seed big tree") # good result
	# process_query("Jesus raises Lazarus from dead") # good result
	# process_query("John's Food in desert") # not on top but in first 10
	# process_query("time of crucifixion") # okay answer
	# process_query("Jesus cooking") # not satisfactory
	# process_query("Poor widow's offering") # good result
	# process_query("sowing seeds") # good result
	# process_query("Who deserves the kingdom of God") # okay result
	# process_query("Jesus angry in temple")
	# process_query("Peter drowning") # not on top but in first 10