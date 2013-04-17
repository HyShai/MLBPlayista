#!/usr/bin/env python

import curses
import curses.textpad
import time
#from listwin import ListWin
from mlbConstants import *

class MLBListWin:

    def __init__(self,myscr,mycfg,data):
        # self.data is everything
        self.data = data
        # self.records is only what's "visible"
        self.records = self.data[0:curses.LINES-4]
        self.mycfg = mycfg
        self.myscr = myscr
        self.current_cursor = 0
        self.record_cursor = 0
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)

    def prompter(self,win,prompt):
        win.clear()
        win.addstr(0,0,prompt,curses.A_BOLD)
        win.refresh()

        responsewin = win.derwin(0, len(prompt))
        responsebox = curses.textpad.Textbox(responsewin)
        responsebox.edit()
        output = responsebox.gather()
        return output

    def Splash(self):
        lines = ('mlbviewer', VERSION, URL)
        for i in xrange(len(lines)):
            self.myscr.addstr(curses.LINES/2+i, (curses.COLS-len(lines[i]))/2, lines[i])
        self.myscr.refresh()

    def Up(self):
        # old basic behavior
        #if self.current_cursor > 0:
        #    self.current_cursor -= 1
        
        # Are we at the top of the window 
        # Do we have more records below record cursor?
        # Move up a window in the records.
        if self.current_cursor -1 < 0 and self.record_cursor - 1 > 0:
            self.current_cursor = curses.LINES-4-1
            if self.record_cursor - curses.LINES -4 < 0:
                self.record_cursor = 0
            else:
                self.record_cursor -= curses.LINES-4
            self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-4]
            #raise Exception,repr(self.records)
        # Elif we are not yet at top of window
        elif self.current_cursor > 0:
            self.current_cursor -= 1
        # Silent else do nothing when at top of window and top of records
        # no negative scrolls

    def Down(self):
        # old behavior
        #if self.current_cursor + 1 < len(self.data):
        #    self.current_cursor += 1
        
        # Are we at bottom of window and
        # still have more records?
        # Move down a window.
        if self.current_cursor + 1 >= len(self.records) and\
           self.record_cursor + self.current_cursor + 1 < len(self.data):
           self.record_cursor += self.current_cursor + 1
           self.current_cursor = 0
           self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-4]
        # Elif not at bottom of window
        elif self.current_cursor + 1 < self.records  and\
            self.current_cursor + 1 < curses.LINES-4:
            if self.current_cursor + 1 + self.record_cursor < len(self.data):
                self.current_cursor += 1
        # Silent else do nothing at bottom of window and bottom of records


    def PgUp(self):
        self.current_cursor = 0
        self.record_cursor = 0
        self.records = self.data[0:curses.LINES-4]

    def PgDown(self):
        # assuming we scrolled down, we'll have len(data) % ( curses.LINES-4 )
        # records left to display
        remaining=len(self.data) % ( curses.LINES-4 )
        self.records = self.data[-remaining:]
        self.record_cursor = len(self.data)- remaining
        self.current_cursor = len(self.records) - 1

    def Refresh(self):
        if len(self.data) == 0:
            #status_str = "There was a parser problem with the listings page"
            #self.statuswin.addstr(0,0,status_str)
            self.titlewin.refresh()
            self.myscr.refresh()
            self.statuswin.refresh()
            #time.sleep(2)
            return

        self.myscr.clear()
        for n in range(curses.LINES-4):
            if n < len(self.records):
                home = str(self.records[n][0]['home'])
                away = str(self.records[n][0]['away'])
                s = self.records[n][1].strftime('%l:%M %p') + ': ' +\
                    ' '.join(TEAMCODES[away][1:]).strip() + ' at ' +\
                    ' '.join(TEAMCODES[home][1:]).strip()
                if self.records[n][7] == 'media_archive':
                    s += ' (Archived)'

                padding = curses.COLS - (len(s) + 1)
                if n == self.current_cursor:
                    s += ' '*padding
            else:
                s = ' '*(curses.COLS-1)

            if n == self.current_cursor:
                if self.records[n][5] == 'I':
                    # highlight and bold if in progress, else just highlight
                    cursesflags = curses.A_REVERSE|curses.A_BOLD
                else:
                    cursesflags = curses.A_REVERSE
            else:
                if n < len(self.records):
                    if self.records[n][5] == 'I':
                        cursesflags = curses.A_BOLD
                    else:
                        cursesflags = 0

            if n < len(self.records):
                if home in self.mycfg.get('favorite') or\
                   away in self.mycfg.get('favorite'):
                    if self.mycfg.get('use_color'):
                        cursesflags = cursesflags |curses.color_pair(1)
                    else:
                        cursesflags = cursesflags | curses.A_UNDERLINE
                self.myscr.addstr(n+2, 0, s, cursesflags)
            else:
                self.myscr.addstr(n+2, 0, s)

        self.myscr.refresh()

    def titleRefresh(self,mysched):
        titlestr = "AVAILABLE GAMES FOR " +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year) + ' ' +\
                '(Use arrow keys to change days)'

        padding = curses.COLS - (len(titlestr) + 6)
        titlestr += ' '*padding
        pos = curses.COLS - 6
        self.titlewin.addstr(0,0,titlestr)
        self.titlewin.addstr(0,pos,'H', curses.A_BOLD)
        self.titlewin.addstr(0,pos+1, 'elp')
        self.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
        self.titlewin.refresh()

    def statusRefresh(self):
        n = self.current_cursor
        if len(self.records) == 0:
            status_str = "No listings available for this day."
            self.statuswin.clear()
            self.statuswin.addstr(0,0,status_str)
            self.statuswin.refresh()
            return

        try:
            status_str = STATUSLINE.get(self.records[n][5],
                                    "Unknown Flag = "+self.records[n][5])
        except:
            raise Exception,"current_cursor:%s, len:%s"%(n,str(len(self.records)))
        if len(self.records[n][2]) + len(self.records[n][3]) == 0:
            status_str += ' (No media)'
        elif len(self.records[n][2]) == 0:
            status_str += ' (No video)'
        elif len(self.records[n][3]) == 0:
            status_str += ' (No audio)'

        speedstr = SPEEDTOGGLE.get(self.mycfg.get('speed'))
        hdstr = SSTOGGLE.get(self.mycfg.get('adaptive_stream'))
        coveragestr = COVERAGETOGGLE.get(self.mycfg.get('coverage'))
        status_str_len = len(status_str) +\
                            + len(speedstr) + len(hdstr) + len(coveragestr) + 2
        if self.mycfg.get('debug'):
            status_str_len += len('[DEBUG]')
        padding = curses.COLS - status_str_len
        # shrink the status string to fit if it is too many chars wide for
        # screen
        if padding < 0:
            status_str=status_str[:padding]
        if self.mycfg.get('debug'):
            debug_str = '[DEBUG]'
        else:
            debug_str = ''
        if self.mycfg.get('use_nexdef'):
            speedstr = '[NEXDF]'
        else:
            hdstr = SSTOGGLE.get(False)

        status_str += ' '*padding + debug_str +  coveragestr + speedstr + hdstr
        # And write the status
        try:
            self.statuswin.addstr(0,0,status_str,curses.A_BOLD)
        except:
            rows = curses.LINES
            cols = curses.COLS
            slen = len(status_str)
            raise Exception,'(' + str(slen) + '/' + str(cols) + ',' + str(n) + '/' + str(rows) + ') ' + status_str
        self.statuswin.refresh()

    def helpScreen(self):
        self.myscr.clear()
        self.titlewin.clear()
        self.myscr.addstr(0,0,VERSION)
        self.myscr.addstr(0,20,URL)
        n = 1

        # TODO: Implement a HelpWin(MLBListWin) class to take advantage of 
        # scrolling
        for heading in HELPFILE:
           if n < curses.LINES-4:
               self.myscr.addstr(n,0,heading[0],curses.A_UNDERLINE)
           else:
               continue
           n += 1
           for helpkeys in heading[1:]:
               for k in helpkeys:
                   if n < curses.LINES-4:
                       self.myscr.addstr(n,0,k)
                       self.myscr.addstr(n,20, ': ' + KEYBINDINGS[k])
                   else:
                       continue
                   n += 1
        self.statuswin.clear()
        self.statuswin.addstr(0,0,'Press a key to continue...')
        self.myscr.refresh()
        self.statuswin.refresh()
        self.myscr.getch()

    def errorScreen(self,errMsg):
        if self.mycfg.get('debug'):
            raise
        self.myscr.clear()
        self.myscr.addstr(0,0,errMsg)
        self.myscr.addstr(2,0,'See %s for more details.' % LOGFILE)
        self.myscr.refresh()
        self.statuswin.clear()
        self.statuswin.addstr(0,0,'Press a key to continue...')
        self.statuswin.refresh()
        self.myscr.getch()

    def statusWrite(self, statusMsg, wait=0):
        self.statuswin.clear()
        self.statuswin.addstr(0,0, str(statusMsg)[:curses.COLS-1],curses.A_BOLD)
        self.statuswin.refresh()
        if wait < 0:
            self.myscr.getch()
        elif wait > 0:
            time.sleep(wait)
