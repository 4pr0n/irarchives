#!/usr/bin/python


###############
# IMPORTS

#import cgitb; cgitb.enable() # for debugging
import cgi # for getting query keys/values

from ClientDB import DB
db = DB('reddit.db')

from ImageHash import avhash, dimensions

from Web import Web

import tempfile
from os import path, close, remove
from sys import argv
from time import sleep

web = Web()

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
# MAIN METHOD

def start():
	hash = None
	keys = get_keys()
	if len(keys) == 0:
		keys = { 'url': argv[1] }
	if 'url' in keys:
		url = keys['url']
		url = url.replace('"', '%22')
		# Check if URL is already in database
		# (Don't download unless we have to)
		imageurls = db.select('*', 'ImageURLs', 'url = "%s"' % (url))
		if len(imageurls) > 0:
			print "URL is in database"
			for asdf in imageurls:
				print asdf
			# URL has already been downloaded/hashed/calculated
			(urlid, url, hashid, width, height, bytes) = imageurls[0]
			print 'hashid = %d' % hashid
			hash = db.select('hash', 'Hashes', 'id = %d' % (hashid))[0][0]
			print 'hash = %s' % hash
		else:
			print "URL not in database, downloading"
			# Download and collect image information 
			# (hash, dimensions, size) located at 'url'
			(hash, width, height, bytes) = get_image_info(url)
			print 'hash = %s' % hash
	
	if hash == None:
		err = {}
		err['error'] = "no url given"
		print json.dumps(err)
		return
	if hash == '':
		result = {}
		result['posts']    = []
		result['comments'] = []
		result['albums']   = []
		print json.dumps(result)
		return
	
	# TODO Return dimensions/filesize of image-to-search
	
	posts    = []
	comments = []
	albums   = []
	# Search for image by hash 'hash'
	images = db.select('*', 'Images', 'hashid in (select id from Hashes where hash = "%s")' % (hash))
	for (urlid, hashid, albumid, postid, commentid) in images:
		print "found: urlid = %d" % urlid
		# TODO Lookup image's dimensions/sizes for each result
		(width, height, size) = db.select('width, height, bytes', 'ImageURLs', 'id = %d' % (urlid))[0]
		if commentid != 0:
			# comment
			(id, postid, hexid, author, body, ups, downs, created) = \
					db.select('*', 'Comments', 'id = %d' % (commentid))[0]
			post_hexid = db.select('hexid', 'Posts', 'id = %d' % (postid))[0][0]
			comment = {}
			comment['width']   = width
			comment['height']  = height
			comment['size']    = size
			if path.exists('thumbs/%d.jpg' % urlid):
				comment['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
			else:
				web.download('http://i.derv.us/thumbs/%d.jpg' % urlid, 'thumbs/%d.jpg' % urlid)
				comment['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
				# comment['thumb'] = 'http://i.derv.us/thumbs/%d.jpg' % urlid
			comment['hexid']   = hexid
			comment['postid']  = post_hexid
			comment['author']  = author
			comment['body']    = body
			comment['ups']     = ups
			comment['downs']   = downs
			comment['created'] = created
			comments.append(comment)
		else:
			# post
			(id, hexid, title, posturl, text, author, permalink, subreddit, \
			 num_comments, ups, downs, score, created, is_self, over_18) = \
					db.select('*', 'Posts', 'id = %d' % (postid))[0]
			post = {}
			post['width']     = width
			post['height']    = height
			post['size']      = size
			if path.exists('thumbs/%d.jpg' % urlid):
				post['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
			else:
				web.download('http://i.derv.us/thumbs/%d.jpg' % urlid, 'thumbs/%d.jpg' % urlid)
				post['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
				#post['thumb'] = 'http://i.derv.us/thumbs/%d.jpg' % urlid
			post['hexid']     = hexid
			post['title']     = title
			post['url']       = posturl
			post['text']      = text
			post['author']    = author
			post['permalink'] = permalink
			post['subreddit'] = subreddit
			post['comments']  = num_comments
			post['ups']       = ups
			post['downs']     = downs
			post['score']     = score
			post['created']   = created
			post['is_self']   = int(is_self)
			post['over_18']   = int(over_18)
			posts.append(post)
		if albumid != 0:
			# also, in an album
			albumurl = db.select('url', 'Albums', 'id = %d' % (albumid))[0][0]
			album = {}
			album['width']  = width
			album['height'] = height
			album['size']   = size
			if path.exists('thumbs/%d.jpg' % urlid):
				album['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
			else:
				web.download('http://i.derv.us/thumbs/%d.jpg' % urlid, 'thumbs/%d.jpg' % urlid)
				album['thumb'] = 'http://i.rarchives.com/thumbs/%d.jpg' % urlid
				# album['thumb'] = 'http://i.derv.us/thumbs/%d.jpg' % urlid
			album['url']    = albumurl
			if albums.count(album) == 0:
				albums.append(album)
	
	result = {}
	result['posts']    = posts
	result['comments'] = comments
	result['albums']   = albums
	print json.dumps(result)
	
	'''
	try_again = True
	while try_again:
		# Insert image we just searched into database (if not already there)
		try_again = False
		try:
			newid = db.insert('Hashes', (None, hash))
		except Exception, e:
			try_again = True
			sleep(0.5)
	if newid == -1:
		hashids = db.select('id', 'Hashes', 'hash = "%s"' % (hash))
		if len(hashids) == 0: return
		newid = hashids[0][0]
	
	# Insert successful
	try_again = True
	while try_again:
		try_again = False
		try:
			db.insert('ImageURLs', (None, url, newid, width, height, bytes))
		except Exception, e:
			try_again = True
			sleep(0.5)
	try_again = True
	while try_again:
		try_again = False
		try:
			db.commit()
		except Exception, e:
			try_again = True
			sleep(0.5)
	'''


######################
# HELPER METHODS

def get_keys():
	""" Retrieves key/value pairs from query, puts in dict """
	form = cgi.FieldStorage()
	keys = {}
	for key in form.keys():
		keys[key] = form[key].value
	return keys


def get_image_info(url):
	""" Gets image hash (int) based on image in URL. Returns 0 if not found. """
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	if not '.' in url: return ('', 0, 0, 0)
	ext = url.lower()[url.rfind('.') + 1:]
	
	if 'reddit.com' in url:
		# TODO reddit link. retrieve post url
		return ('', 0, 0, 0)
	elif ext in ['jpg', 'jpeg', 'gif', 'png']:
		url = url.replace('http://imgur.com', 'http;//i.imgur.com')
	
	elif 'imgur.com' in url and not '.com/a/' in url:
		# Single image, need to get direct link to image (imgur.com/ASDF1 to i.imgur.com/ASDF1.jpg)
		r = web.get(url)
		urls = web.between(r, '<link rel="image_src" href="', '"')
		if len(urls) == 0: return ('', 0, 0, 0)
		url = urls[0].strip()
		url = url.replace('http://imgur.com', 'http://i.imgur.com')
		ext = url.lower()[url.rfind('.') + 1:]
	else:
		# Not hot-linked and non-imgur image; can't get hash.
		return ('', 0, 0, 0)
	
	# Download image
	if '?' in ext: ext = ext[:ext.find('?')]
	(file, temp_image) = tempfile.mkstemp(prefix='redditimg', suffix='.'+ext)
	close(file)
	if not web.download(url, temp_image): return ('', 0, 0, 0)
	
	# Calculate hash of downloaded jmage
	try:                hash = str(avhash(temp_image))
	except IOError:     hash = ''
	except IndexError:  hash = ''
	except MemoryError: hash = ''
	
	# We must have a hash to add image to database
	if hash == '': 
		try: remove(temp_image) # Delete the temporary file
		except OSError: pass
		return ('', 0, 0, 0)
	
	(width, height) = dimensions(temp_image)
	filesize = path.getsize(temp_image)
	
	return (hash, width, height, filesize)


######################
# ENTRY POINT

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	start()
	print '\n\n'

