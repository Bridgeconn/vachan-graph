from pathlib import Path
import re
import scriptures

dir_path = './English'
file_list = Path(dir_path).glob('*.md')

outputfile = open('BibleStriesEnglish.csv','w',encoding='utf-8')


filename_pattern = re.compile(r'\w+/\d+\.md')
storytitle_pattern =  re.compile(r'^# *\d+\.? *(.*)')
image_urls_pattern = re.compile(r'!\[[^\]]*\]\((.*)\)')
reference_pattern = re.compile(r'\n(.*)\n*$')
story_snippet_pattern = re.compile(r'\n([^# \n\!].*)\n')
sl_no = 0

outputfile.write("Sl No\tTitle\tStory\tReference\tImages\n")
for file in file_list:
	filename = str(file)
	if re.match(filename_pattern,filename):
		sl_no = filename.split("/")[-1][:-3]
		full_content = open(filename,'r',encoding='utf-8').read()
		storytitle = ''
		image_urls = []
		references = ''
		story = ''

		matchobj = re.search(storytitle_pattern,full_content)
		storytitle = matchobj.group(1)
		matchobj = None
		# print('storytitle:',storytitle)

		image_urls = re.findall(image_urls_pattern,full_content)
		# print('image_urls:',image_urls)

		matchobj = re.search(reference_pattern,full_content)
		reference_line = matchobj.group(1)
		references = scriptures.extract(reference_line)
		matchobj = None
		# print('reference:',references)

		story = " ".join(re.findall(story_snippet_pattern,full_content)[:-1])
		story.replace("\t",' ')
		story.replace("\n",' ')
		# print('story:',story)
		outputline = str(sl_no) +"\t"+ storytitle +"\t"+ story +"\t"+ ', '.join(["from "+str(ref[0])+" "+str(ref[1])+":"+str(ref[2])+ " to "+str(ref[0])+" "+str(ref[3])+":"+str(ref[4]) for ref in references]) +"\t"+ ", ".join(image_urls) + "\n" 
		outputfile.write(outputline)
	else:
		print("!!!!!Skipping:",filename)
		
	# break
outputfile.close()