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
	return subs

def save_subs(subs):
	f = open('subs.txt', 'w')
	for sub in subs:
		f.write(sub + '\n')
	f.close()

def get_keys():
	""" Retrieves key/value pairs from query, puts in dict """
	form = cgi.FieldStorage()
	keys = {}
	for key in form.keys():
		keys[key] = form[key].value
	return keys

def main():
	keys = get_keys()
	if not 'subreddit' in keys:
		err = {}
		err['result'] = "no subreddit given"
		print json.dumps(err)
		return
	sub = keys['subreddit'].lower()
	while ' ' in sub: sub.replace(' ', '')
	
	subs = get_subs()
	if sub in subs:
		err = {}
		err['result'] = "subreddit already exists"
		print json.dumps(err)
		return
	
	subs.append(sub)
	save_subs(subs)
	
	j = {}
	j['result'] = "subreddit added"
	print json.dumps(j)

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	main()
	print '\n\n'

