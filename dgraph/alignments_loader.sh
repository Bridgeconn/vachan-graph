# bible_name="English ULB bible"
# alignment_table="Eng_ULB_Grk_UGNT4_Alignment"

# for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
# 	echo "working on $book in $alignment_table for $bible_name"
# 	curl -X POST "http://127.0.0.1:7000/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
# done

bible_name="Hindi IRV4 bible"
alignment_table="Hin_4_Grk_UGNT4_Alignment"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo "working on $book in $alignment_table for $bible_name"
	curl -X POST "http://127.0.0.1:7000/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
done

bible_name="Malayalam IRV4 bible"
alignment_table="Mal_4_Grk_UGNT4_Alignment"

for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo "working on $book in $alignment_table for $bible_name"
	curl -X POST "http://127.0.0.1:7000/alignment" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"source_bible\": \"$bible_name\",  \"alignment_table\": \"$alignment_table\",  \"bookcode\": \"$book\" }"
done




