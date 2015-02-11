#!/usr/bin/python

'''
	What this script does:
		1. Scans reddit.com subreddits for new posts/comments
		2. Retrieves images from day-old posts/comments
		3. Stores image information (hash, size, etc) in a database
		4. If post/comment contains image/link, stores post/comment info in database
'''

##############################
# Standard libraries
from os import path, close, remove
from sys import exit, stdout
import time, tempfile
##############################
# Reddit
import ReddiWrap
reddit = ReddiWrap.ReddiWrap()
##############################
# Image hash
from ImageHash import avhash, dimensions, create_thumb
##############################
# WEB
from Httpy import Httpy
web = Httpy()
##############################
# Database
from DB import DB
##############################
# Command-line output
from commands import getstatusoutput

#################
# Globals
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
db = DB('reddit.db', **SCHEMA)

CONSOLE_WIDTH = 150 # With of console (number of characters across)


def main():
	""" 
		Main loop of program. 
		Infinitely iterates over the list of subreddits
	"""
	exit_if_already_started()
	# Login to reddit acct or die
	if not login(): return 
	while True:
		# Subreddits are added to "subs_all.txt", "subs_month.txt", and
		# "subs_week.txt", and "subs.txt" (master list).
		# These lists tell the script which top?t=timeperiod to grab
		# After grabbing the top from all/month, the script continues to
		# check the subreddit's top weekly posts
		for timeframe in ['all', 'month', 'week']:
			if timeframe == 'week':
				# Load subreddits to check the top?t=week of, or load
				# all subs from the masterlist if found to be empty.
				subreddits = load_list('subs_%s.txt' % timeframe, load_subs=True)
			else:
				# Only load subs from all/month, don't load more if the
				# lists are found to be empty
				subreddits = load_list('subs_%s.txt' % timeframe)
			while len(subreddits) > 0:
				# Grab all images/comments from sub, remove from list
				parse_subreddit(subreddits.pop(0), timeframe)
				# Save current list in case script needs to be restarted
				save_list(subreddits, 'subs_%s.txt' % timeframe)
				time.sleep(2)

def exit_if_already_started():
	(status, output) = getstatusoutput('ps aux')
	running_processes = 0
	for line in output.split('\n'):
		if 'python' in line and 'scan.py' in line and not '/bin/sh -c' in line:
			running_processes += 1
	if running_processes > 1:
		print "process is already running, exiting"
		exit(0) # Quit if the bot is already running

def login():
	""" Logs into reddit. Returns false if it can't """
	if path.exists('login_credentials.txt'):
		login_file = open('login_credentials.txt')
		login_list = login_file.read().split('\n')
		login_file.close()
		if len(login_list) >= 2:
			user     = login_list[0]
			password = login_list[1]
			print '      [+] logging in to %s...' % user,
			stdout.flush()
			result = reddit.login(user=user, password=password)
			if result == 0:
				print 'success'
				return True
			else:
				print 'failed (status code %d)' % result
				return False
	print '\n      [!] unable to find/validate user/pass'
	print '          credentials need to be in login_credentials.txt'
	print '          expecting: username and password separated by new lines'
	return False

def parse_subreddit(subreddit, timeframe):
	""" Parses top 1,000 posts from subreddit within timeframe. """
	total_post_count   = 0
	current_post_index = 0
	while True:
		# Check if there are pending albums to be indexed
		check_and_drain_queue()
		query_text = '/r/%s/top?t=%s' % (subreddit, timeframe)
		if total_post_count == 0:
			prntln('      [+] loading first page of %s' % query_text)
			stdout.flush()
			posts = reddit.get(query_text)
		elif reddit.has_next():
			prnt('      [+] loading  next page of %s' % query_text)
			stdout.flush()
			posts = reddit.get_next()
		else:
			# No more pages to load
			return
		if posts == None or len(posts) == 0:
			print '      [!] no posts found'
			return
		total_post_count += len(posts)
		for post in posts:
			current_post_index += 1
			prnt('[%3d/%3d] scraping http://redd.it/%s %s' % \
					(current_post_index, total_post_count, post.id, post.url[:50]))
			stdout.flush()
			if parse_post(post): # Returns True if we made a request to reddit
				time.sleep(2) # Sleep to stay within rate limit
		
		time.sleep(2)
	
def parse_post(post):
	""" Scrapes and indexes a post and it's comments. """
	# Ignore posts less than 24 hours old
	if time.time() - post.created < 60 * 60 * 24: return False
	
	# Add post to database
	postid_db = db.insert('Posts', \
			(None, \
			post.id, \
			post.title, \
			post.url, \
			post.selftext, \
			post.author, \
			post.permalink, \
			post.subreddit, \
			post.num_comments, \
			post.upvotes, \
			post.downvotes, \
			post.score, \
			post.created_utc, \
			int(post.is_self), \
			int(post.over_18)))
	# If post already exists, we've already indexed it; skip!
	if postid_db == -1: return False
	# Write post to DB so we don't hit it again
	
	# NOTE: postid_db is the ID of the post in the database; NOT on reddit
	
	# Check for self-post
	if post.selftext != '':
		urls = get_links_from_body(post.selftext)
		for url in urls:
			parse_url(url, postid=postid_db)
	else:
		# Attempt to retrieve hash(es) from link
		parse_url(post.url, postid=postid_db)
	
	# Iterate over top-level comments
	if post.num_comments > 0:
		reddit.fetch_comments(post)
		for comment in post.comments:
			parse_comment(comment, postid_db)
	db.commit()
	
def parse_comment(comment, postid):
	""" 
		Parses links from a comment. Populates DB.
		Recursively parses child comments.
	"""
	urls = get_links_from_body(comment.body)
	if len(urls) > 0:
		# Only insert comment into DB if it contains a link
		comid_db = db.insert('Comments', \
				(None, \
				postid, \
				comment.id, \
				comment.author, \
				comment.body, \
				comment.upvotes, \
				comment.downvotes, \
				comment.created_utc))
		for url in urls:
			parse_url(url, postid=postid, commentid=comid_db)
	# Recurse over child comments
	for child in comment.children:
		parse_comment(child, postid)

def get_links_from_body(body):
	""" Returns list of URLs found in body (e.g. selfpost or comment). """
	result = []
	i = -1 # Starting index
	while True:
		i = body.find('http://', i + 1) # Find next link
		if i == -1: break
		j = i
		# Iterate forward until we hit the end of the URL
		while j < len(body)   and \
			    body[j] != ')'  and \
			    body[j] != ']'  and \
				  body[j] != ' '  and \
					body[j] != '"'  and \
					body[j] != '\n' and \
					body[j] != '\t':
			j += 1
		result.append(body[i:j]) # Add to list
		i = j
	result = list(set(result)) # Remove duplicates
	return result

def sanitize_url(url):
	""" Sanitizes URLs for DB input, strips excess chars """
	url = url.replace('"', '%22')
	url = url.replace("'", '%27')
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	return url

def parse_url(url, postid=0, commentid=0):
	""" Gets image hash(es) from URL, populates database """
	while url.endswith('/'): url = url[:-1]
	if 'imgur.com' in url:
		url = url.replace('/m.imgur.com/', '/imgur.com/')
		if '?' in url: url = url[:url.find('?')]
		if '.com/a/' in url:
			# Album
			print ''
			result = parse_album(url, postid=postid, commentid=commentid)
			db.commit()
			return result
		elif url.lower().endswith('.jpg') or \
				url.lower().endswith('.jpeg') or \
				url.lower().endswith('.png')  or \
				url.lower().endswith('.gif'):
			# Direct imgur link, find highest res
			url = imgur_get_highest_res(url)
			# Drop out of if statement & parse image
		else:
			# Indirect imgur link (e.g. "imgur.com/abcde")
			r = web.get(url)
			if '"image_src"' in r:
				chunk = web.between(r, '"image_src"', '>')[0]
				url = web.between(chunk, 'href="', '"')[0]
			else:
				print '\n      [!] unable to find direct imgur link for %s (404?)' % url
				return False

	elif url.lower().endswith('.jpg') or \
			url.lower().endswith('.jpeg') or \
			url.lower().endswith('.png')  or \
			url.lower().endswith('.gif'):
		# Direct link to non-imgur image
		pass # Drop out of if statement & parse image

	elif 'gfycat.com' in url:
		r = web.get(url)
		if "og:image' content='" in r:
			url = web.between(r, "og:image' content='", "'")[-1]
		else:
			print '\n      [!] unable to find gfycat image for %s' % url
			return False

	elif 'mediacru.sh' in url:
		r = web.get(url)
		if 'property="og:type" content="' not in r:
			content = web.between(r, 'property="og:type" content="', '')[0]
			if not content.startswith('image'):
				print '\n      [!] got non-image content "%s" for %s ' % (content, url)
				return False
			if content == '':
				# Album (?)
				print ''
				result = parse_album_mediacrush(url, postid=postid, commentid=commentid)
				db.commit()
				return result
			else:
				# Single image (?)
				if 'property="og:image" content="' in r:
					url = web.between(r, '"og:image" content="', '"')[0]
		else:
			print '\n      [!] unable to find mediacru.sh image for ' % url
			return False
	else:
		# Not imgur, not a direct link; no way to parse
		# TODO Develop a way to find images in other websites?
		return False
	print ''
	result = parse_image(url, postid=postid, commentid=commentid)
	db.commit()
	return result

def parse_album_mediacrush(url, postid=0, commentid=0):
	""" Indexes every image in an mediacru.sh album """
	from json import loads
	json = loads(web.get('%s.json' % url))
	files = json['files']
	for fil in files:
		parse_image(fil['url'], postid=postid, commentid=commentid, albumid=albumid)
	if len(files) == 0:
		print '      [!] no images found in album!'
		return False
	else:
		return True

def parse_album(url, postid=0, commentid=0):
	""" Indexes every image in an imgur album """
	# cleanup URL
	url = url.replace('http://', '').replace('https://', '')
	while url.endswith('/'): url = url[:-1]
	while url.count('/') > 2: url = url[:url.rfind('/')]
	if '?' in url: url = url[:url.find('?')]
	if '#' in url: url = url[:url.find('#')]
	url = 'http://%s' % url # How the URL will be stored in the DB
	albumid = db.insert('Albums', (None, url))
	if albumid == -1:
		albumids = db.select('id', 'Albums', 'url = "%s"' % url)
		if len(albumids) == 0: return
		albumid = albumids[0][0]
	# Download album
	url = url + '/noscript'
	r = web.get(url)
	links = web.between(r, 'img src="//i.', '"')
	for link in links:
		link = 'http://i.%s' % link
		if '?' in link: link = link[:link.find('?')]
		if '#' in link: link = link[:link.find('#')]
		link = imgur_get_highest_res(link)
		# Parse each image
		parse_image(link, postid=postid, commentid=commentid, albumid=albumid)
	if len(links) == 0:
		print '      [!] no images found in album!'
		return False
	else:
		return True

def parse_image(url, postid=0, commentid=0, albumid=0):
	""" 
		Downloads & indexes image.
		Populates 'Hashes', 'ImageURLs', and 'Images' tables
	"""
	try:
		(hashid, urlid, downloaded) = get_hashid_and_urlid(url)
	except Exception, e:
		print '\n      [!] failed to calculate hash for %s' % url
		print '      [!] Exception: %s' % str(e)
		return False
	# 'Images' table is used for linking reddit posts/comments to images
	# If there is no post/comment, don't bother linking
	if postid != 0 or commentid != 0:
		imageid = db.insert('Images', (urlid, hashid, albumid, postid, commentid))
	return True


def get_hashid_and_urlid(url, verbose=True):
	""" 
		Retrieves hash ID ('Hashes' table) and URL ID 
		('ImageURLs' table) for an image at a given URL.
		Populates 'Hashes' and 'ImageURLs' if needed.
		3rd tuple is True if downloading of image was required
	"""
	existing = db.select('id, hashid', 'ImageURLs', 'url = "%s"' % url)
	if len(existing) > 0:
		urlid = existing[0][0]
		hashid = existing[0][1]
		return (hashid, urlid, False)
	
	# Download image
	(file, temp_image) = tempfile.mkstemp(prefix='redditimg', suffix='.jpg')
	close(file)
	if url.startswith('//'): url = 'http:%s' % url
	if verbose: print '      [+] downloading %s ...' % url,
	stdout.flush()
	if not web.download(url, temp_image):
		if verbose: print 'failed'
		raise Exception('unable to download image at %s' % url)
	# Get image hash
	try:
		if verbose: print 'hashing ...',
		stdout.flush()
		(width, height) = dimensions(temp_image)
		if width > 4000 or height > 4000:
			print '\n[!] image too large to hash (%dx%d)' % (width, height)
			raise Exception('too large to hash (%dx%d)' % (width, height))
		if width == 161 and height == 81:
			# Size of empty imgur image ('not found!')
			raise Exception('Found 404 image dimensions (161x81)')
		image_hash = str(avhash(temp_image))
	except Exception, e:
		# Failed to get hash, delete image & raise exception
		if verbose: print 'failed'
		try: remove(temp_image)
		except: pass
		raise e
	if verbose: print 'indexing ...',
	stdout.flush()
	
	# Insert image hash into Hashes table
	hashid = db.insert('Hashes', (None, image_hash))
	if hashid == -1: 
		# Already exists, need to lookup existing hash
		hashids = db.select('id', 'Hashes', 'hash = "%s"' % (image_hash))
		if len(hashids) == 0:
			try: remove(temp_image)
			except: pass
			raise Exception('unable to add hash to table, or find hash (wtf?)')
		hashid = hashids[0][0]
	
	# Image attributes
	try:
		filesize = path.getsize(temp_image)
		urlid = db.insert('ImageURLs', (None, url, hashid, width, height, filesize))
		db.commit()
		create_thumb(temp_image, urlid) # Make a thumbnail!
		if verbose: print 'done'
	except Exception, e:
		try: remove(temp_image)
		except: pass
		raise e
	remove(temp_image)
	return (hashid, urlid, True)

def imgur_get_highest_res(url):
	""" Retrieves highest-res imgur image """
	if not 'h.' in url:
		return url
	temp = url.replace('h.', '.')
	m = web.get_meta(temp)
	if 'Content-Type' in m and 'image' in m['Content-Type'].lower() and \
			'Content-Length' in m and m['Content-Length'] != '503':
		return temp
	else:
		return url

def save_subs(filename):
	""" Copies list of subreddits to filename """
	sub_list = load_list('subs.txt')
	save_list(sub_list, filename)
	return sub_list

def save_list(lst, filename):
	""" Saves list to filename """
	f = open(filename, 'w')
	for item in lst:
		f.write(item + '\n')
	f.close()

def load_list(filename, load_subs=False):
	"""
		Loads list from filename
		If 'load_subs' is true and the list is empty,
		automatically load full list of subs & save to file
	"""
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

def check_and_drain_queue():
	""" 
		Indexes & empties file containing list of URLs to index
		File is populated via front-end requests.
	"""
	if not path.exists('index_queue.lst'): return
	# Read URLs
	f = open('index_queue.lst', 'r')
	queue_lines = f.read()
	f.close()
	# Delete
	#remove('index_queue.lst')
	f = open('index_queue.lst', 'w')
	f.write('')
	f.close()
	queue = queue_lines.split('\n')
	while queue.count('') > 0: queue.remove('')
	if len(queue) == 0: return
	queue = list(set(queue)) # remove duplicates
	print '\n      [!] found %d images to index' % len(queue)
	for url in queue:
		url = url.strip()
		if url == '': continue
		parse_url(url)

##################
# Print methods
# Useful for overwriting one-liners
def prnt(text):
	try:
		print '\r%s%s' % (text, ' ' * (CONSOLE_WIDTH - len(text))),
	except: pass
def prntln(text):
	try:
		print '\r%s%s' % (text, ' ' * (CONSOLE_WIDTH - len(text)))
	except: pass

if __name__ == '__main__':
	""" only run when executed (not imported) """
	try:
		main()
	except KeyboardInterrupt:
		print '\n\n Interrupted (^C)'
