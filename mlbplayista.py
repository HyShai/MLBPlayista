#!/usr/bin/env python2

import datetime
import dialogs
from MLBviewer import *
from StringIO import StringIO
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import shutil
import console

mlbConstants.AUTHDIR = os.getcwd()
AUTHFILE = 'config.txt'
# other constants are defined in MLBViewer/mlbConstants.py


def get_config():
	myconfdir = os.path.join(os.environ['HOME'], mlbConstants.AUTHDIR)
	myconf = os.path.join(myconfdir, AUTHFILE)
	mydefaults = {
		'video_player': DEFAULT_V_PLAYER,
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
		'use_librtmp': 1,
		'use_nexdef': 0,
		'condensed': 0,
		'nexdef_url': 0,
		'zdebug': 0,
		'time_offset': '',
		'postseason': 1,
		'international': 1}

	config = MLBConfig(mydefaults)
	config.loads(myconf)
	if config.get('debug'):
		print 'Config: ' + repr(config.data)
	try:
		if not config.get('user'):
			config.set('user', dialogs.input_alert(title='Enter your MLB.tv username'))
		if not config.get('pass'):
			config.set('pass', dialogs.password_alert(
				title='Enter your MLB.tv password'))
		if not config.get('speed'):
			config.set('speed', dialogs.list_dialog(
				title='Select a speed (Kbps)', items=STREAM_SPEEDS))
	except KeyboardInterrupt:
		pass
	for prop in ['user', 'pass', 'speed']:
		if not config.get(prop):
			raise Exception(prop + ' is required')
	return config


def get_listings(config):
	now = datetime.datetime.now()
	if now.hour < 9:
		# go back to yesterday if before 9am
		now = now - datetime.timedelta(1)
	startdate = (now.year, now.month, now.day)
	mysched = MLBSchedule(
		ymd_tuple=startdate,
		time_shift=config.get('time_offset'),
		international=config.get('international'))

	# Now retrieve the listings for that day
	available = mysched.getListings(config.get('speed'), config.get('blackout'))
	if config.get('debug'):
		print 'Listings: ' + repr(available)
	return available


def sort_listings(config, listings):
	teamlist = []
	for listing in listings:
		hometeam = listing[0]['home']
		awayteam = listing[0]['away']
		title = '%s \nat %s\n%s (%s)' % (
			TEAMCODES[awayteam][1],
			TEAMCODES[hometeam][1],
			listing[1].strftime('%l:%M %p').strip(),
			STATUSLINE[listing[5]].replace(
				'Status: ', '').replace(' (Condensed Game Available)', ''))
		teamlist.append({
			'title': title.strip(), 'hometeam': hometeam, 'awayteam': awayteam})
	favorites = config.get('favorite')
	teamlist = sorted(
		teamlist,
		key=lambda i:
			str(
				favorites.index(i['hometeam']) if i['hometeam'] in favorites else
				favorites.index(i['awayteam']) if i['awayteam'] in favorites else 'z'))

	return teamlist


def select_game(listings):
	listings_view = ListingsView(listings)
	listings_view.view.name = 'Select a game'
	listings_view.view.present('sheet')
	listings_view.view.wait_modal()
	if not listings_view.selected_item:
		raise Exception('Please select a game')
	return listings_view.selected_item


def get_media(config, listings, teamcode):
	# Determine media tuple using teamcode e.g. if teamcode is in home or away,
	# use that media tuple.  A media tuple has the format:
	#     ( call_letters, code, content-id, event-id )
	# The code is a numerical value that maps to a teamcode.  It is used
	# to identify a media stream as belonging to one team or the other.  A code
	# of zero is used for national broadcasts or a broadcast that isn't owned by
	# one team or the other.
	if teamcode is not None:
		if teamcode not in TEAMCODES.keys():
			raise Exception('Invalid teamcode: ' + teamcode)
		media = []
		for listing in listings:
			home = listing[0]['home']
			away = listing[0]['away']
			if teamcode in (home, away):
				media.append(listing[2])
				eventId = listing[6]  # ?

	if config.get('debug'):
		print 'Media: ' + repr(media)
	# media assigned above will be a list of both home and away media tuples
	# This next section determines which media tuple to use (home or away)
	# and assign it to a stream tuple.
	if len(media) > 0:
		stream = None
		for m in media:
			for n in range(len(m)):
				(call_letters,
					code,
					content_id,
					event_id) = m[n]

				if code == TEAMCODES[teamcode][0] or code == '0':
					stream = m[n]
					break
	else:
		raise Exception('Could not find media for teamcode: ' + teamcode)
	if config.get('debug'):
		print 'Stream: ' + repr(stream)
	# Before creating GameStream object, get session data from login
	session = MLBSession(
		user=config.get('user'),
		passwd=config.get('pass'),
		debug=config.get('debug'))
	if config.get('debug'):
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
		m = MediaStream(
			stream=stream,
			session=session,
			cfg=config,
			start_time=start_time)
	else:
		raise Exception('Stream could not be found.')
	# Post-rewrite, the url beast has been replaced with locateMedia() which
	# returns a raw url.
	mediaUrl = m.locateMedia()
	if config.get('debug'):
		print 'MediaURL: ' + mediaUrl
	# prepareMediaStreamer turns a raw url into either an mlbhls command or an
	# rtmpdump command that pipes to stdout
	media_url = m.prepareMediaStreamer(mediaUrl)
	if config.get('debug'):
		print 'Prepared media_url: ' + mediaUrl
	rtmp_link = m.preparePlayerCmd(media_url, eventId)
	if config.get('debug'):
		print 'rtmp link: ' + rtmp_link
	global jsonUrl
	jsonUrl = (
		'{"ChannelName":"MLBista","Code":"...",'
		'"Description":"MLBista","StreamId":0,"ShowURL":1,'
		'"Links":["%s"],"Result":"Success","Reason":""}' % rtmp_link.strip(' "'))
	if config.get('debug'):
		print 'jsonUrl: ' + jsonUrl


def serve_json_url():
	server = HTTPServer(('', 4242), MyHandler)
	import webbrowser
	webbrowser.open('live://localhost:4242')
	# potential for race condition... :(
	server.handle_request()


def live_player_is_installed():
	try:
		from objc_util import ObjCClass, nsurl
	except ImportError:
		# don't blow up if objc_util doesn't exist
		return True
	LSApplicationWorkspace = ObjCClass('LSApplicationWorkspace')
	workspace = LSApplicationWorkspace.defaultWorkspace()
	if workspace.applicationForOpeningResource_(
		nsurl('fb493207460770675:')) or workspace.applicationForOpeningResource_(
		nsurl('fb1574042342908027:')):
		return True
	return False


class MyHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		f = StringIO()
		# print(jsonUrl)
		f.write(jsonUrl)
		length = f.tell()
		f.seek(0)
		self.send_response(200)
		self.send_header("Content-Length", str(length))
		self.send_header("Content-type", "application/json")
		self.end_headers()
		shutil.copyfileobj(f, self.wfile)


class ListingsView(object):
	def __init__(self, listings):
		self.items = listings
		self.selected_item = None
		import ui
		self.view = ui.TableView()
		ds = ui.ListDataSource(listings)
		ds.number_of_lines = 3
		ds.action = self.row_selected
		self.view.data_source = ds
		self.view.row_height = 75
		self.view.delegate = ds

	def row_selected(self, ds):
		self.selected_item = self.items[ds.selected_row]
		self.view.close()


if __name__ == '__main__':
	try:
		if not live_player_is_installed():
			raise Exception('Please install Live Player')
		config = get_config()
		console.show_activity('Getting schedule...')
		listings = get_listings(config)
		console.hide_activity()
		gamelist = sort_listings(config, listings)
		game = select_game(gamelist)
		team = dialogs.list_dialog(
			title='Select team broadcast',
			items=[{
				'teamcode': k,
				'title': TEAMCODES[k][1]} for k in [game['hometeam'], game['awayteam']]])
		if not team:
			raise Exception('No broadcast selected')
		teamcode = team['teamcode']
		console.show_activity('Getting media...')
		get_media(config=config, listings=listings, teamcode=teamcode)
		console.hide_activity()
		if config.get('debug'):
			sys.exit()
		serve_json_url()
	except Exception as e:
		dialogs.alert('Error: ' + str(e))
