from pathlib import Path
import re

dir_path = './English Story Study questions'
file_list = Path(dir_path).glob('*.md')

outputfile = open("BibleStroyQuestions_English.csv",'w',encoding='utf-8')

storyTitle_pattern = re.compile(r'# *\d+\. *(.+)\n')
qaPair_pattern =re.compile(r'\n1\. *(.+)[\n\s]+(.+)')
summaryPattern = re.compile(r'\n## *Summary[\n\s]+(.+)')
bracketLinksPattern = re.compile(r'\(See: \[.*\]\(.*\)\)')

count = 0
filecount = 0
outputfile.write("Sl No\tStory Title\tSummary\tQuestionAnswers\n")
for file in file_list:
	filename = str(file)
	full_content = open(filename,'r',encoding='utf-8').read()
	filecount += 1
	# print(full_content)
	story_title = re.search(storyTitle_pattern,full_content).group(1)
	qa_pairs = re.findall(qaPair_pattern,full_content)
	summary = re.search(summaryPattern,full_content).group(1)
	print("story_title:",story_title)
	# print("QAs:",qa_pairs)
	# print("summary:",summary)
	outputline = str(filecount)+"\t"+story_title+"\t"+summary+"\t"
	for qa in qa_pairs:
		q = qa[0]
		a = qa[1]
		a = re.sub(bracketLinksPattern," ",a)
		outputline = outputline+ "<<QUESTION>>: "+q+"<<ANSWER>>: "+a+"|||"
	outputline = outputline +"\n"
	outputfile.write(outputline)
outputfile.close()

