#!/usr/bin/python

from subprocess import Popen, PIPE, call
from os import devnull
import time

while True:
	proc = Popen('ps -aux', stdout=PIPE, stderr=open(devnull, 'w'), shell=True)
	result = proc.communicate()[0]
	running = False
	for line in result.split('\n'):
		if line == '' or 'rarchive' not in line or 'scan.py' not in line or 'python' not in line: continue
		running = True
		break
	
	if not running:
		# Need to restart
		print "(RE)STARTING TEST PROCESS IN 10 SECONDS!"
		time.sleep(10)
		proc = call('/home/rarchive/www/i/scrape.sh', shell=True)
	
	time.sleep(1)

		
