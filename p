#!/bin/sh
#ps -aux | grep "python scan" | grep -v "grep"
ps -aux | grep "python" | grep "rarchive" | egrep "scan.py|/keepalive.py" | grep -v "grep"
