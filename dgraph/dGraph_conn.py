import pydgraph
import datetime
import json, logging


class dGraph_conn:
	client_stub = None
	client = None

	def __init__(self):
		self.create_client_stub()
		self.create_client()

		schema = '''
			<bible>: string @index(exact) .
			<book>: string @index(exact) .
			<bookNumber>:int @index(int) .
			<chapter>:int @index(int) .
			<verse>:int @index(int) .
			<belongsTo>: [uid] @reverse .
			<translationWord>: string @index(exact) .
			<StrongsNumber>: int @index(int) .
			<position>: int @index(int) .
			<alignsTo>: [uid] @reverse .
			<strongsLink>: [uid] @reverse .
			<twType>: string @index(exact) .
			<twLink>: uid @reverse .
			<word>: string @index(exact) .
			<synonym_set>: string @index(exact) .
			<wn_lemma>: string @index(exact) .
			<dictionary>: string @index(exact) .
			<wordnet_link>: [uid] @reverse .
			<synset>: [uid] @reverse .
			<root>: [uid] @reverse .
			<lid>: int @index(int) .
			<hypernym>: [uid] @reverse .
			<antonym>: [uid] @reverse .
			<verseEmbeddings>: [uid] @reverse .
			<cn_term>: string @index(exact) .
			<collection>: string @index(exact) .
			<question>: string @index(exact) .
			<answer>: string @index(exact) .
			<referenceVerse>: [uid] @reverse .
			<language>: string @index(exact) .
			<title>: string @index(exact) .
			<externalUid>: string @index(exact) .
			<name>: string @index(exact) .
			<father>: [uid] @reverse .
			<mother>: [uid] @reverse .
			<spouse>: [uid] @reverse .
			<sameAs>: [uid] @reverse .
		'''

		self.set_schema(schema)
		logging.info("set set_schema")
	

	# Create a client stub.
	def create_client_stub(self):
		self.client_stub = pydgraph.DgraphClientStub('localhost:9080')
		# self.client_stub = pydgraph.DgraphClientStub('graph.bridgeconn.com:9080') # prod server
		# self.client_stub = pydgraph.DgraphClientStub('139.59.90.184:9080') # prod server
		# self.client_stub = pydgraph.DgraphClientStub('128.199.18.6:9080') # new staging server
		


	# Create a client.
	def create_client(self):
		self.client = pydgraph.DgraphClient(self.client_stub)


	# Drop All - discard all data and start from a clean slate.
	def drop_all(self):
		return self.client.alter(pydgraph.Operation(drop_all=True))


	# Set schema.
	def set_schema(self,schema=None):
		# for testing
		if not schema:
			schema = """
			name: string @index(exact) .
			friend: uid @reverse .
			age: int .
			married: bool .
			loc: geo .
			dob: datetime .
			"""
		self.client.alter(pydgraph.Operation(schema=schema))


	# Create data using JSON.
	def create_data(self,p=None):
		# Create a new transaction.
		txn = self.client.txn()
		try:
			if not p:
				# Create data for testing.
				p = {
					'name': 'Alice',
					'age': 26,
					'married': True,
					'loc': {
						'type': 'Point',
						'coordinates': [1.1, 2],
					},
					'dob': datetime.datetime(1980, 1, 1, 23, 0, 0, 0).isoformat(),
					'friend': [
						{
							'name': 'Bob',
							'age': 24,
						},
						{
							'name': 'Charlie',
							'age': 29,
						}
					],
					'school': [
						{
							'name': 'Crown Public School',
						}
					]
				}

			# Run mutation.
			assigned = txn.mutate(set_obj=p)
			
			# Commit transaction.
			txn.commit()

		except Exception as e:
			# raise e
			logging.info('*'*10)
			logging.info(e)
			logging.info('*'*10)
		finally:
			# Clean up. Calling this after txn.commit() is a no-op
			# and hence safe.
			txn.discard()

		# get the uid of the created nodes
		assigned = list(dict((assigned.uids)).values())

		if assigned:
			return_res = assigned[0]
		else:
			return_res = None
		return return_res


	#Deleting a data
	def delete_data(self,uids_to_delete=None):
		# Create a new transaction.
		txn = self.client.txn()
		
		try:
			for uid in uids_to_delete:
					query1 = """query all($a: string) {
						all(func: uid($a)) {
						   uid
						}
					}"""
					logging.info("uid:",uid['uid'])
					variables1 = {'$a': uid['uid']}
					res1 = self.client.txn(read_only=True).query(query1, variables=variables1)
					nodes = json.loads(res1.json)
					for node in nodes['all']:
						logging.info("deleting UID: " + node['uid'])
						txn.mutate(del_obj=node)
						logging.info('deleted')
			txn.commit()
		finally:
			txn.discard()


	# Query for data.
	def query_data(self,query=None,variables=None):
		# Run query.
		if not query:
			# for testing
			query = """query all($a: string) {
				all(func: eq(name, $a)) {
					uid
					name
					age
					married
					loc
					dob
					friend {
						name
						age
					}
					school {
						name
					}
				}
			}"""

			variables = {'$a': 'Alice'}
		# logging.info('variables:',variables)
		try:
			res = self.client.txn(read_only=True).query(query, variables=variables)
		except Exception as e:
			logging.info('**************Error***********')
			logging.info('variables:',variables)
			raise e
		return json.loads(res.json)

	def upsert(self, query=None, nquad=None, variables=None):
		if not query :
			query = """{
				  u as var(func: eq(name, "Alice"))
				}"""
		if not nquad:
			nquad = """
				  uid(u) <name> "Alice" .
				  uid(u) <age> "25" .
				"""
		txn = self.client.txn()
		mutation = txn.create_mutation(set_nquads=nquad)
		request = txn.create_request(query=query, mutations=[mutation], commit_now=True)
		txn.do_request(request) 
		return

if __name__ == '__main__':
	conn = dGraph_conn()
	logging.info("connection ok")
	# conn.delete_data(["0x3459","0x345a","0x345b","0x345c","0x345d","0x345e","0x345f"])

