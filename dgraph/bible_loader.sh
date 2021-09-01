# ##### Table names
name="Grk UGNT4 bible"
table="Grk_UGNT4_BibleWord"


for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
	echo "working on $book from $table"
	curl -X POST "http://127.0.0.1:7000/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
done

# name="Hindi IRV4 bible"
# table="Hin_4_BibleWord"


# for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
# 	echo "working on $book from $table"
# 	curl -X POST "http://127.0.0.1:7000/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
# done

# name="Malayalam IRV4 bible"
# table="Mal_4_BibleWord"


# for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
# 	echo "working on $book from $table"
# 	curl -X POST "http://127.0.0.1:7000/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
# done

# name="English ULB bible"
# table="Eng_ULB_BibleWord"

# for book in mat mrk luk jhn act rom 1co 2co gal eph php col 1th 2th 1ti 2ti tit phm heb jas 1pe 2pe 1jn 2jn 3jn jud rev; do
# 	echo "working on $book from $table"
# 	curl -X POST "http://127.0.0.1:7000/bibles" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"bible_name\":\"$name\"   , \"bookcode\":\"$book\",\"tablename\":\"$table\"   }"
# done


