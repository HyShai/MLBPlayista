#!/usr/bin/env python

from MLBviewer import MLBSchedule
from MLBviewer import GameStream
from MLBviewer import LircConnection
import os
import sys
import re
import curses
import select

AUTHFILE = '.mlbtv'
DEFAULT_PLAYER = 'xterm -e mplayer -cache 2048 -quiet -fs'
DEFAULT_SPEED = 400 


def mainloop(myscr,cfg):

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


    curses.use_default_colors()

    myscr = curses.initscr()

    current_cursor = 0

    mysched = MLBSchedule()
    available = mysched.getListings(cfg['speed'],cfg['blackout'])

    statusline = {
        "I" : "Status: In Progress",
        "W" : "Status: Not Yet Available",
        "F" : "Status: Final",
        "P" : "Status: Not Yet Available",
        "PO": "Status: Postponed",
        "GO": "Status: Game Over - stream not yet avaialble",
        "LB": "Status: Local Blackout"}

    while True:
        myscr.clear()
        datestr= "AVAILABLE GAMES FOR " +\
            str(mysched.month) + '/' +\
            str(mysched.day) + '/' +\
            str(mysched.year) + ' ' +\
            '(Use arrow keys to change days)'

        # Draw the date
        myscr.addstr(0,0,datestr)
        # Draw a line
        myscr.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
        
        for n in range(curses.LINES-3):
            if n < len(available):
                s = available[n][0] + ':' + available[n][1]
                if available[n][3] == 'F':
                    s+= ' (Archived)'
                padding = curses.COLS - (len(s) + 1)
                s += ' '*padding
            else:
                s = ' '*(curses.COLS-1)

            # Only draw the screen if there are any games
            if available:
                if n == current_cursor:
                    myscr.addstr(n+2,0,s, curses.A_REVERSE)
                    myscr.addstr(curses.LINES-1,0,statusline.get(available[n][3],"Unknown Flag = "+available[n][3]))
                else:
                    myscr.addstr(n+2, 0, s)

        myscr.refresh()

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
            if (t-opening).days > 0:
                dif = datetime.timedelta(1)
                t -= dif
            mysched = MLBSchedule((t.year, t.month, t.day))
            available = getListings(mysched,cfg['speed'],cfg['blackout'])
            current_cursor = 0

        # right (foward)
        if c in ('Right', curses.KEY_RIGHT):
            # subtract a day:
            t = datetime.datetime(mysched.year, mysched.month, mysched.day)
            now = datetime.datetime.now()
            if (now-t).days > 0:
                dif = datetime.timedelta(1)
                t += dif
            mysched = MLBSchedule((t.year, t.month, t.day))
            available = getListings(mysched,cfg['speed'],cfg['blackout'])
            current_cursor = 0

        if c in ('Enter', 10):
            try:
                # Turn off socket
                if LIRC:
                    irc_socket.close()
                    irc_conn.connected = False

                gameid = available[current_cursor][2]
                g = GameStream(gameid, cfg['user'], cfg['pass'])
                u = g.urlDebug()
                if '%s' in myplayer:
                    cmd_str = myplayer.replace('%s', '"' + u + '"')
                else:
                    cmd_str = myplayer + ' "' + u + '" '
                play_process=subprocess.Popen(cmd_str,shell=True)
                play_process.wait()
                # And try this now: logging out. Hopefully, this will
                # prevent the concurrent login error.
                g.logout()

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
            available=getListings(mysched,cfg['speed'],cfg['blackout'])

        if c in ('Exit', ord('q')):
            break


if __name__ == "__main__":
    conf = os.path.join(os.environ['HOME'], AUTHFILE)
    fp = open(conf)

    
    # Start with the default settings in place
    datadct = {'speed': DEFAULT_SPEED,
               'video_player': DEFAULT_PLAYER,
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
    
    curses.wrapper(mainloop,datadct)


