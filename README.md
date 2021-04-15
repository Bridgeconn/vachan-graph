# vachan-graph
A knowledge graph of the Bible and associated processing.
Built using [DGraph](https://dgraph.io/) graph platform.

The GUI to the graph can be accessed [here](http://128.199.18.6:8000/?dev).

Some sample queries to try

```
{bible(func:has(bible)){   bible }}
```

```
{bible(func: eq(bible,"Eng ULB bible")){
  name:bible,
  language,
  version,
  book:~belongsTo{
    	name:book,
  	bookNumber,
  	chapters: count(~belongsTo)
  }
}}
```
```
{
  verse(func:uid("0x25039") ){
  name:verse,
  verseText:verseText,
  chapter:belongsTo {
    name:chapter,
    book:belongsTo{
      name:book,
      bookNumber:bookNumber,
      bible:belongsTo{
        name:bible,
        language:language
} } } } }
```
```
{strongs(func:eq(StrongsNumber,1)){
  name:StrongsNumber,
  strongsNumberExtended,
  englishWord,
  definition,
  bibleWord:~strongsLink{
    name:word,
  	bibleWord:~alignsTo{
      name:word
} }}}
```
```
{person(func:uid("0x942c6")){
  name,
  father{
    name,
    grandfather:father{
      name },
    grandmother:mother{
      name },
  	sibling: ~father{
     name }},
  mother{
    name,
    grandfather: father{
      name },
    grandmother: mother{
      name },
  	sibling: ~mother{
    	name }},
  child:~father{
  	name },
  spouse{
    name }
}}
```
## API-Server

The server application which provides REST APIs to build and access the Graph DB.
Implemented in Python, [fastapi](https://fastapi.tiangolo.com/) framework.

### Deployment

1. Clone Git repo 

`git clone https://github.com/Bridgeconn/vachan-graph.git`

2. Pull the dev branch

`cd vachan-graph`

`git pull origin dev`

3. Set up virtual environment

`cd dgraph`

`python3 -m venv vachan-grapn-VENV`

`source vachan-grapn-VENV/bin/activate`

`pip install --upgrade pip`

`pip install -r requirements.txt`

4. Run the app

`gunicorn dGraph_readOnly_server:app -w 4 -k uvicorn.workers.UvicornH11Worker --forwarded-allow-ips='*'`


5. Configure Ngnix

A sample configuration

```
http {
  server {
    listen 80;
    client_max_body_size 4G;

    server_name example.com;

    location / {
      proxy_set_header Host $http_host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_redirect off;
      proxy_buffering off;
      proxy_pass http://uvicorn;
    }

    location /static {
      # path for static files
      root /path/to/dgraph/static;
    }
  }

  upstream uvicorn {
    server unix:/tmp/uvicorn.sock;
  }

}
```