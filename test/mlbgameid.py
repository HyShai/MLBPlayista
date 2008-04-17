#!/usr/bin/env python
 
# $Revision$

import os.path
import sys
import re
import subprocess

cj = None
cookielib = None

COOKIEFILE = '.mlbcookie.lwp'

AUTHFILE = os.path.join(os.environ['HOME'],'.mlb/config')
 
DEFAULT_PLAYER = 'xterm -e mplayer -cache 2048 -quiet -fs'

try:
   import cookielib
except ImportError:
   raise Exception,"Could not load cookielib"

import urllib2
import urllib

conf = os.path.join(os.environ['HOME'], AUTHFILE)
fp = open(conf)

datadct = {'video_player': DEFAULT_PLAYER,
           'blackout': []}

for line in fp:
    # Skip all the comments
    if line.startswith('#'):
        pass
    # Skip all the blank lines
    elif re.match(r'^\s*$',line):
        pass
    else:
        # Break at the first equals sign
        key, val = line.split('=')[0], '='.join(line.split('=')[1:])
        key = key.strip()
        val = val.strip()
        # These are the ones that take multiple values
        if key in ('blackout'):
            datadct[key].append(val)
        # And these are the ones that only take one value, and so,
        # replace the defaults.
        else:
            datadct[key] = val


cj = cookielib.LWPCookieJar()

if cj != None:
   if os.path.isfile(COOKIEFILE):
      cj.load(COOKIEFILE)
   if cookielib:
      opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
      urllib2.install_opener(opener)

# Get the cookie first
theurl = 'https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb'
txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
data = None
req = urllib2.Request(theurl,data,txheaders)
handle = urllib2.urlopen(req)
print 'These are the cookies we have received so far :'
for index, cookie in enumerate(cj):
    print index, '  :  ', cookie        
cj.save(COOKIEFILE,ignore_discard=True) 
#sys.exit()

# now authenticate
theurl = 'https://secure.mlb.com/authenticate.do'
txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13',
             'Referer' : 'https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb'}
values = {'uri' : '/account/login_register.jsp',
          'registrationAction' : 'identify',
          'emailAddress' : datadct['user'],
          'password' : datadct['pass']}

data = urllib.urlencode(values)
try:
   req = urllib2.Request(theurl,data,txheaders)
   handle = urllib2.urlopen(req)
except IOError, e:
   print 'We failed to open "%s".' % theurl
   if hasattr(e, 'code'):
       print 'We failed with error code - %s.' % e.code
   elif hasattr(e, 'reason'):
       print "The error object has the following 'reason' attribute :", e.reason
       print "This usually means the server doesn't exist, is down, or we don't have an internet connection."
       sys.exit()

else:
    print 'Here are the headers of the page :'
    print handle.info()                             # handle.read() returns the page, handle.geturl() returns the true url of the page fetched (in case urlopen has followed any redirects, which it sometimes does)

print
if cj == None:
    print "We don't have a cookie library available - sorry."
    print "I can't show you any cookies."
else:
    print 'These are the cookies we have received so far :'
    for index, cookie in enumerate(cj):
        print index, '  :  ', cookie        
    cj.save(COOKIEFILE,ignore_discard=True) 

page = handle.read()
pattern = re.compile(r'Welcome to your personal mlb.com account.')
try:
    loggedin = re.search(pattern, page).groups()
    print "Logged in successfully!"
except:
    raise Exception,page

#sys.exit()
wfurl = "http://www.mlb.com/enterworkflow.do?" +\
   "flowId=media.media&keepWfParams=true&mediaId=" +\
   sys.argv[1] + "&catCode=mlb_lg&av=v"
data = None

#http://www.mlb.com/enterworkflow.do?flowId=media.media&keepWfParams=true&mediaId=643342&catCode=mlb_lg&av=v

try:
   req = urllib2.Request(wfurl,data,txheaders)
   handle = urllib2.urlopen(req)
   game_info = handle.read()
   handle.close()
except IOError, e:
   print 'We failed to open "%s".' % wfurl
   if hasattr(e, 'code'):
       print 'We failed with error code - %s.' % e.code
   elif hasattr(e, 'reason'):
       print "The error object has the following 'reason' attribute :", e.reason
       print "This usually means the server doesn't exist, is down, or we don't have an internet connection."
       sys.exit()

vid_pattern = re.compile(r'(url:.*\")(mms:\/\/[^ ]*)(".*)')
aud_pattern = re.compile(r'(url:.*\")(http:\/\/[^ ]*)(".*)')


# handle http urls for audio and older video
try:
   game_url = re.search(vid_pattern, game_info).groups()[1]
except:
   try:
       game_url = re.search(aud_pattern, game_info).groups()[1]
   except:
       raise Exception, game_info

print
if cj == None:
    print "We don't have a cookie library available - sorry."
    print "I can't show you any cookies."
else:
    print 'These are the cookies we have received so far :'
    for index, cookie in enumerate(cj):
        print index, '  :  ', cookie        
    cj.save(COOKIEFILE,ignore_discard=True) 

logout_url = 'https://secure.mlb.com/enterworkflow.do?flowId=registration.logout&c_id=mlb'
txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13',
             'Referer' : 'http://mlb.mlb.com/index.jsp'}
data = None
req = urllib2.Request(logout_url,data,txheaders)
handle = urllib2.urlopen(req)
logout_info = handle.read()
handle.close()

print logout_info

print 'The game url parsed is: '
print game_url
#sys.exit()

cmd_str = datadct['video_player'] + ' "' + game_url + '"'
playprocess = subprocess.Popen(cmd_str,shell=True)
playprocess.wait()

