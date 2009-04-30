#!/usr/bin/env python

from MLBviewer import MLBSchedule
from MLBviewer import GameStream
from MLBviewer import LircConnection
from MLBviewer import MLBConfig
from MLBviewer import MLBUrlError
from MLBviewer import MLBJsonError
from MLBviewer import VERSION, URL, AUTHDIR, AUTHFILE, LOGFILE
from MLBviewer import TEAMCODES
from MLBviewer import MLBLog
from MLBviewer import MLBprocess
import os
import signal
import sys
import re
import curses
import curses.textpad
import select
import datetime
import subprocess
import commands
import time
import pickle
import copy

DEFAULT_V_PLAYER = 'xterm -e mplayer -cache 2048 -quiet'
DEFAULT_A_PLAYER = 'xterm -e mplayer -cache 64 -quiet -playlist'
DEFAULT_SPEED = '800'

DEFAULT_FLASH_BROWSER='firefox %s'

BOOKMARK_FILE = os.path.join(os.environ['HOME'], AUTHDIR, 'bookmarks.pf')

KEYBINDINGS = { 'Up/Down'    : 'Highlight games in the current view',
                'Enter'      : 'Play video of highlighted game',
                'Left/Right' : 'Navigate one day forward or back',
                'c'          : 'Play Condensed Game Video (if available)',
                'j'          : 'Jump to a date',
                'm'          : 'Bookmark a game or edit bookmark title',
                'l (or Esc)' : 'Return to listings',
                'b'          : 'View bookmarks',
                'x (or Bksp)': 'Delete a bookmark',
                'r'          : 'Refresh listings',
                'q'          : 'Quit mlbviewer',
                'h'          : 'Display version and keybindings',
                'a'          : 'Play Gameday audio of highlighted game',
                'd'          : 'Toggle debug (does not change config file)',
                'p'          : 'Toggle speed (does not change config file)',
                't'          : 'Display top plays listing for current game'
              }

HELPFILE = (
    ('COMMANDS' , ( 'Enter', 'a', 'c', 'd' )),
    ('LISTINGS', ( 'Up/Down', 'Left/Right', 'j', 'p', 'r' )),
    ('SCREENS'  , ( 't', 'b', 'h', 'l (or Esc)' )),
    ('BOOKMARKS', ( 'm', 'x (or Bksp)' ))
    )



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

def doinstall(config,dct,dir=None):
    print "Creating configuration files"
    if dir:
        try:
            os.mkdir(dir)
        except:
            print 'Could not create directory: ' + dir + '\n'
            print 'See README for configuration instructions\n'
            sys.exit()
    # now write the config file
    try:
        fp = open(config,'w')
    except:
        print 'Could not write config file: ' + config
        print 'Please check directory permissions.'
        sys.exit()
    fp.write('# See README for explanation of these settings.\n')
    fp.write('# user and pass are required except for Top Plays\n')
    fp.write('user=\n')
    fp.write('pass=\n\n')
    for k in dct.keys():
        if type(dct[k]) == type(list()):
            if len(dct[k]) > 0:
                for item in dct[k]:
                    fp.write(k + '=' + str(dct[k]) + '\n')
                fp.write('\n')
            else:
                fp.write(k + '=' + '\n\n')
        else:
            fp.write(k + '=' + str(dct[k]) + '\n\n')
    fp.close()
    print
    print 'Configuration complete!  You are now ready to use mlbviewer.'
    print
    print 'Configuration file written to: '
    print
    print config
    print
    print 'Please review the settings.  You will need to set user and pass.'
    sys.exit()

def prompter(win,prompt):
    win.clear()
    win.addstr(0,0,prompt,curses.A_BOLD)
    win.refresh()

    responsewin = win.derwin(0, len(prompt))
    responsebox = curses.textpad.Textbox(responsewin)
    responsebox.edit()
    output = responsebox.gather()

    return output

def mainloop(myscr,cfg):

    log = open(LOGFILE,"a")
    DISABLED_FEATURES = []
    CURRENT_SCREEN = 'listings'
    # Toggle the speed to 400k for top plays.  
    # Initialize the value here in case 'l' selected before 't'
    RESTORE_SPEED = cfg['speed']

    if cfg['x_display']:
        os.environ['DISPLAY'] = cfg['x_display']

    try: 
        curses.curs_set(0)
    except curses.error: 
        pass

    LIRC = 1
    try:
        irc_conn = LircConnection()
        irc_conn.connect()
        irc_conn.getconfig()
        irc_socket=irc_conn.conn
        s = "LIRC Initialized"
        inputlst = [sys.stdin, irc_socket]
    except:
        s = "LIRC not initialized"
        LIRC = 0
        inputlst = [sys.stdin]

    log.write(s + '\n\n')
    log.flush()

    if hasattr(curses, 'use_default_colors'):
        try:
            curses.use_default_colors()
            if cfg['use_color']:
                try:
                    if cfg.has_key('fg_color'):
                        cfg['favorite_color'] = cfg['fg_color']
                    curses.init_pair(1, COLORS[cfg['favorite_color']],
                                        COLORS[cfg['bg_color']])
                except KeyError:
                    cfg['use_color'] = False
                    curses.init_pair(1, -1, -1)
        except curses.error:
            pass

    myscr = curses.initscr()

    # This will be used for statuslines
    statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
    titlewin  = curses.newwin(2,curses.COLS-1,0,0)


    current_cursor = 0
    
    # Print a simple splash for now just so we don't show dead screen while
    # we're fetching the listings
    lines = ('mlbviewer', VERSION, URL)
    for i in xrange(len(lines)):
        myscr.addstr(curses.LINES/2+i, (curses.COLS-len(lines[i]))/2, lines[i])
    statuswin.addstr(0,0,'Please wait for listings to load...')
    statuswin.refresh()
    myscr.refresh()
    titlewin.refresh()

    mysched = MLBSchedule(ymd_tuple=startdate,time_shift=cfg['time_offset'])
    # We'll make a note of the date, to return to it later.
    today_year = mysched.year
    today_month = mysched.month
    today_day = mysched.day

    try:
        available = mysched.getListings(cfg['speed'],cfg['blackout'],cfg['audio_follow'])
    except (KeyError, MLBJsonError), detail:
        #raise Exception,detail
        if cfg['debug']:
            raise Exception, detail
        available = []
        status_str = "There was a parser problem with the listings page"
        statuswin.addstr(0,0,status_str)
        statuswin.refresh()
        time.sleep(2)

    use_xml = mysched.use_xml

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

    speedtoggle = {
        "400" : "[400K]",
        "800" : "[800K]"}

    coveragetoggle = {
        "away" : "[AWAY]",
        "home" : "[HOME]"}

    cfg['coverage'] = "home"

    while True:
        myscr.clear()
        statuswin.clear()
        titlewin.clear()

        # if we're in top plays screen, listings title is replaced with top
        # plays title
        if 'topPlays' in CURRENT_SCREEN:
            # probably a better way to do this, but some games don't have
            # highlights :(
            if not available:
                titlestr = "NO TOP PLAYS AVAILABLE FOR THIS GAME"
            else:
                titlestr = "TOP PLAYS FOR " + available[current_cursor][0] +\
                ' (' +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year) + ')' 
        elif 'bookmarks' in CURRENT_SCREEN:
            titlestr = "BOOKMARKS (Displaying " + str(len(available)) + ' of ' + str(len(bookmarks)) + ')'
        else:
            titlestr = "AVAILABLE GAMES FOR " +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year) + ' ' +\
                '(Use arrow keys to change days)'

        padding = curses.COLS - (len(titlestr) + 6)
        titlestr += ' '*padding
        pos = len(titlestr)

        # Draw the date
        titlewin.addstr(0,0,titlestr)
        titlewin.addstr(0,pos,'H', curses.A_BOLD)
        titlewin.addstr(0,pos+1,'elp')

        # Draw a line
        titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)

        for n in range(curses.LINES-4):
            if n < len(available):
                if 'topPlays' in CURRENT_SCREEN:
                    s = available[n][1]
                elif 'bookmarks' in CURRENT_SCREEN:
                    s = available[n][0]['home']
                else:
                    home = available[n][0]['home']
                    away = available[n][0]['away']
                    #s = available[n][0] + ':' + available[n][1]
                    #s = ' '.join(TEAMCODES[away][1:]).strip() + ' at ' +\
                    #    ' '.join(TEAMCODES[home][1:]).strip() + ': ' +\
                    #    available[n][1].strftime('%l:%M %p')
                    s = available[n][1].strftime('%l:%M %p') + ': ' +\
                        ' '.join(TEAMCODES[away][1:]).strip() + ' at ' +\
                        ' '.join(TEAMCODES[home][1:]).strip()
                    if available[n][4] in ('F', 'CG'):
                        s+= ' (Archived)'
                    elif use_xml and available[n][6] == 'media_archive':
                        s+= ' (Archived)'

                padding = curses.COLS - (len(s) + 1)
                if n == current_cursor:
                    s += ' '*padding
            else:
                s = ' '*(curses.COLS-1)

            # Only draw the screen if there are any games
            if available:
                if n == current_cursor:
                    if available[n][4] == 'I' or str(available[n][4]) == 'In Progress':
                        #myscr.addstr(n+2,0,s, curses.A_REVERSE|curses.A_BOLD)
                        cursesflags = curses.A_REVERSE|curses.A_BOLD
                    else:
                        #myscr.addstr(n+2,0,s, curses.A_REVERSE)
                        cursesflags = curses.A_REVERSE
                    if 'topPlays' in CURRENT_SCREEN:
                        status_str = 'Press L to return to listings...'
                    else:
                        if use_xml:
                            status = str(available[n][4])
                            if available[n][0]['home'] in cfg['blackout'] or \
                               available[n][0]['away'] in cfg['blackout']:
                                if status in ('Warmup', 'Preview', 'In Progress', 'Pre-Game'):
                                    status = "Local Blackout"
                            status_str = 'Status: ' + status
                        else:
                            status_str = statusline.get(available[n][4],"Unknown Flag = "+available[n][4])
			if available[n][2] is None and available[n][3] is None:
                            status_str += ' (No media available)'
                        elif available[n][2] is None:
                            status_str += ' (No video available)'
                        elif available[n][3] is None:
                            status_str += ' (No audio available)'
                else:
                    if n < len(available):
                        if available[n][4] == 'I' or str(available[n][4]) == 'In Progress':
                            cursesflags = curses.A_BOLD
                        else:
                            cursesflags = 0
                    else:
                        pass
                if home in cfg['favorite'] or away in cfg['favorite']:
                    if cfg['use_color'] and 'listings' in CURRENT_SCREEN:
                        cursesflags = cursesflags|curses.color_pair(1)
                    else:
                        if 'listings' in CURRENT_SCREEN:
                            cursesflags = cursesflags|curses.A_UNDERLINE
                if n < len(available):
                    myscr.addstr(n+2, 0, s, cursesflags)
                else:
                    myscr.addstr(n+2, 0, s)
            else:
                if 'topPlays' in CURRENT_SCREEN:
                    status_str = 'Press L to return to listings...'
                elif 'bookmarks' in CURRENT_SCREEN:
                    status_str = 'Press B to refresh bookmarks...'
                else:
                    status_str = "No listings available for this day."

        # Add the speed toggle plus padding
        status_str_len = len(status_str) + len(speedtoggle.get(cfg['speed'])) +\
                            + len(coveragetoggle.get(cfg['coverage'])) + 2
        if cfg['debug']:
            status_str_len += len('[DEBUG]')
        padding = curses.COLS - status_str_len
        if cfg['debug']:
            debug_str = '[DEBUG]'
        else:
            debug_str = ''
        if str(mysched.year) == '2007' and cfg['speed'] == '800':
            speedstr = '[700K]'
        elif str(mysched.year) == '2009' and cfg['speed'] == '400':
            speedstr = '[600K]'
        else:
            speedstr = speedtoggle.get(cfg['speed'])
        coveragestr = coveragetoggle.get(cfg['coverage'])
        status_str += ' '*padding + debug_str +  coveragestr + speedstr

        # Print an indicator if more bookmarks than lines
        if 'bookmarks' in CURRENT_SCREEN:
            if more == True:
                myscr.addstr(curses.LINES-2,0,'--More--',curses.A_REVERSE)
            else:
                myscr.addstr(curses.LINES-2,0,'--End--',curses.A_REVERSE)

        # And write the status
        statuswin.addstr(0,0,status_str,curses.A_BOLD)

        # And refresh
        myscr.refresh() 
        titlewin.refresh()
        statuswin.refresh()       

        
        # And now we do input.
        inputs, outputs, excepts = select.select(inputlst, [], [])

        if sys.stdin in inputs:
            c = myscr.getch()
        elif LIRC:
            if irc_socket in inputs:
                c = irc_conn.next_code()

        if c in ('Highlights', ord('t')):
            if 'topPlays' in CURRENT_SCREEN:
                continue
            if 'bookmarks' in CURRENT_SCREEN:
                continue
            try:
                GAMEID = available[current_cursor][5]
            except IndexError:
                continue
            DISABLED_FEATURES = ['Jump', ord('j'), \
                                 'Left', curses.KEY_LEFT, \
                                 'Right', curses.KEY_RIGHT, \
                                 'Speed', ord('p'),
                                 'Condensed', ord('c'),
                                 'Audio', ord('a')]
            RESTORE_SPEED = cfg['speed']
            # Switch to 400 for highlights since all highlights are 400k
            # This is really just to toggle the indicator
            cfg['speed'] = '400'
            available = mysched.getTopPlays(GAMEID)
            CURRENT_SCREEN = 'topPlays'
            current_cursor = 0

        if c in ('Space', 32):
            if 'bookmarks' in CURRENT_SCREEN:
                if more == True:
                    current_cursor = 0
                    more_offset += more_end
                    more_beg = more_end
                    more_end = more_beg + curses.LINES-4
                    if more_end > len(bookmarks):
                        more = False
                        #more_end = len(bookmarks)
                    available = copy.deepcopy(bookmarks[more_beg:more_end])
                else:
                    continue
     
        if c in ('Delete', ord('x'), 8):
            if 'bookmarks' in CURRENT_SCREEN:
                confirm = prompter(statuswin,'Delete bookmark? [n] ')
                confirm_pat = re.compile(r'(y|yes)')
                if re.search(confirm_pat,confirm):
                    try:
                        bk = open(BOOKMARK_FILE)
                        bookmarks = pickle.load(bk)
                        bk.close()
                    except Exception,detail:
                        if cfg['debug']:
                            raise
                        statuswin.clear()
                        statuswin.addstr(0,0,detail,curses.A_BOLD)
                        statuswin.refresh()
                        time.sleep(1)
                    else:
                        del bookmarks[current_cursor + more_offset]
                        del available[current_cursor]
                        current_cursor = 0
                        bk = open(BOOKMARK_FILE,'w')
                        pickle.dump(bookmarks,bk)
                        bk.close()
                        statuswin.clear()
                        statuswin.addstr(0,0,'Bookmark deleted.',curses.A_BOLD)
                        statuswin.refresh()
                        time.sleep(1)


        if c in ('Bookmarks', ord('b')):
            if 'topPlays' in CURRENT_SCREEN:
                cfg['speed'] = str(RESTORE_SPEED)
            try:
                bk = open(BOOKMARK_FILE)
                bookmarks = pickle.load(bk)
                bk.close()
                if len(bookmarks) > curses.LINES-5:
                    more = True
                    more_offset = 0
                    more_beg = 0
                    more_end = curses.LINES-4
                    more_len = len(bookmarks)
                    available = copy.deepcopy(bookmarks[:curses.LINES-4])
                else:
                    more = False
                    more_offset = 0
                    available = copy.deepcopy(bookmarks)
            except Exception,detail:
                if cfg['debug']:
                   raise Exception,detail
                statuswin.clear()
                statuswin.addstr(0,0,'No bookmarks found.',curses.A_BOLD)
                statuswin.refresh()
                available = []
                time.sleep(1)
                continue
            DISABLED_FEATURES = ['Jump', ord('j'), \
                                 'Left', curses.KEY_LEFT, \
                                 'Right', curses.KEY_RIGHT, \
                                 'Speed', ord('p'),\
                                 'Refresh', ord('r'),\
                                 'Highlights', ord('t')]
            CURRENT_SCREEN = 'bookmarks'
            current_cursor = 0

        if c in ('Listings', ord('l'), ord('L') , 27):
            DISABLED_FEATURES = []
            CURRENT_SCREEN = 'listings'
            current_cursor = 0
            statuswin.clear()
            statuswin.addstr(0,0,'Refreshing listings...')
            statuswin.refresh()
            cfg['speed'] = str(RESTORE_SPEED)
            try:
                available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
            except (KeyError,MLBJsonError),detail:
                if cfg['debug']:
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                statuswin.addstr(0,0,status_str)
                statuswin.refresh()
                time.sleep(2)

        if c in DISABLED_FEATURES:
            status_str = 'That key is not supported in this screen'
            statuswin.addstr(0,0,status_str)
            statuswin.refresh()
            time.sleep(1)
            continue

        # coveragetoggle ('c' is taken by condensed games, 's' was
        # reserved for scores but I don't think I'll implement that.
        if c in ('Coverage', ord('s')):
            # there's got to be an easier way to do this
            temp = coveragetoggle.copy()
            del temp[cfg['coverage']]
            for coverage in temp:
                cfg['coverage'] = coverage
            del temp
            statuswin.clear()

        # speedtoggle
        if c in ('Speed', ord('p')):
            # there's got to be an easier way to do this
            temp = speedtoggle.copy()
            del temp[cfg['speed']]
            for speed in temp:
                cfg['speed'] = speed
            del temp
            statuswin.clear()
            statuswin.addstr(0,0,'Refreshing listings...')
            statuswin.refresh()
            try:
                available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
            except (KeyError,MLBJsonError),detail:
                if cfg['debug']:
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                statuswin.addstr(0,0,status_str)
                statuswin.refresh()
                time.sleep(2)

        # debug toggle
        if c in ('Debug', ord('d')):
            if cfg['debug']:
                cfg['debug'] = False
            else:
                cfg['debug'] = True
            #statuswin.clear()
            #statuswin.refresh()

        # down
        if c in ('Down', curses.KEY_DOWN):
            if current_cursor + 1 < len(available):
                current_cursor += 1            
        
        # up
        if c in ('Up', curses.KEY_UP):
            if current_cursor > 0:
                current_cursor -= 1

        # left (backward)
        if c in ('Left', curses.KEY_LEFT):
            # subtract a day:
            t = datetime.datetime(mysched.year, mysched.month, mysched.day)
            opening = datetime.datetime(2008,3,31)
            #if (t-opening).days > 0:
            dif = datetime.timedelta(1)
            t -= dif
            mysched = MLBSchedule((t.year, t.month, t.day))
            use_xml = mysched.use_xml
            statuswin.clear()
            statuswin.addstr(0,0,'Refreshing listings...')
            statuswin.refresh()
            try:
                available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
            except ( KeyError, MLBJsonError ),detail:
                if cfg['debug']:
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                statuswin.addstr(0,0,status_str)
                statuswin.refresh()
                time.sleep(2)
            current_cursor = 0

        # right (foward)
        if c in ('Right', curses.KEY_RIGHT):
            # add a day:
            t = datetime.datetime(mysched.year, mysched.month, mysched.day)
            now = datetime.datetime.now()
            # if (t-now).days < 2:
            dif = datetime.timedelta(1)
            t += dif
            mysched = MLBSchedule((t.year, t.month, t.day))
            use_xml = mysched.use_xml
            statuswin.clear()
            statuswin.addstr(0,0,'Refreshing listings...')
            statuswin.refresh()
            try:
                available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
            except (MLBJsonError, MLBUrlError, KeyError ),detail:
                if cfg['debug']:
                    raise Exception,detail
                available = []
                status_str = "There was a parser problem with the listings page"
                statuswin.addstr(0,0,status_str)
                statuswin.refresh()
                time.sleep(2)
            current_cursor = 0

        if c in ('Jump', ord('j')):

            jump_prompt = 'Date (m/d/yy)? '
            if datetime.datetime(mysched.year,mysched.month,mysched.day) <> \
                    datetime.datetime(today_year,today_month,today_day):
                jump_prompt += '(<enter> returns to today) '
            query = prompter(statuswin, jump_prompt)
            # Special case. If the response is blank, we jump back to
            # today.
            if query == '':
                statuswin.clear()
                status_str = "Jumping back to today"
                statuswin.addstr(0,0,status_str,curses.A_BOLD)
                statuswin.refresh()
                time.sleep(1)

                mysched = MLBSchedule((today_year, today_month, today_day))
                use_xml = mysched.use_xml
                statuswin.clear()
                statuswin.addstr(0,0,'Refreshing listings...')
                statuswin.refresh()
                try:
                    available = mysched.getListings(cfg['speed'],
                                                cfg['blackout'],
                                                cfg['audio_follow'])
                except (KeyError,MLBJsonError),detail:
                    if cfg['debug']:
                        raise Exception,detail
                    available = []
                    status_str = "There was a parser problem with the listings page"
                    statuswin.addstr(0,0,status_str)
                    statuswin.refresh()
                    time.sleep(2)
                current_cursor = 0
            else:
                pattern = re.compile(r'([0-9]{1,2})(/)([0-9]{1,2})(/)([0-9]{2})')
                parsed = re.match(pattern,query)
                if not parsed:
                    statuswin.clear()
                    error_str = "Date not in correct format"
                    statuswin.addstr(0,0,error_str,curses.A_BOLD)
                    statuswin.refresh()
                    time.sleep(2)
                else:
                    statuswin.clear()
                    statuswin.addstr(0,0,'Refreshing listings...')
                    statuswin.refresh()
                    split = parsed.groups()
                    prev_tuple = (mysched.year,mysched.month, mysched.day)
                    mymonth = int(split[0])
                    myday = int(split[2])
                    myyear = int('20' + split[4])
                                

                    newsched = MLBSchedule((myyear, mymonth, myday))
                    use_xml = newsched.use_xml
                    try:
                        available = newsched.getListings(cfg['speed'],
                                                         cfg['blackout'],
                                                         cfg['audio_follow'])
                        mysched = newsched
                        current_cursor = 0
                    except (KeyError,MLBUrlError):
                        if cfg['debug']:
                            raise
                        statuswin.clear()
                        error_str = "Could not fetch a schedule for that day."
                        statuswin.addstr(0,0,error_str,curses.A_BOLD)
                        statuswin.refresh()
                        time.sleep(1.5)
                    except MLBJsonError,detail:
                        if cfg['debug']:
                            raise Exception,detail
                        available = []
                        status_str = "There was a parser problem with the listings page"
                        statuswin.addstr(0,0,status_str)
                        statuswin.refresh()
                        time.sleep(2)


        if c in ('Zdebug', ord('z')):
            if 'topPlays' in CURRENT_SCREEN:
                gameid = available[current_cursor][4]
            else:
                gameid = available[current_cursor][5]
            titlewin.clear()
            titlewin.addstr(0,0,'LISTINGS DEBUG FOR ' + gameid)
            titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
            myscr.clear()
            myscr.addstr(2,0,'getListings() for current_cursor:')
            myscr.addstr(3,0,repr(available[current_cursor]))
            statuswin.clear()
            statuswin.addstr(0,0,'Press a key to continue...')
            myscr.refresh()
            titlewin.refresh()
            statuswin.refresh()
            myscr.getch()

        if c in ('Help', ord('h')):
            myscr.clear()
            titlewin.clear()
            myscr.addstr(0,0,VERSION)
            myscr.addstr(0,20,URL)
            n = 2
            #helpkeys = []
            #helpkeys = HELPFILE.keys()
            #helpkeys.sort()
         
            for heading in HELPFILE:
               myscr.addstr(n,0,heading[0],curses.A_UNDERLINE)
               n += 1
               for helpkeys in heading[1:]:
                   for k in helpkeys:
                       myscr.addstr(n,0,k)
                       myscr.addstr(n,20, ': ' + KEYBINDINGS[k])
                       n += 1
            statuswin.clear()
            statuswin.addstr(0,0,'Press a key to continue...')
            myscr.refresh()
            statuswin.refresh()
            myscr.getch()

        if c in ('Mark', ord('m')):
            title = prompter(statuswin, 'Bookmark name? ')
            if title == '':
                statuswin.clear()
                statuswin.addstr(0,0,'Can''t use null name.',curses.A_BOLD)
                statuswin.refresh()
                time.sleep(1)
            else:
                #raise Exception, repr(available[current_cursor])
                try:
                    bk = open(BOOKMARK_FILE)
                    bookmarks = pickle.load(bk)
                    bk.close()
                except IOError,detail:
                    nofile_pat = re.compile(r'No such file')
                    if re.search(nofile_pat,str(detail)):
                        bookmarks = []
                # Overload the title into 'home' field so we don't disrupt the
                # overall structure of the tuple
                try:
                    mark = copy.deepcopy(available[current_cursor])
                except IndexError:
                    continue
                if 'bookmarks' in CURRENT_SCREEN:
                    try:
                        i = bookmarks.index(mark)
                        bookmarks[i] = mark
                        mark[0]['home'] = title
                        available[current_cursor][0]['home'] = title
                    except IndexError:
                        #raise Exception,repr(mark)
                        continue
                    s = 'Bookmark edited: '
                else:
                    mark[0]['home'] = title
                    bookmarks.append(mark)
                    s= 'Bookmark added: '
                bk = open(BOOKMARK_FILE, 'w')
                pickle.dump(bookmarks,bk)
                bk.close()
                statuswin.clear()
                statuswin.addstr(0,0, s + title, curses.A_BOLD)
                statuswin.refresh()
                time.sleep(1)

        if c in ('Flash', ord('f')):
            flash_url = 'http://mlb.mlb.com/flash/mediaplayer/v4/RC11/MP4.jsp?calendar_event_id='
            flash_url += available[current_cursor][3]
            try:
                browser_cmd_str = cfg['flash_browser'].replace('%s',flash_url)
            except:
                browser_cmd_str = cfg['flash_browser'] + ' "' + flash_url + '"'
            browser_process = MLBprocess(browser_cmd_str,retries=0)
            browser_process.open()
            status_str = 'Started flash player using:\n' + str(browser_cmd_str)
            myscr.clear()
            myscr.addstr(0,0,status_str)
            myscr.refresh()
            time.sleep(2)
            browser_process.process.wait()

        if c in ('Enter', 10, 'Audio', ord('a'), 'Condensed', ord('c')):
            if c in ('Audio', ord('a')):
                audio = True
                player = cfg['audio_player']
            elif c in ('Condensed', ord('c')):
                audio = False
                if cfg['top_plays_player']:
                    player = cfg['top_plays_player']
                else:
                    player = cfg['video_player']
            else:
                audio = False
                player = cfg['video_player']
                # if top_plays_player defined, let's use it
                if 'topPlays' in CURRENT_SCREEN:
                    if cfg['top_plays_player']:
                        player = cfg['top_plays_player']
                    # hate doing this here, but for new highlights, 
                    # it doesn't need coverage or GameStream object
                    if use_xml:
                        u = str(available[current_cursor][2])
                        if '%s' in player:
                            cmd_str = player.replace('%s', u)
                        else:
                            cmd_str = player + " '" + u + "'"
                        myscr.clear()
                        if cfg['debug']:
                            myscr.addstr(0,0,'Url received:')
                            myscr.addstr(1,0,u)
                        else:
                            myscr.addstr(0,0,cmd_str)
                        myscr.refresh()
                        if cfg['debug']:
                            time.sleep(2)
                            continue
                        try:
                            play_process=subprocess.Popen(cmd_str,shell=True)
                            play_process.wait()
                            # I want to see mplayer errors before returning to 
                            # listings screen
                            if ['show_player_command']:
                                time.sleep(3)
                        except Exception,detail:
                            myscr.clear()
                            myscr.addstr(0,0,'Error occurred in player process:')
                            myscr.addstr(1,0,detail)
                            myscr.refresh()
                            time.sleep(2)
                        # end the xml handling of top plays
                        continue
                         
            try:
                # Turn off socket
                if LIRC:
                    irc_socket.close()
                    irc_conn.connected = False

                dbg = MLBLog(LOGFILE)
                home = available[current_cursor][0]['home']
                away = available[current_cursor][0]['away']
                defaultcoverage = available[current_cursor][0][cfg['coverage']]
                dbg.write('DEBUG>> home coverage = ' + home + ' away coverage = ' + away + '\n')
                dbg.write('DEBUG>> checking for audio_follow = ' + repr(cfg['audio_follow']) + '\n')
                dbg.write('DEBUG>> checking for video_follow = ' + repr(cfg['video_follow']) + '\n')
                dbg.flush()
                
                use_nexdef = cfg['use_nexdef']

                if audio:
                    stream = available[current_cursor][3]

                    if use_xml:
                        if away in cfg['audio_follow']:
                            coverage = TEAMCODES[away][0]
                        elif home in cfg['video_follow']:
                            coverage = TEAMCODES[home][0]
                        else:
                            coverage = TEAMCODES[defaultcoverage][0]

                        g = GameStream(stream, cfg['user'], cfg['pass'],
                                   cfg['debug'], streamtype='audio',
                                   use_soap=True, use_nexdef=False,
                                   coverage=coverage)
                    else:
                        g = GameStream(stream, cfg['user'], cfg['pass'],
                                   cfg['debug'], streamtype='audio')

                else:
                    if c in ('Condensed', ord('c')):
                        if available[current_cursor][4] in ('CG'):
                            gameid = available[current_cursor][5]
                            stream = mysched.getCondensedVideo(gameid)
                        else:
                            statuswin.clear()
                            statuswin.addstr(0,0,'Condensed Game Not Yet Available')
                            myscr.refresh()
                            statuswin.refresh()
                            time.sleep(2)
                            continue
                    else:
                        stream = available[current_cursor][2]
                    if mysched.use_xml:
                        if away in cfg['video_follow']:
                            coverage = TEAMCODES[away][0]
                        elif home in cfg['video_follow']:
                            coverage = TEAMCODES[home][0]
                        else:
                            coverage = TEAMCODES[defaultcoverage][0]

                        if str(available[current_cursor][4]) in ('In Progress', 'Delayed'):
                            if cfg['live_from_start']:
                                start_time=0
                            else:
                                start_time=None
                        else:
                            start_time=0


                        g = GameStream(stream, cfg['user'], cfg['pass'],
                                   cfg['debug'],use_soap=True,speed=cfg['speed'],
                                   coverage=coverage,use_nexdef=use_nexdef,
                                   max_bps=cfg['max_bps'],start_time=start_time)
                    else:
                        g = GameStream(stream, cfg['user'], cfg['pass'],
                                   cfg['debug'])
                
                # print a "Trying..." message so we don't look frozen
                statuswin.clear()
                statuswin.addstr(0,0,'Fetching URL for game stream...')
                statuswin.refresh()
                myscr.refresh()

                if cfg['debug']:
                    statuswin.clear()
                    statuswin.addstr(0,0,'Debug set, fetching URL but not playing...')
                    statuswin.refresh()
                    myscr.refresh()
                try:
                    if g.use_soap:
                        u = g.soapurl()
                    else:
                        u = g.url()
                except:
                    # Debugging should make errors fatal in case there is a
                    # logic, coding, or other uncaught error being hidden by
                    # the following exception handling code
                    if cfg['debug']:
                        raise
                    myscr.clear()
                    titlewin.clear()
                    myscr.addstr(0,0,'An error occurred in locating the game stream:')
                    myscr.addstr(2,0,g.error_str)
                    myscr.refresh()
                    time.sleep(3)
                    continue
                call_letters = g.call_letters

                # removing over 200 lines of else to the except above (892-1136)
                if cfg['debug']:
                    myscr.clear()
                    titlewin.clear()
                    myscr.addstr(0,0,'Url received:')
                    myscr.addstr(1,0,u)
                    myscr.refresh()
                    time.sleep(3)
                # I'd rather leave an error on the screen but you'll need
                # to write a lirc handler for getch()
                #myscr.getch()
                if cfg['debug']:
                    continue
                try:
                    if '%s' in player:
                        if use_nexdef:
                            cmd_str = player.replace('%s', '"' + u + '"')
                        else:
                            cmd_str = player.replace('%s', '-')
                            cmd_str = u + ' | ' + player
                    else:
                        if use_nexdef:
                            cmd_str = player + ' "' + u + '" '
                        else:
                            cmd_str = u + ' | ' + player + ' - '
                    if '%f' in player:
                        gameid = available[current_cursor][5].replace('/','-')
                        if audio:
                            suf = '.mp3'
                        else:
                            suf = '.mp4'
                        cmd_str = cmd_str.replace('%f', "'" + gameid + '-' + call_letters + suf + "'")
                    #if not use_nexdef:
                    #    g.rec_process.open()
                    if cfg['show_player_command']:
                        myscr.clear()
                        titlewin.clear()
                        myscr.addstr(0,0,cmd_str)
                        ''' NOT NEEDED
                        if not use_nexdef:
                            myscr.addstr(curses.LINES-2,0,"Please wait for stream to buffer...")
                            myscr.refresh()
                            time.sleep(30)
                        NOT NEEDED '''
                        myscr.refresh()
                        time.sleep(3)
		    else:
                        if not audio:
                            statuswin.clear()
                            statuswin.addstr(0,0,"Buffering stream")
                            statuswin.refresh()
                            if use_nexdef:
                                time.sleep(.5)
                            else:
                                time.sleep(30)
                        else:
                            time.sleep(10)

                    play_process=subprocess.Popen(cmd_str,shell=True)
                    while play_process.poll() is None:
                        if not use_xml:
                            continue
                        try:
                            time.sleep(10)
                            g.control(action='ping')
                            if not use_nexdef:
                                continue
                            myscr.clear()
                            status_str =  'STREAM: ' + g.current_encoding[0]
                            status_str += '\nBPS   : ' + g.current_encoding[1]
                            status_str += '\nMS    : ' + g.current_encoding[2]
                            myscr.addstr(curses.LINES-5,0,status_str)
                            myscr.refresh()
                        except:
                            pass
                    play_process.wait()
                    '''try:
                        if not use_nexdef:
                            g.rec_process.close(signal=signal.SIGINT)
                    except:
                        pass'''
                    # I want to see mplayer errors before returning to 
                    # listings screen
                    if ['show_player_command']:
                        time.sleep(3)
                except:
                    raise
                    '''try:
                        if not use_nexdef:
                            g.rec_process.close(signal=signal.SIGINT)
                    except:
                        pass'''
                    myscr.clear()
                    titlewin.clear()
                    ERROR_STRING = "There was an error in the player process."
                    myscr.addstr(0,0,ERROR_STRING)
                    myscr.refresh()
                    time.sleep(3)

                # Turn the ir_program back on                
                if LIRC:
                    irc_conn = LircConnection()
                    irc_conn.connect()
    	            irc_conn.getconfig()
                    irc_socket=irc_conn.conn
                    inputlst = [sys.stdin, irc_socket]
            except IndexError:
                pass

        if c in ('Refresh', ord('r')):
            # refresh
            statuswin.clear()
            statuswin.addstr(0,0,'Refreshing listings...')
            statuswin.refresh()
            try:
                available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
            except ( KeyError, MLBJsonError ),detail:
                if cfg['debug']:
                    raise Exception,detail
                status_str = "There was a parser problem with the listings page"
                statuswin.addstr(0,0,status_str)
                statuswin.refresh()
                time.sleep(2)
                available = []
            if 'topPlays' in CURRENT_SCREEN:
                available = mysched.getTopPlays(GAMEID)

        if c in ('Exit', ord('q')):
            curses.nocbreak()
            myscr.keypad(0)
            curses.echo()
            curses.endwin()
            break


if __name__ == "__main__":

    myconfdir = os.path.join(os.environ['HOME'],AUTHDIR)
    myconf =  os.path.join(myconfdir,AUTHFILE)
    #myconf = os.path.join(os.environ['HOME'], AUTHDIR, AUTHFILE)
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
                  'time_offset': '',
                  'max_bps': 800000,
                  'live_from_start': 0,
                  'use_nexdef': 1,
                  'flash_browser': DEFAULT_FLASH_BROWSER}

    # Auto-install of default configuration file
    try:
        os.lstat(myconf)
    except:
        try:
            os.lstat(myconfdir)
        except:
            dir=myconfdir
        else:
            dir=None
        doinstall(myconf,mydefaults,dir)

    mycfg = MLBConfig(mydefaults)
    mycfg.loads(myconf)

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

    curses.wrapper(mainloop, mycfg.data)
