#!/usr/bin/env python

from MLBviewer import MLBSchedule
from MLBviewer import GameStream
from MLBviewer import LircConnection
from MLBviewer import MLBConfig
from MLBviewer import MLBUrlError
from MLBviewer import VERSION, URL, AUTHDIR, AUTHFILE
import os
import sys
import re
import curses
import select
import datetime
import subprocess
import time

# # Set this to True if you want to see all the html pages in the logfile
# DEBUG = True
# #DEBUG = None

# AUTHDIR = '.mlb'
# AUTHFILE = 'config'
DEFAULT_V_PLAYER = 'xterm -e mplayer -cache 2048 -quiet'
DEFAULT_A_PLAYER = 'xterm -e mplayer -cache 64 -quiet -playlist'
DEFAULT_SPEED = 400 

#VERSION= 'mlbviewer 0.1alpha5-svn  http://sourceforge.net/projects/mlbviewer'

KEYBINDINGS = { 'Up/Down'    : 'Highlight games in the current view',
                'Enter'      : 'Play video of highlighted game',
                'Left/Right' : 'Navigate one day forward or back',
                'j'          : 'Jump to a date',
                'r'          : 'Refresh listings',
                'q'          : 'Quit mlbviewer',
                'h'          : 'Display version and keybindings',
                'a'          : 'Play Gameday audio of highlighted game'
              }

def prompter(win,prompt):
    win.clear()
    win.addstr(0,0,prompt,curses.A_BOLD)
    win.refresh()

    curses.echo()
    output = win.getstr(0,len(prompt))
    curses.noecho()

    return output

def mainloop(myscr,cfg):

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


    if hasattr(curses, 'use_default_colors'):
        try:
            curses.use_default_colors()
        except curses.error:
            pass

    myscr = curses.initscr()

    # This will be used for statuslines
    statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)


    current_cursor = 0
    
    # Print a simple splash for now just so we don't show dead screen while
    # we're fetching the listings
    lines = ('mlbviewer', VERSION, URL)
    for i in xrange(len(lines)):
        myscr.addstr(curses.LINES/2+i, (curses.COLS-len(lines[i]))/2, lines[i])
    statuswin.addstr(0,0,'Please wait for listings to load...')
    statuswin.refresh()
    myscr.refresh()

    mysched = MLBSchedule(time_shift=cfg['time_offset'])
    # We'll make a note of the date, to return to it later.
    today_year = mysched.year
    today_month = mysched.month
    today_day = mysched.day

    available = mysched.getListings(cfg['speed'],cfg['blackout'],cfg['audio_follow'])

    statusline = {
        "I" : "Status: In Progress",
        "W" : "Status: Not Yet Available",
        "F" : "Status: Final",
        "P" : "Status: Not Yet Available",
        "IP": "Status: Pregame",
        "PO": "Status: Postponed",
        "GO": "Status: Game Over - stream not yet available",
        "LB": "Status: Local Blackout"}

    while True:
        myscr.clear()
        statuswin.clear()

        datestr= "AVAILABLE GAMES FOR " +\
            str(mysched.month) + '/' +\
            str(mysched.day) + '/' +\
            str(mysched.year) + ' ' +\
            '(Use arrow keys to change days)'

        # Draw the date
        myscr.addstr(0,0,datestr)
        # Draw a line
        myscr.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)

        for n in range(curses.LINES-4):
            if n < len(available):
                s = available[n][0] + ':' + available[n][1]
                if available[n][4] == 'F':
                    s+= ' (Archived)'
                padding = curses.COLS - (len(s) + 1)
                s += ' '*padding
            else:
                s = ' '*(curses.COLS-1)

            # Only draw the screen if there are any games
            if available:
                if n == current_cursor:
                    if available[n][4] == 'I':
                        myscr.addstr(n+2,0,s, curses.A_REVERSE|curses.A_BOLD)
                    else:
                        myscr.addstr(n+2,0,s, curses.A_REVERSE)
                    status_str = statusline.get(available[n][4],"Unknown Flag = "+available[n][4])
                else:
                    if n < len(available) and available[n][4] == 'I':
                        myscr.addstr(n+2, 0, s, curses.A_BOLD)
                    else:
                        myscr.addstr(n+2, 0, s)
            else:
                status_str = "No listings available for this day."
        # And write the status
        statuswin.addstr(0,0,status_str,curses.A_BOLD)

        # And refresh
        myscr.refresh() 
        statuswin.refresh()       

        
        # And now we do input.
        inputs, outputs, excepts = select.select(inputlst, [], [])

        if sys.stdin in inputs:
            c = myscr.getch()
        elif LIRC:
            if irc_socket in inputs:
                c = irc_conn.next_code()

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
            available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
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
            available = mysched.getListings(cfg['speed'],
                                            cfg['blackout'],
                                            cfg['audio_follow'])
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
                available = mysched.getListings(cfg['speed'],
                                                cfg['blackout'],
                                                cfg['audio_follow'])
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
                    split = parsed.groups()
                    prev_tuple = (mysched.year,mysched.month, mysched.day)
                    mymonth = int(split[0])
                    myday = int(split[2])
                    myyear = int('20' + split[4])
                                

                    newsched = MLBSchedule((myyear, mymonth, myday))
                    try:
                        available = newsched.getListings(cfg['speed'],
                                                         cfg['blackout'],
                                                         cfg['audio_follow'])
                        mysched = newsched
                        current_cursor = 0
                    except MLBUrlError:
                        statuswin.clear()
                        error_str = "Could not fetch a schedule for that day."
                        statuswin.addstr(0,0,error_str,curses.A_BOLD)
                        statuswin.refresh()
                        time.sleep(1.5)


        if c in ('Help', ord('h')):
            myscr.clear()
            myscr.addstr(0,0,VERSION)
            n = 2
            for elem in KEYBINDINGS:
               myscr.addstr(n,0,elem)
               myscr.addstr(n,20,KEYBINDINGS[elem])
               n += 1
            myscr.addstr(curses.LINES-1,0,'Press a key to continue...')
            myscr.getch()




        if c in ('Enter', 10):
            try:
                # Turn off socket
                if LIRC:
                    irc_socket.close()
                    irc_conn.connected = False

                gameid = available[current_cursor][2]
                g = GameStream(gameid, cfg['user'], cfg['pass'], cfg['debug'])
                
                # print a "Trying..." message so we don't look frozen
                myscr.addstr(curses.LINES-1,0,'Fetching URL for game stream...')
                myscr.refresh()

                if cfg['debug']:
                    myscr.addstr(curses.LINES-1,0,'Debug set, fetching URL but not playing...')
                    myscr.refresh()
                    u = g.url()
                    myscr.clear()
                    myscr.addstr(0,0,'Url received:')
                    myscr.addstr(1,0,u)
                    myscr.refresh()
                    time.sleep(3)
                    # I'd rather leave an error on the screen but you'll need
                    # to write a lirc handler for getch()
                    #myscr.getch()
                else:
                    try:
                        u = g.url()
                    except:
                        myscr.clear()
                        myscr.addstr(0,0,'An error occurred in locating the game stream:')
                        myscr.addstr(2,0,g.error_str)
                        myscr.refresh()
                        time.sleep(3)
                    else:
                        try:
                            if '%s' in cfg['video_player']:
                                cmd_str = cfg['video_player'].replace('%s', '"' + u + '"')
                            else:
                                cmd_str = cfg['video_player'] + ' "' + u + '" '
                            if cfg['show_player_command']:
                                myscr.clear()
                                myscr.addstr(0,0,cmd_str)
                                myscr.refresh()
                                time.sleep(3)
			    else:
                                statuswin.clear()
                                statuswin.addstr(0,0,"Buffering stream")
                                statuswin.refresh()
                                time.sleep(.5)

                            play_process=subprocess.Popen(cmd_str,shell=True)
                            play_process.wait()
                        except:
                            myscr.clear()
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


        if c in ('Audio', ord('a')):
            try:
                # Turn off socket
                if LIRC:
                    irc_socket.close()
                    irc_conn.connected = False

                gameid = available[current_cursor][3]
                g = GameStream(gameid, cfg['user'], cfg['pass'], cfg['debug'],
                               streamtype='audio')
                
                # print a "Trying..." message so we don't look frozen
                myscr.addstr(curses.LINES-1,0,'Fetching URL for game stream...')
                myscr.refresh()

                if cfg['debug']:
                    myscr.addstr(curses.LINES-1,0,'Debug set, fetching URL but not playing...')
                    myscr.refresh()
                    u = g.url()
                    myscr.clear()
                    myscr.addstr(0,0,'Url received:')
                    myscr.addstr(1,0,u)
                    myscr.refresh()
                    time.sleep(3)
                    # I'd rather leave an error on the screen but you'll need
                    # to write a lirc handler for getch()
                    #myscr.getch()
                else:
                    try:
                        u = g.url()
                    except:
                        myscr.clear()
                        myscr.addstr(0,0,'An error occurred in locating the game stream:')
                        myscr.addstr(2,0,g.error_str)
                        myscr.refresh()
                        time.sleep(3)
                    else:
                        try:
                            if '%s' in cfg['audio_player']:
                                cmd_str = cfg['audio_player'].replace('%s', '"' + u + '"')
                            else:
                                cmd_str = cfg['audio_player'] + ' "' + u + '" '
                            if cfg['show_player_command']:
                                myscr.clear()
                                myscr.addstr(0,0,cmd_str)
                                myscr.refresh()
                                time.sleep(3)
                            play_process=subprocess.Popen(cmd_str,shell=True)
                            play_process.wait()
                        except:
                            myscr.clear()
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
            available=mysched.getListings(cfg['speed'],
                                          cfg['blackout'],
                                          cfg['audio_follow'])

        if c in ('Exit', ord('q')):
            curses.nocbreak()
            myscr.keypad(0)
            curses.echo()
            curses.endwin()
            break


if __name__ == "__main__":

    myconf = os.path.join(os.environ['HOME'], AUTHDIR, AUTHFILE)
    mydefaults = {'speed': DEFAULT_SPEED,
                  'video_player': DEFAULT_V_PLAYER,
                  'audio_player': DEFAULT_A_PLAYER,
                  'audio_follow': [],
                  'blackout': [],
                  'show_player_command': 0,
                  'debug': 0,
                  'x_display': '',
                  'time_offset': ''}

    mycfg = MLBConfig(mydefaults)
    mycfg.loads(myconf)
    
    curses.wrapper(mainloop, mycfg.data)
