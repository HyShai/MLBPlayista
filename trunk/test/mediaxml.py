#!/usr/bin/env python
 
# $Revision$

import os.path
import sys
import re

import logging
from xml.dom.minidom import parse

FIELDS = ( 'event-id', 'content-id', 'type', 'state', 'cat-code', 
           'playback-scenario', 'login-required', 'auth-required', 
           'innings-index', 'session-key', 'url', 'status-code',
           'status-message', 'postal-code', 'blackout')

OTHERS = ( 'blackout-status', 'auth-status' )

try:
    XMLFILE = sys.argv[1]
except:
    print "Please specify an xml file to parse."
    sys.exit(1)

xp = parse(XMLFILE)

errorReply = False
uve = len(xp.getElementsByTagName('user-verified-event'))

if uve != 1:
    print "No <user-verified-event> found.  This must be an error reply."
    errorReply = True

reply = {}
for elem in FIELDS:
    try:
        reply[elem] = xp.getElementsByTagName(elem)[0].childNodes[0].data 
    except:
        print "could not find elem: " + elem

for elem in OTHERS:
    try:
        tmp = xp.getElementsByTagName(elem)[0].childNodes[0]
    except:
        reply[elem] = ''
    else:
        reply[elem] = tmp.tagName

dattrs = {}
for da in xp.getElementsByTagName('domain-attribute'):
    name = da.getAttribute('name')
    dattrs[name] = da.childNodes[0].data

print 
for key in FIELDS + OTHERS:
    if reply.has_key(key):
        print key + ' = ' + reply[key] + '\n'

print '<<< DOMAIN ATTRIBUTES >>> \n'
for key in dattrs.keys():
    print key + ' = ' + dattrs[key] + '\n'

