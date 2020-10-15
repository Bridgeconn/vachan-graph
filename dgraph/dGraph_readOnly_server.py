from fastapi import FastAPI, Query, Path, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from dGraph_conn import dGraph_conn
import logging, csv, urllib, json, itertools, re
from enum import Enum
from pydantic import BaseModel, AnyUrl
from typing import Optional, List

import networkx as nx
import matplotlib.pyplot as plt

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
graph_conn = None
rel_db_name = 'AutographaMT_Staging'
logging.basicConfig(filename='readOnly_server.log',level=logging.DEBUG)
base_URL = 'http://localhost:7000'
DEFAULT_RETURN_LIMIT = 10

book_num_map = { "mat": 40 ,"mrk": 41 ,"luk": 42 ,"jhn": 43 ,"act": 44 ,"rom": 45 ,"1co": 46 ,"2co": 47 ,"gal": 48 ,"eph": 49 ,"php": 50 ,"col": 51 ,"1th": 52 ,"2th": 53 ,"1ti": 54 ,"2ti": 55 ,"tit": 56 ,"phm": 57 ,"heb": 58 ,"jas": 59 ,"1pe": 60 ,"2pe": 61 ,"1jn": 62 ,"2jn": 63 ,"3jn": 64 ,"jud": 65 ,"rev": 66}

num_book_map = {}
for key in book_num_map:
	num_book_map[book_num_map[key]] = key

book_num_map2 = { "Genesis": 1, "GEN": 1, "Exodus": 2, "EXO": 2, "Leviticus": 3, "LEV": 3, "Numbers": 4, "NUM": 4, "Deuteronomy": 5, "DEU": 5, "Joshua": 6, "JOS": 6, "Judges": 7, "JDG": 7, "Ruth": 8, "RUT": 8, "1 Samuel": 9, "1SA": 9, "2 Samuel": 10, "2SA": 10, "1 Kings": 11, "1KI": 11, "2 Kings": 12, "2KI": 12, "1 Chronicles": 13, "1CH": 13, "2 Chronicles": 14, "2CH": 14, "Ezra": 15, "EZR": 15, "Nehemiah": 16, "NEH": 16, "Esther": 17, "EST": 17, "Job": 18, "JOB": 18, "Psalms": 19, "PSA": 19, "Proverbs": 20, "PRO": 20, "Ecclesiastes": 21, "ECC": 21, "Song of Solomon": 22, "SNG": 22, "Isaiah": 23, "ISA": 23, "Jeremiah": 24, "JER": 24, "Lamentations": 25, "LAM": 25, "Ezekiel": 26, "EZK": 26, "Daniel": 27, "DAN": 27, "Hosea": 28, "HOS": 28, "Joel": 29, "JOL": 29, "Amos": 30, "AMO": 30, "Obadiah": 31, "OBA": 31, "Jonah": 32, "JON": 32, "Micah": 33, "MIC": 33, "Nahum": 34, "NAM": 34, "Habakkuk": 35, "HAB": 35, "Zephaniah": 36, "ZEP": 36, "Haggai": 37, "HAG": 37, "Zechariah": 38, "ZEC": 38, "Malachi": 39, "MAL": 39, "Matthew": 40, "MAT": 40, "Mark": 41, "MRK": 41, "Luke": 42, "LUK": 42, "John": 43, "JHN": 43, "Acts": 44, "ACT": 44, "Romans": 45, "ROM": 45, "1 Corinthians": 46, "1CO": 46, "2 Corinthians": 47, "2CO": 47, "Galatians": 48, "GAL": 48, "Ephesians": 49, "EPH": 49, "Philippians": 50, "PHP": 50, "Colossians": 51, "COL": 51, "1 Thessalonians": 52, "1TH": 52, "2 Thessalonians": 53, "2TH": 53, "1 Timothy": 54, "1TI": 54, "2 Timothy": 55, "2TI": 55, "Titus": 56, "TIT": 56, "Philemon": 57, "PHM": 57, "Hebrews": 58, "HEB": 58, "James": 59, "JAS": 59, "1 Peter": 60, "1PE": 60, "2 Peter": 61, "2PE": 61, "1 John": 62, "1JN": 62, "2 John": 63, "2JN": 63, "3 John": 64, "3JN": 64, "Jude": 65, "JUD": 65, "Revelation": 66, "REV": 66, "Psalm": 19, "PSA": 19}
book_num_map.update(book_num_map2)

class BibleBook(str, Enum):
	mat = "mat"
	mrk = "mrk"
	luk = "luk"
	jhn = "jhn"
	act = "act"
	rom = "rom"
	co1 = "1co"
	co2 = "2co"
	gal = "gal"
	eph = "eph"
	php = "php"
	col = "col"
	th1 = "1th"
	th2 = "2th"
	ti1 = "1ti"
	ti2 = "2ti"
	tit = "tit"
	phm = "phm"
	heb = "heb"
	jas = "jas"
	pe1 = "1pe"
	pe2 = "2pe"
	jn1 = "1jn"
	jn2 = "2jn"
	jn3 = "3jn"
	jud = "jud"
	rev = "rev"

class verseReference(BaseModel):
	bible: str = None
	book : BibleBook
	chapter: int
	verse: int
	verseLink: AnyUrl

class wordReference(BaseModel):
	bible: str = None
	book : BibleBook
	chapter: int
	verse: int
	verseLink: AnyUrl
	verseText: str = None
	word: str
	position: int


class NormalResponse(BaseModel):
	message: str

class ErrorResponse(BaseModel):
	error: str
	details: str


######### Error Handling ##############

class GraphException(Exception):
    def __init__(self, detail: str):
        self.name = "Graph Side Error"
        self.detail = detail
        self.status_code = 502

@app.exception_handler(GraphException)
async def graph_exception_handler(request, exc: GraphException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.name, "details" : exc.detail},
    )

class NotAvailableException(Exception):
    def __init__(self, detail: str):
        self.name = "Requested Content Not Available"
        self.detail = detail
        self.status_code = 404

@app.exception_handler(NotAvailableException)
async def NA_exception_handler(request, exc: NotAvailableException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.name, "details" : exc.detail},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
	return JSONResponse(
		status_code=exc.status_code,
		content={"error": "HTTP Error", "details": str(exc.detail)}
	)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
	logging.info(str(exc))
	return JSONResponse(
		status_code=422,
		content={"error": "Input Validation Error" ,"details": str(exc).replace("\n", ". ")}
	)


################## APIS ###################


@app.get("/", response_model=NormalResponse, responses={502: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}, status_code=200 )
def test():
	global graph_conn
	try:
		graph_conn = dGraph_conn()
	except Exception as e:
		logging.error('At connecting to graph DB')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()  
		else:
			details = str(e)
		raise GraphException(details)
	return {'message': "server up and running"}

########### STRONGS NUMBERS #############

all_strongs_query = '''
		query strongs($skip: int, $limit: int){
		strongs(func: has(StrongsNumber), offset:$skip, first:$limit){
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
		query strongs( $strongs: string, $skip: int, $limit: int){
		strongs(func: eq(StrongsNumber, $strongs)) {
			StrongsNumber,
			pronunciation,
			lexeme,
			transliteration,
			definition,
			strongsNumberExtended,
			englishWord,
			occurences:~strongsLink(offset:$skip, first:$limit) @normalize{
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


class StrongsOut(BaseModel):
	StrongsNumber: int
	pronunciation: str
	lexeme :str
	transliteration: str
	definition: str
	strongsNumberExtended: str
	englishWord: str
	occurences: List[wordReference] = None

@app.get("/strongs", response_model=List[StrongsOut], responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Dictionaries"])
def get_strongs(strongs_number:int=None, skip: int =0, limit: int=DEFAULT_RETURN_LIMIT):
	''' Get the list of strongs nodes and their property values.
	* If strongs_number is sepcified, only its properties are returned, along with occurences .
	* skip=n: skips the first n objects in return list
	* limit=n: limits the no. of items to be returned to n	'''
	if not graph_conn:
		test()
	result = []
	variables = {"$skip": str(skip), "$limit": str(limit)}
	try:
		if not strongs_number:
			query_res = graph_conn.query_data(all_strongs_query,variables)
		else:
			variables['$strongs'] = str(strongs_number)
			query_res = graph_conn.query_data(strongs_link_query,variables)
	except Exception as e:
		logging.error('At fetching strongs numbers')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()  
		else:
			details = str(e)
		raise GraphException(details)
	if len(query_res['strongs']) == 0:
		raise NotAvailableException("Strongs Number: "+str(variables))

	for i, strong in enumerate(query_res['strongs']):
		if 'occurences' in strong:
			occurs = []
			for j,occur in enumerate(strong['occurences']):
				logging.info(occur)
				logging.info(num_book_map)
				verse_link = '%s/bibles/%s/books/%s/chapters/%s/verses/%s/words/%s'%(base_URL, occur['bible'], num_book_map[occur['book']], occur['chapter'], occur['verse'], occur['position'])
				link = urllib.parse.quote(verse_link, safe='/:-')
				query_res['strongs'][i]['occurences'][j]['verseLink'] = link
				query_res['strongs'][i]['occurences'][j]['book'] = num_book_map[occur['book']]
		if 'StrongsNumber' in strong:
			strong_link = '%s/strongs?strongs_number=%s'%(base_URL, strong['StrongsNumber'])
			query_res['strongs'][i]['strongsLink'] = urllib.parse.quote(strong_link, safe='/:?=')
	result = query_res['strongs']
	return result

############ TRANSLATION WORDS #################

all_tw_query = '''
	query tw($skip: int, $limit: int){
	tw(func: has(translationWord), offset:$skip, first:$limit){
		translationWord,
		slNo,
		twType,
		description,
	}
	}
'''

tw_link_query = '''
	query tw($tw: string, $skip: int, $limit: int){
	tw(func: eq(translationWord, $tw)){
		translationWord,
		slNo,
		twType,
		description,
		occurences: ~twLink(offset:$skip, first:$limit) @normalize {
			~alignsTo {
	        position:position,
	        word:word,
			belongsTo{
				verse: verse,
				verseText: verseText,
		        belongsTo{
		            chapter:chapter,
		            belongsTo{
		              book:bookNumber,
		              belongsTo {
		               bible:bible 
	}	}	}	}	} }	} }
'''

class twOut(BaseModel):
	translationWord: str
	slNo: int
	twType: str
	description: str
	occurences: List[wordReference]

@app.get("/translation-words", response_model=List[twOut], responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Dictionaries"])
def get_translationwords(translationWord:str=None, skip: int =0, limit: int=DEFAULT_RETURN_LIMIT):
	'''Get the list of translation words and their property values.
	* If tw is sepcified, only its properties are returned, along with occurences .
	* skip=n: skips the first n objects in return list
	* limit=n: limits the no. of items to be returned to n	
	'''
	if not graph_conn:
		test()
	result = []
	variables = {"$skip": str(skip), "$limit": str(limit)}
	try:
		if not translationWord:
			query_res = graph_conn.query_data(all_tw_query,variables)
		elif translationWord:
			variables['$tw'] = translationWord
			query_res = graph_conn.query_data(tw_link_query,variables)
	except Exception as e:
		logging.error('At fetching translation words')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()  
		else:
			details = str(e)
		raise GraphException(details)
	if len(query_res['tw']) == 0:
		raise NotAvailableException("Translation Words:"+ str(variables))

	for i, tw in enumerate(query_res['tw']):
		if 'occurences' in tw:
			for j,occur in enumerate(tw['occurences']):
				verse_link = '%s/bibles/%s/books/%s/chapters/%s/verses/%s/words/%s'%(base_URL, occur['bible'], num_book_map[occur['book']], occur['chapter'], occur['verse'], occur['position'])
				link = urllib.parse.quote(verse_link, safe='/:-')
				query_res['tw'][i]['occurences'][j]['verseLink'] = link
				query_res['tw'][i]['occurences'][j]['book'] = num_book_map[occur['book']]
		if 'translationWord' in tw:
			tw_link = '%s/translation-words?translationWord=%s'%(base_URL, tw['translationWord'])
			query_res['tw'][i]['twLink'] = urllib.parse.quote(tw_link, safe='/:?=')
	result = query_res['tw']
	return result


############### BIBLE CONTENT ##################

all_bibles_query = '''
	query bibles($skip: int, $limit: int){
	bibles(func: has(bible), offset: $skip, first: $limit){
		bible,
		language,
		versification : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
			chapters: ~belongsTo{
				chapterNumber: chapter,
				totalVerses: count(~belongsTo)
			}
		}
	}
	}

'''

bible_name_query = '''
	query bibles($bib: string, $skip: int, $limit: int){
	bibles(func: eq(bible, $bib), offset: $skip, first: $limit){
		bible,
		language,
		versification : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
			chapters: ~belongsTo{
				chapterNumber: chapter,
				totalVerses: count(~belongsTo)
			}
		}
	}
	}

'''

bible_lang_query = '''
	query bibles($lang: string, $skip: int, $limit: int){
	bibles(func: has(bible), offset: $skip, first: $limit) @filter(eq(language, $lang)){
		bible,
		language,
		versification : ~belongsTo {
			book,
			bookNumber,
			totalChapters: count(~belongsTo)
			chapters: ~belongsTo{
				chapterNumber: chapter,
				totalVerses: count(~belongsTo)
			}
		}
	}
	}

'''
class ChapterVerification(BaseModel):
	chapterNumber: int
	totalVerses: int

class BookVersification(BaseModel):
	bookCode: BibleBook
	book: str
	bookNumber: int
	totalChapters: int
	chapters: List[ChapterVerification]

class BibleOut(BaseModel):
	bible: str
	language: str
	bibleLink: AnyUrl
	versification : List[BookVersification] = None

class WordOut(BaseModel):
	word: str
	position: str
	strongsNumber: int = None
	translationWord: str = None
	name: str = None
	strongsLink: AnyUrl = None
	translationWordLink: AnyUrl = None
	nameLink: AnyUrl = None

class VerseOut(BaseModel):
	verseNumber: int
	verseText: str
	words: List[WordOut] = None

class ChapterOut(BaseModel):
	chapterNumber: int
	verses: List[VerseOut]

class BibleBookOut(BaseModel):
	book: BibleBook
	chapters: List[ChapterOut]

class BibleContentOut(BaseModel):
	bible: str
	language: str
	books : List[BibleBookOut]


@app.get('/bibles', response_model=List[BibleOut], responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Bible Contents"])
def get_bibles(bibleName : str = None, language: str = None, versification: bool = False, skip: int = 0, limit: int = DEFAULT_RETURN_LIMIT):
	''' fetches bibles nodes, properties and available books. 
	* If no query params are given, all bibles in graph are fetched.
	* If bibleName is specified, only that node is returned.
	* If only language if given, all bible nodes, and details vavailable in that language is returned
	* versification flag can be set if the versification structure of the Bible(list of books, number of chapters and number of verses) needs to be returned
	* Number of items returned can be set using the skip and limit parameters.
	'''
	if not graph_conn:
		test()
	result = []
	variables = {"$skip": str(skip), "$limit": str(limit)}
	try:
		if not bibleName and not language:
			query_res = graph_conn.query_data(all_bibles_query,variables)
		elif bibleName:
			variables['$bib'] = bibleName
			query_res = graph_conn.query_data(bible_name_query,variables)
		else:
			variables["$lang"] = language
			query_res = graph_conn.query_data(bible_lang_query,variables)
	except Exception as e:
		logging.error('At fetching Bibles')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()
		else:
			details = str(e)
		raise GraphException(details)
	if len(query_res['bibles']) == 0:
		raise NotAvailableException("Bibles: "+str(variables))

	for i, bib in enumerate(query_res['bibles']):
		bible_link = "%s/bibles?bibleName=%s;versification=true"%(base_URL, urllib.parse.quote(bib['bible']))
		query_res['bibles'][i]['bibleLink'] = bible_link
		if not versification:
			del query_res['bibles'][i]['versification']
		else: 
			for j, book in enumerate(bib['versification']):
				bookCode = num_book_map[book['bookNumber']]
				query_res['bibles'][i]['versification'][j]['bookCode'] = bookCode
	result = query_res['bibles']
	return result


whole_chapter_query = '''
	query chapter($bib: string, $book: int, $chapter: int){
	chapter(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		bookNumber,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapterNumber: chapter
		verses: ~belongsTo {
			verseNumber: verse,
			verseText: verseText,
		}
		}
		}
	}
	}
'''

whole_chapter_detailed_query = '''
	query chapter($bib: string, $book: int, $chapter: int){
	chapter(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		bookNumber,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapterNumber: chapter
		verses: ~belongsTo {
			verseNumber: verse,
			verseText: verseText,
			words: ~belongsTo @normalize{
				word:word,
				position: position,
				twLink {
					translationWord: translationWord,
				},
				strongsLink {
					strongsNumber: StrongsNumber,
				},
				nameLink {
					name: name
				}
				alignsTo: alignsTo {
					twLink {
						translationWord: translationWord,
					}
					strongsLink {
						strongsNumber: StrongsNumber,
					}
					~alignsTo {
						nameLink{
							name: name
						}
					}
				}
			}
		}
		}
		}
	}
	}
'''

@app.get('/bibles/{bibleName}/books/{bookCode}/chapters/{chapter}', response_model=ChapterOut, responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Bible Contents"])
def get_whole_chapter(bibleName: str, bookCode: BibleBook, chapter: int, detailed: bool = False):
	''' fetches all verses of the chapter 
	* if detailed flag if set, the individual words in verses, including their strong number, tw and bible name connections are returned
	'''
	if not graph_conn:
		test()
	result = []
	try:
		variables = {'$bib': bibleName,
					'$book': str(book_num_map[bookCode]),
					'$chapter': str(chapter)}
		if detailed:
			query_res = graph_conn.query_data(whole_chapter_detailed_query,variables)
		else:
			query_res = graph_conn.query_data(whole_chapter_query,variables)
	except Exception as e:
		logging.error('At fetching chapter contents')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()
		else:
			details = str(e)
		raise GraphException(details)
	try:
		result = query_res['chapter'][0]['~belongsTo'][0]['~belongsTo'][0]
	except Exception as e:
		logging.error('At parsing chapter contents')
		logging.error(e)
		raise NotAvailableException("Whole Chapter: "+str(variables))
	if detailed:
		for j,ver in enumerate(result['verses']):
			for i,wrd in enumerate(ver['words']):
				if 'translationWord' in wrd:
					link = '%s/translation-words?translationWord=%s'%(base_URL, urllib.parse.quote(wrd['translationWord']))
					result['verses'][j]['words'][i]['translationWordLink'] = link
				if 'strongsNumber' in wrd:
					link = '%s/strongs?strongsNumber=%s'%(base_URL, wrd['strongsNumber'])
					result['verses'][j]['words'][i]['strongsLink'] = link
				if 'name' in wrd:
					if isinstance(wrd['name'], list):
						result['verses'][j]['words'][i]['name'] = ', '.join(wrd['name'])
						result['verses'][j]['words'][i]['nameLink'] = ', '.join(['%s/names?name=%s'%(base_URL, urllib.parse.quote(nm)) for nm in wrd['name']])
					else:
						result['verses'][j]['words'][i]['nameLink'] = '%s/names?name=%s'%(base_URL, urllib.parse.quote(wrd['name']))
	
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
			verseNumber: verse,
			verseText: verseText,
		}
		}
		}
	}
	}
'''

one_verse_detailed_query = '''
	query verse($bib: string, $book: int, $chapter: int, $verse: int){
	verse(func: eq(bible, $bib)) {
		bible
		~belongsTo @filter(eq(bookNumber, $book)){
		book,
		~belongsTo @filter(eq(chapter, $chapter)){
		chapter
		~belongsTo @filter(eq(verse, $verse)){
			verseNumber: verse,
			verseText: verseText,
			words: ~belongsTo @normalize{
				word:word,
				uid,
				position: position,
				twLink: twLink {
					translationWord: translationWord,
				},
				strongsLink {
					strongsNumber: StrongsNumber,
				},
				nameLink{
					name: name,
					externalUid: externalUid
				},
				alignsTo: alignsTo {
					twLink: twLink {
						translationWord: translationWord,
					}
					strongsLink {
						strongsNumber: StrongsNumber,
					}
					~alignsTo{
						nameLink{
							name: name,
							externalUid: externalUid
						}

					}
				}

			}
		}
		}
		}
	}
	}
'''


@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}', response_model=VerseOut, responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Bible Contents"])
def get_one_verse(bible_name: str, bookcode: BibleBook, chapter: int, verse: int, detailed: bool = False):
	''' fetches one verse.
	* detailed flag can be used to include individual words list and their strong number, tw and bible name connections
	'''
	if not graph_conn:
		test()
	try:
		variables = {'$bib': bible_name,
					'$book': str(book_num_map[bookcode]),
					'$chapter': str(chapter),
					'$verse': str(verse)}
		if detailed:
			query_res = graph_conn.query_data(one_verse_detailed_query,variables)
		else:
			query_res = graph_conn.query_data(one_verse_query,variables)
	except Exception as e:
		logging.error('At fetching chapter contents')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()
		else:
			details = str(e)
		raise GraphException(details)
	try:
		result = query_res['verse'][0]['~belongsTo'][0]['~belongsTo'][0]['~belongsTo'][0]
	except Exception as e:
		logging.error('At parsing verse contents')
		logging.error(e)
		raise NotAvailableException("One verse: "+str(variables))
	if detailed:
		for i,wrd in enumerate(result['words']):
			if 'translationWord' in wrd:
				link = '%s/translation-words?translationWord=%s'%(base_URL, wrd['translationWord'])
				result['words'][i]['translationWordLink'] = urllib.parse.quote(link, safe='/:?=')
			if 'strongsNumber' in wrd:
				link = '%s/strongs?strongs_number=%s'%(base_URL, wrd['strongsNumber'])
				result['words'][i]['strongsLink'] = urllib.parse.quote(link, safe='/:?=')
			if "name" in wrd:
				if isinstance(wrd['name'], list):
					result['words'][i]['name'] = ', '.join(wrd['name'])
					result['words'][i]['nameLink'] = ', '.join(["%s/names?externalUid=%s"%(base_URL, urllib.parse.quote(nm)) for nm in wrd['externalUid']])
				else:
					result['words'][i]['nameLink'] = "%s/names?externalUid=%s"%(base_URL, urllib.parse.quote(wrd['externalUid']))
	return result

@app.get('/bibles/{bible_name}/books/{bookcode}/chapters/{chapter}/verses/{verse}/words/{position}', response_model=VerseOut, responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Bible Contents"])
def get_verse_word(bible_name: str, bookcode: BibleBook, chapter: int, verse: int, position: int):
	''' fetches all details of a bible word 
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


################### BIBLE NAMES #####################

all_names_query = """
			query names($skip: int, $limit: int){
			names(func: has(externalUid), offset: $skip, first: $limit) {
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						externalUid: externalUid
					}
			} }
"""

one_name_xuid_query = """
			query names($skip: int, $limit: int, $xuid: string){
			names(func: eq(externalUid, $xuid), offset: $skip, first: $limit){
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						externalUid: externalUid
					}
			} } 
"""

name_match_query = """
			query names($skip: int, $limit: int, $name: string){
			names(func: eq(name, $name), offset: $skip, first: $limit) {
					name:name,
					externalUid: externalUid,
					description: description,
					gender: gender,
					bornIn: brithPlace,
					brithDate: birthDate,
					diedIn:deathPlace,
					deathDate: deathDate
					sameAs{
						otherName:name,
						externalUid: externalUid
					}
			} } 
"""

family_tree_query = '''
	query relations($xuid: string){
	relations(func: eq(externalUid,$xuid)){
		name,
		externalUid,
		father{
			name,
			externalUid,
			sibling: ~father{
				name,
				externalUid	} },
		mother{
			name,
			externalUid,
			sibling: ~mother{
				name,
				externalUid	} },
		spouse{
			name,
			externalUid	},
		children1:~father{
			name,
			externalUid },
		children2:~mother{
			name,
			externalUid },
		sameAs{
			name,
			externalUid,
			father{
				name,
				externalUid,
				sibling: ~father{
					name,
					externalUid	} },
			mother{
				name,
				externalUid,
				sibling: ~mother{
					name,
					externalUid	} },
			spouse{
				name,
				externalUid	},
			children1:~father{
				name,
				externalUid },
			children2:~mother{
				name,
				externalUid } }
	} }
'''

names_link_query = '''
	query occurences($xuid: string, $skip:int, $limit:int){
	occurences(func: eq(externalUid, $xuid)){
	~nameLink(offset: $skip, first: $limit) @normalize{
		word: word,
		position: position,
		belongsTo{
			verse:verse,
			verseText: verseText,
			belongsTo{
				chapter:chapter,
				belongsTo{
					book: book,
					bookNumber: bookNumber,
					belongsTo{
						bible:bible} }	} } }
	sameAs{
		~nameLink(offset: $skip, first: $limit) @normalize{
			word: word,
			position: position,
			belongsTo{
				verse:verse,
				verseText: verseText,
				belongsTo{
					chapter:chapter,
					belongsTo{
						book: book,
						bookNumber: bookNumber,
						belongsTo{
							bible:bible} }	} } }
	}
	}	}
'''

class OtherName(BaseModel):
	otherName: str
	nameLink: AnyUrl
	externalUid: str

class NameOut(BaseModel):
	name: str
	description: str
	gender: str = None
	bornIn: str = None
	brithDate: str = None
	diedIn: str = None
	deathDate: str = None
	nameLink: AnyUrl
	sameAs: List[OtherName] = None
	relations: AnyUrl = None
	externalUid: str
	occurences: List[wordReference] = None

@app.get('/names', response_model=List[NameOut], responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Dictionaries"])
def get_names(name: str = None, externalUid: str = None, occurences: bool = False, skip:int = 0, limit: int = 10):
	''' Fetched the list of Bible Names in Graph
	* name or externalUid can be used to obtaine specific names and details
	* occurences flag can be used to fetch occurences of the name in bible
	* skip and limit can be used for pagination'''
	if not graph_conn:
		test()
	variables = {
		"$skip": str(skip),
		"$limit": str(limit)
		}
	result = []
	try:
		if not name and not externalUid:
			names_query_res = graph_conn.query_data(all_names_query, variables)
		elif externalUid:
			variables['$xuid'] = externalUid
			names_query_res = graph_conn.query_data(one_name_xuid_query, variables)
		elif name:
			variables['$name'] = name
			names_query_res = graph_conn.query_data(name_match_query, variables)
	except Exception as e:
		logging.error('At fetching names')
		logging.error(e)
		if "details" in dir(e):
			details = e.details()
		else:
			details = str(e)
		raise GraphException(details)

	if len(names_query_res['names']) == 0:
		raise NotAvailableException("Bible Names: "+str(variables))

	result = names_query_res['names']

	for i,person in enumerate(result):
		result[i]['nameLink'] = '%s/names?externalUid=%s;occurences=True'%(base_URL,urllib.parse.quote(person['externalUid']))
		result[i]['relations'] = '%s/names/relations?externalUid=%s'%(base_URL, urllib.parse.quote(person['externalUid']))
		if "sameAs" in person:
			for j,otherName in enumerate(person['sameAs']):
				result[i]['sameAs'][j]['nameLink'] = '%s/names?externalUid=%s;occurences=True'%(base_URL, urllib.parse.quote(otherName['externalUid']))
	if occurences:
		for i, person in enumerate(result):
			result[i]['occurences'] = []
			try:
				occurences_query_res = graph_conn.query_data(names_link_query,{'$xuid': person['externalUid'], "$skip": str(skip), "$limit": str(limit)})
			except Exception as e:
				logging.error('At fetching names occurences of %s'%person['name'])
				logging.error(e)
				if "details" in dir(e):
					details = e.details()
				else:
					details = str(e)
				raise GraphException(details)
			if len(occurences_query_res['occurences']) == 0:
				logging.warn('At fetching names occurences of %s'%person['name'])
				logging.warn("Requested contents not available")
			else:
				if '~nameLink' in occurences_query_res['occurences'][0]:
					result[i]['occurences'] = occurences_query_res['occurences'][0]['~nameLink']
				if 'sameAs' in occurences_query_res['occurences'][0]:
					for otherName_occurences in occurences_query_res['occurences'][0]['sameAs']:
						result[i]['occurences'] += otherName_occurences['~nameLink']
				for j,occur in enumerate(result[i]['occurences']):
					verseLink = '%s/bibles/%s/books/%s/chapters/%s/verses/%s'%(base_URL, urllib.parse.quote(occur['bible']), occur['bookNumber'], occur['chapter'], occur['verse'])
					result[i]['occurences'][j]['verseLink'] = verseLink
					result[i]['occurences'][j]['book'] = num_book_map[occur['bookNumber']]
	return result


@app.get("/names/relations", response_class=FileResponse, responses = {502:{"model":ErrorResponse}, 404:{"model": ErrorResponse}, 422:{"model": ErrorResponse}}, response_model_exclude_unset=True, status_code=200, tags=["Extras"])
def get_person_relations(externalUid: str):
	if not graph_conn:
		test()
	result = {}
	try:
		relations_query_result = graph_conn.query_data(family_tree_query,{'$xuid': externalUid})
	except Exception as e:
		logging.error('At fetching family relations of %s'%extrenalUid)
		logging.error(e)
		if "details" in dir(e):
			details = e.details()
		else:
			details = str(e)
		raise GraphException(details)
	if len(relations_query_result['relations']) == 0:
		raise NotAvailableException("Realtions: "+str(externalUid))

	result['person'] = {"name": relations_query_result['relations'][0]['name'],
						"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['externalUid']))}
	result['siblings'] = []
	if "father" in relations_query_result['relations'][0]:
		result['father'] = {"name": relations_query_result['relations'][0]['father'][0]['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['father'][0]['externalUid'])) 
							}
		if 'sibling' in relations_query_result['relations'][0]['father'][0]:
			for sibling in relations_query_result['relations'][0]['father'][0]['sibling']:
				if sibling['externalUid'] != externalUid:
					result['siblings'].append({"name": sibling['name'],
												"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
												})
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'father' in otherName:
				if 'father' not in result:
					result['father'] = {"name": otherName['father'][0]['name'],
										"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(otherName['father'][0]['externalUid']))}
				if 'sibling' in otherName['father'][0]:
					for sibling in otherName['father'][0]['sibling']:
						result['siblings'].append({"name": sibling['name'],
													"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
													})
				break
	if "mother" in relations_query_result['relations'][0]:
		result['mother'] = {"name": relations_query_result['relations'][0]['mother'][0]['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(relations_query_result['relations'][0]['mother'][0]['externalUid'])) 
							}
		if 'sibling' in relations_query_result['relations'][0]['mother'][0]:
			for sibling in relations_query_result['relations'][0]['mother'][0]['sibling']:
				sib = {"name": sibling['name'],
						"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
						}
				if sibling['externalUid'] != externalUid and sib not in result['siblings']:
					result['siblings'].append()
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'mother' in otherName:
				if 'mother' not in result:
					result['mother'] = {"name": otherName['mother'][0]['name'],
										"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(otherName['mother'][0]['externalUid']))}
				if 'sibling' in otherName['mother'][0]:
					for sibling in otherName['mother'][0]['sibling']:
						sib = {"name": sibling['name'],
								"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
								}
						if sibling['externalUid'] != externalUid and sib not in result['siblings']:
							result['siblings'].append({"name": sibling['name'],
														"link":"%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(sibling['externalUid']))
														})
				break
	result['spouses'] = []
	if "spouse" in relations_query_result['relations'][0]:
		for spouse in relations_query_result['relations'][0]['spouse']:
			sps = {"name": spouse['name'],
				"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(spouse['externalUid']))}
			if sps not in result['spouses']:
				result['spouses'].append(sps)
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if "spouse" in otherName:
				for spouse in otherName['spouse']:
					sps = {"name": spouse['name'],
						"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(spouse['externalUid']))}
					if sps not in result['spouses']:
						result['spouses'].append(sps)
						
	result['children'] = []
	if "children1" in relations_query_result['relations'][0]:
		for child in relations_query_result['relations'][0]['children1']:
			ch = {"name": child['name'],
					"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
			if ch not in result['children']:
				result['children'].append(ch)	
	elif "children2" in relations_query_result['relations'][0]:
		for child in relations_query_result['relations'][0]['children2']:
			ch = {"name": child['name'],
					"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
			if ch not in result['children']:
				result['children'].append(ch)	
	elif "sameAs" in relations_query_result['relations'][0]:
		for otherName in relations_query_result['relations'][0]['sameAs']:
			if 'children1' in otherName:
				for child in otherName['children1']:
					ch = {"name": child['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
					if ch not in result['children']:
						result['children'].append(ch)	
			elif 'children2' in otherName:
				for child in otherName['children2']:
					ch = {"name": child['name'],
							"link": "%s/names/relations?externalUid=%s"%(base_URL, urllib.parse.quote(child['externalUid']))}
					if ch not in result['children']:
						result['children'].append(ch)	
	if len(result['spouses']) == 0:
		del result['spouses']
	if len(result['siblings']) == 0:
		del result['siblings']
	if len(result['children']) == 0:
		del result['children']

	fig = plt.figure(figsize=(12,12))
	ax = plt.subplot(111)
	ax.set_title('Graph - Shapes', fontsize=10)
	G = nx.DiGraph()

	G.add_node(result['person']['name'], level=3)
	colour_list = ["blue"]

	if 'father' in result:
		G.add_node(result['father']['name'], level=4)
		G.add_edge(result['person']['name'], result['father']['name'], label='father')
		colour_list.append("green")

	if 'mother' in result:
		G.add_node(result['mother']['name'], level=4 )
		G.add_edge(result['person']['name'], result['mother']['name'], label='mother')
		colour_list.append("green")

	if 'siblings' in result:
		for sib in result['siblings']:
			G.add_node(sib['name'], level=2)
			G.add_edge(result['person']['name'], sib['name'], label='sibling')
			colour_list.append("purple")

	if 'spouses' in result:
		for sps in result['spouses']:
			G.add_node(sps['name'], level=2)
			G.add_edge(result['person']['name'], sps['name'], label='spouse')
			colour_list.append("pink")

	if 'children' in result:
		for child in result['children']:
			G.add_node(child['name'], level=1)
			G.add_edge(result['person']['name'], child['name'], label='child')
			colour_list.append("orange")

	pos = nx.multipartite_layout(G, subset_key='level', align='horizontal')
	nx.draw(G, pos, node_size=5000, node_color=colour_list, font_size=20, font_weight='bold')
	nx.draw_networkx_labels(G, pos)
	nx.draw_networkx_edge_labels(G, pos)
	plt.tight_layout()
	plt.savefig("static/Family-tree.png")

	rels_html = ""
	for key in result:
		if key in ['person', 'mother', 'father']:
			rels_html += '%s:<a href="%s">%s</a><br>'%(key.upper(), result[key]['link'], result[key]['name'])
		else:
			items = ", ".join(['<a href="%s">%s</a>'%(it['link'], it['name']) for it in result[key]])
			# items = ['<a href="%s">%s</a>'%(it['link'], it['name']) for it in result[key]]
			rels_html += '%s:%s <br>'%(key.upper(), str(items))

	html_file = open("Family-tree.html", "w")
	html_content = '''
	<html>
	<body>
	<div style="float:left" width="25%%">
	%s
	</div>
	<div style="float:left" width="75%%">
	<img src="/static/Family-tree.png" height="750px">
	</div>
	</body>
	</html>
	'''%rels_html

	html_file.write(html_content)
	html_file.close()
	return FileResponse("Family-tree.html")