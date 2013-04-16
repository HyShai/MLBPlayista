#!/usr/bin/env python

import curses
import time
from mlbListWin import MLBListWin
from mlbConstants import *

class MLBBoxScoreWin(MLBListWin):

    def __init__(self,myscr,mycfg,data):
        self.boxdata = data
        self.data = []
        self.records = []
        self.mycfg = mycfg
        self.myscr = myscr
        self.current_cursor = 0
        self.record_cursor = 0
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)
        # scrolling is uneven in box score - want to highlight
        # individual batters and pitchers but possibly not the text blobs
        self.meta = []

    def Refresh(self):
        if len(self.boxdata) == 0:
            self.titlewin.refresh()
            self.myscr.refresh()
            self.statuswin.refresh()
            return

        self.myscr.clear()
        self.data = []
        self.prepareBattingLines('away')
        if len(self.data) > 0:
            self.data.append(" ")
            self.data.append("TODO: BATTING AND FIELDING NOTES GO HERE")
            self.data.append(" ")
        self.prepareBattingLines('home')
        if len(self.data) > 0:
            self.data.append(" ")
            self.data.append("TODO: BATTING AND FIELDING NOTES GO HERE")
            self.data.append(" ")
        self.preparePitchingLines('away')
        if len(self.data) > 0:
            self.data.append(" ")
        self.preparePitchingLines('home')
        if len(self.data) > 0:
            self.data.append(" ")
            self.data.append("TODO: PITCHING NOTES GO HERE")
            self.data.append(" ")
            self.data.append("TODO: UMPIRES, ATTENDANCE, ETC GO HERE")
        #self.prepareGameLines()
        self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-4]
        n = 0
        for s in self.records:
            if n == self.current_cursor:
                pad = curses.COLS-1 - len(s)
                if pad > 0:
                    s += ' '*pad
                self.myscr.addstr(n+2,0,s,curses.A_REVERSE)
            else:
                self.myscr.addstr(n+2,0,s)
            n+=1
        self.myscr.refresh()

    def titleRefresh(self,mysched):
        if len(self.boxdata) == 0:
            titlestr = "NO BOX SCORE AVAILABLE FOR THIS GAME"
        else:
            titlestr = "BOX SCORE FOR  " +\
                self.boxdata['game']['game_id'] +\
                ' (' +\
                str(mysched.month) + '/' +\
                str(mysched.day) + '/' +\
                str(mysched.year) + ' ' +\
                ')'

        titlestr += "[INCOMPLETE]"

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

        status_str = '[INCOMPLETE] Press L to return to listings...'
        #status_str = 'd_len=%s, r_len=%s, cc=%s, rc=%s, cl_-4: %s' %\
        #    ( str(len(self.data)), str(len(self.records)),
        #      str(self.current_cursor), str(self.record_cursor),
        #      str(curses.LINES-4) )

        # And write the status
        try:
            self.statuswin.addstr(0,0,status_str,curses.A_BOLD)
        except:
            rows = curses.LINES
            cols = curses.COLS
            slen = len(status_str)
            raise Exception,'(' + str(slen) + '/' + str(cols) + ',' + str(n) + '/' + str(rows) + ') ' + status_str
        self.statuswin.refresh()

    # let's avoid a big indented for loop and require the team as an arg
    def preparePitchingLines(self,team):
        DOTS_LEN=34
        # shorten the path
        pitching = self.boxdata['pitching'][team]
        PITCHING_STATS = ( 'IP', 'H', 'R', 'ER', 'BB', 'SO', 'HR', ' ERA' )
        header_str = self.boxdata['game'][team+'_sname']
        header_str += ' Pitching'
        dots = DOTS_LEN - len(header_str)
        header_str += ' ' + dots*'.'
        for stat in PITCHING_STATS:
            header_str += '%5s' % stat
        self.data.append(header_str)
        self.data.append('')
        for pitcher in pitching['pitchers']['pitching-order']:
            name_str = pitching['pitchers'][pitcher]['name']
            # pitching note is W, L, SV info
            if pitching['pitchers'][pitcher].has_key('note'):
                name_str += ' ' + pitching['pitchers'][pitcher]['note']
            dots = DOTS_LEN - len(name_str)
            name_str += ' ' + dots*'.'
            for stat in PITCHING_STATS:
                if stat == 'IP':
                    ip = str(int(pitching['pitchers'][pitcher]['out'])/3)
                    ip += '.'
                    ip += str(int(pitching['pitchers'][pitcher]['out'])%3)
                    name_str += '%5s' % ip
                elif stat == ' ERA':
                    name_str += '%6s' % pitching['pitchers'][pitcher]['era']
                else:
                    name_str += '%5s' % pitching['pitchers'][pitcher][stat.lower()]
            self.data.append(name_str)
        # print totals
        totals_str = 'Totals'
        dots = DOTS_LEN - len(totals_str)
        totals_str += ' ' + dots*'.'
        for stat in PITCHING_STATS:
            if stat == 'IP':
                ip = str(int(pitching['out'])/3)
                ip += '.'
                ip += str(int(pitching['out'])%3)
                totals_str += '%5s' % ip
            elif stat == ' ERA':
                totals_str += '%6s' % pitching['era']
            else:
                totals_str += '%5s' % pitching[stat.lower()]
        self.data.append('')
        self.data.append(totals_str)
        

    # let's avoid a big indented for loop and require the team as an arg
    def prepareBattingLines(self,team):
        DOTS_LEN=34
        # shorten the path
        batting = self.boxdata['batting'][team]

        # build the batting order first
        battingOrder = dict()
        for batter_id in batting['batters']:
            try:
                order = int(batting['batters'][batter_id]['bo'])
                battingOrder[order] = batter_id
            except:
                continue
        batters = battingOrder.keys()
        batters = sorted(batters, key=int)

        BATTING_STATS=( 'AB', 'R', 'H', 'RBI', 'BB', 'SO', 'LOB', 'AVG')
        # first a header line
        header_str = self.boxdata['game'][team+'_sname']
        header_str += ' Batting'
        dots = DOTS_LEN - len(header_str)
        header_str += ' ' + dots*'.'
        for stat in BATTING_STATS:
            header_str += '%5s' % stat
        self.data.append(header_str)
        self.data.append('')

        # now the batters in the order just built
        for bo in batters:
            batter_id = battingOrder[bo]
            name_str = batting['batters'][batter_id]['name']
            name_str += ' '
            name_str += batting['batters'][batter_id]['pos']
            # indent if a substitution
            if bo % 100 > 0:
                if batting['batters'][batter_id].has_key('note'):
                    name_str = batting['batters'][batter_id]['note'] + name_str
                    name_str = ' ' + name_str
            dots=DOTS_LEN - len(name_str)
            name_str += ' ' + dots*'.'
            # now the stats
            for stat in BATTING_STATS:
                name_str += '%5s' % batting['batters'][batter_id][stat.lower()]
            self.data.append(name_str)
        self.data.append('')
        # print totals
        totals_str = 'Totals'
        dots = DOTS_LEN - len(totals_str)
        totals_str += ' ' + dots*'.'
        for stat in BATTING_STATS:
            totals_str += '%5s' % batting[stat.lower()]
        self.data.append(totals_str)
        # and the batting-note...
        if len(batting['batting-note']) > 0:
            self.data.append('')
            for bnote in batting['batting-note']:
                # batting-note can be multi-line, break it naturally
                if len(str(bnote)) > curses.COLS-1:
                    tmp = ''
                    for word in str(bnote).split(' '):
                        if len(tmp) + len(word) + 1 < curses.COLS-1:
                            tmp += word + ' '
                        else:
                            self.data.append(tmp.strip())
                            tmp = word + ' '
                    self.data.append(tmp.strip())
                    tmp = ''
                else:
                    self.data.append(str(bnote))

