#!/usr/bin/python

######################
# Standard library   #
import cgitb; cgitb.enable() # for debugging
import cgi
import tempfile
from os   import path, close, remove
from sys  import argv
from time import sleep, time
import json

######################
# Database           #
from DB import DB
######################
# Image hashing      #
from ImageHash import avhash
######################
# Web                #
from Httpy import Httpy

######################
# Globals
db = DB('reddit.db') # Access to database
web = Httpy()        # Web functionality
# Constants
TRUSTED_AUTHORS    = ['4_pr0n', 'pervertedbylanguage', 'WakingLife']
TRUSTED_SUBREDDITS = ['AmateurArchives', 'gonewild', 'pornID', 'tipofmypenis', 'UnrealGirls']
MAX_ALBUM_SEARCH_DEPTH = 3  # Number of images to download from album
MAX_ALBUM_SEARCH_TIME  = 10 # Max time to search album in seconds

def main():
	""" Gets keys from query, performs search, prints results """
	keys = get_keys()
	func_map = { 
			'url'   : search_url,
			'user'  : search_user,
			'cache' : search_cache,
			'text'  : search_text
		}
	for key in func_map:
		if key in keys:
			func_map[key](keys[key])
			return
	print_error('did not receive expected key: url, user, cache, or text')

def get_results_tuple_for_image(url):
	""" Returns tuple of posts, comments, related for an image """
	url = sanitize_url(url)
	
	try:
		(hashid, downloaded) = get_hashid(url)
		if hashid == -1: # No hash matches
			return (url, [], [], [], downloaded)
		image_hashes = db.select('hash', 'Hashes', 'id = %d' % hashid)
		if len(image_hashes) == 0: raise Exception('could not get hash for %s' % url)
		image_hash = image_hashes[0][0]
	except Exception, e:
		raise e
	
	posts    = []
	comments = []
	related  = [] # Comments contaiing links found in posts
	
	# Get matching hashes in 'Images' table.
	# This shows all of the posts, comments, and albums containing the hash
	query_text  = 'hashid IN'
	query_text += ' (SELECT id FROM Hashes WHERE hash = "%s")' % (image_hash)
	query_text += ' GROUP BY postid, commentid'
	query_text += ' LIMIT 50'
	images = db.select('urlid, albumid, postid, commentid', 'Images', query_text)
	for (urlid, albumid, postid, commentid) in images:
		# Get image's URL, dimensions & size
		if commentid != 0:
			# Comment
			comment_dict = build_comment(commentid, urlid, albumid)
			comments.append(comment_dict)
		else:
			# Post
			post_dict = build_post(postid, urlid, albumid)
			posts.append(post_dict)
			
			related += build_related_comments(postid, urlid, albumid)
	posts    = sort_by_ranking(posts)
	comments = sort_by_ranking(comments)
	return (url, posts, comments, related, downloaded)

def get_hashid(url):
	""" 
		Retrieves hash ID ('Hashes' table) for image.
		Returns -1 if the image's hash was not found in the table.
		Does not modify DB! (read only)
	"""
	existing = db.select('hashid', 'ImageURLs', 'url = "%s"' % url)
	if len(existing) > 0:
		return (existing[0][0], False)
	
	# Download image
	(file, temp_image) = tempfile.mkstemp(prefix='redditimg', suffix='.jpg')
	close(file)
	if not web.download(url, temp_image):
		raise Exception('unable to download image at %s' % url)
	
	# Get image hash
	try:
		image_hash = str(avhash(temp_image))
		try: remove(temp_image)
		except: pass
	except Exception, e:
		# Failed to get hash, delete image & raise exception
		try: remove(temp_image)
		except: pass
		raise e
	
	# Get hashid from Hashes table
	hashids = db.select('id', 'Hashes', 'hash = "%s"' % (image_hash))
	if len(hashids) == 0:
		return (-1, True)
	return (hashids[0][0], True)
	
def search_url(url):
	""" Searches for a single URL, prints results """
	if url.lower().startswith('cache:'):
		search_cache(url[len('cache:'):])
		return
	elif 'imgur.com/a/' in url:
		search_album(url) # Searching album
		return
	elif url.lower().startswith('user:'):
		search_user(url[len('user:'):])
		return
	elif url.lower().startswith('text:'):
		search_text(url[len('text:'):])
		return
	elif 'reddit.com/u/' in url:
		search_user(url[url.find('/u/')+3:])
		return
	elif 'reddit.com/user/' in url:
		search_user(url[url.find('/user/')+6:])
		return
	elif 'reddit.com/r/' in url and '/comments/' in url:
		# Reddit post
		r = web.get(url)
		if '"url": "' in r:
			url = web.between(r, '"url": "', '"')[0]
	
	try:
		(url, posts, comments, related, downloaded) = \
				get_results_tuple_for_image(url)
	except Exception, e:
		print_error(str(e))
		return
	print json.dumps( {
			'posts'    : posts,
			'comments' : comments,
			'url'      : url,
			'related'  : related
		} )
	
def search_album(url):
	posts    = []
	comments = []
	related  = []
	checked_count    = 0
	time_started     = time()
	albumids = db.select('id', 'Albums', 'url = "%s"' % url)
	if len(albumids) > 0:
		# Album is already indexed
		albumid = albumids[0][0]
		query_text  = 'id IN '
		query_text += '(SELECT DISTINCT urlid FROM Images '
		query_text +=  'WHERE albumid = %d)' % albumid
		image_urls = db.select('url', 'ImageURLs', query_text)
		for image_url in image_urls:
			image_url = image_url[0]
			if time() - time_started > MAX_ALBUM_SEARCH_TIME: break
			checked_count += 1
			try:
				(imgurl, resposts, rescomments, resrelated, downloaded) = \
						get_results_tuple_for_image(image_url)
				'''
				# Old method; stop after one image returns results
				posts    += resposts
				comments += rescomments
				related  += resrelated
				if len(posts + comments + related) > 0: break
				'''
				# New method: Find as many results as possible, remove dupes
				merge_results(posts, resposts)
				merge_results(comments, rescomments)
				merge_results(related, resrelated)
			except Exception, e:
				continue
	else:
		# Album is not indexed; need to scrape images
		r = web.get('%s/noscript' % url)
		links = web.between(r, 'img src="http://i.', '"')
		if len(links) == 0:
			print_error('empty imgur album (404?)')
			return
		# Search stats
		downloaded_count = 0
		for link in links:
			if downloaded_count >= MAX_ALBUM_SEARCH_DEPTH: break
			if time() - time_started > MAX_ALBUM_SEARCH_TIME: break
			link = 'http://i.%s' % link
			if '?' in link: link = link[:link.find('?')]
			if '#' in link: link = link[:link.find('#')]
			link = imgur_get_highest_res(link)
			checked_count += 1
			try:
				(imgurl, resposts, rescomments, resrelated, downloaded) = \
						get_results_tuple_for_image(link)
				if downloaded: downloaded_count += 1
				'''
				posts    += resposts
				comments += rescomments
				related  += resrelated
				if len(posts + comments + related) > 0: break
				'''
				merge_results(posts, resposts)
				merge_results(comments, rescomments)
				merge_results(related, resrelated)
			except Exception, e:
				continue
	if len(posts + comments + related) == 0:
		print_error('searched %d images from album; no results found' % checked_count)
		return

	print json.dumps( {
			'url'      : url,
			'posts'    : posts,
			'comments' : comments,
			'related'  : related
		} )

def merge_results(source_list, to_add):
	for target in to_add:
		should_add = True
		# Check for duplicates
		for source in source_list:
			if target['hexid'] == source['hexid']:
				should_add = False
				break
		if should_add: source_list.append(target)

def search_user(user):
	""" Returns posts/comments by a reddit user """
	if user.strip() == '' or not is_user_valid(user):
		print_error('invalid username')
		return
	posts    = []
	comments = []
	related  = []
	# This search will pull up all posts and comments by the user
	# NOTE It will also grab all comments containing links in the user's posts (!)
	query_text  = 'postid IN '
	query_text += '(SELECT DISTINCT id FROM Posts '
	query_text +=  'WHERE author LIKE "%s" ' % user
	query_text +=  'ORDER BY ups DESC LIMIT 50) '
	query_text += 'OR '
	query_text += 'commentid IN '
	query_text += '(SELECT DISTINCT id FROM Comments '
	query_text +=  'WHERE author LIKE "%s" ' % user
	query_text +=  'ORDER BY ups DESC LIMIT 50) '
	query_text += 'GROUP BY postid, commentid' #LIMIT 50'
	# To avoid comments not created by the author, use this query:
	#query_text = 'commentid = 0 AND postid IN (SELECT DISTINCT id FROM Posts WHERE author LIKE "%s" ORDER BY ups DESC LIMIT 50) OR commentid IN (SELECT DISTINCT id FROM Comments WHERE author LIKE "%s" ORDER BY ups DESC LIMIT 50) GROUP BY postid, commentid LIMIT 50' % (user, user)
	images = db.select('urlid, albumid, postid, commentid', 'Images', query_text)
	for (urlid, albumid, postid, commentid) in images:
		# Get image's URL, dimensions & size
		if commentid != 0:
			# Comment
			comment_dict = build_comment(commentid, urlid, albumid)
			comments.append(comment_dict)
		else:
			# Post
			post_dict = build_post(postid, urlid, albumid)
			posts.append(post_dict)
			
			related += build_related_comments(postid, urlid, albumid)
	posts    = sort_by_ranking(posts)
	comments = sort_by_ranking(comments)
	print json.dumps( {
			'url'      : 'user:%s' % user, #'http://reddit.com/user/%s' % user,
			'posts'    : posts,
			'comments' : comments,
			'related'  : related
		} )

def search_cache(url):
	"""
		Prints list of images inside of an album
		The images are stored in the database, so 404'd albums
		can be retrieved via this method (sometimes)
	"""
	try:
		url = sanitize_url(url)
	except Exception, e:
		print_error(str(e))
		return
	images = []
	query_text = 'id IN (SELECT urlid FROM Images WHERE albumid IN (SELECT DISTINCT id FROM albums WHERE url = "%s"))' % (url)
	image_tuples = db.select('id, url', 'ImageURLs', query_text)
	for (urlid, imageurl) in image_tuples:
		image = {
				'thumb' : 'thumbs/%d.jpg' % urlid,
				'url'   : imageurl
			}
		images.append(image)
	print json.dumps( {
			'url'    : 'cache:%s' % url,
			'images' : images
		} )

def search_text(text):
	""" Prints posts/comments containing text in title/body. """
	posts    = []
	comments = []
	related  = []
	query_text = 'commentid = 0 AND postid IN (SELECT DISTINCT id FROM Posts WHERE title LIKE "%%%s%%" or text LIKE "%%%s%%" ORDER BY ups DESC LIMIT 50) OR commentid IN (SELECT DISTINCT id FROM Comments WHERE body LIKE "%%%s%%" ORDER BY ups DESC LIMIT 50) GROUP BY postid, commentid LIMIT 50' % (text, text, text)
	images = db.select('urlid, albumid, postid, commentid', 'Images', query_text)
	for (urlid, albumid, postid, commentid) in images:
		# Get image's URL, dimensions & size
		if commentid != 0:
			# Comment
			comment_dict = build_comment(commentid, urlid, albumid)
			comments.append(comment_dict)
		else:
			# Post
			post_dict = build_post(postid, urlid, albumid)
			posts.append(post_dict)
			
			related += build_related_comments(postid, urlid, albumid)
	posts    = sort_by_ranking(posts)
	comments = sort_by_ranking(comments)
	print json.dumps( {
			'url'      : 'text:%s' % text,
			'posts'    : posts,
			'comments' : comments,
			'related'  : related
		} )


###################
# "Builder" methods
			
def build_post(postid, urlid, albumid):
	""" Builds dict containing attributes about a post """
	item = {} # Dict to return
	# Thumbnail
	item['thumb'] = 'thumbs/%d.jpg' % urlid
	if not path.exists(item['thumb']): item['thumb'] = ''
	
	# Get info about post
	(		postid,            \
			item['hexid'],     \
			item['title'],     \
			item['url'],       \
			item['text'],      \
			item['author'],    \
			item['permalink'], \
			item['subreddit'], \
			item['comments'],  \
			item['ups'],       \
			item['downs'],     \
			item['score'],     \
			item['created'],   \
			item['is_self'],   \
			item['over_18'])   \
		= db.select('*', 'Posts', 'id = %d' % (postid))[0]
	# Get info about image
	(		item['imageurl'], \
			item['width'],    \
			item['height'],   \
			item['size'])     \
		= db.select('url, width, height, bytes', 'ImageURLs', 'id = %d' % urlid)[0]
	# Set URL to be the album (if it's an album)
	if albumid != 0:
		item['url'] = db.select("url", "Albums", "id = %d" % albumid)[0][0]
	return item
	
def build_comment(commentid, urlid, albumid):
	""" Builds dict containing attributes about a comment """
	item = {} # Dict to return
	
	# Thumbnail
	item['thumb'] = 'thumbs/%d.jpg' % urlid
	if not path.exists(item['thumb']): item['thumb'] = ''
	
	# Get info about comment
	(   comid,           \
			postid,          \
			item['hexid'],   \
			item['author'],  \
			item['body'],    \
			item['ups'],     \
			item['downs'],   \
			item['created']) \
		= db.select('*', 'Comments', 'id = %d' % commentid)[0]
	
	# Get info about post comment is replying to
	(		item['subreddit'], \
			item['permalink'], \
			item['postid'])    \
		= db.select('subreddit, permalink, hexid', 'Posts', 'id = %d' % (postid))[0]
	# Get info about image
	(		item['imageurl'], \
			item['width'],    \
			item['height'],   \
			item['size'])     \
		= db.select('url, width, height, bytes', 'ImageURLs', 'id = %d' % urlid)[0]
	if albumid != 0:
		item['url'] = db.select("url", "Albums", "id = %d" % albumid)[0][0]
	return item

def build_related_comments(postid, urlid, albumid):
	""" Builds dict containing attributes about a comment related to a post"""
	items = [] # List to return
	#return items
	
	# Get info about post comment is replying to
	(		postsubreddit, \
			postpermalink, \
			posthex)   \
		= db.select('subreddit, permalink, hexid', 'Posts', 'id = %d' % postid)[0]
	
	# Get & iterate over comments
	for (   comid,      \
					postid,     \
					comhexid,   \
					comauthor,  \
					combody,    \
					comups,     \
					comdowns,   \
					comcreated) \
					in db.select('*', 'Comments', 'postid = %d' % postid):
		item = {
			# Post-specific attributes
			'subreddit' : postsubreddit,
			'permalink' : postpermalink,
			'postid'    : posthex,
			# Comment-specific attributes
			'hexid'   : comhexid,
			'author'  : comauthor,
			'body'    : combody,
			'ups'     : comups,
			'downs'   : comdowns,
			'created' : comcreated,
			'thumb'   : '',
			# Image-specific attributes (irrelevant)
			'imageurl': '',
			'width'   : 0,
			'height'  : 0,
			'size'    : 0
		}
		items.append(item)
	return items

########################
# Helper methods

def print_error(text):
	print json.dumps({'error': text})

def get_keys():
	""" Returns key/value pairs from query, uses CLI args if none found. """
	form = cgi.FieldStorage()
	keys = {}
	for key in form.keys():
		keys[key] = form[key].value
	if len(keys) == 0 and len(argv) > 2:
		keys = { argv[1] : argv[2] }
	return keys

def sort_by_ranking(objs):
	""" Sorts list of posts/comments based on heuristic. """
	for obj in objs:
		if 'comments' in obj:
			obj['ranking']  = int(obj['comments'])
			obj['ranking'] += int(obj['ups'])
		else:
			obj['ranking'] = int(obj['ups'])
		if 'url' in obj and 'imgur.com/a/' in obj['url'] \
				or 'imageurl' in obj and 'imgur.com/a/' in obj['imageurl']:
			obj['ranking'] += 600
		if obj['author'] in TRUSTED_AUTHORS:
			obj['ranking'] += 500
		if obj['subreddit'] in TRUSTED_SUBREDDITS:
			obj['ranking'] += 400
	return sorted(objs, reverse=True, key=lambda tup: tup['ranking'])

def sanitize_url(url):
	""" 
		Retrieves direct link to image based on URL.
		Throws Exception if unable to find direct image.
	"""
	url = url.strip()
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	if url == '' or not '.' in url:
		raise Exception('invalid URL')
	
	if not '://' in url: url = 'http://%s' % url # Fix for what'shisface who forgets to prepend http://
	
	while url.endswith('/'): url = url[:-1]
	if 'imgur.com' in url:
		if '.com/a/' in url:
			# Album
			url = url.replace('http://', '').replace('https://', '')
			while url.endswith('/'): url = url[:-1]
			while url.count('/') > 2: url = url[:url.rfind('/')]
			if '?' in url: url = url[:url.find('?')]
			if '#' in url: url = url[:url.find('#')]
			url = 'http://%s' % url # How the URL will be stored in the DB
			return url

		elif url.lower().endswith('.jpeg') or \
				url.lower().endswith('.jpg') or \
				url.lower().endswith('.png') or \
				url.lower().endswith('.gif'):
			# Direct imgur link, find highest res
			url = imgur_get_highest_res(url)
			# Drop out of if statement & parse image
		else:
			# Indirect imgur link (e.g. "imgur.com/abcde")
			r = web.get(url)
			if '"image_src" href="' in r:
				url = web.between(r, '"image_src" href="', '"')[0]
			else:
				raise Exception("unable to find imgur image (404?)")
	elif url.lower().endswith('.jpg') or \
			url.lower().endswith('.jpeg') or \
			url.lower().endswith('.png')  or \
			url.lower().endswith('.gif'):
		# Direct link to non-imgur image
		pass # Drop out of if statement & parse image
	else:
		# Not imgur, not a direct link; no way to parse
		raise Exception("unable to parse non-direct, non-imgur link")
	return url

def imgur_get_highest_res(url):
	""" Retrieves highest-res imgur image """
	if not 'h.' in url:
		return url
	temp = url.replace('h.', '.')
	m = web.get_meta(temp)
	if 'Content-Type' in m and 'image' in m['Content-Type'].lower():
		return temp
	else:
		return url

def is_user_valid(username):
	""" Checks if username is valid reddit name, assumes lcase/strip """
	allowed = 'abcdefghijklmnopqrstuvwxyz1234567890_-'
	valid = True
	for c in username.lower():
		if not c in allowed:
			valid = False
			break
	return valid

if __name__ == '__main__':
	""" Entry point. Only run when executed; not imported. """
	print "Content-Type: application/json"
	print ""
	main()
	print '\n'
