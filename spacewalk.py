import requests, json, secrets, time, urllib, re

startTime = time.time()

# import secrets
ASbaseURL = secrets.ASbaseURL
ASuser = secrets.ASuser
ASpassword = secrets.ASpassword
DSbaseURL = secrets.DSbaseURL

# function to find key in nested dicts: see http://stackoverflow.com/questions/9807634/find-all-occurences-of-a-key-in-nested-python-dictionaries-and-lists
def gen_dict_extract(key, var):
    if hasattr(var,'iteritems'):
        for k, v in var.iteritems():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

# authenticate to ArchivesSpace
auth = requests.post(ASbaseURL + '/users/' + ASuser + '/login?password=' + ASpassword).json()
session = auth["session"]
headers = {'X-ArchivesSpace-Session':session}

# test for successful ArchivesSpace connection
def test_connection():
	try:
		requests.get(ASbaseURL)
		print 'Connected to ArchivesSpace!'
		return True
	except requests.exceptions.ConnectionError:
		print 'ArchivesSpace connection error. Please confirm ArchivesSpace is running.  Trying again in 10 seconds.'
is_connected = test_connection()
while not is_connected:
	time.sleep(10)
	is_connected = test_connection()

# Get Dspace item list
handle = '1774.2/41445'#raw_input('Enter handle: ')
DSendpoint = DSbaseURL + 'rest/handle/' + handle
collection = requests.get(DSendpoint).json()
collectionID = collection['id']
DSendpoint = DSbaseURL + 'rest/collections/' + str(collectionID)+ '/items'
itemList = requests.get(DSendpoint).json()
print itemList
# print 'Found ' + str(len(itemList)-1) + ' DSpace items attached to collection ' + collectionID + '.'

# Get all AOs from the resource record
resourceID = '1045' # raw_input('Enter resource ID: ')

ASendpoint = '/repositories/3/resources/'+resourceID+'/tree'
output = requests.get(ASbaseURL + ASendpoint, headers=headers).json()
archivalObjects = []
for value in gen_dict_extract('record_uri', output):
    if 'archival_objects' in value:
        archivalObjects.append(value)
print 'Found ' + str(len(archivalObjects)-1) + ' archival objects attached to resource ' + resourceID +'.'

for archivalObject in archivalObjects:
	output = requests.get(ASbaseURL + archivalObject, headers=headers).json()
	for instance in output['instances']:
		indicator_1 = instance['container']['indicator_1']
		indicator_1 = indicator_1.split('-')
		indicator_1a = indicator_1[0]
		indicator_1a = indicator_1a.rjust(2,'0')
		indicator_1b = re.sub('[a-z]', '', indicator_1[1])
		indicator_1b = indicator_1b.rjust(2,'0')
		try:
			indicator_2 = instance['container']['indicator_2']
			indicator_2 = '_' + indicator_2.rjust(2,'0')
		except:
			indicator_2 = ''
		try:
			indicator_3 = instance['container']['indicator_3']
			indicator_3 = '_' + indicator_3.rjust(2,'0')
		except:
			indicator_3 = ''
		potentialFilename = indicator_1a + '_' + indicator_1b + indicator_2 + indicator_3
		for item in itemList:
		    itemHandle = item['handle']
		    itemID = str(item['link'])
		    bitstreams = requests.get(DSbaseURL+itemID+'/bitstreams').json()
		    for bitstream in bitstreams:
		        fileName = bitstream['name']
		        strippedFileName = fileName.replace('.pdf','')
			if potentialFilename == strippedFileName:
				match = {}
				match['digital_object_id'] = DSbaseURL + itemHandle
				match['title'] = output['title'] + '(digital copy)'
				match['file_versions'] = [{'file_uri': DSbaseURL + itemHandle}]
				print match
				del itemList[0]

# show script runtime
elapsedTime = time.time() - startTime
m, s = divmod(elapsedTime, 60)
h, m = divmod(m, 60)
print 'Total script run time: ', '%d:%02d:%02d' % (h, m, s)
