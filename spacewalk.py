import requests, json, secrets, time, urllib, re, logging
logging.basicConfig(filename= time.strftime('%Y-%m-%d_%H%M%S') + '_spacewalk.log',format='%(levelname)s:%(message)s',level=logging.INFO)
startTime = time.time()

# import secrets
ASbaseURL = secrets.ASbaseURL
ASuser = secrets.ASuser
ASpassword = secrets.ASpassword
DSStagebaseURL = secrets.DSStagebaseURL
DSProdbaseURL = secrets.DSProdbaseURL

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
		print 'ArchivesSpace connection error. Please confirm ArchivesSpace is running. Trying again in 10 seconds.'
is_connected = test_connection()
while not is_connected:
	time.sleep(10)
	is_connected = test_connection()

# Account for ranges in indicator_2s
def hyphen_range(s):
    # Takes a range in form of "a-b" and generate a list of numbers between a and b inclusive.
    # Also accepts comma separated ranges like "a-b,c-d,f" will build a list which will include
    # Numbers from a to b, a to d and f
    s="".join(s.split()) #removes white space
    r=set()
    for x in s.split(','):
        t=x.split('-')
        if len(t) not in [1,2]: raise SyntaxError("hash_range is given its arguement as "+s+" which seems not correctly formated.")
        r.add(int(t[0])) if len(t)==1 else r.update(set(range(int(t[0]),int(t[1])+1)))
    l=list(r)
    l.sort()
    return l

# Get all AOs from the resource record
resourceID = '1045' # raw_input('Enter resource ID: ')
ASendpoint = '/repositories/3/resources/'+resourceID+'/tree'
output = requests.get(ASbaseURL + ASendpoint, headers=headers).json()
archivalObjects = []
for value in gen_dict_extract('record_uri', output):
    if 'archival_objects' in value:
        archivalObjects.append(value)
print 'Found ' + str(len(archivalObjects)-1) + ' archival objects attached to resource ' + resourceID +'.'

# Get Dspace item list
handle = '1774.2/41445'#raw_input('Enter handle: ')
DSendpoint = DSStagebaseURL + 'rest/handle/' + handle
if DSendpoint != '':
    print 'Connected to DSpace!'
else:
    print 'DSpace connection error. Please confirm DSpace is running.'
collection = requests.get(DSendpoint).json()
collectionID = collection['id']
DSendpoint = DSStagebaseURL + 'rest/collections/' + str(collectionID)+ '/items?limit=2800'
itemList = requests.get(DSendpoint).json()
print 'Found ' + str(len(itemList)) + ' DSpace items attached to collection.'
for item in itemList:
    match = {}
    DSitems = {}
    itemHandle = item['handle']
    itemID = str(item['link'])
    bitstreams = requests.get(DSStagebaseURL+itemID+'/bitstreams').json()
    for bitstream in bitstreams:
        fileName = bitstream['name']
        strippedFileName = fileName.replace('.pdf','')
    DSitems['strippedFileName'] = strippedFileName
    for archivalObject in archivalObjects:
        output = requests.get(ASbaseURL + archivalObject, headers=headers).json()
        aoURI = output['uri']
        for instance in output['instances']:
            if match == {}:
                try:
                    indicator_1 = instance['container']['indicator_1']
                    if indicator_1.startswith('1-'):
                        try:
                            indicator_2 = instance['container']['indicator_2']
                            if '-' in indicator_2 or ',' in indicator_2:
                                indicator_2s = hyphen_range(indicator_2)
                                for i in range(len(indicator_2s)):
                                    indicator_2 = '_' + str(indicator_2s[i]).rjust(2,'0')
                                    indicator_1 = instance['container']['indicator_1']
                                    indicator_1 = indicator_1.split('-')
                                    indicator_1a = indicator_1[0]
                                    indicator_1a = indicator_1a.rjust(2,'0')
                                    indicator_1b = re.sub('[a-z]', '', indicator_1[1])
                                    indicator_1b = indicator_1b.rjust(2,'0')
                                    try:
                                        indicator_3 = instance['container']['indicator_3']
                                        indicator_3 = '_' + indicator_3.rjust(2,'0')
                                    except:
                                        indicator_3 = ''
                                    potentialFilename = indicator_1a + '_' + indicator_1b + indicator_2 + indicator_3
                                    print 'Comparing ' + potentialFilename + ' to ' + DSitems['strippedFileName']
                                    if potentialFilename == DSitems['strippedFileName']:
                                        logging.info('Match between ' + potentialFilename + ' and ' + strippedFileName + '.')
                                        match['digital_object_id'] = DSProdbaseURL + itemHandle
                                        match['title'] = output['title']
                                        match['file_versions'] = [{'file_uri': DSProdbaseURL + itemHandle, 'publish': True}]
                                        match['linked_instances'] = [{'ref': output['uri']}]
                                        match['publish'] = True
                                        print 'Posting new digital object.'
                                        DOpost = requests.post(ASbaseURL + '/repositories/3/digital_objects', headers=headers, data=json.dumps(match)).json()
                                        logging.info(DOpost)
                                        if 'error' in DOpost:
                                            break
                                        instances = output['instances']
                                        digital_obj = {'ref': DOpost['uri']}
                                        digital_obj = {'instance_type': 'digital_object', 'digital_object': digital_obj}
                                        instances.append(digital_obj)
                                        output['instances'] = instances
                                        print 'Linking existing archival object.'
                                        AOpost = requests.post(ASbaseURL + aoURI, headers=headers, data=json.dumps(output)).json()
                                        logging.info(AOpost)
                                        break
                                    indicator_2 = instance['container']['indicator_2']
                                else:
                                    continue
                                break
                            else:
                                indicator_1 = indicator_1.split('-')
                                indicator_1a = indicator_1[0]
                                indicator_1a = indicator_1a.rjust(2,'0')
                                indicator_1b = re.sub('[a-z]', '', indicator_1[1])
                                indicator_1b = indicator_1b.rjust(2,'0')
                                indicator_2 = '_' + indicator_2.rjust(2,'0')
                                try:
                                    indicator_3 = instance['container']['indicator_3']
                                    indicator_3 = '_' + indicator_3.rjust(2,'0')
                                except:
                                    indicator_3 = ''
                                potentialFilename = indicator_1a + '_' + indicator_1b + indicator_2 + indicator_3
                                print 'Comparing ' + potentialFilename + ' to ' + DSitems['strippedFileName']
                                if potentialFilename == DSitems['strippedFileName']:
                                    logging.info('Match between ' + potentialFilename + ' and ' + strippedFileName + '.')
                                    match['digital_object_id'] = DSProdbaseURL + itemHandle
                                    match['title'] = output['title']
                                    match['file_versions'] = [{'file_uri': DSProdbaseURL + itemHandle, 'publish': True}]
                                    match['linked_instances'] = [{'ref': output['uri']}]
                                    match['publish'] = True
                                    print 'Posting new digital object.'
                                    DOpost = requests.post(ASbaseURL + '/repositories/3/digital_objects', headers=headers, data=json.dumps(match)).json()
                                    logging.info(DOpost)
                                    if 'error' in DOpost:
                                        break
                                    instances = output['instances']
                                    digital_obj = {'ref': DOpost['uri']}
                                    digital_obj = {'instance_type': 'digital_object', 'digital_object': digital_obj}
                                    instances.append(digital_obj)
                                    output['instances'] = instances
                                    print 'Linking existing archival object.'
                                    AOpost = requests.post(ASbaseURL + aoURI, headers=headers, data=json.dumps(output)).json()
                                    logging.info(AOpost)
                                    break
                        except:
                            indicator_2 = ''
                except:
                    continue
        else:
            continue
        break
    else:
        logging.warn('No match found for ' + strippedFileName)

# show script runtime
elapsedTime = time.time() - startTime
m, s = divmod(elapsedTime, 60)
h, m = divmod(m, 60)
print 'Total script run time: ', '%d:%02d:%02d' % (h, m, s)
