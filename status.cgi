#!/usr/bin/python


###############
# IMPORTS

import cgitb; cgitb.enable() # for debugging
#import cgi # for getting query keys/values

from ClientDB import DB
db = DB('reddit.db')

import_failed = True
try:
	import json
	import_failed = False
except ImportError: pass

if import_failed:
	# Older versions of python don't work with 'json', so we use simplejson
	try:
		import simplejson as json
		import_failed = False
	except ImportError: pass

if import_failed:
	# If simplejson isn't found, we must be on Python 2.5 or below
	try:
		from JSON import json
	except ImportError:
		print '\un Unable to load JSON library! exiting'
		exit(1)


######################
# METHODS

def start():
	print to_json()

def get_count(table):
	return db.select("count(*)", table)[0][0]

def count_subs_db():
	return db.select("count(distinct subreddit)", "Posts")[0][0]

def count_subs_txt():
	f = open('subs.txt', 'r')
	subs = f.read().split('\n')
	f.close()
	while subs.count("") > 0:
		subs.remove("")
	return len(subs)

def to_json():
	dict = {
			'status' : {
				'posts'    : get_count('Posts'),
				'comments' : get_count('Comments'),
				'albums'   : get_count('Albums'),
				'images'   : get_count('Images'),
				'subreddits' : count_subs_db(),
				'subreddits_pending' : count_subs_txt()
			},
	}
	return json.dumps(dict)

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	start()
	print '\n\n'

