#!/bin/sh

# Launches scraper script 'scan.py', stores all output in 'log.txt'
# Runs script in background!
python scan.py > log.txt 2>&1 &
