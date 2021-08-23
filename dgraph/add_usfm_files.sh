
for filename in ../../versification-specification/data/eng-web/*.usfm; do
	echo $filename
	curl -X POST "http://127.0.0.1:7000/bibles/usfm" -H  "accept: application/json" -H  "Content-Type: multipart/form-data" -F "bible_name=Eng WEB Trial" -F "language=English" -F "version=WEB" -F "usfm_file=@$filename"   
done