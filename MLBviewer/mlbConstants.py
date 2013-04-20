#!/usr/bin/env python

# mlbviewer is free software; you can redistribute it and/or modify
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, Version 2.
#
# mlbviewer is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# For a copy of the GNU General Public License, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307 USA

VERSION ="2013-sf-3"
URL = "http://sourceforge.net/projects/mlbviewer"
EMAIL = "straycat000@yahoo.com"

import os
import subprocess
import select
from copy import deepcopy
import sys
import curses
#from __init__ import VERSION, URL
from mlbDefaultKeyBindings import DEFAULT_KEYBINDINGS

# Set this to True if you want to see all the html pages in the logfile
SESSION_DEBUG=True
#DEBUG = True
#DEBUG = None
#from __init__ import AUTHDIR

# Change this line if you want to use flvstreamer instead
DEFAULT_F_RECORD = 'rtmpdump -f \"LNX 10,0,22,87\" -o %f -r %s'

# Change the next two settings to tweak mlbhd behavior
DEFAULT_HD_PLAYER = 'mlbhls -B %B'
HD_ARCHIVE_OFFSET = '48'

AUTHDIR = '.mlb'
COOKIEFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'cookie')
SESSIONKEY = os.path.join(os.environ['HOME'], AUTHDIR, 'sessionkey')
LOGFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'log')
ERRORLOG_1 = os.path.join(os.environ['HOME'], AUTHDIR, 'unsuccessful-1.xml')
ERRORLOG_2 = os.path.join(os.environ['HOME'], AUTHDIR, 'unsuccessful-2.xml')
MEDIALOG_1 = os.path.join(os.environ['HOME'], AUTHDIR, 'successful-1.xml')
MEDIALOG_2 = os.path.join(os.environ['HOME'], AUTHDIR, 'successful-2.xml')
SESSIONLOG = os.path.join(os.environ['HOME'], AUTHDIR, 'session.xml')
USERAGENT = 'Mozilla/5.0 (Windows NT 5.1; rv:18.0) Gecko/20100101 Firefox/18.0'
TESTXML = os.path.join(os.environ['HOME'], AUTHDIR, 'test_epg.xml')
BLACKFILE = os.path.join(os.environ['HOME'], AUTHDIR, 'blackout.xml')
HIGHLIGHTS_LIST = '/tmp/highlights.m3u8'

SOAPCODES = {
    "1"    : "OK",
    "-1000": "Requested Media Not Found",
    "-1500": "Other Undocumented Error",
    "-1600": "Requested Media Not Available Yet.",
    "-2000": "Authentication Error",
    "-2500": "Blackout Error",
    "-3000": "Identity Error",
    "-3500": "Sign-on Restriction Error",
    "-4000": "System Error",
}

# Status codes: Reverse mapping of status strings back to the status codes
# that were used in the json days.  Oh, those were the days. ;-)
STATUSCODES = {
    "In Progress"     : "I",
    "Completed Early" : "E",
    "Cancelled"       : "C",
    "Final"           : "F",
    "Preview"         : "P",
    "Postponed"       : "PO",
    "Game Over"       : "GO",
    "Delayed Start"   : "D",
    "Delayed"         : "D",
    "Pre-Game"        : "IP",
    "Suspended"       : "S",
    "Warmup"          : "IP",
}



# We've never used the first field, so I'm going to expand its use for 
# audio and video follow functionality.  The first field will contain a tuple
# of call letters for the various media outlets that cover that team.
TEAMCODES = {
    'ana': ('108', 'Los Angeles Angels'),
    'al' : ( None, 'American League', ''),
    'ari': ('109', 'Arizona Diamondbacks', ''),
    'atl': ('144', 'Atlanta Braves', ''),
    'bal': ('110', 'Baltimore Orioles',''),
    'bos': ('111', 'Boston Red Sox', ''),
    'chc': ('112', 'Chicago Cubs', ''),
    'chn': ('112', 'Chicago Cubs', ''),
    'cin': ('113', 'Cincinnati Reds', ''),
    'cle': ('114', 'Cleveland Indians', ''),
    'col': ('115', 'Colorado Rockies', ''),
    'cws': ('145', 'Chicago White Sox', ''),
    'cha': ('145', 'Chicago White Sox', ''),
    'det': ('116', 'Detroit Tigers', ''),
    'fla': ('146', 'Florida Marlins', ''),
    'flo': ('146', 'Florida Marlins', ''),
    'mia': ('146', 'Miami Marlins', ''),
    'hou': ('117', 'Houston Astros', ''),
    'kc':  ('118', 'Kansas City Royals', ''),
    'kca': ('118', 'Kansas City Royals', ''),
    'la':  ('119', 'Los Angeles Dodgers', ''),
    'lan': ('119', 'Los Angeles Dodgers', ''),
    'mil': ('158', 'Milwaukee Brewers', ''),
    'min': ('142', 'Minnesota Twins', ''),
    'nl' : ( None, 'National League', ''),
    'nym': ('121', 'New York Mets', ''),
    'nyn': ('121', 'New York Mets', ''),
    'nyy': ('147', 'New York Yankees', ''),
    'nya': ('147', 'New York Yankees', ''),
    'oak': ('133', 'Oakland Athletics', ''),
    'phi': ('143', 'Philadelphia Phillies', ''),
    'pit': ('134', 'Pittsburgh Pirates', ''),
    'sd':  ('135', 'San Diego Padres', ''),
    'sdn': ('135', 'San Diego Padres', ''),
    'sea': ('136', 'Seattle Mariners', ''),
    'sf':  ('137', 'San Francisco Giants', ''),
    'sfn': ('137', 'San Francisco Giants', ''),
    'stl': ('138', 'St. Louis Cardinals', ''),
    'sln': ('138', 'St. Louis Cardinals', ''),
    'tb':  ('139', 'Tampa Bay Rays', ''),
    'tba': ('139', 'Tampa Bay Rays', ''),
    'tex': ('140', 'Texas Rangers', ''),
    'tor': ('141', 'Toronto Blue Jays', ''),
    'was': ('120', 'Washington Nationals', ''),
    'wft': ('WFT', 'World', 'Futures', 'Team' ),
    'uft': ('UFT', 'USA', 'Futures', 'Team' ),
    'cif': ('CIF', 'Cincinnati Futures Team'),
    'nyf': ('NYF', 'New York Yankees Futures Team'),
    't3944': ( 'T3944', 'CPBL All-Stars' ),
    'unk': ( None, 'Unknown', 'Teamcode'),
    'tbd': ( None, 'TBD'),
    't102': ('T102', 'Round Rock Express'),
    't103': ('T103', 'Lake Elsinore Storm'),
    't234': ('T234', 'Durham Bulls'),
    't235': ('T235', 'Memphis Redbirds'),
    't241': ('T241', 'Yomiuri Giants (Japan)'),
    't249': ('T249', 'Carolina Mudcats'),
    't260': ('T260', 'Tulsa Drillers'),
    't341': ('T341', 'Hanshin Tigers (Japan)'),
    't430': ('T430', 'Mississippi Braves'),
    't445': ('T445', 'Columbus Clippers'),
    't452': ('t452', 'Altoona Curve'),
    't477': ('T477', 'Greensboro Grasshoppers'),
    't494': ('T493', 'Charlotte Knights'),
    't564': ('T564', 'Jacksonville Suns'),
    't569': ('T569', 'Quintana Roo Tigres'),
    't580': ('T580', 'Winston-Salem Dash'),
    't588': ('T588', 'New Orleans Zephyrs'),
    't784': ('T784', 'WBC Canada'),
    't805': ('T805', 'WBC Dominican Republic'),
    't841': ('T841', 'WBC Italy'),
    't878': ('T878', 'WBC Netherlands'),
    't890': ('T890', 'WBC Panama'),
    't897': ('T897', 'WBC Puerto Rico'),
    't944': ('T944', 'WBC Venezuela'),
    't940': ('T940', 'WBC United States'),
    't918': ('T918', 'WBC South Africa'),
    't867': ('T867', 'WBC Mexico'),
    't760': ('T760', 'WBC Australia'),
    't790': ('T790', 'WBC China'),
    't843': ('T843', 'WBC Japan'),
    't791': ('T791', 'WBC Taipei'),
    't798': ('T798', 'WBC Cuba'),
    't1171': ('T1171', 'WBC Korea'),
    't1193': ('T1193', 'WBC Venezuela'),
    't2290': ('T2290', 'University of Michigan'),
    't2330': ('T3330', 'Georgetown University'),
    't2330': ('T3330', 'Georgetown University'),
    't2291': ('T2291', 'St. Louis University'),
    't2292': ('T2292', 'University of Southern Florida'),
    't2510': ('T2510', 'Team Canada'),
    't4744': ('ABK', 'Army Black Knights'),
    'uga' : ('UGA',  'University of Georgia'),
    'mcc' : ('MCC', 'Manatee Community College'),
    'fso' : ('FSO', 'Florida Southern College'),
    'fsu' : ('FSU', 'Florida State University'),
    'neu' : ('NEU',  'Northeastern University'),
    'bc' : ('BC',  'Boston', 'College', ''),
    }

STREAM_SPEEDS = ( '300', '500', '1200', '1800', '2400' )

DEFAULT_SPEED = '1200'

DEFAULT_V_PLAYER = 'mplayer -cache 2048 -really-quiet'
DEFAULT_A_PLAYER = 'mplayer -cache 64 -really-quiet'

DEFAULT_FLASH_BROWSER='firefox %s'

BOOKMARK_FILE = os.path.join(os.environ['HOME'], AUTHDIR, 'bookmarks.pf')

KEYBINDINGS = { 'Up/Down'    : 'Highlight games in the current view',
                'Enter'      : 'Play video of highlighted game',
                'Left/Right' : 'Navigate one day forward or back',
                'c'          : 'Play Condensed Game Video (if available)',
                'j'          : 'Jump to a date',
                'm'          : 'Bookmark a game or edit bookmark title',
                'n'          : 'Toggle NEXDEF mode',
                'l (or Esc)' : 'Return to listings',
                'b'          : 'View line score',
                'z'          : 'Show listings debug',
                'o'          : 'Show options debug',
                'x (or Bksp)': 'Delete a bookmark',
                'r'          : 'Refresh listings',
                'q'          : 'Quit mlbviewer',
                'h'          : 'Display version and keybindings',
                'a'          : 'Play Gameday audio of highlighted game',
                'd'          : 'Toggle debug (does not change config file)',
                'p'          : 'Toggle speed (does not change config file)',
                's'          : 'Toggle coverage for HOME or AWAY stream',
                't'          : 'Display top plays listing for current game',
                'y'          : 'Play all highlights as a playlist',
              }

HELPFILE = (
    ('COMMANDS' , ( 'Enter', 'a', 'c', 'd', 'n', 's' )),
    ('LISTINGS', ( 'Up/Down', 'Left/Right', 'j', 'p', 'r' )),
    ('SCREENS'  , ( 't', 'h', 'l (or Esc)', 'b' )),
    ('DEBUG'    , ( 'z', 'o' )),
    )

KEYBINDINGS_1 = { 
    'UP'                  : 'Move cursor up in the current view',
    'DOWN'                : 'Move cursor down in current view',
    'VIDEO'               : 'Play video of highlighted game',
    'LEFT'                : 'Navigate one day back',
    'RIGHT'               : 'Navigate one day forward',
    'CONDENSED_GAME'      : 'Play Condensed Game Video (if available)',
    'JUMP'                : 'Jump to a date',
    'NEXDEF'              : 'Toggle NEXDEF mode',
    'LISTINGS'            : 'Return to listings',
    'INNINGS'             : 'Jump to specific half inning',
    'LINE_SCORE'          : 'View line score',
    'BOX_SCORE'           : 'View box score',
    'MASTER_SCOREBOARD'   : 'Master scoreboard view',
    'MEDIA_DEBUG'         : 'Show media listings debug',
    'OPTIONS'             : 'Show options debug',
    'REFRESH'             : 'Refresh listings',
    'QUIT'                : 'Quit mlbviewer',
    'HELP'                : 'Display version and keybindings',
    'AUDIO'               : 'Play Gameday audio of highlighted game',
    'DEBUG'               : 'Toggle debug (does not change config file)',
    'SPEED'               : 'Toggle speed (does not change config file)',
    'COVERAGE'            : 'Toggle coverage for HOME or AWAY stream',
    'HIGHLIGHTS'          : 'Display top plays listing for current game',
    'HIGHLIGHTS_PLAYLIST' : 'Play all highlights as a playlist',
    'STANDINGS'           : 'View standings (not real-time; updated once a day)',
    }

HELPBINDINGS = (
    ('COMMANDS', ('VIDEO', 'AUDIO', 'CONDENSED_GAME', 'DEBUG', 'NEXDEF', 
                  'COVERAGE', 'HIGHLIGHTS_PLAYLIST', 'INNINGS') ),
    ('LISTINGS', ('UP', 'DOWN', 'LEFT', 'RIGHT', 'JUMP', 'SPEED', 'REFRESH' )),
    ('SCREENS', ('HIGHLIGHTS', 'HELP', 'LISTINGS', 'LINE_SCORE', 'BOX_SCORE',
     'MASTER_SCOREBOARD', 'STANDINGS' ) ),
    ('DEBUG', ( 'OPTIONS', 'DEBUG', 'MEDIA_DEBUG' )),
    )

OPTIONS_DEBUG = ( 'video_player', 'audio_player', 'top_plays_player',
                  'speed', 'use_nexdef', 'use_wired_web', 'min_bps', 'max_bps',
                  'adaptive_stream', 'use_librtmp', 'live_from_start',
                  'video_follow', 'audio_follow', 'blackout', 'coverage',
                  'free_condensed', 'show_player_command', 'user' )

COLORS = { 'black'   : curses.COLOR_BLACK,
           'red'     : curses.COLOR_RED,
           'green'   : curses.COLOR_GREEN,
           'yellow'  : curses.COLOR_YELLOW,
           'blue'    : curses.COLOR_BLUE,
           'magenta' : curses.COLOR_MAGENTA,
           'cyan'    : curses.COLOR_CYAN,
           'white'   : curses.COLOR_WHITE,
           'xterm'   : -1
         }

STATUSLINE = {
        "E" : "Status: Completed Early",
        "C" : "Status: Cancelled",
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

SPEEDTOGGLE = {
        "300"  : "[ 300K]",
        "500"  : "[ 500K]",
        "1200" : "[1200K]",
        "1800" : "[1800K]",
        "2400" : "[2400K]"}

COVERAGETOGGLE = {
    "away" : "[AWAY]",
    "home" : "[HOME]"}

SSTOGGLE = {
    True  : "[>>]",
    False : "[--]"}


UNSUPPORTED = 'ERROR: That key is not supported in this screen'

# for line scores
RUNNERS_ONBASE_STATUS = {
    '0': 'Empty',
    '1': '1B',
    '2': '2B',
    '3': '3B',
    '4': '1B and 2B',
    '5': '1B and 3B',
    '6': '2B and 3B',
    '7': 'Bases loaded',
}

RUNNERS_ONBASE_STRINGS = {
    'runner_on_1b': 'Runner on 1B',
    'runner_on_2b': 'Runner on 2B',
    'runner_on_3b': 'Runner on 3B',
}

STANDINGS_DIVISIONS = {
    'MLB.AL.E':  'AL East',
    'MLB.AL.C':  'AL Central',
    'MLB.AL.W':  'AL West',
    'MLB.NL.E':  'NL East',
    'MLB.NL.C':  'NL Central',
    'MLB.NL.W':  'NL West',
}

