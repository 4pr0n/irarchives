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

# Checks if username is a valid reddit username
# Assumes input is lowercase & stripped of whitespace
def is_user_valid(username):
	allowed = 'abcdefghijklmnopqrstuvwxyz1234567890_-'
	valid = True
	for c in username.lower():
		if not c in allowed:
			valid = False
			break
	return valid

######################
# SEARCH BY USER
def get_user(user, start=0, count=50):
	user = user.replace('\'', '').replace('"', '').replace('\\', '')
	ps = db.select('*', 'Posts', 'author like "%s" order by ups DESC LIMIT %d' % (user, count))
	#ps = sorted(ps, reverse=True, key=lambda tup: tup[9])
	posts = []
	index = 0
	for (id, hexid, title, url, text, author, permalink, subreddit, comments, ups, downs, score, created, is_self, over_18) in ps:
		index += 1
		if index < start: continue
		count -= 1
		if count < 0: break
		p = {}
		p['width'] = ''
		p['height'] = ''
		p['size'] = ''
		p['hexid'] = hexid
		p['title'] = title.replace('<', '&lt;').replace('>', '&gt;')
		p['thumb'] = ''
		p['url'] = url
		p['text'] = text.replace('<', '&lt;').replace('>', '&gt;')
		p['author'] = author
		p['permalink'] = permalink
		p['subreddit'] = subreddit
		p['comments'] = comments
		p['ups'] = ups
		p['downs'] = downs
		p['score'] = score
		p['created'] = created
		p['is_self'] = is_self
		p['over_18'] = over_18
		posts.append(p)
	comments = []
	cs = db.select('*', 'Comments', 'author like "%s" ORDER BY ups LIMIT %d' % (user, count))
	for (id, postid, hexid, author, body, ups, downs, created) in cs:
		comment = {}
		comment['width'] = 0
		comment['height'] = 0
		comment['size'] = 0
		comment['body'] = body.replace('<', '&lt;').replace('>', '&gt;')
		comment['author'] = author
		comment['hexid'] = hexid
		comment['ups'] = ups
		comment['downs'] = downs
		comment['postid'] = postid
		comment['created'] = created
		comment['thumb'] = ''
		comments.append(comment)
	result = {}
	result['posts'] = posts;
	result['comments'] = comments;
	print json.dumps(result)
	print '\n\n'

def get_album_images(url):
	images = []
	albumids = db.select('id', 'Albums', 'url = "%s"' % url)
	if len(albumids) > 0:
		urlids = db.select('urlid', 'Images', 'albumid = %d' % albumids[0][0])
		for urlid in urlids:
			imgs = db.select('url', 'ImageURLs', 'id = %d' % urlid)
			if len(imgs) > 0:
				image = {}
				if path.exists('thumbs/%d.jpg' % urlid):
					image['thumb'] = 'thumbs/%d.jpg' % urlid
				image['url'] = imgs[0][0]
				images.append(image)
	result = {}
	result['images'] = images
	print json.dumps(result)
	print '\n'

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
		if url.strip() == '' or not '.' in url:
			print '{"error": "invalid url"}\n\n'
			return
		if url.startswith('album:'):
			get_album_images(url[len('album:'):])
			return
		# Check if URL is already in database
		# (Don't download unless we have to)
		imageurls = db.select('*', 'ImageURLs', 'url = "%s"' % (url))
		if len(imageurls) > 0:
			# URL has already been downloaded/hashed/calculated
			(urlid, url, hashid, width, height, bytes) = imageurls[0]
			hash = db.select('hash', 'Hashes', 'id = %d' % (hashid))[0][0]
		else:
			# Download and collect image information 
			# (hash, dimensions, size) located at 'url'
			(hash, width, height, bytes, url) = get_image_info(url)
			if hash == None or hash == '':
				print json.dumps({"err": 'could not retrieve image from url<br>' + \
					'please use <a style="color: #f66; text-decoration: underline" ' + \
					'href="http://www.wikihow.com/Get-the-URL-for-Pictures">direct links to images</a>'})
				return
	elif 'user' in keys:
		user = keys['user']
		if not is_user_valid(user):
			print '{"error": "invalid username"}\n\n'
			return
		if 'start' in keys and 'count' in keys:
			start = keys['start']
			count = keys['count']
		else:
			start = 0
			count = 50
		try:
			get_user(user, start, count)
		except:
			print '{"error": "error while searching for user"}\n\n'
		return
	else:
		print '{"error": "unexpected error occurred"}\n\n'
		return
	
	if hash == None:
		err = {}
		err['error'] = "no url given"
		print json.dumps(err)
		return
	if hash == '':
		result = {}
		result['posts']    = []
		result['comments'] = []
		result['url']      = url
		print json.dumps(result)
		return
	
	# TODO Return dimensions/filesize of image-to-search
	
	posts    = []
	comments = []
	# Search for image by hash 'hash'
	images = db.select('*', 'Images', 'hashid in (select id from Hashes where hash = "%s") group by postid, commentid' % (hash))
	for (urlid, hashid, albumid, postid, commentid) in images:
		# TODO Lookup image's dimensions/sizes for each result
		(imageurl, width, height, size) = db.select('url, width, height, bytes', 'ImageURLs', 'id = %d' % (urlid))[0]
		item = {}
		if commentid != 0:
			# comment
			(id, postid, hexid, author, body, ups, downs, created) = \
					db.select('*', 'Comments', 'id = %d' % (commentid))[0]
			post_hexid = db.select('hexid', 'Posts', 'id = %d' % (postid))[0][0]
			item = {}
			item['imageurl']= imageurl
			item['width']   = width
			item['height']  = height
			item['size']    = size
			if path.exists('thumbs/%d.jpg' % urlid):
				item['thumb'] = 'thumbs/%d.jpg' % urlid
			else:
				item['thumb'] = ''
			item['hexid']   = hexid
			item['postid']  = post_hexid
			item['author']  = author
			item['body']    = body
			item['ups']     = ups
			item['downs']   = downs
			item['created'] = created
			item['ranking'] = ups
			comments.append(item)
		else:
			# post
			(id, hexid, title, posturl, text, author, permalink, subreddit, \
			 num_comments, ups, downs, score, created, is_self, over_18) = \
					db.select('*', 'Posts', 'id = %d' % (postid))[0]
			item = {}
			item['width']     = width
			item['height']    = height
			item['size']      = size
			if path.exists('thumbs/%d.jpg' % urlid):
				item['thumb'] = 'thumbs/%d.jpg' % urlid
			else:
				item['thumb'] = ''
			item['hexid']     = hexid
			item['title']     = title
			item['url']       = posturl
			item['imageurl']  = imageurl
			item['text']      = text
			item['author']    = author
			item['permalink'] = permalink
			item['subreddit'] = subreddit
			item['comments']  = num_comments
			item['ups']       = ups
			item['downs']     = downs
			item['score']     = score
			item['created']   = created
			item['is_self']   = int(is_self)
			item['over_18']   = int(over_18)
			item['ranking']   = 0
			
			count = 0
			# Get comments containing albums in this post
			for (comid, compostid, comhexid, comauthor, combody, comups, comdowns, comcreated) in \
					db.select('*', 'Comments', 'postid = %d' % id):
				count += 1
				#if not 'imgur.com/a/' in combody: continue
				citem = {}
				citem['imageurl']= ''
				citem['width']   = 0
				citem['height']  = 0
				citem['size']    = ''
				citem['thumb']   = ''
				citem['hexid']   = comhexid # Link to comment
				citem['postid']  = hexid # From parent post
				citem['author']  = comauthor
				citem['body']    = combody
				citem['ups']     = comups
				citem['downs']   = comdowns
				citem['created'] = comcreated
				citem['ranking'] = comups
				comments.append(citem)
			item['counties'] = count
			posts.append(item)

			
			if len(posts) >= 40: break
		
		if albumid != 0:
			u = db.select("url", "Albums", "id = %d" % albumid)[0][0]
			item['url'] = u
	
	# Sorting algorithm (favors me & source subreddits)
	for post in posts:
		post['ranking'] += int(post['comments'])
		if post['author'] in ['pervertedbylanguage', 'WakingLife', '4_pr0n']:
			post['ranking'] += 500
		if post['subreddit'] in ['tipofmypenis', 'pornID', 'gonewild', 'AmateurArchives']:
			post['ranking'] += 500
	for comment in comments:
		comment['ups'] += int(comment['ups'])
		if comment['author'] in ['pervertedbylanguage', 'WakingLife', '4_pr0n']:
			comment['ranking'] += 500
	posts = sorted(posts, reverse=True, key=lambda tup: tup['ranking'])
	comments = sorted(comments, reverse=True, key=lambda tup: tup['ranking'])
	result = {}
	result['posts']    = posts
	result['comments'] = comments
	result['url']      = url
	print json.dumps(result)
	


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
	""" Gets image hash, width, height, bytes, and URL based on image in URL. """
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	if not '.' in url: return ('', 0, 0, 0, '')
	
	if 'reddit.com' in url:
		# reddit link; find the URL
		if not url.endswith('.json'): url += '.json'
		r = web.get(url)
		if not '"url": "' in r: return ('', 0, 0, 0, '')
		url = web.between(r, '"url": "', '"')[0]
	
	if 'imgur.com' in url and 'imgur.com/a/' in url:
		# imgur album
		while url.endswith('/'): url = url[:-1]
		r = web.get('%s/noscript' % url)
		if not 'src="http://i.imgur.com/' in r: return ('', 0, 0, 0, '')
		url = 'http://i.imgur.com/%s' % web.between(r, 'src="http://i.imgur.com/', '"')[0]
		if 'h.' in url:
			tempurl = url.replace('h.', '.')
			m = web.get_meta(tempurl)
			if 'Content-Type' in m and 'image' in m['Content-Type']:
				url = tempurl
		
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	if not '.' in url: return ('', 0, 0, 0, '')
	ext = url.lower()[url.rfind('.') + 1:]
	
	if ext in ['jpg', 'jpeg', 'gif', 'png']:
		url = url.replace('http://imgur.com', 'http;//i.imgur.com')
	
	elif 'imgur.com' in url and not 'imgur.com/a/' in url:
		# Single image, need to get direct link to image (imgur.com/ASDF1 to i.imgur.com/ASDF1.jpg)
		r = web.get(url)
		urls = web.between(r, '<link rel="image_src" href="', '"')
		if len(urls) == 0: return ('', 0, 0, 0, '')
		url = urls[0].strip()
		url = url.replace('http://imgur.com', 'http://i.imgur.com')
		ext = url.lower()[url.rfind('.') + 1:]
	else:
		# Not hot-linked and non-imgur image; can't get hash.
		return ('', 0, 0, 0, '')
	
	# Download image
	if '?' in ext: ext = ext[:ext.find('?')]
	(file, temp_image) = tempfile.mkstemp(prefix='redditimg', suffix='.'+ext)
	close(file)
	if not web.download(url, temp_image): return ('', 0, 0, 0, '')
	
	# Calculate hash of downloaded jmage
	try:                hash = str(avhash(temp_image))
	except IOError:     hash = ''
	except IndexError:  hash = ''
	except MemoryError: hash = ''
	
	# We must have a hash to add image to database
	if hash == '': 
		try: remove(temp_image) # Delete the temporary file
		except OSError: pass
		return ('', 0, 0, 0, '')
	
	(width, height) = dimensions(temp_image)
	filesize = path.getsize(temp_image)
	
	return (hash, width, height, filesize, url)


######################
# ENTRY POINT

if __name__ == '__main__':
	print "Content-Type: application/json"
	print ""
	start()
	print '\n\n'

