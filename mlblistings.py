#!/usr/bin/env python
"""Mlblistings.py is a test application that uses the MLBviewer library (which
is why it's not located in the test directory) and prints the listings for
a given day in a predictable "awk-able" format.  It is meant primarily for
finding the event-id of a particular game which can be used with the test
tools described in the next section.

Mlblistings.py supports the startdate=mm/dd/yy command-line option.

Sample output:

$ mlblistings.py
MLB.TV Listings for 5/2/2009
CG: 10:05 AM: 2009/05/02/anamlb-nyamlb-1 E: 14-244538-2009-05-02
CG: 10:05 AM: 2009/05/02/flomlb-chnmlb-1 E: 14-244546-2009-05-02
CG: 10:05 AM: 2009/05/02/slnmlb-wasmlb-1 E: 14-244552-2009-05-02
CG: 10:07 AM: 2009/05/02/balmlb-tormlb-1 E: 14-244540-2009-05-02
CG: 12:30 PM: 2009/05/02/houmlb-atlmlb-1 E: 14-244547-2009-05-02
CG: 12:40 PM: 2009/05/02/clemlb-detmlb-1 E: 14-244544-2009-05-02
CG: 12:40 PM: 2009/05/02/nynmlb-phimlb-1 E: 14-244549-2009-05-02
CG:  1:05 PM: 2009/05/02/colmlb-sfnmlb-1 E: 14-244545-2009-05-02
CG:  4:05 PM: 2009/05/02/arimlb-milmlb-1 E: 14-244539-2009-05-02
CG:  4:05 PM: 2009/05/02/cinmlb-pitmlb-1 E: 14-244543-2009-05-02
CG:  4:08 PM: 2009/05/02/bosmlb-tbamlb-1 E: 14-244541-2009-05-02
CG:  4:10 PM: 2009/05/02/kcamlb-minmlb-1 E: 14-244548-2009-05-02
CG:  5:05 PM: 2009/05/02/chamlb-texmlb-1 E: 14-244542-2009-05-02
CG:  6:10 PM: 2009/05/02/oakmlb-seamlb-1 E: 14-244550-2009-05-02
CG:  7:10 PM: 2009/05/02/sdnmlb-lanmlb-1 E: 14-244551-2009-05-02

The first line can be ignored or excluded with grep -v.

The fields for the remaining lines are:

1:Status Code (one of the following):
        "I" : "Status: In Progress",
        "W" : "Status: Not Yet Available",
        "F" : "Status: Final",
        "CG": "Status: Final (Condensed Game Available)",
        "P" : "Status: Not Yet Available",
        "S" : "Status: Suspended",
        "D" : "Status: Delayed",
        "IP": "Status: Pregame",
        "PO": "Status: Postponed",
        "GO": "Status: Game Over - stream not yet available",
        "NB": "Status: National Blackout",
        "LB": "Status: Local Blackout"

2:Game Time: Translated using time_offset option in ~/.mlb/config, if present

3:Gameid: These game id's are always of the format:
          year/month/day/awayteam-hometeam-sequence
          The sequence number is almost always 1 unless there is a doubleheader
          that day.

4:Event ID: This ID is necessary for the test tools described in the next
            section.

The event ID's can be used with the test scripts in the test directory.

The times are already in a format the 'at' command can accept so it is
possible to schedule a game to play automatically using the at command in
conjunction with mlbplay.  See the at(1) man page for more details on the
at command.

The mlblistings.py script uses the $HOME/.mlb/config file wherever relevant,
and also accepts the startdate=m/d/yy command-line option for looking at
listings in the future (or the past.)

Mlblistings.py can also be used as an example for developing your own
application using the MLBviewer python library.

TEST TOOLS

The following scripts located in the test directory are meant to provide
verbose logging and network debugging.  These scripts are provided as a
means to collect more information than mlbviewer provides and to test new
network algorithms.  They are not meant to replace mlbviewer or mlbplay in
any way.  There will be no feature development for these scripts.  The only
time the end user is expected to use these scripts is when the author requests
more information for troubleshooting problems unique to that user.

All scripts take the event ID (field 4 from mlblistings.py) as the only
mandatory argument.  Optionally, the coverage can be selected by providing the
content ID.  The content ID is found through the 'z' screen in mlbviewer.

gdaudio.py  <event-id>  : Gameday audio

mlbgame.py <event-id>   : Basic service video

nexdef.py <event-id>    : Nexdef (premium service) video

These utilities are only meant to provide small sample files for media player
debugging e.g. to file a bug report with mplayer or ffmpeg development:

mlbgamedl.py <event-id> : Record basic service video

nexdefdl.py <event-id>  : Record nexdef video

MEDIAXML or DEBUGGING FAILED MEDIA REQUESTS

Media location replies are logged to ~/.mlb directory either as:

~/.mlb/successful-1.xml   : contains listing of all available media for
                            requested stream type (audio, video, condensed game)
~/.mlb/successful-2.xml   : reply for specific media from listing above

If one of these requests returns an error status-code, that particular reply
is logged to either ~/.mlb/unsuccessful-1.xml or ~/.mlb/unsuccessful-2.xml,
respectively.

And mlbviewer will display one of the following:

    "-1000": "Requested Media Not Found",
    "-1500": "Other Undocumented Error",
    "-1600": "Requested Media Not Available Yet.",
    "-2000": "Authentication Error",
    "-2500": "Blackout Error",
    "-3000": "Identity Error",
    "-3500": "Sign-on Restriction Error",
    "-4000": "System Error",

mlbviewer should also tell you which of the ~/.mlb XML files to look in for
the failure reply.  The main log file ~/.mlb/log will also have the error
and which xml reply file to consult.

The XML replies are verbose but contain a lot of useful information.  They
can be parsed using the test/mediaxml.py script, e.g.

$ test/mediaxml.py ~/.mlb/unsuccessful-2.xml

This script will convert the XML into something more readable.

When reporting problems about "Requested Media Not Found" or "Blackout Error",
please post the XML files to http://pastebin.com, or post the full output from
mediaxml.py.

DEBUGGING AUDIO / VIDEO PROBLEMS USING TOOLS

First and foremost, mplayer2 is recommended for playing the nexdef media
streams.

Basic Service Debugging

1. Download and install mplayer2.  If your Linux distribution does not have
mplayer2 in its package repository, navigate to http://www.mplayer2.org and
download a binary or build from source.

2. Record a small sample of the stream using the following command:

$ test/mlbgamedl.py 14-332571-2012-04-04

Ctrl-C after a few seconds have been recorded:

INFO: sampledescription:
INFO:   length                513634304.00
INFO:   timescale             48000.00
INFO:   language              und
INFO: sampledescription:
513.631 kB / 4.91 sec (0.0%)

3. Open the sample using mplayer:

$ mplayer 14-332571-2012-04-04.mp4

If the errors are not immediately obvious to you, please post the mplayer
command output to http://pastebin.com .

4. Post the resulting link from the paste operation to http://pastebin.com to
the linuxforums thread mentioned in README file.

Premium Service Debugging

1. Download and install mplayer2.  If your Linux distribution does not have
mplayer2 in its package repository, navigate to http://www.mplayer2.org and
download a binary or build from source.

2. Perform step 2 above recording a small video sample using:

$ test/nexdefdl.py 14-332571-2012-04-04

Ctrl-C after two or three lines like the following:

[MLB] Get: 12/00/01.ts (bw: 500000, time: 2.61s) [Avg. D/L Rate of last 3 chunks: 1.32 Mbps]
[MLB] Get: 12/00/07.ts (bw: 500000, time: 2.58s) [Avg. D/L Rate of last 3 chunks: 1.37 Mbps]

3. Perform step 3 same as above.

4. Perform step 4 same as above.

If video is working but not audio, use the # key in mplayer to switch between
audio streams.  Often the '0' stream is silent, with the '1' and '2'
audio streams being audio from the TV stream and synchronized audio from the
radio stream, respectively.
"""
from MLBviewer import *
import os
import sys
import re

import select
import datetime
import subprocess
import time
import pickle
import copy


def padstr(s,num):
    if len(str(s)) < num:
        p = num - len(str(s))
        return ' '*p + s
    else:
        return s


myconfdir = os.path.join(os.environ['HOME'],AUTHDIR)
myconf =  os.path.join(myconfdir,AUTHFILE)
mydefaults = {'speed': DEFAULT_SPEED,
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
              'use_librtmp': 0,
              'use_nexdef': 0,
              'condensed' : 0,
              'nexdef_url': 0,
              'adaptive_stream': 1,
              'zdebug' : 0,
              'time_offset': '',
               'international':1}

mycfg = MLBConfig(mydefaults)
mycfg.loads(myconf)

cfg = mycfg.data
# check to see if the start date is specified on command-line
if len(sys.argv) > 1:
    pattern = re.compile(r'(.*)=(.*)')
    parsed = re.match(pattern,sys.argv[1])
    if not parsed:
        print 'Error: Arguments should be specified as variable=value'
        sys.exit()
    split = parsed.groups()
    if split[0] not in ('startdate'):
        print 'Error: unknown variable argument: '+split[0]
        sys.exit()

    pattern = re.compile(r'startdate=([0-9]{1,2})(/)([0-9]{1,2})(/)([0-9]{2})')
    parsed = re.match(pattern,sys.argv[1])
    if not parsed:
        print 'Error: listing start date not in mm/dd/yy format.'
        sys.exit()
    split = parsed.groups()
    startmonth = int(split[0])
    startday  = int(split[2])
    startyear  = int('20' + split[4])
    startdate = (startyear, startmonth, startday)
else:
    now = datetime.datetime.now()
    dif = datetime.timedelta(1)
    if now.hour < 9:
        now = now - dif
    startdate = (now.year, now.month, now.day)

mysched = MLBSchedule(ymd_tuple=startdate,time_shift=mycfg.get('time_offset'), cfg=cfg)

try:
    available = mysched.getListings(mycfg.get('speed'),mycfg.get('blackout'))
except (KeyError, MLBXmlError), detail:
    if cfg['debug']:
        raise Exception, detail
    available = []
    #raise 
    print "There was a parser problem with the listings page"
    sys.exit()

# This is more for documentation. Mlblistings.py is meant to produce more 
# machine readable output rather than user-friendly output like mlbviewer.py.
statusline = {
    "I" : "Status: In Progress",
    "W" : "Status: Not Yet Available",
    "F" : "Status: Final",
    "CG": "Status: Final (Condensed Game Available)",
    "P" : "Status: Not Yet Available",
    "S" : "Status: Suspended",
    "D" : "Status: Delayed",
    "IP": "Status: Pregame",
    "PO": "Status: Postponed",
    "GO": "Status: Game Over - stream not yet available",
    "NB": "Status: National Blackout",
    "LB": "Status: Local Blackout"}

print "MLB.TV Listings for " +\
    str(mysched.month) + '/' +\
    str(mysched.day)   + '/' +\
    str(mysched.year)

for n in range(len(available)):
    # This is how you can recreate the mlbviewer output (e.g. user-friendly)
    # You would uncomment the print str(s) line and comment out the 
    # the print str(c) 
    # Or mix and match between the lines to produce the output you find
    # easiest for you (such as printing raw home and away teamcodes without 
    # translating them in the TEAMCODES dictionary, e.g.
    # "kc at tex"  instead of "Kansas City Royals at Texas Rangers"
    home = available[n][0]['home']
    away = available[n][0]['away']
    s = available[n][1].strftime('%l:%M %p') + ': ' +\
       ' '.join(TEAMCODES[away][1:]).strip() + ' at ' +\
       ' '.join(TEAMCODES[home][1:]).strip()
    #print str(s)
    c = padstr(available[n][5],2) + ": " +\
        available[n][1].strftime('%l:%M %p') + ': ' +\
        available[n][6] 
    try:
        c += ' E:' + padstr(str(available[n][3][0][3]),21)
    except (TypeError, IndexError):
        c += ' E:' + padstr('None',21)
    #print str(c)
    print available