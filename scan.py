#!/usr/bin/python

"""
	scan.py
	
	What this script does:
		1. Scans reddit.com for new posts/comments
		2. Retrieves images from posts/comments
		3. Stores image information (hash, size, etc) in a database
		4. If post/comment contains image, stores post/comment info in database
	
	TODO
		* Get more sleep; don't program when tired.
	
	(LOW PRIORITY)
		* min.us support, tumblr support, postimage? (check domain on reddit for relevancy)
		
		* Multithreading for image hashing?
		... SQLite 3.x allows multithreading in python. We shouldn't upgrade b/c web server is outdated as hell
		... DB can only be connected/written/committed from a single thread.
		... Possible solution: Create separate lists for Images, ImageURLs, Hashes, Comments
		... ... These lists would contain Tuples to be inserted into the respective Tables
		... ... Main thread would read these lists and insert tuples into appropriate Table
		... **** QUESTION: How would the worker threads check for duplicates; and how would Image table know the Post/Comment's ID?
		... **** ANSWER:   THIS IS IMPOSSIBLE USING THE CURRENT PROGRAM STRUCTURE. single-threaded ftl ;\
"""

from os import path, close, remove
from sys import exit, stdout

# Reddit username/password contained in text file, separated by new line characters
if not path.exists('login_credentials.txt'):
	print 'need login credentials (username and password, separated by new line) in text file login_credentials.txt'
	exit(1)
login_file = open('login_credentials.txt')
login_list = login_file.read().split('\n')
login_file.close()
if len(login_list) < 2:
	print 'need login credentials (username and password, separated by new line) in text file login_credentials.txt'
	exit(1)
REDDIT_USER     = login_list[0]
REDDIT_PASSWORD = login_list[1]


# Database schema
SCHEMA = {
		'Posts' : 
			'\n\t' +
			'id        INTEGER PRIMARY KEY, \n\t' +
			'hexid     TEXT UNIQUE, \n\t' + # base36 reddit id to comment
			'title     TEXT,    \n\t' +
			'url       TEXT,    \n\t' +
			'text      TEXT,    \n\t' + # self-text
			'author    TEXT,    \n\t' +
			'permalink TEXT,    \n\t' + # /r/Subreddit/comments/id/title
			'subreddit TEXT,    \n\t' + 
			'comments  INTEGER, \n\t' + # Number of comment
			'ups       INTEGER, \n\t' +
			'downs     INTEGER, \n\t' +
			'score     INTEGER, \n\t' +
			'created   INTEGER, \n\t' + # Time in UTC
			'is_self   NUMERIC, \n\t' +
			'over_18   NUMERIC',
			
		'Comments' :
			'\n\t' +
			'id      INTEGER PRIMARY KEY, \n\t' +
			'postid  INTEGER, \n\t' +  # Reference to Posts table
			'hexid   TEXT UNIQUE, \n\t' + # base36 reddit id to comment
			'author  TEXT,    \n\t'    +
			'body    TEXT,    \n\t'    +
			'ups     INTEGER, \n\t' +
			'downs   INTEGER, \n\t' +
			'created INTEGER, \n\t' + # Time in UTC
			'FOREIGN KEY(postid) REFERENCES Posts(id)',
			
		'Hashes' :
			'\n\t' +
			'id   INTEGER PRIMARY KEY, \n\t' +
			'hash TEXT UNIQUE',

		'ImageURLs' : 
			'\n\t' +
			'id      INTEGER PRIMARY KEY, \n\t' + 
			'url     TEXT UNIQUE, \n\t' +
			'hashid  INTEGER,     \n\t' +      # Reference to Hashes table
			'width   INTEGER,     \n\t' +
			'height  INTEGER,     \n\t' +
			'bytes   INTEGER,     \n\t' +
			'FOREIGN KEY(hashid) REFERENCES Hashes(id)',
			
		'Albums' :
			'\n\t' +
			'id  INTEGER PRIMARY KEY, \n\t' +
			'url TEXT UNIQUE',
		
		'Images' :
			'\n\t' +
			'urlid     INTEGER, \n\t' + # Reference to ImageURLs table
			'hashid    INTEGER, \n\t' + # Reference to Hashes table
			'albumid   INTEGER, \n\t' + # Reference to Albums table   (0 if none)
			'postid    INTEGER, \n\t' + # Reference to Posts table
			'commentid INTEGER, \n\t' + # Reference to Comments table (0 if post)
			'FOREIGN KEY(urlid)     REFERENCES ImageURLs(id), \n\t' + 
			'FOREIGN KEY(hashid)    REFERENCES Hashes(id),    \n\t' + 
			'FOREIGN KEY(albumid)   REFERENCES Albums(id),    \n\t' +
			'FOREIGN KEY(postid)    REFERENCES Posts(id),     \n\t' +
			'FOREIGN KEY(commentid) REFERENCES Comments(id),  \n\t' +
			'PRIMARY KEY(urlid, postid, commentid)' # Prevent a post or comment from having more than two of the same exact image
	}

# For keeping track of what recent posts we have already checked
from DB import DB
db = DB('reddit.db', **SCHEMA)

# For calculating image hash, retrieving dimensions, and creating thumbnails (uses PIL)
from ImageHash import avhash, dimensions, create_thumb

import time, tempfile

# Library for interacting with web servers, requesting files, etc
from Web import Web
web = Web()

# Library for interacting with reddit.com
from ReddiWrap import ReddiWrap
reddit = ReddiWrap()


def get_image_hash(url, postid=0, comment=None, albumid=0):
	""" Gets hash for image based on 'url'. Adds to Hashes and Images tables. """
	# Check that we haven't already grabbed this URL
	url = url.replace("'", "%27")
	url = url.replace('"', "%22")
	
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	
	# Get file extension
	if not '.' in url: return
	ext = url.lower()[url.rfind('.') + 1:]
	
	if ext in ['jpg', 'jpeg', 'gif', 'png']:
		# If it's a direct link to a image, then we already have the URL
		url = url.replace('http://imgur.com', 'http://i.imgur.com')
		pass
		
	elif 'imgur.com'         in url:
		# It's an imgur link
		if '.imgur.com'        in url and \
			 not 'i.imgur.com'   in url and \
			 not 'www.imgur.com' in url or  \
			 'imgur.com/a/'      in url:
			# It's an imgur album, Retrieve each image using recursively calls
			get_album_hashes(url, postid=postid, comment=comment)
			return
		
		# Single image, need to get direct link to image (imgur.com/ASDF1 to i.imgur.com/ASDF1.jpg)
		r = web.get(url)
		urls = web.between(r, '<link rel="image_src" href="', '"')
		if len(urls) == 0: return
		url = urls[0].strip()
		url = url.replace('http://imgur.com', 'http://i.imgur.com')
		ext = url.lower()[url.rfind('.') + 1:]
		
	elif 'postimage.org' in url and '/gallery/' in url:
		# Postimage gallery
		get_postimage_hashes(url, postid=postid, comment=comment)
		return
		
	else:
		# Non-hotlinked, non-imgur webpage; skip it
		return
	
	# Check if we have already calculated this image's hash/info
	found = db.select('id, hashid', 'ImageURLs', "url = '%s'" % (url))
	if len(found) > 0:
		# Image URL already stored; get IDs of image
		urlid  = found[0][0]
		hashid = found[0][1]
	else:
		# Download & Calculate hash for image
		if '?' in ext: ext = ext[:ext.find('?')]
		(file, temp_image) = tempfile.mkstemp(prefix='redditimg', suffix='.'+ext)
		close(file)
		print 'downloading %s' % (url)
		stdout.flush()
		if not web.download(url, temp_image): return
		
		# Calculate hash of downloaded jmage
		try:                hash = str(avhash(temp_image))
		except IOError:     hash = ''
		except IndexError:  hash = ''
		except MemoryError: hash = ''
		
		# We must have a hash to add image to database
		if hash == '': 
			try:            remove(temp_image) # Delete the temporary file
			except OSError: pass
			return
		
		# Insert image hash into Hashes table
		hashid = db.insert('Hashes', (None, hash))
		if hashid == -1: 
			# If hash already exists, find it
			#print "Hash already exists: %s" % hash
			hashids = db.select('id', 'Hashes', 'hash = "%s"' % (hash))
			if len(hashids) == 0:
				print "Could not find hash id! (WTF!!!)"
				try: remove(temp_image)
				except OSError: pass
				return
			hashid = hashids[0][0]
		
		# Calculate width/height for image
		(width, height) = dimensions(temp_image)
		# Calculate filesize (in bytes)
		filesize = path.getsize(temp_image)
		# Insert into ImageURLs table
		urlid = db.insert('ImageURLs', (None, url, hashid, width, height, filesize))
		# Create thumbnail, using ImageURLs ID for index
		create_thumb(temp_image, urlid)
		
		remove(temp_image) # Delete the temp file (image)
	
	# Insert comment into database if needed... ONLY if an image hash is found
	if comment != None:
		commentid = db.insert('Comments', (None, postid, comment.id, comment.author, comment.body, comment.upvotes, comment.downvotes, comment.created_utc))
		if commentid == -1:
			# Comment already exists; Find it. This happens if a comment contains multiple image links
			commentid = db.select('id', 'Comments', "hexid = '%s'" % comment.id)[0][0]
	else:
		commentid = 0 # Not a comment
	
	# Insert image into Images tables
	imageid = db.insert('Images', (urlid, hashid, albumid, postid, commentid))
	db.commit()


def get_postimage_hashes(url, postid=0, comment=None):
	url = url.replace('https://', '')
	if not url.startswith('http://'): url = 'http://' + url
	if url.find('#') != -1: url = url[:url.find('#')]
	if url.endswith('/'): url = url[:-1]
	
	# Insert into Albums, get ID, if exists: return
	albumid = db.insert('Albums', (None, url))
	db.commit()
	if albumid == -1: return
	
	r = web.get(url)
	
	chunks = web.between(r, "<table class='gallery'", "</table>")
	if len(chunks) == 0: return
	chunk = chunks[0]
	
	pics = web.between(chunk, "<a href='", "'")
	for pic in pics:
		u = pic
		r = web.get(pic)
		imgs = web.between(r, "<img src='", "'")
		if len(imgs) == 0: continue
		get_image_hash(imgs[0], postid=postid, comment=comment, albumid=albumid)

def get_album_hashes(url, postid=0, comment=None):
	""" Receives imgur album URL, calls get_image_hash for each image in album """
	url = url.replace('https://', '')
	if not url.startswith('http://'): url = 'http://' + url
	if url.find('#') != -1: url = url[:url.find('#')]
	if url.endswith('/'): url = url[:-1]
	
	# Insert into Albums, get ID, if exists: return
	albumid = db.insert('Albums', (None, url))
	db.commit()
	if albumid == -1: return
	
	r = web.get(url + '/noscript')
	
	pics = web.between(r, '<img src="http://i.imgur.com/', '"')
	for pic in pics:
		u = pic
		if len(u) == len('dpugoh.jpg'):  u = u[:5] + u[6:]
		if len(u) == len('dpugoh.jpeg'): u = u[:6] + u[7:]
		get_image_hash('http://i.imgur.com/' + u, postid=postid, comment=comment, albumid=albumid)


def get_images_from_body(body, postid=0, comment=None):
	""" Parses all http links from body, forwards URL to 'get_image_hash()' """
	i = 0
	while True:
		i = body.find('http://', i + 1)
		if i == -1: break
		j = i
		while j < len(body)   and \
			    body[j] != ')'  and \
			    body[j] != ']'  and \
				  body[j] != ' '  and \
					body[j] != '"'  and \
					body[j] != '\n' and \
					body[j] != '\t':
			j += 1
		url = body[i:j]
		get_image_hash(url, postid=postid, comment=comment)
		i = j


def post_id_generator(starting=None):
	""" Generates next reddit post ID (base36). Can resume from 'starting' (+1) """
	alpha = '0123456789abcdefghijklmnopqrstuvwxyz'
	num = 0
	if starting != None:
		p = 0
		for i in xrange(len(starting) - 1, -1, -1):
			num += alpha.find(starting[i]) * pow(len(alpha), p)
			p += 1
	
	while True:
		num += 1
		result = ''
		temp = num
		while temp > 0:
			result = alpha[temp % len(alpha)] + result
			temp /= len(alpha)
		yield num


def scrape_post(post):
	""" Scrapes content/images from Post. Recursively scrapes comments. Writes to DB. """
	# Ignore posts less than 24 hours old
	if time.time() - post.created < 60 * 60 * 24: return False
	
	# Check if Posts table already contains 'reddit_id'
	postid_db = db.insert('Posts', (None, post.id, post.title, post.url, post.selftext, post.author, post.permalink, post.subreddit, post.num_comments, post.upvotes, post.downvotes, post.score, post.created_utc, int(post.is_self), int(post.over_18)))
	if postid_db == -1: return False # Post is not unique; skip
	db.commit()
	
	if post.selftext != '': # Get images from self-text (if any)
		get_images_from_body(post.selftext, postid=postid_db)
	else: # Try to get hash of URL (if relevant)
		get_image_hash(post.url, postid=postid_db)
	
	if post.num_comments > 0 or post.is_self:
		# Retrieve comments for post if there are comments
		reddit.fetch_comments(post)
		
		# Scrape delicious comments for content/images
		while len(post.comments) > 0:
			comment = post.comments.pop(0)
			scrape_comments(comment, postid_db)
			del comment
	return True


# comment   - the comment to recursively scrape (ReddiWrap.Comment object)
# postid_db - numeric reference to Posts table
def scrape_comments(comment, postid_db):
	""" Scrapes data/images contained in "comment", recursively call on children. """
	
	get_images_from_body(comment.body, postid=postid_db, comment=comment)
	# Load more comments?
	while len(comment.children) > 0:
		child_comment = comment.children.pop(0)
		scrape_comments(child_comment, postid_db)
		del child_comment


def save_subs(filename):
	sub_list = load_list('subs.txt')
	save_list(sub_list, filename)
	return sub_list

def save_list(lst, filename):
	f = open(filename, 'w')
	for item in lst:
		f.write(item + '\n')
	f.close()

def load_list(filename, load_subs=False):
	if not path.exists(filename):
		return save_subs(filename)
	f = open(filename, 'r')
	result = f.read().split('\n')
	f.close()
	while result.count("") > 0:
		result.remove("")
	if len(result) == 0 and load_subs:
		return save_subs(filename)
	return result

def start():
	""" Where everything comes together.  """
	result = reddit.login(user=REDDIT_USER, password=REDDIT_PASSWORD)
	if result != 0:
		print ' unable to login (%d), exiting\n' % result
		exit(1)
	
	'''
	# For testing on my sandbox subreddit
	posts = reddit.get('/r/freshbreath/new')
	for i,post in enumerate(posts):
		if i < 13: continue
		print post
		scrape_post(post)
		#break
	exit(0)
	'''
	
	while True:
		for timeframe in ['all', 'month', 'week']:
			if timeframe == 'week':
				SUBREDDITS = load_list('subs_%s.txt' % timeframe, load_subs=True)
			else:
				SUBREDDITS = load_list('subs_%s.txt' % timeframe)
			while len(SUBREDDITS) > 0:
				subreddit = SUBREDDITS.pop(0)
				index        = 0
				total_posts  = 0
				time_started = 0
				while True:
					posts = []
					
					delta = time.time() - time_started  # Time elapsed since the request was made
					time_started = time.time()
					if delta < 2: time.sleep(2 - delta) # Ensure at least 2 seconds between requests
					
					if total_posts == 0:
						print 'grabbing first page... /r/%s/top?t=%s' % (subreddit, timeframe)
						stdout.flush()
						posts = reddit.get('/r/%s/top?t=%s' % (subreddit, timeframe))
					elif reddit.has_next():
						print 'grabbing next page... %s' % (reddit.last_url)
						stdout.flush()
						posts = reddit.get_next()
					else:
						break
					
					if posts == None or len(posts) == 0: break
					total_posts += len(posts)
					
					while len(posts) > 0:
						post = posts.pop(0)
						index += 1
						
						print '%4d/%d) scraping: %s' % (index, total_posts, post.__repr__())
						stdout.flush()
						
						time_started = time.time()
						if scrape_post(post):
							# Only sleep if we actually made a request to reddit
							delta = time.time() - time_started  # Time elapsed since the request was made
							if delta < 2: time.sleep(2 - delta) # Ensure at least 2 seconds between requests
						del post
				save_list(SUBREDDITS, 'subs_%s.txt' % timeframe)
	exit(0)

if __name__ == '__main__':
	# only run when executed
	try:
		start()
	except KeyboardInterrupt:
		print '\n\n Interrupted (^C)'
	
