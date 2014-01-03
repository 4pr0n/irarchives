#!/usr/bin/python

# From http://sprunge.us/WcVJ?py
# All credit goes to original author

from os import path, mkdir, sep, remove
from sys import exit, argv
from Httpy import Httpy

from PIL import Image

def avhash(im):
	"""
		Shrinks image to 16x16 pixels,
		Finds average amongst the pixels,
		Iterates over every pixel, comparing to average.
		1 if above avg, 0 if below.
		Returns resulting integer. (hash of the image 'im')
		Updated to not use ternary operator (not available in python 2.4.x)
	"""
	if not isinstance(im, Image.Image):
		im = Image.open(im)
	im = im.convert('L').resize((16, 16), Image.ANTIALIAS)
	ttl = 0
	for gd in im.getdata(): ttl += gd
	avg = ttl / 256
	result = 0
	for i, gd in enumerate(im.getdata()):
		if gd > avg:
			result += (1 << i)
	del im
	return result

def avhash_dict(im):
	""" 
		Generate hashes for the image, including variations of the image
		* Regular image
		* Mirrored (left-right)
		* Rotated left (90deg)
		* Rotated right (270deg)
	"""
	if not isinstance(im, Image.Image):
		im = Image.open(im)
	im = im.resize((16, 16), Image.ANTIALIAS).convert('L')
	ttl = 0
	for gd in im.getdata(): ttl += gd
	avg = ttl / 256
	result = {}
	
	# Regular hash
	regular_hash = 0
	for i, gd in enumerate(im.getdata()):
		if gd > avg:
			regular_hash += (1 << i)
	result['hash'] = regular_hash
	
	# Mirror hash
	mirror_im = im.transpose(Image.FLIP_LEFT_RIGHT)
	mirror_hash = 0
	for i, gd in enumerate(mirror_im.getdata()):
		if gd > avg:
			mirror_hash += (1 << i)
	result['mirror'] = mirror_hash
	
	# Rotated 90deg hash
	left_im = im.transpose(Image.ROTATE_90)
	left_hash = 0
	for i, gd in enumerate(left_im.getdata()):
		if gd > avg:
			left_hash += (1 << i)
	result['left'] = left_hash
	
	# Rotated 270deg hash
	right_im = im.transpose(Image.ROTATE_270)
	right_hash = 0
	for i, gd in enumerate(right_im.getdata()):
		if gd > avg:
			right_hash += (1 << i)
	result['right'] = right_hash
	del im
	return result

def dimensions(im):
	""" Returns tuple (Width, Height) for given image. """
	if not isinstance(im, Image.Image):
		im = Image.open(im)
	result = im.size
	del im
	return result

def create_thumb(im, num):
	"""
		Creates a thumbnail for a given image file.
		Saves to 'thumbs' directory, named <num>.jpg
	"""
	try: mkdir('thumbs')
	except OSError: pass
	
	if not isinstance(im, Image.Image):
		im = Image.open(im)
	# Convert to RGB if not already
	if im.mode != "RGB": im = im.convert("RGB")
	im.thumbnail( (100, 100), Image.ANTIALIAS)
	im.save('thumbs%s%d.jpg' % (sep, num), 'JPEG')
	del im
	

if __name__ == '__main__':
	args = argv[1:]
	if len(args) == 0:
		print 'argument required: image file location'
		exit(1)
	filename = ' '.join(args)
	remove_file = False
	if not path.exists(filename):
		if '://' in filename:
			web = Httpy()
			web.download(filename, 'img.jpg')
			filename = 'img.jpg'
			remove_file = True
		else:
			print 'file not found: %s' % (filename)
			exit(1)
	
	print 'Hash:\t\t%d' % avhash(filename)
	
	print ''
	d = avhash_dict(filename)
	for key in d:
		print 'Hash[%s] = \t%d' % (key, d[key])
	print ''
	
	dim = dimensions(filename)
	print 'Dimensions:\t%dx%d' % (dim[0], dim[1])

	#create_thumb(filename, 1)
	if remove_file:
		remove(filename)
