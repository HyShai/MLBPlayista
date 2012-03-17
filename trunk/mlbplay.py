#!/usr/bin/env python

from MLBviewer import MLBSchedule
from MLBviewer import GameStream
from MLBviewer import LircConnection
from MLBviewer import MLBConfig
from MLBviewer import MLBUrlError
from MLBviewer import MLBJsonError
from MLBviewer import VERSION, URL, AUTHDIR, AUTHFILE
from MLBviewer import TEAMCODES
from MLBviewer import MLBprocess
import os
import sys
import re
import curses
import curses.textpad
import select
import datetime
import subprocess
import time
import pickle
import copy

DEFAULT_V_PLAYER = 'xterm -e mplayer -cache 2048 -quiet'
DEFAULT_A_PLAYER = 'xterm -e mplayer -cache 64 -quiet -playlist'
DEFAULT_SPEED = '1200'

def padstr(s,num):
    if len(str(s)) < num:
        p = num - len(str(s))
        return ' '*p + s
    else:
        return s

def check_bool(userinput):
    if userinput in ('0', '1', 'True', 'False'):
        return eval(userinput)

myconfdir = os.path.join(os.environ['HOME'],AUTHDIR)
myconf =  os.path.join(myconfdir,AUTHFILE)
mydefaults = {'speed': DEFAULT_SPEED,
              'video_player': DEFAULT_V_PLAYER,
              'audio_player': DEFAULT_A_PLAYER,
              'audio_follow': [],
              'video_follow': [],
              'blackout': [],
              'favorite': [],
              'use_color': 0,
              'favorite_color': 'cyan',
              'bg_color': 'xterm',
              'show_player_command': 0,
              'debug': 0,
              'x_display': '',
              'top_plays_player': '',
              'use_librtmp': 0,
              'use_nexdef': 0,
              'use_mlbhd': 0,
              'condensed' : 0,
              'nexdef_url': 0,
              'zdebug' : 0,
              'time_offset': ''}

mycfg = MLBConfig(mydefaults)
mycfg.loads(myconf)

cfg = mycfg.data

# initialize some defaults
startdate = None

teamcodes_help = "\n" +\
"Valid teamcodes are:" + "\n" +\
"\n" +\
"     'ana', 'ari', 'atl', 'bal', 'bos', 'chc', 'cin', 'cle', 'col',\n" +\
"     'cws', 'det', 'fla', 'hou', 'kc', 'la', 'mil', 'min', 'nym',\n" +\
"     'nyy', 'oak', 'phi', 'pit', 'sd', 'sea', 'sf', 'stl', 'tb',\n" +\
"     'tex', 'tor', 'was'\n" +\
"\n"

# check to see if the start date is specified on command-line
if len(sys.argv) > 1:
    for n in range(len(sys.argv)):
        if n == 0:
            continue
        pattern = re.compile(r'(.*)=(.*)')
        parsed = re.match(pattern,sys.argv[n])
        if not parsed:
            print 'Error: Arguments should be specified as variable=value'
            print "can't parse : " + sys.argv[n]
            sys.exit()
        split = parsed.groups()
        if split[0] in ( 'condensed', 'c'):
            streamtype='condensed'
            cfg['condensed'] = True
            teamcode = split[1]
            if cfg['top_plays_player']:
                player = cfg['top_plays_player']
            else:
                player = cfg['video_player']
        elif split[0] in ( 'audio', 'a' ):
            streamtype = 'audio'
            teamcode = split[1]
            player = cfg['audio_player']
        elif split[0] in ( 'video', 'v' ):
            streamtype = 'video'
            teamcode = split[1]
            player = cfg['video_player']
        elif split[0] in ( 'speed', 'p' ):
            cfg['speed'] = split[1]
        elif split[0] in ( 'nexdefurl', 'nu' ):
            parsed = check_bool(split[1])
            if parsed != None:
                cfg['nexdef_url'] = parsed
        elif split[0] in ( 'debug', 'd' ):
            parsed = check_bool(split[1])
            if parsed != None:
                cfg['debug'] = parsed
        elif split[0] in ( 'zdebug', 'z' ):
            parsed = check_bool(split[1])
            if parsed != None:
                cfg['zdebug'] = parsed
        elif split[0] in ( 'nexdef', 'n' ):
            parsed = check_bool(split[1])
            if parsed != None:
                cfg['use_nexdef'] = parsed
        elif split[0] in ( 'startdate', 'j'):
            try:
                sys.argv[n] = sys.argv[n].replace('j=', 'startdate=')
            except:
                 raise
            pattern = re.compile(r'startdate=([0-9]{1,2})(/)([0-9]{1,2})(/)([0-9]{2})')
            parsed = re.match(pattern,sys.argv[n])
            if not parsed:
                print 'Error: listing start date not in mm/dd/yy format.'
                sys.exit()
            split = parsed.groups()
            startmonth = int(split[0])
            startday  = int(split[2])
            startyear  = int('20' + split[4])
            startdate = (startyear, startmonth, startday)
        else:
            print 'Error: unknown variable argument: '+split[0]
            sys.exit()

if startdate is None:
    now = datetime.datetime.now()
    dif = datetime.timedelta(1)
    if now.hour < 9:
        now = now - dif
    startdate = (now.year, now.month, now.day)

mysched = MLBSchedule(ymd_tuple=startdate,time_shift=cfg['time_offset'])

try:
    available = mysched.getListings(cfg['speed'],cfg['blackout'],
                                    cfg['audio_follow'])
except (KeyError, MLBJsonError), detail:
    if cfg['debug']:
        raise Exception, detail
    available = []
    #raise 
    print "There was a parser problem with the listings page"
    sys.exit()

if teamcode is not None:
    if teamcode not in TEAMCODES.keys():
        print 'Invalid teamcode: ' + teamcode
        print teamcodes_help
        sys.exit()
    media = None
    for n in range(len(available)):
        home = available[n][0]['home']
        away = available[n][0]['away']
        if teamcode in ( home, away ):
            gameid = available[n][6].replace('/','-')
            if streamtype ==  'video':
                media = available[n][2]
            elif streamtype == 'condensed':
                media = available[n][2]
                condensed_media = available[n][4]
            else:
                media = available[n][3]

if media is not None:
    stream = None
    for n in range(len(media)):
        ( call_letters,
          code,
          content_id,
          event_id ) = media[n]
        if code == TEAMCODES[teamcode][0] or code == '0':
            if streamtype == 'condensed':
                stream = condensed_media[0]
            else:
                stream = media[n]
else:
    print 'Could not find media for teamcode: ' + teamcode
    sys.exit()

if cfg['zdebug']:
    print 'media = ' + repr(media)
    print 'prefer = ' + repr(stream)
    sys.exit()

if stream is not None:
    if streamtype == 'audio':
        g = GameStream(stream, cfg['user'], cfg['pass'],
                       cfg['debug'], streamtype='audio',
                       use_soap=True, use_nexdef=False,
                       use_librtmp=cfg['use_librtmp'],
                       coverage=stream[1])
    elif streamtype in ( 'video', 'condensed'):
        g = GameStream(stream, cfg['user'], cfg['pass'],
                       cfg['debug'], use_soap=True,
                       use_nexdef=cfg['use_nexdef'], speed=cfg['speed'],
                       strict=cfg['strict_stream'],
                       coverage=stream[1],condensed=cfg['condensed'],
                       postseason=False,
                       use_librtmp=cfg['use_librtmp'],
                       use_mlbhd=cfg['use_mlbhd'],
                       max_bps=cfg['max_bps'],start_time=0)
    else:
        print 'Unknown streamtype: ' + repr(streamtype)
        sys.exit()
else:
    print 'Stream could not be found.'
    print 'Media listing debug information:'
    print 'media = ' + repr(media)
    print 'prefer = ' + repr(stream)
    sys.exit()

try:
    url = g.url()
except:
    if cfg['debug']:
        raise
    else:
        print 'An error occurred locating the media URL:'
        print g.error_str
        #sys.exit()

if cfg['nexdef_url']:
    print g.nexdef_url
    sys.exit()

if cfg['debug']:
    print 'Media URL received: '
    print url
    sys.exit()

if '%s' in player:
    if cfg['use_librtmp']:
        cmd_str = player.replace('%s', url)
    else:
        cmd_str = player.replace('%s', '-')
        cmd_str = url + ' | ' + cmd_str
else:
    if cfg['use_librtmp']:
        cmd_str = player + ' ' + url
    else:
        cmd_str = url + ' | ' + player + ' -'
if '%f' in player:
    if streamtype == 'audio':
        suf = '.mp3'
    else:
        suf = '.mp4'
    cmd_str = cmd_str.replace('%f', "'" + gameid + '-' + call_letters + suf + "'")

if cfg['show_player_command']:
    print cmd_str

try:
    playprocess = subprocess.Popen(cmd_str,shell=True)
    playprocess.wait()
except KeyboardInterrupt:
    sys.exit()
except:
    raise

