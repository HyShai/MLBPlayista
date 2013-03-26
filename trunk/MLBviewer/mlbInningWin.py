#!/usr/bin/env python

import curses
import curses.textpad
import re
import time
from mlbListWin import MLBListWin
from mlbConstants import *

class MLBInningWin(MLBListWin):

    def __init__(self,myscr,mycfg,data,mysched):
        self.data = data
        self.mycfg = mycfg
        self.myscr = myscr
        self.mysched = mysched
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)
        self.innings = {}
        self.logfile = LOGFILE.replace('log', 'innwin.log')
        self.log = open(self.logfile, "w")

    def Refresh(self):
        streamtype = 'video'
        if len(self.data) == 0:
            self.statuswin.addstr(0,0,'No innings data available for this game')
            self.statuswin.refresh()
            return

        self.statuswin.clear()
        self.statuswin.addstr(0,0,'Fetching innings index...')
        self.statuswin.refresh()
        self.myscr.clear()
        try:
            try:
                this_event = self.data[2][0][3]
            except:
                raise Exception,'Innings list is not availale for this game.'
            myinnings = self.mysched.parseInningsXml(this_event,
                                                     self.mycfg.get('use_nexdef'))
        except Exception,detail:
            self.myscr.clear()
            self.myscr.addstr(2,0,'Could not parse innings: ')
            self.myscr.addstr(3,0,str(detail))
            self.myscr.refresh()
            #time.sleep(3)
            return
  
        for inning in range(len(myinnings)):
            # top half innings will be 1 - 10, 10 being extra innings
            # bottom half innings will be top half plus 10
            if myinnings[inning][1] == 'false':
                self.innings[int(myinnings[inning][0]) + 10] = myinnings[inning][2]
            else:
                self.innings[int(myinnings[inning][0])] = myinnings[inning][2]

        # print header first:
        self.myscr.clear()

        # skip a line
        self.myscr.addstr(2,0,'Enter T or B for top or bottom plus inning to jump to.')
        self.myscr.addstr(3,0,'Example: T6 to jump to Top of 6th inning.')
        self.myscr.addstr(4,0,'Enter E for Extra Innings.')
        self.myscr.addstr(5,0,'Press <Enter> to return to listings.')
        # skip a line, print top half innings
        inn_str = ' '*5 + '[1] [2] [3] [4] [5] [6] [7] [8] [9] [Extra]'
        latest = 0
        for city in ( 'away', 'home' ):
            team = self.data[0][city]
            if len(team) < 3:
                pad = 1
            else:
                pad = 0
            if city == 'away':
                top_str = ' '*pad + team + ' '
            else:
                bot_str = ' '*pad + team + ' '
        for i in range(21):
            if i == 0:
                continue
            if self.innings.has_key(i):
                # no spoilers for home victories
                if i == 19:
                    bot_str += ' [?]'
                elif i > 10:
                    bot_str += ' [+]'
                    if (i - 10) >= latest:
                        latest = i
                else:
                    top_str += ' [+]'
                    latest = i
            else:
                # no spoilers for home victories
                if i == 19:
                    bot_str += ' [?]'
                elif i > 10:
                    bot_str += ' [-]'
                else:
                    top_str += ' [-]'
        if self.mycfg.get('show_inning_frames'):
            self.myscr.addstr(7,0,'[+] = Half inning is available')
            self.myscr.addstr(8,0,'[-] = Half inning is not available')
            self.myscr.addstr(9,0,'[?] = Bottom of 9th availability is never shown to avoid spoilers')
            self.myscr.addstr(12,0,inn_str)
            self.myscr.addstr(14,0,top_str)
            self.myscr.addstr(16,0,bot_str)
        latest_str = 'Last available half inning is: '
        if latest == 0:
            latest_str += 'None'
        elif self.data[5] in ('F', 'CG', 'GO'):
            # remove spoiler of home victories
            latest_str += 'Game Completed'
        elif latest < 10:
            latest_str += 'Top ' + str(latest)
        elif latest < 20:
            latest_str += 'Bot ' + str(latest)
        else:
            latest_str += 'Extra Innings'
        self.myscr.addstr(curses.LINES-3,0,latest_str)
        self.myscr.refresh()

    def selectToPlay(self):
        jump_prompt = 'Enter half inning to jump to: '
        jump = self.prompter(self.statuswin, jump_prompt)
        if jump == '':
            # return to listings
            return
        jump_pat = re.compile(r'(B|T|E)([1-9])?')
        match = re.search(jump_pat, jump.upper())
        if match is None:
            self.statuswin.clear()
            self.statuswin.addstr(0,0,'You have entered invalid half inning.')
            self.statuswin.refresh()
            time.sleep(2)
            return
        elif match.groups()[0] == 'E':
            try:
                start_time = self.innings[10]
            except KeyError:
                self.statuswin.clear()
                self.statuswin.addstr(0,0,'You have entered invalid half inning.')
                self.statuswin.refresh()
                time.sleep(2)
                return
        elif match.groups()[1] is None:
            statuswin.clear()
            self.statuswin.addstr(0,0,'You have entered invalid half inning.')
            self.statuswin.refresh()
            time.sleep(2)
            return
        elif match.groups()[0] == 'B':
            self.log.write('Matched ' + match.groups()[1] + ' inning.\n')
            inning = int(match.groups()[1]) + 10
        elif match.groups()[0] == 'T':
            self.log.write('Matched ' + match.groups()[1] + ' inning.\n')
            inning = int(match.groups()[1])
        try:
            start_time = self.innings[inning]
        except KeyError:
            self.statuswin.clear()
            self.statuswin.addstr(0,0,'You have entered invalid half inning. Returning to listings...')
            self.statuswin.refresh()
            time.sleep(3)
            return
        self.log.write('Selected start_time = ' + str(start_time) + '\n')
        self.statusRefresh('Requesting media stream with start at %s'%str(start_time))
        audio = False
        return start_time

    def getStartOfGame(self,mysched):
        start_time = 0
        try:
            innings = mysched.parseInningsXml(self.data[2][0][3],
                                              self.mycfg.get('use_nexdef'))
        except:
            return None
        if self.data[5] in ('I', 'D') and start_time == 0:
            if self.mycfg.get('live_from_start') and self.mycfg.get('use_nexdef'):
                if innings is not None:   
                    for i in range(len(innings)):
                        if int(innings[i][0]) == 0:
                            start_time = innings[i][2]
                            continue
                        else:
                            start_time = 0
        else:
            if self.mycfg.get('use_nexdef'):
                if innings is not None:
                    for i in range(len(innings)):
                        if int(innings[i][0]) == 0:
                            start_time = innings[i][2]
                            continue
                else:
                    start_time=self.data[8]
            
        return start_time

                
    def titleRefresh(self,mysched):
        if len(self.data) == 0:
            titlestr = 'ERROR OCCURRED IN JUMP TO INNINGS:'
        else:
            titlestr =  'JUMP TO HALF INNINGS: '
            titlestr += str(self.data[6])

        padding = curses.COLS - (len(titlestr) + 6)
        titlestr += ' '*padding
        pos = curses.COLS - 6
        self.titlewin.addstr(0,0,titlestr)
        self.titlewin.addstr(0,pos,'H', curses.A_BOLD)
        self.titlewin.addstr(0,pos+1, 'elp')
        self.titlewin.hline(1, 0, curses.ACS_HLINE, curses.COLS-1)
        self.titlewin.refresh()

    def statusRefresh(self,status_str=None):
        if status_str == None:
            status_str = 'Press L to return to listings...'

        # And write the status
        try:
            self.statuswin.addstr(0,0,status_str,curses.A_BOLD)
        except:
            rows = curses.LINES
            cols = curses.COLS
            slen = len(status_str)
            raise Exception,'(' + str(slen) + '/' + str(cols) + ',' + str(n) + '/' + str(rows) + ') ' + status_str
        self.statuswin.refresh()
