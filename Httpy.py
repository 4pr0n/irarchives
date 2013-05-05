#!/usr/bin/python

from cookielib import LWPCookieJar as CookieJar
from urllib2   import build_opener, HTTPCookieProcessor, Request
from urllib    import urlencode

DEFAULT_USERAGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:19.0) Gecko/20100101 Firefox/19.0'
DEFAULT_TIMEOUT   = 15

class Httpy:
	""" 
		Easily perform GET and POST requests with web servers.
		Keeps cookies to retain web sessions.
		Includes helpful methods that go beyond GET and POST:
		 * get_meta - retrieves meta info about a URL
		 * unshorten - returns (some) redirected URLs
	"""

	def __init__(self, user_agent=DEFAULT_USERAGENT, timeout=DEFAULT_TIMEOUT):
		self.cj      = CookieJar()
		self.opener  = build_opener(HTTPCookieProcessor(self.cj))
		self.urlopen = self.opener.open
		self.user_agent = user_agent
		self.timeout = timeout
	
	def get(self, url, timeout=DEFAULT_TIMEOUT, raise_exception=False):
		""" GET request """
		result  = ''
		headers = self.get_headers()
		try:
			req = Request(url, headers=headers)
			handle = self.urlopen(req, timeout=timeout)
			result = handle.read()
		except Exception, e:
			if raise_exception:
				raise e
		return result

	def post(self, url, postdata=None, timeout=DEFAULT_TIMEOUT, raise_exception=False):
		""" 
			Submits a POST request to URL. Posts 'postdata' if
			not None. URL-encodes postdata and strips Unicode chars.
		"""
		result = ''
		headers = self.get_headers()
		if postdata == None:
			encoded_data = ''
		else:
			encoded_data = urlencode(postdata)
		try:
			req = Request(url, encoded_data, headers)
			handle = self.urlopen(req, timeout=timeout)
			result = handle.read()
		except Exception, e:
			if raise_exception: raise e
		return result

	def download(self, url, save_as, timeout=DEFAULT_TIMEOUT, raise_exception=False):
		""" Downloads file from URL to save_as path. """
		result = False
		headers = self.get_headers()
		outfile = open(save_as, 'w')
		try:
			req = Request(url, headers=headers)
			handle = self.urlopen(req, timeout=timeout)
			while True:
				buf = handle.read(65536)
				if len(buf) == 0: break
				outfile.write(buf)
			result = True
		except Exception, e:
			if raise_exception: raise e
		outfile.close()
		return result
	
	def check_url(self, url):
		""" Returns True if URL is valid and can be opened. """
		try:
			req = Request(url)
			self.urlopen(url)
		except Exception:
			return False
		return True

	def get_meta(self, url, raise_exception=False, timeout=DEFAULT_TIMEOUT):
		""" 
			Returns a dict containing info about the URL.
			Such as Content-Type, Content-Length, etc.
		"""
		try:
			headers = self.get_headers()
			req = Request(url, headers=headers)
			handle = self.urlopen(req, timeout=timeout)
			return handle.info()
		except Exception, e:
			if raise_exception: raise e
		return {}
	
	def unshorten(self, url, timeout=DEFAULT_TIMEOUT):
		""" 
			Attempts to resolve redirected URL. 
			Returns new resolved URL if found,
			otherwise returns original URL.
		"""
		try:
			headers = self.get_headers()
			req = Request(url, headers=headers)
			handle = urlopen(req, timeout=timeout)
			return handle.url
		except Exception:
			return url

	# SETTERS
	def clear_cookies(self):
		self.cj.clear()
	def set_user_agent(self, user_agent):
		self.user_agent = user_agent
			
	# HELPER METHODS
	def get_headers(self):
		""" Returns default headers for URL requests """
		return {'User-agent' : self.user_agent}

	def between(self, source, start, finish):
		"""
			Useful when parsing responses from web servers.
			
			Looks through a given source string for all items between two other strings, 
			returns the list of items (or empty list if none are found).
			
			Example:
				test = 'hello >30< test >20< asdf >>10<< sadf>'
				print between(test, '>', '<')
				
			would print the list:
				['30', '20', '>10']
		"""
		result = []
		i = source.find(start)
		j = source.find(finish, i + len(start) + 1)
		
		while i >= 0 and j >= 0:
			i = i + len(start)
			result.append(source[i:j])
			i = source.find(start, j + len(finish))
			j = source.find(finish, i + len(start) + 1)
		
		return result

