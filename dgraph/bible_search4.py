from dGraph_conn import dGraph_conn
from flask import Flask, render_template, request
import json, requests
import regex as re
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn

from Malayalam_suffix_stripping_stemmer import stem_full_text


graph_conn = None
app = Flask(__name__)

stopWords = {'en': set(stopwords.words('english')), 'hi':[], 'ml':[]}
word_pattern = re.compile(r"\w+")

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
	}'''

allwords_query = '''
	query nodes($term:string){
	nodes(func:has(belongsTo)) 
	@filter( alloftext(verseText,$term) OR alloftext(title,$term) OR alloftext(summary,$term) OR alloftext(question,$term) OR alloftext(answer,$term))
	{
		uid,
		verseText,
		verse,belongsTo{chapter,belongsTo{book} }
		title,
		summary,
		question,
		answer,
		referenceVerse{verseText,verse,belongsTo{chapter,belongsTo{book} } }
	}}
	'''

anywords_query = '''
	query nodes($term:string){
	nodes(func:has(belongsTo)) 
	@filter( anyoftext(verseText,$term) OR anyoftext(title,$term) OR anyoftext(summary,$term) OR anyoftext(question,$term) OR anyoftext(answer,$term))
	{
		uid,
		verseText,
		verse,belongsTo{chapter,belongsTo{book} }
		title,
		summary,
		question,
		answer,
		referenceVerse{verseText,verse,belongsTo{chapter,belongsTo{book} } }
	}}
	'''


nlp = None
def try_stemming(word,lang):
	global nlp
	return_list = []
	if lang== "ml":
		return_list = stem_full_text(word)
		print("root forms:",return_list)
		return return_list[0]
	if lang=="hi":
		if nlp==None:
			import stanfordnlp
			nlp = stanfordnlp.Pipeline(processors = "tokenize,mwt,pos,lemma",model_path="/home/kavitha/stanfordnlp_resources/hi_hdtb_models/", lang="hi", short_hand="hi_hdtb")
		doc = nlp(word)
		for word in doc.sentences[0].words:
				if word.pos.startswith("V"):
					return_list.append(word.lemma+"ना")
					print(word.text,"-->",word.lemma+"ना")
				else:
					return_list.append(word.lemma)
					print(word.text,"-->",word.lemma)
		return " ".join(return_list)
	else:
		return word

def extend_queryword(word,lang='en'):
	synonyms = []
	related_words = []
	syns = []
	if lang == 'en':
		syns = wn.synsets(word)
	if len(syns) > 0: 
		for syn in syns:
			for lemma in syn.lemmas():
				if lemma.name() not in synonyms and lemma.name() not in stopWords:
					synonyms.append(lemma.name())
				for form in lemma.derivationally_related_forms():
					if form.name() not in synonyms and form.name() not in stopWords:
						synonyms.append(form.name())

			related_syns = syn.hypernyms() + syn.hyponyms() + syn.part_holonyms() + syn.part_meronyms()
			for syn in related_syns:
				for lemma in syn.lemmas():
					if lemma.name() not in related_words and lemma.name() not in stopWords:
						related_words.append(lemma.name())
					for form in lemma.derivationally_related_forms():
						if form.name() not in related_words and form.name() not in stopWords:
							related_words.append(form.name())
	else:
		obj = requests.get('http://api.conceptnet.io/c/'+lang+'/'+word).json()
		if len(obj['edges']) > 0:
			for edge in obj['edges']:
				# if edge['rel']['label'] in ['Synonym','IsA'] and edge['end']['language']==lang and edge['start']['language']==lang:
				if edge['rel']['label'] in ['Synonym','IsA']:
					if edge['end']['term'].split('/')[-1] == word:
						synonyms.append(edge['start']['term'].split('/')[-1])
					else:
						synonyms.append(edge['end']['term'].split('/')[-1])
		elif "_" not in word:
			root = try_stemming(word,lang)
			if root != word:
				synonyms,related_words = extend_queryword(root,lang)
			else:
				if lang == "hi" and not(root.endswith("ा")):
					synonyms, related_words = extend_queryword(root+"ा",lang)
					if len(synonyms)>0:
						return synonyms,related_words
				if root not in synonyms:
					synonyms.append(root)

	return synonyms, related_words

@app.route('/dgraph/search/<user_query>/',defaults={'lang':'en'}, methods=["GET"])
@app.route('/dgraph/search/<user_query>/<lang>',methods=["GET"])
def process_query(user_query,lang):
	global graph_conn

	result_verses = {}

	# QUERY ENHANCING BY SYNONYM ADDTION
	qry_words = re.findall(word_pattern,user_query)
	twoWord_combos = ["_".join(qry_words[i:i+2]) for i in range(len(qry_words)-1)]
	threeWord_combos = ["_".join(qry_words[i:i+3]) for i in range(len(qry_words)-2)]

	synonyms = []
	related_words = []
	for word in qry_words+twoWord_combos+threeWord_combos:
		if word in stopWords[lang]:
			print("ignoring:",word)
			continue
		# s_set, h_set, m_set = extend_queryword(word)
		print("extending:",word)
		s_set, more_set = extend_queryword(word,lang)
		for w in s_set:
			if w not in synonyms:
				synonyms.append(w)
		# for w in h_set+m_set:
		for w in more_set:
			if w not in related_words:
				related_words.append(w)
	print("query words:",qry_words)
	print('synonyms:',synonyms)
	# print('related_words:',related_words)

	query_len = len(qry_words)

	### Attempt whole match with query words alone
	### OR any words search including the synonyms also
	result_verses = {}
	extended_qry = qry_words+synonyms
	print("extended_qry:",extended_qry)
	query_res = graph_conn.query_data(anywords_query,{"$term":" ".join(extended_qry)})
	selected = {'score':0,"info":"","verses":[]}
	debug_count = 0
	for node in query_res['nodes']:
			if "title" in node:
				countInTitle = 0
				countInSum = 0
				for w in extended_qry:
					if re.search(w, node['title']):
						countInTitle += 1
					if re.search(w,node['summary']):
						countInSum += 1
				if countInSum/len(node['summary']) > countInTitle/len(node['title']):
					score = countInSum*countInSum/len(node['summary'])
				else:
					score = countInTitle*countInTitle/len(node['title'])
				info_text = node['title']+":"+node['summary']
				verse_list = []
				for ver in node['referenceVerse']:
					ref = ver["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(ver["belongsTo"][0]["chapter"])+":"+str(ver["verse"])
					verse_list.append((ref,ver['verseText']))
				if score > selected['score']:
					selected['score'] = score
					selected['info'] = info_text
					print(info_text)
				for ver in verse_list:
						if ver[0] in result_verses:
							result_verses[ver[0]]['score'] += score
						else: 
							result_verses[ver[0]] = {'score':score, 'verseText':ver[1]}
							debug_count += 1
			if "question" in node:
				countInQuestion = 0
				countInAnswer = 0
				for w in extended_qry:
					if re.search(w, node['question']):
						countInQuestion += 1
					if re.search(w, node['answer']):
						countInAnswer += 1
				if countInQuestion > countInAnswer:
					score = countInQuestion*countInQuestion/len(node['question'])
				else:
					score = countInAnswer*countInAnswer/len(node['answer'])
				info_text = node['answer']
				verse_list = []
				for ver in node['referenceVerse']:
					ref = ver["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(ver["belongsTo"][0]["chapter"])+":"+str(ver["verse"])
					verse_list.append((ref,ver['verseText']))
				if score > selected['score']:
					selected['score'] = score
					selected['info'] = info_text
					print(info_text)
				for ver in verse_list:
						if ver[0] in result_verses:
							result_verses[ver[0]]['score'] += score
						else: 
							result_verses[ver[0]] = {'score':score, 'verseText':ver[1]}
							debug_count += 1

			if "verseText" in node:
					ref = node["belongsTo"][0]["belongsTo"][0]["book"]+" "+str(node["belongsTo"][0]["chapter"])+":"+str(node["verse"])
					verse_list=[(ref,node['verseText'])]
					countInVerse = 0
					for w in extended_qry:
						if re.search(w,node['verseText']):
							countInVerse += 1
					score = countInVerse*countInVerse/len(node['verseText'])
					info_text = ''
					if score > selected['score']:
						selected['score'] = score
						selected['info'] = info_text
						print("info_text:","")
					for ver in verse_list:
							if ver[0] in result_verses:
								result_verses[ver[0]]['score'] += score
							else: 
								result_verses[ver[0]] = {'score':score, 'verseText':ver[1]}
								debug_count += 1
	else:
		selected = {'score':0,"info":"","verses":[]}

	print("selected:",selected['score'],selected['info'])

	sorted_result_verses = ["<br>"+ref+"&nbsp;&nbsp;&nbsp;"+val['verseText'] for ref, val in sorted(result_verses.items(), key= lambda x:x[1]['score'], reverse=True)]
	selected['verses'] = sorted_result_verses[:10]

	return json.dumps(selected,ensure_ascii=False)
	
if __name__ == '__main__':
	graph_conn = dGraph_conn()
	app.run(host='0.0.0.0', port=5000, debug=True)	