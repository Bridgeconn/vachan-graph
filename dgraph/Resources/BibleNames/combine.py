import json, re
# import difflib
import difflib, Levenshtein, distance
import ubs_xlm_parser



bookmap = { "genesis": 1,  "exodus": 2,  "leviticus": 3,  "numbers": 4,  "deuteronomy": 5,  "joshua": 6,  "judges": 7,  "ruth": 8,  "1 samuel": 9,  "2 samuel": 10,  "1 kings": 11,  "2 kings": 12,  "1 chronicles": 13,  "2 chronicles": 14,  "ezra": 15,  "nehemiah": 16,  "esther": 17,  "job": 18,  "psalms": 19,  "proverbs": 20,  "ecclesiastes": 21,  "song of solomon": 22,  "isaiah": 23,  "jeremiah": 24,  "lamentations": 25,  "ezekiel": 26,  "daniel": 27,  "hosea": 28,  "joel": 29,  "amos": 30,  "obadiah": 31,  "jonah": 32,  "micah": 33,  "nahum": 34,  "habakkuk": 35,  "zephaniah": 36,  "haggai": 37,  "zechariah": 38,  "malachi": 39,  "matthew": 40,  "mark": 41,  "luke": 42,  "john": 43,  "acts": 44,  "romans": 45,  "1 corinthians": 46,  "2 corinthians": 47,  "galatians": 48,  "ephesians": 49,  "philippians": 50,  "colossians": 51,  "1 thessalonians": 52,  "2 thessalonians": 53,  "1 timothy": 54,  "2 timothy": 55,  "titus": 56,  "philemon": 57,  "hebrews": 58,  "james": 59,  "1 peter": 60,  "2 peter": 61,  "1 john": 62,  "2 john": 63,  "3 john": 64,  "jude": 65,  "revelation": 66,  "psalm": 19,  "gen": 1,  "exo": 2,  "lev": 3,  "num": 4,  "deu": 5,  "jos": 6,  "jdg": 7,  "rut": 8,  "1sa": 9,  "2sa": 10,  "1ki": 11,  "2ki": 12,  "1ch": 13,  "2ch": 14,  "ezr": 15,  "neh": 16,  "est": 17,  "job": 18,  "psa": 19,  "pro": 20,  "ecc": 21,  "sng": 22,  "isa": 23,  "jer": 24,  "lam": 25,  "ezk": 26,  "dan": 27,  "hos": 28,  "jol": 29,  "amo": 30,  "oba": 31,  "jon": 32,  "mic": 33,  "nam": 34,  "hab": 35,  "zep": 36,  "hag": 37,  "zec": 38,  "mal": 39,  "mat": 40,  "mrk": 41,  "luk": 42,  "jhn": 43,  "act": 44,  "rom": 45,  "1co": 46,  "2co": 47,  "gal": 48,  "eph": 49,  "php": 50,  "col": 51,  "1th": 52,  "2th": 53,  "1ti": 54,  "2ti": 55,  "tit": 56,  "phm": 57,  "heb": 58,  "jas": 59,  "1pe": 60,  "2pe": 61,  "1jn": 62,  "2jn": 63,  "3jn": 64,  "jud": 65,  "rev": 66,  "psa": 19 }


ref_pattern = re.compile('(\d* ?\w+) +(\d+) *: *(\d+\w*)')
def convert_ref2tuple(ref_string):
	match_obj = re.match(ref_pattern, ref_string)
	if match_obj:
		book = match_obj.group(1)
		chapter = int(match_obj.group(2))
		verse = int(match_obj.group(3))
		booknum = bookmap[book.lower()]
		return ((booknum,chapter,verse))
	else:
		# print("RE Error: cannot parse reference", ref_string)
		# process.exit(-1)
		return (0,0,0)

def jaccard_similarity(list1, list2):
	s1 = set(list1)
	s2 = set(list2)
	score = len(s1.intersection(s2)) / len(s1.union(s2))
	return score

def try_exact_name_match(factgrid_names, ubs_names):
	ubs_names_temp = ubs_names
	factgrid_names_temp = factgrid_names
	confident_list = []
	ref_doubtfully_combined = []
	nameOnly_fully_matched = []
	for f_name in factgrid_names:
		# try exact match of labels
		found = False
		ubs_names = ubs_names_temp
		for ubs_name in ubs_names:
			if f_name['PersonLabel'].strip().lower() == ubs_name['name'].strip().lower():
				# confirm with occurance comparisons
				f_occurs = convert_ref2tuple(f_name['notedLabel'])
				for occ in ubs_name['occurances']:
					if (f_occurs[0],f_occurs[1]) == (occ[0],occ[1]):
						# print('matched:',f_name['PersonLabel'],' and ', ubs_name['name'], ' with ', f_name['notedLabel'], ' and ', occ)
						confident_list.append((f_name,"name and ref",ubs_name))
						factgrid_names_temp.remove(f_name)
						ubs_names_temp.remove(ubs_name)
						found = True
						break
					elif (f_occurs[0],f_occurs[1]) == (occ[0],occ[2]):
						# print('matched with doubt:',f_name['PersonLabel'],' and ', ubs_name['name'], ' with ', f_name['notedLabel'], ' and ', occ)
						ref_doubtfully_combined.append((f_name,"name, but ref swapped",ubs_name))
						factgrid_names_temp.remove(f_name)
						ubs_names_temp.remove(ubs_name)
						found = True
						break
				if not found:
						# print("Ref ", f_name['notedLabel'], " not in ", ubs_name['occurances'])
						nameOnly_fully_matched.append((f_name,"name only",ubs_name))
						factgrid_names_temp.remove(f_name)
						ubs_names_temp.remove(ubs_name)
						found = True
			if found:
				break
	return confident_list+ref_doubtfully_combined+nameOnly_fully_matched, factgrid_names_temp, ubs_names_temp

def try_fuzzy_match_level1(factgrid_names, ubs_names, score_threshold):
	factgrid_names_temp = factgrid_names
	ubs_names_temp = ubs_names
	similar_name_desc = []
	for f_name in factgrid_names:
		found = False
		sim_score = 0
		match = None
		ubs_names = ubs_names_temp
		for ubs_name in ubs_names:
			name1 = f_name['PersonLabel'].lower()
			if ',' in name1:
				name1 = name1.split(',')[0]
			name2 = ubs_name['name'].lower()
			# score   = difflib.SequenceMatcher(None, name1, name2).ratio()
			score   = Levenshtein.ratio(name1, name2) 
			# score   = 1 - distance.sorensen(name1, name2)
			# score   = 1 - distance.jaccard(name1, name2)
			desc1 = f_name['PersonLabel'].lower()+ " "+ f_name['PersonDescription'].lower()
			if 'FatherLabel' in f_name:
				desc1 += ' ' + f_name['FatherLabel'].lower()
			if 'MotherLabel' in f_name:
				desc1 += ' ' + f_name['MotherLabel'].lower()
			desc1 = re.findall('\w+',desc1)
			desc2 = re.findall('\w+',ubs_name['name'].lower()+' '+ ubs_name['description'].lower())
			jaccard_score = jaccard_similarity(desc1,desc2)
			if score > 0.6:
				f_occurs = convert_ref2tuple(f_name['notedLabel'])
				for occ in ubs_name['occurances']:
					if (f_occurs[0],f_occurs[1]) == (occ[0],occ[1]):
						score += 0.5
					elif (f_occurs[0],f_occurs[1]) == (occ[0],occ[2]):
						score += 0.3
			score = (score+jaccard_score)
			if score > sim_score:
				sim_score = score
				match = ubs_name
		if sim_score > score_threshold:
			# print(f_name['PersonLabel'], " similar to ", match['name'])
			similar_name_desc.append((f_name,'similar > '+str(score_threshold),match))
			factgrid_names_temp.remove(f_name)
			ubs_names_temp.remove(match)
			found = True
	return similar_name_desc, factgrid_names_temp, ubs_names_temp

def try_exact_match_wikiname(full_list, wiki_names):
	count=0
	wiki_temp = wiki_names
	wiki_attached_list = []
	wiki_template = {"item":'','itemLabel':'','itemDescription':''}
	for row in full_list:
		f_name = row[0]
		ubs_name = row[2]
		name1 = f_name['PersonLabel'].lower()
		name2 = ubs_name['name'].lower()
		wiki_names = wiki_temp
		found = False
		for wiki_name in wiki_names:
			name3 = wiki_name['itemLabel'].lower()
			if name3 == name1 and name3 == name2:
				wiki_attached_list.append((f_name,row[1],ubs_name,'both names',wiki_name))
				wiki_temp.remove(wiki_name)
				found = True
				count += 1
				break
			elif name3 == name1:
				wiki_attached_list.append((f_name,row[1],ubs_name,'factgrid name',wiki_name))
				wiki_temp.remove(wiki_name)
				found = True
				count += 1
				break
			elif name3 == name2:
				wiki_attached_list.append((f_name,row[1],ubs_name,'ubs names',wiki_name))
				wiki_temp.remove(wiki_name)
				found = True
				count += 1
				break
		if not found:
				wiki_attached_list.append((f_name,row[1],ubs_name,'',wiki_template))
	print("Wiki exact name matched:"+str(count))
	return wiki_attached_list, wiki_temp

def try_fuzzy_match_wiki(full_list, wiki_names, score_threshold):
	wiki_temp = wiki_names
	wiki_attached_list = []
	wiki_template = {"item":'','itemLabel':'','itemDescription':''}
	for row in full_list:
		if row[3] != '':
			wiki_attached_list.append(row)
			continue
		f_name = row[0]
		ubs_name = row[2]
		name1 = f_name['PersonLabel'].lower()
		if "," in name1:
			name1 = name1.split(',')[0]
		name2 = ubs_name['name']
		desc1 = f_name['PersonLabel'].lower() + ' ' + f_name['PersonDescription'].lower() 
		if "FatherLabel" in f_name:
			desc1 += ' '+ f_name['FatherLabel']
		if "MotherLabel" in f_name:
			desc1 += ' '+ f_name['MotherLabel']
		desc2 = ubs_name['name'].lower() + ' ' + ubs_name['description']
		wiki_names = wiki_temp
		max_score = 0
		match = None
		for wiki_name in wiki_names:
			name3 = wiki_name['itemLabel']
			desc3 = wiki_name['itemLabel'].lower() 
			if "itemDescription" in wiki_name:
				desc3 += " " + wiki_name['itemDescription']
			if "motherLabel" in wiki_name:
				desc3 += " " + wiki_name['motherLabel']
			if "fatherLabel" in wiki_name:
				desc3 += " " + wiki_name['fatherLabel']
			if "spouseLabel" in wiki_name:
				desc3 += " " + wiki_name['spouseLabel']
			if "birthPlaceLabel" in wiki_name:
				desc3 += " " + wiki_name['birthPlaceLabel']
			if "birthPlaceLabel" in wiki_name:
				desc3 += " " + wiki_name['birthPlaceLabel']

			sim_score = Levenshtein.ratio(name1, name3)
			sim_score2 = Levenshtein.ratio(name2,name3)
			if sim_score2 > sim_score:
				sim_score = sim_score2
			sim_score += jaccard_similarity(desc1 + ' '+ desc2, desc3)
			if sim_score > max_score:
				max_score = sim_score
				match = wiki_name
		if max_score > score_threshold:
			wiki_attached_list.append((f_name,row[1],ubs_name,"similarity > "+str(score_threshold),match))
			wiki_temp.remove(match)
		else:
			wiki_attached_list.append(row)
	return wiki_attached_list, wiki_temp

def write_to_csv(combined_list, filename):
	outfile = open(filename, 'w')
	outfile.write("factgrid-ubs_combining_criteria\twiki_combining_criteria\tfactgrid_id\tubs_id\twiki_id\tfactgrid_name\tubs_name\twiki_name\tfactgrid_desc\tubs_desc\twiki_desc\tfactgrid_ref\tubs_ref\n")
	for name_pair in combined_list:
			wiki_desc = ''
			if 'itemDescription' in name_pair[4]:
				wiki_desc = name_pair[4]['itemDescription']
			outfile.write(name_pair[1]+'\t'+name_pair[3]+'\t'+name_pair[0]['Person'].split('/')[-1]+'\t'+name_pair[2]['id']+'\t'+name_pair[4]["item"].split('/')[-1]+'\t'+name_pair[0]['PersonLabel']+'\t'+name_pair[2]['name']+'\t'+name_pair[4]['itemLabel']+'\t'+name_pair[0]['PersonDescription']+'\t'+name_pair[2]['description']+'\t'+wiki_desc+'\t'+name_pair[0]['notedLabel']+'\t'+str(name_pair[2]['occurances'])+'\n')
	outfile.close()

def write_to_Json(combined_list, filename):
	outfile = open(filename, 'w')
	conn_arr = []
	for name_pair in combined_list:
		obj = {}
		if name_pair[0]['Person'] != '':
			obj["factgrid"] = [name_pair[0]['Person'].split('/')[-1] + " "]
		if name_pair[2]['id'] != '':
			obj["ubs"] = [name_pair[2]['id']+ " "]
		if name_pair[4]['item'] != '':
			obj['wiki'] = [name_pair[4]["item"].split('/')[-1] + " "]
		if ('factgrid' in obj and 'ubs' in obj) or 'wiki' in obj:
			obj['linked'] = name_pair[1] + "<br>" + name_pair[3]
			conn_arr.append(obj)
	print("factgrid links:",len([obj for obj in conn_arr if 'factgrid' in obj]))
	print("ubs links:",len([obj for obj in conn_arr if 'ubs' in obj]))
	print("wiki links:",len([obj for obj in conn_arr if 'wiki' in obj]))
	outfile.write("connection = "+json.dumps(conn_arr))
	outfile.close()
	return


def write_to_json_for_datatable(factgrid_names, ubs_names, wiki_names):
	print("len(factgrid_names):", len(factgrid_names))
	print("len(ubs_names):", len(ubs_names))
	print("len(wiki_names):", len(wiki_names))
	json_obj = []
	for name in factgrid_names:
		name_field = name['PersonLabel']
		desc = name['PersonDescription'] +"<br>" 
		if "FatherLabel" in name:
			desc += "Father: "+ name['FatherLabel']
		if "MotherLabel" in name:
			desc += " Mother: "+ name["MotherLabel"]
		reference = name['notedLabel']
		_id = name['Person'].split('/')[-1] + " "
		json_obj.append([name_field, _id, desc+"  "+reference, 'factgrid'])
	# 	# json_obj.append([_id, name_field])
	# file = open("Names4datatables_factgrid.js",'w')
	# file.write('var data_set1 = '+json.dumps(json_obj))
	# file.close()

	# json_obj = []
	for name in ubs_names:
		name_field = name['name']
		desc = name['description']
		reference = [ book +", "+str(name['occurances'][book]) + " time(s)." for book in name['occurances']]
		_id = name['id'] +" "
		json_obj.append([name_field, _id, desc+"<br/>"+" ".join(reference), 'ubs'])
	# file = open("Names4datatables_ubs.js",'w')
	# file.write('var data_set2 = '+json.dumps(json_obj))
	# file.close()

	
	# json_obj = []
	for wiki_name in wiki_names:
		name_field = wiki_name['itemLabel']
		desc = ''
		if "itemDescription" in wiki_name:
			desc += wiki_name['itemDescription']+"<br>"
		if "motherLabel" in wiki_name:
			desc += "Mother: " + wiki_name['motherLabel']
		if "fatherLabel" in wiki_name:
			desc += "  Father: " + wiki_name['fatherLabel']
		if "spouseLabel" in wiki_name:
			desc += "  Spouse: " + wiki_name['spouseLabel']
		if "birthPlaceLabel" in wiki_name:
			desc += "  Born in: " + wiki_name['birthPlaceLabel']
		if "deathPlaceLabel" in wiki_name:
			desc += "  Died in: " + wiki_name['deathPlaceLabel']
		_id = wiki_name["item"].split('/')[-1] + " "
		json_obj.append([name_field, _id, desc, 'wiki'])
	file = open("Names4datatables.js",'w')
	file.write('var data_set = '+json.dumps(json_obj))
	file.close()
	return



if __name__ == '__main__':

	#### Reading(and pre-processing) data
	factgrid = open('people in bible/factgrid_person_query.json','r').read()
	factgrid_names = json.loads(factgrid)
	print("factgrid_names:"+ str(len(factgrid_names)))

	ubs_names = ubs_xlm_parser.get_nt_ot_names_from_ubs()
	print("ubs_names:"+str(len(ubs_names)))

	wiki = open('people in bible/wiki_person_query.json','r').read()
	wiki_names = json.loads(wiki)
	print("wiki_names:"+ str(len(wiki_names)))
	#######################################


	# ##### try matching factgrid and ubs names #########
	# combined_list, factgridRemaining, ubsRemaining = try_exact_name_match(factgrid_names,ubs_names)
	# print("confident_list:"+str(len([a for a in combined_list if a[1]=='name and ref'])))
	# print("ref_doubtfully_combined:"+str(len([a for a in combined_list if a[1]=='name, but ref swapped'])))
	# print("nameOnly_fully_matched:"+str(len([a for a in combined_list if a[1]=='name only'])))

	# combined_list2, factgridRemaining, ubsRemaining = try_fuzzy_match_level1(factgridRemaining, ubsRemaining, 0.9)

	# print("similar_name_desc:"+str(len(combined_list2)))

	# combined_list3, factgridRemaining, ubsRemaining = try_fuzzy_match_level1(factgridRemaining, ubsRemaining, 0.7)
	# print('similar_low_threshold:'+str(len(combined_list3)))

	# print("Remaining in factgrid_names:"+str(len(factgridRemaining)))
	# print("Remaining in ubs_names:"+str(len(ubsRemaining)))
	# # #####################################################


	# # ##### Adding wiki names to the above output ######
	# combined_list = combined_list + combined_list2 + combined_list3

	# ubs_template = {'id':'','name':'','description':'','occurances':''}
	# factgrid_template = {'Person':'', 'PersonLabel':'', "PersonDescription":'', 'notedLabel':''}
	# combined_list += [(f_name,'',ubs_template) for f_name in factgridRemaining]
	# combined_list += [(factgrid_template,'',ubs_name) for ubs_name in ubsRemaining]

	# combined_list, wikiRemaining = try_exact_match_wikiname(combined_list, wiki_names)
	# # print("Remaining in wiki_names:"+str(len(wikiRemaining)))

	# combined_list, wikiRemaining = try_fuzzy_match_wiki(combined_list, wikiRemaining,1.3)

	# print("Remaining in wiki_names:"+str(len(wikiRemaining)))

	# ###################################################

	# # combined_list += [(factgrid_template,'',ubs_template,'',wiki_name) for wiki_name in wikiRemaining]
	# # write_to_csv(combined_list, 'names_combined.csv')

	# write_to_Json(combined_list, 'connected_ne.js')
	###### Create table for editing UI ##############


	write_to_json_for_datatable(factgrid_names, ubs_names, wiki_names)