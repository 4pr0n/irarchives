#!/usr/bin/python

import cgitb; cgitb.enable() # for debugging
import cgi # for getting query keys/values

from JSON import json

def get_subs():
	f = open('subs.txt', 'r')
	subs = f.read().lower().split('\n')
	f.close()
	while subs.count("") > 0:
		subs.remove("")
	print json.dumps({'subreddits': subs})

def get_keys():
	""" Retrieves key/value pairs from query, puts in dict """
	form = cgi.FieldStorage()
	keys = {}
	for key in form.keys():
		keys[key] = form[key].value
	return keys

def main():
	keys = get_keys()
	if 'get' in keys:
		get_subs()
		return
	print json.dumps({'error': 'no valid keys given'})

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	main()
	print '\n\n'
