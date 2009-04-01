#!/usr/bin/env python
 
# $Revision$

import os.path
import sys
import re
import subprocess

import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

from suds.client import Client

url = 'file:///home/matthew/mlb-2009/sudsy/MediaService.wsdl'
client = Client(url)


cj = None
cookielib = None

try: 
    EVENT = sys.argv[1]
except:
    #EVENT = '164-251363-2009-03-17'
    #EVENT = '14-257635-2009-03-26'
    #EVENT = '14-257676-2009-03-29'
    EVENT = '164-251362-2009-03-16'

try:
    SCENARIO = sys.argv[2]
except:
    SCENARIO = "MLB_FLASH_800K_STREAM"

try:
    session = sys.argv[3]
except:
    session = 'rsewYdqXc5t3h0RANw5QWG/t37U='

COOKIEFILE = 'mlbcookie.lwp'

AUTHFILE = os.path.join(os.environ['HOME'],'.mlb/config')
 
DEFAULT_PLAYER = 'xterm -e mplayer -cache 2048 -quiet -fs'
DEFAULT_RECORDER = 'rtmpdump -f \"LNX 10,0,22,87\" -o %e.mp4 -r %s --resume'

try:
   import cookielib
except ImportError:
   raise Exception,"Could not load cookielib"

import urllib2
import urllib

conf = os.path.join(os.environ['HOME'], AUTHFILE)
fp = open(conf)

datadct = {'video_player': DEFAULT_PLAYER,
           'video_recorder': DEFAULT_RECORDER,
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
response = urllib2.urlopen(req)
print 'These are the cookies we have received so far :'
for index, cookie in enumerate(cj):
    print index, '  :  ', cookie        
cj.save(COOKIEFILE,ignore_discard=True) 

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
   response = urllib2.urlopen(req)
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
    print response.info()                             # handle.read() returns the page, handle.geturl() returns the true url of the page fetched (in case urlopen has followed any redirects, which it sometimes does)

print
if cj == None:
    print "We don't have a cookie library available - sorry."
    print "I can't show you any cookies."
else:
    print 'These are the cookies we have received so far :'
    for index, cookie in enumerate(cj):
        print index, '  :  ', cookie        
    cj.save(COOKIEFILE,ignore_discard=True) 

page = response.read()
pattern = re.compile(r'Welcome to your personal (MLB|mlb).com account.')
try:
    loggedin = re.search(pattern, page).groups()
    print "Logged in successfully!"
except:
    raise Exception,page

# Begin MORSEL extraction
ns_headers = response.headers.getheaders("Set-Cookie")
attrs_set = cookielib.parse_ns_headers(ns_headers)
cookie_tuples = cookielib.CookieJar()._normalized_cookie_tuples(attrs_set)
print repr(cookie_tuples)
cookies = {}
for tup in cookie_tuples:
    name, value, standard, rest = tup
    cookies[name] = value
print repr(cookies)
print "ipid = " + str(cookies['ipid']) + " fingerprint = " + str(cookies['fprt'])
#print "session-key = " + str(cookies['ftmu'])
#sys.exit()
# End MORSEL extraction


# pick up the session key morsel
theurl = 'http://mlb.mlb.com/enterworkflow.do?flowId=media.media'
txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
data = None
req = urllib2.Request(theurl,data,txheaders)
response = urllib2.urlopen(req)

# Begin MORSEL extraction
ns_headers = response.headers.getheaders("Set-Cookie")
attrs_set = cookielib.parse_ns_headers(ns_headers)
cookie_tuples = cookielib.CookieJar()._normalized_cookie_tuples(attrs_set)
print repr(cookie_tuples)
#cookies = {}
for tup in cookie_tuples:
    name, value, standard, rest = tup
    cookies[name] = value
#print repr(cookies)
print "ipid = " + str(cookies['ipid']) + " fingerprint = " + str(cookies['fprt'])
try:
    print "session-key = " + str(cookies['ftmu'])
    session = urllib.unquote(cookies['ftmu'])
except:
    logout_url = 'https://secure.mlb.com/enterworkflow.do?flowId=registration.logout&c_id=mlb'
    txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13',
             'Referer' : 'http://mlb.mlb.com/index.jsp'}
    data = None
    req = urllib2.Request(logout_url,data,txheaders)
    response = urllib2.urlopen(req)
    logout_info = response.read()
    response.close()
    print "No session key, so logged out."
    #session = None

event_id = EVENT
pd = {'event-id':event_id, 'subject':'LIVE_EVENT_COVERAGE' }
reply = client.service.find(**pd)
print reply
#print reply[0][0]['user-verified-content'][0]['content-id']
content_id = reply[0][0]['user-verified-content'][0]['content-id']
print "Event-id = " + str(event_id) + " and content-id = " + str(content_id)

#cmd_str = 'rm -rf /tmp/suds'
#subprocess.Popen(cmd_str,shell=True).wait()

ip = client.factory.create('ns0:IdentityPoint')
ip.__setitem__('identity-point-id', cookies['ipid'])
ip.__setitem__('fingerprint', urllib.unquote(cookies['fprt']))

pe = {'event-id':event_id, 'subject':'LIVE_EVENT_COVERAGE', 'playback-scenario':SCENARIO, 'content-id':content_id, 'fingerprint-identity-point':ip , 'session-key':session}
reply = client.service.find(**pe)
print reply

#print reply[0][0]['user-verified-content'][0]['content-id']
game_url = reply[0][0]['user-verified-content'][0]['user-verified-media-item'][0]['url']
#sys.exit()
try:
    play_path_pat = re.compile(r'ondemand\/(.*)\?')
    play_path = re.search(play_path_pat,game_url).groups()[0]
    print "play_path = " + repr(play_path)
except:
    play_path = None
print "url = " + str(game_url)
#sys.exit()

#sys.exit()
# End MORSEL extraction

""" BEGIN COMMENT OLD CODE
wfurl = "http://www.mlb.com/enterworkflow.do?" +\
   "flowId=media.media&keepWfParams=true&mediaId=" +\
   sys.argv[1] + "&catCode=mlb_lg&av=v"
data = None

#http://www.mlb.com/enterworkflow.do?flowId=media.media&keepWfParams=true&mediaId=643342&catCode=mlb_lg&av=v

try:
   req = urllib2.Request(wfurl,data,txheaders)
   response = urllib2.urlopen(req)
   game_info = response.read()
   response.close()
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
   player = datadct['video_player']
   recorder = datadct['video_recorder']
except:
   try:
       game_url = re.search(aud_pattern, game_info).groups()[1]
       player = datadct['audio_player']
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
response = urllib2.urlopen(req)
logout_info = response.read()
response.close()

print logout_info

print 'The game url parsed is: '
print game_url
#sys.exit()
END COMMENT OLD CODE"""

theurl = 'http://cp65670.edgefcs.net/fcs/ident'
txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
data = None
req = urllib2.Request(theurl,data,txheaders)
response = urllib2.urlopen(req)
print response.read()
#sys.exit()

#theurl = 'https://cp65670.edgefcs.net/crossdomain.xml'
#txheaders = {'User-agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080311 Firefox/2.0.0.13'}
#data = None
#req = urllib2.Request(theurl,data,txheaders)
#response = urllib2.urlopen(req)
#print response.read()

#cmd_str = player + ' "' + game_url + '"'
recorder = datadct['video_recorder']
cmd_str = recorder.replace('%s', '"' + game_url + '"')
if play_path is not None:
    cmd_str += '-y ' + play_path
cmd_str = cmd_str.replace('%e', event_id)
print cmd_str + '\n'
playprocess = subprocess.Popen(cmd_str,shell=True)
playprocess.wait()

