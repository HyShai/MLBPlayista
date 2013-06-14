#!/usr/bin/env python

from mlbListWin import MLBListWin
from mlbStats import MLBStats
import curses
from datetime import datetime
from mlbSchedule import gameTimeConvert
from mlbConstants import TEAMCODES

class MLBStatsWin(MLBListWin):

    def __init__(self,myscr,mycfg,data,last_update,statType,sortColumn):
        self.statdata = data
        self.last_update = last_update
        self.type = statType
        self.sort = sortColumn
        self.data = []
        self.records = []
        self.mycfg = mycfg
        self.myscr = myscr
        self.current_cursor = 0
        self.record_cursor = 0
        self.statuswin = curses.newwin(1,curses.COLS-1,curses.LINES-1,0)
        self.titlewin = curses.newwin(2,curses.COLS-1,0,0)

    def Refresh(self):
        if len(self.statdata) == 0:
            self.titlewin.refresh()
            self.myscr.refresh()
            self.statuswin.refresh()
            return

        self.myscr.clear()
        self.data = []
        if self.type == 'pitching':
            self.preparePitchingStats(self.type,self.sort)
        else:
            self.prepareHittingStats(self.type,self.sort)
        self.records = self.data[self.record_cursor:self.record_cursor+curses.LINES-4]
        n = 0
        for s in self.records:
            text = s[0]
            if n == self.current_cursor:
                pad = curses.COLS-1 - len(text)
                if pad > 0:
                    text += ' '*pad
                try:
                    self.myscr.addnstr(n+2,0,text,curses.COLS-2,
                                       s[1]|curses.A_REVERSE)
                except:
                    raise Exception,repr(s)
            else:
                self.myscr.addnstr(n+2,0,text,curses.COLS-2,s[1])
            n+=1
        self.myscr.refresh()

    def prepareHittingStats(self,statType='hitting', sortColumn='avg'):
        std_fmt = "%-2s %-12s %4s %3s %3s %3s %3s %3s %3s %3s %3s %3s %3s %3s %3s %3s %4s %4s %4s %5s"
        header_str = std_fmt % \
                   ( 'RK', 'Player', 'Team', 'Pos', 'G', 'AB', 'R', 'H',
                     '2B', '3B', 'HR', 'RBI', 'BB', 'SO', 'SB', 'CS', 
                     'AVG', 'OBP', 'SLG', 'OPS' )
        self.data.append((header_str,curses.A_BOLD))
        for player in self.statdata:
            playerStr = std_fmt % \
                   ( player['rank'], player['name_display_last_init'][:12],
                     player['team_abbrev'], player['pos'], player['g'],
                     player['ab'], player['r'], player['h'], player['d'],
                     player['t'], player['hr'], player['rbi'], 
                     player['bb'], player['so'], player['sb'], 
                     player['cs'], player['avg'], player['obp'], 
                     player['slg'], player['ops'] )
                     
            if player['team_abbrev'].lower() in self.mycfg.get('favorite'):
                if self.mycfg.get('use_color'):
                    self.data.append((playerStr,curses.color_pair(1)))
                #else:
                #    self.data.append((playerStr,curses.A_UNDERLINE))
            else:
                self.data.append((playerStr,0))

    def preparePitchingStats(self,statType='pitching', sortColumn='era'):
        std_fmt = "%-2s %-10s %4s %3s %3s %4s %3s %3s %3s %3s %5s %4s %3s %3s %3s %3s %3s %4s %4s"
        header_str = std_fmt % \
                   ( 'RK', 'Player', 'Team', 'W', 'L', 'ERA', 'G', 'GS',
                     'SV', 'SVO', 'IP', 'H', 'R', 'ER', 'HR', 'BB', 
                     'SO', 'AVG', 'WHIP' )
        self.data.append((header_str,curses.A_BOLD))
        for player in self.statdata:
            playerStr = std_fmt % \
                   ( player['rank'], player['name_display_last_init'][:10],
                     player['team_abbrev'], player['w'], player['l'],
                     player['era'], player['g'], player['gs'], player['sv'],
                     player['svo'], player['ip'], player['h'], 
                     player['r'], player['er'], 
                     player['hr'], player['bb'], 
                     player['so'], player['avg'], player['whip'] )
                     
            if player['team_abbrev'].lower() in self.mycfg.get('favorite'):
                if self.mycfg.get('use_color'):
                    self.data.append((playerStr,curses.color_pair(1)))
                #else:
                #    self.data.append((playerStr,curses.A_UNDERLINE))
            else:
                self.data.append((playerStr,0))

    def titleRefresh(self,mysched):
        if len(self.statdata) == 0:
            titlestr = "STATS NOT AVAILABLE"
        else:
            upd = datetime.strptime(self.last_update, "%Y-%m-%dT%H:%M:%S-04:00")
            update_datetime = gameTimeConvert(upd)
            update_str = update_datetime.strftime('%Y-%m-%d %H:%M:%S')
            type = self.type.upper()
            sort = self.sort.upper()
            titlestr = "%s STATS (%s): Last updated: %s" % ( type, 
                                                             sort, update_str )
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

        status_str = 'Press L to return to listings...'
        if self.mycfg.get('curses_debug'):
            status_str = 'd_len=%s, r_len=%s, cc=%s, rc=%s, cl_-4: %s' %\
                ( str(len(self.data)), str(len(self.records)),
                  str(self.current_cursor), str(self.record_cursor),
                  str(curses.LINES-4) )

        # And write the status
        try:
            self.statuswin.addnstr(0,0,status_str,curses.COLS-2,curses.A_BOLD)
        except:
            rows = curses.LINES
            cols = curses.COLS
            slen = len(status_str)
            raise Exception,'(' + str(slen) + '/' + str(cols) + ',' + str(n) + '/' + str(rows) + ') ' + status_str
        self.statuswin.refresh()
