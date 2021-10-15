########NOTE###########
# activate the virtual environment and start the server with
# 	uvicorn dGraph_fastAPI_server:app --port=7000



################# Full Graph rebuild ###################


baseUrl="http://127.0.0.1:7000"


curl -X GET "$baseUrl/graph" -H  "accept: application/json"
curl -X DELETE "$baseUrl/graph" -H  "accept: application/json"
curl -X GET "$baseUrl/graph" -H  "accept: application/json"
curl -X POST localhost:8080/admin/schema --data-binary '@schema.graphql'
echo -e "\nschemas initialized"

curl -X POST "$baseUrl/strongs" -H  "accept: application/json" -d ""

curl -X POST "$baseUrl/translationwords" -H  "accept: application/json" -d ""



################# Bibles #########################

name="Grk UGNT4 bible"
table="Grk_UGNT4_BibleWord"
lang="greek"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e  "\nworking on $book from $table"
	curl -X POST "$baseUrl/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"language\":\"$lang\", \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
done

name="Hindi IRV4 bible"
table="Hin_4_BibleWord"
lang="hindi"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e  "\nworking on $book from $table"
	curl -X POST "$baseUrl/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"language\":\"$lang\", \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
done

name="Malayalam IRV4 bible"
table="Mal_4_BibleWord"
lang="malayalam"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e  "\nworking on $book from $table"
	curl -X POST "$baseUrl/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"language\":\"$lang\",  \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
done

name="English ULB bible"
table="Eng_ULB_BibleWord"
lang="english"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e  "\nworking on $book from $table"
	curl -X POST "$baseUrl/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"language\":\"$lang\", \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
done


for filename in ../../versification-specification/data/eng-web/*.usfm; do
	echo -e "\n"$filename
	curl -X POST "$baseUrl/bibles/usfm" -H  "accept: application/json" -H  "Content-Type: multipart/form-data" -F "bible_name=Eng WEB bible" -F "language=English" -F "version=WEB" -F "usfm_file=@$filename"   
done



############### Alignments ###################

bible_name="English ULB bible"
alignment_table="Eng_ULB_Grk_UGNT4_Alignment"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e "\nworking on $book in $alignment_table for $bible_name"
	curl -X POST "$baseUrl/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
done

bible_name="Hindi IRV4 bible"
alignment_table="Hin_4_Grk_UGNT4_Alignment"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e "\nworking on $book in $alignment_table for $bible_name"
	curl -X POST "$baseUrl/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
done

bible_name="Malayalam IRV4 bible"
alignment_table="Mal_4_Grk_UGNT4_Alignment"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo -e "\nworking on $book in $alignment_table for $bible_name"
	curl -X POST "$baseUrl/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
done




################## Names, versification ########################

echo -e "\n Adding names"
curl -X POST "$baseUrl/names" -H  "accept: application/json" -d ""

echo -e "\n Working on versification"
curl -X POST "$baseUrl/versification/original" -H  "accept: application/json" -H  "Content-Type: application/json" -d "$(<../../versification-specification/versification-mappings/standard-mappings/org.json)"

echo "\n Adding versification for Hindi IRV4 bible"
curl -X POST "$baseUrl/versification/map?bible_name=Hindi%20IRV4%20bible" -H  "accept: application/json" -H  "Content-Type: application/json" -d "$(<../../versification-specification/data/output/IRV-hin.json)"
curl -X POST "$baseUrl/versification/map?bible_name=Eng%20WEB%20bible" -H  "accept: application/json" -H  "Content-Type: application/json" -d "$(<../../versification-specification/data/output/eng-web.json)"

