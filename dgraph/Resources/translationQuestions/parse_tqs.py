from pathlib import Path
import re

dir_path = './English'
file_list = Path(dir_path).glob('*.md')
# file_list = Path(dir_path).glob('**/*.md')

outputfile = open("tQuestionsEnglish.csv",'w',encoding='utf-8')
qa_pair_pattern_ENG = re.compile(r'### *<a[^>]+> *(.*)\n[\n\s]*#### *(.*)\n[\n\s]*(.*)\n')
qa_pair_pattern_MAL = re.compile(r'# *(.*)\n[\n ]*([^\[]+]*)\[([^\]]+)')
qa_pair_pattern_HIN = re.compile(r'# *(.*)\n[\n ]*(.*)')

booknumber_pattern = re.compile(r'/(\d+)-')
QA_s = []
count = 0
filecount = 0
outputfile.write("Sl No\tQuestion\tAnswer\tReference\n")
for file in file_list:
	filename = str(file)
	count = 0
	print(filename)
	matchObj = re.search(booknumber_pattern,filename)
	bookNumber = int(matchObj.group(1))
	filecount += 1
	# bookname,chapter = filename[:-3].split('/')[1:3]
	# bookname,chapter,verse = filename[:-3].split('/')[1:4]
	full_content = open(filename,'r',encoding='utf-8').read()
	ref_count = 0
	start_flag=False
	for char in full_content:
		if char=='[':
			start_flag=True
		if char == ']' and start_flag:
			start_flag = False
			ref_count += 1

	matchObj = re.findall(qa_pair_pattern_ENG,full_content)
	if len(matchObj)< ref_count:
		print(ref_count- len(matchObj)," missed in ",filename )
	currQAs = [ (item[1],item[2],item[0]) for item in matchObj ]
	QA_s = QA_s + currQAs
	for qa in currQAs:
		count += 1
		question = qa[0]
		question.replace("\t"," ")
		question.replace("\r"," ")
		answer = qa[1]
		answer.replace("\t"," ")
		answer.replace("\r"," ")
		ref = qa[2]
		ref.replace("\t"," ")
		ref.replace("\r"," ")
		outputline = str(bookNumber*1000+count)+"\t"+question+"\t"+answer+"\t"+ref+"\n"
		outputfile.write(outputline)
	# QA_s = QA_s + [ (item[0],item[1],bookname+' '+chapter+":"+verse) for item in matchObj ]

outputfile.close()
# print(QA_s)
print(len(QA_s))
print("from ",filecount," files")