#!/usr/bin/env python2

import datetime
import dialogs
from MLBviewer import *
from StringIO import StringIO
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import shutil
global jsonUrl
mlbConstants.AUTHDIR = os.getcwd()
AUTHFILE = 'config.txt'
#other constants are defined in MLBViewer/mlbConstants.py

def get_config():
	myconfdir = os.path.join(os.environ['HOME'],mlbConstants.AUTHDIR)
	myconf =  os.path.join(myconfdir,AUTHFILE)
	mydefaults = {'video_player': DEFAULT_V_PLAYER,
			  'audio_player': DEFAULT_A_PLAYER,
			  'audio_follow': [],
			  'alt_audio_follow': [],
			  'video_follow': [],
			  'blackout': [],
			  'favorite': [],
			  'use_color': 0,
			  'adaptive_stream': 1,
			  'favorite_color': 'cyan',
			  'bg_color': 'xterm',
			  'show_player_command': 0,
			  'debug': 0,
			  'x_display': '',
			  'top_plays_player': '',
			  'use_librtmp': 0,
			  'use_nexdef': 0,
			  'condensed' : 0,
			  'nexdef_url': 0,
			  'zdebug' : 0,
			  'time_offset': '',
			  'postseason':1,
			  'international': 1}

	config = MLBConfig(mydefaults)
	config.loads(myconf)
	if not config.get('speed'):
		config.set('speed', dialogs.list_dialog(title='Select a speed', items=STREAM_SPEEDS))
	if not config.get('user'):
		config.set('user', dialogs.input_alert(title='Enter your MLB.tv username'))
	if not config.get('pass'):
		config.set('pass', dialogs.password_alert(title='Enter your MLB.tv password'))
	for prop in ['speed', 'user', 'pass']:
		if not config.get(prop):
			raise Exception(prop + ' is required.')
	return config

def get_media(config,teamcode):
	# First create a schedule object
	now = datetime.datetime.now()
	startdate = (now.year, now.month, now.day)
	mysched = MLBSchedule(ymd_tuple=startdate, time_shift=config.get('time_offset'), international=config.get('international'))

	# Now retrieve the listings for that day
	available = mysched.getListings(config.get('speed'), config.get('blackout'))

	# Determine media tuple using teamcode e.g. if teamcode is in home or away, use
	# that media tuple.  A media tuple has the format:
	#     ( call_letters, code, content-id, event-id )
	# The code is a numerical value that maps to a teamcode.  It is used
	# to identify a media stream as belonging to one team or the other.  A code
	# of zero is used for national broadcasts or a broadcast that isn't owned by
	# one team or the other.
	if teamcode is not None:
		if teamcode not in TEAMCODES.keys():
			raise Exception('Invalid teamcode: ' + teamcode)
		media = []
		for n in range(len(available)):
			home = available[n][0]['home']
			away = available[n][0]['away']
			if teamcode in ( home, away ):
				listing = available[n]
				media.append(available[n][2])
				eventId = available[n][6] # ?

	# media assigned above will be a list of both home and away media tuples
	# This next section determines which media tuple to use (home or away)
	# and assign it to a stream tuple.

	if len(media) > 0:
		stream = None
		for m in media:
			for n in range(len(m)):
				( call_letters,
				  code,
				  content_id,
				  event_id ) = m[n]

				if code == TEAMCODES[teamcode][0] or code == '0':
					stream = m[n]
					break
	else:
		raise Exception('Could not find media for teamcode: ' + teamcode)

	# Before creating GameStream object, get session data from login
	session = MLBSession(user=config.get('user'), passwd=config.get('pass'), debug=config.get('debug'))
	if config.get('keydebug'):
		sessionkey = session.readSessionKey()
		print "readSessionKey: " + sessionkey
	session.getSessionData()
	# copy all the cookie data to pass to GameStream
	config.set('cookies', {})
	config.set('cookies', session.cookies)
	config.set('cookie_jar', session.cookie_jar)

	# Once the correct media tuple has been assigned to stream, create the
	# MediaStream object for the correct type of media
	if stream is not None:
		start_time = 0
		if config.get('use_nexdef'):
			if config.get('start_inning') is None:
					start_time = mysched.getStartOfGame(listing, config)

		m = MediaStream(stream=stream, session=session, cfg=config, start_time=start_time)
	else:
		print 'Media listing debug information:'
		print 'media = ' + repr(media)
		print 'prefer = ' + repr(stream)
		raise Exception('Stream could not be found.')
	# Post-rewrite, the url beast has been replaced with locateMedia() which
	# returns a raw url.
	mediaUrl = m.locateMedia()

	if config.get('keydebug'):
		sessionkey = session.readSessionKey()
		print "Session-key from media request: " + sessionkey

	# prepareMediaStreamer turns a raw url into either an mlbhls command or an
	# rtmpdump command that pipes to stdout
	media_url = m.prepareMediaStreamer(mediaUrl)

	rtmp_link   = m.preparePlayerCmd(media_url,eventId)

	global jsonUrl
	jsonUrl = '{"ChannelName":"MLBPlayista","Code":"...","Description":"MLBPlayista","StreamId":0,"ShowURL":1,"Links":["%s"],"Result":"Success","Reason":""}' % rtmp_link.strip(' "')

def get_team_list(config):
		favorites = mycfg.get('favorite')
		team_list = sorted(MLB_TEAMS.items(), key=lambda i: str(favorites.index(i[0])) if i[0] in favorites else i[0])
		return team_list

def serve_json_url():
	server = HTTPServer(('',4242),MyHandler)
	import webbrowser
	webbrowser.open('live://localhost:4242')
	#potential for race condition... :(
	server.handle_request()

class MyHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		f = StringIO()
		#print(jsonUrl)
		f.write(jsonUrl)
		length = f.tell()
		f.seek(0)
		self.send_response(200)
		self.send_header("Content-Length", str(length))
		self.send_header("Content-type", "application/json")
		self.end_headers()
		shutil.copyfileobj(f, self.wfile)

if __name__=='__main__':
	try:
		mycfg = get_config()
		team_list = get_team_list(mycfg)
		team = dialogs.list_dialog(items=[{'title': v, 'teamcode': k} for k, v in team_list])
		if not team:
			raise Exception('Please select a team.')
		teamcode = team['teamcode']
		get_media(config=mycfg,teamcode=teamcode)
		serve_json_url()
	except Exception as e:
		dialogs.alert('Error: ' + str(e))
